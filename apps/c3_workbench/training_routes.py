"""Training job API for GeoNex C3."""

from fastapi import APIRouter, HTTPException, Query

from apps.c3_workbench.training_queue import (
    enqueue_training_job,
    get_training_job,
    list_training_jobs,
)


router = APIRouter(
    prefix="/training",
    tags=["C3 Training"],
)


@router.get("/jobs")
def training_jobs(
    limit: int = Query(default=50, ge=1, le=200),
):
    return list_training_jobs(limit=limit)


@router.get("/jobs/{job_id}")
def training_job_details(job_id: str):
    job = get_training_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Training job not found.",
        )

    return job


@router.post("/jobs/{dataset_id}")
def create_training_job(dataset_id: str):
    try:
        return enqueue_training_job(dataset_id)

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error