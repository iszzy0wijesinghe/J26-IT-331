"""Verify approved GeoNex C3 training export integrity."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from apps.c3_workbench.training_approval import (
    EXPORT_ROOT,
    require_training_approval,
)


class TrainingArtifactIntegrityError(ValueError):
    """Raised when an approved training export fails verification."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def verify_training_artifacts(
    dataset_id: str,
) -> dict:
    """Verify approval, manifest, and training/validation files."""

    approval = require_training_approval(dataset_id)

    dataset_dir = EXPORT_ROOT / dataset_id

    manifest_path = dataset_dir / "manifest.json"

    if not manifest_path.is_file():
        raise TrainingArtifactIntegrityError(
            "Training manifest is missing."
        )

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    if manifest.get("dataset_id") != dataset_id:
        raise TrainingArtifactIntegrityError(
            "Manifest dataset identity mismatch."
        )

    if manifest.get("export_version") != "c3-fixed-horizon-v2":
        raise TrainingArtifactIntegrityError(
            "Unsupported training export version."
        )

    if manifest.get("split_policy") != "EPISODE_DISJOINT":
        raise TrainingArtifactIntegrityError(
            "Unsupported dataset split policy."
        )

    if manifest.get("training_approved") is not False:
        raise TrainingArtifactIntegrityError(
            "Export manifest approval metadata was modified."
        )

    verified_files = {}

    for split in ("train", "validation"):
        metadata = manifest.get("files", {}).get(split)

        if not isinstance(metadata, dict):
            raise TrainingArtifactIntegrityError(
                f"Missing {split} file metadata."
            )

        expected_filename = f"{split}.jsonl.gz"

        if metadata.get("filename") != expected_filename:
            raise TrainingArtifactIntegrityError(
                f"Unexpected {split} filename."
            )

        path = dataset_dir / expected_filename

        if not path.is_file():
            raise TrainingArtifactIntegrityError(
                f"Missing training file: {path}"
            )

        expected_hash = metadata.get("sha256")

        actual_hash = sha256_file(path)

        if actual_hash != expected_hash:
            raise TrainingArtifactIntegrityError(
                f"{split} checksum mismatch."
            )

        verified_files[split] = {
            "filename": expected_filename,
            "sha256": actual_hash,
            "examples": metadata.get("examples"),
        }

    return {
        "dataset_id": dataset_id,
        "approval_status": approval["approval_status"],
        "research_profile": approval["research_profile"],
        "dataset_dir": str(dataset_dir),
        "manifest_sha256": sha256_file(manifest_path),
        "files": verified_files,
        "integrity_status": "VERIFIED",
    }