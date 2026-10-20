"""Checkpoint-based inference for GeoNex C3 M4 GRU forecasting."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch

from components.c3_forecasting.models.standard_gru import C3StandardGRU
from components.c3_forecasting.preprocessing.gru_dataset import SENSOR_NAMES
from components.c3_forecasting.preprocessing.gru_normalization import GRUNormalizer
from components.c3_forecasting.preprocessing.gru_target_normalization import (
    GRUTargetNormalizer,
)
from components.c3_forecasting.preprocessing.m4_features import (
    M4_INPUT_FEATURE_COUNT,
    extract_m4_sequence,
)
from components.c3_forecasting.preprocessing.m4_normalization import M4Normalizer

ABLATIONS = {
    "A": (True, False),
    "B": (False, True),
    "C": (True, True),
}

VALID_HORIZONS = frozenset({15, 30, 60})


class C3M4Predictor:
    """Predict future soil moisture using a trained M4 GRU checkpoint."""

    def __init__(
        self,
        checkpoint_path: str | Path,
        *,
        device: str = "cpu",
    ) -> None:
        checkpoint_path = Path(checkpoint_path)

        if not checkpoint_path.is_file():
            raise FileNotFoundError(f"M4 checkpoint not found: {checkpoint_path}")

        if device not in {"cpu", "mps"}:
            raise ValueError("Device must be 'cpu' or 'mps'")

        if device == "mps" and not torch.backends.mps.is_available():
            raise RuntimeError("MPS is unavailable")

        self.device = torch.device(device)

        checkpoint = torch.load(
            checkpoint_path,
            map_location="cpu",
            weights_only=True,
        )

        required_keys = {
            "model_state_dict",
            "model",
            "ablation",
            "include_time",
            "include_mode",
            "horizon_minutes",
            "input_size",
            "hidden_size",
            "num_layers",
            "normalizer",
            "target_normalizer",
        }

        missing = required_keys - checkpoint.keys()

        if missing:
            raise ValueError(f"M4 checkpoint missing fields: {sorted(missing)}")

        if checkpoint["model"] != "m4_gru":
            raise ValueError("Checkpoint is not an M4 GRU model")

        self.ablation = checkpoint["ablation"]

        if self.ablation not in ABLATIONS:
            raise ValueError("Unsupported M4 ablation")

        expected_time, expected_mode = ABLATIONS[self.ablation]

        if (
            type(checkpoint["include_time"]) is not bool
            or type(checkpoint["include_mode"]) is not bool
            or checkpoint["include_time"] != expected_time
            or checkpoint["include_mode"] != expected_mode
        ):
            raise ValueError("Checkpoint feature flags do not match its ablation")

        self.include_time = expected_time
        self.include_mode = expected_mode

        self.horizon_minutes = checkpoint["horizon_minutes"]

        if type(self.horizon_minutes) is not int or self.horizon_minutes not in VALID_HORIZONS:
            raise ValueError("Unsupported forecasting horizon")

        if checkpoint["input_size"] != M4_INPUT_FEATURE_COUNT:
            raise ValueError("Checkpoint input size does not match M4 features")

        # ----------------------------------------------------
        # Restore sensor normalization.
        # ----------------------------------------------------

        normalizer_data = checkpoint["normalizer"]

        sensor_data = normalizer_data["sensor_normalizer"]

        if tuple(sensor_data["sensor_names"]) != SENSOR_NAMES:
            raise ValueError("Checkpoint sensor ordering does not match M4 features")

        means = np.asarray(
            sensor_data["means"],
            dtype=np.float32,
        )

        stds = np.asarray(
            sensor_data["stds"],
            dtype=np.float32,
        )

        sensor_count = len(SENSOR_NAMES)

        if means.shape != (sensor_count,) or stds.shape != (sensor_count,):
            raise ValueError("Invalid sensor normalization shapes")

        if not np.isfinite(means).all() or not np.isfinite(stds).all():
            raise ValueError("Non-finite sensor normalization parameters")

        if np.any(stds <= 0):
            raise ValueError("Sensor standard deviations must be positive")

        sensor_normalizer = GRUNormalizer(
            means=means,
            stds=stds,
        )

        # ----------------------------------------------------
        # Restore elapsed-time normalization.
        # ----------------------------------------------------

        time_mean = float(normalizer_data["time_mean"])
        time_std = float(normalizer_data["time_std"])

        if not np.isfinite(time_mean) or not np.isfinite(time_std):
            raise ValueError("Non-finite time normalization parameters")

        if time_std <= 0:
            raise ValueError("Time standard deviation must be positive")

        self.normalizer = M4Normalizer(
            sensor_normalizer=sensor_normalizer,
            time_mean=time_mean,
            time_std=time_std,
        )

        # ----------------------------------------------------
        # Restore target normalization.
        # ----------------------------------------------------

        target_data = checkpoint["target_normalizer"]

        target_mean = float(target_data["mean"])
        target_std = float(target_data["std"])

        if not np.isfinite(target_mean) or not np.isfinite(target_std):
            raise ValueError("Non-finite target normalization parameters")

        if target_std <= 0:
            raise ValueError("Target standard deviation must be positive")

        self.target_normalizer = GRUTargetNormalizer(
            mean=target_mean,
            std=target_std,
        )

        # ----------------------------------------------------
        # Restore GRU model.
        # ----------------------------------------------------

        self.model = C3StandardGRU(
            input_size=M4_INPUT_FEATURE_COUNT,
            hidden_size=int(checkpoint["hidden_size"]),
            num_layers=int(checkpoint["num_layers"]),
        )

        self.model.load_state_dict(
            checkpoint["model_state_dict"],
            strict=True,
        )

        self.model.to(self.device)
        self.model.eval()

    @torch.inference_mode()
    def predict_array(self, sequence: np.ndarray) -> float:
        """
        Predict future soil moisture from an unnormalized M4 feature array.

        Expected shape:
            [timesteps, 20]

        Features:
            0:7   Sensor values
            7:14  Sensor validity masks
            14    Log-transformed elapsed time
            15    Interval-known indicator
            16:20 Operating-mode one-hot encoding
        """

        if not isinstance(sequence, np.ndarray):
            raise TypeError("Sequence must be a NumPy array")

        if sequence.ndim != 2:
            raise ValueError("Sequence must be two-dimensional")

        if sequence.shape[0] == 0:
            raise ValueError("Sequence cannot be empty")

        if sequence.shape[1] != M4_INPUT_FEATURE_COUNT:
            raise ValueError(f"Expected {M4_INPUT_FEATURE_COUNT} input features")

        if not np.isfinite(sequence).all():
            raise ValueError("Sequence contains non-finite values")

        normalized = self.normalizer.transform(
            sequence.astype(np.float32, copy=True),
            include_time=self.include_time,
            include_mode=self.include_mode,
        )

        inputs = torch.as_tensor(
            normalized,
            dtype=torch.float32,
            device=self.device,
        ).unsqueeze(0)

        lengths = torch.tensor(
            [normalized.shape[0]],
            dtype=torch.long,
        )

        normalized_prediction = self.model(
            inputs,
            lengths,
        )

        prediction = self.target_normalizer.denormalize(normalized_prediction)

        value = float(prediction.item())

        if not np.isfinite(value):
            raise RuntimeError("M4 GRU produced a non-finite prediction")

        return value

    def predict(self, temporal_sequence: dict[str, Any]) -> float:
        """Predict from a raw C3 temporal-sequence record."""

        sequence = extract_m4_sequence(
            temporal_sequence,
            include_time=True,
            include_mode=True,
        )

        return self.predict_array(sequence)
