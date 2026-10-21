"""
Verify approved GeoNex C3 training export integrity.

Phase 1 — Dedicated Training Database Architecture

Verification responsibilities
-----------------------------
1. Verify dataset identity.
2. Require an approved training export.
3. Verify the export manifest.
4. Verify manifest integrity against the approval record.
5. Verify training and validation file checksums.
6. Reject unsupported export formats.
7. Prevent dataset path traversal.

Database access is delegated to training_approval.py.
"""

from __future__ import annotations

import hashlib
import json

from pathlib import Path
from typing import Any

from apps.c3_workbench.training_approval import (
    EXPORT_ROOT,
    require_training_approval,
)


class TrainingArtifactIntegrityError(ValueError):
    """Raised when an approved training export fails verification."""


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


def resolve_dataset_directory(
    dataset_id: str,
) -> Path:
    """
    Resolve the dataset export directory safely.

    Dataset identifiers must be simple directory names,
    not absolute paths or relative traversal expressions.
    """

    if not isinstance(dataset_id, str):
        raise TrainingArtifactIntegrityError(
            "Dataset ID must be a string."
        )

    if (
        not dataset_id
        or dataset_id in {".", ".."}
        or "/" in dataset_id
        or "\\" in dataset_id
        or "\x00" in dataset_id
    ):
        raise TrainingArtifactIntegrityError(
            "Invalid training dataset identifier."
        )

    export_root = Path(EXPORT_ROOT).resolve()

    dataset_dir = (
        export_root / dataset_id
    ).resolve()

    if dataset_dir.parent != export_root:
        raise TrainingArtifactIntegrityError(
            "Dataset directory escapes the training export root."
        )

    return dataset_dir


def verify_training_artifacts(
    dataset_id: str,
) -> dict[str, Any]:
    """
    Verify an approved training export.

    Returns verified dataset metadata when all checks pass.

    Raises TrainingArtifactIntegrityError when the export
    fails integrity verification.
    """

    dataset_dir = resolve_dataset_directory(
        dataset_id
    )

    # The approval service must use the dedicated
    # Training Database after its Phase 1 cutover.
    approval = require_training_approval(
        dataset_id
    )

    if not dataset_dir.is_dir():
        raise TrainingArtifactIntegrityError(
            "Approved training dataset directory is missing: "
            f"{dataset_dir}"
        )

    manifest_path = dataset_dir / "manifest.json"

    if not manifest_path.is_file():
        raise TrainingArtifactIntegrityError(
            "Training manifest is missing."
        )

    actual_manifest_hash = sha256_file(
        manifest_path
    )

    # The approved manifest must remain unchanged.
    expected_manifest_hash = approval.get(
        "export_manifest_sha256"
    )

    if not expected_manifest_hash:
        raise TrainingArtifactIntegrityError(
            "Approved manifest checksum is missing "
            "from the training approval record."
        )

    if actual_manifest_hash != expected_manifest_hash:
        raise TrainingArtifactIntegrityError(
            "Training manifest checksum does not match "
            "the approved export."
        )

    try:
        manifest = json.loads(
            manifest_path.read_text(
                encoding="utf-8"
            )
        )

    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise TrainingArtifactIntegrityError(
            "Training manifest is unreadable or invalid."
        ) from error

    if not isinstance(manifest, dict):
        raise TrainingArtifactIntegrityError(
            "Training manifest must be a JSON object."
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

    files_metadata = manifest.get("files")

    if not isinstance(files_metadata, dict):
        raise TrainingArtifactIntegrityError(
            "Manifest file metadata is missing or invalid."
        )

    verified_files: dict[str, dict[str, Any]] = {}

    for split in ("train", "validation"):
        metadata = files_metadata.get(split)

        if not isinstance(metadata, dict):
            raise TrainingArtifactIntegrityError(
                f"Missing {split} file metadata."
            )

        expected_filename = (
            f"{split}.jsonl.gz"
        )

        if metadata.get("filename") != expected_filename:
            raise TrainingArtifactIntegrityError(
                f"Unexpected {split} filename."
            )

        path = (
            dataset_dir / expected_filename
        ).resolve()

        if path.parent != dataset_dir:
            raise TrainingArtifactIntegrityError(
                f"{split} file escapes the dataset directory."
            )

        if not path.is_file():
            raise TrainingArtifactIntegrityError(
                f"Missing training file: {path}"
            )

        expected_hash = metadata.get(
            "sha256"
        )

        if not isinstance(expected_hash, str):
            raise TrainingArtifactIntegrityError(
                f"Missing or invalid {split} checksum."
            )

        actual_hash = sha256_file(
            path
        )

        if actual_hash != expected_hash:
            raise TrainingArtifactIntegrityError(
                f"{split} checksum mismatch."
            )

        verified_files[split] = {
            "filename": expected_filename,
            "sha256": actual_hash,
            "examples": metadata.get(
                "examples"
            ),
        }

    return {
        "dataset_id": dataset_id,
        "approval_status": approval[
            "approval_status"
        ],
        "research_profile": approval[
            "research_profile"
        ],
        "dataset_dir": str(dataset_dir),
        "manifest_sha256": actual_manifest_hash,
        "files": verified_files,
        "integrity_status": "VERIFIED",
    }