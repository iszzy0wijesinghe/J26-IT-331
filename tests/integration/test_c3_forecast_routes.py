"""Integration tests for GeoNex C3 forecast API routes."""

from fastapi.testclient import TestClient

from apps.c3_workbench import forecast_routes
from apps.c3_workbench.api import app

client = TestClient(app)

REQUEST = {
    "dataset_id": "test_dataset",
    "device_id": "test_device",
    "episode_id": "test_episode",
    "forecast_origin": "2026-02-01T09:55:00+00:00",
}


def test_generate_forecasts_endpoint(monkeypatch):
    """Generation calls existing engine and persistence functions."""

    def fake_generate(**kwargs):
        assert kwargs == REQUEST
        return {
            **REQUEST,
            "forecast_type": "HISTORICAL_REPLAY",
            "target_feature": "soil_moisture_pct",
            "predictions": [],
            "limitations": ["Synthetic research dataset"],
        }

    def fake_save(result):
        assert result["dataset_id"] == REQUEST["dataset_id"]
        return [
            {
                "prediction_id": "test_prediction_15",
                "horizon_minutes": 15,
                "model_name": "M1_RIDGE",
                "predicted_soil_moisture_pct": 66.72,
            }
        ]

    monkeypatch.setattr(
        forecast_routes,
        "generate_active_forecasts",
        fake_generate,
    )
    monkeypatch.setattr(
        forecast_routes,
        "save_forecast_predictions",
        fake_save,
    )

    response = client.post(
        "/research/forecasts/generate",
        json=REQUEST,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "completed"
    assert body["forecast_type"] == "HISTORICAL_REPLAY"
    assert body["predictions"][0]["horizon_minutes"] == 15


def test_get_saved_forecasts_endpoint(monkeypatch):
    """Retrieval uses existing forecast persistence reader."""

    def fake_list(**kwargs):
        assert kwargs["dataset_id"] == REQUEST["dataset_id"]
        assert kwargs["device_id"] == REQUEST["device_id"]
        assert kwargs["episode_id"] == REQUEST["episode_id"]
        return [
            {
                "prediction_id": "test_prediction_15",
                "horizon_minutes": 15,
            }
        ]

    monkeypatch.setattr(
        forecast_routes,
        "list_forecast_predictions",
        fake_list,
    )

    response = client.get(
        "/research/forecasts",
        params={
            "dataset_id": REQUEST["dataset_id"],
            "device_id": REQUEST["device_id"],
            "episode_id": REQUEST["episode_id"],
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 1
    assert body["predictions"][0]["prediction_id"] == "test_prediction_15"


def test_generate_forecast_engine_error(monkeypatch):
    """Forecasting errors produce HTTP 422."""

    def fake_generate(**kwargs):
        raise forecast_routes.ForecastingEngineError(
            "No active model available."
        )

    monkeypatch.setattr(
        forecast_routes,
        "generate_active_forecasts",
        fake_generate,
    )

    response = client.post(
        "/research/forecasts/generate",
        json=REQUEST,
    )

    assert response.status_code == 422
    assert "No active model" in response.json()["detail"]


def test_generate_forecast_invalid_request():
    """Missing required identity fields produce HTTP 422."""

    response = client.post(
        "/research/forecasts/generate",
        json={
            "dataset_id": "test_dataset",
        },
    )

    assert response.status_code == 422