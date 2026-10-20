"""Standalone C2 diagnostic API using the existing trained model."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator

from components.c2_diagnostics.backup_pipe.verification import (
    verify_backup_telemetry,
)
from components.c2_diagnostics.diagnosis.predict import (
    load_model,
    predict_diagnosis,
)

ROOT = Path(__file__).resolve().parents[2]

app = FastAPI(
    title="GeoNex C2 Diagnostics API",
    version="0.1.0",
    description=(
        "Research API for sensor-silence diagnostics and "
        "deterministic backup telemetry verification."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@lru_cache(maxsize=1)
def get_model():
    """Load the existing trained C2 model once per process."""
    return load_model()


class PredictionRequest(BaseModel):
    """Structured sensor features used by the existing C2 model."""

    model_config = ConfigDict(extra="forbid")

    features: dict[str, float] = Field(
        description="The 25 named numeric features expected by the trained model."
    )

    @model_validator(mode="after")
    def validate_feature_schema(self) -> PredictionRequest:
        expected = set(get_model().feature_names_in_)
        provided = set(self.features)

        missing = sorted(expected - provided)
        extra = sorted(provided - expected)

        if missing:
            raise ValueError(f"Missing required features: {missing}")

        if extra:
            raise ValueError(f"Unexpected features: {extra}")

        return self


class BackupVerificationRequest(BaseModel):
    """Primary and backup telemetry to compare deterministically."""

    backup_reachable: bool
    primary_values: dict[str, float] | None = None
    backup_values: dict[str, float] | None = None
    tolerance: float = Field(default=0.5, ge=0)


@app.get("/health")
def health() -> dict[str, str]:
    """Check API availability and model loading."""
    try:
        model = get_model()
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"C2 model unavailable: {exc}",
        ) from exc

    return {
        "status": "ok",
        "component": "c2",
        "model_status": "loaded",
        "model_type": type(model).__name__,
    }


@app.get("/models")
def models() -> dict[str, Any]:
    """Describe the existing model without training another model."""
    try:
        model = get_model()
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"C2 model unavailable: {exc}",
        ) from exc

    return {
        "component": "c2",
        "model_type": type(model).__name__,
        "feature_count": len(model.feature_names_in_),
        "features": list(model.feature_names_in_),
        "classes": [str(label) for label in model.classes_],
        "model_path": str(
            Path("models") / "c2_diagnostics" / "random_forest.joblib"
        ),
        "scope": "existing trained model; research demonstration",
    }


@app.post("/predict")
def predict(request: PredictionRequest) -> dict[str, Any]:
    """Predict a diagnosis from structured sensor features."""
    try:
        model = get_model()
        features = pd.DataFrame([request.features])
        diagnosis = predict_diagnosis(features, model=model)[0]

        probabilities = model.predict_proba(features)[0]
        classes = [str(label) for label in model.classes_]

    except (FileNotFoundError, OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    except (TypeError, KeyError, IndexError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid diagnostic input: {exc}",
        ) from exc

    return {
        "component": "c2",
        "diagnosis": diagnosis,
        "class_probabilities": {
            label: float(probability)
            for label, probability in zip(classes, probabilities)
        },
        "model_type": type(model).__name__,
        "feature_count": len(request.features),
        "warning": (
            "Research demonstration using a synthetic-data-trained model. "
            "Predictions are not validated safety alerts."
        ),
    }


@app.post("/verify-backup")
def verify_backup(
    request: BackupVerificationRequest,
) -> dict[str, Any]:
    """Compare primary and backup telemetry using existing C2 logic."""
    try:
        result = verify_backup_telemetry(
            backup_reachable=request.backup_reachable,
            primary_values=request.primary_values,
            backup_values=request.backup_values,
            tolerance=request.tolerance,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "component": "c2",
        "verified": result.verified,
        "reason": result.reason,
        "maximum_deviation": result.deviation,
        "verification_method": "deterministic_comparison",
        "note": (
            "Verification checks telemetry consistency; it does not prove "
            "that the backup sensor is correctly calibrated or trustworthy."
        ),
    }
