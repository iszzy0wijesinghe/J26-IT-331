"""Persistent Golden Data database for GeoNex C3 research."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    ROOT
    / "data"
    / "workbench"
    / "c3"
    / "golden"
    / "c3_golden.sqlite3"
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=30,
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    connection.execute(
        "PRAGMA busy_timeout = 30000"
    )

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def initialize_golden_database() -> None:
    """Create persistent C3 research tables."""

    with get_connection() as connection:

        connection.execute(
            "PRAGMA journal_mode = WAL"
        )

        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS c3_datasets (
                dataset_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                total_rows INTEGER NOT NULL,
                device_count INTEGER NOT NULL,
                episode_count INTEGER NOT NULL,
                quality_status TEXT NOT NULL,
                pipeline_status TEXT NOT NULL,
                validation_report TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'CSV',
                UNIQUE(file_hash)
            );

            CREATE TABLE IF NOT EXISTS c3_golden_observations (
                observation_id INTEGER PRIMARY KEY AUTOINCREMENT,

                dataset_id TEXT NOT NULL,

                device_id TEXT NOT NULL,
                episode_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,

                operating_mode TEXT NOT NULL,

                soil_moisture_pct REAL NOT NULL,
                rainfall_proxy_counts REAL NOT NULL,
                tilt_deg REAL NOT NULL,
                vibration_g REAL NOT NULL,
                fsr_adc REAL NOT NULL,
                air_temperature_c REAL NOT NULL,
                humidity_pct REAL NOT NULL,

                created_at TEXT NOT NULL,

                FOREIGN KEY(dataset_id)
                    REFERENCES c3_datasets(dataset_id)
                    ON DELETE CASCADE,

                UNIQUE(
                    dataset_id,
                    device_id,
                    episode_id,
                    timestamp
                )
            );

            CREATE INDEX IF NOT EXISTS idx_c3_observations_temporal
            ON c3_golden_observations (
                dataset_id,
                device_id,
                episode_id,
                timestamp
            );

            CREATE TABLE IF NOT EXISTS c3_training_jobs (
                job_id TEXT PRIMARY KEY,

                dataset_id TEXT NOT NULL,

                status TEXT NOT NULL,
                current_stage TEXT NOT NULL,

                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,

                error_message TEXT,

                FOREIGN KEY(dataset_id)
                    REFERENCES c3_datasets(dataset_id)
            );

            CREATE TABLE IF NOT EXISTS c3_training_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,

                job_id TEXT NOT NULL,

                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                stage TEXT NOT NULL,
                message TEXT NOT NULL,

                FOREIGN KEY(job_id)
                    REFERENCES c3_training_jobs(job_id)
            );

            CREATE INDEX IF NOT EXISTS idx_c3_training_events_job
            ON c3_training_events (
                job_id,
                event_id
            );

            CREATE TABLE IF NOT EXISTS c3_model_versions (
                model_version_id TEXT PRIMARY KEY,

                job_id TEXT NOT NULL,
                dataset_id TEXT NOT NULL,

                model_name TEXT NOT NULL,
                horizon_minutes INTEGER NOT NULL,

                checkpoint_path TEXT,

                validation_mae REAL,
                validation_rmse REAL,

                status TEXT NOT NULL,
                created_at TEXT NOT NULL,

                FOREIGN KEY(job_id)
                    REFERENCES c3_training_jobs(job_id),

                FOREIGN KEY(dataset_id)
                    REFERENCES c3_datasets(dataset_id)
            );

            CREATE TABLE IF NOT EXISTS c3_forecast_runs (
                forecast_id TEXT PRIMARY KEY,

                device_id TEXT NOT NULL,
                model_version_id TEXT,

                generated_at TEXT NOT NULL,

                input_window_start TEXT,
                input_window_end TEXT,

                operating_mode TEXT,

                quality_status TEXT NOT NULL,
                status TEXT NOT NULL,

                FOREIGN KEY(model_version_id)
                    REFERENCES c3_model_versions(model_version_id)
            );

            CREATE TABLE IF NOT EXISTS c3_forecast_values (
                forecast_id TEXT NOT NULL,

                horizon_minutes INTEGER NOT NULL,
                target_timestamp TEXT NOT NULL,

                predicted_moisture_pct REAL NOT NULL,

                PRIMARY KEY(
                    forecast_id,
                    horizon_minutes
                ),

                FOREIGN KEY(forecast_id)
                    REFERENCES c3_forecast_runs(forecast_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS c3_alert_events (
                alert_id TEXT PRIMARY KEY,

                forecast_id TEXT NOT NULL,
                device_id TEXT NOT NULL,

                created_at TEXT NOT NULL,

                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,

                trigger_source TEXT NOT NULL,
                rule_version TEXT NOT NULL,

                status TEXT NOT NULL,

                FOREIGN KEY(forecast_id)
                    REFERENCES c3_forecast_runs(forecast_id)
            );
            """
        )


def get_database_statistics() -> dict[str, Any]:
    """Return database counts without exposing observation records."""

    initialize_golden_database()

    with get_connection() as connection:

        tables = {
            "datasets": "c3_datasets",
            "golden_observations": "c3_golden_observations",
            "training_jobs": "c3_training_jobs",
            "training_events": "c3_training_events",
            "model_versions": "c3_model_versions",
            "forecast_runs": "c3_forecast_runs",
            "forecast_values": "c3_forecast_values",
            "alert_events": "c3_alert_events",
        }

        statistics: dict[str, Any] = {
            "database_path": str(DATABASE_PATH),
            "tables": {},
        }

        for label, table in tables.items():
            count = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

            statistics["tables"][label] = count

        return statistics


if __name__ == "__main__":
    initialize_golden_database()

    print(
        json.dumps(
            get_database_statistics(),
            indent=2,
        )
    )