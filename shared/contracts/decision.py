from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from shared.contracts.common import TimeAwareContractModel
from shared.enums import DecisionType, OperatingMode


class Decision(TimeAwareContractModel):
    """Auditable operational decision produced by the Decision Engine.

    Predictive components such as C3 do not own mode transitions.
    """

    schema_version: str = Field(min_length=1)

    decision_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)

    decision_type: DecisionType

    previous_mode: OperatingMode
    selected_mode: OperatingMode

    forecast_id: str | None = None

    policy_version: str = Field(min_length=1)

    reason_codes: list[str] = Field(default_factory=list)

    generated_at: datetime

    correlation_id: str | None = None
    test_run_id: str | None = None

    @model_validator(mode="after")
    def validate_decision_semantics(self) -> "Decision":
        if (
            self.decision_type is DecisionType.MODE_CHANGE
            and self.previous_mode is self.selected_mode
        ):
            raise ValueError(
                "MODE_CHANGE decision requires different previous "
                "and selected modes"
            )

        if (
            self.decision_type is DecisionType.MAINTAIN_MODE
            and self.previous_mode is not self.selected_mode
        ):
            raise ValueError(
                "MAINTAIN_MODE decision requires identical previous "
                "and selected modes"
            )

        return self


class ModeEvent(TimeAwareContractModel):
    """Recorded transition between GeoNex operating modes."""

    schema_version: str = Field(min_length=1)

    mode_event_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)

    previous_mode: OperatingMode
    new_mode: OperatingMode

    effective_at: datetime

    decision_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)

    reason_codes: list[str] = Field(default_factory=list)

    correlation_id: str | None = None
    test_run_id: str | None = None


class SamplingPolicy(TimeAwareContractModel):
    """Versioned mode-specific sensing/reporting policy.

    Exact sampling rates remain configurable and are intentionally not
    frozen by the integration contract.
    """

    schema_version: str = Field(min_length=1)

    policy_version: str = Field(min_length=1)

    mode: OperatingMode

    device_profile: str = Field(min_length=1)

    acquisition_profile: dict[str, Any] = Field(default_factory=dict)
    aggregation_profile: dict[str, Any] = Field(default_factory=dict)

    report_interval_seconds: float | None = Field(
        default=None,
        gt=0.0,
    )