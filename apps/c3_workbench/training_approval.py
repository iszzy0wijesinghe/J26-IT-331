"""
Persistent dataset training approval for GeoNex C3.

Phase 1.5.1 — Dedicated Training Database Cutover

Database responsibilities
-------------------------
Golden Database:
    - Operational sensor observations
    - Temporal readiness assessment
    - Source data quality validation

Training Database:
    - c3_datasets (migrated training dataset metadata)
    - c3_training_approvals
    - Training jobs and model metadata

Filesystem:
    - Training export manifest
    - Training and validation datasets

Synthetic research approval never authorizes operational
deployment of a trained model.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apps.c3_workbench.training_database import (
    connect_training_db,
    get_training_db_path,
)

from apps.c3_workbench.golden_training_readiness import (
    assess_training_readiness,
)


# Preserve existing storage paths during Phase 1.
# Dataset relocation is handled separately in Phase 1.6.
EXPORT_ROOT = Path(
    "data/workbench/c3/training_datasets"
)

APPROVED_PROFILE = "SYNTHETIC_RESEARCH"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def get_approval_connection() -> sqlite3.Connection:
    """
    Connect to the migrated Training Database.

    The database and its migrated dataset table must exist.
    """

    database_path = get_training_db_path()

    if not database_path.is_file():
        raise RuntimeError(
            "GeoNex C3 Training Database does not exist: "
            f"{database_path}"
        )

    connection = connect_training_db()
    connection.row_factory = sqlite3.Row

    dataset_table = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'c3_datasets'
        """
    ).fetchone()

    if dataset_table is None:
        connection.close()

        raise RuntimeError(
            "Training Database is missing the migrated "
            "c3_datasets table."
        )

    return connection


def initialize_training_approvals() -> None:
    """
    Ensure the training approval table exists in the
    dedicated Training Database.

    This function never modifies the Golden Database.
    """

    with get_approval_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS c3_training_approvals (
                dataset_id TEXT PRIMARY KEY,
                approval_status TEXT NOT NULL,
                research_profile TEXT NOT NULL,
                approved_by TEXT,
                approval_reason TEXT,
                approved_at TEXT,
                revoked_at TEXT,
                export_manifest_sha256 TEXT NOT NULL,
                FOREIGN KEY (dataset_id)
                    REFERENCES c3_datasets(dataset_id)
            )
            """
        )


def calculate_sha256(path: Path) -> str:
    """Calculate a file's SHA-256 checksum."""

    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def resolve_export_directory(dataset_id: str) -> Path:
    """
    Resolve an export directory without allowing
    dataset path traversal.
    """

    if (
        not isinstance(dataset_id, str)
        or not dataset_id
        or dataset_id in {".", ".."}
        or "/" in dataset_id
        or "\\" in dataset_id
        or "\x00" in dataset_id
    ):
        raise ValueError(
            "Invalid training dataset ID."
        )

    root = EXPORT_ROOT.resolve()
    dataset_dir = (root / dataset_id).resolve()

    if dataset_dir.parent != root:
        raise ValueError(
            "Training dataset directory escapes export root."
        )

    return dataset_dir


def get_training_approval(
    dataset_id: str,
) -> dict[str, Any]:
    """
    Read training approval exclusively from
    the dedicated Training Database.
    """

    initialize_training_approvals()

    with get_approval_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM c3_training_approvals
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        ).fetchone()

    if row is None:
        return {
            "dataset_id": dataset_id,
            "approval_status": "NOT_APPROVED",
        }

    return dict(row)


def approve_synthetic_dataset(
    dataset_id: str,
    *,
    approved_by: str,
    reason: str,
) -> dict[str, Any]:
    """
    Approve an explicitly identified synthetic research dataset.

    Approval is limited to research training and evaluation.
    It does not authorize operational model deployment.
    """

    initialize_training_approvals()

    if not isinstance(approved_by, str) or not approved_by.strip():
        raise ValueError(
            "Approver is required."
        )

    if not isinstance(reason, str) or not reason.strip():
        raise ValueError(
            "Approval reason is required."
        )

    dataset_dir = resolve_export_directory(dataset_id)

    # Temporal readiness is assessed against the Golden
    # operational data and its existing readiness pipeline.
    readiness = assess_training_readiness(dataset_id)

    if not readiness["temporal_ready"]:
        raise ValueError(
            "Dataset is not temporally ready."
        )

    # Dataset metadata was migrated to the Training Database.
    with get_approval_connection() as connection:
        dataset = connection.execute(
            """
            SELECT filename, file_hash, quality_status
            FROM c3_datasets
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        ).fetchone()

    if dataset is None:
        raise ValueError(
            "Training dataset metadata not found."
        )

    if dataset["quality_status"] != "GOLDEN":
        raise ValueError(
            "Dataset must have GOLDEN quality status."
        )

    manifest_path = dataset_dir / "manifest.json"

    if not manifest_path.is_file():
        raise ValueError(
            "Training export manifest does not exist. "
            "Prepare the export first."
        )

    try:
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )

    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(
            "Training export manifest is invalid."
        ) from error

    if not isinstance(manifest, dict):
        raise ValueError(
            "Training export manifest must be a JSON object."
        )

    if (
        manifest.get("dataset_id") != dataset_id
        or manifest.get("source_file_sha256") != dataset["file_hash"]
        or manifest.get("source_filename") != dataset["filename"]
        or manifest.get("source_provenance_verified") is not False
        or manifest.get("training_approved") is not False
    ):
        raise ValueError(
            "Export manifest/source mismatch or "
            "unsupported provenance flags."
        )

    manifest_sha256 = calculate_sha256(manifest_path)
    now = utc_now()

    # Approval is written only to the Training Database.
    with get_approval_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        connection.execute(
            """
            INSERT INTO c3_training_approvals (
                dataset_id,
                approval_status,
                research_profile,
                approved_by,
                approval_reason,
                approved_at,
                revoked_at,
                export_manifest_sha256
            )
            VALUES (?, ?, ?, ?, ?, ?, NULL, ?)

            ON CONFLICT(dataset_id)
            DO UPDATE SET
                approval_status = excluded.approval_status,
                research_profile = excluded.research_profile,
                approved_by = excluded.approved_by,
                approval_reason = excluded.approval_reason,
                approved_at = excluded.approved_at,
                revoked_at = NULL,
                export_manifest_sha256 =
                    excluded.export_manifest_sha256
            """,
            (
                dataset_id,
                "APPROVED",
                APPROVED_PROFILE,
                approved_by.strip(),
                reason.strip(),
                now,
                manifest_sha256,
            ),
        )

    return get_training_approval(dataset_id)


def revoke_training_approval(
    dataset_id: str,
) -> dict[str, Any]:
    """
    Revoke an existing research training approval.

    Revocation is stored exclusively in the Training Database.
    """

    initialize_training_approvals()

    with get_approval_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        cursor = connection.execute(
            """
            UPDATE c3_training_approvals
            SET
                approval_status = 'REVOKED',
                revoked_at = ?
            WHERE dataset_id = ?
              AND approval_status = 'APPROVED'
            """,
            (
                utc_now(),
                dataset_id,
            ),
        )

        if cursor.rowcount == 0:
            raise ValueError(
                "No active approval exists."
            )

    return get_training_approval(dataset_id)


def require_training_approval(
    dataset_id: str,
) -> dict[str, Any]:
    """
    Require valid research training approval.

    Checks:
        1. Training Database approval status.
        2. Approved manifest SHA-256.
        3. Golden temporal readiness.

    This does not authorize operational deployment.
    """

    approval = get_training_approval(dataset_id)

    if approval["approval_status"] != "APPROVED":
        raise ValueError(
            "Dataset is not approved for training."
        )

    dataset_dir = resolve_export_directory(dataset_id)

    manifest_path = dataset_dir / "manifest.json"

    if not manifest_path.is_file():
        raise ValueError(
            "Approved export manifest is missing."
        )

    actual_hash = calculate_sha256(manifest_path)

    if actual_hash != approval["export_manifest_sha256"]:
        raise ValueError(
            "Training export manifest changed "
            "after approval."
        )

    readiness = assess_training_readiness(dataset_id)

    if not readiness["temporal_ready"]:
        raise ValueError(
            "Dataset no longer passes temporal readiness."
        )

    return approval