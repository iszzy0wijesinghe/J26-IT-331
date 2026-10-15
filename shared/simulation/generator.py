"""Deterministic baseline telemetry generation for GeoNex."""

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from shared.contracts.telemetry import TelemetryPacket
from shared.enums.domain import OperatingMode, SourceOrigin


@dataclass(frozen=True)
class SimulationConfig:
    """Configuration for a reproducible simulation run."""

    seed: int = 42
    zone_id: str = "ZONE_01"
    device_id: str = "PIPE_A1"
    start_time: datetime = datetime(2026, 10, 10, 0, 0, tzinfo=UTC)
    packet_count: int = 10
    operating_mode: OperatingMode = OperatingMode.IDLE


MODE_INTERVALS_SECONDS = {
    OperatingMode.DEEP_SLEEP: 900,
    OperatingMode.IDLE: 300,
    OperatingMode.RISK: 60,
    OperatingMode.WARNING: 15,
    OperatingMode.EMERGENCY: 5,
}


def generate_baseline_packets(
    config: SimulationConfig,
) -> list[TelemetryPacket]:
    """Generate repeatable baseline telemetry packets.

    This is a synthetic engineering fixture, not a calibrated
    physical landslide simulation or research dataset.
    """

    if config.start_time.utcoffset() is None:
        raise ValueError("start_time must be timezone-aware")

    if config.packet_count < 0:
        raise ValueError("packet_count must not be negative")

    if not config.zone_id or not config.device_id:
        raise ValueError("zone_id and device_id must not be empty")

    rng = random.Random(config.seed)

    interval_seconds = MODE_INTERVALS_SECONDS[config.operating_mode]

    packets: list[TelemetryPacket] = []

    for index in range(config.packet_count):
        observed_at = config.start_time + timedelta(seconds=index * interval_seconds)

        received_at = observed_at + timedelta(seconds=2)

        soil_moisture = round(35.0 + rng.uniform(-2.0, 2.0), 3)
        temperature = round(27.0 + rng.uniform(-1.5, 1.5), 3)
        pressure = round(1013.0 + rng.uniform(-3.0, 3.0), 3)

        packet = TelemetryPacket(
            schema_version="1.0",
            packet_id=(f"SIM_{config.seed}_{config.zone_id}_{config.device_id}_{index:06d}"),
            device_id=config.device_id,
            zone_id=config.zone_id,
            boot_id=f"SIM_BOOT_{config.seed}",
            sequence_no=index,
            observed_at=observed_at,
            received_at=received_at,
            message_type="TELEMETRY",
            measurements=[
                {
                    "sensor_instance_id": f"{config.device_id}_SOIL_01",
                    "sensor_type": "SOIL_MOISTURE",
                    "value": soil_moisture,
                    "unit": "%",
                },
                {
                    "sensor_instance_id": f"{config.device_id}_TEMP_01",
                    "sensor_type": "TEMPERATURE",
                    "value": temperature,
                    "unit": "C",
                },
                {
                    "sensor_instance_id": f"{config.device_id}_PRESSURE_01",
                    "sensor_type": "ATMOSPHERIC_PRESSURE",
                    "value": pressure,
                    "unit": "hPa",
                },
            ],
            source_origin=SourceOrigin.SIMULATED,
            test_run_id=f"SIM_RUN_{config.seed}",
            correlation_id=f"SIM_CORR_{config.seed}_{index:06d}",
        )

        packets.append(packet)

    return packets
