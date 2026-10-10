from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from shared.contracts.common import TimeAwareContractModel
from shared.enums import (
    DataQualityStatus,
    OperatingMode,
    ProcessingStatus,
)


class C3TemporalStep(TimeAwareContractModel):
    """One temporal step in a C3 runtime feature sequence.

    Feature names and exact contents are controlled by the referenced
    feature_schema_version rather than frozen in this integration contract.
    """

    time: datetime

    delta_t_seconds: float = Field(ge=0.0)

    operating_mode: OperatingMode

    features: dict[str, float | int | None] = Field(default_factory=dict)

    masks: dict[str, bool] = Field(default_factory=dict)

    ages_seconds: dict[str, float | None] = Field(default_factory=dict)

    quality: dict[str, Any] = Field(default_factory=dict)

    provenance: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_feature_metadata(self) -> "C3TemporalStep":
        feature_names = set(self.features)

        unknown_masks = set(self.masks) - feature_names
        if unknown_masks:
            raise ValueError(
                "C3 masks contain fields not present in features: "
                f"{sorted(unknown_masks)}"
            )

        unknown_ages = set(self.ages_seconds) - feature_names
        if unknown_ages:
            raise ValueError(
                "C3 ages_seconds contain fields not present in features: "
                f"{sorted(unknown_ages)}"
            )

        for feature_name, age in self.ages_seconds.items():
            if age is not None and age < 0:
                raise ValueError(
                    f"Age for feature {feature_name!r} cannot be negative"
                )

        return self


class C3TemporalSequence(TimeAwareContractModel):
    """Versioned temporal input prepared for C3 inference."""

    schema_version: str = Field(min_length=1)

    zone_id: str = Field(min_length=1)

    forecast_origin: datetime

    feature_schema_version: str = Field(min_length=1)
    builder_version: str = Field(min_length=1)

    steps: list[C3TemporalStep] = Field(min_length=1)

    correlation_id: str | None = None
    test_run_id: str | None = None

    @model_validator(mode="after")
    def validate_sequence_as_of_rule(self) -> "C3TemporalSequence":
        previous_time: datetime | None = None

        for step in self.steps:
            if step.time > self.forecast_origin:
                raise ValueError(
                    "C3 temporal sequence cannot contain a step after "
                    "forecast_origin"
                )

            if previous_time is not None and step.time < previous_time:
                raise ValueError(
                    "C3 temporal steps must be ordered chronologically"
                )

            previous_time = step.time

        return self


class ForecastInputManifest(TimeAwareContractModel):
    """Traceability record for the data used to build one forecast."""

    schema_version: str = Field(min_length=1)

    input_manifest_id: str = Field(min_length=1)
    forecast_id: str = Field(min_length=1)

    zone_id: str = Field(min_length=1)

    forecast_origin: datetime

    feature_schema_version: str = Field(min_length=1)
    builder_version: str = Field(min_length=1)

    golden_observation_ids: list[str] = Field(default_factory=list)

    mode_history: list[OperatingMode] = Field(default_factory=list)

    quality_summary: dict[str, Any] = Field(default_factory=dict)
    provenance_summary: dict[str, Any] = Field(default_factory=dict)

    generated_at: datetime

    correlation_id: str | None = None
    test_run_id: str | None = None


class C3Forecast(TimeAwareContractModel):
    """Near-future risk forecast produced by C3.

    This object intentionally does not contain a requested operating mode
    or device command. Mode/action policy belongs to the Decision Engine.
    """

    schema_version: str = Field(min_length=1)

    forecast_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)

    forecast_origin: datetime

    history_start: datetime
    history_end: datetime

    horizon_minutes: int = Field(gt=0)

    risk_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    # Deliberately a string in Integration Baseline v1 because the final
    # risk-class taxonomy/thresholds are not frozen by Document 11.
    risk_class: str | None = None

    input_quality_status: DataQualityStatus

    processing_status: ProcessingStatus = ProcessingStatus.OK

    model_version: str | None = None
    feature_schema_version: str = Field(min_length=1)
    input_manifest_id: str = Field(min_length=1)

    generated_at: datetime

    correlation_id: str | None = None
    test_run_id: str | None = None

    @model_validator(mode="after")
    def validate_forecast(self) -> "C3Forecast":
        if self.history_start > self.history_end:
            raise ValueError(
                "history_start cannot be after history_end"
            )

        if self.history_end > self.forecast_origin:
            raise ValueError(
                "history_end cannot be after forecast_origin"
            )

        successful_statuses = {
            ProcessingStatus.OK,
            ProcessingStatus.PARTIAL,
        }

        if self.processing_status in successful_statuses:
            if self.risk_probability is None:
                raise ValueError(
                    "Successful C3 forecast requires risk_probability"
                )

            if self.model_version is None:
                raise ValueError(
                    "Successful C3 forecast requires model_version"
                )

        else:
            if self.risk_probability is not None:
                raise ValueError(
                    "Failed/unavailable C3 forecast must not fabricate "
                    "risk_probability"
                )

            if self.risk_class is not None:
                raise ValueError(
                    "Failed/unavailable C3 forecast must not fabricate "
                    "risk_class"
                )

        return self