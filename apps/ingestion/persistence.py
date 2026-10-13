
"""Transactional persistence of normalized GeoNex telemetry."""

import json
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256

from sqlalchemy.orm import Session

from database.models import SensorObservationRecord, TelemetryPacketRecord
from shared.contracts.telemetry import TelemetryPacket
from shared.telemetry.identifiers import make_observation_id


class PersistenceStatus(StrEnum):
    """Outcome of a telemetry persistence operation."""

    CREATED = "CREATED"
    ALREADY_EXISTS = "ALREADY_EXISTS"


class PacketConflictError(ValueError):
    """A packet ID was reused with different telemetry content."""


@dataclass(frozen=True)
class PersistenceResult:
    """Result of a successful telemetry persistence operation."""

    packet_id: str
    status: PersistenceStatus
    observation_count: int


def _packet_fingerprint(packet: TelemetryPacket) -> str:
    """Calculate a deterministic fingerprint of normalized packet content."""

    normalized_payload = packet.model_dump(mode="json")

    canonical_json = json.dumps(
        normalized_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )

    return sha256(canonical_json.encode("utf-8")).hexdigest()


def _record_matches_packet(
    record: TelemetryPacketRecord,
    packet: TelemetryPacket,
) -> bool:
    """Compare the persisted normalized packet with an incoming packet."""

    existing_payload = {
        "schema_version": record.schema_version,
        "packet_id": record.packet_id,
        "device_id": record.device_id,
        "zone_id": record.zone_id,
        "boot_id": record.boot_id,
        "sequence_no": record.sequence_no,
        "observed_at": record.observed_at,
        "received_at": record.received_at,
        "message_type": record.message_type,
        "tx_interval_s": record.tx_interval_s,
        "freshness_status": record.freshness_status,
        "measurements": record.measurements,
        "device_health": record.device_health,
        "transport": record.transport,
        "security": record.security,
        "source_origin": record.source_origin,
        "test_run_id": record.test_run_id,
        "correlation_id": record.correlation_id,
    }

    existing_packet = TelemetryPacket.model_validate(existing_payload)

    return _packet_fingerprint(existing_packet) == _packet_fingerprint(packet)


def persist_telemetry_packet(
    session: Session,
    packet: TelemetryPacket,
) -> PersistenceResult:
    """Stage a packet and its observations in the current transaction.

    The caller owns transaction commit and rollback through session_scope.
    Matching packet IDs are treated as idempotent retries.
    Conflicting packet IDs are rejected.
    """

    if not isinstance(packet, TelemetryPacket):
        raise TypeError(
            "packet must be a validated TelemetryPacket instance"
        )

    existing = session.get(TelemetryPacketRecord, packet.packet_id)

    if existing is not None:
        if not _record_matches_packet(existing, packet):
            raise PacketConflictError(
                f"Packet ID {packet.packet_id!r} already exists "
                "with different telemetry content"
            )

        return PersistenceResult(
            packet_id=packet.packet_id,
            status=PersistenceStatus.ALREADY_EXISTS,
            observation_count=len(packet.measurements),
        )

    packet_record = TelemetryPacketRecord(
        packet_id=packet.packet_id,
        schema_version=packet.schema_version,
        device_id=packet.device_id,
        zone_id=packet.zone_id,
        boot_id=packet.boot_id,
        sequence_no=packet.sequence_no,
        observed_at=packet.observed_at,
        received_at=packet.received_at,
        message_type=packet.message_type,
        tx_interval_s=packet.tx_interval_s,
        freshness_status=packet.freshness_status,
        measurements=[
            measurement.model_dump(mode="json")
            for measurement in packet.measurements
        ],
        device_health=packet.device_health.model_dump(mode="json"),
        transport=packet.transport.model_dump(mode="json"),
        security=packet.security.model_dump(mode="json"),
        source_origin=packet.source_origin.value,
        test_run_id=packet.test_run_id,
        correlation_id=packet.correlation_id,
    )

    session.add(packet_record)

    for index, measurement in enumerate(packet.measurements):
        observation = SensorObservationRecord(
            observation_id=make_observation_id(packet.packet_id, index),
            packet_id=packet.packet_id,
            schema_version=packet.schema_version,
            zone_id=packet.zone_id,
            device_id=packet.device_id,
            sensor_instance_id=measurement.sensor_instance_id,
            observed_at=packet.observed_at,
            received_at=packet.received_at,
            raw_value=measurement.raw_value,
            value=measurement.value,
            unit=measurement.unit,
            calibration_version=measurement.calibration_version,
            source_origin=packet.source_origin.value,
            test_run_id=packet.test_run_id,
            correlation_id=packet.correlation_id,
        )

        session.add(observation)

    session.flush()

    return PersistenceResult(
        packet_id=packet.packet_id,
        status=PersistenceStatus.CREATED,
        observation_count=len(packet.measurements),
    )