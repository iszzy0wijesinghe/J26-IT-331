"""
Persistent training queue for GeoNex C3.

Database architecture
---------------------
Training Database:
    - c3_datasets
    - c3_training_jobs
    - c3_training_events

Golden Database:
    - Operational sensor observations
    - Operational forecasts
    - Operational alerts

All training queue operations are performed against the
dedicated Training Database.

Existing function signatures and response formats are
preserved for compatibility with the current backend.
"""

from __future__ import annotations

import sqlite3
import uuid

from datetime import UTC, datetime
from typing import Any

from apps.c3_workbench.training_database import (
    connect_training_db,
    get_training_db_path,
)


TRAINING_STATUSES = {
    "QUEUED",
    "PREPARING",
    "TRAINING",
    "EVALUATING",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
}

TERMINAL_STATUSES = {
    "COMPLETED",
    "FAILED",
    "CANCELLED",
}

ACTIVE_STATUSES = {
    "QUEUED",
    "PREPARING",
    "TRAINING",
    "EVALUATING",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def generate_job_id() -> str:
    return f"c3train_{uuid.uuid4().hex[:16]}"


def row_to_dict(
    row: sqlite3.Row | None,
) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def get_training_connection() -> sqlite3.Connection:
    """
    Open the dedicated Training Database.

    Do not initialize the database here.

    The database must already contain the migrated
    c3_* training tables before this service is used.

    This prevents an accidentally empty database from
    silently replacing the migrated training store.
    """

    database_path = get_training_db_path()

    if not database_path.is_file():
        raise RuntimeError(
            "GeoNex C3 Training Database does not exist: "
            f"{database_path}. "
            "Complete the training store migration first."
        )

    connection = connect_training_db()

    connection.row_factory = sqlite3.Row

    required_tables = {
        "c3_datasets",
        "c3_training_jobs",
        "c3_training_events",
    }

    existing_tables = {
        row[0]
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

        raise RuntimeError(
            "Training Database is missing required tables: "
            + ", ".join(sorted(missing_tables))
        )

    return connection


def append_training_event(
    connection: sqlite3.Connection,
    *,
    job_id: str,
    level: str,
    stage: str,
    message: str,
) -> None:
    """
    Append a training event using an existing transaction.

    The caller is responsible for committing or rolling
    back the transaction.
    """

    connection.execute(
        """
        INSERT INTO c3_training_events (
            job_id,
            timestamp,
            level,
            stage,
            message
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            job_id,
            utc_now(),
            level,
            stage,
            message,
        ),
    )


def enqueue_training_job(
    dataset_id: str,
) -> dict[str, Any]:
    """
    Create a persistent training job for a registered dataset.

    Readiness and training approval must be verified by
    the calling workflow before this function is invoked.

    Existing active jobs are returned instead of creating
    duplicate training jobs.
    """

    if not dataset_id or not dataset_id.strip():
        raise ValueError(
            "dataset_id must not be empty."
        )

    with get_training_connection() as connection:

        # Acquire the write lock before checking for an
        # existing active job to avoid duplicate enqueue
        # operations from concurrent requests.
        connection.execute("BEGIN IMMEDIATE")

        dataset = connection.execute(
            """
            SELECT dataset_id
            FROM c3_datasets
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        ).fetchone()

        if dataset is None:
            raise ValueError(
                "Training dataset does not exist: "
                f"{dataset_id}"
            )

        existing = connection.execute(
            """
            SELECT *
            FROM c3_training_jobs
            WHERE dataset_id = ?
              AND status IN (
                  'QUEUED',
                  'PREPARING',
                  'TRAINING',
                  'EVALUATING'
              )
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (dataset_id,),
        ).fetchone()

        if existing is not None:
            return dict(existing)

        job_id = generate_job_id()

        now = utc_now()

        connection.execute(
            """
            INSERT INTO c3_training_jobs (
                job_id,
                dataset_id,
                status,
                current_stage,
                created_at,
                started_at,
                completed_at,
                error_message
            )
            VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL)
            """,
            (
                job_id,
                dataset_id,
                "QUEUED",
                "WAITING_FOR_WORKER",
                now,
            ),
        )

        append_training_event(
            connection,
            job_id=job_id,
            level="INFO",
            stage="QUEUE",
            message=(
                "Training job created and queued "
                "for background processing."
            ),
        )

        job = connection.execute(
            """
            SELECT *
            FROM c3_training_jobs
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()

        return dict(job)


def list_training_jobs(
    *,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Return training jobs from the Training Database.

    Response format remains compatible with existing APIs.
    """

    limit = max(1, min(int(limit), 1000))

    with get_training_connection() as connection:

        rows = connection.execute(
            """
            SELECT *
            FROM c3_training_jobs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        total = connection.execute(
            """
            SELECT COUNT(*)
            FROM c3_training_jobs
            """
        ).fetchone()[0]

    return {
        "jobs": [
            dict(row)
            for row in rows
        ],
        "total": total,
    }


def get_training_job(
    job_id: str,
) -> dict[str, Any] | None:
    """
    Retrieve a training job and its event history.
    """

    with get_training_connection() as connection:

        job = connection.execute(
            """
            SELECT *
            FROM c3_training_jobs
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()

        if job is None:
            return None

        events = connection.execute(
            """
            SELECT *
            FROM c3_training_events
            WHERE job_id = ?
            ORDER BY event_id ASC
            """,
            (job_id,),
        ).fetchall()

    return {
        **dict(job),
        "events": [
            dict(event)
            for event in events
        ],
    }


def claim_next_training_job() -> dict[str, Any] | None:
    """
    Atomically claim the oldest queued training job.

    IMPORTANT:
    This function only performs queue claiming.

    It does not verify training approval or artifact
    integrity. Callers must enforce those checks
    before executing model training.
    """

    with get_training_connection() as connection:

        connection.execute("BEGIN IMMEDIATE")

        job = connection.execute(
            """
            SELECT *
            FROM c3_training_jobs
            WHERE status = 'QUEUED'
            ORDER BY created_at ASC
            LIMIT 1
            """
        ).fetchone()

        if job is None:
            return None

        job_id = job["job_id"]

        cursor = connection.execute(
            """
            UPDATE c3_training_jobs
            SET
                status = 'PREPARING',
                current_stage = 'DATA_PREPARATION',
                started_at = ?,
                error_message = NULL
            WHERE job_id = ?
              AND status = 'QUEUED'
            """,
            (
                utc_now(),
                job_id,
            ),
        )

        if cursor.rowcount != 1:
            return None

        append_training_event(
            connection,
            job_id=job_id,
            level="INFO",
            stage="PREPARING",
            message=(
                "Background worker claimed training job."
            ),
        )

        updated = connection.execute(
            """
            SELECT *
            FROM c3_training_jobs
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()

        return dict(updated)


def claim_training_job(
    job_id: str,
) -> dict[str, Any] | None:
    """
    Atomically claim a specific queued training job.

    The caller must verify:
        1. Training approval.
        2. Dataset readiness.
        3. Artifact integrity.

    This function does not independently authorize
    model training.
    """

    with get_training_connection() as connection:

        connection.execute("BEGIN IMMEDIATE")

        job = connection.execute(
            """
            SELECT *
            FROM c3_training_jobs
            WHERE job_id = ?
              AND status = 'QUEUED'
            """,
            (job_id,),
        ).fetchone()

        if job is None:
            return None

        cursor = connection.execute(
            """
            UPDATE c3_training_jobs
            SET
                status = 'PREPARING',
                current_stage = 'DATA_PREPARATION',
                started_at = ?,
                error_message = NULL
            WHERE job_id = ?
              AND status = 'QUEUED'
            """,
            (
                utc_now(),
                job_id,
            ),
        )

        if cursor.rowcount != 1:
            return None

        append_training_event(
            connection,
            job_id=job_id,
            level="INFO",
            stage="PREPARING",
            message=(
                "Background worker claimed approved "
                "training job."
            ),
        )

        updated = connection.execute(
            """
            SELECT *
            FROM c3_training_jobs
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()

        return dict(updated)


def update_training_job(
    job_id: str,
    *,
    status: str,
    stage: str,
    message: str,
    level: str = "INFO",
    error_message: str | None = None,
) -> dict[str, Any]:
    """
    Persist a training status transition and event.

    Both updates are performed within the same
    database transaction.
    """

    if status not in TRAINING_STATUSES:
        raise ValueError(
            f"Unsupported training status: {status}"
        )

    with get_training_connection() as connection:

        connection.execute("BEGIN IMMEDIATE")

        existing = connection.execute(
            """
            SELECT status
            FROM c3_training_jobs
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()

        if existing is None:
            raise ValueError(
                f"Training job not found: {job_id}"
            )

        completed_at = (
            utc_now()
            if status in TERMINAL_STATUSES
            else None
        )

        connection.execute(
            """
            UPDATE c3_training_jobs
            SET
                status = ?,
                current_stage = ?,
                completed_at = ?,
                error_message = ?
            WHERE job_id = ?
            """,
            (
                status,
                stage,
                completed_at,
                error_message,
                job_id,
            ),
        )

        append_training_event(
            connection,
            job_id=job_id,
            level=level,
            stage=stage,
            message=message,
        )

        updated = connection.execute(
            """
            SELECT *
            FROM c3_training_jobs
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()

        return dict(updated)