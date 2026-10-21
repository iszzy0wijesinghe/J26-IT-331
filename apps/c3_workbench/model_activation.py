"""
GeoNex C3 controlled model activation infrastructure.

Phase 1.5.3 — Dedicated Training Database Cutover.

Responsibilities
----------------
1. Maintain active model assignments.
2. Maintain activation and rollback history.
3. Validate model eligibility.
4. Verify approved training artifacts.
5. Preserve optimistic concurrency protection.
6. Prevent implicit operational deployment.

Database ownership
------------------
c3_model_versions             -> Training Database
c3_training_jobs              -> Training Database
c3_active_model_assignments   -> Training Database
c3_model_activation_history   -> Training Database

Research activation does not authorize operational
landslide warning deployment.
"""

from __future__ import annotations

import sqlite3
import uuid

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apps.c3_workbench.training_database import (
    connect_training_db,
    get_training_db_path,
)

from apps.c3_workbench.model_registry import (
    collect_model_candidates,
)

from apps.c3_workbench.training_artifact_integrity import (
    verify_training_artifacts,
)


HORIZONS = (15, 30, 60)

RESEARCH_PROFILE = "SYNTHETIC_RESEARCH"


class ModelActivationError(ValueError):
    """Raised when model activation requirements are not satisfied."""


def utc_now() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(UTC).isoformat()


def get_activation_connection() -> sqlite3.Connection:
    """
    Connect exclusively to the dedicated Training Database.

    Required migrated tables must already exist.
    """

    database_path = get_training_db_path()

    if not database_path.is_file():
        raise ModelActivationError(
            "GeoNex C3 Training Database does not exist: "
            f"{database_path}"
        )

    connection = connect_training_db()
    connection.row_factory = sqlite3.Row

    required_tables = {
        "c3_training_jobs",
        "c3_model_versions",
        "c3_training_approvals",
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

    missing = required_tables - existing_tables

    if missing:
        connection.close()

        raise ModelActivationError(
            "Training Database is missing required tables: "
            + ", ".join(sorted(missing))
        )

    return connection


def initialize_model_activation() -> None:
    """
    Ensure activation tables exist in the Training Database.

    This operation is safe to repeat.

    Existing assignments and activation history are preserved.
    """

    with get_activation_connection() as connection:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS c3_active_model_assignments (
                horizon_minutes INTEGER PRIMARY KEY,
                model_version_id TEXT NOT NULL,
                activated_at TEXT NOT NULL,
                activated_by TEXT NOT NULL,
                activation_reason TEXT NOT NULL,

                FOREIGN KEY (model_version_id)
                    REFERENCES c3_model_versions(model_version_id),

                CHECK (horizon_minutes IN (15, 30, 60))
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS c3_model_activation_history (
                activation_id TEXT PRIMARY KEY,
                horizon_minutes INTEGER NOT NULL,
                previous_model_version_id TEXT,
                new_model_version_id TEXT NOT NULL,
                action TEXT NOT NULL,
                activated_at TEXT NOT NULL,
                activated_by TEXT NOT NULL,
                activation_reason TEXT NOT NULL,

                CHECK (horizon_minutes IN (15, 30, 60)),
                CHECK (action IN ('ACTIVATE', 'ROLLBACK')),

                FOREIGN KEY (previous_model_version_id)
                    REFERENCES c3_model_versions(model_version_id),

                FOREIGN KEY (new_model_version_id)
                    REFERENCES c3_model_versions(model_version_id)
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_c3_model_activation_history_horizon

            ON c3_model_activation_history (
                horizon_minutes,
                activated_at
            )
            """
        )


def list_active_model_assignments() -> list[dict[str, Any]]:
    """Return the currently assigned research models."""

    initialize_model_activation()

    with get_activation_connection() as connection:

        rows = connection.execute(
            """
            SELECT
                a.horizon_minutes,
                a.model_version_id,
                a.activated_at,
                a.activated_by,
                a.activation_reason,

                m.model_name,
                m.dataset_id,
                m.job_id,
                m.checkpoint_path,
                m.validation_mae,
                m.validation_rmse,
                m.status AS model_status

            FROM c3_active_model_assignments a

            INNER JOIN c3_model_versions m
                ON m.model_version_id = a.model_version_id

            ORDER BY a.horizon_minutes
            """
        ).fetchall()

    return [dict(row) for row in rows]


def list_model_activation_history(
    horizon_minutes: int | None = None,
) -> list[dict[str, Any]]:
    """Return research activation and rollback history."""

    initialize_model_activation()

    if (
        horizon_minutes is not None
        and horizon_minutes not in HORIZONS
    ):
        raise ModelActivationError(
            f"Unsupported forecast horizon: {horizon_minutes}"
        )

    query = """
        SELECT *
        FROM c3_model_activation_history
    """

    parameters: tuple = ()

    if horizon_minutes is not None:
        query += " WHERE horizon_minutes = ?"
        parameters = (horizon_minutes,)

    query += (
        " ORDER BY activated_at DESC, activation_id DESC"
    )

    with get_activation_connection() as connection:

        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

    return [dict(row) for row in rows]


def _validate_model_for_activation(
    connection: sqlite3.Connection,
    model_version_id: str,
    horizon_minutes: int,
) -> dict[str, Any]:
    """
    Verify that a model is eligible for research activation.

    Must be called within the activation transaction.
    """

    row = connection.execute(
        """
        SELECT
            m.model_version_id,
            m.job_id,
            m.dataset_id,
            m.model_name,
            m.horizon_minutes,
            m.checkpoint_path,
            m.validation_mae,
            m.validation_rmse,
            m.status,

            j.status AS job_status,

            a.approval_status,
            a.research_profile

        FROM c3_model_versions m

        INNER JOIN c3_training_jobs j
            ON j.job_id = m.job_id

        INNER JOIN c3_training_approvals a
            ON a.dataset_id = m.dataset_id

        WHERE m.model_version_id = ?
        """,
        (model_version_id,),
    ).fetchone()

    if row is None:
        raise ModelActivationError(
            f"Unknown or unapproved model version: {model_version_id}"
        )

    model = dict(row)

    if model["horizon_minutes"] != horizon_minutes:
        raise ModelActivationError(
            "Requested horizon does not match model horizon."
        )

    if model["job_status"] != "COMPLETED":
        raise ModelActivationError(
            "Only models from completed training jobs "
            "can be activated."
        )

    if model["status"] not in (
        "CANDIDATE",
        "ACTIVE",
        "INACTIVE",
    ):
        raise ModelActivationError(
            "Model status does not allow activation: "
            f"{model['status']}"
        )

    if model["approval_status"] != "APPROVED":
        raise ModelActivationError(
            "Dataset approval is not active."
        )

    if model["research_profile"] != RESEARCH_PROFILE:
        raise ModelActivationError(
            "Only approved synthetic research models "
            "are eligible for this research activation workflow."
        )

    # Revalidate approved training export and source restrictions.
    verification = verify_training_artifacts(
        model["dataset_id"]
    )

    if verification["integrity_status"] != "VERIFIED":
        raise ModelActivationError(
            "Training dataset integrity verification failed."
        )

    # Revalidate all expected model artifacts and metrics.
    candidates = collect_model_candidates(
        job_id=model["job_id"],
        dataset_id=model["dataset_id"],
    )

    expected = next(
        (
            candidate
            for candidate in candidates
            if candidate["model_name"] == model["model_name"]
            and candidate["horizon_minutes"] == horizon_minutes
        ),
        None,
    )

    if expected is None:
        raise ModelActivationError(
            "Registered model is missing from "
            "validated training artifacts."
        )

    if model["checkpoint_path"] != expected["checkpoint_path"]:
        raise ModelActivationError(
            "Registered checkpoint path does not match "
            "validated artifact."
        )

    if (
        model["validation_mae"] != expected["validation_mae"]
        or model["validation_rmse"] != expected["validation_rmse"]
    ):
        raise ModelActivationError(
            "Registered validation metrics do not match "
            "training artifacts."
        )

    checkpoint = Path(
        model["checkpoint_path"]
    )

    if (
        not checkpoint.is_file()
        or checkpoint.stat().st_size == 0
    ):
        raise ModelActivationError(
            "Model checkpoint is missing or empty."
        )

    return model


def activate_model(
    model_version_id: str,
    horizon_minutes: int,
    activated_by: str,
    reason: str,
    expected_current_model_version_id: str | None = None,
) -> dict[str, Any]:
    """
    Activate a model for one research forecasting horizon.

    expected_current_model_version_id provides optimistic
    concurrency protection.

    This does not authorize operational deployment.
    """

    initialize_model_activation()

    if horizon_minutes not in HORIZONS:
        raise ModelActivationError(
            f"Unsupported horizon: {horizon_minutes}"
        )

    if not isinstance(activated_by, str) or not activated_by.strip():
        raise ModelActivationError(
            "activated_by must not be empty."
        )

    if not isinstance(reason, str) or not reason.strip():
        raise ModelActivationError(
            "Activation reason must not be empty."
        )

    with get_activation_connection() as connection:

        connection.execute(
            "BEGIN IMMEDIATE"
        )

        model = _validate_model_for_activation(
            connection,
            model_version_id,
            horizon_minutes,
        )

        current = connection.execute(
            """
            SELECT model_version_id
            FROM c3_active_model_assignments
            WHERE horizon_minutes = ?
            """,
            (horizon_minutes,),
        ).fetchone()

        previous_model_version_id = (
            current["model_version_id"]
            if current is not None
            else None
        )

        if (
            previous_model_version_id
            != expected_current_model_version_id
        ):
            raise ModelActivationError(
                "Active model changed since the request "
                "was prepared. Refresh before activating."
            )

        if previous_model_version_id == model_version_id:
            raise ModelActivationError(
                "This model is already active for "
                "the selected horizon."
            )

        activated_at = utc_now()

        activation_id = (
            f"c3activation_{uuid.uuid4().hex[:16]}"
        )

        connection.execute(
            """
            INSERT INTO c3_active_model_assignments (
                horizon_minutes,
                model_version_id,
                activated_at,
                activated_by,
                activation_reason
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(horizon_minutes)
            DO UPDATE SET
                model_version_id = excluded.model_version_id,
                activated_at = excluded.activated_at,
                activated_by = excluded.activated_by,
                activation_reason = excluded.activation_reason
            """,
            (
                horizon_minutes,
                model_version_id,
                activated_at,
                activated_by,
                reason,
            ),
        )

        connection.execute(
            """
            INSERT INTO c3_model_activation_history (
                activation_id,
                horizon_minutes,
                previous_model_version_id,
                new_model_version_id,
                action,
                activated_at,
                activated_by,
                activation_reason
            )
            VALUES (?, ?, ?, ?, 'ACTIVATE', ?, ?, ?)
            """,
            (
                activation_id,
                horizon_minutes,
                previous_model_version_id,
                model_version_id,
                activated_at,
                activated_by,
                reason,
            ),
        )

        connection.commit()

    return {
        "activation_id": activation_id,
        "horizon_minutes": horizon_minutes,
        "previous_model_version_id": previous_model_version_id,
        "active_model_version_id": model_version_id,
        "model_name": model["model_name"],
        "activated_at": activated_at,
        "action": "ACTIVATE",
    }


def rollback_model(
    horizon_minutes: int,
    activated_by: str,
    reason: str,
    expected_current_model_version_id: str,
) -> dict[str, Any]:
    """
    Roll back to the model replaced by the latest event.

    The current assignment must match the expected model.
    """

    initialize_model_activation()

    if horizon_minutes not in HORIZONS:
        raise ModelActivationError(
            f"Unsupported horizon: {horizon_minutes}"
        )

    if not isinstance(activated_by, str) or not activated_by.strip():
        raise ModelActivationError(
            "Rollback actor must not be empty."
        )

    if not isinstance(reason, str) or not reason.strip():
        raise ModelActivationError(
            "Rollback reason must not be empty."
        )

    with get_activation_connection() as connection:

        connection.execute(
            "BEGIN IMMEDIATE"
        )

        current = connection.execute(
            """
            SELECT model_version_id
            FROM c3_active_model_assignments
            WHERE horizon_minutes = ?
            """,
            (horizon_minutes,),
        ).fetchone()

        if current is None:
            raise ModelActivationError(
                "No active model exists for this horizon."
            )

        current_model_id = current["model_version_id"]

        if (
            current_model_id
            != expected_current_model_version_id
        ):
            raise ModelActivationError(
                "Active model changed before rollback."
            )

        latest = connection.execute(
            """
            SELECT
                previous_model_version_id,
                new_model_version_id

            FROM c3_model_activation_history

            WHERE horizon_minutes = ?

            ORDER BY activated_at DESC, activation_id DESC

            LIMIT 1
            """,
            (horizon_minutes,),
        ).fetchone()

        if latest is None:
            raise ModelActivationError(
                "No activation history exists for rollback."
            )

        if (
            latest["new_model_version_id"]
            != current_model_id
        ):
            raise ModelActivationError(
                "Activation history does not match "
                "current assignment."
            )

        previous_model_id = latest[
            "previous_model_version_id"
        ]

        if previous_model_id is None:
            raise ModelActivationError(
                "No previously active model is available "
                "for rollback."
            )

        model = _validate_model_for_activation(
            connection,
            previous_model_id,
            horizon_minutes,
        )

        activated_at = utc_now()

        activation_id = (
            f"c3activation_{uuid.uuid4().hex[:16]}"
        )

        connection.execute(
            """
            UPDATE c3_active_model_assignments
            SET
                model_version_id = ?,
                activated_at = ?,
                activated_by = ?,
                activation_reason = ?
            WHERE horizon_minutes = ?
            """,
            (
                previous_model_id,
                activated_at,
                activated_by,
                reason,
                horizon_minutes,
            ),
        )

        connection.execute(
            """
            INSERT INTO c3_model_activation_history (
                activation_id,
                horizon_minutes,
                previous_model_version_id,
                new_model_version_id,
                action,
                activated_at,
                activated_by,
                activation_reason
            )
            VALUES (?, ?, ?, ?, 'ROLLBACK', ?, ?, ?)
            """,
            (
                activation_id,
                horizon_minutes,
                current_model_id,
                previous_model_id,
                activated_at,
                activated_by,
                reason,
            ),
        )

        connection.commit()

    return {
        "activation_id": activation_id,
        "horizon_minutes": horizon_minutes,
        "previous_model_version_id": current_model_id,
        "active_model_version_id": previous_model_id,
        "model_name": model["model_name"],
        "activated_at": activated_at,
        "action": "ROLLBACK",
    }