"""Unit tests for GeoNex C3 GRU checkpoint inference."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch

from components.c3_forecasting.inference.gru_predictor import C3GRUPredictor
from components.c3_forecasting.models.standard_gru import C3StandardGRU
from components.c3_forecasting.preprocessing.gru_dataset import (
    INPUT_FEATURE_COUNT,
    SENSOR_NAMES,
)


@pytest.fixture
def checkpoint_path(tmp_path: Path) -> Path:
    """Create a lightweight, valid GRU checkpoint for unit testing."""

    torch.manual_seed(42)

    model = C3StandardGRU(
        input_size=INPUT_FEATURE_COUNT,
        hidden_size=8,
        num_layers=1,
    )

    path = tmp_path / "test_gru.pt"

    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "horizon_minutes": 15,
            "input_size": INPUT_FEATURE_COUNT,
            "hidden_size": 8,
            "num_layers": 1,
            "normalizer": {
                "sensor_names": list(SENSOR_NAMES),
                "means": [10.0] * len(SENSOR_NAMES),
                "stds": [2.0] * len(SENSOR_NAMES),
            },
            "target_normalizer": {
                "mean": 50.0,
                "std": 10.0,
            },
        },
        path,
    )

    return path


@pytest.fixture
def valid_sequence() -> np.ndarray:
    """Return a valid unnormalized GRU sequence."""

    sensor_count = len(SENSOR_NAMES)

    values = np.full(
        (5, sensor_count),
        12.0,
        dtype=np.float32,
    )

    masks = np.ones(
        (5, sensor_count),
        dtype=np.float32,
    )

    return np.concatenate(
        [values, masks],
        axis=1,
    )


def test_load_valid_checkpoint(checkpoint_path: Path) -> None:
    predictor = C3GRUPredictor(checkpoint_path)

    assert predictor.horizon_minutes == 15
    assert predictor.model.input_size == INPUT_FEATURE_COUNT
    assert predictor.model.hidden_size == 8
    assert predictor.model.training is False


def test_missing_checkpoint_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        C3GRUPredictor(tmp_path / "missing.pt")


def test_invalid_device_raises(checkpoint_path: Path) -> None:
    with pytest.raises(ValueError, match="Device"):
        C3GRUPredictor(checkpoint_path, device="cuda")


def test_predict_returns_finite_float(
    checkpoint_path: Path,
    valid_sequence: np.ndarray,
) -> None:
    predictor = C3GRUPredictor(checkpoint_path)

    prediction = predictor.predict_array(valid_sequence)

    assert isinstance(prediction, float)
    assert np.isfinite(prediction)


def test_predict_is_deterministic(
    checkpoint_path: Path,
    valid_sequence: np.ndarray,
) -> None:
    predictor = C3GRUPredictor(checkpoint_path)

    first = predictor.predict_array(valid_sequence)
    second = predictor.predict_array(valid_sequence)

    assert first == pytest.approx(second, abs=1e-7)


def test_predict_does_not_modify_input(
    checkpoint_path: Path,
    valid_sequence: np.ndarray,
) -> None:
    predictor = C3GRUPredictor(checkpoint_path)

    original = valid_sequence.copy()

    predictor.predict_array(valid_sequence)

    np.testing.assert_array_equal(valid_sequence, original)


def test_empty_sequence_rejected(checkpoint_path: Path) -> None:
    predictor = C3GRUPredictor(checkpoint_path)

    sequence = np.empty(
        (0, INPUT_FEATURE_COUNT),
        dtype=np.float32,
    )

    with pytest.raises(ValueError, match="empty"):
        predictor.predict_array(sequence)


def test_wrong_feature_count_rejected(checkpoint_path: Path) -> None:
    predictor = C3GRUPredictor(checkpoint_path)

    sequence = np.zeros(
        (5, INPUT_FEATURE_COUNT - 1),
        dtype=np.float32,
    )

    with pytest.raises(ValueError, match="Expected"):
        predictor.predict_array(sequence)


def test_nonfinite_sequence_rejected(
    checkpoint_path: Path,
    valid_sequence: np.ndarray,
) -> None:
    predictor = C3GRUPredictor(checkpoint_path)

    valid_sequence[0, 0] = np.nan

    with pytest.raises(ValueError, match="non-finite"):
        predictor.predict_array(valid_sequence)


def test_invalid_sensor_order_rejected(
    checkpoint_path: Path,
) -> None:
    checkpoint = torch.load(
        checkpoint_path,
        weights_only=True,
    )

    checkpoint["normalizer"]["sensor_names"] = list(reversed(SENSOR_NAMES))

    torch.save(checkpoint, checkpoint_path)

    with pytest.raises(ValueError, match="sensor ordering"):
        C3GRUPredictor(checkpoint_path)


def test_invalid_sensor_std_rejected(
    checkpoint_path: Path,
) -> None:
    checkpoint = torch.load(
        checkpoint_path,
        weights_only=True,
    )

    checkpoint["normalizer"]["stds"][0] = 0.0

    torch.save(checkpoint, checkpoint_path)

    with pytest.raises(ValueError, match="standard deviations"):
        C3GRUPredictor(checkpoint_path)


def test_invalid_target_std_rejected(
    checkpoint_path: Path,
) -> None:
    checkpoint = torch.load(
        checkpoint_path,
        weights_only=True,
    )

    checkpoint["target_normalizer"]["std"] = 0.0

    torch.save(checkpoint, checkpoint_path)

    with pytest.raises(ValueError, match="Target standard deviation"):
        C3GRUPredictor(checkpoint_path)
