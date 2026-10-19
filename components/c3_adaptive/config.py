"""GeoNex C3 adaptive monitoring research configuration.

All thresholds and intervals are experimental assumptions for
synthetic replay. They are not field-calibrated landslide
warning thresholds or measured hardware characteristics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


class OperatingMode(str, Enum):
    DEEP_SLEEP = "DEEP_SLEEP"
    IDLE = "IDLE"
    RISK = "RISK"
    WARNING = "WARNING"


MODE_PRIORITY = {
    OperatingMode.DEEP_SLEEP: 0,
    OperatingMode.IDLE: 1,
    OperatingMode.RISK: 2,
    OperatingMode.WARNING: 3,
}


@dataclass(frozen=True)
class MonitoringConfig:
    """Experimental monitoring intervals in seconds."""

    deep_sleep_interval_s: float = 300.0
    idle_interval_s: float = 30.0
    risk_interval_s: float = 10.0
    warning_interval_s: float = 5.0

    def __post_init__(self) -> None:
        intervals = (
            self.deep_sleep_interval_s,
            self.idle_interval_s,
            self.risk_interval_s,
            self.warning_interval_s,
        )

        if any(value <= 0 for value in intervals):
            raise ValueError(
                "Monitoring intervals must be positive."
            )

        if not (
            self.deep_sleep_interval_s
            > self.idle_interval_s
            > self.risk_interval_s
            > self.warning_interval_s
        ):
            raise ValueError(
                "Monitoring intervals must decrease as "
                "monitoring urgency increases."
            )

    def interval_for(self, mode: OperatingMode) -> float:
        mapping = {
            OperatingMode.DEEP_SLEEP:
                self.deep_sleep_interval_s,
            OperatingMode.IDLE:
                self.idle_interval_s,
            OperatingMode.RISK:
                self.risk_interval_s,
            OperatingMode.WARNING:
                self.warning_interval_s,
        }

        return mapping[OperatingMode(mode)]


@dataclass(frozen=True)
class RiskThresholds:
    """Illustrative thresholds for synthetic controller experiments."""

    moisture_risk_pct: float = 65.0
    moisture_warning_pct: float = 85.0

    rainfall_risk_counts: float = 20.0
    rainfall_warning_counts: float = 50.0

    tilt_risk_deg: float = 5.0
    tilt_warning_deg: float = 12.0

    vibration_risk_g: float = 0.15
    vibration_warning_g: float = 0.40

    moisture_rise_risk_pp: float = 5.0
    moisture_rise_warning_pp: float = 12.0

    def __post_init__(self) -> None:
        pairs = (
            (
                self.moisture_risk_pct,
                self.moisture_warning_pct,
            ),
            (
                self.rainfall_risk_counts,
                self.rainfall_warning_counts,
            ),
            (
                self.tilt_risk_deg,
                self.tilt_warning_deg,
            ),
            (
                self.vibration_risk_g,
                self.vibration_warning_g,
            ),
            (
                self.moisture_rise_risk_pp,
                self.moisture_rise_warning_pp,
            ),
        )

        for risk, warning in pairs:
            if not 0 <= risk < warning:
                raise ValueError(
                    "Each warning threshold must exceed "
                    "its corresponding risk threshold."
                )


@dataclass(frozen=True)
class SafetyConfig:
    """Constraints preventing unsafe monitoring reductions."""

    maximum_observation_age_s: float = 600.0

    minimum_history_steps_for_deep_sleep: int = 12

    allow_deep_sleep: bool = True

    # Number of consecutive stable evaluations required before
    # DEEP_SLEEP may be considered.
    stable_evaluations_for_deep_sleep: int = 3
    
    # Minimum elapsed time between independent stable evaluations.
    # Experimental synthetic-replay assumption.
    minimum_stable_evaluation_interval_s: float = 300.0

    def __post_init__(self) -> None:
        if self.maximum_observation_age_s <= 0:
            raise ValueError(
                "Maximum observation age must be positive."
            )

        if self.minimum_history_steps_for_deep_sleep < 3:
            raise ValueError(
                "Deep-sleep history requirement must be >= 3."
            )

        if self.stable_evaluations_for_deep_sleep < 1:
            raise ValueError(
                "Stable evaluation count must be positive."
            )
            
        if (
            not math.isfinite(self.minimum_stable_evaluation_interval_s)
            or self.minimum_stable_evaluation_interval_s <= 0
        ):
            raise ValueError(
                "Minimum stable evaluation interval must be "
                "finite and positive."
            )


@dataclass(frozen=True)
class AdaptiveControllerConfig:
    """Complete versionable controller configuration."""

    monitoring: MonitoringConfig = field(
        default_factory=MonitoringConfig
    )

    thresholds: RiskThresholds = field(
        default_factory=RiskThresholds
    )

    safety: SafetyConfig = field(
        default_factory=SafetyConfig
    )

    policy_version: str = "c3-adaptive-policy-v1"

    research_status: str = (
        "SYNTHETIC_RESEARCH_NOT_FIELD_VALIDATED"
    )