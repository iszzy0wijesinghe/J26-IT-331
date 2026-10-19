"""Persistent dataset training approval for GeoNex C3."""

from __future__ import annotations

import hashlib
from pathlib import Path

from apps.c3_workbench.golden_db import (
    get_connection,
    initialize_golden_database,
    utc_now,
)
from apps.c3_workbench.golden_training_readiness import (
    assess_training_readiness,
)


EXPORT_ROOT = Path(
    "data/workbench/c3/training_datasets"
)

APPROVED_PROFILE = "SYNTHETIC_RESEARCH"


def initialize_training_approvals() -> None:
    initialize_golden_database()

    with get_connection() as connection:
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
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def get_training_approval(dataset_id: str) -> dict:
    initialize_training_approvals()

    with get_connection() as connection:
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
) -> dict:
    """Approve an explicitly identified synthetic research dataset."""

    initialize_training_approvals()

    if not approved_by.strip():
        raise ValueError("Approver is required.")

    if not reason.strip():
        raise ValueError("Approval reason is required.")

    readiness = assess_training_readiness(dataset_id)

    if not readiness["temporal_ready"]:
        raise ValueError(
            "Dataset is not temporally ready."
        )

    with get_connection() as connection:
        dataset = connection.execute(
            """
            SELECT filename, file_hash, quality_status
            FROM c3_datasets
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        ).fetchone()

    if dataset is None:
        raise ValueError("Dataset not found.")

    # Initial research-only allowlist.
    # Filename alone is not sufficient evidence of provenance.
    expected_hash = (
        "16187c5d5c5d659db20d26ba98aaccf"
        "bac8675074481cc68d268a984e7aa577c"
    )

    if (
        dataset["filename"]
        != "geonex_c3_synthetic_observations_v2.csv"
        or dataset["file_hash"] != expected_hash
        or dataset["quality_status"] != "GOLDEN"
    ):
        raise ValueError(
            "Dataset is not an approved synthetic "
            "research source."
        )

    manifest_path = (
        EXPORT_ROOT / dataset_id / "manifest.json"
    )

    if not manifest_path.is_file():
        raise ValueError(
            "Training export manifest does not exist."
        )

    manifest_sha256 = calculate_sha256(manifest_path)

    now = utc_now()

    with get_connection() as connection:
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
) -> dict:
    initialize_training_approvals()

    with get_connection() as connection:
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


def require_training_approval(dataset_id: str) -> dict:
    """Verify approval and exported-manifest integrity."""

    approval = get_training_approval(dataset_id)

    if approval["approval_status"] != "APPROVED":
        raise ValueError(
            "Dataset is not approved for training."
        )

    manifest_path = (
        EXPORT_ROOT / dataset_id / "manifest.json"
    )

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