"""GeoNex C3 model artifact validation and candidate registration."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from apps.c3_workbench.golden_db import (
    get_connection,
    initialize_golden_database,
    utc_now,
)
from apps.c3_workbench.training_artifact_integrity import (
    verify_training_artifacts,
)

MODEL_RUNS_ROOT = Path("data/workbench/c3/model_runs")
HORIZONS = (15, 30, 60)


class ModelRegistrationError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise ModelRegistrationError(
            f"Missing metrics file: {path}"
        )

    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ModelRegistrationError(
            f"Invalid metrics structure: {path}"
        )

    return data


def valid_metric(value, label: str) -> float:
    if isinstance(value, bool):
        raise ModelRegistrationError(
            f"Invalid metric {label}: {value}"
        )

    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ModelRegistrationError(
            f"Invalid metric {label}: {value}"
        ) from exc

    if not math.isfinite(result) or result < 0:
        raise ModelRegistrationError(
            f"Invalid metric {label}: {value}"
        )

    return result


def validate_checkpoint(
    path: Path,
    expected_sha256: str | None = None,
) -> str:
    if not path.is_file() or path.stat().st_size == 0:
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


def collect_model_candidates(
    job_id: str,
    dataset_id: str,
) -> list[dict]:
    """
    Validate every expected model artifact.

    This function only reads files. It does not modify SQLite.
    """

    verification = verify_training_artifacts(dataset_id)

    if verification["integrity_status"] != "VERIFIED":
        raise ModelRegistrationError(
            "Training dataset integrity verification failed."
        )

    root = MODEL_RUNS_ROOT / job_id / "worker_run"

    if not root.is_dir():
        raise ModelRegistrationError(
            f"Model run directory does not exist: {root}"
        )

    candidates = []

    # M1 and M2: three horizons per metrics file.
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
        metrics = load_json(model_dir / "metrics.json")

        results = metrics.get("results")

        if not isinstance(results, dict):
            raise ModelRegistrationError(
                f"Missing horizon results for {model_name}"
            )

        for horizon in HORIZONS:
            result = results.get(str(horizon))

            if not isinstance(result, dict):
                raise ModelRegistrationError(
                    f"Missing {model_name} {horizon}min results"
                )

            validation = result.get("validation")

            if not isinstance(validation, dict):
                raise ModelRegistrationError(
                    f"Missing validation metrics: "
                    f"{model_name} {horizon}min"
                )

            expected_filename = (
                f"{filename_prefix}_{horizon}min.joblib"
            )

            if result.get("model_file") != expected_filename:
                raise ModelRegistrationError(
                    f"Checkpoint filename mismatch: {model_name}"
                )

            checkpoint = model_dir / expected_filename

            checkpoint_sha256 = validate_checkpoint(
                checkpoint,
                result.get("model_sha256"),
            )

            candidates.append(
                {
                    "model_name": model_name,
                    "horizon_minutes": horizon,
                    "checkpoint_path": str(checkpoint.resolve()),
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

    # M3: standard GRU.
    for horizon in HORIZONS:
        model_dir = root / "m3"

        metrics = load_json(
            model_dir / f"gru_{horizon}min_metrics.json"
        )

        if metrics.get("horizon_minutes") != horizon:
            raise ModelRegistrationError(
                f"M3 horizon mismatch: {horizon}"
            )

        expected_filename = f"gru_{horizon}min.pt"

        if metrics.get("checkpoint") != expected_filename:
            raise ModelRegistrationError(
                f"M3 checkpoint mismatch: {horizon}"
            )

        validation = metrics.get("best_validation_metrics", {})

        checkpoint = model_dir / expected_filename

        candidates.append(
            {
                "model_name": "M3_STANDARD_GRU",
                "horizon_minutes": horizon,
                "checkpoint_path": str(checkpoint.resolve()),
                "checkpoint_sha256": validate_checkpoint(checkpoint),
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

    # M4: three ablations × three horizons.
    for ablation in ("A", "B", "C"):
        for horizon in HORIZONS:
            model_dir = root / "m4"

            prefix = f"m4_{ablation.lower()}_{horizon}min"

            metrics = load_json(
                model_dir / f"{prefix}_metrics.json"
            )

            if metrics.get("horizon_minutes") != horizon:
                raise ModelRegistrationError(
                    f"M4-{ablation} horizon mismatch: {horizon}"
                )

            if metrics.get("ablation") != ablation:
                raise ModelRegistrationError(
                    f"M4-{ablation} ablation mismatch"
                )

            expected_filename = f"{prefix}.pt"

            if metrics.get("checkpoint") != expected_filename:
                raise ModelRegistrationError(
                    f"M4-{ablation} checkpoint mismatch"
                )

            validation = metrics.get(
                "best_validation_metrics",
                {},
            )

            checkpoint = model_dir / expected_filename

            candidates.append(
                {
                    "model_name": f"M4_{ablation}_GRU",
                    "horizon_minutes": horizon,
                    "checkpoint_path": str(checkpoint.resolve()),
                    "checkpoint_sha256": validate_checkpoint(checkpoint),
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

    if len(candidates) != 18:
        raise ModelRegistrationError(
            f"Expected 18 model candidates, got {len(candidates)}"
        )

    return candidates


def register_model_candidates(
    job_id: str,
    dataset_id: str,
) -> dict:
    """
    Register validated models as CANDIDATE.

    This does not activate models for inference.
    """

    initialize_golden_database()

    candidates = collect_model_candidates(
        job_id=job_id,
        dataset_id=dataset_id,
    )

    with get_connection() as connection:
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

        if job["status"] not in ("EVALUATING", "COMPLETED"):
            raise ModelRegistrationError(
                f"Job is not ready for registration: "
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
                "This training job already has registered models."
            )

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
                    utc_now(),
                ),
            )

        connection.commit()

    winners = {}

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