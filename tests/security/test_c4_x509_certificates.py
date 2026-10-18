"""Comprehensive security verification tests for C4 X.509 certificates and ECDSA.

Verifies X.509 certificate validation, trusted CA hierarchy, identity binding,
validity period enforcement, key usage constraints, certificate revocation,
fail-closed policy, and integration with the C4 trust gate and ML scoring.
"""

from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from components.c4_trust import (
    C4GateResult,
    C4TelemetryGate,
    C4TrustService,
    DeviceCredential,
    DeviceKind,
    DeviceRegistry,
    QuarantineManager,
    X509CertificateValidator,
    create_ca,
    create_crl,
    create_device_certificate,
)
from shared.contracts import TelemetryPacket
from shared.contracts.telemetry import SecurityMetadata, TransportMetadata
from shared.enums import C4RoutingOutcome, C4TrustLabel, SourceOrigin

DEVICE_ID = "GNX-X509-001"
CREDENTIAL_ID = "cred-x509-001"
ZONE_ID = "ZONE-01"
HUB_ID = "H001"


def make_packet(
    *,
    now: datetime,
    packet_id: str = "packet-x509-001",
    device_id: str = DEVICE_ID,
    sequence_no: int | None = 1,
    boot_id: str | None = "boot-001",
    observed_at: datetime | None = None,
    credential_id: str | None = CREDENTIAL_ID,
    certificate_pem: str | None = None,
    zone_id: str = ZONE_ID,
    gateway_id: str = HUB_ID,
) -> TelemetryPacket:
    """Construct a well-formed telemetry packet for C4 assessment."""
    return TelemetryPacket(
        schema_version="1.0",
        packet_id=packet_id,
        device_id=device_id,
        zone_id=zone_id,
        boot_id=boot_id,
        sequence_no=sequence_no,
        observed_at=observed_at or now - timedelta(seconds=1),
        received_at=now,
        source_origin=SourceOrigin.SIMULATED,
        security=SecurityMetadata(
            credential_id=credential_id,
            integrity_present=True,
            certificate_pem=certificate_pem,
        ),
        transport=TransportMetadata(gateway_id=gateway_id),
    )


# 1. Valid certificate from trusted CA and valid ECDSA signature
def test_valid_x509_certificate_and_ecdsa_accepted() -> None:
    now = datetime.now(UTC)
    ca_key, ca_cert, ca_pem = create_ca("GeoNex Root CA")
    dev_key, dev_cert, dev_pem = create_device_certificate(DEVICE_ID, ca_cert, ca_key)

    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id=ZONE_ID,
        hub_id=HUB_ID,
        credential=DeviceCredential(
            credential_id=CREDENTIAL_ID,
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            certificate_pem=dev_pem,
        ),
    )
    registry.activate(DEVICE_ID)

    service = C4TrustService(
        registry,
        trusted_ca_certificates=[ca_cert],
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )

    packet = make_packet(now=now, certificate_pem=dev_pem.decode("utf-8"))
    signature = service.sign_packet_ecdsa(packet, dev_key)

    result = service.assess(packet, signature, now=now)

    assert result.trust_label is C4TrustLabel.TRUSTED
    assert result.mandatory_security_pass is True
    assert result.routing_outcome is C4RoutingOutcome.ACCEPT
    assert "CERTIFICATE_VALID" in result.reason_codes
    assert "INTEGRITY_VALID" in result.reason_codes
    assert "IDENTITY_VALID" in result.reason_codes


# 2. Expired certificate is rejected
def test_expired_x509_certificate_is_rejected() -> None:
    now = datetime.now(UTC)
    ca_key, ca_cert, ca_pem = create_ca("GeoNex Root CA")
    # Certificate was valid 30 days ago, expired 10 days ago
    dev_key, dev_cert, dev_pem = create_device_certificate(
        DEVICE_ID,
        ca_cert,
        ca_key,
        valid_days=10,
        not_before_offset_days=-30,
    )

    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id=ZONE_ID,
        hub_id=HUB_ID,
        credential=DeviceCredential(
            credential_id=CREDENTIAL_ID,
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            certificate_pem=dev_pem,
        ),
    )
    registry.activate(DEVICE_ID)

    service = C4TrustService(
        registry,
        trusted_ca_certificates=[ca_cert],
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )

    packet = make_packet(now=now, certificate_pem=dev_pem.decode("utf-8"))
    signature = service.sign_packet_ecdsa(packet, dev_key)

    result = service.assess(packet, signature, now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert "CERTIFICATE_EXPIRED" in result.reason_codes


# 3. Not-yet-valid certificate is rejected
def test_not_yet_valid_x509_certificate_is_rejected() -> None:
    now = datetime.now(UTC)
    ca_key, ca_cert, ca_pem = create_ca("GeoNex Root CA")
    # Certificate validity starts 5 days in the future
    dev_key, dev_cert, dev_pem = create_device_certificate(
        DEVICE_ID,
        ca_cert,
        ca_key,
        valid_days=30,
        not_before_offset_days=5,
    )

    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id=ZONE_ID,
        hub_id=HUB_ID,
        credential=DeviceCredential(
            credential_id=CREDENTIAL_ID,
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            certificate_pem=dev_pem,
        ),
    )
    registry.activate(DEVICE_ID)

    service = C4TrustService(
        registry,
        trusted_ca_certificates=[ca_cert],
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )

    packet = make_packet(now=now, certificate_pem=dev_pem.decode("utf-8"))
    signature = service.sign_packet_ecdsa(packet, dev_key)

    result = service.assess(packet, signature, now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert "CERTIFICATE_NOT_YET_VALID" in result.reason_codes


# 4. Untrusted issuer (certificate issued by an unauthorized CA) is rejected
def test_untrusted_issuer_ca_is_rejected() -> None:
    now = datetime.now(UTC)
    trusted_ca_key, trusted_ca_cert, _ = create_ca("Trusted GeoNex Root CA")
    rogue_ca_key, rogue_ca_cert, _ = create_ca("Rogue Imposter CA")

    # Certificate signed by rogue CA
    dev_key, dev_cert, dev_pem = create_device_certificate(
        DEVICE_ID, rogue_ca_cert, rogue_ca_key
    )

    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id=ZONE_ID,
        hub_id=HUB_ID,
        credential=DeviceCredential(
            credential_id=CREDENTIAL_ID,
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            certificate_pem=dev_pem,
        ),
    )
    registry.activate(DEVICE_ID)

    # Server only trusts the trusted CA
    service = C4TrustService(
        registry,
        trusted_ca_certificates=[trusted_ca_cert],
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )

    packet = make_packet(now=now, certificate_pem=dev_pem.decode("utf-8"))
    signature = service.sign_packet_ecdsa(packet, dev_key)

    result = service.assess(packet, signature, now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert "CERTIFICATE_UNTRUSTED_ISSUER" in result.reason_codes


# 5. Device identity mismatch between certificate and telemetry packet is rejected
def test_certificate_identity_mismatch_is_rejected() -> None:
    now = datetime.now(UTC)
    ca_key, ca_cert, _ = create_ca("GeoNex Root CA")
    # Certificate was issued for a different device
    dev_key, dev_cert, dev_pem = create_device_certificate(
        "GNX-OTHER-DEVICE-999", ca_cert, ca_key
    )

    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id=ZONE_ID,
        hub_id=HUB_ID,
        credential=DeviceCredential(
            credential_id=CREDENTIAL_ID,
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            certificate_pem=dev_pem,
        ),
    )
    registry.activate(DEVICE_ID)

    service = C4TrustService(
        registry,
        trusted_ca_certificates=[ca_cert],
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )

    packet = make_packet(now=now, certificate_pem=dev_pem.decode("utf-8"))
    signature = service.sign_packet_ecdsa(packet, dev_key)

    result = service.assess(packet, signature, now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert "CERTIFICATE_IDENTITY_MISMATCH" in result.reason_codes


# 6. Self-signed certificate is rejected unless explicitly trusted
def test_self_signed_certificate_rejected() -> None:
    now = datetime.now(UTC)
    trusted_ca_key, trusted_ca_cert, _ = create_ca("Trusted CA")

    # Generate a self-signed device certificate
    dev_key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, DEVICE_ID)])
    self_signed_cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(dev_key.public_key())
        .serial_number(123456)
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=30))
        .sign(dev_key, hashes.SHA256())
    )
    self_signed_pem = self_signed_cert.public_bytes(serialization.Encoding.PEM)

    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id=ZONE_ID,
        hub_id=HUB_ID,
        credential=DeviceCredential(
            credential_id=CREDENTIAL_ID,
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            certificate_pem=self_signed_pem,
        ),
    )
    registry.activate(DEVICE_ID)

    service = C4TrustService(
        registry,
        trusted_ca_certificates=[trusted_ca_cert],
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )

    packet = make_packet(now=now, certificate_pem=self_signed_pem.decode("utf-8"))
    signature = service.sign_packet_ecdsa(packet, dev_key)

    result = service.assess(packet, signature, now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert (
        "CERTIFICATE_SELF_SIGNED" in result.reason_codes
        or "CERTIFICATE_UNTRUSTED_ISSUER" in result.reason_codes
    )


# 7. Certificate with missing digital_signature key usage is rejected
def test_certificate_key_usage_without_digital_signature_is_rejected() -> None:
    now = datetime.now(UTC)
    ca_key, ca_cert, _ = create_ca("GeoNex Root CA")
    # Certificate explicitly generated with digital_signature=False
    dev_key, dev_cert, dev_pem = create_device_certificate(
        DEVICE_ID,
        ca_cert,
        ca_key,
        digital_signature=False,
    )

    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id=ZONE_ID,
        hub_id=HUB_ID,
        credential=DeviceCredential(
            credential_id=CREDENTIAL_ID,
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            certificate_pem=dev_pem,
        ),
    )
    registry.activate(DEVICE_ID)

    service = C4TrustService(
        registry,
        trusted_ca_certificates=[ca_cert],
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )

    packet = make_packet(now=now, certificate_pem=dev_pem.decode("utf-8"))
    signature = service.sign_packet_ecdsa(packet, dev_key)

    result = service.assess(packet, signature, now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert "CERTIFICATE_KEY_USAGE_INVALID" in result.reason_codes


# 8. Certificate revocation list (CRL) denies revoked certificate
def test_revoked_certificate_in_crl_is_rejected() -> None:
    now = datetime.now(UTC)
    ca_key, ca_cert, _ = create_ca("GeoNex Root CA")
    dev_key, dev_cert, dev_pem = create_device_certificate(DEVICE_ID, ca_cert, ca_key)

    crl = create_crl(ca_cert, ca_key, [dev_cert.serial_number])
    validator = X509CertificateValidator(
        trusted_ca_certificates=[ca_cert],
        crls=[crl],
    )

    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id=ZONE_ID,
        hub_id=HUB_ID,
        credential=DeviceCredential(
            credential_id=CREDENTIAL_ID,
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            certificate_pem=dev_pem,
        ),
    )
    registry.activate(DEVICE_ID)

    service = C4TrustService(
        registry,
        certificate_validator=validator,
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )

    packet = make_packet(now=now, certificate_pem=dev_pem.decode("utf-8"))
    signature = service.sign_packet_ecdsa(packet, dev_key)

    result = service.assess(packet, signature, now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert "CERTIFICATE_REVOKED" in result.reason_codes


# 9. Device revoked in registry is denied
def test_revoked_device_in_registry_is_denied() -> None:
    now = datetime.now(UTC)
    ca_key, ca_cert, _ = create_ca("GeoNex Root CA")
    dev_key, dev_cert, dev_pem = create_device_certificate(DEVICE_ID, ca_cert, ca_key)

    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id=ZONE_ID,
        hub_id=HUB_ID,
        credential=DeviceCredential(
            credential_id=CREDENTIAL_ID,
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            certificate_pem=dev_pem,
        ),
    )
    registry.activate(DEVICE_ID)
    # Revoke device
    registry.revoke(DEVICE_ID)

    service = C4TrustService(
        registry,
        trusted_ca_certificates=[ca_cert],
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )

    packet = make_packet(now=now, certificate_pem=dev_pem.decode("utf-8"))
    signature = service.sign_packet_ecdsa(packet, dev_key)

    result = service.assess(packet, signature, now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert "DEVICE_NOT_ACTIVE" in result.reason_codes


# 10. Tampered telemetry payload fails signature verification even with valid certificate
def test_tampered_telemetry_payload_fails_with_valid_certificate() -> None:
    now = datetime.now(UTC)
    ca_key, ca_cert, _ = create_ca("GeoNex Root CA")
    dev_key, dev_cert, dev_pem = create_device_certificate(DEVICE_ID, ca_cert, ca_key)

    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id=ZONE_ID,
        hub_id=HUB_ID,
        credential=DeviceCredential(
            credential_id=CREDENTIAL_ID,
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            certificate_pem=dev_pem,
        ),
    )
    registry.activate(DEVICE_ID)

    service = C4TrustService(
        registry,
        trusted_ca_certificates=[ca_cert],
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )

    packet = make_packet(now=now, certificate_pem=dev_pem.decode("utf-8"))
    signature = service.sign_packet_ecdsa(packet, dev_key)

    # Tamper with message_type
    tampered_packet = packet.model_copy(update={"message_type": "TAMPERED_ALERT"})
    result = service.assess(tampered_packet, signature, now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert "INTEGRITY_INVALID" in result.reason_codes


# 11. Signature generated with wrong private key is rejected
def test_signature_generated_with_wrong_private_key_is_rejected() -> None:
    now = datetime.now(UTC)
    ca_key, ca_cert, _ = create_ca("GeoNex Root CA")
    dev_key, dev_cert, dev_pem = create_device_certificate(DEVICE_ID, ca_cert, ca_key)
    imposter_key = ec.generate_private_key(ec.SECP256R1())

    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id=ZONE_ID,
        hub_id=HUB_ID,
        credential=DeviceCredential(
            credential_id=CREDENTIAL_ID,
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            certificate_pem=dev_pem,
        ),
    )
    registry.activate(DEVICE_ID)

    service = C4TrustService(
        registry,
        trusted_ca_certificates=[ca_cert],
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )

    packet = make_packet(now=now, certificate_pem=dev_pem.decode("utf-8"))
    imposter_signature = service.sign_packet_ecdsa(packet, imposter_key)

    result = service.assess(packet, imposter_signature, now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert "INTEGRITY_INVALID" in result.reason_codes


# 12. Mandatory security failures cannot be overridden by behavioral ML score
def test_certificate_failure_cannot_be_overridden_by_high_ml_score() -> None:
    now = datetime.now(UTC)
    ca_key, ca_cert, _ = create_ca("GeoNex Root CA")
    # Expired cert
    dev_key, dev_cert, dev_pem = create_device_certificate(
        DEVICE_ID,
        ca_cert,
        ca_key,
        valid_days=5,
        not_before_offset_days=-20,
    )

    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id=ZONE_ID,
        hub_id=HUB_ID,
        credential=DeviceCredential(
            credential_id=CREDENTIAL_ID,
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            certificate_pem=dev_pem,
        ),
    )
    registry.activate(DEVICE_ID)

    service = C4TrustService(
        registry,
        trusted_ca_certificates=[ca_cert],
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )

    packet = make_packet(now=now, certificate_pem=dev_pem.decode("utf-8"))
    signature = service.sign_packet_ecdsa(packet, dev_key)

    # Optimal behavioral score (0.0 = completely normal)
    result = service.assess(packet, signature, now=now, behavioural_score=0.0)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert "CERTIFICATE_EXPIRED" in result.reason_codes


# 13. C4TelemetryGate integration: invalid cert is quarantined, eligible_packet is None
def test_c4_gate_quarantines_certificate_failures(tmp_path) -> None:
    now = datetime.now(UTC)
    ca_key, ca_cert, _ = create_ca("GeoNex Root CA")
    # Expired cert
    dev_key, dev_cert, dev_pem = create_device_certificate(
        DEVICE_ID,
        ca_cert,
        ca_key,
        valid_days=5,
        not_before_offset_days=-20,
    )

    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id=ZONE_ID,
        hub_id=HUB_ID,
        credential=DeviceCredential(
            credential_id=CREDENTIAL_ID,
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            certificate_pem=dev_pem,
        ),
    )
    registry.activate(DEVICE_ID)

    service = C4TrustService(
        registry,
        trusted_ca_certificates=[ca_cert],
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )
    quarantine_mgr = QuarantineManager(quarantine_dir=tmp_path / "quarantine")
    gate = C4TelemetryGate(trust_service=service, quarantine_manager=quarantine_mgr)

    packet = make_packet(now=now, certificate_pem=dev_pem.decode("utf-8"))
    signature = service.sign_packet_ecdsa(packet, dev_key)

    gate_result: C4GateResult = gate.process(packet, signature, now=now)

    assert gate_result.eligible_for_c1 is False
    assert gate_result.eligible_packet is None
    assert gate_result.quarantine_record is not None
    assert gate_result.assessment.trust_label is C4TrustLabel.UNTRUSTED
    assert "CERTIFICATE_EXPIRED" in gate_result.assessment.reason_codes


# 14. Missing certificate when require_certificate=True fails closed
def test_missing_certificate_when_required_fails_closed() -> None:
    now = datetime.now(UTC)
    ca_key, ca_cert, _ = create_ca("GeoNex Root CA")
    private_key = ec.generate_private_key(ec.SECP256R1())

    registry = DeviceRegistry()
    registry.register(
        device_id=DEVICE_ID,
        device_kind=DeviceKind.TYPE_A,
        zone_id=ZONE_ID,
        hub_id=HUB_ID,
        credential=DeviceCredential(
            credential_id=CREDENTIAL_ID,
            secret=b"unused",
            signature_algorithm="ecdsa-sha256",
            public_key_pem=private_key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            ),
            certificate_pem=None,  # No certificate!
        ),
    )
    registry.activate(DEVICE_ID)

    service = C4TrustService(
        registry,
        trusted_ca_certificates=[ca_cert],
        require_certificate=True,  # STRICT ENFORCEMENT
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )

    packet = make_packet(now=now, certificate_pem=None)
    signature = service.sign_packet_ecdsa(packet, private_key)

    result = service.assess(packet, signature, now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert "CERTIFICATE_MISSING" in result.reason_codes
