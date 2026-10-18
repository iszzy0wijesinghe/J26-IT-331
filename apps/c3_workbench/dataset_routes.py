"""Dataset management routes for the GeoNex C3 research workbench.

Supported endpoints:

    GET  /datasets
    GET  /datasets/{dataset_id}
    POST /datasets/upload

Dataset uploads must contain exactly:

    manifest.json
    train.jsonl.gz
    validation.jsonl.gz

The held-out test split must never be uploaded or accessed.

This API supports synthetic C3 forecasting research datasets.
It does not validate landslide-warning performance.
"""

from __future__ import annotations

import shutil
import stat
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from apps.c3_workbench.dataset_registry import (
    C3DatasetRegistryError,
    get_dataset,
    list_datasets,
    register_dataset,
)
from apps.c3_workbench.dataset_validator import (
    C3DatasetValidationError,
)


# ============================================================
# Router configuration
# ============================================================

router = APIRouter(
    prefix="/datasets",
    tags=["C3 Dataset Manager"],
)


# ============================================================
# Upload and extraction limits
# ============================================================

MIB = 1024**2

# Maximum uploaded ZIP archive size.
MAX_UPLOAD_BYTES = 100 * MIB

# Maximum combined size of files extracted from the ZIP.
#
# This is NOT the decompressed size of the nested JSONL gzip files.
MAX_EXTRACTED_BYTES = 100 * MIB

# Maximum manifest size.
MAX_MANIFEST_BYTES = 1 * MIB

# Maximum size of one extracted file.
MAX_EXTRACTED_FILE_BYTES = 100 * MIB

# Streaming chunk size.
CHUNK_BYTES = 1 * MIB


# ============================================================
# Required dataset structure
# ============================================================

REQUIRED_FILES = frozenset(
    {
        "manifest.json",
        "train.jsonl.gz",
        "validation.jsonl.gz",
    }
)


# ============================================================
# Dataset listing
# ============================================================

@router.get("")
def get_datasets() -> dict[str, Any]:
    """List all registered C3 research datasets."""

    datasets = list_datasets()

    return {
        "datasets": datasets,
        "total": len(datasets),
    }


# ============================================================
# Dataset details
# ============================================================

@router.get("/{dataset_id}")
def get_dataset_details(
    dataset_id: str,
) -> dict[str, Any]:
    """Retrieve metadata for a registered dataset."""

    try:
        return get_dataset(dataset_id)

    except C3DatasetRegistryError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


# ============================================================
# ZIP archive validation
# ============================================================

def _validate_zip_entries(
    archive: zipfile.ZipFile,
) -> list[zipfile.ZipInfo]:
    """Validate ZIP structure before extracting any files."""

    entries = archive.infolist()

    filenames = [entry.filename for entry in entries]

    # --------------------------------------------------------
    # Exact file structure
    # --------------------------------------------------------

    if len(entries) != len(REQUIRED_FILES):
        raise HTTPException(
            status_code=422,
            detail=(
                "Dataset ZIP must contain exactly three files: "
                "manifest.json, train.jsonl.gz and "
                "validation.jsonl.gz"
            ),
        )

    # Detect duplicate entries explicitly.
    if len(filenames) != len(set(filenames)):
        raise HTTPException(
            status_code=422,
            detail="Dataset ZIP contains duplicate filenames",
        )

    if set(filenames) != REQUIRED_FILES:
        raise HTTPException(
            status_code=422,
            detail=(
                "Invalid dataset ZIP structure. "
                "Only manifest.json, train.jsonl.gz and "
                "validation.jsonl.gz are permitted."
            ),
        )

    # --------------------------------------------------------
    # Declared extraction size
    # --------------------------------------------------------

    declared_total = 0

    for entry in entries:

        if entry.is_dir():
            raise HTTPException(
                status_code=422,
                detail="Dataset ZIP must not contain directories",
            )

        # ----------------------------------------------------
        # Encryption
        # ----------------------------------------------------

        if entry.flag_bits & 0x1:
            raise HTTPException(
                status_code=422,
                detail="Encrypted ZIP entries are not supported",
            )

        # ----------------------------------------------------
        # Symbolic links and special files
        # ----------------------------------------------------

        if entry.create_system == 3:
            unix_mode = entry.external_attr >> 16

            file_type = stat.S_IFMT(unix_mode)

            if file_type not in (0, stat.S_IFREG):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "ZIP symbolic links and special files "
                        "are not permitted"
                    ),
                )

        # ----------------------------------------------------
        # Compression method
        # ----------------------------------------------------

        if entry.compress_type not in (
            zipfile.ZIP_STORED,
            zipfile.ZIP_DEFLATED,
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Unsupported ZIP compression method "
                    f"for {entry.filename}"
                ),
            )

        # ----------------------------------------------------
        # Individual file size
        # ----------------------------------------------------

        if entry.file_size > MAX_EXTRACTED_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"ZIP entry exceeds the permitted size: "
                    f"{entry.filename}"
                ),
            )

        if (
            entry.filename == "manifest.json"
            and entry.file_size > MAX_MANIFEST_BYTES
        ):
            raise HTTPException(
                status_code=413,
                detail="Dataset manifest exceeds 1 MiB",
            )

        declared_total += entry.file_size

        if declared_total > MAX_EXTRACTED_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Extracted dataset exceeds 100 MiB",
            )

    return entries


# ============================================================
# Bounded ZIP extraction
# ============================================================

def _extract_dataset_zip(
    archive_path: Path,
    destination_dir: Path,
) -> None:
    """Extract an approved dataset ZIP using bounded reads.

    Never extracts paths directly from untrusted ZIP filenames.
    Only the three explicitly allowed filenames are accepted.
    """

    extracted_total = 0

    try:
        with zipfile.ZipFile(archive_path, "r") as archive:

            entries = _validate_zip_entries(archive)

            for entry in entries:

                # ------------------------------------------------
                # Safe destination
                # ------------------------------------------------

                # The filename is already checked against
                # REQUIRED_FILES, so it cannot contain paths.
                destination = destination_dir / entry.filename

                extracted_file_bytes = 0

                # ------------------------------------------------
                # Streaming extraction
                # ------------------------------------------------

                with archive.open(entry, "r") as source:
                    with destination.open("xb") as target:

                        while True:
                            chunk = source.read(CHUNK_BYTES)

                            if not chunk:
                                break

                            extracted_file_bytes += len(chunk)
                            extracted_total += len(chunk)

                            # ------------------------------------
                            # Combined extraction limit
                            # ------------------------------------

                            if extracted_total > MAX_EXTRACTED_BYTES:
                                raise HTTPException(
                                    status_code=413,
                                    detail=(
                                        "Extracted dataset exceeds "
                                        "100 MiB"
                                    ),
                                )

                            # ------------------------------------
                            # Individual file limit
                            # ------------------------------------

                            if (
                                extracted_file_bytes
                                > MAX_EXTRACTED_FILE_BYTES
                            ):
                                raise HTTPException(
                                    status_code=413,
                                    detail=(
                                        "Extracted file exceeds "
                                        "100 MiB"
                                    ),
                                )

                            # ------------------------------------
                            # Manifest limit
                            # ------------------------------------

                            if (
                                entry.filename == "manifest.json"
                                and extracted_file_bytes
                                > MAX_MANIFEST_BYTES
                            ):
                                raise HTTPException(
                                    status_code=413,
                                    detail=(
                                        "Dataset manifest exceeds "
                                        "1 MiB"
                                    ),
                                )

                            target.write(chunk)

                # ------------------------------------------------
                # Verify extracted size
                # ------------------------------------------------

                if extracted_file_bytes != entry.file_size:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "ZIP entry size mismatch: "
                            f"{entry.filename}"
                        ),
                    )

    except (
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
        RuntimeError,
        EOFError,
        NotImplementedError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid or unsupported ZIP archive: {exc}",
        ) from exc


# ============================================================
# Dataset upload
# ============================================================

@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Upload, validate and register a C3 forecasting dataset.

    Processing stages:

        1. Validate uploaded filename.
        2. Stream ZIP into temporary storage.
        3. Enforce upload size limit.
        4. Validate ZIP entries.
        5. Extract with strict byte limits.
        6. Validate manifest and forecasting examples.
        7. Verify SHA-256 integrity.
        8. Check train/validation episode disjointness.
        9. Register dataset or reuse existing registration.

    Uploading does not trigger model training.
    """

    try:
        # ----------------------------------------------------
        # Filename validation
        # ----------------------------------------------------

        if (
            not file.filename
            or not file.filename.lower().endswith(".zip")
        ):
            raise HTTPException(
                status_code=422,
                detail="Upload must be a ZIP archive",
            )

        # ----------------------------------------------------
        # Temporary workspace
        # ----------------------------------------------------

        with tempfile.TemporaryDirectory(
            prefix="geonex_c3_upload_"
        ) as temporary_directory:

            temporary_root = Path(temporary_directory)

            archive_path = temporary_root / "dataset.zip"

            extracted_dir = temporary_root / "extracted"

            extracted_dir.mkdir()

            # ------------------------------------------------
            # Save uploaded ZIP with bounded reads
            # ------------------------------------------------

            uploaded_bytes = 0

            with archive_path.open("wb") as destination:

                while True:
                    chunk = await file.read(CHUNK_BYTES)

                    if not chunk:
                        break

                    uploaded_bytes += len(chunk)

                    if uploaded_bytes > MAX_UPLOAD_BYTES:
                        raise HTTPException(
                            status_code=413,
                            detail=(
                                "Dataset ZIP upload exceeds "
                                "100 MiB"
                            ),
                        )

                    destination.write(chunk)

            if uploaded_bytes == 0:
                raise HTTPException(
                    status_code=422,
                    detail="Uploaded ZIP archive is empty",
                )

            # ------------------------------------------------
            # Validate and extract ZIP
            # ------------------------------------------------

            _extract_dataset_zip(
                archive_path=archive_path,
                destination_dir=extracted_dir,
            )

            # ------------------------------------------------
            # Validate and register dataset
            # ------------------------------------------------

            registered = register_dataset(extracted_dir)

            return {
                "message": (
                    "Dataset validated and registered successfully"
                ),
                "dataset": registered,
            }

    except HTTPException:
        raise

    except (
        C3DatasetValidationError,
        C3DatasetRegistryError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    finally:
        await file.close()