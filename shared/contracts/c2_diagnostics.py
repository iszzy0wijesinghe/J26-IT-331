from datetime import datetime

from pydantic import Field, model_validator

from shared.contracts.common import TimeAwareContractModel
from shared.enums import (
    C2Action,
    C2FailureType,
    OperatingMode,
    ProcessingStatus,
    RecoveryProvenance,
    RecoveryStatus,
    SilenceState,
    SourceOrigin,
)


class ExpectedObservation(TimeAwareContractModel):
    """Expected-report schedule derived from the active sampling policy."""

    schema_version: str = Field(min_length=1)

    device_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)

    policy_version: str = Field(min_length=1)
    operating_mode: OperatingMode

    last_accepted_report_at: datetime
    expected_next_report_at: datetime
    deadline_at: datetime

    @model_validator(mode="after")
    def validate_timing_order(self) -> "ExpectedObservation":
        if self.expected_next_report_at < self.last_accepted_report_at:
            raise ValueError(
                "expected_next_report_at cannot be before "
                "last_accepted_report_at"
            )

        if self.deadline_at < self.expected_next_report_at:
            raise ValueError(
                "deadline_at cannot be before expected_next_report_at"
            )

        return self


class SilenceEvent(TimeAwareContractModel):
    """Represents missing/late telemetry relative to active policy."""

    schema_version: str = Field(min_length=1)

    silence_event_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)

    detected_at: datetime
    expected_at: datetime
    deadline_at: datetime

    operating_mode: OperatingMode
    policy_version: str = Field(min_length=1)

    state: SilenceState

    correlation_id: str | None = None
    test_run_id: str | None = None

    @model_validator(mode="after")
    def validate_silence_timing(self) -> "SilenceEvent":
        if self.deadline_at < self.expected_at:
            raise ValueError("deadline_at cannot be before expected_at")

        return self


class C2Diagnosis(TimeAwareContractModel):
    """High-level C2 diagnosis produced for a silence event."""

    schema_version: str = Field(min_length=1)

    diagnosis_id: str = Field(min_length=1)
    silence_event_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)

    failure_type: C2FailureType

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    backup_verification_used: bool

    evidence_codes: list[str] = Field(default_factory=list)

    recommended_action: C2Action

    model_version: str | None = None
    processing_status: ProcessingStatus = ProcessingStatus.OK

    generated_at: datetime

    correlation_id: str | None = None
    test_run_id: str | None = None


class RecoveryEvent(TimeAwareContractModel):
    """Execution record for a C2 recovery action."""

    schema_version: str = Field(min_length=1)

    recovery_event_id: str = Field(min_length=1)
    silence_event_id: str = Field(min_length=1)
    diagnosis_id: str = Field(min_length=1)

    action: C2Action

    started_at: datetime
    completed_at: datetime | None = None

    status: RecoveryStatus

    recovered_count: int = Field(default=0, ge=0)

    correlation_id: str | None = None
    test_run_id: str | None = None

    @model_validator(mode="after")
    def validate_recovery_timing(self) -> "RecoveryEvent":
        if (
            self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValueError(
                "completed_at cannot be before started_at"
            )

        return self


class RecoveredObservation(TimeAwareContractModel):
    """Observation made available through a C2 recovery path.

    observed_at preserves the original measurement time.
    received_at represents when the recovered value reached the system.
    """

    schema_version: str = Field(min_length=1)

    observation_id: str = Field(min_length=1)

    zone_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    sensor_instance_id: str = Field(min_length=1)

    observed_at: datetime
    received_at: datetime

    raw_value: float | int | None = None
    value: float | None = None
    unit: str | None = None
    calibration_version: str | None = None

    recovery_provenance: RecoveryProvenance

    recovery_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    recovery_event_id: str = Field(min_length=1)

    source_origin: SourceOrigin
    original_packet_id: str | None = None
    original_sequence_no: int | None = Field(default=None, ge=0)

    correlation_id: str | None = None
    test_run_id: str | None = None

    @model_validator(mode="after")
    def validate_recovered_observation(self) -> "RecoveredObservation":
        if self.raw_value is None and self.value is None:
            raise ValueError(
                "Recovered observation must contain raw_value, value, or both"
            )

        if self.recovery_provenance is RecoveryProvenance.DIRECT:
            raise ValueError(
                "RecoveredObservation cannot use DIRECT provenance"
            )

        return self