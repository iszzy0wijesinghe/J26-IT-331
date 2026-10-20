"""API tests. They train a tiny throw-away model, so no real model file is needed."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import xgboost as xgb
from fastapi.testclient import TestClient

from app.config import Settings
from app.inference import FEATURES
from app.main import create_app

CLASSES = ["CLEAN", "ANOMALY", "VALID_EVENT"]


def _train_tiny_model(path: Path) -> None:
    rng = np.random.default_rng(0)
    X = rng.normal(size=(300, len(FEATURES)))
    y = rng.integers(0, 3, size=300)
    booster = xgb.train(
        {"objective": "multi:softprob", "num_class": 3, "max_depth": 2},
        xgb.DMatrix(X, label=y, feature_names=list(FEATURES)),
        num_boost_round=5,
    )
    booster.save_model(str(path))


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    model = tmp_path / "c1_test.json"
    _train_tiny_model(model)
    meta = tmp_path / "c1_test_meta.json"
    meta.write_text(json.dumps({
        "version": "test-1", "classes": CLASSES, "trained_at": "2026-10-20",
        "metrics": {"macro_f1": 0.9, "anomaly_recall": 0.8, "valid_event_recall": 0.85, "evaluated_on": "test split"},
    }))
    return Settings(model, meta, ("http://127.0.0.1:5173",), (), 5, 50)


@pytest.fixture()
def client(settings: Settings):
    with TestClient(create_app(settings)) as c:
        yield c


SAMPLE = {"dt_s": 300, "value": 32.8, "baseline_mean": 32.7, "rain_1h_mm": 0.0, "n_neighbours_fresh": 3, "device_voltage": 3.9}


def test_health_and_models(client):
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["model_loaded"] and h["model_version"] == "test-1"
    m = client.get("/models").json()
    assert m["n_features"] == 18 and m["classes"] == CLASSES and m["class_order_verified"] is True


def test_metrics_come_from_meta(client):
    m = client.get("/metrics").json()
    assert m["available"] and m["macro_f1"] == 0.9 and m["valid_event_recall"] == 0.85


def test_predict_single_with_missing_features(client):
    r = client.post("/predict", json=SAMPLE).json()
    assert r["count"] == 1 and r["model_version"] == "test-1"
    res = r["results"][0]
    assert res["label"] in CLASSES and abs(sum(res["probabilities"].values()) - 1) < 1e-3
    assert res["confidence"] == max(res["probabilities"].values())
    assert "baseline_std" in res["missing_features"] and "value" not in res["missing_features"]


def test_predict_batch_and_history(client):
    r = client.post("/predict", json=[SAMPLE, {**SAMPLE, "value": 61.0}, {}]).json()
    assert r["count"] == 3
    recent = client.get("/predictions/recent?limit=2").json()
    assert len(recent) == 2 and recent[0]["source"] == "api" and recent[0]["input"]["value"] is None  # newest first


@pytest.mark.parametrize("bad", [
    {"rain_1h_mm": -1}, {"neighbour_rise_agree_frac": 1.5}, {"dt_s": 0}, {"unknown_feature": 1}, {"value": "abc"},
])
def test_validation_errors(client, bad):
    assert client.post("/predict", json=bad).status_code == 422


def test_empty_and_oversized_batches(client):
    assert client.post("/predict", json=[]).status_code == 422
    assert client.post("/predict", json=[SAMPLE] * 6).status_code == 422   # max_batch is 5 in this fixture


def test_cors_allows_the_dev_frontend(client):
    r = client.options("/predict", headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_missing_model_degrades_instead_of_crashing(tmp_path: Path):
    s = Settings(tmp_path / "nope.json", tmp_path / "nope_meta.json", ("http://127.0.0.1:5173",), (), 5, 50)
    with TestClient(create_app(s)) as c:
        h = c.get("/health").json()
        assert h["status"] == "degraded" and not h["model_loaded"] and "not found" in h["error"]
        assert c.post("/predict", json=SAMPLE).status_code == 503
        assert c.get("/models").status_code == 503


def test_default_class_order_is_flagged_as_unverified(tmp_path: Path, settings: Settings):
    meta = Path(settings.meta_path); meta.write_text(json.dumps({"version": "x"}))
    with TestClient(create_app(settings)) as c:
        info = c.get("/models").json()
        assert info["class_order_source"] == "default" and info["class_order_verified"] is False
