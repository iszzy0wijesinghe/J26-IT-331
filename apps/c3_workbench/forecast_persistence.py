"""GeoNex C3 forecast persistence.

Stores individual horizon predictions with their exact model identity.

Research safeguards:
- Preserves dataset, device, episode, and forecast origin.
- Stores model identity separately for each horizon.
- Distinguishes historical replay from live inference.
- Does not fabricate actual future observations.
- Does not modify legacy forecasting tables.
"""

from __future__ import annotations

import json
import math
import uuid

from datetime import datetime, timezone
from typing import Any

from apps.c3_workbench.golden_db import (
    get_connection,
    initialize_golden_database,
)

from apps.c3_workbench.forecasting_reader import (
    parse_timestamp,
)


VALID_HORIZONS = {15, 30, 60}


class ForecastPersistenceError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize_forecast_persistence() -> None:
    """Create the forecast prediction table if necessary."""

    initialize_golden_database()

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS c3_forecast_predictions (
                prediction_id TEXT PRIMARY KEY,

                dataset_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                episode_id TEXT NOT NULL,

                forecast_origin TEXT NOT NULL,
                forecast_type TEXT NOT NULL,

                horizon_minutes INTEGER NOT NULL,

                target_timestamp TEXT NOT NULL,

                model_version_id TEXT NOT NULL,
                model_name TEXT NOT NULL,

                predicted_soil_moisture_pct REAL NOT NULL,

                actual_soil_moisture_pct REAL,
                absolute_error REAL,

                input_window_start TEXT NOT NULL,
                input_window_end TEXT NOT NULL,
                sequence_length INTEGER NOT NULL,

                source_origin TEXT NOT NULL,
                source_provenance_verified INTEGER NOT NULL,

                receipt_time_basis TEXT NOT NULL,

                checkpoint_sha256 TEXT NOT NULL,

                created_at TEXT NOT NULL,

                FOREIGN KEY (dataset_id)
                    REFERENCES c3_datasets(dataset_id),

                FOREIGN KEY (model_version_id)
                    REFERENCES c3_model_versions(model_version_id),

                CHECK (horizon_minutes IN (15, 30, 60)),

                CHECK (
                    forecast_type IN (
                        'HISTORICAL_REPLAY',
                        'LIVE_INFERENCE'
                    )
                ),

                CHECK (sequence_length >= 3),

                CHECK (
                    source_provenance_verified IN (0, 1)
                )
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_c3_forecast_predictions_history

            ON c3_forecast_predictions (
                dataset_id,
                device_id,
                episode_id,
                forecast_origin,
                horizon_minutes
            )
            """
        )

        connection.commit()


def save_forecast_predictions(
    forecast_result: dict[str, Any],
) -> list[dict[str, Any]]:
    """Persist one forecasting result atomically."""

    initialize_forecast_persistence()

    dataset_id = forecast_result["dataset_id"]
    device_id = forecast_result["device_id"]
    episode_id = forecast_result["episode_id"]

    forecast_origin = parse_timestamp(
        forecast_result["forecast_origin"]
    )

    window_start = parse_timestamp(
        forecast_result["input_window_start"]
    )

    window_end = parse_timestamp(
        forecast_result["input_window_end"]
    )

    if not (
        window_start <= window_end <= forecast_origin
    ):
        raise ForecastPersistenceError(
            "Invalid historical input window."
        )

    forecast_type = forecast_result["forecast_type"]

    if forecast_type != "HISTORICAL_REPLAY":
        raise ForecastPersistenceError(
            "Only historical replay persistence is enabled."
        )

    predictions = forecast_result["predictions"]

    if not predictions:
        raise ForecastPersistenceError(
            "No predictions supplied."
        )

    horizons = [
        int(prediction["horizon_minutes"])
        for prediction in predictions
    ]

    if (
        len(horizons) != len(set(horizons))
        or not set(horizons).issubset(VALID_HORIZONS)
    ):
        raise ForecastPersistenceError(
            "Invalid or duplicate forecast horizons."
        )

    created_at = utc_now()
    saved = []

    with get_connection() as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")

            for prediction in predictions:
                horizon = int(
                    prediction["horizon_minutes"]
                )

                target_timestamp = parse_timestamp(
                    prediction["target_timestamp"]
                )

                expected_target = (
                    forecast_origin
                    + __import__("datetime").timedelta(
                        minutes=horizon
                    )
                )

                if target_timestamp != expected_target:
                    raise ForecastPersistenceError(
                        "Forecast target timestamp mismatch."
                    )

                predicted_value = float(
                    prediction[
                        "predicted_soil_moisture_pct"
                    ]
                )

                if not math.isfinite(predicted_value):
                    raise ForecastPersistenceError(
                        "Non-finite forecast value."
                    )

                model_version_id = prediction[
                    "model_version_id"
                ]

                model_row = connection.execute(
                    """
                    SELECT
                        model_version_id,
                        dataset_id,
                        model_name,
                        horizon_minutes
                    FROM c3_model_versions
                    WHERE model_version_id = ?
                    """,
                    (model_version_id,),
                ).fetchone()

                if model_row is None:
                    raise ForecastPersistenceError(
                        "Unknown model version."
                    )

                if (
                    model_row["dataset_id"] != dataset_id
                    or model_row["model_name"]
                    != prediction["model_name"]
                    or model_row["horizon_minutes"] != horizon
                ):
                    raise ForecastPersistenceError(
                        "Forecast/model identity mismatch."
                    )

                prediction_id = (
                    "c3prediction_"
                    + uuid.uuid4().hex[:16]
                )

                connection.execute(
                    """
                    INSERT INTO c3_forecast_predictions (
                        prediction_id,
                        dataset_id,
                        device_id,
                        episode_id,
                        forecast_origin,
                        forecast_type,
                        horizon_minutes,
                        target_timestamp,
                        model_version_id,
                        model_name,
                        predicted_soil_moisture_pct,
                        actual_soil_moisture_pct,
                        absolute_error,
                        input_window_start,
                        input_window_end,
                        sequence_length,
                        source_origin,
                        source_provenance_verified,
                        receipt_time_basis,
                        checkpoint_sha256,
                        created_at
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        NULL, NULL,
                        ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        prediction_id,
                        dataset_id,
                        device_id,
                        episode_id,
                        forecast_origin.isoformat(),
                        forecast_type,
                        horizon,
                        target_timestamp.isoformat(),
                        model_version_id,
                        prediction["model_name"],
                        predicted_value,
                        window_start.isoformat(),
                        window_end.isoformat(),
                        int(forecast_result["sequence_length"]),
                        forecast_result["source_origin"],
                        int(
                            forecast_result[
                                "source_provenance_verified"
                            ]
                        ),
                        forecast_result["receipt_time_basis"],
                        prediction["checkpoint_sha256"],
                        created_at,
                    ),
                )

                saved.append(
                    {
                        "prediction_id": prediction_id,
                        "horizon_minutes": horizon,
                        "model_name": prediction["model_name"],
                        "predicted_soil_moisture_pct": predicted_value,
                    }
                )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

    return saved


def list_forecast_predictions(
    *,
    dataset_id: str,
    device_id: str,
    episode_id: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Read previously saved forecasts."""

    initialize_forecast_persistence()

    if not 1 <= limit <= 1000:
        raise ForecastPersistenceError(
            "Limit must be between 1 and 1000."
        )

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM c3_forecast_predictions
            WHERE dataset_id = ?
              AND device_id = ?
              AND episode_id = ?
            ORDER BY
                forecast_origin DESC,
                horizon_minutes ASC
            LIMIT ?
            """,
            (
                dataset_id,
                device_id,
                episode_id,
                limit,
            ),
        ).fetchall()

    return [dict(row) for row in rows]