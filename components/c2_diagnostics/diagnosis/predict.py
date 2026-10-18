"""Prediction utilities for the C2 diagnostic model."""

from pathlib import Path

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "c2_diagnostics"
    / "random_forest.joblib"
)


def load_model(model_path: str | Path = MODEL_PATH):
    """Load a previously trained C2 model."""

    path = Path(model_path)

    if not path.is_file():
        raise FileNotFoundError(f"Trained model not found: {path}")

    return joblib.load(path)


def predict_diagnosis(
    features: pd.DataFrame,
    model=None,
) -> list[str]:
    """Predict diagnostic classes for the provided feature rows."""

    if features.empty:
        raise ValueError("Features cannot be empty.")

    if model is None:
        model = load_model()

    expected_features = list(model.feature_names_in_)
    missing_features = [
        feature
        for feature in expected_features
        if feature not in features.columns
    ]

    if missing_features:
        raise ValueError(
            f"Missing required features: {missing_features}"
        )

    # Keep the same feature order used during training.
    features = features[expected_features]

    predictions = model.predict(features)

    return [str(prediction) for prediction in predictions]