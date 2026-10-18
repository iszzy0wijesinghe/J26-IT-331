"""Checkpoint-based inference for GeoNex C3 standard GRU models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch

from components.c3_forecasting.models.standard_gru import C3StandardGRU
from components.c3_forecasting.preprocessing.gru_dataset import (
    INPUT_FEATURE_COUNT,
    SENSOR_NAMES,
    extract_gru_sequence,
)
from components.c3_forecasting.preprocessing.gru_normalization import GRUNormalizer
from components.c3_forecasting.preprocessing.gru_target_normalization import (
    GRUTargetNormalizer,
)


class C3GRUPredictor:
    """Load a trained standard GRU and predict future soil moisture."""

    def __init__(
        self,
        checkpoint_path: str | Path,
        *,
        device: str = "cpu",
    ) -> None:
        checkpoint_path = Path(checkpoint_path)

        if not checkpoint_path.is_file():
            raise FileNotFoundError(f"GRU checkpoint not found: {checkpoint_path}")

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
            "horizon_minutes",
            "input_size",
            "hidden_size",
            "num_layers",
            "normalizer",
            "target_normalizer",
        }

        missing = required_keys - checkpoint.keys()

        if missing:
            raise ValueError(f"Checkpoint missing required fields: {sorted(missing)}")

        if checkpoint["input_size"] != INPUT_FEATURE_COUNT:
            raise ValueError("Checkpoint input size does not match current GRU features")

        normalizer_data = checkpoint["normalizer"]

        if tuple(normalizer_data["sensor_names"]) != SENSOR_NAMES:
            raise ValueError("Checkpoint sensor ordering does not match current features")

        means = np.asarray(
            normalizer_data["means"],
            dtype=np.float32,
        )

        stds = np.asarray(
            normalizer_data["stds"],
            dtype=np.float32,
        )

        sensor_count = len(SENSOR_NAMES)

        if means.shape != (sensor_count,) or stds.shape != (sensor_count,):
            raise ValueError("Invalid sensor normalization parameter shapes")

        if not np.isfinite(means).all() or not np.isfinite(stds).all():
            raise ValueError("Non-finite sensor normalization parameters")

        if np.any(stds <= 0):
            raise ValueError("Sensor standard deviations must be positive")

        self.sensor_normalizer = GRUNormalizer(
            means=means,
            stds=stds,
        )

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

        self.horizon_minutes = int(checkpoint["horizon_minutes"])

        if self.horizon_minutes not in {15, 30, 60}:
            raise ValueError("Unsupported checkpoint forecasting horizon")

        self.model = C3StandardGRU(
            input_size=int(checkpoint["input_size"]),
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
        Predict future soil moisture from an unnormalized GRU feature array.

        Expected shape:
            [timesteps, 14]

        Feature layout:
            7 sensor values followed by 7 validity masks.
        """

        if not isinstance(sequence, np.ndarray):
            raise TypeError("Sequence must be a NumPy array")

        if sequence.ndim != 2:
            raise ValueError("Sequence must be two-dimensional")

        if sequence.shape[0] == 0:
            raise ValueError("Sequence cannot be empty")

        if sequence.shape[1] != INPUT_FEATURE_COUNT:
            raise ValueError(f"Expected {INPUT_FEATURE_COUNT} features")

        if not np.isfinite(sequence).all():
            raise ValueError("Sequence contains non-finite values")

        normalized = self.sensor_normalizer.transform(sequence.astype(np.float32, copy=True))

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
            raise RuntimeError("GRU produced a non-finite prediction")

        return value

    def predict(self, temporal_sequence: dict[str, Any]) -> float:
        """
        Predict future soil moisture from a C3 temporal-sequence record.

        Uses the same extraction rules as GRU training.
        """

        sequence = extract_gru_sequence(temporal_sequence)

        return self.predict_array(sequence)
