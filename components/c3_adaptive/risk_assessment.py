"""GeoNex C3 forecast-informed monitoring urgency assessment.

This module combines current sensor indicators and future
soil-moisture forecasts to recommend monitoring urgency.

All thresholds are synthetic research assumptions.
This module does not predict landslide probability.
"""

from __future__ import annotations

import math

from dataclasses import dataclass
from typing import Any

from components.c3_adaptive.config import (
    AdaptiveControllerConfig,
    MODE_PRIORITY,
    OperatingMode,
)


REQUIRED_SENSORS = (
    "soil_moisture_pct",
    "rainfall_proxy_counts",
    "tilt_deg",
    "vibration_g",
)

REQUIRED_HORIZONS = frozenset({15, 30, 60})


@dataclass(frozen=True)
class RiskAssessment:
    recommended_mode: OperatingMode
    current_sensor_mode: OperatingMode
    forecast_mode: OperatingMode
    reasons: tuple[str, ...]
    forecast_moisture_rise_pp: float | None
    input_complete: bool
    assessment_type: str = "SYNTHETIC_MONITORING_URGENCY"


def _maximum_mode(
    first: OperatingMode,
    second: OperatingMode,
) -> OperatingMode:
    return max(
        (first, second),
        key=lambda mode: MODE_PRIORITY[mode],
    )


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None

    return number if math.isfinite(number) else None


def assess_monitoring_urgency(
    *,
    current_sensors: dict[str, Any],
    forecasts: list[dict[str, Any]],
    config: AdaptiveControllerConfig | None = None,
) -> RiskAssessment:
    """Assess monitoring urgency using current readings and forecasts."""

    config = config or AdaptiveControllerConfig()
    thresholds = config.thresholds

    reasons: list[str] = []

    current_mode = OperatingMode.IDLE
    forecast_mode = OperatingMode.IDLE

    # --------------------------------------------------
    # Validate required current sensors.
    # --------------------------------------------------

    sensor_values = {
        name: _finite_number(current_sensors.get(name))
        for name in REQUIRED_SENSORS
    }

    invalid_sensors = [
        name
        for name, value in sensor_values.items()
        if value is None
    ]

    if invalid_sensors:
        reasons.append(
            "Missing or invalid current sensors: "
            + ", ".join(invalid_sensors)
        )

        current_mode = OperatingMode.RISK

    moisture = sensor_values["soil_moisture_pct"]
    rainfall = sensor_values["rainfall_proxy_counts"]
    tilt = sensor_values["tilt_deg"]
    vibration = sensor_values["vibration_g"]

    # --------------------------------------------------
    # Current moisture indicator.
    # --------------------------------------------------

    if moisture is not None:
        if not 0 <= moisture <= 100:
            reasons.append(
                "Current soil moisture is outside the valid percentage range."
            )
            current_mode = _maximum_mode(
                current_mode,
                OperatingMode.RISK,
            )

        elif moisture >= thresholds.moisture_warning_pct:
            current_mode = _maximum_mode(
                current_mode,
                OperatingMode.WARNING,
            )
            reasons.append(
                "Current soil moisture exceeds the experimental warning threshold."
            )

        elif moisture >= thresholds.moisture_risk_pct:
            current_mode = _maximum_mode(
                current_mode,
                OperatingMode.RISK,
            )
            reasons.append(
                "Current soil moisture exceeds the experimental risk threshold."
            )

    # --------------------------------------------------
    # Current rainfall indicator.
    # --------------------------------------------------

    if rainfall is not None:
        if rainfall < 0:
            current_mode = _maximum_mode(
                current_mode,
                OperatingMode.RISK,
            )
            reasons.append(
                "Rainfall proxy is outside its valid nonnegative range."
            )

        elif rainfall >= thresholds.rainfall_warning_counts:
            current_mode = _maximum_mode(
                current_mode,
                OperatingMode.WARNING,
            )
            reasons.append(
                "Rainfall proxy exceeds the experimental warning threshold."
            )

        elif rainfall >= thresholds.rainfall_risk_counts:
            current_mode = _maximum_mode(
                current_mode,
                OperatingMode.RISK,
            )
            reasons.append(
                "Rainfall proxy exceeds the experimental risk threshold."
            )

    # --------------------------------------------------
    # Current tilt indicator.
    # --------------------------------------------------

    if tilt is not None:
        absolute_tilt = abs(tilt)

        if absolute_tilt >= thresholds.tilt_warning_deg:
            current_mode = _maximum_mode(
                current_mode,
                OperatingMode.WARNING,
            )
            reasons.append(
                "Tilt magnitude exceeds the experimental warning threshold."
            )

        elif absolute_tilt >= thresholds.tilt_risk_deg:
            current_mode = _maximum_mode(
                current_mode,
                OperatingMode.RISK,
            )
            reasons.append(
                "Tilt magnitude exceeds the experimental risk threshold."
            )

    # --------------------------------------------------
    # Current vibration indicator.
    # --------------------------------------------------

    if vibration is not None:
        if vibration < 0:
            current_mode = _maximum_mode(
                current_mode,
                OperatingMode.RISK,
            )
            reasons.append(
                "Vibration magnitude is invalid."
            )

        elif vibration >= thresholds.vibration_warning_g:
            current_mode = _maximum_mode(
                current_mode,
                OperatingMode.WARNING,
            )
            reasons.append(
                "Vibration exceeds the experimental warning threshold."
            )

        elif vibration >= thresholds.vibration_risk_g:
            current_mode = _maximum_mode(
                current_mode,
                OperatingMode.RISK,
            )
            reasons.append(
                "Vibration exceeds the experimental risk threshold."
            )

    # --------------------------------------------------
    # Validate forecasting horizons.
    # --------------------------------------------------

    forecast_values: dict[int, float] = {}

    duplicate_horizons = False
    invalid_forecasts = False

    for prediction in forecasts:
        if not isinstance(prediction, dict):
            invalid_forecasts = True
            continue

        horizon = prediction.get("horizon_minutes")

        if type(horizon) is not int:
            invalid_forecasts = True
            continue

        if horizon not in REQUIRED_HORIZONS:
            invalid_forecasts = True
            continue

        if horizon in forecast_values:
            duplicate_horizons = True
            continue

        value = _finite_number(
            prediction.get("predicted_soil_moisture_pct")
        )

        if value is None or not 0 <= value <= 100:
            invalid_forecasts = True
            continue

        forecast_values[horizon] = value

    forecasts_complete = (
        set(forecast_values) == REQUIRED_HORIZONS
        and not duplicate_horizons
        and not invalid_forecasts
    )

    if not forecasts_complete:
        forecast_mode = OperatingMode.RISK
        reasons.append(
            "Forecast information is missing, duplicated, or invalid."
        )

    # --------------------------------------------------
    # Forecasted moisture thresholds.
    # --------------------------------------------------

    for horizon, predicted_moisture in sorted(
        forecast_values.items()
    ):
        if predicted_moisture >= thresholds.moisture_warning_pct:
            forecast_mode = _maximum_mode(
                forecast_mode,
                OperatingMode.WARNING,
            )
            reasons.append(
                f"+{horizon} minute forecast exceeds "
                "the experimental moisture warning threshold."
            )

        elif predicted_moisture >= thresholds.moisture_risk_pct:
            forecast_mode = _maximum_mode(
                forecast_mode,
                OperatingMode.RISK,
            )
            reasons.append(
                f"+{horizon} minute forecast exceeds "
                "the experimental moisture risk threshold."
            )

    # --------------------------------------------------
    # Forecasted moisture rise.
    # --------------------------------------------------

    moisture_rise = None

    if (
        moisture is not None
        and 0 <= moisture <= 100
        and forecasts_complete
    ):
        moisture_rise = max(
            predicted - moisture
            for predicted in forecast_values.values()
        )

        if moisture_rise >= thresholds.moisture_rise_warning_pp:
            forecast_mode = _maximum_mode(
                forecast_mode,
                OperatingMode.WARNING,
            )
            reasons.append(
                "Forecasted moisture rise exceeds the "
                "experimental warning threshold."
            )

        elif moisture_rise >= thresholds.moisture_rise_risk_pp:
            forecast_mode = _maximum_mode(
                forecast_mode,
                OperatingMode.RISK,
            )
            reasons.append(
                "Forecasted moisture rise exceeds the "
                "experimental risk threshold."
            )

    # --------------------------------------------------
    # Combine current conditions and forecasts.
    # --------------------------------------------------

    recommended_mode = _maximum_mode(
        current_mode,
        forecast_mode,
    )

    input_complete = (
        not invalid_sensors
        and forecasts_complete
        and all(
            (
                moisture is not None
                and 0 <= moisture <= 100,
                rainfall is not None
                and rainfall >= 0,
                tilt is not None,
                vibration is not None
                and vibration >= 0,
            )
        )
    )

    if not reasons:
        reasons.append(
            "No experimental risk thresholds were exceeded."
        )

    return RiskAssessment(
        recommended_mode=recommended_mode,
        current_sensor_mode=current_mode,
        forecast_mode=forecast_mode,
        reasons=tuple(reasons),
        forecast_moisture_rise_pp=moisture_rise,
        input_complete=input_complete,
    )