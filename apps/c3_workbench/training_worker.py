"""
Background training worker for GeoNex C3.

Phase 1.4 — Dedicated Training Database Integration

Responsibilities
----------------
1. Retrieve a queued training job.
2. Verify dataset approval and artifact integrity.
3. Atomically claim the job.
4. Execute the configured training commands.
5. Persist training progress and events.
6. Move the job into EVALUATING after training.
7. Record failures safely.

Database ownership
------------------
Training job state and events:
    data/training/c3_training.sqlite3

Operational sensor observations:
    data/workbench/c3/golden/c3_golden.sqlite3

The worker must not directly write training state
into the Golden Database.
"""

from __future__ import annotations

import argparse
import json
import traceback

from pathlib import Path
from typing import Any

from apps.c3_workbench.training_artifact_integrity import (
    verify_training_artifacts,
)

from apps.c3_workbench.training_queue import (
    claim_training_job,
    get_training_job,
    update_training_job,
)

from apps.c3_workbench.training_runner import (
    MODEL_RUN_ROOT,
    build_training_commands,
    run_training_command,
)


def validate_training_configuration(
    *,
    max_epochs: int,
    patience: int,
    device: str,
) -> None:
    """Validate training configuration before claiming a job."""

    if max_epochs < 1:
        raise ValueError(
            "max_epochs must be greater than zero."
        )

    if patience < 1:
        raise ValueError(
            "patience must be greater than zero."
        )

    if device not in {"auto", "cpu", "mps"}:
        raise ValueError(
            f"Unsupported training device: {device}"
        )


def prepare_training_directory(
    job_id: str,
) -> Path:
    """
    Prepare a unique directory for this worker execution.

    Existing run directories are never overwritten because
    they may contain checkpoints, logs, and research results.
    """

    job_dir = (
        MODEL_RUN_ROOT
        / job_id
        / "worker_run"
    ).resolve()

    if job_dir.exists():
        raise FileExistsError(
            "Training output directory already exists: "
            f"{job_dir}. "
            "Existing research artifacts will not be overwritten."
        )

    job_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    return job_dir


def execute_training_job(
    job_id: str,
    *,
    max_epochs: int = 30,
    patience: int = 6,
    device: str = "auto",
) -> dict[str, Any]:
    """
    Execute one explicitly selected training job.

    The worker does not automatically process all queued jobs.

    Training approval and artifact integrity must be valid
    before execution and remain valid throughout training.
    """

    validate_training_configuration(
        max_epochs=max_epochs,
        patience=patience,
        device=device,
    )

    job = get_training_job(job_id)

    if job is None:
        raise ValueError(
            f"Training job not found: {job_id}"
        )

    if job["status"] != "QUEUED":
        raise ValueError(
            f"Job must be QUEUED. "
            f"Current status: {job['status']}"
        )

    dataset_id = job["dataset_id"]

    # Verify approval and artifact integrity before claiming.
    verification = verify_training_artifacts(
        dataset_id
    )

    dataset_dir = Path(
        verification["dataset_dir"]
    ).resolve()

    if not dataset_dir.is_dir():
        raise FileNotFoundError(
            "Verified training dataset directory "
            f"does not exist: {dataset_dir}"
        )

    # Prevent overwriting an earlier execution.
    expected_job_dir = (
        MODEL_RUN_ROOT
        / job_id
        / "worker_run"
    ).resolve()

    if expected_job_dir.exists():
        raise FileExistsError(
            "Training output directory already exists: "
            f"{expected_job_dir}"
        )

    # Claim the job atomically in the Training Database.
    claimed = claim_training_job(job_id)

    if claimed is None:
        raise RuntimeError(
            "Job could not be claimed. "
            "It may have been claimed by another worker."
        )

    job_dir: Path | None = None

    try:
        job_dir = prepare_training_directory(
            job_id
        )

        commands = build_training_commands(
            dataset_dir=dataset_dir,
            job_dir=job_dir,
            max_epochs=max_epochs,
            patience=patience,
            device=device,
        )

        if not commands:
            raise RuntimeError(
                "Training runner returned no commands."
            )

        total_commands = len(commands)

        for index, (stage, command) in enumerate(
            commands,
            start=1,
        ):
            # Approval can be revoked during training.
            # The dataset must remain valid for every stage.
            verify_training_artifacts(
                dataset_id
            )

            update_training_job(
                job_id,
                status="TRAINING",
                stage=stage,
                message=(
                    f"Starting task {index}/"
                    f"{total_commands}: {stage}"
                ),
            )

            log_path = (
                job_dir
                / "logs"
                / f"{stage}.log"
            )

            log_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            run_training_command(
                job_id=job_id,
                stage=stage,
                command=command,
                log_path=log_path,
            )

            update_training_job(
                job_id,
                status="TRAINING",
                stage=stage,
                message=(
                    f"Completed task {index}/"
                    f"{total_commands}: {stage}"
                ),
            )

        # Training completion does not automatically mean
        # that the model is approved or deployable.
        update_training_job(
            job_id,
            status="EVALUATING",
            stage="ARTIFACT_REVIEW",
            message=(
                f"All {total_commands} training commands "
                "completed. Model artifact review is pending."
            ),
        )

        result = {
            "job_id": job_id,
            "dataset_id": dataset_id,
            "status": "EVALUATING",
            "tasks_completed": total_commands,
            "job_dir": str(job_dir),
        }

        result_path = (
            job_dir
            / "worker_result.json"
        )

        result_path.write_text(
            json.dumps(
                result,
                indent=2,
            ),
            encoding="utf-8",
        )

        return result

    except Exception as error:
        # Preserve the original failure even if recording
        # the failure in the database also encounters an error.
        try:
            update_training_job(
                job_id,
                status="FAILED",
                stage="TRAINING_FAILED",
                level="ERROR",
                message=(
                    f"Training worker failed: {error}"
                ),
                error_message=str(error),
            )

        except Exception as persistence_error:
            print(
                "WARNING: Could not persist training failure: "
                f"{persistence_error}",
                flush=True,
            )

        traceback.print_exc()

        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run one approved GeoNex C3 "
            "background training job."
        )
    )

    parser.add_argument(
        "--job-id",
        required=True,
        help="Existing queued training job ID.",
    )

    parser.add_argument(
        "--max-epochs",
        type=int,
        default=30,
    )

    parser.add_argument(
        "--patience",
        type=int,
        default=6,
    )

    parser.add_argument(
        "--device",
        choices=(
            "auto",
            "cpu",
            "mps",
        ),
        default="auto",
    )

    args = parser.parse_args()

    result = execute_training_job(
        args.job_id,
        max_epochs=args.max_epochs,
        patience=args.patience,
        device=args.device,
    )

    print(
        json.dumps(
            result,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()