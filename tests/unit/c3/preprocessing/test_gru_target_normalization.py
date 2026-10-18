"""Unit tests for GeoNex C3 GRU target normalization."""

import numpy as np
import pytest
import torch

from components.c3_forecasting.preprocessing.gru_target_normalization import (
    GRUTargetNormalizer,
)


def make_examples(targets: list[float]) -> list[dict]:
    """Build minimal training examples with regression targets."""
    return [{"target": target} for target in targets]


def test_fit_calculates_correct_training_statistics():
    examples = make_examples([20.0, 40.0, 60.0, 80.0])

    normalizer = GRUTargetNormalizer.fit(examples)

    assert normalizer.mean == pytest.approx(50.0)
    assert normalizer.std == pytest.approx(np.std([20.0, 40.0, 60.0, 80.0]))


def test_normalize_produces_expected_values():
    normalizer = GRUTargetNormalizer(mean=50.0, std=10.0)

    targets = torch.tensor([40.0, 50.0, 60.0])

    normalized = normalizer.normalize(targets)

    torch.testing.assert_close(
        normalized,
        torch.tensor([-1.0, 0.0, 1.0]),
    )


def test_denormalize_restores_original_units():
    normalizer = GRUTargetNormalizer(mean=50.0, std=10.0)

    predictions = torch.tensor([-1.0, 0.0, 1.0])

    restored = normalizer.denormalize(predictions)

    torch.testing.assert_close(
        restored,
        torch.tensor([40.0, 50.0, 60.0]),
    )


def test_normalize_denormalize_round_trip():
    normalizer = GRUTargetNormalizer(mean=47.7531, std=14.1019)

    original = torch.tensor([25.0, 40.0, 60.0, 85.0])

    normalized = normalizer.normalize(original)
    restored = normalizer.denormalize(normalized)

    torch.testing.assert_close(restored, original)


def test_constant_training_targets_use_safe_standard_deviation():
    examples = make_examples([55.0, 55.0, 55.0])

    normalizer = GRUTargetNormalizer.fit(examples)

    assert normalizer.mean == pytest.approx(55.0)
    assert normalizer.std == pytest.approx(1.0)

    normalized = normalizer.normalize(torch.tensor([55.0]))

    torch.testing.assert_close(
        normalized,
        torch.tensor([0.0]),
    )


def test_empty_training_examples_are_rejected():
    with pytest.raises(ValueError, match="empty examples"):
        GRUTargetNormalizer.fit([])


@pytest.mark.parametrize(
    "invalid_target",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_non_finite_training_targets_are_rejected(invalid_target):
    examples = make_examples([40.0, invalid_target, 60.0])

    with pytest.raises(ValueError, match="non-finite"):
        GRUTargetNormalizer.fit(examples)


def test_validation_targets_do_not_change_fitted_statistics():
    training_examples = make_examples([40.0, 50.0, 60.0])

    validation_examples = make_examples([90.0, 95.0, 99.0])

    normalizer = GRUTargetNormalizer.fit(training_examples)

    expected_mean = np.mean([40.0, 50.0, 60.0])
    expected_std = np.std([40.0, 50.0, 60.0])

    assert normalizer.mean == pytest.approx(expected_mean)
    assert normalizer.std == pytest.approx(expected_std)

    # Validation data is transformed, not used to refit the normalizer.
    validation_targets = torch.tensor([example["target"] for example in validation_examples])

    normalized_validation = normalizer.normalize(validation_targets)

    expected_normalized = (validation_targets - normalizer.mean) / normalizer.std

    torch.testing.assert_close(
        normalized_validation,
        expected_normalized,
    )

    # Fitted statistics must remain unchanged.
    assert normalizer.mean == pytest.approx(expected_mean)
    assert normalizer.std == pytest.approx(expected_std)


def test_fitting_is_deterministic():
    examples = make_examples([25.0, 35.0, 45.0, 55.0])

    first = GRUTargetNormalizer.fit(examples)
    second = GRUTargetNormalizer.fit(examples)

    assert first == second


def test_normalizer_parameters_are_serializable():
    normalizer = GRUTargetNormalizer(mean=47.5, std=12.25)

    parameters = normalizer.to_dict()

    assert parameters == {
        "mean": 47.5,
        "std": 12.25,
    }


def test_normalization_preserves_tensor_shape():
    normalizer = GRUTargetNormalizer(mean=50.0, std=10.0)

    targets = torch.tensor(
        [
            [40.0],
            [50.0],
            [60.0],
        ]
    )

    normalized = normalizer.normalize(targets)
    restored = normalizer.denormalize(normalized)

    assert normalized.shape == targets.shape
    assert restored.shape == targets.shape


def test_normalization_preserves_tensor_dtype():
    normalizer = GRUTargetNormalizer(mean=50.0, std=10.0)

    targets = torch.tensor(
        [40.0, 50.0, 60.0],
        dtype=torch.float32,
    )

    normalized = normalizer.normalize(targets)
    restored = normalizer.denormalize(normalized)

    assert normalized.dtype == torch.float32
    assert restored.dtype == torch.float32
