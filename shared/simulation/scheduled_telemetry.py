"""Mode-aware deterministic telemetry generation for GeoNex."""

from dataclasses import dataclass
from datetime import UTC, datetime

from shared.contracts.telemetry import TelemetryPacket
from shared.enums.domain import OperatingMode
from shared.simulation.generator import SimulationConfig, generate_baseline_packets
from shared.simulation.mode_schedule import ModeSegment, generate_mode_schedule
from shared.simulation.runner import derive_device_seed
from shared.simulation.topology import GEONEX_DEMO_ZONES, SimulatedZone


@dataclass(frozen=True)
class ScheduledTelemetry:
    """A telemetry packet with simulation-only operating-mode context."""

    packet: TelemetryPacket
    operating_mode: OperatingMode
    delta_t_seconds: float | None


@dataclass(frozen=True)
class ScheduledTelemetryConfig:
    """Configuration for deterministic variable-rate telemetry."""

    seed: int = 42
    start_time: datetime = datetime(2026, 10, 10, 0, 0, tzinfo=UTC)
    segments: tuple[ModeSegment, ...] = (
        ModeSegment(OperatingMode.DEEP_SLEEP, 2),
        ModeSegment(OperatingMode.IDLE, 2),
        ModeSegment(OperatingMode.RISK, 2),
        ModeSegment(OperatingMode.WARNING, 2),
        ModeSegment(OperatingMode.EMERGENCY, 2),
    )


def generate_scheduled_demo_telemetry(
    config: ScheduledTelemetryConfig,
    zones: tuple[SimulatedZone, ...] = GEONEX_DEMO_ZONES,
) -> list[ScheduledTelemetry]:
    """Generate six-pipe telemetry with deterministic mode transitions.

    Sensor values remain synthetic engineering fixtures.
    Mode transitions are supplied by the simulation configuration,
    not inferred from sensor measurements.
    """

    schedule = generate_mode_schedule(config.start_time, config.segments)

    results: list[ScheduledTelemetry] = []

    for zone in zones:
        for pipe in zone.pipes:
            device_seed = derive_device_seed(
                simulation_seed=config.seed,
                zone_id=pipe.zone_id,
                device_id=pipe.device_id,
            )

            # Generate one continuous sensor-value sequence per device.
            # The schedule supplies the timestamps and operating modes.
            baseline_packets = generate_baseline_packets(
                SimulationConfig(
                    seed=device_seed,
                    zone_id=pipe.zone_id,
                    device_id=pipe.device_id,
                    start_time=config.start_time,
                    packet_count=len(schedule),
                    operating_mode=OperatingMode.IDLE,
                )
            )

            for sample, baseline_packet in zip(
                schedule,
                baseline_packets,
                strict=True,
            ):
                updated_packet = baseline_packet.model_copy(
                    update={
                        "observed_at": sample.observed_at,
                        "received_at": sample.observed_at,
                    }
                )

                results.append(
                    ScheduledTelemetry(
                        packet=updated_packet,
                        operating_mode=sample.operating_mode,
                        delta_t_seconds=sample.delta_t_seconds,
                    )
                )

    results.sort(
        key=lambda item: (
            item.packet.observed_at,
            item.packet.zone_id,
            item.packet.device_id,
            item.packet.sequence_no,
        )
    )

    return results