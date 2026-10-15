from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from shared.enums import ProcessingStatus


class ContractModel(BaseModel):
    """Base class for GeoNex shared integration contracts."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,
    )


class TimeAwareContractModel(ContractModel):
    """Base for contracts containing timestamps.

    Shared integration timestamps must be timezone-aware.
    """

    @field_validator("*", mode="after")
    @classmethod
    def validate_datetime_timezone(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("GeoNex shared timestamps must be timezone-aware")
        return value


class EventSource(ContractModel):
    """Identifies the software source of a shared event."""

    service: str = Field(min_length=1)
    component: str | None = None


class EventEnvelope(TimeAwareContractModel):
    """Software-facing event envelope.

    Database rows do not have to physically use this wrapper.
    """

    schema_version: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    generated_at: datetime
    source: EventSource
    correlation_id: str | None = None
    payload: dict[str, Any]


class ProcessingError(TimeAwareContractModel):
    """Explicit component/service processing failure."""

    status: ProcessingStatus
    error_code: str = Field(min_length=1)
    retryable: bool
    correlation_id: str | None = None
    generated_at: datetime

    @field_validator("status")
    @classmethod
    def status_must_represent_failure(
        cls,
        value: ProcessingStatus,
    ) -> ProcessingStatus:
        invalid_values = {
            ProcessingStatus.OK,
            ProcessingStatus.PARTIAL,
        }

        if value in invalid_values:
            raise ValueError("ProcessingError status cannot be OK or PARTIAL")

        return value
