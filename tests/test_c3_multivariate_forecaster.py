"""
GeoNex C3 multivariate forecasting tests.
"""

from datetime import timedelta

import pytest

from components.c3_forecasting.inference.multivariate_forecaster import (
    SENSOR_CONFIG,
    apply_sensor_bounds,
    calculate_time_aware_trend,
    predict_sensor_value,
    validate_observations,
    MultivariateForecastingError,
)


def make_observations():

    base_time = "2026-10-21T00:00:00+00:00"

    from datetime import datetime

    start = datetime.fromisoformat(base_time)

    observations = []

    for index in range(5):

        timestamp = (
            start + timedelta(minutes=index * 5)
        ).isoformat()

        observation = {
            "timestamp": timestamp,
            "operating_mode": "IDLE",
            "soil_moisture_pct": 40 + index,
            "humidity_pct": 70 + index,
            "air_temperature_c": 28 - index * 0.1,
            "rainfall_proxy_counts": 10 + index,
            "tilt_deg": 1.0 + index * 0.1,
            "vibration_g": 0.02 + index * 0.001,
            "fsr_adc": 1000 + index * 10,
        }

        observations.append(observation)

    return observations


def test_sensor_configuration():

    assert len(SENSOR_CONFIG) == 7


def test_observation_validation():

    observations = make_observations()

    validate_observations(observations)


def test_positive_soil_moisture_trend():

    observations = make_observations()

    latest, slope = calculate_time_aware_trend(
        observations,
        "soil_moisture_pct",
    )

    assert latest == 44.0
    assert slope > 0


def test_future_prediction_increases():

    observations = make_observations()

    predicted = predict_sensor_value(
        observations,
        "soil_moisture_pct",
        15,
    )

    assert predicted > 44.0


def test_humidity_upper_bound():

    result = apply_sensor_bounds(
        "humidity_pct",
        120.0,
    )

    assert result == 100.0


def test_negative_rainfall_proxy_is_clamped():

    result = apply_sensor_bounds(
        "rainfall_proxy_counts",
        -10.0,
    )

    assert result == 0.0


def test_duplicate_timestamp_rejected():

    observations = make_observations()

    observations[1]["timestamp"] = (
        observations[0]["timestamp"]
    )

    with pytest.raises(
        MultivariateForecastingError
    ):
        validate_observations(observations)


def test_missing_sensor_rejected():

    observations = make_observations()

    observations[0]["humidity_pct"] = None

    with pytest.raises(
        MultivariateForecastingError
    ):
        validate_observations(observations)