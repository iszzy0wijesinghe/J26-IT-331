"""CSV upload and validation endpoints for GeoNex C3.

This module validates raw sensor observations.

It does not:
- Register datasets
- Create training splits
- Start training
- Access held-out test data
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from apps.c3_workbench.csv_validator import (
    MAX_CSV_BYTES,
    validate_csv,
)


router = APIRouter(
    prefix="/datasets/csv",
    tags=["C3 CSV Validation"],
)

CHUNK_BYTES = 1024 * 1024


@router.post("/validate")
async def validate_uploaded_csv(
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Validate an uploaded C3 observations CSV."""

    filename = Path(file.filename or "").name

    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=422,
            detail="Only CSV files are supported",
        )

    with tempfile.TemporaryDirectory(
        prefix="geonex_c3_csv_"
    ) as temporary_directory:

        destination = (
            Path(temporary_directory) / "uploaded.csv"
        )

        total_bytes = 0

        try:
            with destination.open("wb") as output:
                while True:
                    chunk = await file.read(CHUNK_BYTES)

                    if not chunk:
                        break

                    total_bytes += len(chunk)

                    if total_bytes > MAX_CSV_BYTES:
                        raise HTTPException(
                            status_code=413,
                            detail=(
                                "CSV exceeds the maximum "
                                "upload size of 100 MiB"
                            ),
                        )

                    output.write(chunk)

            if total_bytes == 0:
                raise HTTPException(
                    status_code=422,
                    detail="Uploaded CSV is empty",
                )

            result = validate_csv(destination)
            report = result.to_dict()
            report["filename"] = filename

            return {
                "message": (
                    "CSV validation completed successfully"
                    if result.status == "VALIDATED"
                    else "CSV validation failed"
                ),
                "validation": report,
                "registered": False,
                "training_started": False,
            }

        finally:
            await file.close()