"""Request / response models. Feature names are exactly the ones the model was trained on."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

F = dict(allow_inf_nan=False)   # NaN / inf are rejected, send null for a missing value


class Observation(BaseModel):
    """One observation. Every feature is optional, null = missing (XGBoost handles it)."""

    model_config = ConfigDict(extra="forbid")

    # dt_s removed to match the V2 model (realistic 4-year dataset)
    value: float | None = Field(None, **F)
    delta_prev_pct_per_min: float | None = Field(None, **F)
    baseline_mean: float | None = Field(None, **F)
    baseline_std: float | None = Field(None, ge=0, **F)
    value_minus_baseline: float | None = Field(None, **F)
    stuck_run_len: float | None = Field(None, ge=0, **F)
    rain_15m_mm: float | None = Field(None, ge=0, **F)
    rain_1h_mm: float | None = Field(None, ge=0, **F)
    rain_3h_mm: float | None = Field(None, ge=0, **F)
    steps_since_rain: float | None = Field(None, ge=0, **F)
    n_neighbours_fresh: float | None = Field(None, ge=0, **F)
    neighbour_consensus_change: float | None = Field(None, **F)
    target_minus_consensus: float | None = Field(None, **F)
    neighbour_change_spread: float | None = Field(None, ge=0, **F)
    neighbour_rise_agree_frac: float | None = Field(None, ge=0, le=1, **F)
    device_voltage: float | None = Field(None, ge=0, **F)
    history_obs: float | None = Field(None, ge=0, **F)


class PredictionResult(BaseModel):
    label: str
    confidence: float
    probabilities: dict[str, float]
    missing_features: list[str]


class PredictResponse(BaseModel):
    model_version: str
    count: int
    latency_ms: float
    results: list[PredictionResult]


class HealthResponse(BaseModel):
    status: str                    # "ok" | "degraded"
    model_loaded: bool
    model_version: str | None
    uptime_s: float
    error: str | None


class ModelInfoResponse(BaseModel):
    name: str
    version: str
    trained_at: str | None
    format: str
    objective: str | None
    n_features: int
    features: list[str]
    classes: list[str]
    class_order_source: str        # "meta file" | "environment" | "default"
    class_order_verified: bool


class MetricsResponse(BaseModel):
    available: bool
    macro_f1: float | None = None
    anomaly_recall: float | None = None
    valid_event_recall: float | None = None
    evaluated_on: str | None = None


class RecentPrediction(BaseModel):
    id: str
    timestamp: str
    label: str
    confidence: float
    probabilities: dict[str, float]
    input: dict[str, Any]
    source: str