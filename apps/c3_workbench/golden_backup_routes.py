"""Golden Database backup API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from apps.c3_workbench.golden_backup import (
    create_golden_backup,
    get_golden_backup,
    list_golden_backups,
)


router = APIRouter(
    prefix="/database/backups",
    tags=["C3 Golden Database Backups"],
)


@router.post("")
def create_backup():
    """Create a verified Golden Database backup."""

    try:
        backup = create_golden_backup()

        return {
            "message": "Golden Database backup created successfully",
            "backup": backup,
        }

    except (OSError, ValueError) as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error


@router.get("")
def list_backups():
    """List available database backups."""

    return list_golden_backups()


@router.get("/{backup_id}")
def get_backup_details(backup_id: str):
    """Get backup metadata after integrity verification."""

    try:
        _, metadata = get_golden_backup(backup_id)

        return metadata

    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error


@router.get("/{backup_id}/download")
def download_backup(backup_id: str):
    """Download a verified SQLite database backup."""

    try:
        path, metadata = get_golden_backup(backup_id)

        return FileResponse(
            path=path,
            filename=metadata["filename"],
            media_type="application/x-sqlite3",
        )

    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error