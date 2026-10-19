"""End-to-end test for Component 4 (C4)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from components.c4_trust import (
    C4TelemetryGate,
    C4TrustService,
    DeviceCredential,
    DeviceKind,
    DeviceRegistry,
    QuarantineManager,
    QuarantineReason,
)
from shared.contracts import C4TrustAssessment, TelemetryPacket
from shared.contracts.telemetry import SecurityMetadata, TransportMetadata
from shared.enums import C4RoutingOutcome, C4TrustLabel, SourceOrigin


def make_active_registry() -> DeviceRegistry:
    registry = DeviceRegistry()
    registry.register(
        "TEST-001",
        DeviceKind.TYPE_A,
        "Z1",
        "H001",
        DeviceCredential("cred-001", b"test-secret"),
    )
    registry.activate("TEST-001")
    return registry


def make_packet() -> TelemetryPacket:
    now = datetime.now(UTC)
    return TelemetryPacket(
        schema_version="1.0",
        packet_id="test-001",
        device_id="TEST-001",
        zone_id="Z1",
        boot_id="boot-001",
        sequence_no=1,
        observed_at=now - timedelta(seconds=1),
        received_at=now,
        source_origin=SourceOrigin.SIMULATED,
        security=SecurityMetadata(
            credential_id="cred-001",
            integrity_present=True,
        ),
        transport=TransportMetadata(gateway_id="H001"),
    )


def make_quarantined_record(quarantine: QuarantineManager):
    return quarantine.quarantine(
        packet_id="test-002",
        device_id="TEST-001",
        trust_label=C4TrustLabel.SUSPICIOUS,
        routing_outcome=C4RoutingOutcome.QUARANTINE,
        reason_codes=["BEHAVIOURAL_ANOMALY"],
        quarantine_reason=QuarantineReason.BEHAVIOURAL_ANOMALY,
        packet_data={"rssi_dbm": -110},
    )


def test_device_registry() -> None:
    registry = make_active_registry()

    assert registry.is_active("TEST-001")


def test_c4_trust_service() -> None:
    registry = make_active_registry()
    service = C4TrustService(
        registry,
        attestation_verifier=lambda packet, device: True,
        provenance_verifier=lambda packet, device: True,
        allow_deterministic_only=True,
    )
    packet = make_packet()

    signature = service.sign_packet(packet, b"test-secret")
    assessment = service.assess(packet, signature)

    assert assessment.trust_label is C4TrustLabel.TRUSTED
    assert assessment.routing_outcome is C4RoutingOutcome.ACCEPT


def test_c4_gate_forwards_only_verified_packets_and_quarantines_failures(
    tmp_path: Path,
) -> None:
    registry = make_active_registry()
    service = C4TrustService(
        registry,
        attestation_verifier=lambda packet, device: True,
        provenance_verifier=lambda packet, device: True,
        behavioural_scorer=lambda packet: 0.1,
    )
    quarantine = QuarantineManager(tmp_path)
    gate = C4TelemetryGate(service, quarantine)
    trusted_packet = make_packet()

    accepted = gate.process(
        trusted_packet,
        service.sign_packet(trusted_packet, b"test-secret"),
    )
    rejected = gate.process(make_packet(), "invalid-signature")

    assert accepted.eligible_for_c1
    assert accepted.eligible_packet is trusted_packet
    assert accepted.quarantine_record is None
    assert rejected.assessment.trust_label is C4TrustLabel.UNTRUSTED
    assert not rejected.eligible_for_c1
    assert rejected.quarantine_record is not None
    assert quarantine.count() == 1


def test_quarantine(tmp_path: Path) -> None:
    quarantine = QuarantineManager(tmp_path)

    record = make_quarantined_record(quarantine)

    assert not record.released
    assert (tmp_path / f"{record.quarantine_id}.json").is_file()


def test_quarantine_release(tmp_path: Path) -> None:
    quarantine = QuarantineManager(
        tmp_path,
        release_authorizer=lambda reviewer_id: reviewer_id == "test-reviewer",
    )
    record = make_quarantined_record(quarantine)

    review_assessment = C4TrustAssessment(
        schema_version="1.0",
        assessment_id="C4A_RELEASE_001",
        packet_id=record.packet_id,
        device_id=record.device_id,
        trust_label=C4TrustLabel.TRUSTED,
        trust_score=1.0,
        mandatory_security_pass=True,
        reason_codes=["REVALIDATED"],
        routing_outcome=C4RoutingOutcome.ACCEPT,
        generated_at=record.quarantined_at + timedelta(seconds=1),
    )
    updated = quarantine.release(
        record.quarantine_id,
        "Review confirmed legitimate",
        review_assessment=review_assessment,
        reviewer_id="test-reviewer",
    )

    assert updated.released
    assert updated.trust_label is C4TrustLabel.TRUSTED
    assert updated.routing_outcome is C4RoutingOutcome.ACCEPT
    assert updated.review_assessment == review_assessment
    assert quarantine.get(record.quarantine_id) is updated


def test_report_generation(tmp_path: Path) -> None:
    quarantine = QuarantineManager(tmp_path)
    make_quarantined_record(quarantine)

    report = quarantine.generate_report()

    assert report["total_quarantined"] == 1
    assert report["unreleased_count"] == 1
    assert report["released_count"] == 0
    assert report["by_reason"][QuarantineReason.BEHAVIOURAL_ANOMALY.value] == 1
