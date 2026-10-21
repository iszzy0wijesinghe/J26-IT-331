"""CSV ingestion into GeoNex C3 Golden and Training Databases.

Database ownership
------------------
Training Database:
    c3_datasets

Golden Database:
    c3_golden_observations

Temporary compatibility:
    c3_datasets in Golden is maintained only because the
    existing observation schema contains a local foreign key.

Safety:
    - Validates CSV before ingestion.
    - Detects duplicate uploads using SHA-256.
    - Does not start training.
    - Does not activate models.
    - Uses transactional observation insertion.
    - Attempts to clean up newly registered metadata on failure.

Limitations:
    - Cross-database operations are not fully atomic.
    - Concurrent uploads require additional coordination.
    - Legacy Golden metadata can be removed only after the
      Golden observation foreign-key migration.
"""

from __future__ import annotations

import csv
import hashlib
import json

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from apps.c3_workbench.csv_validator import validate_csv

from apps.c3_workbench.golden_db import (
    get_connection,
    initialize_golden_database,
    utc_now,
)

from apps.c3_workbench.training_database import (
    connect_training_db,
    initialize_training_database,
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
    """Raised when Golden CSV ingestion cannot be completed."""


def calculate_file_hash(path: Path) -> str:
    """Calculate the SHA-256 fingerprint of the uploaded CSV."""

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _find_existing_dataset(
    file_hash: str,
) -> dict[str, Any] | None:
    """Find an existing dataset in the authoritative Training DB."""

    with connect_training_db() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM c3_datasets
            WHERE file_hash = ?
            """,
            (file_hash,),
        ).fetchone()

    return dict(row) if row is not None else None


def _dataset_metadata(
    *,
    dataset_id: str,
    original_filename: str,
    file_hash: str,
    validation: Any,
) -> tuple[Any, ...]:
    """Prepare dataset metadata shared by both schemas."""

    report = validation.to_dict()
    report["filename"] = original_filename

    return (
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
    )


DATASET_INSERT_SQL = """
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
"""


def _insert_training_metadata(
    metadata: tuple[Any, ...],
) -> None:
    """Register dataset metadata in the Training Database."""

    with connect_training_db() as connection:
        connection.execute(
            DATASET_INSERT_SQL,
            metadata,
        )

        connection.commit()


def _remove_training_metadata(
    dataset_id: str,
) -> None:
    """Remove a newly registered dataset after ingestion failure."""

    with connect_training_db() as connection:
        connection.execute(
            """
            DELETE FROM c3_datasets
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        )

        connection.commit()


def _insert_golden_observations(
    *,
    path: Path,
    metadata: tuple[Any, ...],
    dataset_id: str,
) -> int:
    """Insert observations and legacy FK metadata in one Golden transaction."""

    inserted = 0

    with get_connection() as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")

            # Temporary compatibility row.
            #
            # The existing Golden observation schema still has:
            #
            # FOREIGN KEY(dataset_id)
            # REFERENCES c3_datasets(dataset_id)
            #
            # Remove this step only after a safe Golden schema migration.

            connection.execute(
                DATASET_INSERT_SQL,
                metadata,
            )

            with path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as file:
                reader = csv.DictReader(file)

                for row in reader:
                    timestamp_text = row[
                        "timestamp"
                    ].strip()

                    if timestamp_text.endswith("Z"):
                        timestamp_text = (
                            timestamp_text[:-1]
                            + "+00:00"
                        )

                    parsed_timestamp = datetime.fromisoformat(
                        timestamp_text
                    )

                    if parsed_timestamp.tzinfo is None:
                        raise GoldenIngestionError(
                            "Observation timestamp must include timezone"
                        )

                    timestamp = parsed_timestamp.astimezone(
                        UTC
                    ).isoformat()

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

                    inserted += 1

            connection.commit()

        except Exception:
            connection.rollback()
            raise

    return inserted


def ingest_golden_csv(
    path: str | Path,
    original_filename: str,
) -> dict[str, Any]:
    """Validate and ingest a Golden CSV into separated databases.

    This transitional implementation retains a Golden-local
    dataset metadata row for legacy foreign-key compatibility.

    It does not execute training or activate models.
    """

    path = Path(path)

    # -------------------------------------------------
    # Step 1 — Validate CSV.
    # -------------------------------------------------

    validation = validate_csv(path)

    if validation.status != "VALIDATED":
        raise GoldenIngestionError(
            "CSV failed Golden Data validation"
        )

    # -------------------------------------------------
    # Step 2 — Initialize both databases.
    # -------------------------------------------------

    initialize_training_database()
    initialize_golden_database()

    # -------------------------------------------------
    # Step 3 — Calculate file hash.
    # -------------------------------------------------

    file_hash = calculate_file_hash(path)

    # -------------------------------------------------
    # Step 4 — Detect duplicate uploads.
    # -------------------------------------------------

    existing = _find_existing_dataset(
        file_hash
    )

    if existing is not None:
        return {
            "dataset_id": existing["dataset_id"],
            "status": existing["pipeline_status"],
            "already_registered": True,
            "observations": existing["total_rows"],
            "quality_status": existing["quality_status"],
            "training_started": False,
        }

    # -------------------------------------------------
    # Step 5 — Generate dataset ID and metadata.
    # -------------------------------------------------

    dataset_id = (
        f"c3raw_{uuid4().hex[:16]}"
    )

    metadata = _dataset_metadata(
        dataset_id=dataset_id,
        original_filename=original_filename,
        file_hash=file_hash,
        validation=validation,
    )

    # -------------------------------------------------
    # Step 6 — Register metadata in Training DB.
    # -------------------------------------------------

    try:
        _insert_training_metadata(
            metadata
        )

    except Exception as exc:
        raise GoldenIngestionError(
            "Unable to register dataset in Training Database"
        ) from exc

    # -------------------------------------------------
    # Step 7 — Insert observations in Golden DB.
    # -------------------------------------------------

    try:
        inserted = _insert_golden_observations(
            path=path,
            metadata=metadata,
            dataset_id=dataset_id,
        )

    except Exception as exc:

        # Best-effort compensation.
        #
        # The Golden transaction is rolled back by
        # _insert_golden_observations().
        #
        # Remove newly inserted Training DB metadata.

        try:
            _remove_training_metadata(
                dataset_id
            )

        except Exception as cleanup_error:
            raise GoldenIngestionError(
                "Golden ingestion failed and Training Database "
                "cleanup also failed. Manual reconciliation is "
                f"required for dataset {dataset_id}."
            ) from cleanup_error

        raise GoldenIngestionError(
            "Golden observation ingestion failed. "
            "New Training Database metadata was rolled back."
        ) from exc

    # -------------------------------------------------
    # Step 8 — Verify observation count.
    # -------------------------------------------------

    if inserted != validation.total_rows:
        raise GoldenIngestionError(
            "Observation count mismatch after ingestion. "
            f"Dataset: {dataset_id}; "
            f"expected: {validation.total_rows}; "
            f"inserted: {inserted}. "
            "Manual reconciliation may be required."
        )

    # -------------------------------------------------
    # Step 9 — Return existing API contract.
    # -------------------------------------------------

    return {
        "dataset_id": dataset_id,
        "status": "REGISTERED",
        "already_registered": False,
        "observations": inserted,
        "quality_status": "GOLDEN",
        "training_started": False,
    }