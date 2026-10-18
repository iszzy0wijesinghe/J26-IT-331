"""Canonical CSV schema for GeoNex C3 forecasting datasets.

The sensor feature list is imported directly from the existing
forecasting implementation to prevent schema drift.
"""

from __future__ import annotations

from dataclasses import dataclass

from components.c3_forecasting.preprocessing.gru_dataset import (
    SENSOR_NAMES,
)
from components.c3_forecasting.preprocessing.m4_features import (
    OPERATING_MODES,
)

CSV_SCHEMA_VERSION = "c3-observations-v1"

# Raw CSV metadata columns.
REQUIRED_METADATA_COLUMNS = (
    "device_id",
    "episode_id",
    "timestamp",
    "operating_mode",
)

# Soil moisture is the forecasting target.
TARGET_COLUMN = "soil_moisture_pct"

# Reuse the model's authoritative sensor names.
SENSOR_COLUMNS = tuple(SENSOR_NAMES)

# Missing readings are permitted for sensor inputs, subject
# to later data-quality and forecast-feasibility checks.
REQUIRED_COLUMNS = (
    *REQUIRED_METADATA_COLUMNS,
    *SENSOR_COLUMNS,
)

SUPPORTED_OPERATING_MODES = frozenset(OPERATING_MODES)

SUPPORTED_FORECAST_HORIZONS_MINUTES = (15, 30, 60)


@dataclass(frozen=True)
class C3CSVSchema:
    version: str
    required_columns: tuple[str, ...]
    metadata_columns: tuple[str, ...]
    sensor_columns: tuple[str, ...]
    target_column: str
    operating_modes: tuple[str, ...]
    forecast_horizons_minutes: tuple[int, ...]


def get_csv_schema() -> C3CSVSchema:
    """Return the canonical CSV import contract."""

    if len(SENSOR_COLUMNS) != 7:
        raise RuntimeError(
            "C3 CSV schema expects exactly seven sensor features; "
            f"found {len(SENSOR_COLUMNS)}."
        )

    if TARGET_COLUMN not in SENSOR_COLUMNS:
        raise RuntimeError(
            "Soil moisture must be one of the model's sensor features."
        )

    if len(set(REQUIRED_COLUMNS)) != len(REQUIRED_COLUMNS):
        raise RuntimeError(
            "C3 CSV schema contains duplicate required columns."
        )

    return C3CSVSchema(
        version=CSV_SCHEMA_VERSION,
        required_columns=REQUIRED_COLUMNS,
        metadata_columns=REQUIRED_METADATA_COLUMNS,
        sensor_columns=SENSOR_COLUMNS,
        target_column=TARGET_COLUMN,
        operating_modes=tuple(OPERATING_MODES),
        forecast_horizons_minutes=(
            SUPPORTED_FORECAST_HORIZONS_MINUTES
        ),
    )