"""Tests for GeoNex C3 M4 temporal feature extraction."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from components.c3_forecasting.preprocessing.gru_dataset import (
    INPUT_FEATURE_COUNT,
    SENSOR_NAMES,
    extract_gru_sequence,
)
from components.c3_forecasting.preprocessing.m4_features import (
    M4_INPUT_FEATURE_COUNT,
    OPERATING_MODES,
    extract_m4_sequence,
)


@pytest.fixture
def temporal_sequence() -> dict:
    """Construct a minimal valid synthetic temporal sequence."""

    steps = []

    for index, (mode, interval) in enumerate(
        [
            ("DEEP_SLEEP", 0.0),
            ("IDLE", 900.0),
            ("RISK", 300.0),
            ("WARNING", 60.0),
        ]
    ):
        features = {
            sensor: float(index + sensor_index + 1)
            for sensor_index, sensor in enumerate(SENSOR_NAMES)
        }

        masks = {sensor: True for sensor in SENSOR_NAMES}

        steps.append(
            {
                "features": features,
                "masks": masks,
                "operating_mode": mode,
                "delta_t_seconds": interval,
                "quality": {
                    "first_interval_unknown": index == 0,
                    "imputed_flags": {},
                    "corrected_flags": {},
                },
            }
        )

    return {"steps": steps}


def test_m4_feature_shape(temporal_sequence: dict) -> None:
    features = extract_m4_sequence(temporal_sequence)

    assert features.shape == (4, M4_INPUT_FEATURE_COUNT)
    assert M4_INPUT_FEATURE_COUNT == 20


def test_preserves_m3_sensor_features(temporal_sequence: dict) -> None:
    expected = extract_gru_sequence(temporal_sequence)
    actual = extract_m4_sequence(temporal_sequence)

    np.testing.assert_array_equal(
        actual[:, :INPUT_FEATURE_COUNT],
        expected,
    )


def test_elapsed_time_encoding(temporal_sequence: dict) -> None:
    features = extract_m4_sequence(temporal_sequence)

    np.testing.assert_allclose(
        features[:, 14],
        [
            0.0,
            np.log1p(900.0),
            np.log1p(300.0),
            np.log1p(60.0),
        ],
        rtol=1e-6,
    )


def test_interval_known_indicator(temporal_sequence: dict) -> None:
    features = extract_m4_sequence(temporal_sequence)

    np.testing.assert_array_equal(
        features[:, 15],
        [0.0, 1.0, 1.0, 1.0],
    )


def test_mode_one_hot_encoding(temporal_sequence: dict) -> None:
    features = extract_m4_sequence(temporal_sequence)

    np.testing.assert_array_equal(
        features[:, 16:20],
        np.eye(len(OPERATING_MODES), dtype=np.float32),
    )


def test_time_only_ablation(temporal_sequence: dict) -> None:
    features = extract_m4_sequence(
        temporal_sequence,
        include_time=True,
        include_mode=False,
    )

    assert np.any(features[:, 14:16] != 0)
    assert np.all(features[:, 16:20] == 0)


def test_mode_only_ablation(temporal_sequence: dict) -> None:
    features = extract_m4_sequence(
        temporal_sequence,
        include_time=False,
        include_mode=True,
    )

    assert np.all(features[:, 14:16] == 0)
    assert np.any(features[:, 16:20] != 0)


def test_combined_ablation(temporal_sequence: dict) -> None:
    features = extract_m4_sequence(temporal_sequence)

    assert np.any(features[:, 14:16] != 0)
    assert np.any(features[:, 16:20] != 0)


def test_unknown_operating_mode_rejected(
    temporal_sequence: dict,
) -> None:
    temporal_sequence["steps"][1]["operating_mode"] = "UNKNOWN"

    with pytest.raises(ValueError, match="Unsupported operating mode"):
        extract_m4_sequence(temporal_sequence)


@pytest.mark.parametrize("invalid_interval", [-1.0, np.nan, np.inf, True, None])
def test_invalid_elapsed_time_rejected(
    temporal_sequence: dict,
    invalid_interval: object,
) -> None:
    temporal_sequence["steps"][1]["delta_t_seconds"] = invalid_interval

    with pytest.raises(ValueError, match="Invalid elapsed-time"):
        extract_m4_sequence(temporal_sequence)


def test_first_interval_must_be_unknown(
    temporal_sequence: dict,
) -> None:
    temporal_sequence["steps"][0]["quality"]["first_interval_unknown"] = False

    with pytest.raises(ValueError, match="First timestep"):
        extract_m4_sequence(temporal_sequence)


def test_later_interval_cannot_be_unknown(
    temporal_sequence: dict,
) -> None:
    temporal_sequence["steps"][2]["quality"]["first_interval_unknown"] = True

    with pytest.raises(ValueError, match="Only the first"):
        extract_m4_sequence(temporal_sequence)


def test_does_not_mutate_source(temporal_sequence: dict) -> None:
    original = deepcopy(temporal_sequence)

    extract_m4_sequence(temporal_sequence)

    assert temporal_sequence == original


def test_output_is_float32_and_finite(temporal_sequence: dict) -> None:
    features = extract_m4_sequence(temporal_sequence)

    assert features.dtype == np.float32
    assert np.isfinite(features).all()
