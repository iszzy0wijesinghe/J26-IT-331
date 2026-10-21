"""
GeoNex C3 — M5 V3 Standalone Inference Service.

Loads the trained M5 multivariate GRU and its original
training scaler.

Produces seven-sensor forecasts at 15, 30 and 60 minutes.

Experimental synthetic-data research use only.
"""

from functools import lru_cache
from pathlib import Path

import numpy as np
import torch

from components.c3_forecasting.models.m5_multivariate_gru import (
    C3M5MultivariateGRU,
    SENSOR_FEATURES,
    FORECAST_HORIZONS,
    OPERATING_MODES,
)

from components.c3_forecasting.preprocessing.m5_features import (
    extract_m5_sequence,
)

from components.c3_forecasting.preprocessing.m5_scaler import (
    M5SensorScaler,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHECKPOINT_PATH = (
    PROJECT_ROOT
    / "artifacts"
    / "c3"
    / "experiments"
    / "m5_variable_rate_v3"
    / "m5_multivariate_gru.pt"
)


class M5InferenceError(ValueError):
    pass


@lru_cache(maxsize=1)
def load_m5_model():

    if not CHECKPOINT_PATH.exists():
        raise M5InferenceError(
            f"M5 checkpoint not found: {CHECKPOINT_PATH}"
        )

    checkpoint = torch.load(
        CHECKPOINT_PATH,
        map_location="cpu",
        weights_only=True,
    )

    # Validate checkpoint compatibility.
    if tuple(checkpoint["sensor_features"]) != tuple(
        SENSOR_FEATURES
    ):
        raise M5InferenceError(
            "Checkpoint sensor configuration mismatch"
        )

    if tuple(checkpoint["forecast_horizons"]) != tuple(
        FORECAST_HORIZONS
    ):
        raise M5InferenceError(
            "Checkpoint forecast horizon mismatch"
        )

    if tuple(checkpoint["operating_modes"]) != tuple(
        OPERATING_MODES
    ):
        raise M5InferenceError(
            "Checkpoint operating mode mismatch"
        )

    model = C3M5MultivariateGRU()

    model.load_state_dict(
        checkpoint["model_state_dict"]
    )

    model.eval()

    scaler = M5SensorScaler.from_dict(
        checkpoint["scaler"]
    )

    return model, scaler, checkpoint


def predict_m5(observations: list[dict]) -> dict:

    if not 3 <= len(observations) <= 32:
        raise M5InferenceError(
            "M5 requires between 3 and 32 observations"
        )

    model, scaler, checkpoint = load_m5_model()

    # Apply exactly the same feature extraction
    # used during training.
    features = extract_m5_sequence(
        observations
    )

    normalized_features = (
        scaler.transform_features(features)
    )

    tensor = torch.from_numpy(
        np.asarray(
            normalized_features,
            dtype=np.float32,
        )
    ).unsqueeze(0)

    lengths = torch.tensor(
        [len(observations)],
        dtype=torch.long,
    )

    with torch.inference_mode():

        normalized_predictions = model(
            tensor,
            lengths,
        )

    normalized_predictions = (
        normalized_predictions
        .squeeze(0)
        .cpu()
        .numpy()
    )

    predictions = scaler.inverse_transform_targets(
        normalized_predictions
    )

    results = []

    for horizon_index, horizon in enumerate(
        FORECAST_HORIZONS
    ):

        sensor_predictions = {}

        for sensor_index, sensor in enumerate(
            SENSOR_FEATURES
        ):

            sensor_predictions[sensor] = float(
                predictions[
                    horizon_index,
                    sensor_index,
                ]
            )

        results.append(
            {
                "horizon_minutes": horizon,
                "sensors": sensor_predictions,
            }
        )

    return {
        "model": "M5_V3_MULTIVARIATE_GRU",
        "model_version": checkpoint["model_version"],
        "sequence_length": len(observations),
        "sensor_features": list(SENSOR_FEATURES),
        "forecast_horizons": list(FORECAST_HORIZONS),
        "predictions": results,
        "dataset_type": "SYNTHETIC_ENGINEERING_SIMULATION",
        "research_status": "EXPERIMENTAL",
        "warning": (
            "Experimental sensor forecasting only. "
            "Not a validated landslide risk prediction "
            "or emergency warning system."
        ),
    }