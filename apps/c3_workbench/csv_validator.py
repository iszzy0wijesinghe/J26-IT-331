"""CSV validation engine for GeoNex C3 observation datasets."""

from __future__ import annotations

import csv
import math
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apps.c3_workbench.csv_schema import get_csv_schema


MAX_CSV_BYTES = 100 * 1024 * 1024
MAX_ROWS = 1_000_000
MAX_ISSUES = 100

# Initial physical/data-integrity limits.
# These are configurable validation policies, not calibrated
# sensor specifications.
SENSOR_RANGES: dict[str, tuple[float, float]] = {
    "soil_moisture_pct": (0.0, 100.0),
    "rainfall_proxy_counts": (0.0, 1_000_000.0),
    "tilt_deg": (-180.0, 180.0),
    "vibration_g": (0.0, 100.0),
    "fsr_adc": (0.0, 65535.0),
    "air_temperature_c": (-50.0, 100.0),
    "humidity_pct": (0.0, 100.0),
}


@dataclass
class ValidationIssue:
    severity: str
    code: str
    message: str
    row: int | None = None
    column: str | None = None


@dataclass
class CSVValidationResult:
    status: str = "FAILED"
    schema_version: str = ""
    filename: str = ""
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    missing_values: dict[str, int] = field(default_factory=dict)
    operating_modes: dict[str, int] = field(default_factory=dict)
    devices: int = 0
    episodes: int = 0
    timestamp_start: str | None = None
    timestamp_end: str | None = None
    issues: list[ValidationIssue] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_timestamp(value: str) -> datetime:
    text = value.strip()

    if not text:
        raise ValueError("Timestamp is empty")

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    parsed = datetime.fromisoformat(text)

    if parsed.tzinfo is None:
        raise ValueError(
            "Timestamp must include timezone information"
        )

    return parsed.astimezone(timezone.utc)


def validate_csv(path: str | Path) -> CSVValidationResult:
    """Validate a raw C3 observations CSV without training models."""

    schema = get_csv_schema()
    path = Path(path)

    result = CSVValidationResult(
        schema_version=schema.version,
        filename=path.name,
        missing_values={
            sensor: 0 for sensor in schema.sensor_columns
        },
    )

    def issue(
        severity: str,
        code: str,
        message: str,
        *,
        row: int | None = None,
        column: str | None = None,
    ) -> None:
        if severity == "ERROR":
            result.error_count += 1
        else:
            result.warning_count += 1

        if len(result.issues) < MAX_ISSUES:
            result.issues.append(
                ValidationIssue(
                    severity=severity,
                    code=code,
                    message=message,
                    row=row,
                    column=column,
                )
            )

    if not path.is_file():
        issue("ERROR", "FILE_NOT_FOUND", "CSV file does not exist")
        return result

    if path.stat().st_size > MAX_CSV_BYTES:
        issue(
            "ERROR",
            "FILE_TOO_LARGE",
            "CSV exceeds the 100 MiB upload limit",
        )
        return result

    if path.suffix.lower() != ".csv":
        issue(
            "ERROR",
            "INVALID_EXTENSION",
            "Only .csv files are supported",
        )
        return result

    devices: set[str] = set()
    episodes: set[tuple[str, str]] = set()
    seen_observations: set[tuple[str, str, datetime]] = set()
    mode_counts: Counter[str] = Counter()

    minimum_timestamp: datetime | None = None
    maximum_timestamp: datetime | None = None

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            if not reader.fieldnames:
                issue(
                    "ERROR",
                    "EMPTY_HEADER",
                    "CSV must contain a header row",
                )
                return result

            headers = [
                name.strip() if name is not None else ""
                for name in reader.fieldnames
            ]

            if len(headers) != len(set(headers)):
                issue(
                    "ERROR",
                    "DUPLICATE_COLUMNS",
                    "CSV contains duplicate column names",
                )
                return result

            missing_columns = sorted(
                set(schema.required_columns) - set(headers)
            )

            if missing_columns:
                issue(
                    "ERROR",
                    "MISSING_COLUMNS",
                    "Missing required columns: "
                    + ", ".join(missing_columns),
                )
                return result

            for row_number, row in enumerate(reader, start=2):
                if result.total_rows >= MAX_ROWS:
                    issue(
                        "ERROR",
                        "ROW_LIMIT_EXCEEDED",
                        "CSV exceeds the maximum supported row count",
                        row=row_number,
                    )
                    break

                result.total_rows += 1
                row_valid = True

                if None in row:
                    issue(
                        "ERROR",
                        "EXTRA_FIELDS",
                        "Row contains more fields than the header",
                        row=row_number,
                    )
                    row_valid = False

                device_id = (row.get("device_id") or "").strip()
                episode_id = (row.get("episode_id") or "").strip()
                mode = (row.get("operating_mode") or "").strip()

                if not device_id:
                    issue(
                        "ERROR",
                        "MISSING_DEVICE",
                        "Device ID is required",
                        row=row_number,
                        column="device_id",
                    )
                    row_valid = False

                if not episode_id:
                    issue(
                        "ERROR",
                        "MISSING_EPISODE",
                        "Episode ID is required",
                        row=row_number,
                        column="episode_id",
                    )
                    row_valid = False

                if mode not in schema.operating_modes:
                    issue(
                        "ERROR",
                        "INVALID_MODE",
                        f"Unsupported operating mode: {mode!r}",
                        row=row_number,
                        column="operating_mode",
                    )
                    row_valid = False

                timestamp: datetime | None = None

                try:
                    timestamp = _parse_timestamp(
                        row.get("timestamp") or ""
                    )
                except (ValueError, TypeError):
                    issue(
                        "ERROR",
                        "INVALID_TIMESTAMP",
                        "Timestamp must be ISO 8601 with timezone",
                        row=row_number,
                        column="timestamp",
                    )
                    row_valid = False

                for sensor in schema.sensor_columns:
                    raw_value = (row.get(sensor) or "").strip()

                    if not raw_value:
                        result.missing_values[sensor] += 1
                        continue

                    try:
                        value = float(raw_value)
                    except ValueError:
                        issue(
                            "ERROR",
                            "INVALID_SENSOR_TYPE",
                            f"{sensor} must be numeric",
                            row=row_number,
                            column=sensor,
                        )
                        row_valid = False
                        continue

                    if not math.isfinite(value):
                        issue(
                            "ERROR",
                            "NONFINITE_SENSOR",
                            f"{sensor} must be finite",
                            row=row_number,
                            column=sensor,
                        )
                        row_valid = False
                        continue

                    limits = SENSOR_RANGES.get(sensor)

                    if limits is not None:
                        lower, upper = limits

                        if not lower <= value <= upper:
                            issue(
                                "ERROR",
                                "OUT_OF_RANGE",
                                f"{sensor} must be between "
                                f"{lower} and {upper}",
                                row=row_number,
                                column=sensor,
                            )
                            row_valid = False

                if device_id and episode_id and timestamp:
                    observation_key = (
                        device_id,
                        episode_id,
                        timestamp,
                    )

                    if observation_key in seen_observations:
                        issue(
                            "ERROR",
                            "DUPLICATE_OBSERVATION",
                            "Duplicate device, episode, and timestamp",
                            row=row_number,
                        )
                        row_valid = False
                    else:
                        seen_observations.add(observation_key)

                if row_valid:
                    result.valid_rows += 1

                    devices.add(device_id)
                    episodes.add((device_id, episode_id))
                    mode_counts[mode] += 1

                    if timestamp is not None:
                        if (
                            minimum_timestamp is None
                            or timestamp < minimum_timestamp
                        ):
                            minimum_timestamp = timestamp

                        if (
                            maximum_timestamp is None
                            or timestamp > maximum_timestamp
                        ):
                            maximum_timestamp = timestamp
                else:
                    result.invalid_rows += 1

    except (OSError, UnicodeError, csv.Error) as exc:
        issue(
            "ERROR",
            "CSV_READ_ERROR",
            f"Unable to read CSV: {exc}",
        )
        return result

    if result.total_rows == 0:
        issue(
            "ERROR",
            "EMPTY_DATASET",
            "CSV contains no observation rows",
        )

    for sensor, count in result.missing_values.items():
        if count:
            issue(
                "WARNING",
                "MISSING_SENSOR_VALUES",
                f"{sensor} contains {count} missing readings",
                column=sensor,
            )

    result.devices = len(devices)
    result.episodes = len(episodes)
    result.operating_modes = dict(mode_counts)

    if minimum_timestamp is not None:
        result.timestamp_start = minimum_timestamp.isoformat()

    if maximum_timestamp is not None:
        result.timestamp_end = maximum_timestamp.isoformat()

    result.status = (
        "VALIDATED"
        if result.error_count == 0 and result.valid_rows > 0
        else "FAILED"
    )

    return result