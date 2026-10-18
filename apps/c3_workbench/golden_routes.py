"""Golden dataset history endpoints for GeoNex C3."""

from __future__ import annotations

import json
import re

from typing import Any

from fastapi import APIRouter, HTTPException

from apps.c3_workbench.golden_db import (
    get_connection,
    initialize_golden_database,
)


router = APIRouter(
    prefix="/datasets/golden",
    tags=["C3 Golden Datasets"],
)

DATASET_ID_PATTERN = re.compile(r"^c3raw_[a-f0-9]{16}$")


def _serialize_dataset(row: Any) -> dict[str, Any]:
    return {
        "dataset_id": row["dataset_id"],
        "filename": row["filename"],
        "file_hash": row["file_hash"],
        "uploaded_at": row["uploaded_at"],
        "total_rows": row["total_rows"],
        "device_count": row["device_count"],
        "episode_count": row["episode_count"],
        "quality_status": row["quality_status"],
        "pipeline_status": row["pipeline_status"],
        "source_type": row["source_type"],
    }


@router.get("")
def list_golden_datasets() -> dict[str, Any]:
    """List registered raw CSV datasets."""

    initialize_golden_database()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM c3_datasets
            ORDER BY uploaded_at DESC
            """
        ).fetchall()

    datasets = [_serialize_dataset(row) for row in rows]

    return {
        "datasets": datasets,
        "total": len(datasets),
    }


@router.get("/{dataset_id}")
def get_golden_dataset(dataset_id: str) -> dict[str, Any]:
    """Retrieve one Golden dataset's metadata and validation report."""

    if not DATASET_ID_PATTERN.fullmatch(dataset_id):
        raise HTTPException(
            status_code=422,
            detail="Invalid Golden dataset ID",
        )

    initialize_golden_database()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM c3_datasets
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Golden dataset not found",
            )

        observation_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM c3_golden_observations
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        ).fetchone()[0]

    return {
        **_serialize_dataset(row),
        "stored_observations": observation_count,
        "validation": json.loads(row["validation_report"]),
    }