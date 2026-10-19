"""Read-only Golden Database observation explorer."""

from __future__ import annotations

import csv
import io
import sqlite3
from datetime import datetime
from typing import Any

from apps.c3_workbench.golden_db import DATABASE_PATH

OBSERVATION_COLUMNS = (
    "observation_id",
    "dataset_id",
    "device_id",
    "episode_id",
    "timestamp",
    "operating_mode",
    "soil_moisture_pct",
    "rainfall_proxy_counts",
    "tilt_deg",
    "vibration_g",
    "fsr_adc",
    "air_temperature_c",
    "humidity_pct",
    "created_at",
)

ALLOWED_SORT_COLUMNS = {
    "timestamp",
    "observation_id",
    "device_id",
    "episode_id",
    "operating_mode",
    "soil_moisture_pct",
    "rainfall_proxy_counts",
    "tilt_deg",
    "vibration_g",
    "fsr_adc",
    "air_temperature_c",
    "humidity_pct",
}

ALLOWED_MODES = {
    "DEEP_SLEEP",
    "IDLE",
    "RISK",
    "WARNING",
}


def open_readonly_connection() -> sqlite3.Connection:
    """Open an existing database without permitting writes."""

    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(
            f"Golden Database not found: {DATABASE_PATH}"
        )

    connection = sqlite3.connect(
        f"{DATABASE_PATH.resolve().as_uri()}?mode=ro",
        uri=True,
        timeout=30,
    )

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA query_only = ON")

    return connection


def validate_timestamp(value: str | None) -> str | None:
    if value is None or value == "":
        return None

    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(
            f"Invalid ISO-8601 timestamp: {value}"
        ) from error

    return value


def build_where_clause(
    *,
    dataset_id: str | None = None,
    device_id: str | None = None,
    episode_id: str | None = None,
    operating_mode: str | None = None,
    timestamp_from: str | None = None,
    timestamp_to: str | None = None,
    search: str | None = None,
) -> tuple[str, list[Any]]:
    conditions: list[str] = []
    parameters: list[Any] = []

    if dataset_id:
        conditions.append("dataset_id = ?")
        parameters.append(dataset_id)

    if device_id:
        conditions.append("device_id = ?")
        parameters.append(device_id)

    if episode_id:
        conditions.append("episode_id = ?")
        parameters.append(episode_id)

    if operating_mode:
        if operating_mode not in ALLOWED_MODES:
            raise ValueError(
                f"Unsupported operating mode: {operating_mode}"
            )

        conditions.append("operating_mode = ?")
        parameters.append(operating_mode)

    timestamp_from = validate_timestamp(timestamp_from)
    timestamp_to = validate_timestamp(timestamp_to)

    if timestamp_from:
        conditions.append("timestamp >= ?")
        parameters.append(timestamp_from)

    if timestamp_to:
        conditions.append("timestamp <= ?")
        parameters.append(timestamp_to)

    if search:
        escaped = (
            search.strip()
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )

        if escaped:
            conditions.append(
                "("
                "device_id LIKE ? ESCAPE '\\' "
                "OR episode_id LIKE ? ESCAPE '\\'"
                ")"
            )

            pattern = f"%{escaped}%"
            parameters.extend([pattern, pattern])

    if not conditions:
        return "", parameters

    return "WHERE " + " AND ".join(conditions), parameters


def list_observations(
    *,
    dataset_id: str | None = None,
    device_id: str | None = None,
    episode_id: str | None = None,
    operating_mode: str | None = None,
    timestamp_from: str | None = None,
    timestamp_to: str | None = None,
    search: str | None = None,
    sort_by: str = "timestamp",
    sort_order: str = "desc",
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """Return a paginated selection of Golden observations."""

    if sort_by not in ALLOWED_SORT_COLUMNS:
        raise ValueError(
            f"Unsupported sorting column: {sort_by}"
        )

    direction = sort_order.lower()

    if direction not in {"asc", "desc"}:
        raise ValueError(
            "sort_order must be 'asc' or 'desc'"
        )

    if not 1 <= limit <= 200:
        raise ValueError(
            "limit must be between 1 and 200"
        )

    if offset < 0:
        raise ValueError(
            "offset must not be negative"
        )

    where_clause, parameters = build_where_clause(
        dataset_id=dataset_id,
        device_id=device_id,
        episode_id=episode_id,
        operating_mode=operating_mode,
        timestamp_from=timestamp_from,
        timestamp_to=timestamp_to,
        search=search,
    )

    column_sql = ", ".join(OBSERVATION_COLUMNS)

    with open_readonly_connection() as connection:
        total = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM c3_golden_observations
            {where_clause}
            """,
            parameters,
        ).fetchone()[0]

        rows = connection.execute(
            f"""
            SELECT {column_sql}
            FROM c3_golden_observations
            {where_clause}
            ORDER BY {sort_by} {direction.upper()},
                     observation_id {direction.upper()}
            LIMIT ? OFFSET ?
            """,
            [*parameters, limit, offset],
        ).fetchall()

    observations = [
        dict(row)
        for row in rows
    ]

    return {
        "observations": observations,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(observations) < total,
        "sort_by": sort_by,
        "sort_order": direction,
    }


def get_observation_filters(
    dataset_id: str | None = None,
) -> dict[str, Any]:
    """Return filter options derived from stored observations."""

    where_clause = "WHERE dataset_id = ?" if dataset_id else ""
    parameters = [dataset_id] if dataset_id else []

    with open_readonly_connection() as connection:
        datasets = [
            dict(row)
            for row in connection.execute(
                """
                SELECT dataset_id, filename, total_rows
                FROM c3_datasets
                ORDER BY uploaded_at DESC
                """
            ).fetchall()
        ]

        devices = [
            row[0]
            for row in connection.execute(
                f"""
                SELECT DISTINCT device_id
                FROM c3_golden_observations
                {where_clause}
                ORDER BY device_id
                """,
                parameters,
            ).fetchall()
        ]

        episodes = [
            row[0]
            for row in connection.execute(
                f"""
                SELECT DISTINCT episode_id
                FROM c3_golden_observations
                {where_clause}
                ORDER BY episode_id
                """,
                parameters,
            ).fetchall()
        ]

        modes = [
            row[0]
            for row in connection.execute(
                f"""
                SELECT DISTINCT operating_mode
                FROM c3_golden_observations
                {where_clause}
                ORDER BY operating_mode
                """,
                parameters,
            ).fetchall()
        ]

    return {
        "datasets": datasets,
        "devices": devices,
        "episodes": episodes,
        "operating_modes": modes,
    }


def export_observations_csv(
    *,
    dataset_id: str | None = None,
    device_id: str | None = None,
    episode_id: str | None = None,
    operating_mode: str | None = None,
    timestamp_from: str | None = None,
    timestamp_to: str | None = None,
    search: str | None = None,
) -> str:
    """Export matching observations as CSV without modifying SQLite."""

    where_clause, parameters = build_where_clause(
        dataset_id=dataset_id,
        device_id=device_id,
        episode_id=episode_id,
        operating_mode=operating_mode,
        timestamp_from=timestamp_from,
        timestamp_to=timestamp_to,
        search=search,
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(OBSERVATION_COLUMNS)

    column_sql = ", ".join(OBSERVATION_COLUMNS)

    with open_readonly_connection() as connection:
        cursor = connection.execute(
            f"""
            SELECT {column_sql}
            FROM c3_golden_observations
            {where_clause}
            ORDER BY timestamp ASC, observation_id ASC
            """,
            parameters,
        )

        for row in cursor:
            writer.writerow(
                [row[column] for column in OBSERVATION_COLUMNS]
            )

    return output.getvalue()