"""
GeoNex C3 - M5 Multivariate Training Dataset Builder.

Research objectives:
- Mode-conditioned variable-rate forecasting
- Multi-sensor temporal learning
- Multi-horizon prediction
- Chronological target alignment
- Episode/device isolation
- No future-data leakage

Forecast horizons:
    15, 30, 60 minutes.

Target alignment:
    Nearest actual observation within configured tolerance.

Missing targets:
    Represented using target masks.

IMPORTANT:
    This module does not fabricate future sensor observations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import numpy as np

from components.c3_forecasting.models.m5_multivariate_gru import (
    FORECAST_HORIZONS,
    SENSOR_FEATURES,
)

from components.c3_forecasting.preprocessing.m5_features import (
    extract_m5_sequence,
    parse_utc_timestamp,
)


@dataclass
class M5DatasetConfig:

    sequence_length: int = 32

    minimum_sequence_length: int = 3

    target_tolerance_minutes: float = 3.0

    minimum_valid_targets: int = 1

    require_all_horizons: bool = False


@dataclass
class M5TrainingSample:

    features: np.ndarray

    targets: np.ndarray

    target_mask: np.ndarray

    sequence_length: int

    dataset_id: str

    device_id: str

    episode_id: str

    forecast_origin: str


class M5DatasetError(RuntimeError):
    pass


def _group_observations(
    observations: list[dict[str, Any]],
) -> dict[tuple[str, str, str], list[dict[str, Any]]]:

    groups = {}

    for observation in observations:

        key = (
            str(observation["dataset_id"]),
            str(observation["device_id"]),
            str(observation["episode_id"]),
        )

        groups.setdefault(key, []).append(observation)

    for group in groups.values():

        group.sort(
            key=lambda row: parse_utc_timestamp(
                row["timestamp"]
            )
        )

        previous_timestamp = None

        for row in group:

            timestamp = parse_utc_timestamp(
                row["timestamp"]
            )

            if (
                previous_timestamp is not None
                and timestamp <= previous_timestamp
            ):
                raise M5DatasetError(
                    "Duplicate or non-increasing timestamps "
                    "within a device/episode."
                )

            previous_timestamp = timestamp

    return groups


def _find_target_observation(
    observations: list[dict[str, Any]],
    target_time,
    tolerance_minutes: float,
):

    tolerance_seconds = tolerance_minutes * 60.0

    best_observation = None
    best_difference = float("inf")

    for observation in observations:

        timestamp = parse_utc_timestamp(
            observation["timestamp"]
        )

        difference = abs(
            (timestamp - target_time).total_seconds()
        )

        if difference > tolerance_seconds:
            continue

        if difference < best_difference:

            best_difference = difference

            best_observation = observation

    return best_observation


def _extract_target_values(
    observation: dict[str, Any] | None,
) -> tuple[np.ndarray, np.ndarray]:

    target = np.zeros(
        len(SENSOR_FEATURES),
        dtype=np.float32,
    )

    mask = np.zeros(
        len(SENSOR_FEATURES),
        dtype=np.float32,
    )

    if observation is None:
        return target, mask

    for index, sensor in enumerate(SENSOR_FEATURES):

        value = observation.get(sensor)

        if value is None:
            continue

        numeric_value = float(value)

        if not np.isfinite(numeric_value):
            continue

        target[index] = numeric_value

        mask[index] = 1.0

    return target, mask


def build_m5_training_samples(
    observations: list[dict[str, Any]],
    config: M5DatasetConfig | None = None,
) -> list[M5TrainingSample]:

    if config is None:
        config = M5DatasetConfig()

    if config.sequence_length < 1:
        raise ValueError(
            "sequence_length must be positive"
        )

    if config.minimum_sequence_length < 1:
        raise ValueError(
            "minimum_sequence_length must be positive"
        )

    if config.target_tolerance_minutes < 0:
        raise ValueError(
            "Target tolerance cannot be negative"
        )

    groups = _group_observations(observations)

    samples = []

    for group_key, group in groups.items():

        dataset_id, device_id, episode_id = group_key

        if len(group) < config.minimum_sequence_length:
            continue

        for origin_index in range(
            config.minimum_sequence_length - 1,
            len(group),
        ):

            origin_observation = group[origin_index]

            origin_time = parse_utc_timestamp(
                origin_observation["timestamp"]
            )

            start_index = max(
                0,
                origin_index - config.sequence_length + 1,
            )

            history = group[
                start_index : origin_index + 1
            ]

            if len(history) < config.minimum_sequence_length:
                continue

            features = extract_m5_sequence(history)

            targets = np.zeros(
                (
                    len(FORECAST_HORIZONS),
                    len(SENSOR_FEATURES),
                ),
                dtype=np.float32,
            )

            target_mask = np.zeros_like(targets)

            for horizon_index, horizon in enumerate(
                FORECAST_HORIZONS
            ):

                target_time = origin_time + timedelta(
                    minutes=horizon
                )

                # Only observations strictly after the
                # forecast origin are eligible targets.
                future_observations = [
                    observation
                    for observation in group[origin_index + 1 :]
                ]

                matched_observation = (
                    _find_target_observation(
                        future_observations,
                        target_time,
                        config.target_tolerance_minutes,
                    )
                )

                values, masks = _extract_target_values(
                    matched_observation
                )

                targets[horizon_index] = values

                target_mask[horizon_index] = masks

            valid_target_count = int(
                target_mask.sum()
            )

            if (
                valid_target_count
                < config.minimum_valid_targets
            ):
                continue

            if config.require_all_horizons:

                horizon_coverage = (
                    target_mask.sum(axis=1) > 0
                )

                if not horizon_coverage.all():
                    continue

            samples.append(
                M5TrainingSample(
                    features=features,
                    targets=targets,
                    target_mask=target_mask,
                    sequence_length=len(history),
                    dataset_id=dataset_id,
                    device_id=device_id,
                    episode_id=episode_id,
                    forecast_origin=origin_time.isoformat(),
                )
            )

    return samples


def pad_m5_samples(
    samples: list[M5TrainingSample],
) -> dict[str, np.ndarray]:

    if not samples:
        raise M5DatasetError(
            "Cannot pad an empty sample collection"
        )

    maximum_length = max(
        sample.sequence_length
        for sample in samples
    )

    feature_count = samples[0].features.shape[1]

    batch_size = len(samples)

    features = np.zeros(
        (
            batch_size,
            maximum_length,
            feature_count,
        ),
        dtype=np.float32,
    )

    targets = np.stack(
        [sample.targets for sample in samples]
    )

    target_masks = np.stack(
        [sample.target_mask for sample in samples]
    )

    lengths = np.zeros(
        batch_size,
        dtype=np.int64,
    )

    for index, sample in enumerate(samples):

        length = sample.sequence_length

        features[index, :length] = sample.features

        lengths[index] = length

    return {
        "features": features,
        "targets": targets,
        "target_masks": target_masks,
        "lengths": lengths,
    }