"""GeoNex C3 adaptive monitoring energy replay.

Estimates monitoring energy using a chronological sequence
of actual C3 adaptive controller decisions.

Research assumptions:
- Decisions are generated at historical observation times.
- Each selected interval remains active until the next decision.
- Monitoring cycles are simulated, not observed.
- Energy parameters are hypothetical, not hardware-measured.
- No intermediate sensor readings or ML forecasts are invented.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from components.c3_simulation.energy_model import (
    EnergyModelConfig,
    estimate_fixed_interval_energy,
)


@dataclass(frozen=True)
class AdaptiveEnergySegment:
    start_timestamp: str
    end_timestamp: str
    duration_s: float
    monitoring_mode: str
    monitoring_interval_s: float
    monitoring_cycles: int
    baseline_energy_mj: float
    monitoring_energy_mj: float
    total_energy_mj: float


@dataclass(frozen=True)
class AdaptiveEnergyReplay:
    total_duration_s: float
    total_monitoring_cycles: int
    total_baseline_energy_mj: float
    total_monitoring_energy_mj: float
    total_energy_mj: float
    total_energy_wh: float
    average_power_mw: float
    segments: tuple[AdaptiveEnergySegment, ...]


def _parse_timestamp(value: str) -> datetime:
    """Parse a timezone-aware ISO timestamp."""

    parsed = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if parsed.tzinfo is None:
        raise ValueError(
            "Replay timestamps must include a timezone."
        )

    return parsed.astimezone(UTC)


def estimate_adaptive_energy(
    *,
    decisions: list[dict[str, Any]],
    end_timestamp: str,
    config: EnergyModelConfig | None = None,
) -> AdaptiveEnergyReplay:
    """Estimate energy from chronological adaptive decisions.

    Each decision controls the interval from its forecast origin
    until the next decision, or until end_timestamp.

    Monitoring schedules restart at each decision boundary.
    This is an explicit modeling assumption.
    """

    config = config or EnergyModelConfig()

    if not decisions:
        raise ValueError(
            "At least one adaptive decision is required."
        )

    end_time = _parse_timestamp(end_timestamp)

    segments: list[AdaptiveEnergySegment] = []

    previous_time: datetime | None = None

    for index, result in enumerate(decisions):
        start_timestamp = result["forecast_origin"]
        start_time = _parse_timestamp(start_timestamp)

        if (
            previous_time is not None
            and start_time <= previous_time
        ):
            raise ValueError(
                "Adaptive decisions must be strictly chronological."
            )

        if index + 1 < len(decisions):
            segment_end_timestamp = decisions[
                index + 1
            ]["forecast_origin"]

            segment_end_time = _parse_timestamp(
                segment_end_timestamp
            )
        else:
            segment_end_timestamp = end_timestamp
            segment_end_time = end_time

        if segment_end_time <= start_time:
            raise ValueError(
                "Each adaptive segment must have positive duration."
            )

        decision = result["adaptive_decision"]

        interval_s = float(
            decision["monitoring_interval_s"]
        )

        mode = decision["selected_mode"]

        duration_s = (
            segment_end_time - start_time
        ).total_seconds()

        estimate = estimate_fixed_interval_energy(
            duration_s=duration_s,
            monitoring_interval_s=interval_s,
            config=config,
        )

        segments.append(
            AdaptiveEnergySegment(
                start_timestamp=start_timestamp,
                end_timestamp=segment_end_timestamp,
                duration_s=duration_s,
                monitoring_mode=mode,
                monitoring_interval_s=interval_s,
                monitoring_cycles=estimate.monitoring_cycles,
                baseline_energy_mj=estimate.baseline_energy_mj,
                monitoring_energy_mj=estimate.monitoring_energy_mj,
                total_energy_mj=estimate.total_energy_mj,
            )
        )

        previous_time = start_time

    total_duration_s = sum(
        segment.duration_s
        for segment in segments
    )

    total_cycles = sum(
        segment.monitoring_cycles
        for segment in segments
    )

    total_baseline_energy_mj = sum(
        segment.baseline_energy_mj
        for segment in segments
    )

    total_monitoring_energy_mj = sum(
        segment.monitoring_energy_mj
        for segment in segments
    )

    total_energy_mj = (
        total_baseline_energy_mj
        + total_monitoring_energy_mj
    )

    total_energy_wh = (
        total_energy_mj / 3_600_000.0
    )

    average_power_mw = (
        total_energy_mj / total_duration_s
    )

    return AdaptiveEnergyReplay(
        total_duration_s=total_duration_s,
        total_monitoring_cycles=total_cycles,
        total_baseline_energy_mj=total_baseline_energy_mj,
        total_monitoring_energy_mj=total_monitoring_energy_mj,
        total_energy_mj=total_energy_mj,
        total_energy_wh=total_energy_wh,
        average_power_mw=average_power_mw,
        segments=tuple(segments),
    )