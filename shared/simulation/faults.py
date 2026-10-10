"""Fault scenario definitions for GeoNex telemetry simulation."""

from dataclasses import dataclass
from enum import StrEnum


class FaultType(StrEnum):
    """Supported simulated telemetry fault categories."""

    PACKET_DROP = "PACKET_DROP"
    DELIVERY_DELAY = "DELIVERY_DELAY"
    SENSOR_SPIKE = "SENSOR_SPIKE"
    SENSOR_DRIFT = "SENSOR_DRIFT"
    SEQUENCE_ANOMALY = "SEQUENCE_ANOMALY"


@dataclass(frozen=True)
class FaultScenario:
    """A deterministic fault targeting a specific device and sample."""

    fault_type: FaultType
    device_id: str
    start_sequence: int
    end_sequence: int

    sensor_instance_id: str | None = None
    magnitude: float | None = None
    delay_seconds: float | None = None

    def __post_init__(self) -> None:
        if not self.device_id:
            raise ValueError("device_id must not be empty")

        if self.start_sequence < 0:
            raise ValueError("start_sequence must not be negative")

        if self.end_sequence < self.start_sequence:
            raise ValueError(
                "end_sequence must be greater than or equal to start_sequence"
            )

        if self.fault_type in {
            FaultType.SENSOR_SPIKE,
            FaultType.SENSOR_DRIFT,
        }:
            if not self.sensor_instance_id:
                raise ValueError(
                    "Sensor faults require sensor_instance_id"
                )

            if self.magnitude is None:
                raise ValueError(
                    "Sensor faults require magnitude"
                )

        if self.fault_type == FaultType.DELIVERY_DELAY:
            if self.delay_seconds is None or self.delay_seconds < 0:
                raise ValueError(
                    "Delivery delays require nonnegative delay_seconds"
                )