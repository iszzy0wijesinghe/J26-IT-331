from datetime import datetime

from pydantic import Field, model_validator

from shared.contracts.common import TimeAwareContractModel
from shared.enums import (
    C1CredibilityLabel,
    C4TrustLabel,
    RecoveryProvenance,
)


class GoldenObservation(TimeAwareContractModel):
    """Selected downstream environmental representation.

    Golden observations never replace the underlying raw evidence.
    available_at controls runtime as-of eligibility.
    """

    schema_version: str = Field(min_length=1)

    golden_observation_id: str = Field(min_length=1)
    source_observation_id: str = Field(min_length=1)

    zone_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    sensor_instance_id: str = Field(min_length=1)

    observed_at: datetime
    available_at: datetime

    value: float
    unit: str | None = None

    recovery_provenance: RecoveryProvenance

    trust_label: C4TrustLabel
    credibility_label: C1CredibilityLabel

    quality_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    is_estimated: bool

    c4_assessment_id: str = Field(min_length=1)
    c1_assessment_id: str = Field(min_length=1)
    c2_recovery_event_id: str | None = None

    correlation_id: str | None = None
    test_run_id: str | None = None

    @model_validator(mode="after")
    def validate_provenance_consistency(self) -> "GoldenObservation":
        estimated_provenance = {
            RecoveryProvenance.FUSED,
            RecoveryProvenance.DERIVED,
        }

        if (
            self.recovery_provenance in estimated_provenance
            and not self.is_estimated
        ):
            raise ValueError(
                "FUSED or DERIVED Golden observations must be marked "
                "is_estimated=True"
            )

        if (
            self.recovery_provenance is RecoveryProvenance.DIRECT
            and self.c2_recovery_event_id is not None
        ):
            raise ValueError(
                "DIRECT Golden observation cannot reference a C2 recovery event"
            )

        if (
            self.recovery_provenance is not RecoveryProvenance.DIRECT
            and self.c2_recovery_event_id is None
        ):
            raise ValueError(
                "Recovered Golden observation must reference a C2 recovery event"
            )

        return self

    def is_available_as_of(self, as_of_time: datetime) -> bool:
        """Return whether this value was legitimately available at runtime."""

        if as_of_time.tzinfo is None or as_of_time.utcoffset() is None:
            raise ValueError("as_of_time must be timezone-aware")

        return self.available_at <= as_of_time