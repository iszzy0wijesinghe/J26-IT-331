
from components.c4_trust import (
    C4TrustService,
    DeviceCredential,
    DeviceKind,
    DeviceRegistry,
)
from components.c4_trust.pipeline import C4TelemetryGate
from components.c4_trust.quarantine import QuarantineManager
from shared.contracts.telemetry import SecurityMetadata, TransportMetadata
from shared.enums import C4RoutingOutcome, C4TrustLabel
from shared.simulation.scheduled_telemetry import (
    ScheduledTelemetryConfig,
    generate_scheduled_demo_telemetry,
)
from shared.simulation.topology import get_all_demo_pipes

TEST_SEED = 20261010

HUB_BY_ZONE = {
    "ZONE_01": "H001",
    "ZONE_02": "H002",
}


def build_test_gate(quarantine_dir):
    registry = DeviceRegistry()
    credentials = {}

    kind_by_role = {
        "TYPE_A": DeviceKind.TYPE_A,
        "TYPE_B": DeviceKind.TYPE_B,
        "BACKUP": DeviceKind.BACKUP,
    }

    for pipe in get_all_demo_pipes():
        credential = DeviceCredential(
            credential_id=f"TEST-CRED-{pipe.device_id}",
            secret=f"test-only-secret-{pipe.device_id}".encode(),
        )
        credentials[pipe.device_id] = credential

        registry.register(
            device_id=pipe.device_id,
            device_kind=kind_by_role[pipe.role.value],
            zone_id=pipe.zone_id,
            hub_id=HUB_BY_ZONE[pipe.zone_id],
            credential=credential,
        )
        registry.activate(pipe.device_id)

    def verify_attestation(packet, device):
        return packet.security.attestation_evidence == {
            "test_attestation": packet.device_id
        }

    def verify_provenance(packet, device):
        return packet.security.provenance_evidence == {
            "test_provenance": packet.packet_id
        }

    service = C4TrustService(
        registry,
        attestation_verifier=verify_attestation,
        provenance_verifier=verify_provenance,
        allow_deterministic_only=True,
        max_age_seconds=30,
        future_tolerance_seconds=5,
    )

    gate = C4TelemetryGate(
        trust_service=service,
        quarantine_manager=QuarantineManager(
            quarantine_dir=quarantine_dir
        ),
    )

    return gate, service, credentials


def prepare_packet(item, credential):
    packet = item.packet
    hub_id = HUB_BY_ZONE[packet.zone_id]

    return packet.model_copy(
        update={
            "transport": TransportMetadata(gateway_id=hub_id),
            "security": SecurityMetadata(
                credential_id=credential.credential_id,
                integrity_present=True,
                freshness_counter=packet.sequence_no,
                session_id=f"TEST-SESSION-{packet.device_id}",
                attestation_evidence={
                    "test_attestation": packet.device_id
                },
                provenance_evidence={
                    "test_provenance": packet.packet_id
                },
            ),
        }
    )


def generate_test_items():
    return generate_scheduled_demo_telemetry(
        ScheduledTelemetryConfig(seed=TEST_SEED)
    )


def test_six_pipe_simulation_passes_c4_gate(tmp_path):
    items = generate_test_items()
    gate, _, credentials = build_test_gate(tmp_path / "quarantine")

    assert len(items) == 60

    accepted = 0
    quarantined = 0

    for item in items:
        credential = credentials[item.packet.device_id]
        packet = prepare_packet(item, credential)
        signature = C4TrustService.sign_packet(packet, credential.secret)

        result = gate.process(
            packet,
            signature,
            now=packet.observed_at,
        )

        if result.eligible_for_c1:
            accepted += 1
            assert result.assessment.trust_label is C4TrustLabel.TRUSTED
            assert (
                result.assessment.routing_outcome
                is C4RoutingOutcome.ACCEPT
            )
            assert result.assessment.mandatory_security_pass
        else:
            quarantined += 1

    assert accepted == 60
    assert quarantined == 0


def test_c4_gate_blocks_tampered_packet(tmp_path):
    items = generate_test_items()
    gate, _, credentials = build_test_gate(tmp_path / "quarantine")

    original = items[0].packet
    credential = credentials[original.device_id]
    packet = prepare_packet(items[0], credential)
    signature = C4TrustService.sign_packet(packet, credential.secret)

    tampered_packet = packet.model_copy(
        update={"message_type": "TAMPERED_TELEMETRY"}
    )

    result = gate.process(
        tampered_packet,
        signature,
        now=tampered_packet.observed_at,
    )

    assert not result.eligible_for_c1
    assert result.assessment.trust_label is C4TrustLabel.UNTRUSTED
    assert "INTEGRITY_INVALID" in result.assessment.reason_codes
    assert result.quarantine_record is not None


def test_c4_gate_detects_replayed_packet(tmp_path):
    items = generate_test_items()
    gate, _, credentials = build_test_gate(tmp_path / "quarantine")

    item = items[0]
    credential = credentials[item.packet.device_id]
    packet = prepare_packet(item, credential)
    signature = C4TrustService.sign_packet(packet, credential.secret)

    first_result = gate.process(
        packet,
        signature,
        now=packet.observed_at,
    )
    replay_result = gate.process(
        packet,
        signature,
        now=packet.observed_at,
    )

    assert first_result.eligible_for_c1
    assert not replay_result.eligible_for_c1
    assert replay_result.assessment.trust_label is C4TrustLabel.UNTRUSTED
    assert any(
        reason in replay_result.assessment.reason_codes
        for reason in ("REPLAY_DETECTED", "SEQUENCE_REPLAY_DETECTED")
    )
    assert replay_result.quarantine_record is not None