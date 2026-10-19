"""Standalone, read-only M4 inference API. No training or test-split access."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from components.c3_forecasting.inference.m4_predictor import C3M4Predictor

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_DIR = ROOT / "data" / "processed" / "c3_m4_results"
app = FastAPI(title="GeoNex C3 Research Workbench", version="0.1.0")


class ForecastRequest(BaseModel):
    ablation: Literal["A", "B", "C"] = "A"
    horizon_minutes: Literal[15, 30, 60] = 15
    temporal_sequence: dict[str, Any] = Field(
        description="C3 temporal sequence record with 'steps' compatible with extract_m4_sequence"
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
        "note": "Availability checks files only; checkpoint loading occurs at prediction time.",
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
        "forecast_soil_moisture_percent": value,
        "warning": "Synthetic-data research forecast; NOT a landslide probability or safety alert.",
    }
