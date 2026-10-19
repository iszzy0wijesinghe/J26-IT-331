"""GeoNex C3 V2 synthetic telemetry reader.

Preserves simulation provenance, observation masks,
missingness information, and episode boundaries.
"""

from __future__ import annotations

import gzip
import json
import math
from collections import defaultdict
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

EXPECTED_SCHEMA = "c3-synthetic-v2"

EXPECTED_FEATURES = frozenset(
    {
        "soil_moisture_pct",
        "rainfall_proxy_counts",
        "tilt_deg",
        "vibration_g",
        "fsr_adc",
        "air_temperature_c",
        "humidity_pct",
    }
)

VALID_MODES = frozenset(
    {
        "DEEP_SLEEP",
        "IDLE",
        "RISK",
        "WARNING",
        "EMERGENCY",
    }
)


class C3V2DatasetError(ValueError):
    """Raised when V2 telemetry violates the dataset contract."""


def validate_v2_record(record: dict[str, Any]) -> None:
    """Validate one synthetic telemetry record."""

    if record.get("schema_version") != EXPECTED_SCHEMA:
        raise C3V2DatasetError("Unexpected schema version")

    if record.get("source_origin") != "SIMULATED":
        raise C3V2DatasetError("Expected simulated telemetry")

    if record.get("effective_mode") not in VALID_MODES:
        raise C3V2DatasetError("Invalid operating mode")

    if record.get("split") not in {
        "train",
        "validation",
        "test",
    }:
        raise C3V2DatasetError("Invalid dataset split")

    for field in (
        "scenario_id",
        "device_id",
        "packet_id",
        "observed_at",
        "received_at",
    ):
        if not isinstance(record.get(field), str) or not record[field]:
            raise C3V2DatasetError(f"Missing or invalid {field}")

    observed_at = datetime.fromisoformat(record["observed_at"])
    received_at = datetime.fromisoformat(record["received_at"])

    if observed_at.tzinfo is None or received_at.tzinfo is None:
        raise C3V2DatasetError("Timestamps must be timezone-aware")

    if received_at < observed_at:
        raise C3V2DatasetError("Receipt precedes observation")

    features = record.get("features")
    masks = record.get("masks")
    ages = record.get("ages_seconds")
    imputed = record.get("imputed_flags")
    corrected = record.get("corrected_flags")
    methods = record.get("imputation_methods")

    mappings = {
        "features": features,
        "masks": masks,
        "ages_seconds": ages,
        "imputed_flags": imputed,
        "corrected_flags": corrected,
        "imputation_methods": methods,
    }

    for name, mapping in mappings.items():
        if not isinstance(mapping, dict):
            raise C3V2DatasetError(f"Invalid {name}")

        if set(mapping) != EXPECTED_FEATURES:
            raise C3V2DatasetError(
                f"{name} does not match expected features"
            )

    for feature in EXPECTED_FEATURES:
        value = features[feature]
        age = ages[feature]

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise C3V2DatasetError(
                f"Invalid numerical value: {feature}"
            )

        if (
            isinstance(age, bool)
            or not isinstance(age, (int, float))
            or not math.isfinite(age)
        ):
            raise C3V2DatasetError(
                f"Invalid measurement age: {feature}"
            )

        for name, flags in (
            ("masks", masks),
            ("imputed_flags", imputed),
            ("corrected_flags", corrected),
        ):
            if not isinstance(flags[feature], bool):
                raise C3V2DatasetError(
                    f"Invalid {name} flag: {feature}"
                )

        if not isinstance(methods[feature], str):
            raise C3V2DatasetError(
                f"Invalid imputation method: {feature}"
            )


def iter_v2_records(
    dataset_dir: str | Path,
) -> Iterator[dict[str, Any]]:
    """Read and validate V2 telemetry without loading it all into memory."""

    path = Path(dataset_dir) / "telemetry.jsonl.gz"

    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise C3V2DatasetError(
                    f"Invalid JSON at line {line_number}"
                ) from exc

            if not isinstance(record, dict):
                raise C3V2DatasetError(
                    f"Invalid record at line {line_number}"
                )

            try:
                validate_v2_record(record)
            except C3V2DatasetError as exc:
                raise C3V2DatasetError(
                    f"Line {line_number}: {exc}"
                ) from exc

            yield record


def group_v2_by_episode_device(
    dataset_dir: str | Path,
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Group records without mixing simulation episodes or devices."""

    groups = defaultdict(list)
    episode_splits = {}

    for record in iter_v2_records(dataset_dir):
        episode_id = record["scenario_id"]
        device_id = record["device_id"]
        split = record["split"]

        previous_split = episode_splits.setdefault(
            episode_id,
            split,
        )

        if previous_split != split:
            raise C3V2DatasetError(
                f"Episode {episode_id} appears in multiple splits"
            )

        groups[(episode_id, device_id)].append(record)

    for records in groups.values():
        records.sort(
            key=lambda record: (
                record["observed_at"],
                record["received_at"],
                record["packet_id"],
            )
        )

    return dict(groups)