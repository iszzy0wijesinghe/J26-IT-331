"""Integration tests for C3 training authorization and artifact integrity."""

import hashlib
import json
import sqlite3

import pytest

from apps.c3_workbench import (
    golden_db,
    training_approval,
    training_artifact_integrity,
    training_queue,
    training_worker,
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def authorization_environment(tmp_path, monkeypatch):
    """Create isolated database, exports, and readiness assessment."""

    database_path = tmp_path / "golden.sqlite3"
    export_root = tmp_path / "training_datasets"

    monkeypatch.setattr(
        golden_db,
        "DATABASE_PATH",
        database_path,
    )

    monkeypatch.setattr(
        training_approval,
        "EXPORT_ROOT",
        export_root,
    )

    monkeypatch.setattr(
        training_artifact_integrity,
        "EXPORT_ROOT",
        export_root,
    )

    monkeypatch.setattr(
        training_approval,
        "assess_training_readiness",
        lambda dataset_id: {"temporal_ready": True},
    )

    golden_db.initialize_golden_database()
    training_approval.initialize_training_approvals()

    return {
        "database_path": database_path,
        "export_root": export_root,
    }


def create_dataset(environment, dataset_id):
    """Create a Golden dataset and valid training export."""

    database_path = environment["database_path"]
    export_root = environment["export_root"]

    filename = f"{dataset_id}.csv"
    source_hash = hashlib.sha256(dataset_id.encode()).hexdigest()

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO c3_datasets (
                dataset_id,
                filename,
                file_hash,
                uploaded_at,
                total_rows,
                device_count,
                episode_count,
                quality_status,
                pipeline_status,
                validation_report,
                source_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                filename,
                source_hash,
                "2026-10-19T00:00:00+00:00",
                100,
                1,
                1,
                "GOLDEN",
                "READY",
                "{}",
                "CSV",
            ),
        )

    dataset_dir = export_root / dataset_id
    dataset_dir.mkdir(parents=True)

    files = {}

    for split in ("train", "validation"):
        path = dataset_dir / f"{split}.jsonl.gz"

        # Integrity tests only: contents are not consumed by a trainer.
        path.write_bytes(f"test-{split}-{dataset_id}".encode())

        files[split] = {
            "filename": path.name,
            "sha256": sha256(path),
            "examples": 1,
        }

    manifest = {
        "dataset_id": dataset_id,
        "source_filename": filename,
        "source_file_sha256": source_hash,
        "source_provenance_verified": False,
        "training_approved": False,
        "export_version": "c3-fixed-horizon-v2",
        "split_policy": "EPISODE_DISJOINT",
        "files": files,
    }

    manifest_path = dataset_dir / "manifest.json"

    manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    return dataset_dir


def approve(dataset_id):
    return training_approval.approve_synthetic_dataset(
        dataset_id,
        approved_by="C3 Integration Test",
        reason="Controlled synthetic research experiment",
    )


def test_approved_dataset_passes_integrity_verification(
    authorization_environment,
):
    dataset_id = "approved_001"

    create_dataset(authorization_environment, dataset_id)
    approve(dataset_id)

    result = training_artifact_integrity.verify_training_artifacts(
        dataset_id
    )

    assert result["approval_status"] == "APPROVED"
    assert result["integrity_status"] == "VERIFIED"
    assert set(result["files"]) == {"train", "validation"}


def test_unapproved_dataset_is_rejected(
    authorization_environment,
):
    dataset_id = "unapproved_001"

    create_dataset(authorization_environment, dataset_id)

    with pytest.raises(ValueError, match="not approved"):
        training_artifact_integrity.verify_training_artifacts(
            dataset_id
        )


def test_revoked_approval_is_rejected(
    authorization_environment,
):
    dataset_id = "revoked_001"

    create_dataset(authorization_environment, dataset_id)
    approve(dataset_id)

    training_approval.revoke_training_approval(dataset_id)

    with pytest.raises(ValueError, match="not approved"):
        training_artifact_integrity.verify_training_artifacts(
            dataset_id
        )


def test_modified_manifest_is_rejected(
    authorization_environment,
):
    dataset_id = "manifest_modified_001"

    dataset_dir = create_dataset(
        authorization_environment,
        dataset_id,
    )

    approve(dataset_id)

    manifest_path = dataset_dir / "manifest.json"

    manifest = json.loads(manifest_path.read_text())
    manifest["split_policy"] = "MODIFIED_POLICY"

    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(ValueError, match="manifest changed"):
        training_artifact_integrity.verify_training_artifacts(
            dataset_id
        )


@pytest.mark.parametrize("split", ["train", "validation"])
def test_modified_export_file_is_rejected(
    authorization_environment,
    split,
):
    dataset_id = f"modified_{split}_001"

    dataset_dir = create_dataset(
        authorization_environment,
        dataset_id,
    )

    approve(dataset_id)

    file_path = dataset_dir / f"{split}.jsonl.gz"

    with file_path.open("ab") as file:
        file.write(b"tampered")

    with pytest.raises(
        training_artifact_integrity.TrainingArtifactIntegrityError,
        match="checksum mismatch",
    ):
        training_artifact_integrity.verify_training_artifacts(
            dataset_id
        )


def test_invalid_split_policy_is_rejected(
    authorization_environment,
):
    dataset_id = "invalid_policy_001"

    dataset_dir = create_dataset(
        authorization_environment,
        dataset_id,
    )

    manifest_path = dataset_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    manifest["split_policy"] = "RANDOM_SPLIT"

    manifest_path.write_text(json.dumps(manifest))

    # Approval currently checks source identity/provenance, not split policy.
    approve(dataset_id)

    with pytest.raises(
        training_artifact_integrity.TrainingArtifactIntegrityError,
        match="split policy",
    ):
        training_artifact_integrity.verify_training_artifacts(
            dataset_id
        )


def test_worker_rejects_unapproved_job_before_claim(
    authorization_environment,
):
    dataset_id = "worker_unapproved_001"

    create_dataset(authorization_environment, dataset_id)

    # Queue is a persistence primitive; worker enforces authorization.
    job = training_queue.enqueue_training_job(dataset_id)

    with pytest.raises(ValueError, match="not approved"):
        training_worker.execute_training_job(job["job_id"])

    stored = training_queue.get_training_job(job["job_id"])

    assert stored["status"] == "QUEUED"
    assert stored["started_at"] is None