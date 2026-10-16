"""One-zone, hardware-aligned GeoNex telemetry *simulation* for PP1.

This is NOT firmware data, calibrated field telemetry, or landslide ground truth.
Device profiles reflect an engineering demonstration, not verified installation.
"""

import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Literal

from shared.contracts.telemetry import TelemetryPacket
from shared.enums.domain import OperatingMode, SourceOrigin
from shared.simulation.mode_schedule import ModeSegment, generate_mode_schedule
from shared.simulation.scheduled_telemetry import ScheduledTelemetry

Scenario = Literal["stable", "gradual_wetting", "rapid_wetting_tilt"]

DEVICE_IDS = ("PIPE_A1", "PIPE_B1", "PIPE_BK1", "HUB_01")
GATEWAY_ID = "BLACK_BOX_01"


@dataclass(frozen=True)
class DemoNetworkConfig:
    seed: int = 42
    scenario: Scenario = "gradual_wetting"
    start_time: datetime = datetime(2026, 10, 16, 0, 0, tzinfo=UTC)
    zone_id: str = "ZONE_01"
    segments: tuple[ModeSegment, ...] = (
        ModeSegment(OperatingMode.DEEP_SLEEP, 8),
        ModeSegment(OperatingMode.IDLE, 8),
        ModeSegment(OperatingMode.RISK, 8),
        ModeSegment(OperatingMode.WARNING, 8),
        ModeSegment(OperatingMode.EMERGENCY, 8),
    )


def _device_seed(seed: int, device_id: str) -> int:
    digest = sha256(f"{seed}:{device_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _scenario_state(scenario: Scenario, fraction: float) -> tuple[float, float, float]:
    """Latent simulation state: moisture %, tilt degrees, rainfall-proxy counts.

    This generates correlated scenarios but does NOT encode landslide events.
    """
    if scenario == "stable":
        return 35.0, 0.8, 0.0
    if scenario == "gradual_wetting":
        return 35.0 + 28.0 * fraction, 0.8 + 1.5 * fraction, 2.0 + 8.0 * fraction
    if scenario == "rapid_wetting_tilt":
        return 35.0 + 48.0 * fraction**1.5, 0.8 + 8.0 * fraction**2, 5.0 + 22.0 * fraction
    raise ValueError(f"Unknown scenario: {scenario}")


def _measurement(sensor_id: str, sensor_type: str, value: float, unit: str,
                 channel: str) -> dict[str, object]:
    return {
        "sensor_instance_id": sensor_id,
        "sensor_type": sensor_type,
        "channel": channel,
        "value": round(value, 4),
        "unit": unit,
        "calibration_version": "SIMULATED_ONLY_V1",
    }


def _readings(
    device_id: str,
    moisture_pct: float,
    tilt_deg: float,
    rain_proxy: float,
    rng: random.Random,
) -> list[dict[str, object]]:
    def soil(channel: int, offset: float) -> dict[str, object]:
        value = max(0.0, min(100.0, moisture_pct + offset + rng.gauss(0, 0.5)))
        return _measurement(
            f"{device_id}_SOIL_{channel:02d}", "SOIL_MOISTURE", value, "%", f"CH{channel}"
        )

    def fsr(channel: int) -> dict[str, object]:
        # Engineering raw ADC counts: not a calibrated force or pressure.
        return {
            "sensor_instance_id": f"{device_id}_FSR_{channel:02d}",
            "sensor_type": "FSR402_RAW_ADC",
            "channel": f"CH{channel}",
            "raw_value": max(0, min(4095, round(850 + 15 * tilt_deg + rng.gauss(0, 16)))),
            "unit": "adc_count",
        }

    def imu() -> list[dict[str, object]]:
        theta = math.radians(tilt_deg + rng.gauss(0, 0.08))
        readings = (math.sin(theta), rng.gauss(0, 0.01), math.cos(theta))
        return [
            _measurement(f"{device_id}_IMU_{axis}", f"MPU9250_ACCEL_{axis}",
                         reading, "g", axis)
            for axis, reading in zip(("X", "Y", "Z"), readings, strict=True)
        ]

    if device_id == "PIPE_A1":
        return [
            soil(1, 0.0), soil(2, 0.7), fsr(1), fsr(2), *imu(),
            _measurement(
                f"{device_id}_DHT_T", "DHT22_TEMPERATURE",
                27 + rng.gauss(0, 0.4), "C", "T"
            ),
            _measurement(
                f"{device_id}_DHT_RH", "DHT22_HUMIDITY",
                70 + rng.gauss(0, 1), "%", "RH"
            ),
            _measurement(
                f"{device_id}_DS18", "DS18B20_TEMPERATURE",
                26 + rng.gauss(0, 0.3), "C", "T"
            ),
        ]
    if device_id == "PIPE_B1":
        return [soil(1, -1.0), soil(2, -0.4), fsr(1), *imu()]
    if device_id == "PIPE_BK1":
        # Provisional backup-device profile pending final channel registry.
        return [soil(1, 0.4)]
    if device_id == "HUB_01":
        return [
            {
                "sensor_instance_id": "HUB_01_RAIN_RAW_01",
                "sensor_type": "RAIN_MECHANISM_RAW",
                "channel": "RAW",
                "raw_value": int(max(0, round(rain_proxy + rng.gauss(0, 1)))),
                "unit": "simulated_count",
            },
        ]
    raise ValueError(f"Unknown simulated device: {device_id}")


def generate_one_zone_demo(
    config: DemoNetworkConfig = DemoNetworkConfig(),
) -> list[ScheduledTelemetry]:
    """Generate chronologically ordered, correlated simulated device packets.

    Four simulated telemetry-producing nodes: Type A, Type B, independent
    Backup Pipe, Sensor Hub. Main Black Box is a gateway identifier;
    Centralized Power Hub is never treated as an environmental sensor.
    """
    if not config.zone_id:
        raise ValueError("zone_id must not be empty")
    if config.start_time.utcoffset() is None:
        raise ValueError("start_time must be timezone-aware")
    if config.scenario not in ("stable", "gradual_wetting", "rapid_wetting_tilt"):
        raise ValueError(f"Unknown scenario: {config.scenario}")

    schedule = generate_mode_schedule(config.start_time, config.segments)
    if len(schedule) < 2:
        raise ValueError("At least two scheduled samples are required")

    result: list[ScheduledTelemetry] = []
    run_id = f"SIM_HW_{config.seed}_{config.scenario}"
    total_elapsed_seconds = (schedule[-1].observed_at - schedule[0].observed_at).total_seconds()

    for device_id in DEVICE_IDS:
        rng = random.Random(_device_seed(config.seed, device_id))
        for index, scheduled in enumerate(schedule):
            progress = (
                (scheduled.observed_at - schedule[0].observed_at).total_seconds()
                / total_elapsed_seconds
            )
            base_moisture, base_tilt, rain = _scenario_state(config.scenario, progress)
            readings = _readings(device_id, base_moisture, base_tilt, rain, rng)
            packet = TelemetryPacket(
                schema_version="1.0",
                packet_id=f"{run_id}_{device_id}_{index:05d}",
                zone_id=config.zone_id,
                device_id=device_id,
                boot_id=f"{run_id}_{device_id}_BOOT",
                sequence_no=index,
                observed_at=scheduled.observed_at,
                received_at=scheduled.observed_at + timedelta(seconds=2),
                source_origin=SourceOrigin.SIMULATED,
                test_run_id=run_id,
                measurements=readings,
                device_health={
                    "battery_voltage": round(4.05 - progress * 0.08, 3),
                    "sensor_read_error": False,
                },
                transport={
                    "gateway_id": GATEWAY_ID,
                    "rssi_dbm": round(-67 + rng.gauss(0, 2), 2),
                    "snr_db": round(8 + rng.gauss(0, 1), 2),
                    "extra_metadata": {
                        "simulation": True,
                        "route": "SIMULATED_PIPE_OR_HUB_TO_BLACK_BOX",
                    },
                },
            )
            result.append(
                ScheduledTelemetry(
                    packet=packet,
                    operating_mode=scheduled.operating_mode,
                    delta_t_seconds=scheduled.delta_t_seconds,
                )
            )

    return sorted(result, key=lambda row: (
        row.packet.observed_at, row.packet.device_id, row.packet.sequence_no
    ))
