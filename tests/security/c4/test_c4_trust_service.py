
from datetime import UTC, datetime, timedelta

import pytest

from components.c4_trust import C4TrustService, DeviceCredential, DeviceKind, DeviceRegistry
from shared.contracts import C4TrustAssessment, TelemetryPacket
from shared.contracts.telemetry import SecurityMetadata, TransportMetadata
from shared.enums import (
    AssessmentContext,
    C4RoutingOutcome,
    C4TrustLabel,
    ProcessingStatus,
    SourceOrigin,
)

SECRET = b"test-device-secret"
CREDENTIAL_ID = "cred-001"
DEVICE_ID = "GNX-DEVICE-001"


def make_service() -> C4TrustService:
    return C4TrustService(
        {
            DEVICE_ID: DeviceCredential(
                credential_id=CREDENTIAL_ID,
                secret=SECRET,
            )
        },
        max_age_seconds=30,
        future_tolerance_seconds=5,
        suspicious_score_threshold=0.7,
        attestation_verifier=lambda packet, device: True,
        provenance_verifier=lambda packet, device: True,
        allow_deterministic_only=True,
    )


def make_packet(
    *,
    now: datetime,
    packet_id: str = "packet-001",
    device_id: str = DEVICE_ID,
    sequence_no: int | None = 1,
    boot_id: str | None = "boot-001",
    observed_at: datetime | None = None,
    credential_id: str | None = CREDENTIAL_ID,
) -> TelemetryPacket:
    return TelemetryPacket(
        schema_version="1.0",
        packet_id=packet_id,
        device_id=device_id,
        zone_id="ZONE-01",
        boot_id=boot_id,
        sequence_no=sequence_no,
        observed_at=observed_at or now - timedelta(seconds=1),
        received_at=now,
        source_origin=SourceOrigin.SIMULATED,
        security=SecurityMetadata(
            credential_id=credential_id,
            integrity_present=True,
        ),
        transport=TransportMetadata(gateway_id="H001"),
    )


def sign(service: C4TrustService, packet: TelemetryPacket) -> str:
    return service.sign_packet(packet, SECRET)


def test_valid_packet_is_trusted_and_accepted() -> None:
    now = datetime.now(UTC)
    service = make_service()
    packet = make_packet(now=now)

    result = service.assess(packet, sign(service, packet), now=now)

    assert result.trust_label is C4TrustLabel.TRUSTED
    assert result.mandatory_security_pass is True
    assert result.routing_outcome is C4RoutingOutcome.ACCEPT
    assert {
        "IDENTITY_VALID",
        "CREDENTIAL_ID_VALID",
        "INTEGRITY_VALID",
        "ATTESTATION_VALID",
        "PROVENANCE_VALID",
        "FRESHNESS_VALID",
        "REPLAY_CHECK_VALID",
    }.issubset(result.reason_codes)


def test_tampered_packet_fails_integrity_check() -> None:
    now = datetime.now(UTC)
    service = make_service()
    packet = make_packet(now=now)
    signature = sign(service, packet)
    tampered_packet = packet.model_copy(update={"zone_id": "ZONE-02"})

    result = service.assess(tampered_packet, signature, now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert "INTEGRITY_INVALID" in result.reason_codes
    assert result.routing_outcome is C4RoutingOutcome.REJECT


def test_unknown_device_is_rejected() -> None:
    now = datetime.now(UTC)
    service = make_service()
    packet = make_packet(now=now, device_id="UNKNOWN-DEVICE")

    result = service.assess(packet, "invalid-signature", now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert "DEVICE_UNKNOWN" in result.reason_codes
    assert result.routing_outcome is C4RoutingOutcome.REJECT


def test_missing_credential_id_is_rejected() -> None:
    now = datetime.now(UTC)
    service = make_service()
    packet = make_packet(now=now, credential_id=None)

    result = service.assess(packet, sign(service, packet), now=now)

    assert result.trust_label is C4TrustLabel.UNKNOWN
    assert result.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW
    assert "CREDENTIAL_ID_MISSING" in result.reason_codes


def test_expired_packet_is_rejected() -> None:
    now = datetime.now(UTC)
    service = make_service()
    packet = make_packet(
        now=now,
        observed_at=now - timedelta(seconds=60),
    )

    result = service.assess(packet, sign(service, packet), now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert "FRESHNESS_EXPIRED" in result.reason_codes


def test_future_timestamp_is_rejected() -> None:
    now = datetime.now(UTC)
    service = make_service()
    packet = make_packet(
        now=now,
        observed_at=now + timedelta(seconds=10),
    )

    result = service.assess(packet, sign(service, packet), now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert "TIMESTAMP_IN_FUTURE" in result.reason_codes


def test_duplicate_packet_is_rejected_as_replay() -> None:
    now = datetime.now(UTC)
    service = make_service()
    packet = make_packet(now=now)
    signature = sign(service, packet)

    first_result = service.assess(packet, signature, now=now)
    second_result = service.assess(packet, signature, now=now)

    assert first_result.trust_label is C4TrustLabel.TRUSTED
    assert second_result.trust_label is C4TrustLabel.UNTRUSTED
    assert "REPLAY_DETECTED" in second_result.reason_codes


def test_repeated_sequence_number_is_rejected() -> None:
    now = datetime.now(UTC)
    service = make_service()
    first_packet = make_packet(
        now=now,
        packet_id="packet-first",
        sequence_no=10,
    )
    second_packet = make_packet(
        now=now,
        packet_id="packet-second",
        sequence_no=10,
    )

    first_result = service.assess(
        first_packet,
        sign(service, first_packet),
        now=now,
    )
    second_result = service.assess(
        second_packet,
        sign(service, second_packet),
        now=now,
    )

    assert first_result.trust_label is C4TrustLabel.TRUSTED
    assert second_result.trust_label is C4TrustLabel.UNTRUSTED
    assert "SEQUENCE_REPLAY_DETECTED" in second_result.reason_codes


def test_behavioural_score_cannot_override_security_failure() -> None:
    now = datetime.now(UTC)
    service = make_service()
    packet = make_packet(now=now)

    result = service.assess(
        packet,
        "wrong-signature",
        now=now,
        behavioural_score=1.0,
    )

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT


def test_naive_assessment_time_is_rejected() -> None:
    service = make_service()
    packet = make_packet(now=datetime.now(UTC))

    with pytest.raises(ValueError, match="timezone-aware"):
        service.assess(
            packet,
            sign(service, packet),
            now=datetime(2026, 10, 11, 12, 0, 0),
        )


def test_high_behavioural_score_is_quarantined() -> None:
    now = datetime.now(UTC)
    service = make_service()
    packet = make_packet(now=now)

    result = service.assess(
        packet,
        sign(service, packet),
        now=now,
        behavioural_score=0.9,
    )

    assert result.trust_label is C4TrustLabel.SUSPICIOUS
    assert result.mandatory_security_pass is True
    assert result.routing_outcome is C4RoutingOutcome.QUARANTINE
    assert "BEHAVIOURAL_ANOMALY" in result.reason_codes


def test_low_behavioural_score_remains_trusted() -> None:
    now = datetime.now(UTC)
    service = make_service()
    packet = make_packet(now=now)

    result = service.assess(
        packet,
        sign(service, packet),
        now=now,
        behavioural_score=0.1,
    )

    assert result.trust_label is C4TrustLabel.TRUSTED
    assert result.mandatory_security_pass is True
    assert result.routing_outcome is C4RoutingOutcome.ACCEPT


def test_invalid_behavioural_score_is_rejected() -> None:
    now = datetime.now(UTC)
    service = make_service()
    packet = make_packet(now=now)

    with pytest.raises(ValueError, match="between 0 and 1"):
        service.assess(
            packet,
            sign(service, packet),
            now=now,
            behavioural_score=1.5,
        )


def test_service_with_device_registry() -> None:
    """Test C4TrustService integration with DeviceRegistry."""
    now = datetime.now(UTC)

    # Create registry with active device
    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id="ZONE-01",
        hub_id="H001",
        credential=DeviceCredential(
            credential_id=CREDENTIAL_ID,
            secret=SECRET,
        ),
    )
    registry.activate(DEVICE_ID)

    # Create service with registry
    service = C4TrustService(
        registry,
        max_age_seconds=30,
        future_tolerance_seconds=5,
        suspicious_score_threshold=0.7,
        attestation_verifier=lambda packet, device: True,
        provenance_verifier=lambda packet, device: True,
        allow_deterministic_only=True,
    )

    packet = make_packet(now=now)
    result = service.assess(packet, sign(service, packet), now=now)

    assert result.trust_label is C4TrustLabel.TRUSTED
    assert result.mandatory_security_pass is True


def test_missing_attestation_or_provenance_is_unknown_and_reviewed() -> None:
    now = datetime.now(UTC)
    service = C4TrustService(
        {DEVICE_ID: DeviceCredential(CREDENTIAL_ID, SECRET)},
        allow_deterministic_only=True,
    )
    packet = make_packet(now=now)

    result = service.assess(packet, sign(service, packet), now=now)

    assert result.trust_label is C4TrustLabel.UNKNOWN
    assert result.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW
    assert result.mandatory_security_pass is False
    assert "ATTESTATION_UNVERIFIED" in result.reason_codes
    assert "PROVENANCE_UNVERIFIED" in result.reason_codes


@pytest.mark.parametrize(
    ("attestation_result", "provenance_result", "expected_reason"),
    [
        (False, True, "ATTESTATION_INVALID"),
        (True, False, "PROVENANCE_INVALID"),
    ],
)
def test_failed_attestation_or_provenance_is_untrusted(
    attestation_result: bool,
    provenance_result: bool,
    expected_reason: str,
) -> None:
    now = datetime.now(UTC)
    service = C4TrustService(
        {DEVICE_ID: DeviceCredential(CREDENTIAL_ID, SECRET)},
        attestation_verifier=lambda packet, device: attestation_result,
        provenance_verifier=lambda packet, device: provenance_result,
        allow_deterministic_only=True,
    )
    packet = make_packet(now=now)

    result = service.assess(packet, sign(service, packet), now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert expected_reason in result.reason_codes


def test_expired_credential_is_untrusted() -> None:
    now = datetime.now(UTC)
    service = C4TrustService(
        {
            DEVICE_ID: DeviceCredential(
                CREDENTIAL_ID,
                SECRET,
                expires_at=now - timedelta(seconds=1),
            )
        },
        attestation_verifier=lambda packet, device: True,
        provenance_verifier=lambda packet, device: True,
        allow_deterministic_only=True,
    )
    packet = make_packet(now=now)

    result = service.assess(packet, sign(service, packet), now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert "CREDENTIAL_EXPIRED" in result.reason_codes


def test_missing_sequence_evidence_is_unknown():
    now = datetime.now(UTC)
    service = make_service()
    packet = make_packet(now=now, boot_id=None, sequence_no=None)

    result = service.assess(packet, sign(service, packet), now=now)

    assert result.trust_label is C4TrustLabel.UNKNOWN
    assert result.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW
    assert "SEQUENCE_EVIDENCE_MISSING" in result.reason_codes


def test_required_firmware_approval_without_registry_approval_is_unknown():
    now = datetime.now(UTC)
    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id="ZONE-01",
        hub_id="H001",
        credential=DeviceCredential(CREDENTIAL_ID, SECRET),
    )
    registry.activate(DEVICE_ID)
    service = C4TrustService(
        registry,
        attestation_verifier=lambda packet, device: True,
        provenance_verifier=lambda packet, device: True,
        allow_deterministic_only=True,
        require_firmware_approval=True,
    )
    packet = make_packet(now=now)

    result = service.assess(packet, sign(service, packet), now=now)

    assert result.trust_label is C4TrustLabel.UNKNOWN
    assert "FIRMWARE_APPROVAL_MISSING" in result.reason_codes


def test_registered_zone_mismatch_is_untrusted() -> None:
    now = datetime.now(UTC)
    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id="OTHER-ZONE",
        hub_id="H001",
        credential=DeviceCredential(CREDENTIAL_ID, SECRET),
    )
    registry.activate(DEVICE_ID)
    service = C4TrustService(
        registry,
        attestation_verifier=lambda packet, device: True,
        provenance_verifier=lambda packet, device: True,
        allow_deterministic_only=True,
    )
    packet = make_packet(now=now)

    result = service.assess(packet, sign(service, packet), now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert "ZONE_MISMATCH" in result.reason_codes


def test_authorized_recovery_can_bypass_freshness_only_with_valid_context() -> None:
    now = datetime.now(UTC)
    service = make_service()
    packet = make_packet(now=now, observed_at=now - timedelta(minutes=5))
    service.create_recovery_context(
        "RECOVERY-1",
        DEVICE_ID,
        packet.observed_at - timedelta(seconds=1),
        packet.observed_at + timedelta(seconds=1),
    )

    result = service.assess(
        packet,
        sign(service, packet),
        now=now,
        recovery_request_id="RECOVERY-1",
    )

    assert result.trust_label is C4TrustLabel.TRUSTED
    assert "AUTHORIZED_REPLAY_FRESHNESS_EXCEPTION" in result.reason_codes


def test_deterministic_only_trust_requires_explicit_policy() -> None:
    now = datetime.now(UTC)
    service = C4TrustService(
        {DEVICE_ID: DeviceCredential(CREDENTIAL_ID, SECRET)},
        attestation_verifier=lambda packet, device: True,
        provenance_verifier=lambda packet, device: True,
    )
    packet = make_packet(now=now)

    result = service.assess(packet, sign(service, packet), now=now)

    assert result.trust_label is C4TrustLabel.UNKNOWN
    assert result.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW
    assert result.mandatory_security_pass is True
    assert "BEHAVIOURAL_SCORE_UNAVAILABLE" in result.reason_codes


def test_service_with_suspended_device_is_rejected() -> None:
    """Test that suspended devices are rejected."""
    now = datetime.now(UTC)

    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
        credential=DeviceCredential(
            credential_id=CREDENTIAL_ID,
            secret=SECRET,
        ),
    )
    registry.suspend(DEVICE_ID)

    service = C4TrustService(registry)

    packet = make_packet(now=now)
    result = service.assess(packet, sign(service, packet), now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert "DEVICE_NOT_ACTIVE" in result.reason_codes


def test_service_with_revoked_and_retired_device_is_rejected() -> None:
    now = datetime.now(UTC)

    # Test revoked device
    registry_revoked = DeviceRegistry()
    registry_revoked.register(
        device_id="GNX-REVOKED-01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="ZONE-01",
        hub_id="H001",
        credential=DeviceCredential(CREDENTIAL_ID, SECRET),
    )
    registry_revoked.activate("GNX-REVOKED-01")
    registry_revoked.revoke("GNX-REVOKED-01")

    service_revoked = C4TrustService(registry_revoked)
    packet_revoked = make_packet(now=now, device_id="GNX-REVOKED-01")
    result_revoked = service_revoked.assess(
        packet_revoked,
        service_revoked.sign_packet(packet_revoked, SECRET),
        now=now,
    )
    assert result_revoked.trust_label is C4TrustLabel.UNTRUSTED
    assert result_revoked.routing_outcome is C4RoutingOutcome.REJECT
    assert "DEVICE_NOT_ACTIVE" in result_revoked.reason_codes

    # Test retired device
    registry_retired = DeviceRegistry()
    registry_retired.register(
        device_id="GNX-RETIRED-01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="ZONE-01",
        hub_id="H001",
        credential=DeviceCredential(CREDENTIAL_ID, SECRET),
    )
    registry_retired.activate("GNX-RETIRED-01")
    registry_retired.retire("GNX-RETIRED-01")

    service_retired = C4TrustService(registry_retired)
    packet_retired = make_packet(now=now, device_id="GNX-RETIRED-01")
    result_retired = service_retired.assess(
        packet_retired,
        service_retired.sign_packet(packet_retired, SECRET),
        now=now,
    )
    assert result_retired.trust_label is C4TrustLabel.UNTRUSTED
    assert result_retired.routing_outcome is C4RoutingOutcome.REJECT
    assert "DEVICE_NOT_ACTIVE" in result_retired.reason_codes


def test_registered_device_without_configured_credential_is_reviewed() -> None:
    now = datetime.now(UTC)
    registry = DeviceRegistry()
    registry.register(
        device_id="GNX-NO-CRED-01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="ZONE-01",
        hub_id="H001",
        credential=None,
    )
    registry.activate("GNX-NO-CRED-01")

    service = C4TrustService(registry, allow_deterministic_only=True)
    packet = make_packet(now=now, device_id="GNX-NO-CRED-01")
    result = service.assess(packet, "any-sig", now=now)

    assert result.trust_label is C4TrustLabel.UNKNOWN
    assert result.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW
    assert result.mandatory_security_pass is False
    assert "CREDENTIAL_NOT_CONFIGURED" in result.reason_codes
    assert "SIGNATURE_UNVERIFIABLE" in result.reason_codes


def test_firmware_and_config_approval_failures_in_assessment() -> None:
    now = datetime.now(UTC)
    registry = DeviceRegistry()
    registry.register(
        device_id="GNX-APPROVED-01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="ZONE-01",
        hub_id="H001",
        credential=DeviceCredential(CREDENTIAL_ID, SECRET),
        firmware_hash="approved-fw-hash-001",
        config_hash="approved-cfg-hash-001",
        approved_firmware=True,
        approved_config=True,
    )
    registry.activate("GNX-APPROVED-01")

    service = C4TrustService(
        registry,
        allow_deterministic_only=True,
        require_firmware_approval=True,
        require_config_approval=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )

    # 1. Firmware hash mismatch -> FIRMWARE_UNAPPROVED
    packet_fw_mismatch = make_packet(now=now, device_id="GNX-APPROVED-01").model_copy(
        update={
            "security": SecurityMetadata(
                credential_id=CREDENTIAL_ID,
                integrity_present=True,
                firmware_hash="unapproved-fw-hash",
                config_hash="approved-cfg-hash-001",
            )
        }
    )
    sig_fw = service.sign_packet(packet_fw_mismatch, SECRET)
    res_fw = service.assess(packet_fw_mismatch, sig_fw, now=now)
    assert res_fw.trust_label is C4TrustLabel.UNTRUSTED
    assert res_fw.routing_outcome is C4RoutingOutcome.REJECT
    assert "FIRMWARE_UNAPPROVED" in res_fw.reason_codes

    # 2. Firmware evidence missing -> FIRMWARE_EVIDENCE_MISSING
    packet_fw_missing = make_packet(now=now, device_id="GNX-APPROVED-01").model_copy(
        update={
            "security": SecurityMetadata(
                credential_id=CREDENTIAL_ID,
                integrity_present=True,
                firmware_hash=None,
                config_hash="approved-cfg-hash-001",
            )
        }
    )
    sig_fw_miss = service.sign_packet(packet_fw_missing, SECRET)
    res_fw_miss = service.assess(packet_fw_missing, sig_fw_miss, now=now)
    assert res_fw_miss.trust_label is C4TrustLabel.UNKNOWN
    assert res_fw_miss.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW
    assert "FIRMWARE_EVIDENCE_MISSING" in res_fw_miss.reason_codes

    # 3. Config hash mismatch -> CONFIG_MISMATCH
    packet_cfg_mismatch = make_packet(now=now, device_id="GNX-APPROVED-01").model_copy(
        update={
            "security": SecurityMetadata(
                credential_id=CREDENTIAL_ID,
                integrity_present=True,
                firmware_hash="approved-fw-hash-001",
                config_hash="unapproved-cfg-hash",
            )
        }
    )
    sig_cfg = service.sign_packet(packet_cfg_mismatch, SECRET)
    res_cfg = service.assess(packet_cfg_mismatch, sig_cfg, now=now)
    assert res_cfg.trust_label is C4TrustLabel.UNTRUSTED
    assert res_cfg.routing_outcome is C4RoutingOutcome.REJECT
    assert "CONFIG_MISMATCH" in res_cfg.reason_codes

    # 4. Config evidence missing -> CONFIG_EVIDENCE_MISSING
    packet_cfg_missing = make_packet(now=now, device_id="GNX-APPROVED-01").model_copy(
        update={
            "security": SecurityMetadata(
                credential_id=CREDENTIAL_ID,
                integrity_present=True,
                firmware_hash="approved-fw-hash-001",
                config_hash=None,
            )
        }
    )
    sig_cfg_miss = service.sign_packet(packet_cfg_missing, SECRET)
    res_cfg_miss = service.assess(packet_cfg_missing, sig_cfg_miss, now=now)
    assert res_cfg_miss.trust_label is C4TrustLabel.UNKNOWN
    assert res_cfg_miss.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW
    assert "CONFIG_EVIDENCE_MISSING" in res_cfg_miss.reason_codes


def test_gateway_hub_id_enforcement() -> None:
    now = datetime.now(UTC)
    registry = DeviceRegistry()
    registry.register(
        device_id="GNX-HUB-TEST-01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="ZONE-01",
        hub_id="H001",
        credential=DeviceCredential(CREDENTIAL_ID, SECRET),
    )
    registry.activate("GNX-HUB-TEST-01")

    service = C4TrustService(
        registry,
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )

    # Missing gateway_id -> HUB_ID_MISSING
    packet_missing_hub = make_packet(now=now, device_id="GNX-HUB-TEST-01").model_copy(
        update={"transport": TransportMetadata(gateway_id=None)}
    )
    sig_missing = service.sign_packet(packet_missing_hub, SECRET)
    res_missing = service.assess(packet_missing_hub, sig_missing, now=now)
    assert res_missing.trust_label is C4TrustLabel.UNKNOWN
    assert res_missing.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW
    assert "HUB_ID_MISSING" in res_missing.reason_codes

    # Mismatched gateway_id -> HUB_MISMATCH
    packet_wrong_hub = make_packet(now=now, device_id="GNX-HUB-TEST-01").model_copy(
        update={"transport": TransportMetadata(gateway_id="H999_ROGUE")}
    )
    sig_wrong = service.sign_packet(packet_wrong_hub, SECRET)
    res_wrong = service.assess(packet_wrong_hub, sig_wrong, now=now)
    assert res_wrong.trust_label is C4TrustLabel.UNTRUSTED
    assert res_wrong.routing_outcome is C4RoutingOutcome.REJECT
    assert "HUB_MISMATCH" in res_wrong.reason_codes


def test_credential_validity_window_enforcement() -> None:
    now = datetime.now(UTC)

    # Credential not yet valid (issued_at in future)
    service_future_cred = C4TrustService(
        {
            DEVICE_ID: DeviceCredential(
                credential_id=CREDENTIAL_ID,
                secret=SECRET,
                issued_at=now + timedelta(hours=1),
            )
        },
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )
    packet = make_packet(now=now)
    sig = service_future_cred.sign_packet(packet, SECRET)
    res_not_yet = service_future_cred.assess(packet, sig, now=now)
    assert res_not_yet.trust_label is C4TrustLabel.UNTRUSTED
    assert res_not_yet.routing_outcome is C4RoutingOutcome.REJECT
    assert "CREDENTIAL_NOT_YET_VALID" in res_not_yet.reason_codes

    # Naive issued_at and expires_at
    service_naive_cred = C4TrustService(
        {
            DEVICE_ID: DeviceCredential(
                credential_id=CREDENTIAL_ID,
                secret=SECRET,
                issued_at=datetime(2026, 1, 1, 0, 0, 0),  # naive
                expires_at=datetime(2026, 12, 31, 0, 0, 0),  # naive
            )
        },
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )
    res_naive = service_naive_cred.assess(packet, sig, now=now)
    assert res_naive.trust_label is C4TrustLabel.UNKNOWN
    assert res_naive.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW
    assert "CREDENTIAL_ISSUED_AT_INVALID" in res_naive.reason_codes
    assert "CREDENTIAL_EXPIRES_AT_INVALID" in res_naive.reason_codes


def test_behavioral_scorer_failure_and_invalid_score_fail_closed() -> None:
    now = datetime.now(UTC)

    # Scorer raises an exception
    def broken_scorer(p: TelemetryPacket) -> float:
        raise RuntimeError("ML model execution error")

    service_broken = C4TrustService(
        {DEVICE_ID: DeviceCredential(CREDENTIAL_ID, SECRET)},
        behavioural_scorer=broken_scorer,
        allow_deterministic_only=False,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )
    packet = make_packet(now=now)
    sig = service_broken.sign_packet(packet, SECRET)
    res_broken = service_broken.assess(packet, sig, now=now)
    assert res_broken.trust_label is C4TrustLabel.UNKNOWN
    assert res_broken.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW
    assert "BEHAVIOURAL_INFERENCE_FAILED" in res_broken.reason_codes

    # Scorer returns float('nan')
    service_nan = C4TrustService(
        {DEVICE_ID: DeviceCredential(CREDENTIAL_ID, SECRET)},
        behavioural_scorer=lambda p: float("nan"),
        allow_deterministic_only=False,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )
    res_nan = service_nan.assess(packet, sig, now=now)
    assert res_nan.trust_label is C4TrustLabel.UNKNOWN
    assert res_nan.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW
    assert "BEHAVIOURAL_SCORE_INVALID" in res_nan.reason_codes


def test_hmac_signature_mismatch_is_rejected() -> None:
    now = datetime.now(UTC)
    service = make_service()
    packet = make_packet(now=now)

    # Construct wrong HMAC signature (valid hex of wrong key)
    wrong_sig = C4TrustService.sign_packet(packet, b"wrong-secret-key")
    result = service.assess(packet, wrong_sig, now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert "INTEGRITY_INVALID" in result.reason_codes


def test_untrusted_and_unknown_contracts_reject_accept_outcome() -> None:
    now = datetime.now(UTC)

    # UNTRUSTED cannot route to ACCEPT
    with pytest.raises(ValueError, match="cannot use the ACCEPT routing outcome"):
        C4TrustAssessment(
            schema_version="1.0",
            assessment_id="TEST-001",
            packet_id="PKT-001",
            device_id="DEV-001",
            trust_label=C4TrustLabel.UNTRUSTED,
            trust_score=0.0,
            mandatory_security_pass=False,
            routing_outcome=C4RoutingOutcome.ACCEPT,
            processing_status=ProcessingStatus.OK,
            assessment_context=AssessmentContext.RUNTIME,
            generated_at=now,
        )

    # UNKNOWN cannot route to ACCEPT
    with pytest.raises(ValueError, match="must use the SECURITY_REVIEW routing outcome"):
        C4TrustAssessment(
            schema_version="1.0",
            assessment_id="TEST-002",
            packet_id="PKT-002",
            device_id="DEV-002",
            trust_label=C4TrustLabel.UNKNOWN,
            trust_score=None,
            mandatory_security_pass=False,
            routing_outcome=C4RoutingOutcome.ACCEPT,
            processing_status=ProcessingStatus.OK,
            assessment_context=AssessmentContext.RUNTIME,
            generated_at=now,
        )
