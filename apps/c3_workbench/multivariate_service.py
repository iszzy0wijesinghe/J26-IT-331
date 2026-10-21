"""
GeoNex C3 Multivariate Forecasting Service.

Provides a stable service interface for multivariate
Golden Database forecasting.

Does not modify existing active-model assignments.
"""

from __future__ import annotations

from typing import Any

from components.c3_forecasting.inference.multivariate_forecaster import (
    generate_multivariate_forecasts,
)


def run_multivariate_forecasting(
    *,
    dataset_id: str,
    device_id: str,
    episode_id: str,
    forecast_origin: str,
) -> dict[str, Any]:

    result = generate_multivariate_forecasts(
        dataset_id=dataset_id,
        device_id=device_id,
        episode_id=episode_id,
        forecast_origin=forecast_origin,
    )

    return {
        "status": "success",
        "component": "C3",
        "forecasting_capability": "MULTIVARIATE",
        "data": result,
    }