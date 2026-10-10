"""PostgreSQL integration tests for GeoNex telemetry persistence."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.ingestion.persistence import (
    PacketConflictError,
    PersistenceStatus,
    persist_telemetry_packet,
)
from database.models import SensorObservationRecord, TelemetryPacketRecord
from database.session import create_database_engine
from shared.contracts.telemetry import TelemetryPacket
from shared.telemetry.identifiers import make_observation_id


@pytest.fixture
def db_session():
    """Provide an isolated PostgreSQL session for each test.

    The session uses a savepoint inside an outer transaction.

    Session commits and rollbacks cannot permanently modify the
    development database because the outer transaction is rolled
    back during fixture cleanup.
    """

    engine = create_database_engine()

    connection = engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()

        if transaction.is_active:
            transaction.rollback()

        connection.close()
        engine.dispose()


def make_packet(
    *,
    packet_id: str | None = None,
    first_value: float = 42.5,
) -> TelemetryPacket:
    """Build a valid packet with two sensor measurements."""

    timestamp = datetime(2026, 10, 10, 10, 0, tzinfo=UTC)

    return TelemetryPacket.model_validate(
        {
            "schema_version": "1.0",
            "packet_id": packet_id or f"TEST_{uuid4().hex}",
            "device_id": "PIPE_A1",
            "zone_id": "ZONE_01",
            "observed_at": timestamp,
            "received_at": timestamp,
            "source_origin": "SIMULATED",
            "measurements": [
                {
                    "sensor_instance_id": "SOIL_01",
                    "sensor_type": "SOIL_MOISTURE",
                    "value": first_value,
                    "unit": "%",
                },
                {
                    "sensor_instance_id": "TEMP_01",
                    "sensor_type": "TEMPERATURE",
                    "value": 28.4,
                    "unit": "C",
                },
            ],
        }
    )


def test_persist_packet_and_observations(db_session):
    packet = make_packet()

    result = persist_telemetry_packet(db_session, packet)

    assert result.status is PersistenceStatus.CREATED
    assert result.observation_count == 2

    stored_packet = db_session.get(
        TelemetryPacketRecord,
        packet.packet_id,
    )

    assert stored_packet is not None
    assert stored_packet.device_id == "PIPE_A1"

    observations = db_session.scalars(
        select(SensorObservationRecord).where(
            SensorObservationRecord.packet_id == packet.packet_id
        )
    ).all()

    assert len(observations) == 2

    observation_ids = {item.observation_id for item in observations}

    assert observation_ids == {
        make_observation_id(packet.packet_id, 0),
        make_observation_id(packet.packet_id, 1),
    }


def test_identical_retry_is_idempotent(db_session):
    packet = make_packet()

    first = persist_telemetry_packet(db_session, packet)
    second = persist_telemetry_packet(db_session, packet)

    assert first.status is PersistenceStatus.CREATED
    assert second.status is PersistenceStatus.ALREADY_EXISTS

    count = db_session.scalar(
        select(func.count())
        .select_from(SensorObservationRecord)
        .where(SensorObservationRecord.packet_id == packet.packet_id)
    )

    assert count == 2


def test_conflicting_packet_id_is_rejected(db_session):
    packet = make_packet()

    persist_telemetry_packet(db_session, packet)

    conflicting_packet = make_packet(
        packet_id=packet.packet_id,
        first_value=99.9,
    )

    with pytest.raises(PacketConflictError):
        persist_telemetry_packet(db_session, conflicting_packet)

    stored_packet = db_session.get(
        TelemetryPacketRecord,
        packet.packet_id,
    )

    assert stored_packet is not None
    assert stored_packet.measurements[0]["value"] == 42.5


def test_transaction_rollback_removes_packet_and_observations(db_session):
    packet = make_packet()

    persist_telemetry_packet(db_session, packet)

    db_session.rollback()

    stored_packet = db_session.get(
        TelemetryPacketRecord,
        packet.packet_id,
    )

    assert stored_packet is None

    count = db_session.scalar(
        select(func.count())
        .select_from(SensorObservationRecord)
        .where(SensorObservationRecord.packet_id == packet.packet_id)
    )

    assert count == 0


def test_observation_ids_are_deterministic():
    first = make_observation_id("PKT_001", 0)
    second = make_observation_id("PKT_001", 0)
    different = make_observation_id("PKT_001", 1)

    assert first == second
    assert first != different


def test_identical_retry_across_independent_sessions(db_session):
    """A committed packet remains idempotent in a new session."""

    packet = make_packet()

    first_result = persist_telemetry_packet(db_session, packet)

    assert first_result.status is PersistenceStatus.CREATED

    # Commit the session's savepoint, not the fixture's outer transaction.
    db_session.commit()

    # Create a separate SQLAlchemy session using the same connection.
    # The outer transaction keeps all test changes isolated.
    second_session = Session(
        bind=db_session.get_bind(),
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        second_result = persist_telemetry_packet(second_session, packet)

        assert second_result.status is PersistenceStatus.ALREADY_EXISTS
        assert second_result.observation_count == 2

        observation_count = second_session.scalar(
            select(func.count())
            .select_from(SensorObservationRecord)
            .where(SensorObservationRecord.packet_id == packet.packet_id)
        )

        assert observation_count == 2

    finally:
        second_session.close()