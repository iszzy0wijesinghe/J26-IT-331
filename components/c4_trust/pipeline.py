from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from components.c4_trust.quarantine import (
    QuarantineManager,
    QuarantineReason,
    QuarantineRecord,
)
from components.c4_trust.service import C4TrustService
from shared.contracts import C4TrustAssessment, TelemetryPacket
from shared.enums import C4RoutingOutcome, C4TrustLabel


@dataclass(frozen=True)
class C4GateResult:
    """Decision and downstream eligibility produced by the C4 boundary."""

    assessment: C4TrustAssessment
    eligible_packet: TelemetryPacket | None
    quarantine_record: QuarantineRecord | None

    @property
    def eligible_for_c1(self) -> bool:
        return self.eligible_packet is not None


class C4TelemetryGate:
    """Apply C4 trust policy before a packet can be handed to C1."""

    def __init__(
        self,
        trust_service: C4TrustService,
        quarantine_manager: QuarantineManager,
    ) -> None:
        self._trust_service = trust_service
        self._quarantine_manager = quarantine_manager

    def process(
        self,
        packet: TelemetryPacket,
        signature: str | None,
        *,
        now: datetime | None = None,
        recovery_request_id: str | None = None,
    ) -> C4GateResult:
        assessment = self._trust_service.assess(
            packet,
            signature,
            now=now,
            recovery_request_id=recovery_request_id,
        )

        if (
            assessment.trust_label is C4TrustLabel.TRUSTED
            and assessment.mandatory_security_pass
            and assessment.routing_outcome is C4RoutingOutcome.ACCEPT
        ):
            return C4GateResult(
                assessment=assessment,
                eligible_packet=packet,
                quarantine_record=None,
            )

        if assessment.trust_label is C4TrustLabel.UNKNOWN:
            quarantine_reason = QuarantineReason.EVIDENCE_UNAVAILABLE
        elif assessment.trust_label is C4TrustLabel.UNTRUSTED:
            quarantine_reason = QuarantineReason.SECURITY_FAILURE
        else:
            quarantine_reason = QuarantineReason.BEHAVIOURAL_ANOMALY

        record = self._quarantine_manager.quarantine(
            packet_id=packet.packet_id,
            device_id=packet.device_id,
            trust_label=assessment.trust_label,
            routing_outcome=assessment.routing_outcome or C4RoutingOutcome.SECURITY_REVIEW,
            reason_codes=assessment.reason_codes,
            quarantine_reason=quarantine_reason,
            packet_data=packet.model_dump(mode="json"),
            assessment=assessment,
            metadata={
                "mandatory_security_pass": assessment.mandatory_security_pass,
                "security_policy_version": assessment.security_policy_version,
            },
        )
        return C4GateResult(
            assessment=assessment,
            eligible_packet=None,
            quarantine_record=record,
        )