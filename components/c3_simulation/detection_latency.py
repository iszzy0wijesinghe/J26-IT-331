"""GeoNex C3 simulated event-detection latency.

Estimates sampling delay between an event onset and the
next scheduled monitoring cycle.

Assumptions:
- Event onset is known exactly in the synthetic scenario.
- Monitoring occurs at a fixed interval.
- Monitoring begins at simulation time zero.
- An event is detectable at the first sample after onset.
- No sensor, inference, communication, or alert delay is included.

Research simulation only.
Not a validated landslide-detection model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class DetectionLatencyEstimate:
    event_onset_s: float
    monitoring_interval_s: float
    detection_time_s: float
    detection_latency_s: float


def estimate_fixed_detection_latency(
    *,
    event_onset_s: float,
    monitoring_interval_s: float,
) -> DetectionLatencyEstimate:
    """Estimate delay until the next scheduled monitoring cycle.

    Monitoring occurs at:
        0, interval, 2*interval, 3*interval, ...

    If an event begins exactly at a monitoring timestamp,
    detection latency is zero.
    """

    if (
        not math.isfinite(event_onset_s)
        or event_onset_s < 0
    ):
        raise ValueError(
            "Event onset must be finite and non-negative."
        )

    if (
        not math.isfinite(monitoring_interval_s)
        or monitoring_interval_s <= 0
    ):
        raise ValueError(
            "Monitoring interval must be finite and positive."
        )

    # Use a small numerical tolerance when identifying
    # an event that occurs exactly on a sample boundary.
    cycle_index = math.ceil(
        event_onset_s / monitoring_interval_s - 1e-12
    )

    detection_time_s = (
        cycle_index * monitoring_interval_s
    )

    detection_latency_s = max(
        0.0,
        detection_time_s - event_onset_s,
    )

    return DetectionLatencyEstimate(
        event_onset_s=event_onset_s,
        monitoring_interval_s=monitoring_interval_s,
        detection_time_s=detection_time_s,
        detection_latency_s=detection_latency_s,
    )