from datetime import datetime

from pydantic import Field, model_validator

from shared.contracts.common import TimeAwareContractModel
from shared.enums import (
    AssessmentContext,
    C1ContextStatus,
    C1CredibilityLabel,
    ProcessingStatus,
)


class C1CredibilityAssessment(TimeAwareContractModel):
    """C1 credibility assessment attached to an existing observation.

    This contract never replaces or mutates the original observation.
    """

    schema_version: str = Field(min_length=1)

    assessment_id: str = Field(min_length=1)
    observation_id: str = Field(min_length=1)

    credibility_label: C1CredibilityLabel

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    class_probabilities: dict[C1CredibilityLabel, float] | None = None

    context_status: C1ContextStatus

    reason_codes: list[str] = Field(default_factory=list)

    model_version: str | None = None

    processing_status: ProcessingStatus = ProcessingStatus.OK
    assessment_context: AssessmentContext = AssessmentContext.RUNTIME

    generated_at: datetime

    correlation_id: str | None = None
    test_run_id: str | None = None

    @model_validator(mode="after")
    def validate_class_probabilities(self) -> "C1CredibilityAssessment":
        probabilities = self.class_probabilities

        if probabilities is None:
            return self

        for probability in probabilities.values():
            if probability < 0.0 or probability > 1.0:
                raise ValueError("C1 class probabilities must be between 0 and 1")

        total = sum(probabilities.values())

        if abs(total - 1.0) > 1e-6:
            raise ValueError("C1 class probabilities must sum to 1.0")

        return self
