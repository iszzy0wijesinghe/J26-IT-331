"""
GeoNex C3 model artifact validation and candidate registration.

Phase 1.5.2 — Dedicated Training Database Cutover.

Responsibilities:
    - Verify approved training artifacts.
    - Validate M1–M4 model checkpoints.
    - Validate evaluation metrics.
    - Register model candidates in the Training Database.
    - Preserve existing model versions.
    - Prevent duplicate registrations.
    - Identify validation winners without activating models.

Database ownership:
    c3_training_jobs     -> Training Database
    c3_model_versions    -> Training Database

This module never writes to the Golden Database.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apps.c3_workbench.training_database import (
    connect_training_db,
    get_training_db_path,
)

from apps.c3_workbench.training_artifact_integrity import (
    verify_training_artifacts,
)


MODEL_RUNS_ROOT = Path(
    "data/workbench/c3/model_runs"
)

HORIZONS = (15, 30, 60)

EXPECTED_MODEL_COUNT = 18


class ModelRegistrationError(ValueError):
    """Raised when model validation or registration fails."""


def utc_now() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(UTC).isoformat()


def get_registry_connection() -> sqlite3.Connection:
    """
    Connect exclusively to the dedicated Training Database.

    Refuse to operate if the database or required migrated
    tables are missing.
    """

    database_path = get_training_db_path()

    if not database_path.is_file():
        raise ModelRegistrationError(
            "GeoNex C3 Training Database does not exist: "
            f"{database_path}"
        )

    connection = connect_training_db()
    connection.row_factory = sqlite3.Row

    required_tables = {
        "c3_training_jobs",
        "c3_model_versions",
    }

    existing_tables = {
        row["name"]
        for row in connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()
    }

    missing_tables = required_tables - existing_tables

    if missing_tables:
        connection.close()

        raise ModelRegistrationError(
            "Training Database is missing required tables: "
            + ", ".join(sorted(missing_tables))
        )

    return connection


def sha256_file(path: Path) -> str:
    """Calculate a file's SHA-256 checksum."""

    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    """Load and validate a model metrics JSON file."""

    if not path.is_file():
        raise ModelRegistrationError(
            f"Missing metrics file: {path}"
        )

    try:
        data = json.loads(
            path.read_text(encoding="utf-8")
        )

    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ModelRegistrationError(
            f"Invalid metrics JSON file: {path}"
        ) from error

    if not isinstance(data, dict):
        raise ModelRegistrationError(
            f"Invalid metrics structure: {path}"
        )

    return data


def valid_metric(
    value: Any,
    label: str,
) -> float:
    """Require a finite, non-negative numerical metric."""

    if isinstance(value, bool):
        raise ModelRegistrationError(
            f"Invalid metric {label}: {value}"
        )

    try:
        result = float(value)

    except (TypeError, ValueError) as error:
        raise ModelRegistrationError(
            f"Invalid metric {label}: {value}"
        ) from error

    if not math.isfinite(result) or result < 0:
        raise ModelRegistrationError(
            f"Invalid metric {label}: {value}"
        )

    return result


def validate_checkpoint(
    path: Path,
    expected_sha256: str | None = None,
) -> str:
    """
    Verify that a checkpoint exists, is non-empty,
    and matches its expected checksum when supplied.
    """

    if (
        not path.is_file()
        or path.stat().st_size == 0
    ):
        raise ModelRegistrationError(
            f"Missing or empty checkpoint: {path}"
        )

    actual_sha256 = sha256_file(path)

    if (
        expected_sha256 is not None
        and actual_sha256 != expected_sha256
    ):
        raise ModelRegistrationError(
            f"Checkpoint SHA-256 mismatch: {path}"
        )

    return actual_sha256


def resolve_model_run_directory(
    job_id: str,
) -> Path:
    """Resolve a model run directory safely."""

    if (
        not isinstance(job_id, str)
        or not job_id
        or job_id in {".", ".."}
        or "/" in job_id
        or "\\" in job_id
        or "\x00" in job_id
    ):
        raise ModelRegistrationError(
            "Invalid training job identifier."
        )

    root = MODEL_RUNS_ROOT.resolve()

    run_directory = (
        root / job_id / "worker_run"
    ).resolve()

    if root not in run_directory.parents:
        raise ModelRegistrationError(
            "Model run directory escapes the configured root."
        )

    return run_directory


def collect_model_candidates(
    job_id: str,
    dataset_id: str,
) -> list[dict[str, Any]]:
    """
    Validate every expected model artifact.

    This function only reads files.

    Expected candidates:
        M1 Ridge:               3
        M2 Gradient Boosting:   3
        M3 Standard GRU:        3
        M4 Ablation A:          3
        M4 Ablation B:          3
        M4 Ablation C:          3

    Total: 18
    """

    verification = verify_training_artifacts(
        dataset_id
    )

    if verification["integrity_status"] != "VERIFIED":
        raise ModelRegistrationError(
            "Training dataset integrity verification failed."
        )

    root = resolve_model_run_directory(
        job_id
    )

    if not root.is_dir():
        raise ModelRegistrationError(
            f"Model run directory does not exist: {root}"
        )

    candidates: list[dict[str, Any]] = []

    # -----------------------------------------------------
    # M1 and M2 — Tabular models
    # -----------------------------------------------------

    tabular_models = (
        (
            "M1_RIDGE",
            "m1",
            "ridge",
        ),
        (
            "M2_GRADIENT_BOOSTING",
            "m2",
            "gradient_boosting",
        ),
    )

    for model_name, folder, filename_prefix in tabular_models:

        model_dir = root / folder

        metrics = load_json(
            model_dir / "metrics.json"
        )

        results = metrics.get("results")

        if not isinstance(results, dict):
            raise ModelRegistrationError(
                f"Missing horizon results for {model_name}"
            )

        for horizon in HORIZONS:

            result = results.get(
                str(horizon)
            )

            if not isinstance(result, dict):
                raise ModelRegistrationError(
                    f"Missing {model_name} "
                    f"{horizon}min results"
                )

            validation = result.get(
                "validation"
            )

            if not isinstance(validation, dict):
                raise ModelRegistrationError(
                    "Missing validation metrics: "
                    f"{model_name} {horizon}min"
                )

            expected_filename = (
                f"{filename_prefix}_{horizon}min.joblib"
            )

            if result.get("model_file") != expected_filename:
                raise ModelRegistrationError(
                    "Checkpoint filename mismatch: "
                    f"{model_name}"
                )

            checkpoint = (
                model_dir / expected_filename
            )

            checkpoint_sha256 = validate_checkpoint(
                checkpoint,
                result.get("model_sha256"),
            )

            candidates.append(
                {
                    "model_name": model_name,
                    "horizon_minutes": horizon,
                    "checkpoint_path": str(
                        checkpoint.resolve()
                    ),
                    "checkpoint_sha256": checkpoint_sha256,
                    "validation_mae": valid_metric(
                        validation.get("mae"),
                        f"{model_name} {horizon}min MAE",
                    ),
                    "validation_rmse": valid_metric(
                        validation.get("rmse"),
                        f"{model_name} {horizon}min RMSE",
                    ),
                }
            )

    # -----------------------------------------------------
    # M3 — Standard GRU
    # -----------------------------------------------------

    for horizon in HORIZONS:

        model_dir = root / "m3"

        metrics = load_json(
            model_dir / f"gru_{horizon}min_metrics.json"
        )

        if metrics.get("horizon_minutes") != horizon:
            raise ModelRegistrationError(
                f"M3 horizon mismatch: {horizon}"
            )

        expected_filename = (
            f"gru_{horizon}min.pt"
        )

        if metrics.get("checkpoint") != expected_filename:
            raise ModelRegistrationError(
                f"M3 checkpoint mismatch: {horizon}"
            )

        validation = metrics.get(
            "best_validation_metrics",
            {},
        )

        checkpoint = (
            model_dir / expected_filename
        )

        candidates.append(
            {
                "model_name": "M3_STANDARD_GRU",
                "horizon_minutes": horizon,
                "checkpoint_path": str(
                    checkpoint.resolve()
                ),
                "checkpoint_sha256": validate_checkpoint(
                    checkpoint
                ),
                "validation_mae": valid_metric(
                    validation.get("mae"),
                    f"M3 {horizon}min MAE",
                ),
                "validation_rmse": valid_metric(
                    validation.get("rmse"),
                    f"M3 {horizon}min RMSE",
                ),
            }
        )

    # -----------------------------------------------------
    # M4 — GRU ablation models
    # -----------------------------------------------------

    for ablation in ("A", "B", "C"):

        for horizon in HORIZONS:

            model_dir = root / "m4"

            prefix = (
                f"m4_{ablation.lower()}_{horizon}min"
            )

            metrics = load_json(
                model_dir / f"{prefix}_metrics.json"
            )

            if metrics.get("horizon_minutes") != horizon:
                raise ModelRegistrationError(
                    "M4 horizon mismatch: "
                    f"{ablation} {horizon}"
                )

            if metrics.get("ablation") != ablation:
                raise ModelRegistrationError(
                    f"M4-{ablation} ablation mismatch"
                )

            expected_filename = (
                f"{prefix}.pt"
            )

            if metrics.get("checkpoint") != expected_filename:
                raise ModelRegistrationError(
                    f"M4-{ablation} checkpoint mismatch"
                )

            validation = metrics.get(
                "best_validation_metrics",
                {},
            )

            checkpoint = (
                model_dir / expected_filename
            )

            candidates.append(
                {
                    "model_name": f"M4_{ablation}_GRU",
                    "horizon_minutes": horizon,
                    "checkpoint_path": str(
                        checkpoint.resolve()
                    ),
                    "checkpoint_sha256": validate_checkpoint(
                        checkpoint
                    ),
                    "validation_mae": valid_metric(
                        validation.get("mae"),
                        f"M4-{ablation} {horizon}min MAE",
                    ),
                    "validation_rmse": valid_metric(
                        validation.get("rmse"),
                        f"M4-{ablation} {horizon}min RMSE",
                    ),
                }
            )

    if len(candidates) != EXPECTED_MODEL_COUNT:
        raise ModelRegistrationError(
            "Expected "
            f"{EXPECTED_MODEL_COUNT} model candidates, "
            f"got {len(candidates)}"
        )

    return candidates


def register_model_candidates(
    job_id: str,
    dataset_id: str,
) -> dict[str, Any]:
    """
    Register validated model candidates in the Training DB.

    This operation:
        - Requires an EVALUATING or COMPLETED job.
        - Rejects mismatched dataset IDs.
        - Rejects duplicate registrations.
        - Inserts all 18 candidates atomically.
        - Does not change the training job status.
        - Does not activate any model.
    """

    # Validate artifacts before opening a write transaction.
    candidates = collect_model_candidates(
        job_id=job_id,
        dataset_id=dataset_id,
    )

    with get_registry_connection() as connection:

        # Prevent concurrent registration attempts.
        connection.execute(
            "BEGIN IMMEDIATE"
        )

        job = connection.execute(
            """
            SELECT job_id, dataset_id, status
            FROM c3_training_jobs
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()

        if job is None:
            raise ModelRegistrationError(
                f"Unknown training job: {job_id}"
            )

        if job["dataset_id"] != dataset_id:
            raise ModelRegistrationError(
                "Training job dataset mismatch."
            )

        if job["status"] not in (
            "EVALUATING",
            "COMPLETED",
        ):
            raise ModelRegistrationError(
                "Job is not ready for registration: "
                f"{job['status']}"
            )

        existing = connection.execute(
            """
            SELECT COUNT(*)
            FROM c3_model_versions
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()[0]

        if existing:
            raise ModelRegistrationError(
                "This training job already has "
                "registered models."
            )

        created_at = utc_now()

        for candidate in candidates:

            model_version_id = (
                f"{job_id}__"
                f"{candidate['model_name'].lower()}__"
                f"{candidate['horizon_minutes']}min"
            )

            connection.execute(
                """
                INSERT INTO c3_model_versions (
                    model_version_id,
                    job_id,
                    dataset_id,
                    model_name,
                    horizon_minutes,
                    checkpoint_path,
                    validation_mae,
                    validation_rmse,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model_version_id,
                    job_id,
                    dataset_id,
                    candidate["model_name"],
                    candidate["horizon_minutes"],
                    candidate["checkpoint_path"],
                    candidate["validation_mae"],
                    candidate["validation_rmse"],
                    "CANDIDATE",
                    created_at,
                ),
            )

        connection.commit()

    # -----------------------------------------------------
    # Determine validation winners.
    # This does NOT activate models.
    # -----------------------------------------------------

    winners: dict[str, dict[str, Any]] = {}

    for horizon in HORIZONS:

        horizon_candidates = [
            candidate
            for candidate in candidates
            if candidate["horizon_minutes"] == horizon
        ]

        winner = min(
            horizon_candidates,
            key=lambda item: (
                item["validation_mae"],
                item["validation_rmse"],
            ),
        )

        winners[str(horizon)] = {
            "model_name": winner["model_name"],
            "validation_mae": winner["validation_mae"],
            "validation_rmse": winner["validation_rmse"],
        }

    return {
        "job_id": job_id,
        "dataset_id": dataset_id,
        "registered_models": len(candidates),
        "status": "CANDIDATE",
        "validation_winners": winners,
        "job_status_unchanged": True,
    }