"""
GeoNex C3 - Dedicated Training Database

Purpose:
    Provide an independent SQLite database for C3
    training metadata, experiments, and model records.

Important:
    - Does not modify the Golden Database.
    - Does not automatically migrate existing records.
    - Does not delete existing data.
    - Does not train models.
    - Uses a separate SQLite connection.
"""

from __future__ import annotations

import os
import sqlite3

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_TRAINING_DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "training"
    / "c3_training.sqlite3"
)


def get_training_db_path() -> Path:
    """
    Resolve the training database location.

    Supports an optional environment variable:
        GEONEX_C3_TRAINING_DB
    """

    configured_path = os.getenv(
        "GEONEX_C3_TRAINING_DB"
    )

    if configured_path:
        return Path(configured_path).expanduser().resolve()

    return DEFAULT_TRAINING_DB_PATH


def connect_training_db() -> sqlite3.Connection:
    """
    Open a connection to the dedicated training database.
    """

    database_path = get_training_db_path()

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        str(database_path),
        timeout=30,
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    connection.execute(
        "PRAGMA busy_timeout = 30000"
    )

    connection.execute(
        "PRAGMA journal_mode = WAL"
    )

    return connection


@contextmanager
def training_db_session() -> Iterator[sqlite3.Connection]:
    """
    Transaction-managed training database session.

    Commits successful operations.
    Rolls back failed operations.
    Always closes the connection.
    """

    connection = connect_training_db()

    try:
        yield connection

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def initialize_training_database() -> Path:
    """
    Initialize dedicated training metadata tables.

    This schema is intentionally isolated from the
    existing Golden Database schema.

    Existing production training tables must be
    migrated and reconciled separately.
    """

    with training_db_session() as connection:

        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS training_datasets (
                dataset_id TEXT PRIMARY KEY,

                dataset_name TEXT NOT NULL,

                dataset_type TEXT NOT NULL,

                source_path TEXT,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                metadata_json TEXT
            );

            CREATE TABLE IF NOT EXISTS training_experiments (
                experiment_id TEXT PRIMARY KEY,

                dataset_id TEXT NOT NULL,

                experiment_name TEXT NOT NULL,

                model_family TEXT NOT NULL,

                model_name TEXT NOT NULL,

                status TEXT NOT NULL
                    DEFAULT 'CREATED',

                configuration_json TEXT,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (dataset_id)
                    REFERENCES training_datasets(dataset_id)
            );

            CREATE TABLE IF NOT EXISTS training_model_versions (
                model_version_id TEXT PRIMARY KEY,

                experiment_id TEXT,

                model_name TEXT NOT NULL,

                model_family TEXT NOT NULL,

                checkpoint_path TEXT,

                scaler_path TEXT,

                metrics_json TEXT,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (experiment_id)
                    REFERENCES training_experiments(experiment_id)
            );

            CREATE INDEX IF NOT EXISTS
                idx_training_experiments_dataset
            ON training_experiments(dataset_id);

            CREATE INDEX IF NOT EXISTS
                idx_training_models_experiment
            ON training_model_versions(experiment_id);
            """
        )

    return get_training_db_path()


def get_training_database_status() -> dict:
    """
    Return training database information.
    """

    database_path = get_training_db_path()

    if not database_path.exists():
        return {
            "initialized": False,
            "database_path": str(database_path),
        }

    connection = connect_training_db()

    try:
        integrity_result = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

        return {
            "initialized": True,
            "database_path": str(database_path),
            "integrity": integrity_result,
            "tables": [
                row["name"]
                for row in tables
            ],
        }

    finally:
        connection.close()


if __name__ == "__main__":

    database_path = initialize_training_database()

    print(
        "Training database initialized:",
        database_path,
    )

    print(get_training_database_status())