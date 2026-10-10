"""Deterministic operating-mode schedules for GeoNex simulations."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from shared.enums.domain import OperatingMode
from shared.simulation.generator import MODE_INTERVALS_SECONDS


@dataclass(frozen=True)
class ModeSegment:
    """A period during which a device operates in one mode."""

    mode: OperatingMode
    sample_count: int


@dataclass(frozen=True)
class ScheduledSample:
    """One scheduled observation and its active operating mode."""

    sequence_no: int
    observed_at: datetime
    operating_mode: OperatingMode
    delta_t_seconds: float | None


def generate_mode_schedule(
    start_time: datetime,
    segments: tuple[ModeSegment, ...],
) -> list[ScheduledSample]:
    """Generate a deterministic variable-rate observation schedule.

    Each segment's sampling interval determines the time until its
    next observation, including the transition to the next segment.

    This is an engineering simulation policy, not a validated
    physical-device sampling policy.
    """

    if start_time.utcoffset() is None:
        raise ValueError("start_time must be timezone-aware")

    if not segments:
        raise ValueError("At least one mode segment is required")

    if any(segment.sample_count <= 0 for segment in segments):
        raise ValueError("Every mode segment must have a positive sample_count")

    samples: list[ScheduledSample] = []
    current_time = start_time
    previous_time: datetime | None = None

    for segment in segments:
        interval = timedelta(seconds=MODE_INTERVALS_SECONDS[segment.mode])

        for _ in range(segment.sample_count):
            delta_t = (
                None
                if previous_time is None
                else (current_time - previous_time).total_seconds()
            )

            samples.append(
                ScheduledSample(
                    sequence_no=len(samples),
                    observed_at=current_time,
                    operating_mode=segment.mode,
                    delta_t_seconds=delta_t,
                )
            )

            previous_time = current_time
            current_time += interval

    return samples