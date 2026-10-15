from datetime import datetime

from pydantic import Field, model_validator

from shared.contracts.common import TimeAwareContractModel
from shared.enums import (
    AssessmentContext,
    C4RoutingOutcome,
    C4TrustLabel,
    ProcessingStatus,
)


class C4TrustAssessment(TimeAwareContractModel):
    """C4 source/transmission trust assessment for one telemetry packet.

    Mandatory deterministic security checks remain authoritative.
    Behavioural ML cannot override a failed mandatory security check.
    """

    schema_version: str = Field(min_length=1)

    assessment_id: str = Field(min_length=1)
    packet_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)

    trust_label: C4TrustLabel
    trust_score: float | None = Field(default=None, ge=0.0, le=1.0)

    mandatory_security_pass: bool

    reason_codes: list[str] = Field(default_factory=list)

    behavioural_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    routing_outcome: C4RoutingOutcome | None = None

    model_version: str | None = None
    security_policy_version: str | None = None

    processing_status: ProcessingStatus = ProcessingStatus.OK
    assessment_context: AssessmentContext = AssessmentContext.RUNTIME

    generated_at: datetime

    correlation_id: str | None = None
    test_run_id: str | None = None

    @model_validator(mode="after")
    def enforce_mandatory_security_override(self) -> "C4TrustAssessment":
        if not self.mandatory_security_pass and self.trust_label is C4TrustLabel.TRUSTED:
            raise ValueError("A packet cannot be TRUSTED when mandatory security fails")

        return self
