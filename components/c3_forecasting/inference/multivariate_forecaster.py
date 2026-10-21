"""
GeoNex C3 - Multivariate Environmental Forecasting

Development stage:
    Research baseline (not trained neural forecasting).

Purpose:
    Forecast multiple environmental sensor measurements
    from Golden Database historical observations.

Supported horizons:
    15, 30, 60 minutes.

Research principles:
    - No future observations used as inputs.
    - Actual elapsed time is respected.
    - Historical operating modes are preserved.
    - Predictions are generated per sensor variable.
    - Sensor outputs are bounded where physically appropriate.
    - No unsupported landslide-event probability claims.

IMPORTANT:
    This is a time-aware trend baseline.
    It is not the final mode-conditioned GRU model.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np

from apps.c3_workbench.forecasting_reader import (
    load_historical_sequence,
    parse_timestamp,
)


FORECAST_HORIZONS = (15, 30, 60)


SENSOR_CONFIG = {
    "soil_moisture_pct": {
        "minimum": 0.0,
        "maximum": 100.0,
        "unit": "%",
    },
    "humidity_pct": {
        "minimum": 0.0,
        "maximum": 100.0,
        "unit": "%",
    },
    "air_temperature_c": {
        "minimum": None,
        "maximum": None,
        "unit": "C",
    },
    "rainfall_proxy_counts": {
        "minimum": 0.0,
        "maximum": None,
        "unit": "proxy_counts",
    },
    "tilt_deg": {
        "minimum": None,
        "maximum": None,
        "unit": "degrees",
    },
    "vibration_g": {
        "minimum": 0.0,
        "maximum": None,
        "unit": "g",
    },
    "fsr_adc": {
        "minimum": 0.0,
        "maximum": None,
        "unit": "adc",
    },
}


class MultivariateForecastingError(RuntimeError):
    pass


def validate_observations(
    observations: list[dict[str, Any]],
) -> None:

    if len(observations) < 3:
        raise MultivariateForecastingError(
            "At least three observations are required."
        )

    previous_time = None

    for observation in observations:

        current_time = parse_timestamp(
            observation["timestamp"]
        )

        if previous_time is not None:
            if current_time <= previous_time:
                raise MultivariateForecastingError(
                    "Observation timestamps must be strictly increasing."
                )

        previous_time = current_time

        for sensor in SENSOR_CONFIG:

            value = observation.get(sensor)

            if value is None:
                raise MultivariateForecastingError(
                    f"Missing sensor value: {sensor}"
                )

            try:
                numeric_value = float(value)
            except (TypeError, ValueError) as exc:
                raise MultivariateForecastingError(
                    f"Invalid numeric value for {sensor}"
                ) from exc

            if not np.isfinite(numeric_value):
                raise MultivariateForecastingError(
                    f"Non-finite value for {sensor}"
                )


def calculate_elapsed_minutes(
    observations: list[dict[str, Any]],
) -> np.ndarray:

    first_timestamp = parse_timestamp(
        observations[0]["timestamp"]
    )

    elapsed = []

    for observation in observations:

        timestamp = parse_timestamp(
            observation["timestamp"]
        )

        minutes = (
            timestamp - first_timestamp
        ).total_seconds() / 60.0

        elapsed.append(minutes)

    return np.asarray(
        elapsed,
        dtype=np.float64,
    )


def calculate_time_aware_trend(
    observations: list[dict[str, Any]],
    sensor: str,
) -> tuple[float, float]:

    elapsed = calculate_elapsed_minutes(
        observations
    )

    values = np.asarray(
        [
            float(observation[sensor])
            for observation in observations
        ],
        dtype=np.float64,
    )

    # Recent observations receive greater weight.
    weights = np.linspace(
        0.5,
        1.0,
        len(values),
    )

    time_mean = np.average(
        elapsed,
        weights=weights,
    )

    value_mean = np.average(
        values,
        weights=weights,
    )

    centered_time = elapsed - time_mean
    centered_values = values - value_mean

    numerator = np.sum(
        weights
        * centered_time
        * centered_values
    )

    denominator = np.sum(
        weights
        * centered_time
        * centered_time
    )

    if denominator <= 1e-12:
        slope = 0.0
    else:
        slope = float(
            numerator / denominator
        )

    # The forecast starts from the latest observed value.
    latest_value = float(values[-1])

    return latest_value, slope


def apply_sensor_bounds(
    sensor: str,
    value: float,
) -> float:

    config = SENSOR_CONFIG[sensor]

    minimum = config["minimum"]
    maximum = config["maximum"]

    if minimum is not None:
        value = max(
            minimum,
            value,
        )

    if maximum is not None:
        value = min(
            maximum,
            value,
        )

    return float(value)


def predict_sensor_value(
    observations: list[dict[str, Any]],
    sensor: str,
    horizon_minutes: int,
) -> float:

    latest_value, slope = (
        calculate_time_aware_trend(
            observations,
            sensor,
        )
    )

    prediction = (
        latest_value
        + slope * horizon_minutes
    )

    return apply_sensor_bounds(
        sensor,
        prediction,
    )


def generate_multivariate_forecasts(
    *,
    dataset_id: str,
    device_id: str,
    episode_id: str,
    forecast_origin: str,
) -> dict[str, Any]:

    sequence = load_historical_sequence(
        dataset_id=dataset_id,
        device_id=device_id,
        episode_id=episode_id,
        forecast_origin=forecast_origin,
    )

    observations = sequence["observations"]

    validate_observations(
        observations
    )

    origin = parse_timestamp(
        sequence["forecast_origin"]
    )

    latest_observation_time = parse_timestamp(
        observations[-1]["timestamp"]
    )

    # Prevent pretending that stale observations
    # represent current environmental conditions.
    observation_age_minutes = (
        origin - latest_observation_time
    ).total_seconds() / 60.0

    if observation_age_minutes < 0:
        raise MultivariateForecastingError(
            "Latest observation occurs after forecast origin."
        )

    forecasts = []

    for horizon in FORECAST_HORIZONS:

        target_timestamp = (
            origin
            + timedelta(minutes=horizon)
        )

        # The regression is anchored at the last observation,
        # not necessarily at the requested forecast origin.
        effective_horizon = (
            target_timestamp - latest_observation_time
        ).total_seconds() / 60.0

        sensor_predictions = {}

        for sensor, config in SENSOR_CONFIG.items():

            predicted_value = predict_sensor_value(
                observations,
                sensor,
                effective_horizon,
            )

            sensor_predictions[sensor] = {
                "value": round(
                    predicted_value,
                    6,
                ),
                "unit": config["unit"],
            }

        forecasts.append(
            {
                "horizon_minutes": horizon,
                "target_timestamp": (
                    target_timestamp.isoformat()
                ),
                "predictions": sensor_predictions,
            }
        )

    historical_modes = [
        observation["operating_mode"]
        for observation in observations
    ]

    return {
        "dataset_id": dataset_id,
        "device_id": device_id,
        "episode_id": episode_id,
        "forecast_origin": origin.isoformat(),
        "forecast_type": sequence["forecast_type"],
        "source_origin": sequence["source_origin"],
        "model_name": (
            "M0_MULTIVARIATE_TIME_AWARE_TREND"
        ),
        "model_type": "RESEARCH_BASELINE",
        "trained_model": False,
        "sequence_length": len(observations),
        "observation_age_minutes": round(
            observation_age_minutes,
            3,
        ),
        "input_window_start": (
            sequence["window_start"]
        ),
        "input_window_end": (
            sequence["window_end"]
        ),
        "historical_operating_modes": (
            historical_modes
        ),
        "mode_conditioned_learning": False,
        "forecasts": forecasts,
        "limitations": [
            (
                "Time-aware historical trend baseline; "
                "not a trained neural model."
            ),
            (
                "Operating modes are retained but are "
                "not yet model conditioning inputs."
            ),
            (
                "Rainfall proxy counts are not "
                "calibrated rainfall measurements."
            ),
            (
                "Forecasts are sensor-value estimates, "
                "not landslide-event probabilities."
            ),
            (
                "Prediction intervals are not calibrated."
            ),
            (
                "Long-range extrapolation is not "
                "scientifically validated."
            ),
        ],
    }