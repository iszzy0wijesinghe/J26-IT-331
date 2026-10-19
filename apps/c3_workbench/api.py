"""Standalone C3 research API: trained M4 inference and validation examples only."""
from __future__ import annotations

import gzip
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from apps.c3_workbench.dataset_routes import router as dataset_router
from apps.c3_workbench.csv_routes import router as csv_router
from apps.c3_workbench.golden_routes import router as golden_router
from components.c3_forecasting.inference.m4_predictor import C3M4Predictor
from apps.c3_workbench.golden_backup_routes import (
    router as golden_backup_router,
)
from apps.c3_workbench.golden_explorer_routes import (
    router as golden_explorer_router,
)
from apps.c3_workbench.training_routes import (
    router as training_router,
)
from apps.c3_workbench.training_readiness_routes import (
    router as training_readiness_router,

)


ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_DIR = ROOT / "data" / "processed" / "c3_m4_results"
VALIDATION_DATA = ROOT / "data" / "processed" / "c3_v2" / "validation.jsonl.gz"

app = FastAPI(
    title="GeoNex C3 Research Workbench",
    version="0.3.0",
)

# Register specific dataset routes before dynamic dataset routes.
# Otherwise, /datasets/{dataset_id} may intercept /datasets/golden.

app.include_router(csv_router)
app.include_router(golden_router)
app.include_router(dataset_router)
app.include_router(golden_backup_router)
app.include_router(golden_explorer_router)
app.include_router(training_router)
app.include_router(training_readiness_router)

class ForecastRequest(BaseModel):
    ablation: Literal["A", "B", "C"] = "A"
    horizon_minutes: Literal[15, 30, 60] = 15
    temporal_sequence: dict[str, Any] = Field(
        description="C3 temporal sequence containing 'steps', compatible with extract_m4_sequence"
    )


@lru_cache(maxsize=9)
def load_predictor(ablation: str, horizon: int) -> C3M4Predictor:
    path = CHECKPOINT_DIR / f"m4_{ablation.lower()}_{horizon}min.pt"
    if not path.is_file():
        raise FileNotFoundError(f"Checkpoint missing: {path.relative_to(ROOT)}")
    return C3M4Predictor(path, device="cpu")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "component": "c3", "scope": "standalone research demonstration"}


@app.get("/models")
def models() -> dict[str, Any]:
    return {
        "models": [
            {
                "model": f"M4-{ablation}",
                "horizon_minutes": horizon,
                "available": (CHECKPOINT_DIR / f"m4_{ablation.lower()}_{horizon}min.pt").is_file(),
            }
            for horizon in (15, 30, 60)
            for ablation in ("A", "B", "C")
        ],
        "note": "Availability checks checkpoint files; loading occurs at prediction time.",
    }


@app.get("/examples")
def examples(
    horizon_minutes: int = Query(
        default=15,
        description="Forecast horizon in minutes: 15, 30 or 60",
    ),
    limit: int = Query(default=10, ge=1, le=25),
    offset: int = Query(default=0, ge=0, le=100000),
) -> dict[str, Any]:

    if horizon_minutes not in (15, 30, 60):
        raise HTTPException(
            status_code=422,
            detail="horizon_minutes must be 15, 30 or 60",
        )
    """Return paged synthetic validation examples; never read the held-out test split."""
    if not VALIDATION_DATA.is_file():
        raise HTTPException(status_code=404, detail="Synthetic validation dataset not found")

    items: list[dict[str, Any]] = []
    matched = 0
    has_more = False
    try:
        with gzip.open(VALIDATION_DATA, "rt", encoding="utf-8") as stream:
            for line in stream:
                record = json.loads(line)
                target = record.get("target", {})
                if target.get("requested_horizon_minutes") != horizon_minutes:
                    continue
                if matched < offset:
                    matched += 1
                    continue
                if len(items) >= limit:
                    has_more = True
                    break
                sequence = record.get("input_sequence", {})
                if not isinstance(sequence, dict) or not isinstance(sequence.get("steps"), list):
                    continue
                items.append({
                    "id": f"{record.get('episode_id', 'unknown')}:{record.get('forecast_origin', '')}:{matched}",
                    "episode_id": record.get("episode_id"),
                    "device_id": record.get("device_id"),
                    "forecast_origin": record.get("forecast_origin"),
                    "target_observed_at": target.get("observed_at"),
                    "actual_horizon_seconds": target.get("actual_horizon_seconds"),
                    "actual_soil_moisture_percent": target.get("value"),
                    "temporal_sequence": sequence,
                })
                matched += 1
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Cannot read validation dataset") from exc

    return {
        "dataset": "c3_v2 synthetic validation",
        "horizon_minutes": horizon_minutes,
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
        "examples": items,
        "warning": "Synthetic validation examples only; held-out test data is not exposed.",
    }


@app.post("/predict")
def predict(request: ForecastRequest) -> dict[str, Any]:
    try:
        predictor = load_predictor(request.ablation, request.horizon_minutes)
        value = predictor.predict(request.temporal_sequence)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TypeError, ValueError, KeyError, IndexError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid temporal sequence: {exc}") from exc
    return {
        "model": f"M4-{request.ablation}",
        "horizon_minutes": request.horizon_minutes,
        "forecast_soil_moisture_percent": float(value),
        "warning": "Synthetic-data research forecast; NOT a landslide probability or safety alert.",
    }
