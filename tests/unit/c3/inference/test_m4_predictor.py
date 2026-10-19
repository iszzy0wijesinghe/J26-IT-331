"""Tests for GeoNex C3 M4 checkpoint-based inference."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch

from components.c3_forecasting.inference.m4_predictor import C3M4Predictor
from components.c3_forecasting.models.standard_gru import C3StandardGRU
from components.c3_forecasting.preprocessing.gru_dataset import SENSOR_NAMES


@pytest.fixture
def checkpoint_data() -> dict:
    """Create a minimal valid M4 checkpoint without requiring trained files."""

    model = C3StandardGRU(
        input_size=20,
        hidden_size=8,
        num_layers=1,
    )

    return {
        "model": "m4_gru",
        "model_state_dict": model.state_dict(),
        "ablation": "C",
        "include_time": True,
        "include_mode": True,
        "horizon_minutes": 15,
        "input_size": 20,
        "hidden_size": 8,
        "num_layers": 1,
        "normalizer": {
            "sensor_normalizer": {
                "sensor_names": list(SENSOR_NAMES),
                "means": [0.0] * len(SENSOR_NAMES),
                "stds": [1.0] * len(SENSOR_NAMES),
            },
            "time_mean": 0.0,
            "time_std": 1.0,
        },
        "target_normalizer": {
            "mean": 50.0,
            "std": 10.0,
        },
    }


def save_checkpoint(
    tmp_path: Path,
    checkpoint: dict,
    name: str = "m4_test.pt",
) -> Path:
    path = tmp_path / name
    torch.save(checkpoint, path)
    return path


@pytest.mark.parametrize(
    ("ablation", "include_time", "include_mode"),
    [
        ("A", True, False),
        ("B", False, True),
        ("C", True, True),
    ],
)
def test_loads_supported_ablations(
    tmp_path: Path,
    checkpoint_data: dict,
    ablation: str,
    include_time: bool,
    include_mode: bool,
) -> None:
    checkpoint_data["ablation"] = ablation
    checkpoint_data["include_time"] = include_time
    checkpoint_data["include_mode"] = include_mode

    path = save_checkpoint(tmp_path, checkpoint_data)

    predictor = C3M4Predictor(path)

    assert predictor.ablation == ablation
    assert predictor.include_time is include_time
    assert predictor.include_mode is include_mode


def test_missing_checkpoint(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        C3M4Predictor(tmp_path / "missing.pt")


def test_rejects_wrong_model_type(
    tmp_path: Path,
    checkpoint_data: dict,
) -> None:
    checkpoint_data["model"] = "m3_gru"

    path = save_checkpoint(tmp_path, checkpoint_data)

    with pytest.raises(ValueError, match="not an M4"):
        C3M4Predictor(path)


def test_rejects_inconsistent_ablation_flags(
    tmp_path: Path,
    checkpoint_data: dict,
) -> None:
    checkpoint_data["ablation"] = "A"
    checkpoint_data["include_time"] = False
    checkpoint_data["include_mode"] = True

    path = save_checkpoint(tmp_path, checkpoint_data)

    with pytest.raises(ValueError, match="feature flags"):
        C3M4Predictor(path)


def test_rejects_incorrect_sensor_order(
    tmp_path: Path,
    checkpoint_data: dict,
) -> None:
    checkpoint_data["normalizer"]["sensor_normalizer"]["sensor_names"] = list(
        reversed(SENSOR_NAMES)
    )

    path = save_checkpoint(tmp_path, checkpoint_data)

    with pytest.raises(ValueError, match="sensor ordering"):
        C3M4Predictor(path)


def test_rejects_invalid_input_width(
    tmp_path: Path,
    checkpoint_data: dict,
) -> None:
    path = save_checkpoint(tmp_path, checkpoint_data)

    predictor = C3M4Predictor(path)

    with pytest.raises(ValueError, match="20"):
        predictor.predict_array(np.zeros((4, 14), dtype=np.float32))


def test_rejects_nonfinite_input(
    tmp_path: Path,
    checkpoint_data: dict,
) -> None:
    path = save_checkpoint(tmp_path, checkpoint_data)

    predictor = C3M4Predictor(path)

    sequence = np.zeros((4, 20), dtype=np.float32)
    sequence[0, 0] = np.nan

    with pytest.raises(ValueError, match="non-finite"):
        predictor.predict_array(sequence)


@pytest.mark.parametrize(
    ("ablation", "include_time", "include_mode"),
    [
        ("A", True, False),
        ("B", False, True),
        ("C", True, True),
    ],
)
def test_predicts_finite_value(
    tmp_path: Path,
    checkpoint_data: dict,
    ablation: str,
    include_time: bool,
    include_mode: bool,
) -> None:
    checkpoint_data["ablation"] = ablation
    checkpoint_data["include_time"] = include_time
    checkpoint_data["include_mode"] = include_mode

    path = save_checkpoint(tmp_path, checkpoint_data)

    predictor = C3M4Predictor(path)

    sequence = np.zeros((4, 20), dtype=np.float32)

    sequence[:, 7:14] = 1.0
    sequence[1:, 14] = np.log1p(300.0)
    sequence[1:, 15] = 1.0
    sequence[:, 16] = 1.0

    prediction = predictor.predict_array(sequence)

    assert isinstance(prediction, float)
    assert np.isfinite(prediction)


def test_prediction_is_deterministic(
    tmp_path: Path,
    checkpoint_data: dict,
) -> None:
    path = save_checkpoint(tmp_path, checkpoint_data)

    predictor = C3M4Predictor(path)

    sequence = np.zeros((4, 20), dtype=np.float32)
    sequence[:, 7:14] = 1.0
    sequence[:, 16] = 1.0

    first = predictor.predict_array(sequence)
    second = predictor.predict_array(sequence)

    assert first == second


def test_rejects_invalid_target_std(
    tmp_path: Path,
    checkpoint_data: dict,
) -> None:
    checkpoint_data["target_normalizer"]["std"] = 0.0

    path = save_checkpoint(tmp_path, checkpoint_data)

    with pytest.raises(ValueError, match="Target standard deviation"):
        C3M4Predictor(path)


def test_rejects_invalid_time_std(
    tmp_path: Path,
    checkpoint_data: dict,
) -> None:
    checkpoint_data["normalizer"]["time_std"] = 0.0

    path = save_checkpoint(tmp_path, checkpoint_data)

    with pytest.raises(ValueError, match="Time standard deviation"):
        C3M4Predictor(path)
