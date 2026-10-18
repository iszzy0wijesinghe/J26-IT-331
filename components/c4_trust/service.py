
from __future__ import annotations

import hashlib
import hmac
import json
import math
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from components.c4_trust.certificates import (
    CertificateValidationResult,
    X509CertificateValidator,
    load_certificate,
)
from components.c4_trust.registry import DeviceCredential, DeviceRecord, DeviceRegistry
from shared.contracts import C4TrustAssessment, TelemetryPacket
from shared.enums import C4RoutingOutcome, C4TrustLabel

EvidenceVerifier = Callable[[TelemetryPacket, DeviceRecord | None], bool | None]
BehaviouralScorer = Callable[[TelemetryPacket], float | None]


@dataclass
class RecoveryContext:
    """Context for authorized C2 recovery replay."""

    recovery_request_id: str
    authorized_device_id: str
    authorized_start_time: datetime
    authorized_end_time: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    is_active: bool = True


class C4TrustService:
    def __init__(
        self,
        credentials_or_registry: Mapping[str, DeviceCredential] | DeviceRegistry,
        *,
        max_age_seconds: float = 30.0,
        future_tolerance_seconds: float = 5.0,
        suspicious_score_threshold: float = 0.7,
        attestation_verifier: EvidenceVerifier | None = None,
        provenance_verifier: EvidenceVerifier | None = None,
        behavioural_scorer: BehaviouralScorer | None = None,
        allow_deterministic_only: bool = False,
        require_sequence: bool = True,
        require_firmware_approval: bool = False,
        require_config_approval: bool = False,
        require_certificate: bool = False,
        certificate_validator: X509CertificateValidator | None = None,
        trusted_ca_certificates: Sequence[x509.Certificate | bytes | str] | None = None,
        revoked_certificates: Sequence[int] | set[int] | None = None,
    ) -> None:
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        if future_tolerance_seconds < 0:
            raise ValueError("future_tolerance_seconds cannot be negative")
        if not 0.0 <= suspicious_score_threshold <= 1.0:
            raise ValueError("suspicious_score_threshold must be between 0 and 1")

        if isinstance(credentials_or_registry, DeviceRegistry):
            self._registry = credentials_or_registry
            self._credentials = {}
        else:
            self._registry = None
            self._credentials = dict(credentials_or_registry)

        self._max_age = timedelta(seconds=max_age_seconds)
        self._future_tolerance = timedelta(seconds=future_tolerance_seconds)
        self._suspicious_score_threshold = suspicious_score_threshold
        self._attestation_verifier = attestation_verifier
        self._provenance_verifier = provenance_verifier
        self._behavioural_scorer = behavioural_scorer
        self._allow_deterministic_only = allow_deterministic_only
        self._require_sequence = require_sequence
        self._require_firmware_approval = require_firmware_approval
        self._require_config_approval = require_config_approval
        self._require_certificate = require_certificate
        self._revoked_certificates: set[int] = set(revoked_certificates or ())

        if certificate_validator is not None:
            self._certificate_validator = certificate_validator
        elif trusted_ca_certificates is not None or require_certificate:
            self._certificate_validator = X509CertificateValidator(
                trusted_ca_certificates=trusted_ca_certificates,
                revoked_serial_numbers=self._revoked_certificates,
            )
        else:
            self._certificate_validator = None

        self._seen_packets: set[tuple[str, str]] = set()
        self._last_sequence: dict[tuple[str, str | None], int] = {}
        self._recovery_contexts: dict[str, RecoveryContext] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _canonical_packet(packet: TelemetryPacket) -> bytes:
        payload = packet.model_dump(mode="json")
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    @classmethod
    def sign_packet(
        cls,
        packet: TelemetryPacket,
        secret: bytes,
    ) -> str:
        return hmac.new(
            secret,
            cls._canonical_packet(packet),
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    def sign_packet_ecdsa(
        cls,
        packet: TelemetryPacket,
        private_key: ec.EllipticCurvePrivateKey,
    ) -> str:
        return private_key.sign(
            cls._canonical_packet(packet),
            ec.ECDSA(hashes.SHA256()),
        ).hex()

    def create_recovery_context(
        self,
        recovery_request_id: str,
        authorized_device_id: str,
        authorized_start_time: datetime,
        authorized_end_time: datetime,
    ) -> RecoveryContext:
        for name, value in (
            ("authorized_start_time", authorized_start_time),
            ("authorized_end_time", authorized_end_time),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if authorized_end_time < authorized_start_time:
            raise ValueError("authorized_end_time must not precede authorized_start_time")

        context = RecoveryContext(
            recovery_request_id=recovery_request_id,
            authorized_device_id=authorized_device_id,
            authorized_start_time=authorized_start_time,
            authorized_end_time=authorized_end_time,
        )

        with self._lock:
            self._recovery_contexts[recovery_request_id] = context

        return context

    def revoke_recovery_context(self, recovery_request_id: str) -> bool:
        with self._lock:
            context = self._recovery_contexts.get(recovery_request_id)
            if context is None:
                return False
            context.is_active = False
            return True

    def _check_authorized_replay(
        self,
        packet: TelemetryPacket,
        recovery_request_id: str | None,
    ) -> bool:
        if not recovery_request_id:
            return False

        with self._lock:
            context = self._recovery_contexts.get(recovery_request_id)

        if context is None or not context.is_active:
            return False

        if packet.device_id != context.authorized_device_id:
            return False

        return (
            context.authorized_start_time
            <= packet.observed_at
            <= context.authorized_end_time
        )

    @staticmethod
    def _verify_evidence(
        verifier: EvidenceVerifier | None,
        packet: TelemetryPacket,
        device_record: DeviceRecord | None,
    ) -> bool | None:
        if verifier is None:
            return None
        try:
            return verifier(packet, device_record)
        except Exception:
            return None

    @classmethod
    def attach_certificate(
        cls,
        packet: TelemetryPacket,
        certificate: x509.Certificate | bytes | str,
    ) -> TelemetryPacket:
        """Attach an X.509 certificate to a telemetry packet."""
        if isinstance(certificate, x509.Certificate):
            cert_str = certificate.public_bytes(serialization.Encoding.PEM).decode("utf-8")
        elif isinstance(certificate, bytes):
            cert_str = certificate.decode("utf-8")
        else:
            cert_str = certificate

        return packet.model_copy(
            update={
                "security": packet.security.model_copy(
                    update={"certificate_pem": cert_str}
                )
            }
        )

    @staticmethod
    def _verify_signature(
        packet: TelemetryPacket,
        signature: str,
        credential: DeviceCredential,
        public_key: ec.EllipticCurvePublicKey | None = None,
    ) -> bool | None:
        """Return True for valid signatures, False for invalid ones, or None if unverifiable."""
        algorithm = credential.signature_algorithm

        if algorithm == "hmac-sha256":
            expected = C4TrustService.sign_packet(packet, credential.secret)
            return hmac.compare_digest(expected, signature.lower())

        if algorithm == "ecdsa-sha256":
            if public_key is None:
                if not credential.public_key_pem:
                    return None

                try:
                    pem = credential.public_key_pem
                    if isinstance(pem, str):
                        pem = pem.encode("utf-8")

                    loaded_key = serialization.load_pem_public_key(pem)
                    if not isinstance(loaded_key, ec.EllipticCurvePublicKey):
                        return None
                    public_key = loaded_key
                except Exception:
                    return None

            try:
                signature_bytes = bytes.fromhex(signature)
                public_key.verify(
                    signature_bytes,
                    C4TrustService._canonical_packet(packet),
                    ec.ECDSA(hashes.SHA256()),
                )
                return True
            except InvalidSignature:
                return False
            except (TypeError, ValueError):
                return False

        return None

    def assess(
        self,
        packet: TelemetryPacket,
        signature: str | None,
        *,
        now: datetime | None = None,
        behavioural_score: float | None = None,
        recovery_request_id: str | None = None,
    ) -> C4TrustAssessment:
        assessed_at = now or datetime.now(UTC)

        if assessed_at.tzinfo is None or assessed_at.utcoffset() is None:
            raise ValueError("now must be timezone-aware")

        if behavioural_score is not None:
            try:
                behavioural_score = float(behavioural_score)
            except (TypeError, ValueError) as exc:
                raise ValueError("behavioural_score must be numeric") from exc
            if (
                not math.isfinite(behavioural_score)
                or not 0.0 <= behavioural_score <= 1.0
            ):
                raise ValueError("behavioural_score must be finite and between 0 and 1")

        failures: list[str] = []
        security_unknowns: list[str] = []
        behavioural_unknowns: list[str] = []
        verified: list[str] = []
        device_record: DeviceRecord | None = None
        credential: DeviceCredential | None

        if self._registry is not None:
            device_record = self._registry.get(packet.device_id)
            if device_record is None:
                failures.append("DEVICE_UNKNOWN")
            elif not self._registry.is_active(packet.device_id):
                failures.append("DEVICE_NOT_ACTIVE")

            credential = device_record.credential if device_record else None

            if device_record is not None:
                if packet.zone_id != device_record.zone_id:
                    failures.append("ZONE_MISMATCH")
                else:
                    verified.append("ZONE_VALID")

                if packet.transport.gateway_id is None:
                    security_unknowns.append("HUB_ID_MISSING")
                elif packet.transport.gateway_id != device_record.hub_id:
                    failures.append("HUB_MISMATCH")
                else:
                    verified.append("HUB_VALID")

                if (
                    self._require_firmware_approval
                    and not device_record.approved_firmware
                ):
                    security_unknowns.append("FIRMWARE_APPROVAL_MISSING")
                elif device_record.approved_firmware:
                    if (
                        not device_record.firmware_hash
                        or not packet.security.firmware_hash
                    ):
                        security_unknowns.append("FIRMWARE_EVIDENCE_MISSING")
                    elif device_record.firmware_hash != packet.security.firmware_hash:
                        failures.append("FIRMWARE_UNAPPROVED")
                    else:
                        verified.append("FIRMWARE_VALID")

                if self._require_config_approval and not device_record.approved_config:
                    security_unknowns.append("CONFIG_APPROVAL_MISSING")
                elif device_record.approved_config:
                    if (
                        not device_record.config_hash
                        or not packet.security.config_hash
                    ):
                        security_unknowns.append("CONFIG_EVIDENCE_MISSING")
                    elif device_record.config_hash != packet.security.config_hash:
                        failures.append("CONFIG_MISMATCH")
                    else:
                        verified.append("CONFIG_VALID")
        else:
            credential = self._credentials.get(packet.device_id)
            if credential is None:
                failures.append("DEVICE_UNKNOWN")
            else:
                verified.append("IDENTITY_VALID")

        if device_record is not None and self._registry is not None:
            if credential is None:
                security_unknowns.append("CREDENTIAL_NOT_CONFIGURED")
            else:
                verified.append("IDENTITY_VALID")

        if credential is not None:
            if not packet.security.credential_id:
                security_unknowns.append("CREDENTIAL_ID_MISSING")
            elif not hmac.compare_digest(
                packet.security.credential_id,
                credential.credential_id,
            ):
                failures.append("CREDENTIAL_ID_MISMATCH")
            else:
                verified.append("CREDENTIAL_ID_VALID")

            for name, value in (
                ("CREDENTIAL_ISSUED_AT_INVALID", credential.issued_at),
                ("CREDENTIAL_EXPIRES_AT_INVALID", credential.expires_at),
            ):
                if value is not None and (
                    value.tzinfo is None or value.utcoffset() is None
                ):
                    security_unknowns.append(name)

            if (
                credential.issued_at is not None
                and credential.issued_at.tzinfo is not None
                and credential.issued_at.utcoffset() is not None
                and credential.issued_at > assessed_at
            ):
                failures.append("CREDENTIAL_NOT_YET_VALID")

            if (
                credential.expires_at is not None
                and credential.expires_at.tzinfo is not None
                and credential.expires_at.utcoffset() is not None
                and credential.expires_at <= assessed_at
            ):
                failures.append("CREDENTIAL_EXPIRED")

            if not any(
                reason.startswith("CREDENTIAL_")
                for reason in security_unknowns + failures
            ):
                verified.append("CREDENTIAL_VALID")
        elif self._registry is not None and device_record is None:
            security_unknowns.append("CREDENTIAL_UNAVAILABLE")

        cert_data = packet.security.certificate_pem or (
            credential.certificate_pem if credential else None
        )
        cert_public_key: ec.EllipticCurvePublicKey | None = None

        if (
            packet.security.certificate_pem is not None
            and credential is not None
            and credential.certificate_pem is not None
        ):
            try:
                pkt_cert = load_certificate(packet.security.certificate_pem)
                reg_cert = load_certificate(credential.certificate_pem)
                if pkt_cert.public_bytes(
                    serialization.Encoding.PEM
                ) != reg_cert.public_bytes(serialization.Encoding.PEM):
                    failures.append("CERTIFICATE_CREDENTIAL_MISMATCH")
            except Exception:
                failures.append("CERTIFICATE_CREDENTIAL_MISMATCH")

        if cert_data is not None:
            validator = self._certificate_validator or X509CertificateValidator(
                allow_self_signed=False
            )
            cert_res = validator.validate(
                cert_data,
                expected_device_id=packet.device_id,
                now=assessed_at,
            )
            if (
                cert_res.certificate is not None
                and self._registry is not None
                and self._registry.is_certificate_revoked(
                    cert_res.certificate.serial_number
                )
            ):
                cert_res = CertificateValidationResult(
                    is_valid=False,
                    reason_code="CERTIFICATE_REVOKED",
                    certificate=cert_res.certificate,
                    error_detail="Certificate revoked in registry",
                )

            if cert_res.is_valid:
                verified.append("CERTIFICATE_VALID")
                cert_public_key = cert_res.public_key

                if credential is not None and credential.public_key_pem is not None:
                    try:
                        cred_pem = credential.public_key_pem
                        if isinstance(cred_pem, str):
                            cred_pem = cred_pem.encode("utf-8")
                        cred_key = serialization.load_pem_public_key(cred_pem)
                        if isinstance(cred_key, ec.EllipticCurvePublicKey):
                            if cert_public_key.public_bytes(
                                serialization.Encoding.PEM,
                                serialization.PublicFormat.SubjectPublicKeyInfo,
                            ) != cred_key.public_bytes(
                                serialization.Encoding.PEM,
                                serialization.PublicFormat.SubjectPublicKeyInfo,
                            ):
                                failures.append("CREDENTIAL_KEY_MISMATCH")
                        else:
                            failures.append("CREDENTIAL_KEY_MISMATCH")
                    except Exception:
                        failures.append("CREDENTIAL_KEY_MISMATCH")
            else:
                failures.append(cert_res.reason_code)
        elif self._require_certificate:
            failures.append("CERTIFICATE_MISSING")

        if not signature:
            security_unknowns.append("SIGNATURE_MISSING")
        elif credential is None:
            security_unknowns.append("SIGNATURE_UNVERIFIABLE")
        else:
            signature_result = self._verify_signature(
                packet,
                signature,
                credential,
                public_key=cert_public_key,
            )
            if signature_result is True:
                verified.append("INTEGRITY_VALID")
            elif signature_result is False:
                failures.append("INTEGRITY_INVALID")
            else:
                security_unknowns.append("SIGNATURE_UNVERIFIABLE")

        attestation = self._verify_evidence(
            self._attestation_verifier, packet, device_record
        )
        if attestation is True:
            verified.append("ATTESTATION_VALID")
        elif attestation is False:
            failures.append("ATTESTATION_INVALID")
        else:
            security_unknowns.append("ATTESTATION_UNVERIFIED")

        provenance = self._verify_evidence(
            self._provenance_verifier, packet, device_record
        )
        if provenance is True:
            verified.append("PROVENANCE_VALID")
        elif provenance is False:
            failures.append("PROVENANCE_INVALID")
        else:
            security_unknowns.append("PROVENANCE_UNVERIFIED")

        if packet.observed_at.tzinfo is None or packet.observed_at.utcoffset() is None:
            security_unknowns.append("TIMESTAMP_UNVERIFIABLE")
        elif packet.observed_at > assessed_at + self._future_tolerance:
            failures.append("TIMESTAMP_IN_FUTURE")
        else:
            authorized_replay = self._check_authorized_replay(
                packet, recovery_request_id
            )
            if (
                assessed_at - packet.observed_at > self._max_age
                and not authorized_replay
            ):
                failures.append("FRESHNESS_EXPIRED")
            elif (
                authorized_replay
                and assessed_at - packet.observed_at > self._max_age
            ):
                verified.append("AUTHORIZED_REPLAY_FRESHNESS_EXCEPTION")
            else:
                verified.append("FRESHNESS_VALID")

        packet_key = (packet.device_id, packet.packet_id)
        sequence_key = (packet.device_id, packet.boot_id)
        is_authorized_replay = self._check_authorized_replay(
            packet, recovery_request_id
        )

        if self._require_sequence and (
            packet.boot_id is None or packet.sequence_no is None
        ):
            security_unknowns.append("SEQUENCE_EVIDENCE_MISSING")

        if not failures and not security_unknowns:
            with self._lock:
                if packet_key in self._seen_packets and not is_authorized_replay:
                    failures.append("REPLAY_DETECTED")

                if packet.sequence_no is not None:
                    previous = self._last_sequence.get(sequence_key)
                    if (
                        previous is not None
                        and packet.sequence_no <= previous
                        and not is_authorized_replay
                    ):
                        failures.append("SEQUENCE_REPLAY_DETECTED")

                if not failures and not is_authorized_replay:
                    self._seen_packets.add(packet_key)
                    if packet.sequence_no is not None:
                        self._last_sequence[sequence_key] = packet.sequence_no

                if not failures:
                    verified.append("REPLAY_CHECK_VALID")

        score = behavioural_score
        mandatory_security_pass = not failures and not security_unknowns

        if failures:
            trust_label = C4TrustLabel.UNTRUSTED
            routing_outcome = C4RoutingOutcome.REJECT
            trust_score = 0.0
        elif security_unknowns:
            trust_label = C4TrustLabel.UNKNOWN
            routing_outcome = C4RoutingOutcome.SECURITY_REVIEW
            trust_score = None
        else:
            if score is None and self._behavioural_scorer is not None:
                try:
                    score_value = self._behavioural_scorer(packet)
                    score = None if score_value is None else float(score_value)
                except Exception:
                    behavioural_unknowns.append("BEHAVIOURAL_INFERENCE_FAILED")

            if score is None and not self._allow_deterministic_only:
                behavioural_unknowns.append("BEHAVIOURAL_SCORE_UNAVAILABLE")

            if score is not None and (
                not math.isfinite(score) or not 0.0 <= score <= 1.0
            ):
                behavioural_unknowns.append("BEHAVIOURAL_SCORE_INVALID")
                score = None

            if behavioural_unknowns:
                trust_label = C4TrustLabel.UNKNOWN
                routing_outcome = C4RoutingOutcome.SECURITY_REVIEW
                trust_score = None
            elif score is not None and score >= self._suspicious_score_threshold:
                trust_label = C4TrustLabel.SUSPICIOUS
                routing_outcome = C4RoutingOutcome.QUARANTINE
                trust_score = 1.0 - score
                verified.append("BEHAVIOURAL_ANOMALY")
            else:
                trust_label = C4TrustLabel.TRUSTED
                routing_outcome = C4RoutingOutcome.ACCEPT
                trust_score = 1.0 if score is None else 1.0 - score
                if score is None:
                    verified.append("DETERMINISTIC_ONLY_POLICY")
                else:
                    verified.append("BEHAVIOURAL_NORMAL")

        return C4TrustAssessment(
            schema_version="1.0",
            assessment_id=f"C4A_{uuid4().hex}",
            packet_id=packet.packet_id,
            device_id=packet.device_id,
            trust_label=trust_label,
            trust_score=trust_score,
            mandatory_security_pass=mandatory_security_pass,
            reason_codes=list(
                dict.fromkeys(
                    verified + failures + security_unknowns + behavioural_unknowns
                )
            ),
            behavioural_score=score,
            routing_outcome=routing_outcome,
            model_version="C4_RULE_BASELINE_001",
            security_policy_version="C4_POLICY_1.1",
            generated_at=assessed_at,
            correlation_id=packet.correlation_id,
            test_run_id=packet.test_run_id,
        )
