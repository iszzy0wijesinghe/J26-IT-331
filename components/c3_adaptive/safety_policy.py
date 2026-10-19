"""GeoNex C3 stateful adaptive monitoring safety policy.

Controls monitoring-mode transitions using:
- Forecast-informed urgency assessments
- Observation freshness
- Historical sequence completeness
- Consecutive independent stable evaluations
- Observation-quality safeguards
- Conservative recovery from elevated monitoring modes

Experimental research policy only.
Not a field-certified landslide warning controller.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from components.c3_adaptive.config import (
    MODE_PRIORITY,
    AdaptiveControllerConfig,
    OperatingMode,
)
from components.c3_adaptive.risk_assessment import (
    RiskAssessment,
)


@dataclass(frozen=True)
class SafetyDecision:
    previous_mode: OperatingMode
    selected_mode: OperatingMode
    monitoring_interval_s: float
    stable_evaluation_count: int
    safety_override_applied: bool
    reasons: tuple[str, ...]
    policy_version: str


class AdaptiveSafetyPolicy:
    """Stateful safety-constrained monitoring-mode selector."""

    def __init__(
        self,
        config: AdaptiveControllerConfig | None = None,
        *,
        initial_mode: OperatingMode = OperatingMode.IDLE,
    ) -> None:
        self.config = config or AdaptiveControllerConfig()

        self.current_mode = OperatingMode(initial_mode)

        self.stable_evaluation_count = 0

        self.last_evaluation_time: datetime | None = None

        self.last_stable_evaluation_time: datetime | None = None

    @staticmethod
    def _parse_time(
        value: str | datetime,
    ) -> datetime:
        if isinstance(value, datetime):
            parsed = value

        elif isinstance(value, str):
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )

        else:
            raise ValueError(
                "Invalid observation timestamp."
            )

        if parsed.tzinfo is None:
            raise ValueError(
                "Observation timestamp must include a timezone."
            )

        return parsed.astimezone(UTC)

    def evaluate(
        self,
        *,
        assessment: RiskAssessment,
        observation_timestamp: str | datetime,
        evaluation_timestamp: str | datetime,
        history_steps: int,
        observation_quality_valid: bool = True,
        deep_sleep_quality_eligible: bool = True,
    ) -> SafetyDecision:
        """Select a safe monitoring mode and update controller state.

        observation_quality_valid:
            Whether required current sensor readings satisfy
            basic quality checks.

        deep_sleep_quality_eligible:
            Whether the observation meets the stricter quality
            requirements for DEEP_SLEEP.

        Both default to True for backward compatibility with
        existing synthetic unit tests. The integrated controller
        must explicitly supply validated values.
        """

        previous_mode = self.current_mode

        reasons = list(assessment.reasons)

        observation_time = self._parse_time(
            observation_timestamp
        )

        evaluation_time = self._parse_time(
            evaluation_timestamp
        )

        # --------------------------------------------------
        # 1. Validate evaluation chronology.
        # --------------------------------------------------

        if (
            self.last_evaluation_time is not None
            and evaluation_time <= self.last_evaluation_time
        ):
            raise ValueError(
                "Safety evaluations must have strictly "
                "increasing timestamps."
            )

        if history_steps < 0:
            raise ValueError(
                "Historical sequence length cannot be negative."
            )

        if type(observation_quality_valid) is not bool:
            raise ValueError(
                "observation_quality_valid must be boolean."
            )

        if type(deep_sleep_quality_eligible) is not bool:
            raise ValueError(
                "deep_sleep_quality_eligible must be boolean."
            )

        # --------------------------------------------------
        # 2. Validate observation freshness.
        # --------------------------------------------------

        observation_age_s = (
            evaluation_time - observation_time
        ).total_seconds()

        freshness_valid = (
            math.isfinite(observation_age_s)
            and 0 <= observation_age_s
            <= self.config.safety.maximum_observation_age_s
        )

        safety_override = False

        required_mode = assessment.recommended_mode

        # --------------------------------------------------
        # 3. Enforce freshness protection.
        # --------------------------------------------------

        if not freshness_valid:
            if (
                MODE_PRIORITY[required_mode]
                < MODE_PRIORITY[OperatingMode.RISK]
            ):
                required_mode = OperatingMode.RISK

            reasons.append(
                "Observation freshness is invalid or "
                "exceeds the configured maximum age."
            )

            safety_override = True

        # --------------------------------------------------
        # 4. Enforce completeness protection.
        # --------------------------------------------------

        if not assessment.input_complete:
            if (
                MODE_PRIORITY[required_mode]
                < MODE_PRIORITY[OperatingMode.RISK]
            ):
                required_mode = OperatingMode.RISK

            reasons.append(
                "Incomplete sensor or forecast information "
                "prevents low-frequency monitoring."
            )

            safety_override = True

        # --------------------------------------------------
        # 5. Enforce observation-quality protection.
        # --------------------------------------------------

        if not observation_quality_valid:
            if (
                MODE_PRIORITY[required_mode]
                < MODE_PRIORITY[OperatingMode.RISK]
            ):
                required_mode = OperatingMode.RISK

            reasons.append(
                "Observation quality is insufficient "
                "for routine low-frequency monitoring."
            )

            safety_override = True

        # --------------------------------------------------
        # 6. Determine whether stability can be counted.
        # --------------------------------------------------

        stable_conditions = (
            required_mode == OperatingMode.IDLE
            and assessment.input_complete
            and freshness_valid
            and observation_quality_valid
        )

        stable_required = (
            self.config.safety
            .stable_evaluations_for_deep_sleep
        )

        minimum_stable_interval = (
            self.config.safety
            .minimum_stable_evaluation_interval_s
        )

        # Compute proposed state locally.
        # Commit it only after successful decision selection.

        next_stable_count = self.stable_evaluation_count

        next_stable_time = self.last_stable_evaluation_time

        if stable_conditions:
            enough_time_elapsed = (
                next_stable_time is None
                or (
                    evaluation_time - next_stable_time
                ).total_seconds()
                >= minimum_stable_interval
            )

            if enough_time_elapsed:
                next_stable_count += 1
                next_stable_time = evaluation_time

            else:
                reasons.append(
                    "Stable evaluation not counted because "
                    "the minimum elapsed-time requirement "
                    "has not been satisfied."
                )

        else:
            next_stable_count = 0
            next_stable_time = None

        # --------------------------------------------------
        # 7. Immediate escalation.
        # --------------------------------------------------

        if (
            required_mode in (
                OperatingMode.RISK,
                OperatingMode.WARNING,
            )
            and MODE_PRIORITY[required_mode]
            > MODE_PRIORITY[previous_mode]
        ):
            selected_mode = required_mode

            next_stable_count = 0
            next_stable_time = None

            reasons.append(
                "Monitoring urgency increased; "
                "immediate escalation applied."
            )

        # --------------------------------------------------
        # 8. Maintain elevated monitoring when required.
        # --------------------------------------------------

        elif required_mode in (
            OperatingMode.RISK,
            OperatingMode.WARNING,
        ):
            selected_mode = (
                previous_mode
                if (
                    MODE_PRIORITY[previous_mode]
                    > MODE_PRIORITY[required_mode]
                )
                else required_mode
            )

            next_stable_count = 0
            next_stable_time = None

            if selected_mode != required_mode:
                reasons.append(
                    "Higher monitoring mode retained until "
                    "stable recovery conditions are met."
                )

        # --------------------------------------------------
        # 9. Controlled recovery and DEEP_SLEEP selection.
        # --------------------------------------------------

        else:
            if previous_mode == OperatingMode.WARNING:
                if next_stable_count >= stable_required:
                    selected_mode = OperatingMode.RISK

                    next_stable_count = 0
                    next_stable_time = None

                    reasons.append(
                        "Sustained stability permits recovery "
                        "from WARNING to RISK."
                    )

                else:
                    selected_mode = OperatingMode.WARNING

            elif previous_mode == OperatingMode.RISK:
                if next_stable_count >= stable_required:
                    selected_mode = OperatingMode.IDLE

                    next_stable_count = 0
                    next_stable_time = None

                    reasons.append(
                        "Sustained stability permits recovery "
                        "from RISK to IDLE."
                    )

                else:
                    selected_mode = OperatingMode.RISK

            elif previous_mode == OperatingMode.IDLE:
                deep_sleep_allowed = (
                    self.config.safety.allow_deep_sleep
                    and deep_sleep_quality_eligible
                    and history_steps >= (
                        self.config.safety
                        .minimum_history_steps_for_deep_sleep
                    )
                    and next_stable_count >= stable_required
                )

                if deep_sleep_allowed:
                    selected_mode = OperatingMode.DEEP_SLEEP

                    reasons.append(
                        "Independent stable evaluations, "
                        "history requirements, and observation "
                        "quality permit DEEP_SLEEP."
                    )

                else:
                    selected_mode = OperatingMode.IDLE

                    if not deep_sleep_quality_eligible:
                        reasons.append(
                            "DEEP_SLEEP blocked by observation "
                            "quality eligibility requirements."
                        )

            else:
                # Already in DEEP_SLEEP.
                # Recheck eligibility instead of retaining it
                # unconditionally.

                deep_sleep_still_allowed = (
                    self.config.safety.allow_deep_sleep
                    and stable_conditions
                    and deep_sleep_quality_eligible
                    and history_steps >= (
                        self.config.safety
                        .minimum_history_steps_for_deep_sleep
                    )
                )

                if deep_sleep_still_allowed:
                    selected_mode = OperatingMode.DEEP_SLEEP

                else:
                    selected_mode = OperatingMode.IDLE

                    next_stable_count = 0
                    next_stable_time = None

                    reasons.append(
                        "DEEP_SLEEP eligibility no longer "
                        "satisfied; returning to IDLE."
                    )

        # --------------------------------------------------
        # 10. Resolve monitoring interval.
        # --------------------------------------------------

        interval = self.config.monitoring.interval_for(
            selected_mode
        )

        # --------------------------------------------------
        # 11. Commit successful policy state.
        # --------------------------------------------------

        self.current_mode = selected_mode

        self.stable_evaluation_count = next_stable_count

        self.last_stable_evaluation_time = next_stable_time

        self.last_evaluation_time = evaluation_time

        return SafetyDecision(
            previous_mode=previous_mode,
            selected_mode=selected_mode,
            monitoring_interval_s=interval,
            stable_evaluation_count=next_stable_count,
            safety_override_applied=safety_override,
            reasons=tuple(reasons),
            policy_version=self.config.policy_version,
        )