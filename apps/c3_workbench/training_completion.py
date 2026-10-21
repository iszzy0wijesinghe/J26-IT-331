"""
GeoNex C3 training job completion service.

Phase 1.5.4 — Dedicated Training Database Cutover.

Responsibilities:
    - Verify approved training dataset integrity.
    - Revalidate all 18 expected model artifacts.
    - Verify registered model metadata.
    - Require exactly 18 unique model/horizon combinations.
    - Atomically transition EVALUATING -> COMPLETED.
    - Preserve existing completed jobs.
    - Never activate models automatically.

Database ownership:
    c3_training_jobs   -> Training Database
    c3_model_versions  -> Training Database

This module does not write to the Golden Database.
"""

from __future__ import annotations

import sqlite3

from datetime import UTC, datetime
from typing import Any

from apps.c3_workbench.training_database import (
    connect_training_db,
    get_training_db_path,
)

from apps.c3_workbench.model_registry import (
    collect_model_candidates,
)

from apps.c3_workbench.training_artifact_integrity import (
    verify_training_artifacts,
)


EXPECTED_MODEL_COUNT = 18


class TrainingCompletionError(ValueError):
    """Raised when a training job cannot be completed."""


def utc_now() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(UTC).isoformat()


def get_completion_connection() -> sqlite3.Connection:
    """
    Connect exclusively to the dedicated Training Database.

    Refuse to operate if the database or required migrated
    tables are missing.
    """

    database_path = get_training_db_path()

    if not database_path.is_file():
        raise TrainingCompletionError(
            "GeoNex C3 Training Database does not exist: "
            f"{database_path}"
        )

    connection = connect_training_db()
    connection.row_factory = sqlite3.Row

    required_tables = {
        "c3_training_jobs",
        "c3_model_versions",
    }

    existing_tables = {
        row["name"]
        for row in connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()
    }

    missing_tables = required_tables - existing_tables

    if missing_tables:
        connection.close()

        raise TrainingCompletionError(
            "Training Database is missing required tables: "
            + ", ".join(sorted(missing_tables))
        )

    return connection


def complete_training_job(
    job_id: str,
    dataset_id: str,
) -> dict[str, Any]:
    """
    Complete a training job only after all expected
    model candidates have been validated and registered.

    Requirements:
        1. Approved training dataset.
        2. Verified training artifacts.
        3. Exactly 18 expected model candidates.
        4. Exactly 18 registered model versions.
        5. Unique model/horizon combinations.
        6. Matching checkpoint paths.
        7. Matching validation metrics.
        8. Every model remains CANDIDATE.
        9. Training job status is EVALUATING.

    Does not activate models.
    """

    # -----------------------------------------------------
    # Step 1 — Verify dataset approval and integrity.
    # -----------------------------------------------------

    verification = verify_training_artifacts(
        dataset_id
    )

    if verification["integrity_status"] != "VERIFIED":
        raise TrainingCompletionError(
            "Training dataset integrity verification failed."
        )

    # -----------------------------------------------------
    # Step 2 — Revalidate all expected model artifacts.
    # -----------------------------------------------------

    expected_candidates = collect_model_candidates(
        job_id=job_id,
        dataset_id=dataset_id,
    )

    if len(expected_candidates) != EXPECTED_MODEL_COUNT:
        raise TrainingCompletionError(
            "Expected "
            f"{EXPECTED_MODEL_COUNT} validated candidates, "
            f"found {len(expected_candidates)}"
        )

    expected_by_key = {
        (
            candidate["model_name"],
            candidate["horizon_minutes"],
        ): candidate
        for candidate in expected_candidates
    }

    if len(expected_by_key) != EXPECTED_MODEL_COUNT:
        raise TrainingCompletionError(
            "Expected 18 unique model/horizon combinations."
        )

    expected_keys = set(
        expected_by_key.keys()
    )

    # -----------------------------------------------------
    # Step 3 — Validate registered models and job state.
    # -----------------------------------------------------

    with get_completion_connection() as connection:

        # Prevent concurrent job completion transitions.
        connection.execute(
            "BEGIN IMMEDIATE"
        )

        job = connection.execute(
            """
            SELECT
                job_id,
                dataset_id,
                status

            FROM c3_training_jobs

            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()

        if job is None:
            raise TrainingCompletionError(
                f"Unknown training job: {job_id}"
            )

        if job["dataset_id"] != dataset_id:
            raise TrainingCompletionError(
                "Training job dataset mismatch."
            )

        if job["status"] == "COMPLETED":
            raise TrainingCompletionError(
                "Training job is already completed."
            )

        if job["status"] != "EVALUATING":
            raise TrainingCompletionError(
                "Cannot complete job in status: "
                f"{job['status']}"
            )

        registered = connection.execute(
            """
            SELECT
                model_version_id,
                model_name,
                horizon_minutes,
                checkpoint_path,
                validation_mae,
                validation_rmse,
                status

            FROM c3_model_versions

            WHERE job_id = ?
              AND dataset_id = ?
            """,
            (
                job_id,
                dataset_id,
            ),
        ).fetchall()

        if len(registered) != EXPECTED_MODEL_COUNT:
            raise TrainingCompletionError(
                "Expected "
                f"{EXPECTED_MODEL_COUNT} registered models, "
                f"found {len(registered)}"
            )

        registered_keys = {
            (
                row["model_name"],
                row["horizon_minutes"],
            )
            for row in registered
        }

        if len(registered_keys) != EXPECTED_MODEL_COUNT:
            raise TrainingCompletionError(
                "Registered models contain duplicate "
                "model/horizon combinations."
            )

        if registered_keys != expected_keys:
            raise TrainingCompletionError(
                "Registered models do not match "
                "validated artifacts."
            )

        # -------------------------------------------------
        # Step 4 — Validate every registered model.
        # -------------------------------------------------

        for row in registered:

            if row["status"] != "CANDIDATE":
                raise TrainingCompletionError(
                    "All registered models must remain "
                    "CANDIDATE before completion."
                )

            key = (
                row["model_name"],
                row["horizon_minutes"],
            )

            expected = expected_by_key[key]

            if (
                row["checkpoint_path"]
                != expected["checkpoint_path"]
            ):
                raise TrainingCompletionError(
                    f"Checkpoint path mismatch: {key}"
                )

            if (
                row["validation_mae"]
                != expected["validation_mae"]
                or row["validation_rmse"]
                != expected["validation_rmse"]
            ):
                raise TrainingCompletionError(
                    f"Validation metrics mismatch: {key}"
                )

        # -------------------------------------------------
        # Step 5 — Atomically complete the training job.
        # -------------------------------------------------

        completed_at = utc_now()

        result = connection.execute(
            """
            UPDATE c3_training_jobs

            SET
                status = 'COMPLETED',
                current_stage = 'CANDIDATES_REGISTERED',
                completed_at = ?,
                error_message = NULL

            WHERE job_id = ?
              AND dataset_id = ?
              AND status = 'EVALUATING'
            """,
            (
                completed_at,
                job_id,
                dataset_id,
            ),
        )

        if result.rowcount != 1:
            raise TrainingCompletionError(
                "Training job completion transition failed."
            )

        connection.commit()

    # -----------------------------------------------------
    # Step 6 — Return completion summary.
    # -----------------------------------------------------

    return {
        "job_id": job_id,
        "dataset_id": dataset_id,
        "status": "COMPLETED",
        "current_stage": "CANDIDATES_REGISTERED",
        "registered_candidates": EXPECTED_MODEL_COUNT,
        "active_models_changed": False,
        "completed_at": completed_at,
    }