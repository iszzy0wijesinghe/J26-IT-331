"""Integration tests for loading GeoNex simulated telemetry."""


from dataclasses import replace

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.ingestion.persistence import PacketConflictError
from apps.ingestion.simulation_loader import (
    SimulationLoadStatus,
    load_simulated_telemetry,
    load_simulated_telemetry_with_c4,
)
from components.c4_trust import C4TrustService
from database.models import SensorObservationRecord, TelemetryPacketRecord
from database.session import create_database_engine
from shared.simulation.scheduled_telemetry import (
    ScheduledTelemetryConfig,
    generate_scheduled_demo_telemetry,
)
from tests.integration.test_c4_simulation_gate import (
    build_test_gate,
    prepare_packet,
)


@pytest.fixture
def db_session():
    """Provide a database session isolated by an outer transaction."""

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


def generate_test_items():
    """Generate a reproducible six-pipe simulation batch."""

    return generate_scheduled_demo_telemetry(
        ScheduledTelemetryConfig(
            seed=20261010,
        )
    )


def count_test_packets(session, packet_ids):
    """Count database packets belonging to this test batch."""

    return session.scalar(
        select(func.count())
        .select_from(TelemetryPacketRecord)
        .where(TelemetryPacketRecord.packet_id.in_(packet_ids))
    )


def count_test_observations(session, packet_ids):
    """Count observations belonging to this test batch."""

    return session.scalar(
        select(func.count())
        .select_from(SensorObservationRecord)
        .where(SensorObservationRecord.packet_id.in_(packet_ids))
    )


def test_simulation_loader_creates_packets_and_observations(db_session):
    items = generate_test_items()

    assert len(items) == 60

    result = load_simulated_telemetry(db_session, items)

    assert result.status == SimulationLoadStatus.COMPLETED
    assert result.total_packets == 60
    assert result.created_packets == 60
    assert result.existing_packets == 0
    assert result.created_observations == 180

    packet_ids = [item.packet.packet_id for item in items]

    assert count_test_packets(db_session, packet_ids) == 60
    assert count_test_observations(db_session, packet_ids) == 180

    db_session.flush()


def test_simulation_loader_is_idempotent(db_session):
    items = generate_test_items()

    first = load_simulated_telemetry(db_session, items)
    second = load_simulated_telemetry(db_session, items)

    assert first.created_packets == 60
    assert first.created_observations == 180

    assert second.total_packets == 60
    assert second.created_packets == 0
    assert second.existing_packets == 60
    assert second.created_observations == 0

    packet_ids = [item.packet.packet_id for item in items]

    assert count_test_packets(db_session, packet_ids) == 60
    assert count_test_observations(db_session, packet_ids) == 180


def test_simulation_loader_rejects_conflicting_packet(db_session):
    items = generate_test_items()

    load_simulated_telemetry(db_session, items)

    original = items[0]

    modified_packet = original.packet.model_copy(
        update={
            "message_type": "CONFLICTING_TELEMETRY",
        }
    )

    conflicting_item = replace(
        original,
        packet=modified_packet,
    )

    with pytest.raises(PacketConflictError):
        load_simulated_telemetry(
            db_session,
            [conflicting_item],
        )


def test_simulation_loader_rollback(db_session):
    items = generate_test_items()

    packet_ids = [item.packet.packet_id for item in items]

    # The session uses a savepoint inside the fixture's outer transaction.
    # Rolling back this savepoint must discard the simulated batch.
    nested_transaction = db_session.begin_nested()

    try:
        result = load_simulated_telemetry(db_session, items)

        assert result.created_packets == 60
        assert count_test_packets(db_session, packet_ids) == 60

    finally:
        nested_transaction.rollback()

    assert count_test_packets(db_session, packet_ids) == 0
    assert count_test_observations(db_session, packet_ids) == 0


def test_simulation_loader_handles_empty_batch(db_session):
    result = load_simulated_telemetry(db_session, [])

    assert result.status == SimulationLoadStatus.COMPLETED
    assert result.total_packets == 0
    assert result.created_packets == 0
    assert result.existing_packets == 0
    assert result.created_observations == 0
def test_c4_gated_loader_persists_only_trusted_packets(db_session, tmp_path):
    items = generate_test_items()
    gate, _, credentials = build_test_gate(tmp_path / "quarantine")

    def prepare_and_sign(item):
        credential = credentials[item.packet.device_id]
        packet = prepare_packet(item, credential)
        signature = C4TrustService.sign_packet(packet, credential.secret)
        return packet, signature

    result = load_simulated_telemetry_with_c4(
        session=db_session,
        items=items,
        gate=gate,
        prepare_and_sign=prepare_and_sign,
        now_provider=lambda packet: packet.observed_at,
    )

    packet_ids = [item.packet.packet_id for item in items]

    assert result.status == SimulationLoadStatus.COMPLETED
    assert result.total_packets == 60
    assert result.accepted_packets == 60
    assert result.created_packets == 60
    assert result.existing_packets == 0
    assert result.quarantined_packets == 0
    assert count_test_packets(db_session, packet_ids) == 60
    assert count_test_observations(db_session, packet_ids) == 180


def test_c4_gated_loader_never_persists_rejected_packets(
    db_session,
    tmp_path,
):
    items = generate_test_items()[:1]
    gate, _, credentials = build_test_gate(tmp_path / "quarantine")

    def prepare_and_sign(item):
        credential = credentials[item.packet.device_id]
        packet = prepare_packet(item, credential)
        signature = C4TrustService.sign_packet(packet, credential.secret)

        tampered_packet = packet.model_copy(
            update={"message_type": "TAMPERED_TELEMETRY"}
        )

        return tampered_packet, signature

    result = load_simulated_telemetry_with_c4(
        session=db_session,
        items=items,
        gate=gate,
        prepare_and_sign=prepare_and_sign,
        now_provider=lambda packet: packet.observed_at,
    )

    packet_ids = [item.packet.packet_id for item in items]

    assert result.total_packets == 1
    assert result.accepted_packets == 0
    assert result.created_packets == 0
    assert result.existing_packets == 0
    assert result.quarantined_packets == 1
    assert count_test_packets(db_session, packet_ids) == 0
    assert count_test_observations(db_session, packet_ids) == 0