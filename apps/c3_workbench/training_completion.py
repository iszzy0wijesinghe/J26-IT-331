"""Finalize a GeoNex C3 training job after candidate registration."""

from __future__ import annotations

from apps.c3_workbench.golden_db import (
    get_connection,
    initialize_golden_database,
    utc_now,
)
from apps.c3_workbench.training_artifact_integrity import (
    verify_training_artifacts,
)
from apps.c3_workbench.model_registry import (
    collect_model_candidates,
)


class TrainingCompletionError(ValueError):
    pass


def complete_training_job(
    job_id: str,
    dataset_id: str,
) -> dict:
    """
    Complete a training job only when all expected model
    candidates have been validated and registered.

    Does not activate any model.
    """

    initialize_golden_database()

    # Recheck approval and exported training-data integrity.
    verify_training_artifacts(dataset_id)

    # Recheck the 18 expected model artifacts and metrics.
    expected_candidates = collect_model_candidates(
        job_id=job_id,
        dataset_id=dataset_id,
    )

    expected_keys = {
        (
            candidate["model_name"],
            candidate["horizon_minutes"],
        )
        for candidate in expected_candidates
    }

    if len(expected_keys) != 18:
        raise TrainingCompletionError(
            "Expected 18 unique model/horizon combinations."
        )

    with get_connection() as connection:
        # Acquire a write transaction before reading job state.
        connection.execute("BEGIN IMMEDIATE")

        job = connection.execute(
            """
            SELECT job_id, dataset_id, status
            FROM c3_training_jobs
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()

        if job is None:
            raise TrainingCompletionError(
                f"Unknown training job: {job_id}"
            )

        if job["dataset_id"] != dataset_id:
            raise TrainingCompletionError(
                "Training job dataset mismatch."
            )

        if job["status"] == "COMPLETED":
            raise TrainingCompletionError(
                "Training job is already completed."
            )

        if job["status"] != "EVALUATING":
            raise TrainingCompletionError(
                f"Cannot complete job in status: {job['status']}"
            )

        registered = connection.execute(
            """
            SELECT
                model_name,
                horizon_minutes,
                checkpoint_path,
                validation_mae,
                validation_rmse,
                status
            FROM c3_model_versions
            WHERE job_id = ?
              AND dataset_id = ?
            """,
            (job_id, dataset_id),
        ).fetchall()

        if len(registered) != 18:
            raise TrainingCompletionError(
                f"Expected 18 registered models, found {len(registered)}"
            )

        registered_keys = {
            (
                row["model_name"],
                row["horizon_minutes"],
            )
            for row in registered
        }

        if registered_keys != expected_keys:
            raise TrainingCompletionError(
                "Registered models do not match validated artifacts."
            )

        expected_by_key = {
            (
                candidate["model_name"],
                candidate["horizon_minutes"],
            ): candidate
            for candidate in expected_candidates
        }

        for row in registered:
            if row["status"] != "CANDIDATE":
                raise TrainingCompletionError(
                    "All models must remain CANDIDATE before completion."
                )

            key = (
                row["model_name"],
                row["horizon_minutes"],
            )

            expected = expected_by_key[key]

            if row["checkpoint_path"] != expected["checkpoint_path"]:
                raise TrainingCompletionError(
                    f"Checkpoint path mismatch: {key}"
                )

            if (
                row["validation_mae"] != expected["validation_mae"]
                or row["validation_rmse"] != expected["validation_rmse"]
            ):
                raise TrainingCompletionError(
                    f"Validation metrics mismatch: {key}"
                )

        completed_at = utc_now()

        result = connection.execute(
            """
            UPDATE c3_training_jobs
            SET
                status = 'COMPLETED',
                current_stage = 'CANDIDATES_REGISTERED',
                completed_at = ?,
                error_message = NULL
            WHERE job_id = ?
              AND dataset_id = ?
              AND status = 'EVALUATING'
            """,
            (
                completed_at,
                job_id,
                dataset_id,
            ),
        )

        if result.rowcount != 1:
            raise TrainingCompletionError(
                "Training job completion transition failed."
            )

        connection.commit()

    return {
        "job_id": job_id,
        "dataset_id": dataset_id,
        "status": "COMPLETED",
        "current_stage": "CANDIDATES_REGISTERED",
        "registered_candidates": 18,
        "active_models_changed": False,
        "completed_at": completed_at,
    }