

from apps.c3_workbench.forecasting_reader import (
    ForecastingReaderError, load_historical_sequence, parse_timestamp,
)
from apps.c3_workbench.golden_db import get_connection, initialize_golden_database
from datetime import timedelta
from apps.c3_workbench.m5_inference_service import (
    M5InferenceError,
    predict_m5,
)

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
    
    
@router.post("/m5/generate")
def generate_m5_forecasts(
    request: GenerateForecastRequest,
) -> dict[str, Any]:
    """
    Generate experimental M5 multivariate forecasts.

    Uses historical Golden Database observations.
    Does not modify existing active-model assignments
    or persist predictions into legacy forecast tables.
    """

    try:
        history = load_historical_sequence(
            dataset_id=request.dataset_id,
            device_id=request.device_id,
            episode_id=request.episode_id,
            forecast_origin=request.forecast_origin,
            max_sequence_length=32,
        )

        result = predict_m5(
            history["observations"]
        )

    except (
        ForecastingReaderError,
        M5InferenceError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return {
        "status": "completed",
        "forecast_type": "M5_EXPERIMENTAL_HISTORICAL_REPLAY",
        "dataset_id": request.dataset_id,
        "device_id": request.device_id,
        "episode_id": request.episode_id,
        "forecast_origin": history["forecast_origin"],
        "window_start": history["window_start"],
        "window_end": history["window_end"],
        "sequence_length": history["sequence_length"],
        "model": result["model"],
        "model_version": result["model_version"],
        "sensor_features": result["sensor_features"],
        "forecast_horizons": result["forecast_horizons"],
        "predictions": result["predictions"],
        "dataset_type": result["dataset_type"],
        "research_status": result["research_status"],
        "warning": result["warning"],
    }

# Operational interface: model training dataset IDs are not frontend inputs.
# Legacy dataset/episode identifiers are internal lineage keys in the Golden DB.
class OperationalM5Request(BaseModel):
    device_id: str = Field(min_length=1)
    forecast_origin: str = Field(min_length=1)
    target_timestamp: str | None = None


@router.get("/operational/devices")
def operational_devices() -> dict[str, Any]:
    initialize_golden_database()
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT DISTINCT device_id FROM c3_golden_observations ORDER BY device_id"
        ).fetchall()
    return {"devices": [row["device_id"] for row in rows]}


@router.get("/operational/devices/{device_id}/latest")
def operational_latest_observation(device_id: str) -> dict[str, Any]:
    """Latest observed timestamp, never a fabricated current-time observation."""
    initialize_golden_database()
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT timestamp FROM c3_golden_observations WHERE device_id = ?",
            (device_id,),
        ).fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="No Golden Database observations for device")
    latest = max(parse_timestamp(row["timestamp"]) for row in rows)
    return {"device_id": device_id, "latest_observation": latest.isoformat()}


@router.post("/operational/m5/generate")
def operational_m5_forecast(request: OperationalM5Request) -> dict[str, Any]:
    try:
        origin = parse_timestamp(request.forecast_origin)
        target = parse_timestamp(request.target_timestamp) if request.target_timestamp else None
        if target is not None and target <= origin:
            raise ValueError("Target timestamp must be after forecast origin.")
        if target is not None:
            horizon_seconds = (target - origin).total_seconds()
            if horizon_seconds not in (900, 1800, 3600):
                raise ValueError(
                    "The available M5 checkpoint is validated for its configured "
                    "+15, +30, +60-minute outputs only. Arbitrary timestamps "
                    "require a separately trained and evaluated model."
                )
        initialize_golden_database()
        with get_connection() as connection:
            rows = connection.execute(
                """SELECT dataset_id, episode_id, timestamp
                   FROM c3_golden_observations
                   WHERE device_id = ?
                   ORDER BY timestamp DESC, observation_id DESC""",
                (request.device_id,),
            ).fetchall()
        # Choose the most recent observed episode at/before origin;
        # never use data from the requested future target.
        eligible = [row for row in rows if parse_timestamp(row["timestamp"]) <= origin]
        if not eligible:
            raise ValueError("No Golden Database observations exist for this device at or before the selected origin.")
        chosen = eligible[0]
        history = load_historical_sequence(
            dataset_id=chosen["dataset_id"],
            device_id=request.device_id,
            episode_id=chosen["episode_id"],
            forecast_origin=origin.isoformat(),
            max_sequence_length=32,
        )
        result = predict_m5(history["observations"])
        forecasts = [
            {**item, "target_timestamp": (origin + timedelta(minutes=item["horizon_minutes"])).isoformat()}
            for item in result["predictions"]
        ]
        if target is not None:
            forecasts = [item for item in forecasts if parse_timestamp(item["target_timestamp"]) == target]
        return {
            **result,
            "status": "completed",
            "forecast_type": "GOLDEN_DATABASE_MODEL_INFERENCE",
            "device_id": request.device_id,
            "forecast_origin": origin.isoformat(),
            "window_start": history["window_start"],
            "window_end": history["window_end"],
            "predictions": forecasts,
            "risk_status": "NOT_AVAILABLE_NO_VALIDATED_RISK_MODEL",
            "alert_status": "NOT_AVAILABLE_NO_VALIDATED_DECISION_ENGINE",
            "data_source": "GOLDEN_DATABASE",
        }
    except (ForecastingReaderError, M5InferenceError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
