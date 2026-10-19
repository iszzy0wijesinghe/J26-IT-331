"""Export GeoNex C3 Golden observations as forecasting training examples.

Research safeguards:
- Only one explicitly selected Golden dataset is exported.
- Episodes remain disjoint between train and validation.
- Historical sequences never cross device or episode boundaries.
- Targets come from future stored soil-moisture observations.
- Golden CSV provenance limitations are explicitly documented.
- No held-out test split is read, created, or modified.
- Exporting does not authorize or initiate model training.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import random
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from apps.c3_workbench.golden_db import (
    get_connection,
    initialize_golden_database,
)
from apps.c3_workbench.golden_training_readiness import (
    assess_training_readiness,
)
from components.c3_forecasting.features.tabular_features import (
    FEATURE_NAMES,
    extract_tabular_features,
)
from components.c3_forecasting.preprocessing.gru_dataset import (
    extract_gru_sequence,
)
from components.c3_forecasting.preprocessing.m4_features import (
    extract_m4_sequence,
)

EXPORT_VERSION = "c3-fixed-horizon-v2"

ADAPTER_VERSION = "c3-golden-csv-adapter-v1"

HORIZONS = (15, 30, 60)

MIN_HISTORY_STEPS = 3
MAX_HISTORY_STEPS = 32

TARGET_TOLERANCE_MINUTES = 2.0

SPLIT_SEED = 20261019
TRAIN_FRACTION = 0.80

OUTPUT_ROOT = Path(
    "data/workbench/c3/training_datasets"
)


def parse_timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if timestamp.tzinfo is None:
        raise ValueError(
            "Observation timestamp must be timezone-aware."
        )

    return timestamp.astimezone(UTC)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def write_jsonl_gz(
    path: Path,
    records: list[dict[str, Any]],
) -> None:
    """Write reproducible compressed JSONL."""

    with path.open("wb") as raw:
        with gzip.GzipFile(
            fileobj=raw,
            mode="wb",
            filename="",
            mtime=0,
        ) as compressed:
            for record in records:
                encoded = json.dumps(
                    record,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )

                compressed.write(
                    (encoded + "\n").encode("utf-8")
                )


def load_golden_dataset(
    dataset_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:

    initialize_golden_database()

    with get_connection() as connection:
        dataset_row = connection.execute(
            """
            SELECT *
            FROM c3_datasets
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        ).fetchone()

        if dataset_row is None:
            raise ValueError(
                f"Dataset not found: {dataset_id}"
            )

        observation_rows = connection.execute(
            """
            SELECT
                observation_id,
                dataset_id,
                device_id,
                episode_id,
                timestamp,
                operating_mode,
                soil_moisture_pct,
                rainfall_proxy_counts,
                tilt_deg,
                vibration_g,
                fsr_adc,
                air_temperature_c,
                humidity_pct,
                created_at
            FROM c3_golden_observations
            WHERE dataset_id = ?
            ORDER BY
                episode_id,
                device_id,
                timestamp,
                observation_id
            """,
            (dataset_id,),
        ).fetchall()

    return (
        dict(dataset_row),
        [dict(row) for row in observation_rows],
    )


def group_observations(
    observations: list[dict[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:

    groups = defaultdict(list)

    for observation in observations:
        identity = (
            observation["episode_id"],
            observation["device_id"],
        )

        groups[identity].append(observation)

    for rows in groups.values():
        rows.sort(
            key=lambda row: (
                parse_timestamp(row["timestamp"]),
                row["observation_id"],
            )
        )

    return dict(groups)


def assign_episode_splits(
    groups: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ],
) -> dict[str, str]:
    """Deterministic episode-disjoint train/validation split."""

    episodes = sorted({
        episode_id
        for episode_id, _ in groups
    })

    if len(episodes) < 3:
        raise ValueError(
            "At least three episodes are required."
        )

    shuffled = episodes.copy()

    random.Random(SPLIT_SEED).shuffle(shuffled)

    validation_count = max(
        1,
        round(
            len(shuffled) * (1.0 - TRAIN_FRACTION)
        ),
    )

    validation_count = min(
        validation_count,
        len(shuffled) - 2,
    )

    validation_episodes = set(
        shuffled[:validation_count]
    )

    return {
        episode_id: (
            "validation"
            if episode_id in validation_episodes
            else "train"
        )
        for episode_id in episodes
    }


def make_step(
    observation: dict[str, Any],
    *,
    previous_time: datetime | None,
) -> dict[str, Any]:
    """Convert one Golden observation into a temporal step."""

    observed_at = parse_timestamp(
        observation["timestamp"]
    )

    delta_t_seconds = (
        0.0
        if previous_time is None
        else (
            observed_at - previous_time
        ).total_seconds()
    )

    if delta_t_seconds < 0:
        raise ValueError(
            "Historical sequence is not chronological."
        )

    features = {
        sensor: float(observation[sensor])
        for sensor in FEATURE_NAMES
    }

    # The Golden CSV schema requires finite numerical values.
    # It does not preserve original per-sensor observation masks.
    #
    # These masks mean "accepted CSV value is present",
    # NOT "physically verified, unmodified sensor measurement".
    masks = {
        sensor: True
        for sensor in FEATURE_NAMES
    }

    # Measurement ages are unknown for Golden CSV observations.
    # Do not fabricate zero-second measurement ages.
    ages_seconds = {
        sensor: None
        for sensor in FEATURE_NAMES
    }

    return {
        "time": observed_at.isoformat(),
        "delta_t_seconds": delta_t_seconds,
        "operating_mode": observation["operating_mode"],
        "features": features,
        "masks": masks,
        "ages_seconds": ages_seconds,
        "quality": {
            "source_origin": "GOLDEN_CSV",
            "observation_quality": (
                "ACCEPTED_CSV_VALUE_UNVERIFIED_PROVENANCE"
            ),
            "imputed_flags": {},
            "corrected_flags": {},
            "imputation_methods": {},
            "first_interval_unknown": (
                previous_time is None
            ),
        },
        "provenance": {
            "dataset_id": observation["dataset_id"],
            "device_id": observation["device_id"],
            "episode_id": observation["episode_id"],
            "observation_id": observation["observation_id"],
            # CSV profile assumption:
            # acquisition timestamp is the only available
            # causal timestamp. This is NOT verified receipt time.
            "received_at": observed_at.isoformat(),
            "receipt_time_basis": (
                "ASSUMED_EQUAL_TO_OBSERVATION_TIME"
            ),
            "database_created_at": (
                observation["created_at"]
            ),
        },
    }


def build_sequence(
    history: list[dict[str, Any]],
    *,
    forecast_origin: datetime,
    dataset_id: str,
    episode_id: str,
    device_id: str,
) -> dict[str, Any]:

    if not history:
        raise ValueError(
            "Historical sequence cannot be empty."
        )

    history = history[-MAX_HISTORY_STEPS:]

    steps = []
    previous_time = None

    for observation in history:
        observed_at = parse_timestamp(
            observation["timestamp"]
        )

        if observed_at > forecast_origin:
            raise ValueError(
                "Future observation detected in history."
            )

        step = make_step(
            observation,
            previous_time=previous_time,
        )

        steps.append(step)
        previous_time = observed_at

    return {
        "schema_version": "1.0",
        "zone_id": f"GOLDEN-{device_id}",
        "forecast_origin": (
            forecast_origin.isoformat()
        ),
        "feature_schema_version": (
            "c3-golden-csv-features-v1"
        ),
        "builder_version": ADAPTER_VERSION,
        "steps": steps,
        "test_run_id": episode_id,
    }


def build_examples(
    *,
    dataset_id: str,
    groups: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ],
    episode_splits: dict[str, str],
) -> dict[str, list[dict[str, Any]]]:

    result = {
        "train": [],
        "validation": [],
    }

    tolerance = timedelta(
        minutes=TARGET_TOLERANCE_MINUTES
    )

    for (
        episode_id,
        device_id,
    ), observations in sorted(groups.items()):

        split = episode_splits[episode_id]

        timestamps = [
            parse_timestamp(row["timestamp"])
            for row in observations
        ]

        if len(timestamps) != len(set(timestamps)):
            raise ValueError(
                "Duplicate observation timestamps: "
                f"{episode_id}/{device_id}"
            )

        for index, origin_row in enumerate(observations):

            if index + 1 < MIN_HISTORY_STEPS:
                continue

            forecast_origin = timestamps[index]

            history = observations[
                max(
                    0,
                    index - MAX_HISTORY_STEPS + 1,
                ):
                index + 1
            ]

            sequence = build_sequence(
                history,
                forecast_origin=forecast_origin,
                dataset_id=dataset_id,
                episode_id=episode_id,
                device_id=device_id,
            )

            for horizon in HORIZONS:

                expected_target_time = (
                    forecast_origin
                    + timedelta(minutes=horizon)
                )

                candidates = []

                for future_index in range(
                    index + 1,
                    len(observations),
                ):
                    target_time = timestamps[
                        future_index
                    ]

                    if target_time <= forecast_origin:
                        continue

                    deviation = abs(
                        target_time
                        - expected_target_time
                    )

                    if deviation <= tolerance:
                        candidates.append(
                            (
                                deviation,
                                target_time,
                                observations[future_index],
                            )
                        )

                    if target_time > (
                        expected_target_time
                        + tolerance
                    ):
                        break

                if not candidates:
                    continue

                candidates.sort(
                    key=lambda item: (
                        item[0],
                        item[1],
                        item[2]["observation_id"],
                    )
                )

                _, target_time, target_row = candidates[0]

                record = {
                    "dataset_version": EXPORT_VERSION,
                    "episode_id": episode_id,
                    "device_id": device_id,
                    "zone_id": f"GOLDEN-{device_id}",
                    "split": split,
                    "forecast_origin": (
                        forecast_origin.isoformat()
                    ),
                    "input_sequence": sequence,
                    "target": {
                        "feature": "soil_moisture_pct",
                        "value": float(
                            target_row[
                                "soil_moisture_pct"
                            ]
                        ),
                        "observed_at": (
                            target_time.isoformat()
                        ),
                        "packet_id": (
                            f"golden_obs_"
                            f"{target_row['observation_id']}"
                        ),
                        "requested_horizon_minutes": horizon,
                        "actual_horizon_seconds": (
                            target_time
                            - forecast_origin
                        ).total_seconds(),
                    },
                }

                result[split].append(record)

    return result


def validate_feature_compatibility(
    records: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Check the actual feature extractors used by M1/M3/M4."""

    checked = {}

    for split in ("train", "validation"):
        examples = records[split]

        if not examples:
            raise ValueError(
                f"No examples available for {split}."
            )

        sample = examples[0]
        sequence = sample["input_sequence"]

        tabular = extract_tabular_features(sequence)

        gru = extract_gru_sequence(sequence)

        m4 = extract_m4_sequence(
            sequence,
            include_time=True,
            include_mode=True,
        )

        checked[split] = {
            "tabular_features": len(tabular),
            "gru_shape": list(gru.shape),
            "m4_shape": list(m4.shape),
        }

    return checked


def export_golden_training_dataset(
    dataset_id: str,
    *,
    output_root: Path = OUTPUT_ROOT,
) -> dict[str, Any]:
    """Export an unapproved training candidate for inspection.

    This function does not authorize training.
    """

    readiness = assess_training_readiness(
        dataset_id
    )

    if not readiness["temporal_ready"]:
        raise ValueError(
            "Dataset failed temporal readiness: "
            + "; ".join(readiness["reasons"])
        )

    dataset, observations = load_golden_dataset(
        dataset_id
    )

    # Explicit safeguard for the known repaired test CSV.
    # A future approval system must replace this narrow check
    # with durable, per-dataset provenance metadata.
    if dataset["filename"] == "sample_c3_golden_test.csv":
        raise ValueError(
            "Repaired sample test CSV is excluded "
            "from research training exports."
        )

    groups = group_observations(observations)

    episode_splits = assign_episode_splits(
        groups
    )

    records = build_examples(
        dataset_id=dataset_id,
        groups=groups,
        episode_splits=episode_splits,
    )

    counts = {
        split: Counter(
            example["target"][
                "requested_horizon_minutes"
            ]
            for example in records[split]
        )
        for split in ("train", "validation")
    }

    for split in ("train", "validation"):
        for horizon in HORIZONS:
            if counts[split][horizon] == 0:
                raise ValueError(
                    f"No examples for {split}/{horizon}."
                )

    compatibility = validate_feature_compatibility(
        records
    )

    output_dir = output_root / dataset_id

    if output_dir.exists():
        raise FileExistsError(
            "Training export already exists: "
            f"{output_dir}. "
            "Exports are immutable; do not overwrite."
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    exported_files = {}

    for split in ("train", "validation"):
        path = output_dir / f"{split}.jsonl.gz"

        ordered = sorted(
            records[split],
            key=lambda example: (
                example["episode_id"],
                example["device_id"],
                example["forecast_origin"],
                example["target"][
                    "requested_horizon_minutes"
                ],
            ),
        )

        write_jsonl_gz(path, ordered)

        exported_files[split] = {
            "filename": path.name,
            "examples": len(ordered),
            "sha256": sha256_file(path),
        }

    manifest = {
        "export_version": EXPORT_VERSION,
        "adapter_version": ADAPTER_VERSION,
        "dataset_id": dataset_id,
        "source_filename": dataset["filename"],
        "source_file_sha256": dataset["file_hash"],
        "source_origin": "GOLDEN_CSV",
        "source_provenance_verified": False,
        "not_landslide_ground_truth": True,
        "training_objective": (
            "FUTURE_SENSOR_VALUE_REGRESSION"
        ),
        "target_feature": "soil_moisture_pct",
        "forecast_horizons_minutes": list(HORIZONS),
        "target_tolerance_minutes": (
            TARGET_TOLERANCE_MINUTES
        ),
        "minimum_history_steps": MIN_HISTORY_STEPS,
        "maximum_history_steps": MAX_HISTORY_STEPS,
        "split_policy": "EPISODE_DISJOINT",
        "split_seed": SPLIT_SEED,
        "episode_splits": episode_splits,
        "total_examples": sum(
            len(items)
            for items in records.values()
        ),
        "counts_by_split_horizon": {
            split: {
                str(horizon): counts[split][horizon]
                for horizon in HORIZONS
            }
            for split in ("train", "validation")
        },
        "files": exported_files,
        "feature_compatibility": compatibility,
        "training_approved": False,
        "limitations": [
            "Golden CSV values do not retain original "
            "per-sensor observation provenance.",
            "Receipt time is unavailable and is assumed "
            "equal to observation time for this export.",
            "Per-sensor measurement ages are unknown.",
            "Accepted CSV values are not independently "
            "verified as unmodified physical measurements.",
            "Synthetic or experimental source status "
            "requires separate provenance approval.",
            "Forecasting targets are future sensor values, "
            "not landslide-event ground truth.",
            "No held-out test split is generated.",
        ],
    }

    manifest_path = output_dir / "manifest.json"

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return {
        "dataset_id": dataset_id,
        "output_dir": str(output_dir),
        "status": "EXPORTED_UNAPPROVED",
        "total_examples": manifest["total_examples"],
        "counts_by_split_horizon": (
            manifest["counts_by_split_horizon"]
        ),
        "feature_compatibility": compatibility,
        "manifest_path": str(manifest_path),
    }