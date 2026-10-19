"""Detached, explicitly authorized C3 training job runner.

Run from repository root: python -m apps.c3_workbench.training_auto_runner JOB_ID
"""
from __future__ import annotations

import argparse
import traceback

from apps.c3_workbench.model_registry import register_model_candidates
from apps.c3_workbench.training_completion import complete_training_job
from apps.c3_workbench.training_queue import get_training_job, update_training_job
from apps.c3_workbench.training_worker import execute_training_job


def run(job_id: str) -> dict:
    job = get_training_job(job_id)
    if job is None:
        raise ValueError(f"Unknown job: {job_id}")
    if job['status'] != 'QUEUED':
        raise ValueError(f"Expected QUEUED, got {job['status']}")
    dataset_id = job['dataset_id']
    try:
        execute_training_job(job_id, max_epochs=30, patience=6, device='auto')
        # Both functions validate artifacts and enforce job/dataset consistency.
        registered = register_model_candidates(job_id, dataset_id)
        completed = complete_training_job(job_id, dataset_id)
        return {'registration': registered, 'completion': completed}
    except Exception as exc:
        # Do not overwrite a successful or separately failed terminal state.
        latest = get_training_job(job_id)
        if latest and latest['status'] not in ('FAILED', 'COMPLETED', 'CANCELLED'):
            update_training_job(job_id, status='FAILED', stage='AUTOMATION_FAILED', level='ERROR', message=f'Automatic pipeline failed: {exc}', error_message=str(exc))
        traceback.print_exc()
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('job_id')
    args = parser.parse_args()
    run(args.job_id)

if __name__ == '__main__':
    main()
