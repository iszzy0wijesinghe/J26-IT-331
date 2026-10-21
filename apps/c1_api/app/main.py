"""GeoNex C1 API: sensor credibility classification (CLEAN / ANOMALY / VALID_EVENT).

run from apps/c1_api:
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8033 --reload
docs: http://127.0.0.1:8033/docs
"""
from __future__ import annotations

import io
import logging
import threading
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from fastapi import Body, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, load_settings
from .inference import C1Predictor, ModelNotReady
from .schemas import (
    HealthResponse, MetricsResponse, ModelInfoResponse, Observation,
    PredictionResult, PredictResponse, RecentPrediction,
)

logger = logging.getLogger("c1_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@dataclass
class AppState:
    settings: Settings
    started: float = field(default_factory=time.time)
    predictor: C1Predictor | None = None
    error: str | None = None
    history: deque = field(default_factory=deque)
    lock: threading.Lock = field(default_factory=threading.Lock)


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state = AppState(settings=cfg, history=deque(maxlen=cfg.history_size))
        try:
            state.predictor = C1Predictor(cfg.model_path, cfg.meta_path, cfg.env_class_order)
            logger.info("model loaded: %s (%s)", state.predictor.version, state.predictor.class_source)
        except ModelNotReady as exc:
            state.error = str(exc)
            logger.error("model not ready: %s", exc)
        except Exception as exc:
            state.error = f"{type(exc).__name__}: {exc}"
            logger.exception("unexpected error while loading the model")
        app.state.c1 = state
        yield

    app = FastAPI(
        title="GeoNex C1 Credibility API",
        version="0.1.0",
        description="Research API for sensor credibility classification (CLEAN / ANOMALY / VALID_EVENT).",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(cfg.cors_origins),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    def state_of(request: Request) -> AppState:
        return request.app.state.c1

    def predictor_of(request: Request) -> C1Predictor:
        state = state_of(request)
        if state.predictor is None:
            raise HTTPException(status_code=503, detail=f"C1 model is not loaded: {state.error}")
        return state.predictor

    @app.get("/health", response_model=HealthResponse)
    def health(request: Request) -> HealthResponse:
        s = state_of(request)
        return HealthResponse(
            status="ok" if s.predictor else "degraded",
            model_loaded=s.predictor is not None,
            model_version=s.predictor.version if s.predictor else None,
            uptime_s=round(time.time() - s.started, 1),
            error=s.error,
        )

    @app.get("/models", response_model=ModelInfoResponse)
    def models(request: Request) -> dict[str, Any]:
        return predictor_of(request).info()

    @app.get("/metrics", response_model=MetricsResponse)
    def metrics(request: Request) -> dict[str, Any]:
        s = state_of(request)
        return s.predictor.metrics() if s.predictor else {"available": False}

    @app.post("/predict", response_model=PredictResponse)
    def predict(request: Request, payload: Observation | list[Observation] = Body(...)) -> PredictResponse:
        predictor = predictor_of(request)
        state = state_of(request)

        observations = payload if isinstance(payload, list) else [payload]
        if not observations:
            raise HTTPException(status_code=422, detail="send at least one observation")
        if len(observations) > cfg.max_batch:
            raise HTTPException(status_code=422, detail=f"batch too large: {len(observations)} > {cfg.max_batch}")

        rows = [o.model_dump() for o in observations]
        started = time.perf_counter()
        results = predictor.predict(rows)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with state.lock:
            for row, res in zip(rows, results):
                state.history.appendleft({
                    "id": uuid.uuid4().hex[:8], "timestamp": now, "label": res["label"],
                    "confidence": res["confidence"], "probabilities": res["probabilities"],
                    "input": row, "source": "api",
                })
        return PredictResponse(
            model_version=predictor.version,
            count=len(results),
            latency_ms=latency_ms,
            results=[PredictionResult(**r) for r in results],
        )

    @app.post("/predict/csv", response_model=PredictResponse)
    async def predict_csv(request: Request, file: UploadFile = File(...)) -> PredictResponse:
        predictor = predictor_of(request)
        state = state_of(request)

        if not file.filename.endswith(".csv"):
            raise HTTPException(status_code=422, detail="File must be a CSV")

        try:
            contents = await file.read()
            df = pd.read_csv(io.BytesIO(contents))
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not read CSV: {exc}")

        if df.empty:
            raise HTTPException(status_code=422, detail="CSV is empty")
        if len(df) > cfg.max_batch:
            raise HTTPException(status_code=422, detail=f"CSV has too many rows: {len(df)} > {cfg.max_batch}")

        rows = df.to_dict(orient="records")
        started = time.perf_counter()
        results = predictor.predict(rows)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with state.lock:
            for row, res in zip(rows, results):
                state.history.appendleft({
                    "id": uuid.uuid4().hex[:8], "timestamp": now, "label": res["label"],
                    "confidence": res["confidence"], "probabilities": res["probabilities"],
                    "input": row, "source": "csv_upload",
                })

        return PredictResponse(
            model_version=predictor.version,
            count=len(results),
            latency_ms=latency_ms,
            results=[PredictionResult(**r) for r in results],
        )

    @app.get("/predictions/recent", response_model=list[RecentPrediction])
    def recent(request: Request, limit: int = Query(20, ge=1, le=200)) -> list[dict[str, Any]]:
        state = state_of(request)
        with state.lock:
            return list(state.history)[:limit]

    return app


app = create_app()