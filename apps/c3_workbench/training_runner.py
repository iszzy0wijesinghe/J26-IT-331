"""
Execute GeoNex C3 forecasting training scripts.

Phase 1.4.3 — Dedicated Training Database Integration

Database ownership
------------------
Training Database:
    - c3_training_jobs
    - c3_training_events
    - Training approval and model metadata

Golden Database:
    - Operational sensor observations
    - Operational forecasting results
    - Operational alerts

Training subprocess output is persisted exclusively to
the dedicated Training Database.

The existing M1–M4 training pipeline is preserved.
"""

from __future__ import annotations

import os
import subprocess
import sys
import traceback

from pathlib import Path
from typing import Any

from apps.c3_workbench.training_database import (
    connect_training_db,
)

from apps.c3_workbench.training_artifact_integrity import (
    verify_training_artifacts,
)

from apps.c3_workbench.training_queue import (
    append_training_event,
    get_training_job,
    update_training_job,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Preserve the existing model artifact location during
# Phase 1.4 to avoid breaking downstream consumers.
#
# Artifact storage separation will be addressed in
# Phase 1.6 after model registry dependencies are reviewed.
MODEL_RUN_ROOT = Path(
    "data/workbench/c3/model_runs"
)


def log_training_output(
    job_id: str,
    *,
    stage: str,
    message: str,
) -> None:
    """
    Persist subprocess output to the Training Database.

    Never write training events to the Golden Database.
    """

    with connect_training_db() as connection:
        append_training_event(
            connection,
            job_id=job_id,
            level="INFO",
            stage=stage,
            message=message,
        )


def run_training_command(
    *,
    job_id: str,
    stage: str,
    command: list[str],
    log_path: Path,
) -> None:
    """
    Execute one training subprocess.

    Output is written to:
        1. The stage-specific log file.
        2. The dedicated Training Database.
        3. The console.

    A nonzero subprocess exit code raises RuntimeError.
    """

    if not command:
        raise ValueError(
            "Training command cannot be empty."
        )

    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    environment = os.environ.copy()

    environment["PYTHONUNBUFFERED"] = "1"

    with log_path.open(
        "w",
        encoding="utf-8",
    ) as log_file:

        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        assert process.stdout is not None

        try:
            for line in process.stdout:
                message = line.rstrip("\r\n")

                log_file.write(line)
                log_file.flush()

                if not message.strip():
                    continue

                print(
                    f"[{stage}] {message}",
                    flush=True,
                )

                log_training_output(
                    job_id,
                    stage=stage,
                    message=message,
                )

            return_code = process.wait()

        except Exception:
            # Avoid leaving a training subprocess running
            # if output handling or database logging fails.
            if process.poll() is None:
                process.terminate()

                try:
                    process.wait(timeout=10)

                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

            raise

        finally:
            process.stdout.close()

        if return_code != 0:
            raise RuntimeError(
                f"{stage} failed with exit code "
                f"{return_code}. See {log_path}"
            )


def build_training_commands(
    *,
    dataset_dir: Path,
    job_dir: Path,
    max_epochs: int = 30,
    patience: int = 6,
    device: str = "auto",
) -> list[tuple[str, list[str]]]:
    """
    Build the existing M1–M4 training commands.

    M1:
        Ridge Regression

    M2:
        Gradient Boosting

    M3:
        GRU for 15, 30, and 60 minutes

    M4:
        GRU ablations A/B/C for 15, 30, and 60 minutes

    Total:
        14 training commands.
    """

    if max_epochs < 1:
        raise ValueError(
            "max_epochs must be greater than zero."
        )

    if patience < 1:
        raise ValueError(
            "patience must be greater than zero."
        )

    if device not in {
        "auto",
        "cpu",
        "mps",
    }:
        raise ValueError(
            f"Unsupported training device: {device}"
        )

    dataset_dir = Path(dataset_dir).resolve()

    job_dir = Path(job_dir).resolve()

    if not dataset_dir.is_dir():
        raise FileNotFoundError(
            "Training dataset directory does not exist: "
            f"{dataset_dir}"
        )

    commands: list[tuple[str, list[str]]] = []

    def base_command(
        module: str,
        output_dir: Path,
    ) -> list[str]:
        return [
            sys.executable,
            "-m",
            module,
            "--dataset-dir",
            str(dataset_dir),
            "--output-dir",
            str(output_dir),
        ]

    # --------------------------------------------------
    # M1 — Ridge Regression
    # --------------------------------------------------

    commands.append(
        (
            "TRAINING_M1",
            base_command(
                "scripts.train.train_c3_m1_ridge",
                job_dir / "m1",
            ),
        )
    )

    # --------------------------------------------------
    # M2 — Gradient Boosting
    # --------------------------------------------------

    commands.append(
        (
            "TRAINING_M2",
            base_command(
                "scripts.train.train_c3_m2_gradient_boosting",
                job_dir / "m2",
            ),
        )
    )

    # --------------------------------------------------
    # M3 — GRU
    # --------------------------------------------------

    for horizon in (15, 30, 60):
        commands.append(
            (
                f"TRAINING_M3_{horizon}MIN",
                base_command(
                    "scripts.train.train_c3_m3_gru",
                    job_dir / "m3",
                )
                + [
                    "--horizon",
                    str(horizon),
                    "--max-epochs",
                    str(max_epochs),
                    "--patience",
                    str(patience),
                    "--device",
                    device,
                ],
            )
        )

    # --------------------------------------------------
    # M4 — GRU Ablation Experiments
    # --------------------------------------------------

    for ablation in ("A", "B", "C"):
        for horizon in (15, 30, 60):
            commands.append(
                (
                    f"TRAINING_M4_{ablation}_{horizon}MIN",
                    base_command(
                        "scripts.train.train_c3_m4_gru",
                        job_dir / "m4",
                    )
                    + [
                        "--horizon",
                        str(horizon),
                        "--ablation",
                        ablation,
                        "--max-epochs",
                        str(max_epochs),
                        "--patience",
                        str(patience),
                        "--device",
                        device,
                    ],
                )
            )

    return commands


def run_training_pipeline(
    *,
    job_id: str,
    dataset_id: str,
    max_epochs: int = 30,
    patience: int = 6,
    device: str = "auto",
) -> dict[str, Any]:
    """
    Execute the existing M1–M4 training pipeline.

    Preconditions:
        - Training job exists.
        - Job belongs to the specified dataset.
        - Job has already been claimed by an authorized worker.
        - Dataset approval and artifact integrity are valid.

    The pipeline does not claim queued jobs itself.
    """

    job = get_training_job(job_id)

    if job is None:
        raise ValueError(
            f"Training job not found: {job_id}"
        )

    if job["dataset_id"] != dataset_id:
        raise ValueError(
            "Training job dataset mismatch. "
            f"Job dataset: {job['dataset_id']}; "
            f"requested dataset: {dataset_id}"
        )

    if job["status"] not in {
        "PREPARING",
        "TRAINING",
    }:
        raise ValueError(
            "Training pipeline requires a claimed job "
            "with PREPARING or TRAINING status. "
            f"Current status: {job['status']}"
        )

    # Verify dataset approval and artifact integrity
    # before starting the training pipeline.
    verification = verify_training_artifacts(
        dataset_id
    )

    dataset_dir = Path(
        verification["dataset_dir"]
    ).resolve()

    job_dir = (
        MODEL_RUN_ROOT / job_id
    ).resolve()

    job_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    commands = build_training_commands(
        dataset_dir=dataset_dir,
        job_dir=job_dir,
        max_epochs=max_epochs,
        patience=patience,
        device=device,
    )

    try:
        for index, (stage, command) in enumerate(
            commands,
            start=1,
        ):
            # Approval can be revoked between tasks.
            verify_training_artifacts(
                dataset_id
            )

            update_training_job(
                job_id,
                status="TRAINING",
                stage=stage,
                message=(
                    f"Starting training task "
                    f"{index}/{len(commands)}: {stage}"
                ),
            )

            log_path = (
                job_dir
                / "logs"
                / f"{stage}.log"
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
                    f"Completed training task "
                    f"{index}/{len(commands)}: {stage}"
                ),
            )

        update_training_job(
            job_id,
            status="EVALUATING",
            stage="ARTIFACT_REVIEW",
            message=(
                f"All {len(commands)} model training "
                "commands finished. "
                "Awaiting model artifact evaluation."
            ),
        )

        return {
            "job_id": job_id,
            "dataset_id": dataset_id,
            "job_dir": str(job_dir),
            "tasks_completed": len(commands),
            "status": "EVALUATING",
        }

    except Exception as error:
        try:
            update_training_job(
                job_id,
                status="FAILED",
                stage="TRAINING_FAILED",
                level="ERROR",
                message=(
                    f"Training pipeline failed: {error}"
                ),
                error_message=str(error),
            )

        except Exception as persistence_error:
            print(
                "WARNING: Failed to persist training "
                f"pipeline error: {persistence_error}",
                file=sys.stderr,
                flush=True,
            )

        traceback.print_exc()

        raise