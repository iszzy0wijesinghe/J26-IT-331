"""Multi-pipe deterministic telemetry simulation for GeoNex."""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from shared.contracts.telemetry import TelemetryPacket
from shared.enums.domain import OperatingMode
from shared.simulation.generator import SimulationConfig, generate_baseline_packets
from shared.simulation.topology import GEONEX_DEMO_ZONES, SimulatedZone


@dataclass(frozen=True)
class MultiPipeSimulationConfig:
    """Configuration for a reproducible multi-pipe simulation."""

    seed: int = 42
    start_time: datetime = datetime(2026, 10, 10, 0, 0, tzinfo=UTC)
    packets_per_pipe: int = 5
    operating_mode: OperatingMode = OperatingMode.IDLE


def derive_device_seed(
    simulation_seed: int,
    zone_id: str,
    device_id: str,
) -> int:
    """Derive a stable random seed for one simulated device."""

    identity = f"{simulation_seed}:{zone_id}:{device_id}"

    digest = sha256(identity.encode("utf-8")).digest()

    return int.from_bytes(digest[:8], byteorder="big")


def generate_demo_packets(
    config: MultiPipeSimulationConfig,
    zones: tuple[SimulatedZone, ...] = GEONEX_DEMO_ZONES,
) -> list[TelemetryPacket]:
    """Generate chronologically ordered, device-specific telemetry.

    This is an engineering test fixture, not a calibrated landslide model.
    """

    if config.packets_per_pipe < 0:
        raise ValueError("packets_per_pipe must not be negative")

    if config.start_time.utcoffset() is None:
        raise ValueError("start_time must be timezone-aware")

    packets: list[TelemetryPacket] = []

    for zone in zones:
        for pipe in zone.pipes:
            device_seed = derive_device_seed(
                simulation_seed=config.seed,
                zone_id=pipe.zone_id,
                device_id=pipe.device_id,
            )

            pipe_config = SimulationConfig(
                seed=device_seed,
                zone_id=pipe.zone_id,
                device_id=pipe.device_id,
                start_time=config.start_time,
                packet_count=config.packets_per_pipe,
                operating_mode=config.operating_mode,
            )

            packets.extend(generate_baseline_packets(pipe_config))

    packets.sort(
        key=lambda packet: (
            packet.observed_at,
            packet.zone_id,
            packet.device_id,
            packet.sequence_no,
        )
    )

    return packets
