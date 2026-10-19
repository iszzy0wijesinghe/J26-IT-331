"""Mode-conditioned variable-rate features for GeoNex C3 M4."""

from __future__ import annotations

from typing import Any

import numpy as np

from components.c3_forecasting.preprocessing.gru_dataset import (
    INPUT_FEATURE_COUNT,
    extract_gru_sequence,
)

OPERATING_MODES = (
    "DEEP_SLEEP",
    "IDLE",
    "RISK",
    "WARNING",
)

MODE_COUNT = len(OPERATING_MODES)

M4_INPUT_FEATURE_COUNT = INPUT_FEATURE_COUNT + 2 + MODE_COUNT

MODE_TO_INDEX = {
    mode: index
    for index, mode in enumerate(OPERATING_MODES)
}


def extract_m4_sequence(
    sequence: dict[str, Any],
    *,
    include_time: bool = True,
    include_mode: bool = True,
) -> np.ndarray:
    """Extract mode-conditioned temporal features.

    Feature layout:
        0:14  - Standard M3 sensor values and masks
        14    - log1p(elapsed seconds)
        15    - Interval-known indicator
        16:20 - Operating-mode one-hot encoding

    Disabled feature groups are represented by zeros so all
    ablation variants use the same input dimensionality.
    """

    base = extract_gru_sequence(sequence)

    steps = sequence["steps"]

    result = np.zeros(
        (len(steps), M4_INPUT_FEATURE_COUNT),
        dtype=np.float32,
    )

    result[:, :INPUT_FEATURE_COUNT] = base

    for index, step in enumerate(steps):
        if include_time:
            quality = step.get("quality") or {}

            first_interval_unknown = quality.get(
                "first_interval_unknown"
            )

            # The first retained timestep has no known preceding interval.
            if index == 0:
                if first_interval_unknown is not True:
                    raise ValueError(
                        "First timestep must mark its interval as unknown"
                    )

            else:
                if first_interval_unknown is True:
                    raise ValueError(
                        "Only the first timestep may have an unknown interval"
                    )

                delta_t = step.get("delta_t_seconds")

                if (
                    isinstance(delta_t, bool)
                    or not isinstance(delta_t, (int, float))
                    or not np.isfinite(delta_t)
                    or delta_t < 0
                ):
                    raise ValueError(
                        "Invalid elapsed-time value"
                    )

                result[index, 14] = np.log1p(delta_t)
                result[index, 15] = 1.0

        if include_mode:
            mode = step.get("operating_mode")

            if mode not in MODE_TO_INDEX:
                raise ValueError(
                    f"Unsupported operating mode: {mode}"
                )

            result[
                index,
                INPUT_FEATURE_COUNT + 2 + MODE_TO_INDEX[mode],
            ] = 1.0

    if not np.isfinite(result).all():
        raise ValueError(
            "M4 features contain non-finite values"
        )

    return result