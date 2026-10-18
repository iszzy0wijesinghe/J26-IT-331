"""Training-only normalization for GeoNex C3 M4 temporal features."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from components.c3_forecasting.preprocessing.gru_dataset import (
    INPUT_FEATURE_COUNT,
)
from components.c3_forecasting.preprocessing.gru_normalization import (
    GRUNormalizer,
)
from components.c3_forecasting.preprocessing.m4_features import (
    M4_INPUT_FEATURE_COUNT,
)

TIME_INDEX = INPUT_FEATURE_COUNT
TIME_KNOWN_INDEX = INPUT_FEATURE_COUNT + 1
MODE_START_INDEX = INPUT_FEATURE_COUNT + 2


def _validate_interval_indicators(sequence: np.ndarray) -> None:
    """Require interval-known indicators to contain only 0 or 1."""

    indicators = sequence[:, TIME_KNOWN_INDEX]

    valid = (indicators == 0.0) | (indicators == 1.0)

    if not np.all(valid):
        raise ValueError("Interval-known indicators must contain only 0 or 1")


@dataclass(frozen=True)
class M4Normalizer:
    """Normalize sensor values and known elapsed-time measurements."""

    sensor_normalizer: GRUNormalizer
    time_mean: float
    time_std: float

    @classmethod
    def fit(cls, examples: list[dict]) -> M4Normalizer:
        """Fit normalization statistics from M4 training examples only."""

        if not examples:
            raise ValueError("Cannot fit M4 normalizer on empty examples")

        sensor_examples = []
        known_times = []

        for example in examples:
            sequence = example["sequence"]

            if (
                sequence.ndim != 2
                or sequence.shape[1] != M4_INPUT_FEATURE_COUNT
                or sequence.shape[0] == 0
            ):
                raise ValueError("Invalid M4 training sequence shape")

            if not np.isfinite(sequence).all():
                raise ValueError("M4 training sequence contains non-finite values")

            # Ensure malformed interval indicators cannot silently
            # enter the normalization statistics.
            _validate_interval_indicators(sequence)

            sensor_examples.append(
                {
                    "sequence": sequence[:, :INPUT_FEATURE_COUNT],
                }
            )

            # Only known intervals contribute to time statistics.
            # The first retained timestep has an unknown interval
            # and must not contribute its placeholder value.
            known = sequence[:, TIME_KNOWN_INDEX] == 1.0

            known_times.extend(sequence[known, TIME_INDEX].astype(np.float64).tolist())

        # Reuse the existing M3 sensor normalization procedure.
        sensor_normalizer = GRUNormalizer.fit(sensor_examples)

        if known_times:
            values = np.asarray(
                known_times,
                dtype=np.float64,
            )

            time_mean = float(values.mean())
            time_std = float(values.std())

            # Avoid division by zero when all observed
            # sampling intervals are identical.
            if time_std < 1e-6:
                time_std = 1.0

        else:
            # Safe defaults for sequences containing no
            # known elapsed-time intervals.
            time_mean = 0.0
            time_std = 1.0

        return cls(
            sensor_normalizer=sensor_normalizer,
            time_mean=time_mean,
            time_std=time_std,
        )

    def transform(
        self,
        sequence: np.ndarray,
        *,
        include_time: bool = True,
        include_mode: bool = True,
    ) -> np.ndarray:
        """Normalize M4 features while preserving ablation settings.

        Feature layout:
            0:7   - Sensor measurements
            7:14  - Sensor observation-validity masks
            14    - log1p(elapsed seconds)
            15    - Interval-known indicator
            16:20 - Operating-mode one-hot encoding

        Disabled feature groups remain zero.
        """

        if (
            sequence.ndim != 2
            or sequence.shape[1] != M4_INPUT_FEATURE_COUNT
            or sequence.shape[0] == 0
        ):
            raise ValueError("Invalid M4 sequence shape")

        if not np.isfinite(sequence).all():
            raise ValueError("M4 sequence contains non-finite values")

        # Reject malformed interval-known indicators before
        # applying normalization or ablation masking.
        _validate_interval_indicators(sequence)

        # Copy the input to prevent mutation of the source sequence.
        result = sequence.astype(
            np.float32,
            copy=True,
        )

        # Normalize the seven sensor values using the
        # existing M3 normalization implementation.
        #
        # Observation-validity masks are preserved.
        result[:, :INPUT_FEATURE_COUNT] = self.sensor_normalizer.transform(
            result[:, :INPUT_FEATURE_COUNT]
        )

        if include_time:
            known = result[:, TIME_KNOWN_INDEX] == 1.0

            # Standardize known log-transformed intervals.
            # Unknown intervals retain their zero placeholder.
            result[:, TIME_INDEX] = np.where(
                known,
                (result[:, TIME_INDEX] - self.time_mean) / self.time_std,
                0.0,
            )

        else:
            # M4-B: Disable both elapsed-time information
            # and the interval-known indicator.
            result[
                :,
                TIME_INDEX : TIME_KNOWN_INDEX + 1,
            ] = 0.0

        if not include_mode:
            # M4-A: Disable all operating-mode features.
            result[:, MODE_START_INDEX:] = 0.0

        if not np.isfinite(result).all():
            raise ValueError("M4 normalization produced non-finite values")

        return result

    def to_dict(self) -> dict:
        """Return serializable normalization parameters."""

        return {
            "sensor_normalizer": (self.sensor_normalizer.to_dict()),
            "time_mean": self.time_mean,
            "time_std": self.time_std,
        }
