"""
GeoNex C3 Model Review API.

Phase 1.4.9 — Dedicated Training Database Cutover.

Read-only endpoints:
    GET /research/models/candidates
    GET /research/models/active
    GET /research/models/history

Database ownership:
    c3_model_versions             -> Training Database
    c3_active_model_assignments   -> Training Database
    c3_model_activation_history   -> Training Database

This module does not:
    - Access the Golden Database.
    - Register model candidates.
    - Activate models.
    - Roll back models.
    - Execute training.
"""

from __future__ import annotations

import sqlite3

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from apps.c3_workbench.training_database import (
    connect_training_db,
    get_training_db_path,
)

from apps.c3_workbench.model_activation import (
    ModelActivationError,
    list_active_model_assignments,
    list_model_activation_history,
)


router = APIRouter(
    prefix="/research/models",
    tags=["C3 Model Review"],
)


def get_model_review_connection() -> sqlite3.Connection:
    """
    Connect exclusively to the dedicated Training Database.

    Refuse to silently create a new empty database if
    the expected Training Database is missing.
    """

    database_path = get_training_db_path()

    if not database_path.is_file():
        raise RuntimeError(
            "GeoNex C3 Training Database does not exist: "
            f"{database_path}"
        )

    connection = connect_training_db()

    connection.row_factory = sqlite3.Row

    required_tables = {
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

        raise RuntimeError(
            "Training Database is missing required tables: "
            + ", ".join(sorted(missing_tables))
        )

    return connection


@router.get("/candidates")
def candidates(
    dataset_id: str | None = None,
    job_id: str | None = None,
):
    """
    List registered model versions.

    Optional filters:
        dataset_id
        job_id

    Results are ordered by:
        forecast horizon,
        validation MAE,
        validation RMSE,
        model name.

    No model activation occurs.
    """

    sql = """
        SELECT
            model_version_id,
            job_id,
            dataset_id,
            model_name,
            horizon_minutes,
            validation_mae,
            validation_rmse,
            status,
            created_at

        FROM c3_model_versions

        WHERE 1 = 1
    """

    params = []

    if dataset_id:
        sql += " AND dataset_id = ?"
        params.append(dataset_id)

    if job_id:
        sql += " AND job_id = ?"
        params.append(job_id)

    sql += """
        ORDER BY
            horizon_minutes,
            validation_mae,
            validation_rmse,
            model_name
    """

    try:
        with get_model_review_connection() as connection:
            rows = [
                dict(row)
                for row in connection.execute(
                    sql,
                    params,
                ).fetchall()
            ]

    except (sqlite3.Error, RuntimeError) as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Training Database model review "
                "is temporarily unavailable."
            ),
        ) from error

    return {
        "candidates": rows,
        "total": len(rows),
        "selection_basis": "validation metrics only",
    }


@router.get("/active")
def active():
    """
    Return currently active research model assignments.

    This endpoint is read-only.

    Active research assignment does not constitute
    authorization for field deployment.
    """

    try:
        assignments = list_active_model_assignments()

    except ModelActivationError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    return {
        "assignments": assignments,
    }


@router.get("/history")
def history(
    horizon_minutes: int | None = Query(
        default=None,
    ),
):
    """
    Return model activation and rollback history.

    Optional filter:
        horizon_minutes

    No activation or rollback occurs.
    """

    try:
        events = list_model_activation_history(
            horizon_minutes
        )

    except ModelActivationError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    return {
        "events": events,
    }