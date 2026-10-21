"""
GeoNex C3 — M5 Reference-Aligned Dataset Builder.

Development 09B: Exact-Time Reference Interpolation.

Inputs:
    Historical variable-rate sensor observations.

Targets:
    High-resolution reference timeline.

Features:
    - Episode-isolated sequence construction
    - Exact-time target interpolation
    - 15/30/60-minute forecast horizons
    - Seven sensor targets
    - Missing-target masking
    - No future reference data in model inputs
    - No cross-episode target matching

IMPORTANT:
Reference timeline values are simulated environmental
measurements, not independently validated landslide data.
"""

from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
from datetime import timedelta

import numpy as np

from components.c3_forecasting.models.m5_multivariate_gru import (
    SENSOR_FEATURES,
    FORECAST_HORIZONS,
)

from components.c3_forecasting.preprocessing.m5_features import (
    extract_m5_sequence,
    parse_utc_timestamp,
)

from components.c3_forecasting.preprocessing.m5_dataset import (
    M5TrainingSample,
    M5DatasetConfig,
)


# ============================================================
# GROUPING UTILITIES
# ============================================================

def observation_group_key(row):
    return (
        str(row["dataset_id"]),
        str(row["device_id"]),
        str(row["episode_id"]),
    )


def group_and_sort(rows):
    groups = defaultdict(list)

    for row in rows:
        groups[observation_group_key(row)].append(row)

    for key, group in groups.items():

        group.sort(
            key=lambda item: parse_utc_timestamp(
                item["timestamp"]
            )
        )

        previous_timestamp = None

        for row in group:

            timestamp = parse_utc_timestamp(
                row["timestamp"]
            )

            if (
                previous_timestamp is not None
                and timestamp <= previous_timestamp
            ):
                raise ValueError(
                    "Duplicate or non-increasing "
                    f"timestamp in group {key}"
                )

            previous_timestamp = timestamp

    return groups


# ============================================================
# REFERENCE TIMELINE INDEX
# ============================================================

class ReferenceTimelineIndex:
    """
    Index high-resolution reference observations.

    Each episode has its own sorted timeline.

    The index supports exact-time interpolation
    between adjacent reference observations.
    """

    def __init__(self, reference_rows):

        grouped = group_and_sort(reference_rows)

        self.groups = {}

        for key, rows in grouped.items():

            timestamps = [
                parse_utc_timestamp(row["timestamp"])
                for row in rows
            ]

            self.groups[key] = {
                "timestamps": timestamps,
                "rows": rows,
            }

    def find_target(
        self,
        key,
        target_timestamp,
        tolerance_seconds=5.0,
    ):
        """
        Find an exact-time target.

        If the target timestamp exactly matches a
        reference timestamp, return that record.

        Otherwise, interpolate sensor values between
        the surrounding reference observations.

        Interpolation is permitted only when both
        reference points are within the tolerance.

        No extrapolation is allowed.
        """

        group = self.groups.get(key)

        if group is None:
            return None

        timestamps = group["timestamps"]
        rows = group["rows"]

        if not timestamps:
            return None

        position = bisect_left(
            timestamps,
            target_timestamp,
        )

        # ----------------------------------------------------
        # CASE 1: EXACT TIMESTAMP MATCH
        # ----------------------------------------------------

        if (
            position < len(timestamps)
            and timestamps[position] == target_timestamp
        ):
            return rows[position].copy()

        # ----------------------------------------------------
        # CASE 2: TARGET OUTSIDE REFERENCE COVERAGE
        # ----------------------------------------------------

        if (
            position == 0
            or position >= len(timestamps)
        ):
            return None

        previous_index = position - 1
        next_index = position

        previous_time = timestamps[previous_index]
        next_time = timestamps[next_index]

        previous_gap = (
            target_timestamp - previous_time
        ).total_seconds()

        next_gap = (
            next_time - target_timestamp
        ).total_seconds()

        if (
            previous_gap < 0
            or next_gap < 0
        ):
            return None

        # ----------------------------------------------------
        # CASE 3: REJECT LARGE REFERENCE GAPS
        # ----------------------------------------------------

        if (
            previous_gap > tolerance_seconds
            or next_gap > tolerance_seconds
        ):
            return None

        total_gap = (
            next_time - previous_time
        ).total_seconds()

        if total_gap <= 0:
            return None

        # ----------------------------------------------------
        # CASE 4: LINEAR INTERPOLATION
        # ----------------------------------------------------

        weight = previous_gap / total_gap

        previous_row = rows[previous_index]
        next_row = rows[next_index]

        interpolated = {
            "dataset_id": key[0],
            "device_id": key[1],
            "episode_id": key[2],
            "timestamp": target_timestamp.isoformat(),
        }

        for sensor in SENSOR_FEATURES:

            previous_value = previous_row.get(sensor)
            next_value = next_row.get(sensor)

            if (
                previous_value is None
                or next_value is None
                or previous_value == ""
                or next_value == ""
            ):
                interpolated[sensor] = None
                continue

            previous_value = float(previous_value)
            next_value = float(next_value)

            if not (
                np.isfinite(previous_value)
                and np.isfinite(next_value)
            ):
                interpolated[sensor] = None
                continue

            interpolated[sensor] = (
                previous_value
                + weight * (
                    next_value - previous_value
                )
            )

        return interpolated


# ============================================================
# REFERENCE-ALIGNED TRAINING SAMPLE BUILDER
# ============================================================

def build_reference_aligned_samples(
    observations,
    reference_rows,
    config=None,
    target_tolerance_seconds=5.0,
):
    """
    Build M5 training samples.

    Historical model inputs come exclusively from
    variable-rate observations.

    Future prediction targets come exclusively from
    the high-resolution reference timeline.

    Forecast horizons:
        +15 minutes
        +30 minutes
        +60 minutes

    No future reference values enter model inputs.
    """

    if config is None:

        config = M5DatasetConfig(
            sequence_length=32,
            minimum_sequence_length=3,
            minimum_valid_targets=1,
            require_all_horizons=False,
        )

    observation_groups = group_and_sort(
        observations
    )

    reference_index = ReferenceTimelineIndex(
        reference_rows
    )

    samples = []

    # --------------------------------------------------------
    # PROCESS EACH EPISODE INDEPENDENTLY
    # --------------------------------------------------------

    for key, group in observation_groups.items():

        for origin_index in range(len(group)):

            # ------------------------------------------------
            # BUILD HISTORICAL INPUT WINDOW
            # ------------------------------------------------

            history_start = max(
                0,
                origin_index
                - config.sequence_length
                + 1,
            )

            history = group[
                history_start:origin_index + 1
            ]

            if (
                len(history)
                < config.minimum_sequence_length
            ):
                continue

            origin = group[origin_index]

            origin_timestamp = parse_utc_timestamp(
                origin["timestamp"]
            )

            # ------------------------------------------------
            # INITIALIZE FUTURE TARGETS
            # ------------------------------------------------

            targets = np.zeros(
                (
                    len(FORECAST_HORIZONS),
                    len(SENSOR_FEATURES),
                ),
                dtype=np.float32,
            )

            target_mask = np.zeros_like(
                targets
            )

            # ------------------------------------------------
            # ALIGN EACH FORECAST HORIZON
            # ------------------------------------------------

            for horizon_index, horizon_minutes in enumerate(
                FORECAST_HORIZONS
            ):

                target_timestamp = (
                    origin_timestamp
                    + timedelta(
                        minutes=horizon_minutes
                    )
                )

                reference_target = (
                    reference_index.find_target(
                        key,
                        target_timestamp,
                        tolerance_seconds=(
                            target_tolerance_seconds
                        ),
                    )
                )

                if reference_target is None:
                    continue

                # --------------------------------------------
                # EXTRACT SEVEN SENSOR TARGETS
                # --------------------------------------------

                for sensor_index, sensor in enumerate(
                    SENSOR_FEATURES
                ):

                    value = reference_target.get(
                        sensor
                    )

                    if value is None or value == "":
                        continue

                    numeric_value = float(value)

                    if not np.isfinite(numeric_value):
                        continue

                    targets[
                        horizon_index,
                        sensor_index,
                    ] = numeric_value

                    target_mask[
                        horizon_index,
                        sensor_index,
                    ] = 1.0

            # ------------------------------------------------
            # VALIDATE TARGET COVERAGE
            # ------------------------------------------------

            valid_targets = int(
                np.count_nonzero(target_mask)
            )

            if (
                valid_targets
                < config.minimum_valid_targets
            ):
                continue

            if config.require_all_horizons:

                horizon_coverage = (
                    target_mask.sum(axis=1) > 0
                )

                if not np.all(horizon_coverage):
                    continue

            # ------------------------------------------------
            # EXTRACT HISTORICAL FEATURES
            # ------------------------------------------------

            features = extract_m5_sequence(
                history
            )

            # ------------------------------------------------
            # CREATE TRAINING SAMPLE
            # ------------------------------------------------

            samples.append(
                M5TrainingSample(
                    features=features,
                    targets=targets,
                    target_mask=target_mask,
                    sequence_length=len(history),
                    dataset_id=key[0],
                    device_id=key[1],
                    episode_id=key[2],
                    forecast_origin=origin["timestamp"],
                )
            )

    return samples