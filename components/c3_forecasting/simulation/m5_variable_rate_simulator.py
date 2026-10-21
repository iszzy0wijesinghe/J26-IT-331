"""
GeoNex C3 — M5 Variable-Rate Environmental Simulator.

Generates:
1. High-resolution synthetic environmental reference observations.
2. Mode-conditioned variable-rate sensor observations.

Synthetic engineering data only.
Not validated real-world landslide observations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import exp, pi, sin
import random


MODE_INTERVALS = {
    "DEEP_SLEEP": (900, 1500),
    "IDLE": (420, 720),
    "RISK": (120, 240),
    "WARNING": (30, 90),
    "EMERGENCY": (8, 25),
}

SENSORS = (
    "soil_moisture_pct",
    "rainfall_proxy_counts",
    "tilt_deg",
    "vibration_g",
    "fsr_adc",
    "air_temperature_c",
    "humidity_pct",
)


@dataclass
class SimulationConfig:
    episodes: int = 36
    duration_hours: int = 24
    reference_interval_seconds: int = 5
    seed: int = 42


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def determine_mode(risk):
    if risk >= 0.85:
        return "EMERGENCY"
    if risk >= 0.65:
        return "WARNING"
    if risk >= 0.45:
        return "RISK"
    if risk >= 0.20:
        return "IDLE"
    return "DEEP_SLEEP"


def generate_episode(
    episode_index: int,
    config: SimulationConfig,
):
    rng = random.Random(config.seed + episode_index)

    start = datetime(
        2026, 1, 1, tzinfo=timezone.utc
    ) + timedelta(days=episode_index)

    duration_seconds = config.duration_hours * 3600
    step = config.reference_interval_seconds

    base_moisture = rng.uniform(25, 45)
    base_temperature = rng.uniform(23, 31)
    rainfall_strength = rng.uniform(0.5, 1.0)
    instability_strength = rng.uniform(0.6, 1.0)

    storm_center = duration_seconds * rng.uniform(0.35, 0.65)
    storm_width = duration_seconds * rng.uniform(0.10, 0.18)

    reference = []

    for second in range(0, duration_seconds + 1, step):
        timestamp = start + timedelta(seconds=second)

        storm = exp(
            -0.5 * ((second - storm_center) / storm_width) ** 2
        )

        rainfall = rainfall_strength * storm

        moisture = clamp(
            base_moisture
            + 45 * rainfall
            + 5 * sin(2 * pi * second / duration_seconds),
            0,
            100,
        )

        humidity = clamp(
            60 + 35 * rainfall,
            0,
            100,
        )

        temperature = (
            base_temperature
            + 3 * sin(2 * pi * second / duration_seconds)
            - 2 * rainfall
        )

        tilt = (
            0.4
            + instability_strength * 5 * storm
            + 0.000002 * second
        )

        vibration = (
            0.01
            + instability_strength * 0.30 * storm
        )

        fsr = (
            900
            + instability_strength * 1600 * storm
        )

        rainfall_proxy = 100 * rainfall

        # Synthetic scheduling score, not a validated
        # landslide probability.
        #
        # Low-risk periods should support DEEP_SLEEP.
        # Severe storm periods should support WARNING
        # and EMERGENCY when the simulated conditions
        # justify those states.

        risk = clamp(
            0.02
            + 0.34 * rainfall
            + 0.16 * (moisture / 100)
            + 0.22 * (tilt / 6)
            + 0.30 * instability_strength * storm,
            0,
            1,
        )

        reference.append({
            "dataset_id": "M5_SYNTHETIC_VARIABLE_RATE",
            "device_id": f"PIPE_{episode_index:03d}",
            "episode_id": f"SYN_VR_EP_{episode_index:03d}",
            "timestamp": timestamp.isoformat(),
            "operating_mode": determine_mode(risk),
            "soil_moisture_pct": round(moisture, 5),
            "rainfall_proxy_counts": round(rainfall_proxy, 5),
            "tilt_deg": round(tilt, 5),
            "vibration_g": round(vibration, 6),
            "fsr_adc": round(fsr, 5),
            "air_temperature_c": round(temperature, 5),
            "humidity_pct": round(humidity, 5),
            "synthetic_risk": round(risk, 5),
            "source_type": "SIMULATED",
        })

    observations = []

    current_second = 0

    while current_second <= duration_seconds:
        reference_index = min(
        current_second // step,
        len(reference) - 1,
    )

        observation = reference[reference_index].copy()

        # Preserve the actual scheduled sampling timestamp.
        # The sensor values are taken from the preceding
        # reference point, which is at most one reference
        # interval earlier.
        actual_timestamp = start + timedelta(
            seconds=current_second
        )

        observation["timestamp"] = actual_timestamp.isoformat()

        observations.append(observation)

        mode = observation["operating_mode"]
        lower, upper = MODE_INTERVALS[mode]

        interval = rng.randint(lower, upper)
        current_second += interval

    return reference, observations


def generate_dataset(config: SimulationConfig):
    all_reference = []
    all_observations = []

    for episode_index in range(config.episodes):
        reference, observations = generate_episode(
            episode_index,
            config,
        )

        all_reference.extend(reference)
        all_observations.extend(observations)

    return all_reference, all_observations