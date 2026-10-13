
from __future__ import annotations

import hashlib
import hmac
import json
import threading
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from components.c4_trust.registry import DeviceCredential, DeviceRegistry
from shared.contracts import C4TrustAssessment, TelemetryPacket
from shared.enums import C4RoutingOutcome, C4TrustLabel


class C4TrustService:
    def __init__(
        self,
        credentials_or_registry: Mapping[str, DeviceCredential] | DeviceRegistry,
        *,
        max_age_seconds: float = 30.0,
        future_tolerance_seconds: float = 5.0,
        suspicious_score_threshold: float = 0.7,
    ) -> None:
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        if future_tolerance_seconds < 0:
            raise ValueError("future_tolerance_seconds cannot be negative")
        if not 0.0 <= suspicious_score_threshold <= 1.0:
            raise ValueError("suspicious_score_threshold must be between 0 and 1")

        # Support both legacy credentials mapping and new DeviceRegistry
        if isinstance(credentials_or_registry, DeviceRegistry):
            self._registry = credentials_or_registry
            self._credentials = {}
        else:
            self._registry = None
            self._credentials = dict(credentials_or_registry)

        self._max_age = timedelta(seconds=max_age_seconds)
        self._future_tolerance = timedelta(seconds=future_tolerance_seconds)
        self._suspicious_score_threshold = suspicious_score_threshold
        self._seen_packets: set[tuple[str, str]] = set()
        self._last_sequence: dict[tuple[str, str | None], int] = {}
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

    def assess(
        self,
        packet: TelemetryPacket,
        signature: str | None,
        *,
        now: datetime | None = None,
        behavioural_score: float | None = None,
    ) -> C4TrustAssessment:
        assessed_at = now or datetime.now(UTC)

        if assessed_at.tzinfo is None or assessed_at.utcoffset() is None:
            raise ValueError("now must be timezone-aware")

        if behavioural_score is not None and not (
            0.0 <= behavioural_score <= 1.0
        ):
            raise ValueError("behavioural_score must be between 0 and 1")

        reasons: list[str] = []

        # Get credential from registry or legacy credentials mapping
        if self._registry is not None:
            device_record = self._registry.get(packet.device_id)
            if device_record is None:
                reasons.append("DEVICE_UNKNOWN")
            elif not self._registry.is_active(packet.device_id):
                reasons.append("DEVICE_NOT_ACTIVE")
            credential = device_record.credential if device_record else None
        else:
            credential = self._credentials.get(packet.device_id)
            if credential is None:
                reasons.append("DEVICE_UNKNOWN")

        if credential is None:
            # Already added DEVICE_UNKNOWN or DEVICE_NOT_ACTIVE above
            pass
        elif not packet.security.credential_id:
            reasons.append("CREDENTIAL_ID_MISSING")
        elif not hmac.compare_digest(
            packet.security.credential_id,
            credential.credential_id,
        ):
            reasons.append("CREDENTIAL_ID_MISMATCH")

        if not signature:
            reasons.append("SIGNATURE_MISSING")
        elif credential is not None:
            expected = self.sign_packet(packet, credential.secret)
            if not hmac.compare_digest(expected, signature.lower()):
                reasons.append("INTEGRITY_INVALID")

        if packet.observed_at > assessed_at + self._future_tolerance:
            reasons.append("TIMESTAMP_IN_FUTURE")
        elif assessed_at - packet.observed_at > self._max_age:
            reasons.append("FRESHNESS_EXPIRED")

        packet_key = (packet.device_id, packet.packet_id)
        sequence_key = (packet.device_id, packet.boot_id)

        with self._lock:
            if packet_key in self._seen_packets:
                reasons.append("REPLAY_DETECTED")

            if packet.sequence_no is not None:
                previous = self._last_sequence.get(sequence_key)
                if previous is not None and packet.sequence_no <= previous:
                    reasons.append("SEQUENCE_REPLAY_DETECTED")

            reasons = list(dict.fromkeys(reasons))
            mandatory_pass = not reasons

            if mandatory_pass:
                self._seen_packets.add(packet_key)
                if packet.sequence_no is not None:
                    self._last_sequence[sequence_key] = packet.sequence_no

        if not mandatory_pass:
            trust_label = C4TrustLabel.UNTRUSTED
            routing_outcome = C4RoutingOutcome.REJECT
            trust_score = 0.0
        elif (
            behavioural_score is not None
            and behavioural_score >= self._suspicious_score_threshold
        ):
            trust_label = C4TrustLabel.SUSPICIOUS
            routing_outcome = C4RoutingOutcome.QUARANTINE
            trust_score = 1.0 - behavioural_score
            reasons.append("BEHAVIOURAL_ANOMALY")
        else:
            trust_label = C4TrustLabel.TRUSTED
            routing_outcome = C4RoutingOutcome.ACCEPT
            trust_score = 1.0

        if mandatory_pass:
            reasons = (
                reasons
                if "BEHAVIOURAL_ANOMALY" in reasons
                else [
                    "IDENTITY_VALID",
                    "INTEGRITY_VALID",
                    "FRESHNESS_VALID",
                    "REPLAY_CHECK_VALID",
                ]
            )

        return C4TrustAssessment(
            schema_version="1.0",
            assessment_id=f"C4A_{uuid4().hex}",
            packet_id=packet.packet_id,
            device_id=packet.device_id,
            trust_label=trust_label,
            trust_score=trust_score,
            mandatory_security_pass=mandatory_pass,
            reason_codes=reasons,
            behavioural_score=behavioural_score,
            routing_outcome=routing_outcome,
            model_version="C4_RULE_BASELINE_001",
            security_policy_version="C4_POLICY_1.1",
            generated_at=assessed_at,
            correlation_id=packet.correlation_id,
            test_run_id=packet.test_run_id,
        )