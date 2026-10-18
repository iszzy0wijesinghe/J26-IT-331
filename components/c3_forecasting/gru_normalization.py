"""Training-only sensor normalization for GeoNex C3 GRU models."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from components.c3_forecasting.gru_dataset import SENSOR_NAMES

SENSOR_COUNT = len(SENSOR_NAMES)


@dataclass(frozen=True)
class GRUNormalizer:
    """Normalize valid sensor readings without modifying validity masks."""

    means: np.ndarray
    stds: np.ndarray

    @classmethod
    def fit(cls, examples: list[dict]) -> GRUNormalizer:
        """Calculate statistics from training examples only."""

        if not examples:
            raise ValueError("Cannot fit normalizer on empty examples")

        sums = np.zeros(SENSOR_COUNT, dtype=np.float64)
        squared_sums = np.zeros(SENSOR_COUNT, dtype=np.float64)
        counts = np.zeros(SENSOR_COUNT, dtype=np.float64)

        for example in examples:
            sequence = example["sequence"]

            values = sequence[:, :SENSOR_COUNT].astype(np.float64)
            masks = sequence[:, SENSOR_COUNT:]

            sums += (values * masks).sum(axis=0)
            squared_sums += ((values**2) * masks).sum(axis=0)
            counts += masks.sum(axis=0)

        means = np.divide(
            sums,
            counts,
            out=np.zeros_like(sums),
            where=counts > 0,
        )

        variances = np.divide(
            squared_sums,
            counts,
            out=np.zeros_like(sums),
            where=counts > 0,
        ) - means**2

        variances = np.maximum(variances, 0.0)

        stds = np.sqrt(variances)

        # Avoid division by zero for constant or unobserved sensors.
        stds[stds < 1e-6] = 1.0

        return cls(
            means=means.astype(np.float32),
            stds=stds.astype(np.float32),
        )

    def transform(self, sequence: np.ndarray) -> np.ndarray:
        """Normalize valid values while preserving masks and placeholders."""

        if sequence.ndim != 2 or sequence.shape[1] != SENSOR_COUNT * 2:
            raise ValueError("Invalid GRU sequence shape")

        result = sequence.copy()

        values = result[:, :SENSOR_COUNT]
        masks = result[:, SENSOR_COUNT:]

        normalized = (values - self.means) / self.stds

        # Invalid measurements remain zero, not normalized placeholders.
        result[:, :SENSOR_COUNT] = np.where(
            masks > 0,
            normalized,
            0.0,
        )

        if not np.isfinite(result).all():
            raise ValueError("Normalization produced non-finite values")

        return result

    def to_dict(self) -> dict:
        """Return serializable normalization parameters."""

        return {
            "sensor_names": list(SENSOR_NAMES),
            "means": self.means.tolist(),
            "stds": self.stds.tolist(),
        }