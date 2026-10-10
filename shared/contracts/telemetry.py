from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from shared.contracts.common import TimeAwareContractModel
from shared.enums import SourceOrigin


class MeasurementEntry(TimeAwareContractModel):
    """One measurement contained inside a telemetry packet.

    Sensor type remains a controlled string for now because the final
    sensor registry is explicitly deferred by Integration Contract v1.
    """

    sensor_instance_id: str = Field(min_length=1)
    sensor_type: str = Field(min_length=1)
    channel: str | None = None

    raw_value: float | int | None = None
    value: float | None = None
    unit: str | None = None

    calibration_version: str | None = None

    @model_validator(mode="after")
    def require_measurement_value(self) -> "MeasurementEntry":
        if self.raw_value is None and self.value is None:
            raise ValueError(
                "A measurement must contain raw_value, value, or both"
            )

        return self


class DeviceHealth(TimeAwareContractModel):
    """Device/system-health metadata carried with telemetry.

    This is intentionally separate from environmental measurements.
    """

    battery_voltage: float | None = None
    supply_current: float | None = None
    restart_count: int | None = Field(default=None, ge=0)
    sensor_read_error: bool | None = None
    sd_status: str | None = None

    extra_metrics: dict[str, Any] = Field(default_factory=dict)


class TransportMetadata(TimeAwareContractModel):
    """Transport/network metadata associated with a packet."""

    rssi_dbm: float | None = None
    snr_db: float | None = None
    retry_count: int | None = Field(default=None, ge=0)
    gateway_id: str | None = None

    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityMetadata(TimeAwareContractModel):
    """Non-secret security metadata associated with telemetry.

    Secret keys, passwords, tokens and raw credentials must never be
    placed in this contract.
    """

    credential_id: str | None = None
    integrity_present: bool | None = None
    freshness_counter: int | None = Field(default=None, ge=0)
    session_id: str | None = None

    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class TelemetryPacket(TimeAwareContractModel):
    """Normalized gateway-to-ingestion telemetry packet."""

    schema_version: str = Field(min_length=1)

    packet_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)

    boot_id: str | None = None
    sequence_no: int | None = Field(default=None, ge=0)

    observed_at: datetime
    received_at: datetime

    message_type: str = Field(default="TELEMETRY", min_length=1)

    measurements: list[MeasurementEntry] = Field(default_factory=list)

    device_health: DeviceHealth = Field(default_factory=DeviceHealth)
    transport: TransportMetadata = Field(default_factory=TransportMetadata)
    security: SecurityMetadata = Field(default_factory=SecurityMetadata)

    source_origin: SourceOrigin
    test_run_id: str | None = None

    correlation_id: str | None = None


class SensorObservation(TimeAwareContractModel):
    """Normalized observation extracted from a telemetry packet.

    One telemetry packet may produce multiple SensorObservation objects.
    """

    schema_version: str = Field(min_length=1)

    observation_id: str = Field(min_length=1)
    packet_id: str = Field(min_length=1)

    zone_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    sensor_instance_id: str = Field(min_length=1)

    observed_at: datetime
    received_at: datetime

    raw_value: float | int | None = None
    value: float | None = None
    unit: str | None = None

    calibration_version: str | None = None

    source_origin: SourceOrigin
    test_run_id: str | None = None

    correlation_id: str | None = None

    @model_validator(mode="after")
    def require_observation_value(self) -> "SensorObservation":
        if self.raw_value is None and self.value is None:
            raise ValueError(
                "An observation must contain raw_value, value, or both"
            )

        return self