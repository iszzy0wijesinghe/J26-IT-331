"""Atomic CSV ingestion into the GeoNex C3 Golden Database."""

from __future__ import annotations

import csv
import hashlib
import json

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from apps.c3_workbench.csv_validator import validate_csv
from apps.c3_workbench.golden_db import (
    get_connection,
    initialize_golden_database,
    utc_now,
)


SENSOR_COLUMNS = (
    "soil_moisture_pct",
    "rainfall_proxy_counts",
    "tilt_deg",
    "vibration_g",
    "fsr_adc",
    "air_temperature_c",
    "humidity_pct",
)


class GoldenIngestionError(ValueError):
    pass


def calculate_file_hash(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def ingest_golden_csv(
    path: str | Path,
    original_filename: str,
) -> dict[str, Any]:
    """Validate and atomically insert an entire Golden CSV dataset."""

    path = Path(path)

    validation = validate_csv(path)

    if validation.status != "VALIDATED":
        raise GoldenIngestionError(
            "CSV failed Golden Data validation"
        )

    initialize_golden_database()

    file_hash = calculate_file_hash(path)

    with get_connection() as connection:
        existing = connection.execute(
            """
            SELECT *
            FROM c3_datasets
            WHERE file_hash = ?
            """,
            (file_hash,),
        ).fetchone()

        if existing is not None:
            return {
                "dataset_id": existing["dataset_id"],
                "status": existing["pipeline_status"],
                "already_registered": True,
                "observations": existing["total_rows"],
            }

    dataset_id = f"c3raw_{uuid4().hex[:16]}"

    report = validation.to_dict()
    report["filename"] = original_filename

    # All observations and their dataset metadata are committed
    # together. An exception rolls back the entire transaction.
    with get_connection() as connection:

        connection.execute(
            """
            INSERT INTO c3_datasets (
                dataset_id,
                filename,
                file_hash,
                uploaded_at,
                total_rows,
                device_count,
                episode_count,
                quality_status,
                pipeline_status,
                validation_report,
                source_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                original_filename,
                file_hash,
                utc_now(),
                validation.total_rows,
                validation.devices,
                validation.episodes,
                "GOLDEN",
                "REGISTERED",
                json.dumps(report),
                "CSV",
            ),
        )

        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:
                timestamp_text = row["timestamp"].strip()

                if timestamp_text.endswith("Z"):
                    timestamp_text = (
                        timestamp_text[:-1] + "+00:00"
                    )

                timestamp = datetime.fromisoformat(
                    timestamp_text
                ).astimezone(timezone.utc).isoformat()

                connection.execute(
                    """
                    INSERT INTO c3_golden_observations (
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
                    )
                    VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?
                    )
                    """,
                    (
                        dataset_id,
                        row["device_id"].strip(),
                        row["episode_id"].strip(),
                        timestamp,
                        row["operating_mode"].strip(),
                        *(
                            float(row[column])
                            for column in SENSOR_COLUMNS
                        ),
                        utc_now(),
                    ),
                )

    return {
        "dataset_id": dataset_id,
        "status": "REGISTERED",
        "already_registered": False,
        "observations": validation.total_rows,
        "quality_status": "GOLDEN",
        "training_started": False,
    }