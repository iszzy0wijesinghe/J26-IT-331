"""Database-backed integration tests for the C3 training queue."""

import sqlite3

import pytest

from apps.c3_workbench import golden_db, training_queue


@pytest.fixture
def isolated_database(tmp_path, monkeypatch):
    """Redirect all Golden database operations to a temporary database."""

    database_path = tmp_path / "c3_training_test.sqlite3"

    monkeypatch.setattr(
        golden_db,
        "DATABASE_PATH",
        database_path,
    )

    golden_db.initialize_golden_database()

    yield database_path


def create_test_dataset(database_path, dataset_id):
    """Create the minimum valid dataset record for queue testing."""

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO c3_datasets (
                dataset_id,
                filename,
                file_hash,
                uploaded_at,
                total_rows,
                device_count,
                episode_count,
                quality_status,
                pipeline_status,
                validation_report,
                source_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                f"{dataset_id}.csv",
                f"test_hash_{dataset_id}",
                "2026-10-19T00:00:00+00:00",
                10,
                1,
                1,
                "VALID",
                "READY",
                "{}",
                "CSV",
            ),
        )


def test_enqueue_training_job_persists_to_database(isolated_database):
    dataset_id = "dataset_queue_001"

    create_test_dataset(isolated_database, dataset_id)

    job = training_queue.enqueue_training_job(dataset_id)

    assert job["dataset_id"] == dataset_id
    assert job["status"] == "QUEUED"
    assert job["current_stage"] == "WAITING_FOR_WORKER"

    with sqlite3.connect(isolated_database) as connection:
        stored = connection.execute(
            """
            SELECT status, current_stage
            FROM c3_training_jobs
            WHERE job_id = ?
            """,
            (job["job_id"],),
        ).fetchone()

        assert stored == ("QUEUED", "WAITING_FOR_WORKER")


def test_duplicate_enqueue_returns_existing_job(isolated_database):
    dataset_id = "dataset_queue_002"

    create_test_dataset(isolated_database, dataset_id)

    first = training_queue.enqueue_training_job(dataset_id)
    second = training_queue.enqueue_training_job(dataset_id)

    assert first["job_id"] == second["job_id"]

    with sqlite3.connect(isolated_database) as connection:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM c3_training_jobs
            WHERE dataset_id = ?
            """,
            (dataset_id,),
        ).fetchone()[0]

    assert count == 1


def test_claim_training_job_updates_status(isolated_database):
    dataset_id = "dataset_queue_003"

    create_test_dataset(isolated_database, dataset_id)

    queued = training_queue.enqueue_training_job(dataset_id)

    claimed = training_queue.claim_training_job(queued["job_id"])

    assert claimed is not None
    assert claimed["status"] == "PREPARING"
    assert claimed["current_stage"] == "DATA_PREPARATION"
    assert claimed["started_at"] is not None


def test_training_job_cannot_be_claimed_twice(isolated_database):
    dataset_id = "dataset_queue_004"

    create_test_dataset(isolated_database, dataset_id)

    queued = training_queue.enqueue_training_job(dataset_id)

    first_claim = training_queue.claim_training_job(queued["job_id"])
    second_claim = training_queue.claim_training_job(queued["job_id"])

    assert first_claim is not None
    assert second_claim is None


def test_unknown_dataset_cannot_be_enqueued(isolated_database):
    with pytest.raises(
        ValueError,
        match="Golden dataset does not exist",
    ):
        training_queue.enqueue_training_job("unknown_dataset")


def test_training_events_are_persisted(isolated_database):
    dataset_id = "dataset_queue_005"

    create_test_dataset(isolated_database, dataset_id)

    queued = training_queue.enqueue_training_job(dataset_id)

    training_queue.claim_training_job(queued["job_id"])

    with sqlite3.connect(isolated_database) as connection:
        events = connection.execute(
            """
            SELECT stage
            FROM c3_training_events
            WHERE job_id = ?
            ORDER BY event_id
            """,
            (queued["job_id"],),
        ).fetchall()

    assert [event[0] for event in events] == [
        "QUEUE",
        "PREPARING",
    ]