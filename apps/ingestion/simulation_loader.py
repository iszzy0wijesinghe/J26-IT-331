"""Database loader for GeoNex simulated telemetry."""

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.orm import Session

from apps.ingestion.persistence import (
    PersistenceStatus,
    persist_telemetry_packet,
)
from shared.simulation.scheduled_telemetry import ScheduledTelemetry


class SimulationLoadStatus(StrEnum):
    """Outcome of loading a simulation batch."""

    COMPLETED = "COMPLETED"


@dataclass(frozen=True)
class SimulationLoadResult:
    """Summary of a simulated telemetry database load."""

    status: SimulationLoadStatus
    total_packets: int
    created_packets: int
    existing_packets: int
    created_observations: int


def load_simulated_telemetry(
    session: Session,
    items: list[ScheduledTelemetry],
) -> SimulationLoadResult:
    """Persist a batch of simulated telemetry using existing ingestion logic.

    The caller owns the transaction and must commit or roll back.
    This function does not create a database connection or commit.
    """

    created_packets = 0
    existing_packets = 0
    created_observations = 0

    for item in items:
        result = persist_telemetry_packet(
            session=session,
            packet=item.packet,
        )

        if result.status == PersistenceStatus.CREATED:
            created_packets += 1
            created_observations += result.observation_count

        elif result.status == PersistenceStatus.ALREADY_EXISTS:
            existing_packets += 1

        else:
            raise ValueError(
                f"Unexpected persistence status: {result.status}"
            )

    return SimulationLoadResult(
        status=SimulationLoadStatus.COMPLETED,
        total_packets=len(items),
        created_packets=created_packets,
        existing_packets=existing_packets,
        created_observations=created_observations,
    )