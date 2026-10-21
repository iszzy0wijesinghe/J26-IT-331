"""
GeoNex C3 M5 feature extraction.

Transforms Golden DB-compatible observations into
multivariate, mode-conditioned temporal sequences.

Features:
- Seven sensor measurements
- Seven validity indicators
- Actual elapsed time
- Interval-known indicator
- Five operating-mode indicators

Missing measurements are represented using masks.

Sensor normalization must be fitted separately
using training data only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np

from components.c3_forecasting.models.m5_multivariate_gru import (
    INPUT_SIZE,
    OPERATING_MODES,
    SENSOR_FEATURES,
)


MODE_TO_INDEX = {
    mode: index
    for index, mode in enumerate(OPERATING_MODES)
}


def parse_utc_timestamp(value: str) -> datetime:

    timestamp = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if timestamp.tzinfo is None:
        raise ValueError(
            "Timestamp must include timezone"
        )

    return timestamp.astimezone(timezone.utc)


def extract_m5_sequence(
    observations: list[dict[str, Any]],
) -> np.ndarray:

    if not observations:
        raise ValueError(
            "Observation sequence cannot be empty"
        )

    result = np.zeros(
        (len(observations), INPUT_SIZE),
        dtype=np.float32,
    )

    previous_timestamp = None

    sensor_count = len(SENSOR_FEATURES)

    for index, observation in enumerate(observations):

        timestamp = parse_utc_timestamp(
            observation["timestamp"]
        )

        if previous_timestamp is not None:

            delta_seconds = (
                timestamp - previous_timestamp
            ).total_seconds()

            if delta_seconds <= 0:
                raise ValueError(
                    "Timestamps must be strictly increasing"
                )

            result[index, sensor_count * 2] = (
                np.log1p(delta_seconds)
            )

            result[index, sensor_count * 2 + 1] = 1.0

        previous_timestamp = timestamp

        for sensor_index, sensor in enumerate(
            SENSOR_FEATURES
        ):

            value = observation.get(sensor)

            if value is None:
                continue

            numeric_value = float(value)

            if not np.isfinite(numeric_value):
                raise ValueError(
                    f"Non-finite sensor value: {sensor}"
                )

            result[index, sensor_index] = (
                numeric_value
            )

            result[
                index,
                sensor_count + sensor_index,
            ] = 1.0

        mode = observation.get(
            "operating_mode"
        )

        if mode not in MODE_TO_INDEX:
            raise ValueError(
                f"Unsupported operating mode: {mode}"
            )

        mode_offset = sensor_count * 2 + 2

        result[
            index,
            mode_offset + MODE_TO_INDEX[mode],
        ] = 1.0

    return result