"""GeoNex C3 Golden Database historical forecasting reader."""

from __future__ import annotations

from datetime import UTC, datetime

from apps.c3_workbench.golden_db import (
    get_connection,
    initialize_golden_database,
)

SENSOR_COLUMNS = (
    "soil_moisture_pct",
    "rainfall_proxy_counts",
    "tilt_deg",
    "vibration_g",
    "fsr_adc",
    "air_temperature_c",
    "humidity_pct",
)

MAX_SEQUENCE_LENGTH = 32


class ForecastingReaderError(ValueError):
    pass


def parse_timestamp(value: str) -> datetime:
    """Parse a timestamp and normalize it to UTC."""

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except (TypeError, ValueError) as exc:
        raise ForecastingReaderError(
            f"Invalid timestamp: {value}"
        ) from exc

    if parsed.tzinfo is None:
        raise ForecastingReaderError(
            "Forecast timestamps must include timezone information."
        )

    return parsed.astimezone(UTC)


def load_historical_sequence(
    dataset_id: str,
    device_id: str,
    episode_id: str,
    forecast_origin: str,
    max_sequence_length: int = MAX_SEQUENCE_LENGTH,
) -> dict:
    """
    Load historical Golden observations for one device and episode.

    Never loads observations after forecast_origin.
    """

    initialize_golden_database()

    if max_sequence_length < 3 or max_sequence_length > 32:
        raise ForecastingReaderError(
            "Sequence length must be between 3 and 32."
        )

    origin_dt = parse_timestamp(forecast_origin)

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT
                observation_id,
                dataset_id,
                device_id,
                episode_id,
                timestamp,
                operating_mode,
                soil_moisture_pct,
                rainfall_proxy_counts,
                tilt_deg,
                vibration_g,
                fsr_adc,
                air_temperature_c,
                humidity_pct,
                created_at

            FROM c3_golden_observations

            WHERE dataset_id = ?
              AND device_id = ?
              AND episode_id = ?

            ORDER BY timestamp ASC, observation_id ASC
            """,
            (
                dataset_id,
                device_id,
                episode_id,
            ),
        ).fetchall()

    if not rows:
        raise ForecastingReaderError(
            "No observations found for the selected dataset/device/episode."
        )

    historical = []

    for row in rows:
        observation = dict(row)

        observed_at = parse_timestamp(
            observation["timestamp"]
        )

        if observed_at <= origin_dt:
            historical.append(observation)

    historical = historical[-max_sequence_length:]

    if len(historical) < 3:
        raise ForecastingReaderError(
            "At least 3 historical observations are required."
        )

    for observation in historical:
        for sensor in SENSOR_COLUMNS:
            if observation[sensor] is None:
                raise ForecastingReaderError(
                    f"Missing {sensor} in observation "
                    f"{observation['observation_id']}"
                )

    return {
        "dataset_id": dataset_id,
        "device_id": device_id,
        "episode_id": episode_id,
        "forecast_origin": origin_dt.isoformat(),
        "sequence_length": len(historical),
        "window_start": historical[0]["timestamp"],
        "window_end": historical[-1]["timestamp"],
        "observations": historical,
        "source_origin": "GOLDEN_CSV",
        "forecast_type": "HISTORICAL_REPLAY",
    }