
"""Database loaders for GeoNex simulated telemetry."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy.orm import Session

from apps.ingestion.persistence import (
    PersistenceStatus,
    persist_telemetry_packet,
)
from components.c4_trust.pipeline import C4TelemetryGate
from shared.contracts.telemetry import TelemetryPacket
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


@dataclass(frozen=True)
class C4SimulationLoadResult:
    """Summary of a simulation batch processed through C4."""

    status: SimulationLoadStatus
    total_packets: int
    accepted_packets: int
    created_packets: int
    existing_packets: int
    quarantined_packets: int
    created_observations: int


def load_simulated_telemetry(
    session: Session,
    items: list[ScheduledTelemetry],
) -> SimulationLoadResult:
    """Persist simulated telemetry using the existing ingestion logic.

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
            raise ValueError(f"Unexpected persistence status: {result.status}")

    return SimulationLoadResult(
        status=SimulationLoadStatus.COMPLETED,
        total_packets=len(items),
        created_packets=created_packets,
        existing_packets=existing_packets,
        created_observations=created_observations,
    )
<<<<<<< HEAD
=======


def load_simulated_telemetry_with_c4(
    session: Session,
    items: list[ScheduledTelemetry],
    *,
    gate: C4TelemetryGate,
    prepare_and_sign: Callable[
        [ScheduledTelemetry], tuple[TelemetryPacket, str]
    ],
    now_provider: Callable[[TelemetryPacket], datetime] | None = None,
) -> C4SimulationLoadResult:
    """Validate simulated telemetry through C4 before persistence.

    prepare_and_sign must return a prepared packet and its valid signature.
    In production, credentials and verification evidence must come from
    trusted security providers rather than test fixtures.

    If now_provider is omitted, C4 uses its normal clock. Historical
    simulation packets may fail freshness validation.

    Rejected packets are quarantined by the C4 gate and are never sent
    to database persistence by this function.

    The caller owns the database transaction. This function does not
    create a database connection or commit.
    """

    accepted_packets = 0
    created_packets = 0
    existing_packets = 0
    quarantined_packets = 0
    created_observations = 0

    for item in items:
        packet, signature = prepare_and_sign(item)

        gate_kwargs: dict[str, datetime] = {}

        if now_provider is not None:
            gate_kwargs["now"] = now_provider(packet)

        gate_result = gate.process(
            packet,
            signature,
            **gate_kwargs,
        )

        eligible_packet = gate_result.eligible_packet

        if eligible_packet is None:
            quarantined_packets += 1
            continue

        accepted_packets += 1

        persistence_result = persist_telemetry_packet(
            session=session,
            packet=eligible_packet,
        )

        if persistence_result.status == PersistenceStatus.CREATED:
            created_packets += 1
            created_observations += persistence_result.observation_count

        elif (
            persistence_result.status
            == PersistenceStatus.ALREADY_EXISTS
        ):
            existing_packets += 1

        else:
            raise ValueError(
                "Unexpected persistence status: "
                f"{persistence_result.status}"
            )

    return C4SimulationLoadResult(
        status=SimulationLoadStatus.COMPLETED,
        total_packets=len(items),
        accepted_packets=accepted_packets,
        created_packets=created_packets,
        existing_packets=existing_packets,
        quarantined_packets=quarantined_packets,
        created_observations=created_observations,
    )
>>>>>>> a3a0e76f7d4d51298b0cf715c59230d82010503a
