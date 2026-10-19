"""Background training worker for GeoNex C3."""

from __future__ import annotations

import argparse
import json
import traceback

from pathlib import Path

from apps.c3_workbench.training_artifact_integrity import (
    verify_training_artifacts,
)
from apps.c3_workbench.training_queue import (
    claim_training_job,
    get_training_job,
    update_training_job,
)
from apps.c3_workbench.training_runner import (
    build_training_commands,
    run_training_command,
    MODEL_RUN_ROOT,
)


def execute_training_job(
    job_id: str,
    *,
    max_epochs: int = 30,
    patience: int = 6,
    device: str = "auto",
) -> dict:
    """
    Execute one explicitly selected queued training job.

    This initial worker is intentionally job-specific.
    It does not automatically process every queued dataset.
    """

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

    # Verify approval and exported-file integrity
    # before changing the job state.
    verification = verify_training_artifacts(
        dataset_id
    )

    claimed = claim_training_job(job_id)

    if claimed is None:
        raise RuntimeError(
            "Job could not be claimed. "
            "It may have been claimed by another worker."
        )

    dataset_dir = Path(
        verification["dataset_dir"]
    ).resolve()

    job_dir = (
        MODEL_RUN_ROOT
        / job_id
        / "worker_run"
    ).resolve()

    try:
        job_dir.mkdir(
            parents=True,
            exist_ok=False,
        )

        commands = build_training_commands(
            dataset_dir=dataset_dir,
            job_dir=job_dir,
            max_epochs=max_epochs,
            patience=patience,
            device=device,
        )

        for index, (stage, command) in enumerate(
            commands,
            start=1,
        ):
            # Approval can be revoked while a job is queued
            # or while earlier models are training.
            verify_training_artifacts(dataset_id)

            update_training_job(
                job_id,
                status="TRAINING",
                stage=stage,
                message=(
                    f"Starting task {index}/"
                    f"{len(commands)}: {stage}"
                ),
            )

            run_training_command(
                job_id=job_id,
                stage=stage,
                command=command,
                log_path=(
                    job_dir
                    / "logs"
                    / f"{stage}.log"
                ),
            )

        update_training_job(
            job_id,
            status="EVALUATING",
            stage="ARTIFACT_REVIEW",
            message=(
                "All 14 training commands finished. "
                "Model artifact review is pending."
            ),
        )

        result = {
            "job_id": job_id,
            "dataset_id": dataset_id,
            "status": "EVALUATING",
            "tasks_completed": len(commands),
            "job_dir": str(job_dir),
        }

        result_path = (
            job_dir / "worker_result.json"
        )

        result_path.write_text(
            json.dumps(result, indent=2),
            encoding="utf-8",
        )

        return result

    except Exception as error:
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
        choices=("auto", "cpu", "mps"),
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
        json.dumps(result, indent=2),
        flush=True,
    )


if __name__ == "__main__":
    main()