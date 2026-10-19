"""GeoNex C3 adaptive monitoring sampling-latency simulation.

Calculates the delay between a synthetic event onset and
the next scheduled monitoring cycle.

Uses the same piecewise-constant schedule assumption as
adaptive_energy_replay.py:

- Each decision takes effect at its forecast origin.
- The selected interval applies until the next decision.
- The monitoring schedule restarts at each decision boundary.
- Each segment includes a sample at its start.
- Segment ends are exclusive.
- The final simulation endpoint is exclusive.

This is a counterfactual sampling-delay model.
It does not validate physical landslide detection.
"""

from __future__ import annotations

import math

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AdaptiveDetectionLatencyEstimate:
    event_onset_timestamp: str
    detection_timestamp: str | None
    detection_latency_s: float | None
    detected_within_window: bool
    monitoring_mode_at_onset: str
    monitoring_interval_at_onset_s: float


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if parsed.tzinfo is None:
        raise ValueError(
            "Timestamps must include a timezone."
        )

    return parsed.astimezone(timezone.utc)


def estimate_adaptive_detection_latency(
    *,
    decisions: list[dict[str, Any]],
    event_onset_timestamp: str,
    end_timestamp: str,
) -> AdaptiveDetectionLatencyEstimate:
    """Find the first scheduled sample at or after event onset."""

    if not decisions:
        raise ValueError(
            "At least one adaptive decision is required."
        )

    event_time = _parse_timestamp(
        event_onset_timestamp
    )

    end_time = _parse_timestamp(
        end_timestamp
    )

    origins = [
        _parse_timestamp(result["forecast_origin"])
        for result in decisions
    ]

    if any(
        origins[index] <= origins[index - 1]
        for index in range(1, len(origins))
    ):
        raise ValueError(
            "Adaptive decisions must be strictly chronological."
        )

    if end_time <= origins[-1]:
        raise ValueError(
            "Simulation end must follow the final decision."
        )

    if not origins[0] <= event_time < end_time:
        raise ValueError(
            "Event onset must lie inside the simulation window."
        )

    mode_at_onset: str | None = None
    interval_at_onset: float | None = None

    detection_time: datetime | None = None

    for index, result in enumerate(decisions):
        segment_start = origins[index]

        segment_end = (
            origins[index + 1]
            if index + 1 < len(origins)
            else end_time
        )

        decision = result["adaptive_decision"]

        interval_s = float(
            decision["monitoring_interval_s"]
        )

        if (
            not math.isfinite(interval_s)
            or interval_s <= 0
        ):
            raise ValueError(
                "Monitoring interval must be finite and positive."
            )

        # Identify the mode active when the event begins.
        if segment_start <= event_time < segment_end:
            mode_at_onset = decision["selected_mode"]
            interval_at_onset = interval_s

        # Earlier segments cannot detect a later event.
        if segment_end <= event_time:
            continue

        # The first eligible sample must be at or after
        # both the event onset and the segment start.
        search_time = max(
            event_time,
            segment_start,
        )

        offset_s = (
            search_time - segment_start
        ).total_seconds()

        cycle_index = max(
            0,
            math.ceil(
                offset_s / interval_s - 1e-12
            ),
        )

        candidate_offset_s = (
            cycle_index * interval_s
        )

        segment_duration_s = (
            segment_end - segment_start
        ).total_seconds()

        # Segment end is exclusive.
        if candidate_offset_s >= segment_duration_s:
            continue

        from datetime import timedelta

        candidate_time = (
            segment_start
            + timedelta(seconds=candidate_offset_s)
        )

        if candidate_time < event_time:
            continue

        detection_time = candidate_time
        break

    if mode_at_onset is None or interval_at_onset is None:
        raise RuntimeError(
            "Unable to determine the monitoring mode at event onset."
        )

    if detection_time is None:
        return AdaptiveDetectionLatencyEstimate(
            event_onset_timestamp=event_onset_timestamp,
            detection_timestamp=None,
            detection_latency_s=None,
            detected_within_window=False,
            monitoring_mode_at_onset=mode_at_onset,
            monitoring_interval_at_onset_s=interval_at_onset,
        )

    latency_s = (
        detection_time - event_time
    ).total_seconds()

    return AdaptiveDetectionLatencyEstimate(
        event_onset_timestamp=event_onset_timestamp,
        detection_timestamp=detection_time.isoformat(),
        detection_latency_s=latency_s,
        detected_within_window=True,
        monitoring_mode_at_onset=mode_at_onset,
        monitoring_interval_at_onset_s=interval_at_onset,
    )