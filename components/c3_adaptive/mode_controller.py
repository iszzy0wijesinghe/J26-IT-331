"""GeoNex C3 forecast-informed adaptive monitoring controller.

Connects:
- Golden Database historical observations
- Active ML forecasting models
- Monitoring urgency assessment
- Stateful safety-constrained mode selection

Research prototype only. Does not issue real-world warnings.
"""

from __future__ import annotations

from typing import Any

from apps.c3_workbench.forecasting_adapter import (
    prepare_forecasting_inputs,
)
from apps.c3_workbench.forecasting_engine import (
    generate_active_forecasts,
)
from apps.c3_workbench.forecasting_reader import (
    parse_timestamp,
)
from components.c3_adaptive.config import (
    AdaptiveControllerConfig,
    OperatingMode,
)
from components.c3_adaptive.risk_assessment import (
    REQUIRED_SENSORS,
    assess_monitoring_urgency,
)
from components.c3_adaptive.safety_policy import (
    AdaptiveSafetyPolicy,
)


class C3AdaptiveModeController:
    """Maintain adaptive monitoring state for one device/episode replay."""

    def __init__(
        self,
        config: AdaptiveControllerConfig | None = None,
    ) -> None:
        self.config = config or AdaptiveControllerConfig()

        self.policy = AdaptiveSafetyPolicy(
            config=self.config,
            initial_mode=OperatingMode.IDLE,
        )

        # A controller instance belongs to one dataset/device/episode.
        self.session_identity: tuple[str, str, str] | None = None

        # Last successfully processed observation.
        self._last_observation_id: int | None = None
        self._last_observation_time = None

    def evaluate(
        self,
        *,
        dataset_id: str,
        device_id: str,
        episode_id: str,
        forecast_origin: str,
    ) -> dict[str, Any]:
        """Generate forecasts and select the next monitoring mode.

        Each successful evaluation must process a newer observation.

        Failed evaluations must not advance the stored observation
        identity or timestamp.
        """

        # --------------------------------------------------
        # 1. Validate replay session identity.
        # --------------------------------------------------

        identity = (
            dataset_id,
            device_id,
            episode_id,
        )

        if (
            self.session_identity is not None
            and self.session_identity != identity
        ):
            raise ValueError(
                "A controller instance cannot mix datasets, "
                "devices, or episodes. Create a new controller "
                "for a new replay session."
            )

        # --------------------------------------------------
        # 2. Load historical forecasting inputs.
        # --------------------------------------------------

        inputs = prepare_forecasting_inputs(
            dataset_id=dataset_id,
            device_id=device_id,
            episode_id=episode_id,
            forecast_origin=forecast_origin,
        )

        steps = inputs["temporal_sequence"]["steps"]

        if not steps:
            raise ValueError(
                "Historical forecasting sequence is empty."
            )

        latest_step = steps[-1]

        current_sensors = dict(
            latest_step["features"]
        )

        observation_timestamp = latest_step["time"]

        observation_time = parse_timestamp(
            observation_timestamp
        )

        evaluation_time = parse_timestamp(
            forecast_origin
        )

        # --------------------------------------------------
        # 3. Validate observation chronology.
        # --------------------------------------------------

        if observation_time > evaluation_time:
            raise ValueError(
                "The observation timestamp cannot be later "
                "than the forecast origin."
            )

        if (
            self._last_observation_time is not None
            and observation_time <= self._last_observation_time
        ):
            raise ValueError(
                "The latest observation timestamp must advance "
                "between adaptive monitoring evaluations."
            )

        # --------------------------------------------------
        # 4. Validate sensor masks.
        # --------------------------------------------------

        sensor_masks = latest_step.get(
            "masks", {}
        )

        invalid_mask_sensors = [
            sensor
            for sensor in REQUIRED_SENSORS
            if sensor_masks.get(sensor) is not True
        ]

        # Invalid sensor masks must not be interpreted
        # as valid numerical measurements.
        for sensor in invalid_mask_sensors:
            current_sensors[sensor] = None

        # --------------------------------------------------
        # 5. Inspect observation quality and provenance.
        # --------------------------------------------------

        quality = latest_step.get(
            "quality", {}
        )

        provenance = latest_step.get(
            "provenance", {}
        )

        observation_quality = quality.get(
            "observation_quality",
            "UNKNOWN",
        )

        receipt_time_basis = provenance.get(
            "receipt_time_basis",
            "UNKNOWN",
        )

        source_origin = quality.get(
            "source_origin",
            "UNKNOWN",
        )

        observation_id = provenance.get(
            "observation_id"
        )

        # --------------------------------------------------
        # 6. Validate observation identity.
        # --------------------------------------------------

        if observation_id is not None:
            if (
                isinstance(observation_id, bool)
                or not isinstance(observation_id, int)
            ):
                raise ValueError(
                    "Observation ID must be an integer."
                )

            if (
                self._last_observation_id is not None
                and observation_id <= self._last_observation_id
            ):
                raise ValueError(
                    "The latest observation ID must advance "
                    "between adaptive monitoring evaluations."
                )

        duplicate_observation = False

        # --------------------------------------------------
        # 7. Generate actual ML forecasts.
        # --------------------------------------------------

        forecast_result = generate_active_forecasts(
            dataset_id=dataset_id,
            device_id=device_id,
            episode_id=episode_id,
            forecast_origin=forecast_origin,
        )

        predictions = forecast_result["predictions"]

        # --------------------------------------------------
        # 8. Assess monitoring urgency.
        # --------------------------------------------------

        assessment = assess_monitoring_urgency(
            current_sensors=current_sensors,
            forecasts=predictions,
            config=self.config,
        )

        # --------------------------------------------------
        # 9. Apply stateful safety constraints.
        # --------------------------------------------------

        # --------------------------------------------------
        # Determine observation-quality eligibility.
        # --------------------------------------------------

        imputed_flags = quality.get("imputed_flags", {})
        corrected_flags = quality.get("corrected_flags", {})

        required_sensor_imputed = any(
            imputed_flags.get(sensor) is True
            for sensor in REQUIRED_SENSORS
        )

        required_sensor_corrected = any(
            corrected_flags.get(sensor) is True
            for sensor in REQUIRED_SENSORS
        )

        observation_quality_valid = (
            not invalid_mask_sensors
            and not required_sensor_imputed
            and not required_sensor_corrected
        )

        # The Golden CSV has no independently verified
        # individual sensor ages or receipt timestamps.
        #
        # We permit experimental DEEP_SLEEP evaluation only
        # under explicitly declared historical-replay assumptions.
        # This must never be interpreted as deployment eligibility.

        deep_sleep_quality_eligible = (
            observation_quality_valid
            and source_origin == "GOLDEN_CSV"
            and receipt_time_basis
            == "ASSUMED_EQUAL_TO_OBSERVATION_TIME"
            and observation_quality
            == "ACCEPTED_CSV_VALUE_UNVERIFIED_PROVENANCE"
        )

        decision = self.policy.evaluate(
            assessment=assessment,
            observation_timestamp=observation_timestamp,
            evaluation_timestamp=forecast_origin,
            history_steps=len(steps),
            observation_quality_valid=observation_quality_valid,
            deep_sleep_quality_eligible=deep_sleep_quality_eligible,
        )

        # --------------------------------------------------
        # 10. Commit successful observation processing.
        #
        # This occurs only after the forecasting,
        # risk-assessment, and safety-policy stages
        # complete successfully.
        # --------------------------------------------------

        self._last_observation_id = observation_id
        self._last_observation_time = observation_time

        if self.session_identity is None:
            self.session_identity = identity

        # --------------------------------------------------
        # 11. Return integrated monitoring decision.
        # --------------------------------------------------

        return {
            "dataset_id": dataset_id,
            "device_id": device_id,
            "episode_id": episode_id,
            "forecast_origin": forecast_origin,
            "forecast_type": "HISTORICAL_REPLAY",
            "research_status": self.config.research_status,
            "policy_version": decision.policy_version,

            # ----------------------------------------------
            # Current sensor observations.
            # ----------------------------------------------

            "current_sensor_values": current_sensors,

            # ----------------------------------------------
            # Observation quality and provenance.
            # ----------------------------------------------

            "observation_quality": {
                "observation_id": observation_id,
                "observation_timestamp": observation_timestamp,
                "sensor_masks": sensor_masks,
                "invalid_mask_sensors": invalid_mask_sensors,
                "duplicate_observation": duplicate_observation,
                "observation_quality": observation_quality,
                "source_origin": source_origin,
                "receipt_time_basis": receipt_time_basis,
                "source_provenance_verified": False,
                "individual_sensor_ages_verified": False,
                "required_sensor_imputed": required_sensor_imputed,
                "required_sensor_corrected": required_sensor_corrected,
                "observation_quality_valid": observation_quality_valid,
                "deep_sleep_quality_eligible": deep_sleep_quality_eligible,
            },

            # ----------------------------------------------
            # ML forecasting outputs.
            # ----------------------------------------------

            "forecasts": predictions,

            # ----------------------------------------------
            # Monitoring urgency assessment.
            # ----------------------------------------------

            "risk_assessment": {
                "recommended_mode": (
                    assessment.recommended_mode.value
                ),
                "current_sensor_mode": (
                    assessment.current_sensor_mode.value
                ),
                "forecast_mode": (
                    assessment.forecast_mode.value
                ),
                "forecast_moisture_rise_pp": (
                    assessment.forecast_moisture_rise_pp
                ),
                "input_complete": (
                    assessment.input_complete
                ),
                "reasons": list(
                    assessment.reasons
                ),
            },

            # ----------------------------------------------
            # Final safety-constrained adaptive decision.
            # ----------------------------------------------

            "adaptive_decision": {
                "previous_mode": (
                    decision.previous_mode.value
                ),
                "selected_mode": (
                    decision.selected_mode.value
                ),
                "monitoring_interval_s": (
                    decision.monitoring_interval_s
                ),
                "stable_evaluation_count": (
                    decision.stable_evaluation_count
                ),
                "safety_override_applied": (
                    decision.safety_override_applied
                ),
                "reasons": list(
                    decision.reasons
                ),
            },

            # ----------------------------------------------
            # Research limitations.
            # ----------------------------------------------

            "limitations": [
                "Synthetic research evaluation only.",
                "Monitoring thresholds are experimental assumptions.",
                "Forecasted moisture is not a landslide probability.",
                "No physical energy measurement is performed.",
                "Golden CSV receipt times are not independently verified.",
                "Individual sensor freshness is not independently verified.",
                "Monitoring intervals are simulated policy outputs.",
            ],
        }