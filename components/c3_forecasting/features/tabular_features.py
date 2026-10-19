"""Causal fixed-length features for GeoNex C3 tabular baselines."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

FEATURE_NAMES = (
    "soil_moisture_pct",
    "rainfall_proxy_counts",
    "tilt_deg",
    "vibration_g",
    "fsr_adc",
    "air_temperature_c",
    "humidity_pct",
)

OPERATING_MODES = (
    "DEEP_SLEEP",
    "IDLE",
    "RISK",
    "WARNING",
    "EMERGENCY",
)


def _parse_time(value: str) -> datetime:
    """Parse an ISO-8601 timestamp."""

    timestamp = datetime.fromisoformat(value)

    if timestamp.tzinfo is None:
        raise ValueError("Timestamps must be timezone-aware")

    return timestamp


def _valid_measurement(
    step: dict[str, Any],
    feature: str,
) -> bool:
    """Check whether a sensor value is genuinely observed."""

    if not step["masks"].get(feature, False):
        return False

    quality = step.get("quality", {})

    if quality.get("imputed_flags", {}).get(feature, False):
        return False

    if quality.get("corrected_flags", {}).get(feature, False):
        return False

    value = step["features"].get(feature)

    if value is None:
        return False

    return isinstance(value, (int, float)) and math.isfinite(value)


def extract_tabular_features(
    sequence: dict[str, Any],
) -> dict[str, float]:
    """Extract fixed-length features from an as-of-safe C3 sequence.

    All features use only observations available at forecast_origin.
    Missing sensor histories are represented with zero-filled
    statistics plus explicit availability indicators.
    """

    forecast_origin = _parse_time(sequence["forecast_origin"])

    eligible_steps = []

    for step in sequence["steps"]:
        observed_at = _parse_time(step["time"])
        received_at = _parse_time(
            step["provenance"]["received_at"]
        )

        if observed_at > forecast_origin:
            continue

        if received_at > forecast_origin:
            continue

        eligible_steps.append(
            (observed_at, received_at, step)
        )

    eligible_steps.sort(key=lambda item: (item[0], item[1]))

    if not eligible_steps:
        raise ValueError("No eligible historical steps")

    first_time = eligible_steps[0][0]
    last_time = eligible_steps[-1][0]

    duration_seconds = max(
        0.0,
        (last_time - first_time).total_seconds(),
    )

    features = {
        "history_step_count": float(len(eligible_steps)),
        "history_duration_minutes": duration_seconds / 60.0,
        "last_step_age_seconds": (
            forecast_origin - last_time
        ).total_seconds(),
    }

    if len(eligible_steps) >= 2:
        previous_time = eligible_steps[-2][0]

        features["last_interval_seconds"] = (
            last_time - previous_time
        ).total_seconds()
    else:
        features["last_interval_seconds"] = 0.0

    latest_mode = eligible_steps[-1][2]["operating_mode"]

    for mode in OPERATING_MODES:
        features[f"mode_{mode}"] = float(latest_mode == mode)

    for sensor in FEATURE_NAMES:
        valid = []

        for observed_at, _, step in eligible_steps:
            if _valid_measurement(step, sensor):
                valid.append(
                    (
                        observed_at,
                        float(step["features"][sensor]),
                    )
                )

        prefix = sensor

        features[f"{prefix}_valid_count"] = float(len(valid))
        features[f"{prefix}_valid_fraction"] = (
            len(valid) / len(eligible_steps)
        )
        features[f"{prefix}_available"] = float(bool(valid))

        if not valid:
            features[f"{prefix}_latest"] = 0.0
            features[f"{prefix}_mean"] = 0.0
            features[f"{prefix}_min"] = 0.0
            features[f"{prefix}_max"] = 0.0
            features[f"{prefix}_change"] = 0.0
            features[f"{prefix}_trend_per_minute"] = 0.0
            features[f"{prefix}_age_seconds"] = 0.0
            continue

        values = [value for _, value in valid]

        first_observed_at, first_value = valid[0]
        latest_observed_at, latest_value = valid[-1]

        elapsed_minutes = (
            latest_observed_at - first_observed_at
        ).total_seconds() / 60.0

        change = latest_value - first_value

        trend = (
            change / elapsed_minutes
            if elapsed_minutes > 0
            else 0.0
        )

        features[f"{prefix}_latest"] = latest_value
        features[f"{prefix}_mean"] = sum(values) / len(values)
        features[f"{prefix}_min"] = min(values)
        features[f"{prefix}_max"] = max(values)
        features[f"{prefix}_change"] = change
        features[f"{prefix}_trend_per_minute"] = trend
        features[f"{prefix}_age_seconds"] = (
            forecast_origin - latest_observed_at
        ).total_seconds()

    return features