"""Persistent training queue for GeoNex C3."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from apps.c3_workbench.golden_db import (
    get_connection,
    initialize_golden_database,
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


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def generate_job_id() -> str:
    return f"c3train_{uuid.uuid4().hex[:16]}"


def row_to_dict(
    row: sqlite3.Row | None,
) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def append_training_event(
    connection: sqlite3.Connection,
    *,
    job_id: str,
    level: str,
    stage: str,
    message: str,
) -> None:
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

    Readiness checks must be completed before this function
    is called by the automatic upload workflow.
    """

    initialize_golden_database()

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

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
                f"Golden dataset does not exist: {dataset_id}"
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
    initialize_golden_database()

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

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
        "jobs": [dict(row) for row in rows],
        "total": total,
    }


def get_training_job(
    job_id: str,
) -> dict[str, Any] | None:
    initialize_golden_database()

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

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
        "events": [dict(event) for event in events],
    }


def claim_next_training_job() -> dict[str, Any] | None:
    """
    Atomically claim one queued job.

    Only the background worker should call this function.
    """

    initialize_golden_database()

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

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

        connection.execute(
            """
            UPDATE c3_training_jobs
            SET status = 'PREPARING',
                current_stage = 'DATA_PREPARATION',
                started_at = ?
            WHERE job_id = ?
              AND status = 'QUEUED'
            """,
            (
                utc_now(),
                job_id,
            ),
        )

        append_training_event(
            connection,
            job_id=job_id,
            level="INFO",
            stage="PREPARING",
            message="Background worker claimed training job.",
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
    Atomically claim a specific queued job.

    The caller must verify training approval and
    artifact integrity before invoking this function.

    This function does not itself authorize training.
    """

    initialize_golden_database()

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

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
    """Persist a training status transition and event."""

    if status not in TRAINING_STATUSES:
        raise ValueError(
            f"Unsupported training status: {status}"
        )

    initialize_golden_database()

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

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
            if status in {
                "COMPLETED",
                "FAILED",
                "CANCELLED",
            }
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
