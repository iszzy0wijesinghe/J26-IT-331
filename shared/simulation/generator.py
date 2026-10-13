
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
    """Generate reproducible synthetic baseline telemetry.

    This is an engineering fixture, not calibrated physical telemetry
    or a replacement for the C4 behavioral training dataset.
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
        observed_at = config.start_time + timedelta(
            seconds=index * interval_seconds
        )
        received_at = observed_at + timedelta(seconds=2)

        soil_moisture = round(35.0 + rng.uniform(-2.0, 2.0), 3)
        temperature = round(27.0 + rng.uniform(-1.5, 1.5), 3)
        pressure = round(1013.0 + rng.uniform(-3.0, 3.0), 3)

        rssi_dbm = round(-75.0 + rng.uniform(-8.0, 8.0), 2)
        snr_db = round(7.0 + rng.uniform(-3.0, 3.0), 2)
        retry_count = rng.randint(0, 2)

        # Calculate freshness status based on receive delay
        receive_delay = (received_at - observed_at).total_seconds()
        if receive_delay <= 5:
            freshness_status = "fresh"
        elif receive_delay <= 30:
            freshness_status = "delayed"
        else:
            freshness_status = "stale"

        # Generate device health metrics
        battery_pct = round(80.0 + rng.uniform(-10.0, 10.0), 2)
        battery_voltage = round(12.0 + rng.uniform(-0.5, 0.5), 3)
        supply_current = round(120.0 + rng.uniform(-20.0, 20.0), 2)
        reboot_count = rng.randint(0, 3)
        sensor_fault = rng.random() < 0.05  # 5% chance of sensor fault

        packet = TelemetryPacket(
            schema_version="1.0",
            packet_id=(
                f"SIM_{config.seed}_{config.zone_id}_"
                f"{config.device_id}_{index:06d}"
            ),
            device_id=config.device_id,
            zone_id=config.zone_id,
            boot_id=f"SIM_BOOT_{config.seed}",
            sequence_no=index,
            observed_at=observed_at,
            received_at=received_at,
            message_type="TELEMETRY",
            tx_interval_s=float(interval_seconds),
            freshness_status=freshness_status,
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
            device_health={
                "battery_voltage": battery_voltage,
                "supply_current": supply_current,
                "restart_count": reboot_count,
                "battery_pct": battery_pct,
                "reboot_count_24h": reboot_count,
                "sensor_fault_flag": sensor_fault,
            },
            transport={
                "rssi_dbm": rssi_dbm,
                "snr_db": snr_db,
                "retry_count": retry_count,
            },
            source_origin=SourceOrigin.SIMULATED,
            test_run_id=f"SIM_RUN_{config.seed}",
            correlation_id=f"SIM_CORR_{config.seed}_{index:06d}",
        )

        packets.append(packet)

    return packets