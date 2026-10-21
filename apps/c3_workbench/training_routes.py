"""
GeoNex C3 Training Job API.

Phase 1.4.5 — Dedicated Training Database Integration.

Responsibilities:
    - List training jobs.
    - Retrieve training job details.
    - Verify approved training artifacts.
    - Create or reuse queued training jobs.
    - Prevent duplicate active jobs.
    - Preserve existing API response structures.

Database ownership:
    c3_training_jobs -> Dedicated Training Database

IMPORTANT:
    Automatic worker execution is intentionally disabled
    during Phase 1 database migration.

    Creating a job does not start model training.
"""

from __future__ import annotations

import sqlite3

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from apps.c3_workbench.training_database import (
    connect_training_db,
)

from apps.c3_workbench.training_artifact_integrity import (
    verify_training_artifacts,
)

from apps.c3_workbench.training_queue import (
    enqueue_training_job,
    get_training_job,
    list_training_jobs,
)


router = APIRouter(
    prefix="/training",
    tags=["C3 Training"],
)


ACTIVE_JOB_STATUSES = (
    "QUEUED",
    "PREPARING",
    "TRAINING",
    "EVALUATING",
)


def find_active_training_job(
    dataset_id: str,
) -> dict | None:
    """
    Find an existing active job for the dataset.

    Unlike a limited job listing, this searches all
    matching records in the dedicated Training Database.
    """

    with connect_training_db() as connection:

        connection.row_factory = sqlite3.Row

        row = connection.execute(
            """
            SELECT job_id
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

    if row is None:
        return None

    return get_training_job(
        row["job_id"]
    )


@router.get("/jobs")
def training_jobs(
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
):
    """List training jobs from the Training Database."""

    return list_training_jobs(
        limit=limit
    )


@router.get("/jobs/{job_id}")
def training_job_details(
    job_id: str,
):
    """Retrieve a training job from the Training Database."""

    job = get_training_job(
        job_id
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Training job not found.",
        )

    return job


@router.post("/jobs/{dataset_id}")
def create_training_job(
    dataset_id: str,
):
    """
    Verify training artifacts and create or reuse a job.

    Automatic worker execution remains disabled
    until Phase 1 integration testing is complete.
    """

    try:

        # -------------------------------------------------
        # Step 1 — Validate dataset approval and integrity.
        # -------------------------------------------------

        verification = verify_training_artifacts(
            dataset_id
        )

        if verification["integrity_status"] != "VERIFIED":
            raise HTTPException(
                status_code=422,
                detail=(
                    "Training dataset integrity "
                    "verification failed."
                ),
            )

        # -------------------------------------------------
        # Step 2 — Reuse an existing active job.
        # -------------------------------------------------

        existing_job = find_active_training_job(
            dataset_id
        )

        if existing_job is not None:
            return {
                **existing_job,
                "automatic_worker_launched": False,
                "note": (
                    "An existing active training job "
                    "was reused. No worker launched."
                ),
            }

        # -------------------------------------------------
        # Step 3 — Create a queued training job.
        # -------------------------------------------------

        job = enqueue_training_job(
            dataset_id
        )

        return {
            **job,
            "automatic_worker_launched": False,
            "note": (
                "Training job queued successfully. "
                "Automatic execution is disabled "
                "during Phase 1 database migration."
            ),
        }

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    except sqlite3.Error as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Training Database operation failed."
            ),
        ) from error