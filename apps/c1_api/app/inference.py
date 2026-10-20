"""Loads the trained C1 XGBoost model and turns observations into predictions.

NOTE: this loads models/c1/c1_xgboost_v1.json directly with xgboost, using the same
18 features the model was trained on. If C1CredibilityService
(components/c1_credibility/inference/predict.py) does extra work (clipping, feature
engineering, class mapping), call it from `C1Predictor._predict_proba` instead, that
method is the only place that touches the model.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import xgboost as xgb

from .config import DEFAULT_CLASS_ORDER

logger = logging.getLogger("c1_api")

# the model's training feature order
FEATURES: tuple[str, ...] = (
    "dt_s", "value", "delta_prev_pct_per_min", "baseline_mean",
    "baseline_std", "value_minus_baseline", "stuck_run_len",
    "rain_15m_mm", "rain_1h_mm", "rain_3h_mm", "steps_since_rain",
    "n_neighbours_fresh", "neighbour_consensus_change",
    "target_minus_consensus", "neighbour_change_spread",
    "neighbour_rise_agree_frac", "device_voltage", "history_obs",
)


class ModelNotReady(RuntimeError):
    """The model (or its meta file) could not be loaded."""


class C1Predictor:
    def __init__(self, model_path: Path, meta_path: Path, env_class_order: Sequence[str] = ()) -> None:
        if not model_path.is_file():
            raise ModelNotReady(f"model file not found: {model_path}")
        self.model_path = model_path
        self.meta = self._read_meta(meta_path)

        self.booster = xgb.Booster()
        try:
            self.booster.load_model(str(model_path))
        except xgb.core.XGBoostError as exc:
            raise ModelNotReady(f"could not load {model_path.name}: {exc}") from exc

        self.features = self._resolve_features()
        self.classes, self.class_source = self._resolve_classes(env_class_order)
        self._check_output_width()
        self._lock = threading.Lock()   # one predict at a time, simple and safe

    # ---- loading helpers ----

    @staticmethod
    def _read_meta(path: Path) -> dict[str, Any]:
        if not path.is_file():
            logger.warning("no meta file at %s, class order falls back to env/default", path)
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ModelNotReady(f"could not read meta file {path}: {exc}") from exc

    def _resolve_features(self) -> tuple[str, ...]:
        names = self.booster.feature_names
        if not names:                       # model saved without names, trust the API list
            return FEATURES
        if set(names) != set(FEATURES):
            only_model = sorted(set(names) - set(FEATURES))
            only_api = sorted(set(FEATURES) - set(names))
            raise ModelNotReady(f"model features differ from the API list, only in model: {only_model}, only in API: {only_api}")
        return tuple(names)                 # use the model's own order

    def _resolve_classes(self, env_order: Sequence[str]) -> tuple[tuple[str, ...], str]:
        meta_classes = self.meta.get("classes")
        if meta_classes:
            return tuple(meta_classes), "meta file"
        if env_order:
            return tuple(env_order), "environment"
        logger.warning("class order not confirmed, using default %s. Add \"classes\" to the meta file.", DEFAULT_CLASS_ORDER)
        return DEFAULT_CLASS_ORDER, "default"

    def _check_output_width(self) -> None:
        probe = self._predict_proba(np.full((1, len(self.features)), np.nan, dtype=np.float32))
        if probe.ndim != 2 or probe.shape[1] != len(self.classes):
            raise ModelNotReady(f"model output shape {probe.shape} does not match {len(self.classes)} classes, "
                                "it must be a multi:softprob model")

    # ---- the single place that touches the model ----

    def _predict_proba(self, X: np.ndarray) -> np.ndarray:
        matrix = xgb.DMatrix(X, feature_names=list(self.features), missing=np.nan)
        return self.booster.predict(matrix)

    # ---- public api ----

    @property
    def version(self) -> str:
        return str(self.meta.get("version") or self.model_path.stem)

    def info(self) -> dict[str, Any]:
        try:
            objective = json.loads(self.booster.save_config())["learner"]["objective"]["name"]
        except (KeyError, ValueError, TypeError):
            objective = None
        return {
            "name": "C1 sensor credibility classifier",
            "version": self.version,
            "trained_at": self.meta.get("trained_at"),
            "format": "xgboost-json",
            "objective": objective,
            "n_features": len(self.features),
            "features": list(self.features),
            "classes": list(self.classes),
            "class_order_source": self.class_source,
            "class_order_verified": self.class_source != "default",
        }

    def metrics(self) -> dict[str, Any]:
        m = self.meta.get("metrics") or {}
        return {
            "available": bool(m),
            "macro_f1": m.get("macro_f1"),
            "anomaly_recall": m.get("anomaly_recall"),
            "valid_event_recall": m.get("valid_event_recall"),
            "evaluated_on": m.get("evaluated_on"),
        }

    def predict(self, rows: Sequence[Mapping[str, float | None]]) -> list[dict[str, Any]]:
        X = np.full((len(rows), len(self.features)), np.nan, dtype=np.float32)
        for i, row in enumerate(rows):
            for j, name in enumerate(self.features):
                value = row.get(name)
                if value is not None:
                    X[i, j] = value
        with self._lock:
            proba = self._predict_proba(X)

        results = []
        for row, p in zip(rows, proba):
            k = int(np.argmax(p))
            results.append({
                "label": self.classes[k],
                "confidence": round(float(p[k]), 6),
                "probabilities": {c: round(float(p[i]), 6) for i, c in enumerate(self.classes)},
                "missing_features": [f for f in self.features if row.get(f) is None],
            })
        return results
