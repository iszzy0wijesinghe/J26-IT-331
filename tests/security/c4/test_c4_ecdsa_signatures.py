"""Comprehensive security verification tests for C4 ECDSA-SHA256 signatures.

Verifies ECDSA-SHA256 signing and verification, public-key validation,
fail-closed error handling, algorithm isolation, and mandatory security
precedence over behavioral ML scoring.
"""

from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from components.c4_trust import (
    C4TrustService,
    DeviceCredential,
    DeviceKind,
    DeviceRegistry,
)
from shared.contracts import TelemetryPacket
from shared.contracts.telemetry import SecurityMetadata, TransportMetadata
from shared.enums import C4RoutingOutcome, C4TrustLabel, SourceOrigin

DEVICE_ID = "GNX-ECDSA-001"
CREDENTIAL_ID = "cred-ecdsa-001"
ZONE_ID = "ZONE-01"
HUB_ID = "H001"


def generate_ec_key_pair() -> tuple[ec.EllipticCurvePrivateKey, bytes]:
    """Generate a fresh EC key pair in memory (private key kept in memory only)."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_key, public_pem


def generate_rsa_public_key_pem() -> bytes:
    """Generate an RSA public key PEM to test non-EC public key rejection."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def make_packet(
    *,
    now: datetime,
    packet_id: str = "packet-ecdsa-001",
    device_id: str = DEVICE_ID,
    sequence_no: int | None = 1,
    boot_id: str | None = "boot-001",
    observed_at: datetime | None = None,
    credential_id: str | None = CREDENTIAL_ID,
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
        ),
        transport=TransportMetadata(gateway_id=gateway_id),
    )


def make_service(
    public_key_pem: bytes | str | None,
    *,
    device_id: str = DEVICE_ID,
    credential_id: str = CREDENTIAL_ID,
    signature_algorithm: str = "ecdsa-sha256",
    allow_deterministic_only: bool = True,
    behavioural_scorer=None,
) -> C4TrustService:
    """Construct a C4TrustService with ECDSA credential."""
    credential = DeviceCredential(
        credential_id=credential_id,
        secret=b"unused-for-ecdsa",
        signature_algorithm=signature_algorithm,
        public_key_pem=public_key_pem,
    )
    return C4TrustService(
        {device_id: credential},
        max_age_seconds=30,
        future_tolerance_seconds=5,
        suspicious_score_threshold=0.7,
        attestation_verifier=lambda packet, device: True,
        provenance_verifier=lambda packet, device: True,
        behavioural_scorer=behavioural_scorer,
        allow_deterministic_only=allow_deterministic_only,
    )


# 1. Valid ECDSA-SHA256 signature accepted when all checks pass
def test_valid_ecdsa_signature_accepted_when_all_checks_pass() -> None:
    now = datetime.now(UTC)
    private_key, public_pem = generate_ec_key_pair()
    service = make_service(public_pem)
    packet = make_packet(now=now)

    signature = service.sign_packet_ecdsa(packet, private_key)
    result = service.assess(packet, signature, now=now)

    assert result.trust_label is C4TrustLabel.TRUSTED
    assert result.mandatory_security_pass is True
    assert result.routing_outcome is C4RoutingOutcome.ACCEPT
    assert result.trust_score == 1.0
    assert {
        "IDENTITY_VALID",
        "CREDENTIAL_ID_VALID",
        "INTEGRITY_VALID",
        "ATTESTATION_VALID",
        "PROVENANCE_VALID",
        "FRESHNESS_VALID",
        "REPLAY_CHECK_VALID",
    }.issubset(result.reason_codes)


# 2. Telemetry modified after signing is rejected
def test_telemetry_modified_after_ecdsa_signing_is_rejected() -> None:
    now = datetime.now(UTC)
    private_key, public_pem = generate_ec_key_pair()
    service = make_service(public_pem)
    packet = make_packet(now=now)

    signature = service.sign_packet_ecdsa(packet, private_key)

    # Tampering with zone_id
    tampered_zone = packet.model_copy(update={"zone_id": "ZONE-02"})
    result_zone = service.assess(tampered_zone, signature, now=now)

    assert result_zone.trust_label is C4TrustLabel.UNTRUSTED
    assert result_zone.mandatory_security_pass is False
    assert result_zone.routing_outcome is C4RoutingOutcome.REJECT
    assert "INTEGRITY_INVALID" in result_zone.reason_codes

    # Tampering with packet_id
    tampered_id = packet.model_copy(update={"packet_id": "packet-tampered-999"})
    result_id = service.assess(tampered_id, signature, now=now)

    assert result_id.trust_label is C4TrustLabel.UNTRUSTED
    assert result_id.mandatory_security_pass is False
    assert result_id.routing_outcome is C4RoutingOutcome.REJECT
    assert "INTEGRITY_INVALID" in result_id.reason_codes


# 3. Signature verified against wrong public key is rejected
def test_signature_verified_against_wrong_public_key_is_rejected() -> None:
    now = datetime.now(UTC)
    private_key_actual, _ = generate_ec_key_pair()
    _, public_pem_unrelated = generate_ec_key_pair()

    service = make_service(public_pem_unrelated)
    packet = make_packet(now=now)

    # Signed with private_key_actual, but service has public_pem_unrelated
    signature = service.sign_packet_ecdsa(packet, private_key_actual)
    result = service.assess(packet, signature, now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert "INTEGRITY_INVALID" in result.reason_codes


# 4. Missing or malformed public-key material cannot result in acceptance
@pytest.mark.parametrize(
    "invalid_public_key",
    [
        None,
        b"",
        "",
        b"not-a-valid-pem-key",
        "-----BEGIN PUBLIC KEY-----\nINVALID_BASE64\n-----END PUBLIC KEY-----",
        generate_rsa_public_key_pem(),
    ],
)
def test_missing_or_malformed_public_key_cannot_result_in_acceptance(
    invalid_public_key: bytes | str | None,
) -> None:
    now = datetime.now(UTC)
    service = make_service(invalid_public_key)
    packet = make_packet(now=now)

    # Even with a well-formed signature from an arbitrary key
    private_key, _ = generate_ec_key_pair()
    signature = service.sign_packet_ecdsa(packet, private_key)

    result = service.assess(packet, signature, now=now)

    assert result.trust_label is C4TrustLabel.UNKNOWN
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW
    assert result.routing_outcome != C4RoutingOutcome.ACCEPT
    assert "SIGNATURE_UNVERIFIABLE" in result.reason_codes


# 5. Malformed signature data is handled safely and does not escape as unhandled exception
@pytest.mark.parametrize(
    "malformed_signature",
    [
        "not-a-hex-signature",
        "0",
        "01",
        "00112233",
        "deadbeef" * 8,
        "ff" * 72,
    ],
)
def test_malformed_signature_data_handled_safely_and_rejected(
    malformed_signature: str,
) -> None:
    now = datetime.now(UTC)
    _, public_pem = generate_ec_key_pair()
    service = make_service(public_pem)
    packet = make_packet(now=now)

    result = service.assess(packet, malformed_signature, now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert "INTEGRITY_INVALID" in result.reason_codes


# 6. ECDSA credentials never silently fall back to HMAC
def test_ecdsa_credentials_never_silently_fall_back_to_hmac() -> None:
    now = datetime.now(UTC)
    _, public_pem = generate_ec_key_pair()
    secret = b"shared-device-secret-12345"

    credential = DeviceCredential(
        credential_id=CREDENTIAL_ID,
        secret=secret,
        signature_algorithm="ecdsa-sha256",
        public_key_pem=public_pem,
    )
    service = C4TrustService(
        {DEVICE_ID: credential},
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )
    packet = make_packet(now=now)

    # Generate HMAC signature using the credential secret
    hmac_sig = service.sign_packet(packet, secret)

    # Verification must fail because ECDSA is configured, never falling back to HMAC
    result = service.assess(packet, hmac_sig, now=now)

    assert result.trust_label is C4TrustLabel.UNTRUSTED
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.REJECT
    assert "INTEGRITY_INVALID" in result.reason_codes

    # When public_key_pem is missing on an ECDSA credential, it must NOT fall back to HMAC
    service_no_pk = C4TrustService(
        {
            DEVICE_ID: DeviceCredential(
                credential_id=CREDENTIAL_ID,
                secret=secret,
                signature_algorithm="ecdsa-sha256",
                public_key_pem=None,
            )
        },
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )
    result_no_pk = service_no_pk.assess(packet, hmac_sig, now=now)

    assert result_no_pk.trust_label is C4TrustLabel.UNKNOWN
    assert result_no_pk.mandatory_security_pass is False
    assert result_no_pk.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW
    assert "SIGNATURE_UNVERIFIABLE" in result_no_pk.reason_codes


# 7. Existing HMAC-SHA256 signing and verification remain compatible
def test_existing_hmac_sha256_signing_and_verification_remain_compatible() -> None:
    now = datetime.now(UTC)
    secret = b"test-hmac-key-material"
    credential = DeviceCredential(
        credential_id=CREDENTIAL_ID,
        secret=secret,
        signature_algorithm="hmac-sha256",
    )
    service = C4TrustService(
        {DEVICE_ID: credential},
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )
    packet = make_packet(now=now)

    # Valid HMAC
    hmac_signature = service.sign_packet(packet, secret)
    result_valid = service.assess(packet, hmac_signature, now=now)

    assert result_valid.trust_label is C4TrustLabel.TRUSTED
    assert result_valid.mandatory_security_pass is True
    assert result_valid.routing_outcome is C4RoutingOutcome.ACCEPT
    assert "INTEGRITY_VALID" in result_valid.reason_codes

    # Tampered HMAC
    tampered_packet = packet.model_copy(update={"zone_id": "ZONE-99"})
    result_tampered = service.assess(tampered_packet, hmac_signature, now=now)

    assert result_tampered.trust_label is C4TrustLabel.UNTRUSTED
    assert result_tampered.mandatory_security_pass is False
    assert result_tampered.routing_outcome is C4RoutingOutcome.REJECT
    assert "INTEGRITY_INVALID" in result_tampered.reason_codes


# 8. ECDSA signature verification works with a fresh key pair generated in the test
def test_ecdsa_signature_verification_works_with_fresh_key_pair() -> None:
    now = datetime.now(UTC)
    fresh_private_key, fresh_public_pem = generate_ec_key_pair()

    registry = DeviceRegistry()
    registry.register(
        device_id="GNX-FRESH-KEY-001",
        device_kind=DeviceKind.TYPE_A,
        zone_id="ZONE-01",
        hub_id="H001",
        credential=DeviceCredential(
            credential_id="cred-fresh-001",
            secret=b"not-used",
            signature_algorithm="ecdsa-sha256",
            public_key_pem=fresh_public_pem,
        ),
    )
    registry.activate("GNX-FRESH-KEY-001")

    service = C4TrustService(
        registry,
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )

    packet = make_packet(
        now=now,
        device_id="GNX-FRESH-KEY-001",
        credential_id="cred-fresh-001",
    )
    signature = service.sign_packet_ecdsa(packet, fresh_private_key)
    result = service.assess(packet, signature, now=now)

    assert result.trust_label is C4TrustLabel.TRUSTED
    assert result.mandatory_security_pass is True
    assert result.routing_outcome is C4RoutingOutcome.ACCEPT
    assert "INTEGRITY_VALID" in result.reason_codes


# 9. Unknown signature algorithm is handled fail-closed
@pytest.mark.parametrize(
    "unknown_algorithm",
    [
        "unknown-algorithm",
        "rsa-pss-sha256",
        "ed25519",
        "sha256",
        "",
    ],
)
def test_unknown_signature_algorithm_is_handled_fail_closed(
    unknown_algorithm: str,
) -> None:
    now = datetime.now(UTC)
    service = make_service(
        public_key_pem=b"some-public-key",
        signature_algorithm=unknown_algorithm,
    )
    packet = make_packet(now=now)

    result = service.assess(packet, "any-signature-string", now=now)

    assert result.trust_label is C4TrustLabel.UNKNOWN
    assert result.mandatory_security_pass is False
    assert result.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW
    assert result.routing_outcome != C4RoutingOutcome.ACCEPT
    assert "SIGNATURE_UNVERIFIABLE" in result.reason_codes


# 10. Mandatory security failures cannot be overridden by high behavioral ML score
def test_mandatory_security_failures_cannot_be_overridden_by_high_ml_score() -> None:
    now = datetime.now(UTC)
    private_key, public_pem = generate_ec_key_pair()
    service = make_service(public_pem)
    packet = make_packet(now=now)

    # Invalid signature with optimal behavioral score (0.0 = completely normal)
    result_invalid_sig = service.assess(
        packet,
        "bad-signature-data",
        now=now,
        behavioural_score=0.0,
    )
    assert result_invalid_sig.trust_label is C4TrustLabel.UNTRUSTED
    assert result_invalid_sig.mandatory_security_pass is False
    assert result_invalid_sig.routing_outcome is C4RoutingOutcome.REJECT
    assert "INTEGRITY_INVALID" in result_invalid_sig.reason_codes

    # Tampered packet with optimal behavioral score
    signature = service.sign_packet_ecdsa(packet, private_key)
    tampered_packet = packet.model_copy(update={"zone_id": "ZONE-99"})
    result_tampered = service.assess(
        tampered_packet,
        signature,
        now=now,
        behavioural_score=0.0,
    )
    assert result_tampered.trust_label is C4TrustLabel.UNTRUSTED
    assert result_tampered.mandatory_security_pass is False
    assert result_tampered.routing_outcome is C4RoutingOutcome.REJECT
    assert "INTEGRITY_INVALID" in result_tampered.reason_codes

    # Missing public key with optimal behavioral score
    service_no_pk = make_service(None)
    result_no_pk = service_no_pk.assess(
        packet,
        signature,
        now=now,
        behavioural_score=0.0,
    )
    assert result_no_pk.trust_label is C4TrustLabel.UNKNOWN
    assert result_no_pk.mandatory_security_pass is False
    assert result_no_pk.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW
    assert "SIGNATURE_UNVERIFIABLE" in result_no_pk.reason_codes


# Additional tests: Hex case insensitivity and DeviceRegistry lifecycle with ECDSA
def test_ecdsa_signature_hex_case_insensitivity() -> None:
    now = datetime.now(UTC)
    private_key, public_pem = generate_ec_key_pair()
    service = make_service(public_pem)
    packet = make_packet(now=now)

    signature = service.sign_packet_ecdsa(packet, private_key)
    upper_signature = signature.upper()

    result = service.assess(packet, upper_signature, now=now)
    assert result.trust_label is C4TrustLabel.TRUSTED
    assert result.mandatory_security_pass is True
    assert "INTEGRITY_VALID" in result.reason_codes


def test_ecdsa_device_registry_lifecycle_enforcement() -> None:
    now = datetime.now(UTC)
    private_key, public_pem = generate_ec_key_pair()

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
            public_key_pem=public_pem,
        ),
    )
    # Device provisioned but not activated yet
    service = C4TrustService(
        registry,
        allow_deterministic_only=True,
        attestation_verifier=lambda p, d: True,
        provenance_verifier=lambda p, d: True,
    )
    packet = make_packet(now=now)
    signature = service.sign_packet_ecdsa(packet, private_key)

    result_provisioned = service.assess(packet, signature, now=now)
    assert result_provisioned.trust_label is C4TrustLabel.UNTRUSTED
    assert "DEVICE_NOT_ACTIVE" in result_provisioned.reason_codes

    # Activate device -> accepted
    registry.activate(DEVICE_ID)
    result_active = service.assess(packet, signature, now=now)
    assert result_active.trust_label is C4TrustLabel.TRUSTED
    assert result_active.routing_outcome is C4RoutingOutcome.ACCEPT

    # Suspend device -> rejected
    registry.suspend(DEVICE_ID)
    result_suspended = service.assess(packet, signature, now=now)
    assert result_suspended.trust_label is C4TrustLabel.UNTRUSTED
    assert "DEVICE_NOT_ACTIVE" in result_suspended.reason_codes
