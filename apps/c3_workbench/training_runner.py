"""Execute GeoNex C3 forecasting training scripts."""

from __future__ import annotations

import os
import subprocess
import sys

from pathlib import Path

from apps.c3_workbench.training_artifact_integrity import (
    verify_training_artifacts,
)
from apps.c3_workbench.training_queue import (
    append_training_event,
    update_training_job,
)
from apps.c3_workbench.golden_db import get_connection


MODEL_RUN_ROOT = Path(
    "data/workbench/c3/model_runs"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def log_training_output(
    job_id: str,
    *,
    stage: str,
    message: str,
) -> None:
    """Persist actual subprocess output as a training event."""

    with get_connection() as connection:
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
    """Run one training process and capture its output."""

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

        for line in process.stdout:
            message = line.rstrip("\n")

            log_file.write(line)
            log_file.flush()

            if message.strip():
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
    """Build isolated commands for M1–M4."""

    commands = []

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

    commands.append(
        (
            "TRAINING_M1",
            base_command(
                "scripts.train.train_c3_m1_ridge",
                job_dir / "m1",
            ),
        )
    )

    commands.append(
        (
            "TRAINING_M2",
            base_command(
                "scripts.train.train_c3_m2_gradient_boosting",
                job_dir / "m2",
            ),
        )
    )

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
) -> dict:
    """Execute M1–M4 against one approved dataset."""

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

    for index, (stage, command) in enumerate(
        commands,
        start=1,
    ):
        # Recheck approval and integrity before each model.
        verify_training_artifacts(dataset_id)

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
            job_dir / "logs" / f"{stage}.log"
        )

        run_training_command(
            job_id=job_id,
            stage=stage,
            command=command,
            log_path=log_path,
        )

    update_training_job(
        job_id,
        status="EVALUATING",
        stage="ARTIFACT_REVIEW",
        message=(
            "All model training commands finished. "
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