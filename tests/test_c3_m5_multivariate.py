import numpy as np
import pytest
import torch

from components.c3_forecasting.models.m5_multivariate_gru import (
    C3M5MultivariateGRU,
    INPUT_SIZE,
    SENSOR_COUNT,
    FORECAST_HORIZONS,
)

from components.c3_forecasting.preprocessing.m5_features import (
    extract_m5_sequence,
)


def make_observations():

    return [
        {
            "timestamp": "2026-10-21T00:00:00Z",
            "operating_mode": "IDLE",
            "soil_moisture_pct": 45.0,
            "rainfall_proxy_counts": 3.0,
            "tilt_deg": 1.2,
            "vibration_g": 0.02,
            "fsr_adc": 1200,
            "air_temperature_c": 28.0,
            "humidity_pct": 75.0,
        },
        {
            "timestamp": "2026-10-21T00:07:00Z",
            "operating_mode": "RISK",
            "soil_moisture_pct": 47.0,
            "rainfall_proxy_counts": 5.0,
            "tilt_deg": 1.4,
            "vibration_g": 0.03,
            "fsr_adc": 1220,
            "air_temperature_c": 27.8,
            "humidity_pct": 78.0,
        },
        {
            "timestamp": "2026-10-21T00:08:00Z",
            "operating_mode": "EMERGENCY",
            "soil_moisture_pct": 49.0,
            "rainfall_proxy_counts": 7.0,
            "tilt_deg": 1.7,
            "vibration_g": 0.05,
            "fsr_adc": 1250,
            "air_temperature_c": 27.5,
            "humidity_pct": 81.0,
        },
    ]


def test_feature_dimensions():

    features = extract_m5_sequence(
        make_observations()
    )

    assert features.shape == (3, INPUT_SIZE)


def test_elapsed_time():

    features = extract_m5_sequence(
        make_observations()
    )

    assert features[0, 14] == 0.0
    assert features[0, 15] == 0.0

    assert features[1, 14] == pytest.approx(
        np.log1p(420)
    )

    assert features[2, 14] == pytest.approx(
        np.log1p(60)
    )


def test_emergency_mode_supported():

    features = extract_m5_sequence(
        make_observations()
    )

    # 14 sensor/mask + 2 time + 5 modes
    assert INPUT_SIZE == 21

    # EMERGENCY is the fifth operating mode.
    assert features[2, 20] == 1.0


def test_model_output_shape():

    model = C3M5MultivariateGRU()

    inputs = torch.randn(
        4,
        12,
        INPUT_SIZE,
    )

    outputs = model(inputs)

    assert outputs.shape == (
        4,
        len(FORECAST_HORIZONS),
        SENSOR_COUNT,
    )


def test_variable_length_sequences():

    model = C3M5MultivariateGRU()

    inputs = torch.randn(
        3,
        10,
        INPUT_SIZE,
    )

    lengths = torch.tensor(
        [10, 7, 5]
    )

    outputs = model(
        inputs,
        lengths,
    )

    assert outputs.shape == (
        3,
        3,
        7,
    )


def test_invalid_feature_dimension():

    model = C3M5MultivariateGRU()

    inputs = torch.randn(
        2,
        10,
        10,
    )

    with pytest.raises(ValueError):
        model(inputs)


def test_missing_sensor_mask():

    observations = make_observations()

    observations[1]["humidity_pct"] = None

    features = extract_m5_sequence(
        observations
    )

    # Humidity is sensor index 6.
    # Its validity mask is index 13.
    assert features[1, 13] == 0.0


def test_non_monotonic_timestamps():

    observations = make_observations()

    observations[1]["timestamp"] = (
        observations[0]["timestamp"]
    )

    with pytest.raises(ValueError):
        extract_m5_sequence(observations)