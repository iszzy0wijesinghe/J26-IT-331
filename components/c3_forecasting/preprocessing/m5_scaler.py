"""
GeoNex C3 - M5 Feature and Target Normalization.

Research requirements:
- Fit using training data only.
- Preserve sensor validity masks.
- Preserve operating-mode encodings.
- Preserve elapsed-time encodings.
- Apply identical scaling during inference.
- Support inverse transformation of predictions.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from components.c3_forecasting.models.m5_multivariate_gru import (
    SENSOR_COUNT,
)


@dataclass
class M5ScalerState:

    sensor_mean: np.ndarray

    sensor_std: np.ndarray


class M5SensorScaler:

    def __init__(self):

        self.state: M5ScalerState | None = None

    def fit(
        self,
        training_features: list[np.ndarray],
    ) -> "M5SensorScaler":

        if not training_features:
            raise ValueError(
                "Training features cannot be empty"
            )

        values = []
        masks = []

        for sequence in training_features:

            values.append(
                sequence[:, :SENSOR_COUNT]
            )

            masks.append(
                sequence[
                    :,
                    SENSOR_COUNT : SENSOR_COUNT * 2,
                ]
            )

        all_values = np.concatenate(
            values,
            axis=0,
        )

        all_masks = np.concatenate(
            masks,
            axis=0,
        )

        means = np.zeros(
            SENSOR_COUNT,
            dtype=np.float32,
        )

        stds = np.ones(
            SENSOR_COUNT,
            dtype=np.float32,
        )

        for sensor_index in range(SENSOR_COUNT):

            valid = (
                all_masks[:, sensor_index] > 0
            )

            sensor_values = all_values[
                valid,
                sensor_index,
            ]

            if len(sensor_values) == 0:
                continue

            means[sensor_index] = np.mean(
                sensor_values
            )

            std = np.std(
                sensor_values
            )

            stds[sensor_index] = (
                std if std > 1e-8 else 1.0
            )

        self.state = M5ScalerState(
            sensor_mean=means,
            sensor_std=stds,
        )

        return self

    def transform_features(
        self,
        features: np.ndarray,
    ) -> np.ndarray:

        if self.state is None:
            raise RuntimeError(
                "Scaler must be fitted first"
            )

        result = features.copy().astype(
            np.float32
        )

        sensor_values = result[
            :,
            :SENSOR_COUNT,
        ]

        sensor_masks = result[
            :,
            SENSOR_COUNT : SENSOR_COUNT * 2,
        ]

        normalized = (
            sensor_values - self.state.sensor_mean
        ) / self.state.sensor_std

        # Missing measurements remain zero.
        normalized = np.where(
            sensor_masks > 0,
            normalized,
            0.0,
        )

        result[:, :SENSOR_COUNT] = normalized

        return result

    def transform_targets(
        self,
        targets: np.ndarray,
        target_mask: np.ndarray | None = None,
    ) -> np.ndarray:

        if self.state is None:
            raise RuntimeError(
                "Scaler must be fitted first"
            )

        normalized = (
            targets - self.state.sensor_mean
        ) / self.state.sensor_std

        if target_mask is not None:

            normalized = np.where(
                target_mask > 0,
                normalized,
                0.0,
            )

        return normalized.astype(np.float32)

    def inverse_transform_targets(
        self,
        normalized_targets: np.ndarray,
    ) -> np.ndarray:

        if self.state is None:
            raise RuntimeError(
                "Scaler must be fitted first"
            )

        return (
            normalized_targets * self.state.sensor_std
            + self.state.sensor_mean
        ).astype(np.float32)

    def to_dict(self) -> dict:

        if self.state is None:
            raise RuntimeError(
                "Scaler must be fitted first"
            )

        return {
            "sensor_mean": (
                self.state.sensor_mean.tolist()
            ),
            "sensor_std": (
                self.state.sensor_std.tolist()
            ),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
    ) -> "M5SensorScaler":

        scaler = cls()

        scaler.state = M5ScalerState(
            sensor_mean=np.asarray(
                data["sensor_mean"],
                dtype=np.float32,
            ),
            sensor_std=np.asarray(
                data["sensor_std"],
                dtype=np.float32,
            ),
        )

        return scaler