"""Real-model HTTP forecasting test against an isolated SQLite snapshot."""

import sqlite3
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from apps.c3_workbench import golden_db
from apps.c3_workbench.api import app

DATASET_ID = "c3raw_cf19059376cd4dd7"
DEVICE_ID = "GN-C3-001"
EPISODE_ID = "SYN-EP-001"
FORECAST_ORIGIN = "2026-02-01T09:55:00+00:00"


def test_real_forecast_http_workflow(tmp_path, monkeypatch):
    """Run real inference and persistence without writing to the source DB."""

    source_path = golden_db.DATABASE_PATH

    assert source_path.is_file(), (
        "Research database is missing."
    )

    snapshot_path = tmp_path / "c3_snapshot.sqlite3"

    # --------------------------------------------------
    # Copy committed database state into an isolated DB
    # --------------------------------------------------

    # SQLite backup API includes committed WAL contents.

    with sqlite3.connect(
        f"file:{source_path}?mode=ro",
        uri=True,
    ) as source:

        with sqlite3.connect(snapshot_path) as target:
            source.backup(target)

    # --------------------------------------------------
    # Redirect shared Golden Database connections
    # --------------------------------------------------

    monkeypatch.setattr(
        golden_db,
        "DATABASE_PATH",
        snapshot_path,
    )

    client = TestClient(app)

    request = {
        "dataset_id": DATASET_ID,
        "device_id": DEVICE_ID,
        "episode_id": EPISODE_ID,
        "forecast_origin": FORECAST_ORIGIN,
    }

    # --------------------------------------------------
    # First HTTP request: generate and persist forecasts
    # --------------------------------------------------

    first = client.post(
        "/research/forecasts/generate",
        json=request,
    )

    assert first.status_code == 200, first.text

    first_body = first.json()
    first_predictions = first_body["predictions"]

    assert first_body["status"] == "completed"
    assert first_body["forecast_type"] == "HISTORICAL_REPLAY"
    assert first_body["target_feature"] == "soil_moisture_pct"

    assert len(first_predictions) == 3

    assert {
        prediction["horizon_minutes"]
        for prediction in first_predictions
    } == {15, 30, 60}

    # --------------------------------------------------
    # Verify complete prediction response metadata
    # --------------------------------------------------

    origin = datetime.fromisoformat(FORECAST_ORIGIN)

    for prediction in first_predictions:

        horizon = prediction["horizon_minutes"]

        assert prediction["prediction_id"]
        assert prediction["dataset_id"] == DATASET_ID
        assert prediction["device_id"] == DEVICE_ID
        assert prediction["episode_id"] == EPISODE_ID

        assert prediction["forecast_type"] == "HISTORICAL_REPLAY"

        assert prediction["forecast_origin"] == FORECAST_ORIGIN

        assert prediction["target_timestamp"]

        target = datetime.fromisoformat(
            prediction["target_timestamp"]
        )

        expected_target = origin + timedelta(
            minutes=horizon
        )

        assert target == expected_target

        assert prediction["model_version_id"]
        assert prediction["model_name"]
        assert prediction["checkpoint_sha256"]

        assert prediction["input_window_start"]
        assert prediction["input_window_end"]

        assert prediction["sequence_length"] >= 3

        assert prediction["source_origin"]

        assert prediction["receipt_time_basis"]

        assert prediction["created_at"]

        assert isinstance(
            prediction["predicted_soil_moisture_pct"],
            (int, float),
        )

        # Actual future observations must not be fabricated.

        assert prediction["actual_soil_moisture_pct"] is None
        assert prediction["absolute_error"] is None

    # --------------------------------------------------
    # Second HTTP request: verify idempotent persistence
    # --------------------------------------------------

    second = client.post(
        "/research/forecasts/generate",
        json=request,
    )

    assert second.status_code == 200, second.text

    second_predictions = second.json()["predictions"]

    assert len(second_predictions) == 3

    # Existing prediction identities must be preserved.

    assert {
        prediction["prediction_id"]
        for prediction in first_predictions
    } == {
        prediction["prediction_id"]
        for prediction in second_predictions
    }

    # Existing target timestamps must also be preserved.

    assert {
        prediction["target_timestamp"]
        for prediction in first_predictions
    } == {
        prediction["target_timestamp"]
        for prediction in second_predictions
    }

    # Complete records should be identical for repeated requests.

    first_by_id = {
        prediction["prediction_id"]: prediction
        for prediction in first_predictions
    }

    second_by_id = {
        prediction["prediction_id"]: prediction
        for prediction in second_predictions
    }

    assert first_by_id == second_by_id

    # --------------------------------------------------
    # GET request: verify persisted forecast history
    # --------------------------------------------------

    history = client.get(
        "/research/forecasts",
        params={
            "dataset_id": DATASET_ID,
            "device_id": DEVICE_ID,
            "episode_id": EPISODE_ID,
        },
    )

    assert history.status_code == 200, history.text

    history_body = history.json()

    saved_predictions = history_body["predictions"]

    saved_by_id = {
        prediction["prediction_id"]: prediction
        for prediction in saved_predictions
    }

    for prediction_id, prediction in first_by_id.items():

        assert prediction_id in saved_by_id

        assert saved_by_id[prediction_id] == prediction

    # --------------------------------------------------
    # Verify SQLite contains exactly three predictions
    # for this forecast origin.
    # --------------------------------------------------

    with sqlite3.connect(snapshot_path) as connection:

        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM c3_forecast_predictions
            WHERE dataset_id = ?
              AND device_id = ?
              AND episode_id = ?
              AND forecast_origin = ?
            """,
            (
                DATASET_ID,
                DEVICE_ID,
                EPISODE_ID,
                FORECAST_ORIGIN,
            ),
        ).fetchone()[0]

    assert count == 3