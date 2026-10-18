"""Training-only target normalization for GeoNex C3 GRU."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch


@dataclass(frozen=True)
class GRUTargetNormalizer:
    """Standardize regression targets using training-only statistics."""

    mean: float
    std: float

    @classmethod
    def fit(
        cls,
        examples: list[dict],
    ) -> GRUTargetNormalizer:
        """Fit using training targets only."""

        if not examples:
            raise ValueError(
                "Cannot fit target normalizer on empty examples"
            )

        targets = np.asarray(
            [example["target"] for example in examples],
            dtype=np.float64,
        )

        if not np.isfinite(targets).all():
            raise ValueError(
                "Training targets contain non-finite values"
            )

        mean = float(targets.mean())
        std = float(targets.std())

        if std < 1e-6:
            std = 1.0

        return cls(
            mean=mean,
            std=std,
        )

    def normalize(
        self,
        targets: torch.Tensor,
    ) -> torch.Tensor:
        """Convert raw targets to standardized targets."""

        return (targets - self.mean) / self.std

    def denormalize(
        self,
        predictions: torch.Tensor,
    ) -> torch.Tensor:
        """Convert standardized predictions to original units."""

        return predictions * self.std + self.mean

    def to_dict(self) -> dict[str, float]:
        """Return serializable parameters."""

        return {
            "mean": self.mean,
            "std": self.std,
        }