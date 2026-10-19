"""GeoNex C3 hypothetical monitoring energy model.

Estimates monitoring energy consumption using:
- Continuous baseline power
- Additional energy consumed per monitoring cycle
- Monitoring interval
- Simulation duration

All numerical defaults are illustrative assumptions.
They are NOT measurements of GeoNex hardware.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class EnergyModelConfig:
    """Configurable hypothetical hardware energy parameters."""

    # Continuous background power consumption.
    baseline_power_mw: float = 5.0

    # Additional energy per monitoring cycle.
    monitoring_cycle_energy_mj: float = 20.0

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.baseline_power_mw)
            or self.baseline_power_mw < 0
        ):
            raise ValueError(
                "Baseline power must be finite and non-negative."
            )

        if (
            not math.isfinite(self.monitoring_cycle_energy_mj)
            or self.monitoring_cycle_energy_mj < 0
        ):
            raise ValueError(
                "Monitoring-cycle energy must be finite "
                "and non-negative."
            )


@dataclass(frozen=True)
class EnergyEstimate:
    duration_s: float
    monitoring_interval_s: float
    monitoring_cycles: int
    baseline_energy_mj: float
    monitoring_energy_mj: float
    total_energy_mj: float
    total_energy_wh: float
    average_power_mw: float


def estimate_fixed_interval_energy(
    *,
    duration_s: float,
    monitoring_interval_s: float,
    config: EnergyModelConfig | None = None,
) -> EnergyEstimate:
    """Estimate energy for periodic monitoring.

    Assumptions:
    - A monitoring cycle occurs at t=0.
    - Further cycles occur at multiples of the interval.
    - The simulation window is [0, duration_s).
    - Each monitoring cycle has identical incremental energy.
    - Background power is constant throughout the window.
    """

    config = config or EnergyModelConfig()

    if not math.isfinite(duration_s) or duration_s <= 0:
        raise ValueError(
            "Simulation duration must be finite and positive."
        )

    if (
        not math.isfinite(monitoring_interval_s)
        or monitoring_interval_s <= 0
    ):
        raise ValueError(
            "Monitoring interval must be finite and positive."
        )

    # Number of scheduled samples in [0, duration_s).
    # Small epsilon protects exact multiples from float rounding.
    monitoring_cycles = math.ceil(
        duration_s / monitoring_interval_s - 1e-12
    )

    baseline_energy_mj = (
        config.baseline_power_mw * duration_s
    )

    monitoring_energy_mj = (
        monitoring_cycles
        * config.monitoring_cycle_energy_mj
    )

    total_energy_mj = (
        baseline_energy_mj + monitoring_energy_mj
    )

    # 1 Wh = 3,600,000 mJ.
    total_energy_wh = (
        total_energy_mj / 3_600_000.0
    )

    average_power_mw = (
        total_energy_mj / duration_s
    )

    return EnergyEstimate(
        duration_s=duration_s,
        monitoring_interval_s=monitoring_interval_s,
        monitoring_cycles=monitoring_cycles,
        baseline_energy_mj=baseline_energy_mj,
        monitoring_energy_mj=monitoring_energy_mj,
        total_energy_mj=total_energy_mj,
        total_energy_wh=total_energy_wh,
        average_power_mw=average_power_mw,
    )