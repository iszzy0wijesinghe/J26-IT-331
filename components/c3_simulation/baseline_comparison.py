"""GeoNex C3 fixed monitoring baseline comparison.

Compares fixed-frequency monitoring strategies under
identical hypothetical energy assumptions.

Research simulation only.
No physical energy measurements are used.
"""

from __future__ import annotations

from dataclasses import dataclass

from components.c3_simulation.energy_model import (
    EnergyModelConfig,
    EnergyEstimate,
    estimate_fixed_interval_energy,
)


@dataclass(frozen=True)
class BaselineComparison:
    strategy_name: str
    monitoring_interval_s: float
    energy: EnergyEstimate
    reference_energy_mj: float
    energy_saving_pct: float


def compare_fixed_baselines(
    *,
    duration_s: float,
    intervals_s: tuple[float, ...] = (
        5.0,
        10.0,
        30.0,
        300.0,
    ),
    reference_interval_s: float = 5.0,
    config: EnergyModelConfig | None = None,
) -> list[BaselineComparison]:
    """Compare fixed monitoring intervals.

    The reference strategy is fixed monitoring at
    reference_interval_s.

    Energy saving (%) =
        (reference_energy - strategy_energy)
        / reference_energy * 100
    """

    config = config or EnergyModelConfig()

    if not intervals_s:
        raise ValueError(
            "At least one monitoring interval is required."
        )

    reference = estimate_fixed_interval_energy(
        duration_s=duration_s,
        monitoring_interval_s=reference_interval_s,
        config=config,
    )

    if reference.total_energy_mj <= 0:
        raise ValueError(
            "Reference energy must be positive."
        )

    comparisons = []

    for interval in intervals_s:
        estimate = estimate_fixed_interval_energy(
            duration_s=duration_s,
            monitoring_interval_s=interval,
            config=config,
        )

        saving_pct = (
            (
                reference.total_energy_mj
                - estimate.total_energy_mj
            )
            / reference.total_energy_mj
        ) * 100.0

        comparisons.append(
            BaselineComparison(
                strategy_name=f"FIXED_{interval:g}S",
                monitoring_interval_s=interval,
                energy=estimate,
                reference_energy_mj=reference.total_energy_mj,
                energy_saving_pct=saving_pct,
            )
        )

    return comparisons