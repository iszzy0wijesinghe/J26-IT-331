from datetime import datetime

from pydantic import Field, model_validator

from shared.contracts.common import TimeAwareContractModel
from shared.enums import CommandStatus, CommandType, OperatingMode


class DeviceCommand(TimeAwareContractModel):
    """Versioned command issued to a GeoNex device."""

    schema_version: str = Field(min_length=1)

    command_id: str = Field(min_length=1)

    target_device_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)

    command_type: CommandType

    requested_mode: OperatingMode | None = None

    policy_version: str | None = None

    issued_at: datetime
    expires_at: datetime

    decision_id: str | None = None

    correlation_id: str | None = None
    test_run_id: str | None = None

    @model_validator(mode="after")
    def validate_command(self) -> "DeviceCommand":
        if self.expires_at <= self.issued_at:
            raise ValueError(
                "expires_at must be after issued_at"
            )

        if (
            self.command_type is CommandType.APPLY_MODE
            and self.requested_mode is None
        ):
            raise ValueError(
                "APPLY_MODE command requires requested_mode"
            )

        if (
            self.command_type is not CommandType.APPLY_MODE
            and self.requested_mode is not None
        ):
            raise ValueError(
                "requested_mode is only valid for APPLY_MODE commands"
            )

        return self


class CommandAcknowledgement(TimeAwareContractModel):
    """Device acknowledgement for a previously issued command."""

    schema_version: str = Field(min_length=1)

    command_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)

    received_at: datetime
    applied_at: datetime | None = None

    status: CommandStatus

    active_mode: OperatingMode | None = None
    active_policy_version: str | None = None

    reason_code: str | None = None

    correlation_id: str | None = None
    test_run_id: str | None = None

    @model_validator(mode="after")
    def validate_acknowledgement(self) -> "CommandAcknowledgement":
        if (
            self.applied_at is not None
            and self.applied_at < self.received_at
        ):
            raise ValueError(
                "applied_at cannot be before received_at"
            )

        if (
            self.status is CommandStatus.APPLIED
            and self.applied_at is None
        ):
            raise ValueError(
                "APPLIED acknowledgement requires applied_at"
            )

        return self