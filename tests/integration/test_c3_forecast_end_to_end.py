"""Real-model HTTP forecasting test against an isolated SQLite snapshot."""

import sqlite3

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
    assert source_path.is_file(), "Research database is missing."

    snapshot_path = tmp_path / "c3_snapshot.sqlite3"

    # SQLite backup API includes committed WAL contents.
    with sqlite3.connect(
        f"file:{source_path}?mode=ro",
        uri=True,
    ) as source:
        with sqlite3.connect(snapshot_path) as target:
            source.backup(target)

    # All shared Golden Database connections now use the snapshot.
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

    first = client.post(
        "/research/forecasts/generate",
        json=request,
    )

    assert first.status_code == 200, first.text

    first_predictions = first.json()["predictions"]

    assert len(first_predictions) == 3
    assert {
        prediction["horizon_minutes"]
        for prediction in first_predictions
    } == {15, 30, 60}

    # Repeating the same request must not create duplicate predictions.
    second = client.post(
        "/research/forecasts/generate",
        json=request,
    )

    assert second.status_code == 200, second.text

    second_predictions = second.json()["predictions"]

    assert {
        prediction["prediction_id"]
        for prediction in first_predictions
    } == {
        prediction["prediction_id"]
        for prediction in second_predictions
    }

    history = client.get(
        "/research/forecasts",
        params={
            "dataset_id": DATASET_ID,
            "device_id": DEVICE_ID,
            "episode_id": EPISODE_ID,
        },
    )

    assert history.status_code == 200, history.text

    saved_ids = {
        prediction["prediction_id"]
        for prediction in history.json()["predictions"]
    }

    assert {
        prediction["prediction_id"]
        for prediction in first_predictions
    }.issubset(saved_ids)

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