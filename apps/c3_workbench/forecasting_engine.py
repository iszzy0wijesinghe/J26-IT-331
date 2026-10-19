"""GeoNex C3 active-model forecasting engine.

Generates fixed-horizon soil-moisture forecasts from Golden Database
historical observations.

Research safeguards:
- Uses the active model assigned to each forecast horizon.
- Reuses training-compatible feature construction.
- Verifies dataset approval and training artifact integrity.
- Verifies the selected checkpoint against registered artifacts.
- Never uses future observations as forecasting inputs.
- Does not modify active models or retrain anything.
- Clearly identifies Golden CSV provenance limitations.
- Does not claim landslide-event prediction.
"""

from __future__ import annotations

import hashlib
import math

from datetime import timedelta
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from apps.c3_workbench.forecasting_adapter import (
    prepare_forecasting_inputs,
)
from apps.c3_workbench.forecasting_reader import (
    parse_timestamp,
)
from apps.c3_workbench.model_activation import (
    list_active_model_assignments,
)
from apps.c3_workbench.model_registry import (
    collect_model_candidates,
)
from apps.c3_workbench.training_artifact_integrity import (
    verify_training_artifacts,
)

from components.c3_forecasting.inference.m4_predictor import (
    C3M4Predictor,
)


HORIZONS = (15, 30, 60)

MODEL_FEATURE_KEYS = {
    "M4_A_GRU": "m4_a_features",
    "M4_B_GRU": "m4_b_features",
    "M4_C_GRU": "m4_c_features",
}


class ForecastingEngineError(RuntimeError):
    """Raised when forecasting cannot be performed safely."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def verify_active_checkpoint(
    assignment: dict[str, Any],
) -> Path:
    """Verify an active checkpoint against registered model artifacts."""

    dataset_id = assignment["dataset_id"]
    job_id = assignment["job_id"]

    verify_training_artifacts(dataset_id)

    candidates = collect_model_candidates(
        job_id,
        dataset_id,
    )

    matching = [
        candidate
        for candidate in candidates
        if (
            candidate["model_name"] == assignment["model_name"]
            and candidate["horizon_minutes"]
            == assignment["horizon_minutes"]
        )
    ]

    if len(matching) != 1:
        raise ForecastingEngineError(
            "Unable to identify the registered model artifact."
        )

    candidate = matching[0]

    checkpoint = Path(
        assignment["checkpoint_path"]
    ).resolve()

    registered_path = Path(
        candidate["checkpoint_path"]
    ).resolve()

    if checkpoint != registered_path:
        raise ForecastingEngineError(
            "Active checkpoint path does not match the registered artifact."
        )

    if not checkpoint.is_file():
        raise ForecastingEngineError(
            "Active checkpoint file is missing."
        )

    if checkpoint.stat().st_size == 0:
        raise ForecastingEngineError(
            "Active checkpoint is empty."
        )

    # The candidate collector derives its checksum from the
    # current artifact. This detects inconsistencies during
    # execution but is not a substitute for an immutable,
    # independently stored trusted checkpoint hash.
    current_hash = sha256_file(checkpoint)

    if current_hash != candidate["checkpoint_sha256"]:
        raise ForecastingEngineError(
            "Checkpoint checksum mismatch."
        )

    return checkpoint


def predict_ridge(
    checkpoint_path: Path,
    inputs: dict[str, Any],
    expected_horizon: int,
) -> float:
    """Predict with the fitted M1 Ridge pipeline."""

    checkpoint = joblib.load(checkpoint_path)

    if checkpoint.get("horizon_minutes") != expected_horizon:
        raise ForecastingEngineError(
            "Ridge checkpoint horizon mismatch."
        )

    if checkpoint.get("target_feature") != "soil_moisture_pct":
        raise ForecastingEngineError(
            "Unexpected Ridge prediction target."
        )

    feature_names = tuple(
        checkpoint["feature_names"]
    )

    available_features = inputs["tabular_features"]

    if len(feature_names) != 79:
        raise ForecastingEngineError(
            "Unexpected Ridge feature count."
        )

    if set(feature_names) != set(available_features):
        raise ForecastingEngineError(
            "Ridge feature schema mismatch."
        )

    vector = np.asarray(
        [
            available_features[name]
            for name in feature_names
        ],
        dtype=np.float64,
    ).reshape(1, -1)

    if not np.isfinite(vector).all():
        raise ForecastingEngineError(
            "Non-finite Ridge input features."
        )

    prediction = checkpoint["model"].predict(vector)

    return float(prediction[0])


def predict_m4(
    checkpoint_path: Path,
    inputs: dict[str, Any],
    model_name: str,
    expected_horizon: int,
) -> float:
    """Predict using the correct M4 ablation feature array."""

    predictor = C3M4Predictor(
        checkpoint_path,
        device="cpu",
    )

    expected_ablation = model_name.split("_")[1]

    if predictor.ablation != expected_ablation:
        raise ForecastingEngineError(
            "M4 checkpoint ablation mismatch."
        )

    if predictor.horizon_minutes != expected_horizon:
        raise ForecastingEngineError(
            "M4 checkpoint horizon mismatch."
        )

    feature_key = MODEL_FEATURE_KEYS[model_name]

    return predictor.predict_array(
        inputs[feature_key]
    )


def generate_active_forecasts(
    *,
    dataset_id: str,
    device_id: str,
    episode_id: str,
    forecast_origin: str,
) -> dict[str, Any]:
    """Generate 15/30/60-minute forecasts using active models."""

    inputs = prepare_forecasting_inputs(
        dataset_id=dataset_id,
        device_id=device_id,
        episode_id=episode_id,
        forecast_origin=forecast_origin,
    )

    assignments = {
        assignment["horizon_minutes"]: assignment
        for assignment in list_active_model_assignments()
    }

    if set(assignments) != set(HORIZONS):
        raise ForecastingEngineError(
            "Exactly one active model is required for each horizon."
        )

    origin = parse_timestamp(
        inputs["forecast_origin"]
    )

    predictions = []

    for horizon in HORIZONS:
        assignment = assignments[horizon]

        if assignment["dataset_id"] != dataset_id:
            raise ForecastingEngineError(
                "Active model dataset does not match the forecasting dataset."
            )

        checkpoint = verify_active_checkpoint(
            assignment
        )

        model_name = assignment["model_name"]

        if model_name == "M1_RIDGE":
            predicted_value = predict_ridge(
                checkpoint,
                inputs,
                horizon,
            )

        elif model_name in MODEL_FEATURE_KEYS:
            predicted_value = predict_m4(
                checkpoint,
                inputs,
                model_name,
                horizon,
            )

        else:
            raise ForecastingEngineError(
                f"Unsupported active model: {model_name}"
            )

        if not math.isfinite(predicted_value):
            raise ForecastingEngineError(
                "Model produced a non-finite prediction."
            )

        target_time = origin + timedelta(
            minutes=horizon
        )

        predictions.append(
            {
                "horizon_minutes": horizon,
                "model_version_id": assignment["model_version_id"],
                "model_name": model_name,
                "checkpoint_sha256": sha256_file(checkpoint),
                "target_timestamp": target_time.isoformat(),
                "predicted_soil_moisture_pct": predicted_value,
                "validation_mae": assignment["validation_mae"],
                "validation_rmse": assignment["validation_rmse"],
            }
        )

    return {
        "dataset_id": dataset_id,
        "device_id": device_id,
        "episode_id": episode_id,
        "forecast_origin": inputs["forecast_origin"],
        "forecast_type": "HISTORICAL_REPLAY",
        "source_origin": "GOLDEN_CSV",
        "source_provenance_verified": False,
        "receipt_time_basis": (
            "ASSUMED_EQUAL_TO_OBSERVATION_TIME"
        ),
        "target_feature": "soil_moisture_pct",
        "sequence_length": inputs["sequence_length"],
        "input_window_start": inputs["window_start"],
        "input_window_end": inputs["window_end"],
        "predictions": predictions,
        "limitations": [
            "Synthetic research dataset",
            "Not validated against field landslide events",
            "Golden CSV does not preserve verified sensor receipt times",
            "Forecasts are sensor-value estimates, not landslide probabilities",
        ],
    }