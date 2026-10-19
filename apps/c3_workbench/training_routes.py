"""Training job API for GeoNex C3."""

import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from apps.c3_workbench.training_artifact_integrity import verify_training_artifacts
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
        # Authorization and exported data integrity must pass before scheduling.
        verify_training_artifacts(dataset_id)
        active = [j for j in list_training_jobs(limit=200)['jobs'] if j['dataset_id'] == dataset_id and j['status'] in ('QUEUED', 'PREPARING', 'TRAINING', 'EVALUATING')]
        if active:
            return {**active[0], 'automatic_worker_launched': False, 'note': 'An existing active job was reused. No second worker launched.'}
        job = enqueue_training_job(dataset_id)
        # Never start a second process for an already claimed/existing job.
        if job['status'] != 'QUEUED' or job.get('current_stage') != 'WAITING_FOR_WORKER':
            return job
        # A detached process survives the HTTP request; its progress is persisted.
        # The process uses the same interpreter/environment as the API.
        root = Path(__file__).resolve().parents[2]
        log_dir = root / 'data' / 'workbench' / 'c3' / 'auto_worker_logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / f"{job['job_id']}.log").open('ab') as log:
            subprocess.Popen(
                [sys.executable, '-m', 'apps.c3_workbench.training_auto_runner', job['job_id']],
                cwd=str(root), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        return {**job, 'automatic_worker_launched': True}

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error