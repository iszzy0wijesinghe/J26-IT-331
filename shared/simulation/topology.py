"""GeoNex demonstration topology definitions."""

from dataclasses import dataclass
from enum import StrEnum


class PipeRole(StrEnum):
    """Logical role of a sensor pipe."""

    TYPE_A = "TYPE_A"
    TYPE_B = "TYPE_B"
    BACKUP = "BACKUP"


@dataclass(frozen=True)
class SimulatedPipe:
    """A sensor pipe belonging to one monitoring zone."""

    device_id: str
    zone_id: str
    role: PipeRole


@dataclass(frozen=True)
class SimulatedZone:
    """A monitoring zone containing multiple sensor pipes."""

    zone_id: str
    pipes: tuple[SimulatedPipe, ...]


GEONEX_DEMO_ZONES = (
    SimulatedZone(
        zone_id="ZONE_01",
        pipes=(
            SimulatedPipe(
                device_id="PIPE_A1",
                zone_id="ZONE_01",
                role=PipeRole.TYPE_A,
            ),
            SimulatedPipe(
                device_id="PIPE_B1",
                zone_id="ZONE_01",
                role=PipeRole.TYPE_B,
            ),
            SimulatedPipe(
                device_id="PIPE_BK1",
                zone_id="ZONE_01",
                role=PipeRole.BACKUP,
            ),
        ),
    ),
    SimulatedZone(
        zone_id="ZONE_02",
        pipes=(
            SimulatedPipe(
                device_id="PIPE_A2",
                zone_id="ZONE_02",
                role=PipeRole.TYPE_A,
            ),
            SimulatedPipe(
                device_id="PIPE_B2",
                zone_id="ZONE_02",
                role=PipeRole.TYPE_B,
            ),
            SimulatedPipe(
                device_id="PIPE_BK2",
                zone_id="ZONE_02",
                role=PipeRole.BACKUP,
            ),
        ),
    ),
)


def get_all_demo_pipes() -> tuple[SimulatedPipe, ...]:
    """Return every pipe in the two-zone demonstration."""

    return tuple(
        pipe
        for zone in GEONEX_DEMO_ZONES
        for pipe in zone.pipes
    )


def get_demo_zone(zone_id: str) -> SimulatedZone:
    """Return a demonstration zone by identifier."""

    for zone in GEONEX_DEMO_ZONES:
        if zone.zone_id == zone_id:
            return zone

    raise ValueError(f"Unknown GeoNex demonstration zone: {zone_id}")