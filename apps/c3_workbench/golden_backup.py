"""Verified SQLite backup management for GeoNex C3."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from apps.c3_workbench.golden_db import (
    DATABASE_PATH,
    get_connection,
    initialize_golden_database,
    utc_now,
)

BACKUP_DIRECTORY = DATABASE_PATH.parent / "backups"

BACKUP_ID_PATTERN = re.compile(
    r"^c3backup_[a-f0-9]{16}$"
)


def _backup_path(backup_id: str) -> Path:
    if not BACKUP_ID_PATTERN.fullmatch(backup_id):
        raise ValueError("Invalid backup ID")

    return BACKUP_DIRECTORY / f"{backup_id}.sqlite3"


def _metadata_path(backup_id: str) -> Path:
    if not BACKUP_ID_PATTERN.fullmatch(backup_id):
        raise ValueError("Invalid backup ID")

    return BACKUP_DIRECTORY / f"{backup_id}.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _verify_database(path: Path) -> None:
    """Verify SQLite integrity and expected C3 tables."""

    connection = sqlite3.connect(
        f"{path.resolve().as_uri()}?mode=ro",
        uri=True,
        timeout=30,
    )

    try:
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()

        if integrity is None or integrity[0] != "ok":
            raise ValueError(
                "SQLite integrity verification failed"
            )

        required_tables = {
            "c3_datasets",
            "c3_golden_observations",
            "c3_training_jobs",
            "c3_training_events",
            "c3_model_versions",
            "c3_forecast_runs",
            "c3_forecast_values",
            "c3_alert_events",
        }

        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

        existing_tables = {
            row[0] for row in rows
        }

        missing = required_tables - existing_tables

        if missing:
            raise ValueError(
                "Backup is missing required tables: "
                + ", ".join(sorted(missing))
            )

        foreign_keys = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if foreign_keys:
            raise ValueError(
                "Backup contains foreign-key violations"
            )

    finally:
        connection.close()


def create_golden_backup() -> dict[str, Any]:
    """Create and verify a consistent Golden Database snapshot."""

    initialize_golden_database()

    BACKUP_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    backup_id = f"c3backup_{uuid.uuid4().hex[:16]}"

    destination = _backup_path(backup_id)
    temporary = BACKUP_DIRECTORY / f"{backup_id}.tmp"

    metadata_file = _metadata_path(backup_id)

    destination_connection: sqlite3.Connection | None = None

    try:
        with get_connection() as source:
            destination_connection = sqlite3.connect(
                temporary,
                timeout=30,
            )

            source.backup(
                destination_connection,
                pages=100,
                sleep=0.1,
            )

            destination_connection.close()
            destination_connection = None

        _verify_database(temporary)

        os.replace(
            temporary,
            destination,
        )

        metadata: dict[str, Any] = {
            "backup_id": backup_id,
            "filename": destination.name,
            "created_at": utc_now(),
            "size_bytes": destination.stat().st_size,
            "sha256": _sha256(destination),
            "status": "VERIFIED",
            "database_filename": DATABASE_PATH.name,
        }

        metadata_file.write_text(
            json.dumps(
                metadata,
                indent=2,
            ),
            encoding="utf-8",
        )

        return metadata

    except Exception:
        if destination_connection is not None:
            destination_connection.close()

        temporary.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        metadata_file.unlink(missing_ok=True)

        raise


def list_golden_backups() -> dict[str, Any]:
    """List backups that have valid metadata files."""

    BACKUP_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    backups: list[dict[str, Any]] = []

    for metadata_file in BACKUP_DIRECTORY.glob(
        "c3backup_*.json"
    ):
        try:
            metadata = json.loads(
                metadata_file.read_text(
                    encoding="utf-8"
                )
            )

            backup_id = metadata.get("backup_id")

            if (
                not isinstance(backup_id, str)
                or not BACKUP_ID_PATTERN.fullmatch(backup_id)
            ):
                continue

            backup_file = _backup_path(backup_id)

            if not backup_file.is_file():
                continue

            backups.append(metadata)

        except (OSError, ValueError, json.JSONDecodeError):
            continue

    backups.sort(
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )

    return {
        "backups": backups,
        "total": len(backups),
    }


def get_golden_backup(
    backup_id: str,
) -> tuple[Path, dict[str, Any]]:
    """Return a backup only if its integrity checks pass."""

    backup_file = _backup_path(backup_id)
    metadata_file = _metadata_path(backup_id)

    if not backup_file.is_file():
        raise FileNotFoundError(
            "Backup file not found"
        )

    if not metadata_file.is_file():
        raise FileNotFoundError(
            "Backup metadata not found"
        )

    metadata = json.loads(
        metadata_file.read_text(
            encoding="utf-8"
        )
    )

    if metadata.get("backup_id") != backup_id:
        raise ValueError(
            "Backup metadata ID mismatch"
        )

    expected_hash = metadata.get("sha256")

    if not isinstance(expected_hash, str):
        raise ValueError(
            "Backup checksum is missing"
        )

    actual_hash = _sha256(backup_file)

    if actual_hash != expected_hash:
        raise ValueError(
            "Backup checksum verification failed"
        )

    _verify_database(backup_file)

    return backup_file, metadata