"""Safe offline Golden Database restoration for GeoNex C3."""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import uuid
from pathlib import Path

from apps.c3_workbench.golden_backup import (
    BACKUP_DIRECTORY,
    get_golden_backup,
)
from apps.c3_workbench.golden_db import (
    DATABASE_PATH,
)


def verify_database(path: Path) -> dict:
    """Check SQLite integrity, foreign keys and research record counts."""

    connection = sqlite3.connect(
        f"{path.resolve().as_uri()}?mode=ro",
        uri=True,
        timeout=30,
    )

    try:
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise ValueError(
                f"Database integrity check failed: {integrity}"
            )

        required_tables = {
            "c3_golden_observations",
            "c3_forecast_runs",
            "c3_forecast_values",
            "c3_alert_events",
        }

        existing_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

        missing = required_tables - existing_tables

        if missing:
            raise ValueError(
                f"Missing required tables: {sorted(missing)}"
            )

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if foreign_key_errors:
            raise ValueError(
                "Database contains foreign-key violations"
            )

        datasets = connection.execute(
            """
            SELECT COUNT(DISTINCT dataset_id)
            FROM c3_golden_observations
            """
        ).fetchone()[0]

        observations = connection.execute(
            "SELECT COUNT(*) FROM c3_golden_observations"
        ).fetchone()[0]

        return {
            "integrity": "ok",
            "datasets": datasets,
            "observations": observations,
        }

    finally:
        connection.close()


def _assert_database_not_in_use() -> None:
    """
    Require exclusive access to the live database.

    This catches active SQLite connections holding locks.
    It does not detect an idle process that may reopen the
    database later, so the API must also be stopped.
    """

    if not DATABASE_PATH.exists():
        return

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=0,
    )

    try:
        connection.execute(
            "BEGIN EXCLUSIVE"
        )

        connection.execute(
            "SELECT COUNT(*) FROM sqlite_master"
        ).fetchone()

        connection.rollback()

    except sqlite3.OperationalError as error:
        raise RuntimeError(
            "Database is currently locked. Stop the C3 backend "
            "and other database clients before restoring."
        ) from error

    finally:
        connection.close()


def restore_golden_database(
    backup_id: str,
    confirmation: str,
) -> dict:
    """
    Restore a verified backup with a pre-restore safety snapshot.

    Must only be executed while all database clients are stopped.
    """

    if confirmation != "RESTORE GOLDEN DATABASE":
        raise ValueError(
            "Restoration requires exact confirmation: "
            "RESTORE GOLDEN DATABASE"
        )

    backup_path, metadata = get_golden_backup(
        backup_id
    )

    verify_database(backup_path)

    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    BACKUP_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    _assert_database_not_in_use()

    # SQLite WAL must be checkpointed before replacing the main file.
    # The backend and all other SQLite clients must already be stopped.
    if DATABASE_PATH.exists():
        connection = sqlite3.connect(
            DATABASE_PATH,
            timeout=5,
        )

        try:
            result = connection.execute(
                "PRAGMA wal_checkpoint(TRUNCATE)"
            ).fetchone()

            if result and result[0] != 0:
                raise RuntimeError(
                    "WAL checkpoint could not complete. "
                    "Database may still be in use."
                )

        finally:
            connection.close()

    safety_id = f"pre_restore_{uuid.uuid4().hex[:16]}"

    safety_path = (
        BACKUP_DIRECTORY
        / f"{safety_id}.sqlite3"
    )

    if DATABASE_PATH.exists():
        source = sqlite3.connect(
            DATABASE_PATH,
            timeout=30,
        )

        destination = sqlite3.connect(
            safety_path,
            timeout=30,
        )

        try:
            source.backup(destination)

        finally:
            destination.close()
            source.close()

        verify_database(safety_path)

    temporary_path = (
        DATABASE_PATH.parent
        / f".restore_{uuid.uuid4().hex}.sqlite3"
    )

    try:
        source = sqlite3.connect(
            f"{backup_path.resolve().as_uri()}?mode=ro",
            uri=True,
        )

        destination = sqlite3.connect(
            temporary_path
        )

        try:
            source.backup(destination)

        finally:
            destination.close()
            source.close()

        restored_statistics = verify_database(
            temporary_path
        )

        # Recheck that the live database is not locked.
        _assert_database_not_in_use()

        # WAL should already be checkpointed and truncated.
        wal_path = Path(
            str(DATABASE_PATH) + "-wal"
        )

        shm_path = Path(
            str(DATABASE_PATH) + "-shm"
        )

        if wal_path.exists() and wal_path.stat().st_size > 0:
            raise RuntimeError(
                "Non-empty WAL file detected. "
                "Stop all database clients before restoring."
            )

        os.replace(
            temporary_path,
            DATABASE_PATH,
        )

        # These files must not remain from the previous database.
        wal_path.unlink(missing_ok=True)
        shm_path.unlink(missing_ok=True)

        final_statistics = verify_database(
            DATABASE_PATH
        )

        if final_statistics != restored_statistics:
            raise RuntimeError(
                "Restored database verification mismatch"
            )

        return {
            "status": "RESTORED",
            "backup_id": backup_id,
            "backup_created_at": metadata["created_at"],
            "restored_database": str(DATABASE_PATH),
            "safety_backup": (
                str(safety_path)
                if safety_path.exists()
                else None
            ),
            "statistics": final_statistics,
        }

    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Restore the GeoNex C3 Golden Database"
    )

    parser.add_argument(
        "--backup-id",
        required=True,
        help="ID of the verified backup to restore",
    )

    parser.add_argument(
        "--confirm",
        default="",
        help="Must equal RESTORE GOLDEN DATABASE",
    )

    args = parser.parse_args()

    try:
        result = restore_golden_database(
            backup_id=args.backup_id,
            confirmation=args.confirm,
        )

        print("\nGolden Database restored successfully.")
        print(f"Backup: {result['backup_id']}")
        print(f"Safety copy: {result['safety_backup']}")
        print(f"Statistics: {result['statistics']}")

    except Exception as error:
        print(
            f"\nRESTORATION FAILED: {error}",
            file=sys.stderr,
        )

        sys.exit(1)


if __name__ == "__main__":
    main()