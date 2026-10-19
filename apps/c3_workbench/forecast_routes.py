"""GeoNex C3 active-model forecasting API.

Research safeguards:
- Uses existing activated forecasting models.
- Generates 15/30/60-minute forecasts together.
- Persists forecasts atomically.
- Returns existing predictions for identical requests.
- Exposes historical-replay forecasts only.
- Does not trigger model training or activation.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from apps.c3_workbench.forecast_persistence import (
    ForecastPersistenceError,
    list_forecast_predictions,
    save_forecast_predictions,
)
from apps.c3_workbench.forecasting_engine import (
    ForecastingEngineError,
    generate_active_forecasts,
)

router = APIRouter(
    prefix="/research/forecasts",
    tags=["C3 Research Forecasts"],
)


class GenerateForecastRequest(BaseModel):
    dataset_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    episode_id: str = Field(min_length=1)
    forecast_origin: str = Field(min_length=1)


@router.post("/generate")
def generate_forecasts(
    request: GenerateForecastRequest,
) -> dict[str, Any]:
    """Generate and persist active-model historical forecasts."""

    try:
        result = generate_active_forecasts(
            dataset_id=request.dataset_id,
            device_id=request.device_id,
            episode_id=request.episode_id,
            forecast_origin=request.forecast_origin,
        )

        saved = save_forecast_predictions(result)

    except (ForecastingEngineError, ForecastPersistenceError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return {
        "status": "completed",
        "forecast_type": "HISTORICAL_REPLAY",
        "dataset_id": result["dataset_id"],
        "device_id": result["device_id"],
        "episode_id": result["episode_id"],
        "forecast_origin": result["forecast_origin"],
        "target_feature": result["target_feature"],
        "predictions": saved,
        "limitations": result["limitations"],
        "warning": (
            "Synthetic-data research forecasts only. "
            "Not landslide probabilities or safety alerts."
        ),
    }


@router.get("")
def get_forecasts(
    dataset_id: str = Query(min_length=1),
    device_id: str = Query(min_length=1),
    episode_id: str = Query(min_length=1),
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    """Retrieve previously saved research forecasts."""

    try:
        predictions = list_forecast_predictions(
            dataset_id=dataset_id,
            device_id=device_id,
            episode_id=episode_id,
            limit=limit,
        )

    except ForecastPersistenceError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return {
        "dataset_id": dataset_id,
        "device_id": device_id,
        "episode_id": episode_id,
        "total": len(predictions),
        "predictions": predictions,
        "warning": (
            "Research forecasts are soil moisture estimates, "
            "not landslide probabilities."
        ),
    }