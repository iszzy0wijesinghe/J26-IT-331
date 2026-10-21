"""
Detached, explicitly authorized GeoNex C3 training job runner.

Run from repository root:

    python -m apps.c3_workbench.training_auto_runner JOB_ID

Workflow
--------
1. Validate the selected training job.
2. Verify dataset approval and artifact integrity.
3. Execute training through the dedicated training worker.
4. Register trained model candidates.
5. Complete the training job.

Database ownership
------------------
Training jobs, events, model metadata and approvals belong
to the dedicated C3 Training Database.

This module does not directly access either database.
Database access is delegated to the corresponding services.
"""

from __future__ import annotations

import argparse
import json
import traceback

from typing import Any

from apps.c3_workbench.model_registry import (
    register_model_candidates,
)

from apps.c3_workbench.training_artifact_integrity import (
    verify_training_artifacts,
)

from apps.c3_workbench.training_completion import (
    complete_training_job,
)

from apps.c3_workbench.training_queue import (
    get_training_job,
    update_training_job,
)

from apps.c3_workbench.training_worker import (
    execute_training_job,
)


TERMINAL_STATUSES = {
    "COMPLETED",
    "FAILED",
    "CANCELLED",
}


def run(job_id: str) -> dict[str, Any]:
    """
    Execute one explicitly selected training job.

    This function does not automatically process all queued
    jobs.

    The selected job must already be queued, and its dataset
    must have valid approval and verified training artifacts.
    """

    if not job_id or not job_id.strip():
        raise ValueError(
            "Training job ID must not be empty."
        )

    job = get_training_job(job_id)

    if job is None:
        raise ValueError(
            f"Unknown training job: {job_id}"
        )

    if job["status"] != "QUEUED":
        raise ValueError(
            "Training job must be QUEUED. "
            f"Current status: {job['status']}"
        )

    dataset_id = job["dataset_id"]

    # Verify authorization before any job state changes.
    #
    # This service must itself be migrated to the dedicated
    # Training Database before enabling automatic training.
    verify_training_artifacts(dataset_id)

    try:
        training_result = execute_training_job(
            job_id,
            max_epochs=30,
            patience=6,
            device="auto",
        )

        if training_result["status"] != "EVALUATING":
            raise RuntimeError(
                "Training worker did not reach the "
                "EVALUATING state."
            )

        # Verify that the job still belongs to the same
        # dataset and is awaiting artifact review.
        latest = get_training_job(job_id)

        if latest is None:
            raise RuntimeError(
                "Training job disappeared after execution."
            )

        if latest["dataset_id"] != dataset_id:
            raise RuntimeError(
                "Training job dataset changed unexpectedly."
            )

        if latest["status"] != "EVALUATING":
            raise RuntimeError(
                "Expected EVALUATING after training, "
                f"got {latest['status']}."
            )

        # Approval may have been revoked during training.
        # Reverify before registering model candidates.
        verify_training_artifacts(dataset_id)

        registered = register_model_candidates(
            job_id,
            dataset_id,
        )

        # Completion must verify model artifacts and
        # persist the final state in the Training Database.
        completed = complete_training_job(
            job_id,
            dataset_id,
        )

        return {
            "job_id": job_id,
            "dataset_id": dataset_id,
            "training": training_result,
            "registration": registered,
            "completion": completed,
        }

    except Exception as error:
        # Do not overwrite an existing terminal state.
        try:
            latest = get_training_job(job_id)

            if (
                latest is not None
                and latest["status"] not in TERMINAL_STATUSES
            ):
                update_training_job(
                    job_id,
                    status="FAILED",
                    stage="AUTOMATION_FAILED",
                    level="ERROR",
                    message=(
                        "Automatic training pipeline failed: "
                        f"{error}"
                    ),
                    error_message=str(error),
                )

        except Exception as persistence_error:
            print(
                "WARNING: Could not persist automatic "
                f"training failure: {persistence_error}",
                flush=True,
            )

        traceback.print_exc()

        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Execute one explicitly authorized "
            "GeoNex C3 training job."
        )
    )

    parser.add_argument(
        "job_id",
        help="Existing queued training job ID.",
    )

    args = parser.parse_args()

    result = run(args.job_id)

    print(
        json.dumps(
            result,
            indent=2,
            default=str,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()