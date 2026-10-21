"""
GeoNex C3 M5 Dataset Audit.

Usage:
    python -m scripts.data.audit_c3_m5_dataset \
        --input geonex_c3_export.csv

This script:
- Audits dataset schema
- Checks timestamps and sensor values
- Identifies operating modes
- Checks duplicate observations
- Measures multi-horizon target availability
- Produces a JSON audit report

It does not modify the input dataset.
It does not approve datasets automatically.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path

import numpy as np

from components.c3_forecasting.models.m5_multivariate_gru import (
    FORECAST_HORIZONS,
    OPERATING_MODES,
    SENSOR_FEATURES,
)

from components.c3_forecasting.preprocessing.m5_features import (
    parse_utc_timestamp,
)


REQUIRED_COLUMNS = {
    "device_id",
    "episode_id",
    "timestamp",
    "operating_mode",
    *SENSOR_FEATURES,
}


def read_csv(path: Path):

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError("CSV has no header")

        columns = set(reader.fieldnames)

        missing = REQUIRED_COLUMNS - columns

        if missing:
            raise ValueError(
                f"Missing required columns: {sorted(missing)}"
            )

        return list(reader)


def audit_dataset(rows, tolerance_minutes=3.0):

    mode_counts = Counter()
    missing_values = Counter()
    invalid_values = Counter()

    groups = defaultdict(list)

    duplicate_count = 0
    invalid_timestamps = 0
    unknown_modes = Counter()

    seen = set()

    for row in rows:

        mode = row["operating_mode"]

        mode_counts[mode] += 1

        if mode not in OPERATING_MODES:
            unknown_modes[mode] += 1

        try:
            timestamp = parse_utc_timestamp(
                row["timestamp"]
            )
        except (ValueError, TypeError):
            invalid_timestamps += 1
            continue

        key = (
            row.get("dataset_id", ""),
            row["device_id"],
            row["episode_id"],
        )

        observation_key = (
            key,
            timestamp.isoformat(),
        )

        if observation_key in seen:
            duplicate_count += 1

        seen.add(observation_key)

        groups[key].append(
            (timestamp, row)
        )

        for sensor in SENSOR_FEATURES:

            value = row.get(sensor)

            if value is None or str(value).strip() == "":
                missing_values[sensor] += 1
                continue

            try:
                numeric = float(value)
            except (TypeError, ValueError):
                invalid_values[sensor] += 1
                continue

            if not np.isfinite(numeric):
                invalid_values[sensor] += 1

    horizon_counts = {
        str(horizon): 0
        for horizon in FORECAST_HORIZONS
    }

    horizon_total_origins = 0

    tolerance = timedelta(
        minutes=tolerance_minutes
    )

    for group in groups.values():

        group.sort(
            key=lambda item: item[0]
        )

        timestamps = [
            item[0]
            for item in group
        ]

        for index, origin in enumerate(timestamps):

            horizon_total_origins += 1

            future_times = timestamps[index + 1:]

            for horizon in FORECAST_HORIZONS:

                target_time = origin + timedelta(
                    minutes=horizon
                )

                matched = any(
                    abs(timestamp - target_time) <= tolerance
                    for timestamp in future_times
                )

                if matched:
                    horizon_counts[str(horizon)] += 1

    horizon_coverage = {}

    for horizon, count in horizon_counts.items():

        percentage = (
            100.0 * count / horizon_total_origins
            if horizon_total_origins
            else 0.0
        )

        horizon_coverage[horizon] = {
            "matched_origins": count,
            "coverage_pct": round(percentage, 2),
        }

    synthetic_episode_count = sum(
        1
        for key in groups
        if "SYN" in key[2].upper()
    )

    issues = []

    if duplicate_count:
        issues.append(
            "Duplicate device/episode timestamps detected."
        )

    if invalid_timestamps:
        issues.append(
            "Invalid timestamps detected."
        )

    if unknown_modes:
        issues.append(
            "Unknown operating modes detected."
        )

    if missing_values:
        issues.append(
            "Missing sensor measurements detected."
        )

    if invalid_values:
        issues.append(
            "Invalid sensor measurements detected."
        )

    if "EMERGENCY" not in mode_counts:
        issues.append(
            "No EMERGENCY-mode observations."
        )

    if synthetic_episode_count:
        issues.append(
            "Synthetic episode identifiers detected."
        )

    return {
        "total_rows": len(rows),
        "group_count": len(groups),
        "synthetic_episode_groups": synthetic_episode_count,
        "mode_distribution": dict(mode_counts),
        "unknown_modes": dict(unknown_modes),
        "duplicate_observations": duplicate_count,
        "invalid_timestamps": invalid_timestamps,
        "missing_sensor_values": dict(missing_values),
        "invalid_sensor_values": dict(invalid_values),
        "horizon_target_coverage": horizon_coverage,
        "issues": issues,
        "training_approved": False,
        "approval_note": (
            "Manual provenance and research-quality "
            "review required before final training."
        ),
    }


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
    )

    parser.add_argument(
        "--output",
        default="artifacts/c3/m5_dataset_audit.json",
    )

    parser.add_argument(
        "--tolerance-minutes",
        type=float,
        default=3.0,
    )

    args = parser.parse_args()

    if args.tolerance_minutes < 0:
        parser.error(
            "--tolerance-minutes must be nonnegative"
        )

    input_path = Path(args.input)

    rows = read_csv(input_path)

    report = audit_dataset(
        rows,
        tolerance_minutes=args.tolerance_minutes,
    )

    report["input_file"] = str(input_path)

    output_path = Path(args.output)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            report,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            report,
            indent=2,
        )
    )

    print(
        f"\nAudit saved to: {output_path}"
    )


if __name__ == "__main__":
    main()