
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from components.c4_trust import (
    C4TrustService,
    DeviceCredential,
    DeviceKind,
    DeviceRegistry,
)
from components.c4_trust.pipeline import C4TelemetryGate
from components.c4_trust.quarantine import QuarantineManager, QuarantineReason
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


def test_c4_gate_accepts_valid_ecdsa_stream(tmp_path):
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    registry = DeviceRegistry()
    registry.register(
        device_id="PIPE_A1",
        device_kind=DeviceKind.TYPE_A,
        zone_id="ZONE_01",
        hub_id="H001",
        credential=DeviceCredential(
            credential_id="ECDSA-CRED-01",
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            public_key_pem=public_pem,
        ),
    )
    registry.activate("PIPE_A1")

    service = C4TrustService(
        registry,
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )
    gate = C4TelemetryGate(
        trust_service=service,
        quarantine_manager=QuarantineManager(quarantine_dir=tmp_path / "quarantine"),
    )

    items = generate_test_items()
    pipe_01_items = [it for it in items if it.packet.device_id == "PIPE_A1"]
    assert len(pipe_01_items) > 0

    for item in pipe_01_items:
        packet = item.packet.model_copy(
            update={
                "transport": TransportMetadata(gateway_id="H001"),
                "security": SecurityMetadata(
                    credential_id="ECDSA-CRED-01",
                    integrity_present=True,
                    attestation_evidence={"test": "ok"},
                    provenance_evidence={"test": "ok"},
                ),
            }
        )
        sig = service.sign_packet_ecdsa(packet, private_key)
        res = gate.process(packet, sig, now=packet.observed_at)
        assert res.eligible_for_c1
        assert res.assessment.trust_label is C4TrustLabel.TRUSTED
        assert res.quarantine_record is None


def test_c4_gate_quarantines_tampered_and_unverifiable_ecdsa_packets(tmp_path):
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    registry = DeviceRegistry()
    registry.register(
        device_id="PIPE_A1",
        device_kind=DeviceKind.TYPE_A,
        zone_id="ZONE_01",
        hub_id="H001",
        credential=DeviceCredential(
            credential_id="ECDSA-CRED-01",
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            public_key_pem=public_pem,
        ),
    )
    registry.register(
        device_id="PIPE_B1",
        device_kind=DeviceKind.TYPE_B,
        zone_id="ZONE_01",
        hub_id="H001",
        credential=DeviceCredential(
            credential_id="ECDSA-CRED-02",
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            public_key_pem=None,
        ),
    )
    registry.activate("PIPE_A1")
    registry.activate("PIPE_B1")

    service = C4TrustService(
        registry,
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )
    gate = C4TelemetryGate(
        trust_service=service,
        quarantine_manager=QuarantineManager(quarantine_dir=tmp_path / "quarantine"),
    )

    items = generate_test_items()
    item_a = [it for it in items if it.packet.device_id == "PIPE_A1"][0]
    packet_a = item_a.packet.model_copy(
        update={
            "transport": TransportMetadata(gateway_id="H001"),
            "security": SecurityMetadata(
                credential_id="ECDSA-CRED-01",
                integrity_present=True,
            ),
        }
    )
    sig_a = service.sign_packet_ecdsa(packet_a, private_key)

    # 1. Tampered packet -> Quarantined with SECURITY_FAILURE
    tampered_a = packet_a.model_copy(update={"zone_id": "ZONE_02"})
    res_tampered = gate.process(tampered_a, sig_a, now=tampered_a.observed_at)
    assert not res_tampered.eligible_for_c1
    assert res_tampered.assessment.trust_label is C4TrustLabel.UNTRUSTED
    assert res_tampered.quarantine_record is not None
    assert res_tampered.quarantine_record.quarantine_reason is QuarantineReason.SECURITY_FAILURE
    assert "INTEGRITY_INVALID" in res_tampered.assessment.reason_codes
    assert "private_key" not in res_tampered.quarantine_record.packet_data
    assert "private_key" not in res_tampered.quarantine_record.metadata

    # 2. Unverifiable packet (missing public key) -> Quarantined with EVIDENCE_UNAVAILABLE
    item_b = [it for it in items if it.packet.device_id == "PIPE_B1"][0]
    packet_b = item_b.packet.model_copy(
        update={
            "transport": TransportMetadata(gateway_id="H001"),
            "security": SecurityMetadata(
                credential_id="ECDSA-CRED-02",
                integrity_present=True,
            ),
        }
    )
    sig_b = service.sign_packet_ecdsa(packet_b, private_key)
    res_unverifiable = gate.process(packet_b, sig_b, now=packet_b.observed_at)
    assert not res_unverifiable.eligible_for_c1
    assert res_unverifiable.assessment.trust_label is C4TrustLabel.UNKNOWN
    assert res_unverifiable.assessment.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW
    assert (
        res_unverifiable.quarantine_record.quarantine_reason
        is QuarantineReason.EVIDENCE_UNAVAILABLE
    )
    assert "SIGNATURE_UNVERIFIABLE" in res_unverifiable.assessment.reason_codes
