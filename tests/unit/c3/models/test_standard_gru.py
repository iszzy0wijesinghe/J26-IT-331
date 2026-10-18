"""Tests for GeoNex C3 GRU dataset, normalization, and model."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from components.c3_forecasting.models.standard_gru import C3StandardGRU
from components.c3_forecasting.preprocessing.gru_dataset import (
    INPUT_FEATURE_COUNT,
    SENSOR_NAMES,
    C3GRUDataset,
    collate_gru_batch,
    extract_gru_sequence,
)
from components.c3_forecasting.preprocessing.gru_normalization import GRUNormalizer


def make_step(
    *,
    value: float = 20.0,
    observed: bool = True,
    imputed: bool = False,
    corrected: bool = False,
) -> dict:
    """Create a minimal C3 temporal step."""

    sensor = SENSOR_NAMES[0]

    return {
        "features": {sensor: value},
        "masks": {sensor: observed},
        "quality": {
            "imputed_flags": {sensor: imputed},
            "corrected_flags": {sensor: corrected},
        },
    }


def make_array(
    values: list[float],
    masks: list[float] | None = None,
) -> np.ndarray:
    """Construct a GRU input array using the first sensor channel."""

    if masks is None:
        masks = [1.0] * len(values)

    array = np.zeros(
        (len(values), INPUT_FEATURE_COUNT),
        dtype=np.float32,
    )

    array[:, 0] = values
    array[:, len(SENSOR_NAMES)] = masks

    return array


def test_gru_sequence_has_fourteen_features():
    sequence = {
        "steps": [
            make_step(value=10.0),
            make_step(value=20.0),
        ]
    }

    result = extract_gru_sequence(sequence)

    assert result.shape == (2, 14)
    assert result.dtype == np.float32

    assert result[0, 0] == 10.0
    assert result[1, 0] == 20.0

    assert result[0, 7] == 1.0
    assert result[1, 7] == 1.0


@pytest.mark.parametrize(
    ("observed", "imputed", "corrected"),
    [
        (False, False, False),
        (True, True, False),
        (True, False, True),
    ],
)
def test_invalid_sensor_observations_are_masked(
    observed,
    imputed,
    corrected,
):
    sequence = {
        "steps": [
            make_step(
                value=999.0,
                observed=observed,
                imputed=imputed,
                corrected=corrected,
            )
        ]
    }

    result = extract_gru_sequence(sequence)

    assert result[0, 0] == 0.0
    assert result[0, 7] == 0.0


def test_gru_sequence_rejects_empty_history():
    with pytest.raises(ValueError, match="empty"):
        extract_gru_sequence({"steps": []})


def test_gru_dataset_filters_horizon():
    examples = [
        {
            "sequence": make_array([10.0]),
            "target": 11.0,
            "horizon_minutes": 15,
        },
        {
            "sequence": make_array([20.0]),
            "target": 21.0,
            "horizon_minutes": 30,
        },
        {
            "sequence": make_array([30.0]),
            "target": 31.0,
            "horizon_minutes": 60,
        },
    ]

    dataset = C3GRUDataset(
        dataset_dir="unused",
        split="train",
        horizon_minutes=30,
        preloaded_examples=examples,
    )

    assert len(dataset) == 1
    assert dataset[0]["target"] == 21.0


def test_collate_preserves_lengths_and_padding():
    batch = [
        {
            "sequence": make_array([10.0, 20.0]),
            "target": 30.0,
        },
        {
            "sequence": make_array([40.0, 50.0, 60.0]),
            "target": 70.0,
        },
    ]

    result = collate_gru_batch(batch)

    assert result["inputs"].shape == (2, 3, 14)
    assert result["lengths"].tolist() == [2, 3]
    assert result["targets"].tolist() == [30.0, 70.0]

    assert torch.all(
        result["inputs"][0, 2] == 0
    )


def test_normalizer_uses_only_valid_observations():
    sequence = make_array(
        values=[10.0, 20.0, 999.0],
        masks=[1.0, 1.0, 0.0],
    )

    normalizer = GRUNormalizer.fit(
        [{"sequence": sequence}]
    )

    assert normalizer.means[0] == pytest.approx(15.0)
    assert normalizer.stds[0] == pytest.approx(5.0)

    transformed = normalizer.transform(sequence)

    assert transformed[0, 0] == pytest.approx(-1.0)
    assert transformed[1, 0] == pytest.approx(1.0)

    assert transformed[2, 0] == 0.0
    assert transformed[2, 7] == 0.0


def test_validation_values_do_not_change_fitted_statistics():
    training = [
        {
            "sequence": make_array([10.0, 20.0]),
        }
    ]

    validation = make_array([1000.0, 2000.0])

    normalizer = GRUNormalizer.fit(training)

    original_mean = normalizer.means.copy()
    original_std = normalizer.stds.copy()

    normalizer.transform(validation)

    np.testing.assert_array_equal(
        normalizer.means,
        original_mean,
    )

    np.testing.assert_array_equal(
        normalizer.stds,
        original_std,
    )

    assert normalizer.means[0] == pytest.approx(15.0)


def test_normalizer_preserves_masks():
    sequence = make_array(
        values=[10.0, 20.0, 30.0],
        masks=[1.0, 0.0, 1.0],
    )

    normalizer = GRUNormalizer.fit(
        [{"sequence": sequence}]
    )

    transformed = normalizer.transform(sequence)

    np.testing.assert_array_equal(
        transformed[:, 7:],
        sequence[:, 7:],
    )

    assert transformed[1, 0] == 0.0


def test_gru_forward_output_shape():
    model = C3StandardGRU(
        input_size=14,
        hidden_size=64,
        num_layers=1,
    )

    inputs = torch.randn(4, 10, 14)

    lengths = torch.tensor(
        [3, 5, 8, 10],
        dtype=torch.long,
    )

    predictions = model(inputs, lengths)

    assert predictions.shape == (4,)
    assert torch.isfinite(predictions).all()


def test_gru_ignores_padded_timesteps():
    torch.manual_seed(42)

    model = C3StandardGRU()
    model.eval()

    inputs = torch.randn(3, 10, 14)

    lengths = torch.tensor(
        [3, 6, 10],
        dtype=torch.long,
    )

    with torch.no_grad():
        original = model(inputs, lengths)

        modified = inputs.clone()

        for index, length in enumerate(lengths.tolist()):
            modified[index, length:] = 999.0

        changed = model(modified, lengths)

    torch.testing.assert_close(
        original,
        changed,
        atol=1e-6,
        rtol=0,
    )


def test_gru_backpropagation():
    model = C3StandardGRU()

    inputs = torch.randn(4, 8, 14)

    lengths = torch.tensor(
        [3, 5, 7, 8],
        dtype=torch.long,
    )

    predictions = model(inputs, lengths)

    loss = predictions.square().mean()
    loss.backward()

    gradients = [
        parameter.grad
        for parameter in model.parameters()
    ]

    assert all(
        gradient is not None
        for gradient in gradients
    )

    assert all(
        torch.isfinite(gradient).all()
        for gradient in gradients
    )


def test_gru_rejects_invalid_sequence_lengths():
    model = C3StandardGRU()

    inputs = torch.randn(2, 5, 14)

    with pytest.raises(ValueError, match="positive"):
        model(
            inputs,
            torch.tensor([0, 5]),
        )

    with pytest.raises(ValueError, match="exceeds"):
        model(
            inputs,
            torch.tensor([6, 5]),
        )