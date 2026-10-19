"""Persistent dataset registry for the GeoNex C3 research workbench."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from apps.c3_workbench.dataset_validator import (
    REQUIRED_SPLITS,
    calculate_sha256,
    validate_dataset_directory,
)

ROOT = Path(__file__).resolve().parents[2]

REGISTRY_ROOT = ROOT / "data" / "workbench" / "c3" / "datasets"

DATASET_FILES = (
    "manifest.json",
    "train.jsonl.gz",
    "validation.jsonl.gz",
)


class C3DatasetRegistryError(ValueError):
    """Raised when a dataset registry operation fails."""


def _dataset_fingerprint(dataset_dir: Path) -> str:
    """Generate a fingerprint from the accepted dataset files."""

    digest = hashlib.sha256()

    for filename in DATASET_FILES:
        path = dataset_dir / filename

        digest.update(filename.encode("utf-8"))
        digest.update(bytes.fromhex(calculate_sha256(path)))

    return digest.hexdigest()


def _read_metadata(path: Path) -> dict[str, Any]:
    """Read one registered dataset's metadata."""

    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise C3DatasetRegistryError(
            f"Cannot read registry metadata: {path.name}"
        ) from exc

    if not isinstance(metadata, dict):
        raise C3DatasetRegistryError("Invalid registry metadata")

    return metadata


def list_datasets() -> list[dict[str, Any]]:
    """List registered datasets without reading forecasting records."""

    if not REGISTRY_ROOT.exists():
        return []

    datasets = []

    for directory in REGISTRY_ROOT.iterdir():
        if not directory.is_dir():
            continue

        metadata_path = directory / "metadata.json"

        if not metadata_path.is_file():
            continue

        datasets.append(_read_metadata(metadata_path))

    return sorted(
        datasets,
        key=lambda item: item["created_at"],
        reverse=True,
    )


def get_dataset(dataset_id: str) -> dict[str, Any]:
    """Retrieve one dataset's metadata."""

    if not dataset_id.startswith("c3ds_"):
        raise C3DatasetRegistryError("Invalid dataset ID")

    if not all(
        character.isalnum() or character == "_"
        for character in dataset_id
    ):
        raise C3DatasetRegistryError("Invalid dataset ID")

    metadata_path = REGISTRY_ROOT / dataset_id / "metadata.json"

    if not metadata_path.is_file():
        raise C3DatasetRegistryError("Dataset not found")

    return _read_metadata(metadata_path)


def register_dataset(dataset_dir: str | Path) -> dict[str, Any]:
    """Validate and persist a forecast-ready dataset."""

    dataset_dir = Path(dataset_dir)

    validate_dataset_directory(dataset_dir)

    fingerprint = _dataset_fingerprint(dataset_dir)

    REGISTRY_ROOT.mkdir(parents=True, exist_ok=True)

    # Return existing registration for identical dataset content.
    for existing in list_datasets():
        if existing.get("fingerprint") == fingerprint:
            return existing

    dataset_id = f"c3ds_{uuid4().hex[:16]}"

    final_directory = REGISTRY_ROOT / dataset_id

    temporary_directory = Path(
        tempfile.mkdtemp(
            prefix=".c3ds_staging_",
            dir=REGISTRY_ROOT,
        )
    )

    try:
        for filename in DATASET_FILES:
            shutil.copy2(
                dataset_dir / filename,
                temporary_directory / filename,
            )

        # Verify the stored copy before publishing the registration.
        stored_validation = validate_dataset_directory(
            temporary_directory
        )

        stored_fingerprint = _dataset_fingerprint(
            temporary_directory
        )

        if stored_fingerprint != fingerprint:
            raise C3DatasetRegistryError(
                "Dataset content changed during registration"
            )

        metadata = {
            "dataset_id": dataset_id,
            "status": "VALIDATED",
            "created_at": datetime.now(UTC).isoformat(),
            "fingerprint": fingerprint,
            "dataset_version": stored_validation["dataset_version"],
            "export_version": stored_validation["export_version"],
            "source_origin": stored_validation["source_origin"],
            "target_feature": stored_validation["target_feature"],
            "forecast_horizons_minutes": stored_validation[
                "forecast_horizons_minutes"
            ],
            "available_splits": list(REQUIRED_SPLITS),
            "held_out_test_included": False,
            "validation": stored_validation,
        }

        metadata_path = temporary_directory / "metadata.json"

        metadata_path.write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

        # Publish only after all checks pass.
        os.rename(
            temporary_directory,
            final_directory,
        )

        return metadata

    finally:
        if temporary_directory.exists():
            shutil.rmtree(temporary_directory)