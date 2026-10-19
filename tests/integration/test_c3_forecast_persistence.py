"""Integration tests for C3 forecast persistence."""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from apps.c3_workbench import forecast_persistence, golden_db


@pytest.fixture
def persistence_environment(tmp_path, monkeypatch):
    """Use a separate SQLite database for each test."""

    database_path = tmp_path / "c3_forecast_test.sqlite3"

    monkeypatch.setattr(
        golden_db,
        "DATABASE_PATH",
        database_path,
    )

    golden_db.initialize_golden_database()
    forecast_persistence.initialize_forecast_persistence()

    dataset_id = "test_forecast_dataset"

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO c3_datasets (
                dataset_id, filename, file_hash, uploaded_at,
                total_rows, device_count, episode_count,
                quality_status, pipeline_status,
                validation_report, source_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                "test.csv",
                "forecast_test_hash",
                "2026-10-19T00:00:00+00:00",
                100,
                1,
                1,
                "GOLDEN",
                "READY",
                "{}",
                "CSV",
            ),
        )

        for horizon, model_name in (
            (15, "M1_RIDGE"),
            (30, "M4_C_GRU"),
            (60, "M4_A_GRU"),
        ):
            connection.execute(
                """
                INSERT INTO c3_model_versions (
                    model_version_id,
                    job_id,
                    dataset_id,
                    model_name,
                    horizon_minutes,
                    checkpoint_path,
                    validation_mae,
                    validation_rmse,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"test_model_{horizon}",
                    "test_training_job",
                    dataset_id,
                    model_name,
                    horizon,
                    None,
                    0.5,
                    0.7,
                    "CANDIDATE",
                    "2026-10-19T00:00:00+00:00",
                ),
            )

    return {
        "database_path": database_path,
        "dataset_id": dataset_id,
    }


def make_forecast_result(dataset_id):
    """Build a valid three-horizon forecast result."""

    origin = datetime(
        2026, 2, 1, 9, 55, tzinfo=UTC
    )

    predictions = []

    for horizon, model_name, value in (
        (15, "M1_RIDGE", 66.7181),
        (30, "M4_C_GRU", 66.6862),
        (60, "M4_A_GRU", 66.7279),
    ):
        predictions.append(
            {
                "horizon_minutes": horizon,
                "model_version_id": f"test_model_{horizon}",
                "model_name": model_name,
                "target_timestamp": (
                    origin + timedelta(minutes=horizon)
                ).isoformat(),
                "predicted_soil_moisture_pct": value,
                "checkpoint_sha256": "test_checkpoint_hash",
            }
        )

    return {
        "dataset_id": dataset_id,
        "device_id": "GN-C3-001",
        "episode_id": "SYN-EP-001",
        "forecast_origin": origin.isoformat(),
        "forecast_type": "HISTORICAL_REPLAY",
        "input_window_start": (
            origin - timedelta(minutes=155)
        ).isoformat(),
        "input_window_end": origin.isoformat(),
        "sequence_length": 32,
        "source_origin": "GOLDEN_CSV",
        "source_provenance_verified": False,
        "receipt_time_basis": (
            "ASSUMED_EQUAL_TO_OBSERVATION_TIME"
        ),
        "predictions": predictions,
    }


def test_save_three_forecast_horizons(persistence_environment):
    """All three forecasts should be saved atomically."""

    environment = persistence_environment

    result = make_forecast_result(
        environment["dataset_id"]
    )

    saved = forecast_persistence.save_forecast_predictions(
        result
    )

    assert len(saved) == 3

    assert {
        row["horizon_minutes"] for row in saved
    } == {15, 30, 60}

    with sqlite3.connect(
        environment["database_path"]
    ) as connection:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM c3_forecast_predictions
            """
        ).fetchone()[0]

    assert count == 3


def test_retrieve_saved_forecasts(persistence_environment):
    """Saved forecasts should be available for retrieval."""

    environment = persistence_environment

    result = make_forecast_result(
        environment["dataset_id"]
    )

    forecast_persistence.save_forecast_predictions(result)

    records = forecast_persistence.list_forecast_predictions(
        dataset_id=environment["dataset_id"],
        device_id="GN-C3-001",
        episode_id="SYN-EP-001",
    )

    assert len(records) == 3

    assert [
        row["horizon_minutes"] for row in records
    ] == [15, 30, 60]

    assert all(
        row["actual_soil_moisture_pct"] is None
        for row in records
    )

    assert all(
        row["absolute_error"] is None
        for row in records
    )


def test_invalid_model_rolls_back_transaction(
    persistence_environment,
):
    """One invalid prediction must roll back the entire batch."""

    environment = persistence_environment

    result = make_forecast_result(
        environment["dataset_id"]
    )

    result["predictions"][1][
        "model_version_id"
    ] = "unknown_model"

    with pytest.raises(
        forecast_persistence.ForecastPersistenceError
    ):
        forecast_persistence.save_forecast_predictions(
            result
        )

    with sqlite3.connect(
        environment["database_path"]
    ) as connection:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM c3_forecast_predictions
            """
        ).fetchone()[0]

    assert count == 0


def test_reject_duplicate_horizons_in_one_request(
    persistence_environment,
):
    """A single request cannot contain repeated horizons."""

    result = make_forecast_result(
        persistence_environment["dataset_id"]
    )

    result["predictions"].append(
        result["predictions"][0].copy()
    )

    with pytest.raises(
        forecast_persistence.ForecastPersistenceError
    ):
        forecast_persistence.save_forecast_predictions(
            result
        )


def test_repeated_forecast_is_idempotent(
    persistence_environment,
):
    """Saving the same forecast twice must not duplicate records."""

    environment = persistence_environment

    result = make_forecast_result(
        environment["dataset_id"]
    )

    first = forecast_persistence.save_forecast_predictions(
        result
    )

    second = forecast_persistence.save_forecast_predictions(
        result
    )

    assert len(first) == 3
    assert len(second) == 3

    assert {
        row["prediction_id"] for row in first
    } == {
        row["prediction_id"] for row in second
    }

    with sqlite3.connect(
        environment["database_path"]
    ) as connection:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM c3_forecast_predictions
            """
        ).fetchone()[0]

    assert count == 3
    
def test_conflicting_repeated_forecast_is_rejected(
    persistence_environment,
):
    """A repeated identity with changed values must be rejected."""

    environment = persistence_environment
    result = make_forecast_result(environment["dataset_id"])

    original = forecast_persistence.save_forecast_predictions(
        result
    )

    conflicting = make_forecast_result(
        environment["dataset_id"]
    )

    conflicting["predictions"][0][
        "predicted_soil_moisture_pct"
    ] = 77.1234

    with pytest.raises(
        forecast_persistence.ForecastPersistenceError,
        match="Conflicting forecast",
    ):
        forecast_persistence.save_forecast_predictions(
            conflicting
        )

    with golden_db.get_connection() as connection:
        rows = connection.execute(
            """
            SELECT prediction_id
            FROM c3_forecast_predictions
            """
        ).fetchall()

    assert len(rows) == 3

    assert {row["prediction_id"] for row in rows} == {
        row["prediction_id"] for row in original
    }


def test_conflict_rolls_back_earlier_insert(
    persistence_environment,
):
    """A later conflict must roll back earlier inserts in the batch."""

    environment = persistence_environment
    dataset_id = environment["dataset_id"]

    original = make_forecast_result(dataset_id)

    forecast_persistence.save_forecast_predictions(
        original
    )

    # Remove only the 15-minute prediction so that the next
    # batch inserts it before encountering a conflict at 30m.
    #
    # This test uses an isolated temporary SQLite database.

    with golden_db.get_connection() as connection:
        connection.execute(
            """
            DELETE FROM c3_forecast_predictions
            WHERE dataset_id = ?
              AND horizon_minutes = 15
            """,
            (dataset_id,),
        )
        connection.commit()

    conflicting = make_forecast_result(dataset_id)

    # 15-minute prediction does not exist and would be inserted.
    # 30-minute prediction exists but has a conflicting value.

    conflicting["predictions"][1][
        "predicted_soil_moisture_pct"
    ] = 88.5678

    with pytest.raises(
        forecast_persistence.ForecastPersistenceError,
        match="Conflicting forecast",
    ):
        forecast_persistence.save_forecast_predictions(
            conflicting
        )

    with golden_db.get_connection() as connection:
        rows = connection.execute(
            """
            SELECT horizon_minutes
            FROM c3_forecast_predictions
            WHERE dataset_id = ?
            ORDER BY horizon_minutes
            """,
            (dataset_id,),
        ).fetchall()

    # The 15-minute insertion must be rolled back.
    # Only the original 30-minute and 60-minute records remain.

    assert [
        row["horizon_minutes"] for row in rows
    ] == [30, 60]