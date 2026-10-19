"""Temporal training-readiness analysis for GeoNex C3 Golden datasets."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from apps.c3_workbench.golden_db import (
    get_connection,
    initialize_golden_database,
)

HORIZONS_MINUTES = (15, 30, 60)

TARGET_TOLERANCE_MINUTES = 2.0

MIN_HISTORY_STEPS = 3

MAX_HISTORY_STEPS = 32

MIN_TRAIN_EPISODES = 2

MIN_VALIDATION_EPISODES = 1


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp as a UTC datetime."""

    timestamp = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if timestamp.tzinfo is None:
        raise ValueError(
            "Golden observation timestamp must include timezone"
        )

    return timestamp.astimezone(UTC)


def load_dataset_observations(
    dataset_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load only observations belonging to the selected dataset."""

    initialize_golden_database()

    with get_connection() as connection:
        dataset = connection.execute(
            """
            SELECT *
            FROM c3_datasets
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        ).fetchone()

        if dataset is None:
            raise ValueError(
                f"Golden dataset not found: {dataset_id}"
            )

        observations = connection.execute(
            """
            SELECT
                observation_id,
                dataset_id,
                device_id,
                episode_id,
                timestamp,
                operating_mode,
                soil_moisture_pct
            FROM c3_golden_observations
            WHERE dataset_id = ?
            ORDER BY device_id, episode_id, timestamp
            """,
            (dataset_id,),
        ).fetchall()

    return (
        dict(dataset),
        [dict(row) for row in observations],
    )


def assess_training_readiness(
    dataset_id: str,
) -> dict[str, Any]:
    """Assess whether Golden observations support fixed-horizon training."""

    dataset, observations = load_dataset_observations(
        dataset_id
    )

    groups = defaultdict(list)

    for observation in observations:
        key = (
            observation["device_id"],
            observation["episode_id"],
        )

        groups[key].append(observation)

    horizon_counts = Counter()

    episode_reports = []

    duplicate_timestamp_count = 0

    tolerance = timedelta(
        minutes=TARGET_TOLERANCE_MINUTES
    )

    for (device_id, episode_id), rows in sorted(groups.items()):

        parsed_rows = [
            (
                parse_timestamp(row["timestamp"]),
                row,
            )
            for row in rows
        ]

        parsed_rows.sort(
            key=lambda item: (
                item[0],
                item[1]["observation_id"],
            )
        )

        timestamps = [
            timestamp
            for timestamp, _ in parsed_rows
        ]

        duplicates = len(timestamps) - len(
            set(timestamps)
        )

        duplicate_timestamp_count += duplicates

        local_counts = Counter()

        for index, (origin_time, origin_row) in enumerate(
            parsed_rows
        ):

            history = parsed_rows[
                max(0, index - MAX_HISTORY_STEPS + 1):
                index + 1
            ]

            if len(history) < MIN_HISTORY_STEPS:
                continue

            for horizon in HORIZONS_MINUTES:

                expected_target = origin_time + timedelta(
                    minutes=horizon
                )

                candidates = [
                    (
                        abs(target_time - expected_target),
                        target_time,
                        target_row,
                    )
                    for target_time, target_row in parsed_rows[
                        index + 1:
                    ]
                    if (
                        target_time > origin_time
                        and abs(
                            target_time - expected_target
                        ) <= tolerance
                    )
                ]

                if not candidates:
                    continue

                candidates.sort(
                    key=lambda item: (
                        item[0],
                        item[1],
                        item[2]["observation_id"],
                    )
                )

                local_counts[horizon] += 1
                horizon_counts[horizon] += 1

        intervals = [
            (
                timestamps[index] -
                timestamps[index - 1]
            ).total_seconds()
            for index in range(1, len(timestamps))
        ]

        positive_intervals = [
            interval
            for interval in intervals
            if interval > 0
        ]

        typical_interval_seconds = (
            Counter(positive_intervals).most_common(1)[0][0]
            if positive_intervals
            else None
        )

        episode_reports.append(
            {
                "device_id": device_id,
                "episode_id": episode_id,
                "observations": len(rows),
                "duplicate_timestamps": duplicates,
                "first_observation": (
                    timestamps[0].isoformat()
                    if timestamps
                    else None
                ),
                "last_observation": (
                    timestamps[-1].isoformat()
                    if timestamps
                    else None
                ),
                "typical_interval_seconds": (
                    typical_interval_seconds
                ),
                "available_targets": {
                    str(horizon): local_counts[horizon]
                    for horizon in HORIZONS_MINUTES
                },
            }
        )

    eligible_episodes = sum(
        1
        for report in episode_reports
        if all(
            report["available_targets"][str(horizon)] > 0
            for horizon in HORIZONS_MINUTES
        )
    )

    reasons = []

    if not observations:
        reasons.append(
            "Dataset contains no Golden observations."
        )

    if duplicate_timestamp_count:
        reasons.append(
            "Duplicate timestamps exist within device episodes."
        )

    if eligible_episodes < (
        MIN_TRAIN_EPISODES +
        MIN_VALIDATION_EPISODES
    ):
        reasons.append(
            "Insufficient eligible episodes for episode-disjoint "
            "training and validation."
        )

    for horizon in HORIZONS_MINUTES:
        if horizon_counts[horizon] == 0:
            reasons.append(
                f"No valid {horizon}-minute forecasting targets."
            )

    temporal_ready = len(reasons) == 0

    return {
        "dataset_id": dataset_id,
        "filename": dataset["filename"],
        "quality_status": dataset["quality_status"],
        "pipeline_status": dataset["pipeline_status"],
        "temporal_ready": temporal_ready,
        "training_approved": False,
        "training_approval_reason": (
            "Temporal readiness does not establish sensor provenance "
            "or research approval."
        ),
        "observations": len(observations),
        "episodes": len(episode_reports),
        "eligible_episodes": eligible_episodes,
        "duplicate_timestamps": duplicate_timestamp_count,
        "configuration": {
            "horizons_minutes": list(HORIZONS_MINUTES),
            "target_tolerance_minutes": (
                TARGET_TOLERANCE_MINUTES
            ),
            "minimum_history_steps": MIN_HISTORY_STEPS,
            "maximum_history_steps": MAX_HISTORY_STEPS,
            "minimum_train_episodes": MIN_TRAIN_EPISODES,
            "minimum_validation_episodes": (
                MIN_VALIDATION_EPISODES
            ),
        },
        "available_targets": {
            str(horizon): horizon_counts[horizon]
            for horizon in HORIZONS_MINUTES
        },
        "reasons": reasons,
        "episode_reports": episode_reports,
    }