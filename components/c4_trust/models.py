from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.preprocessing import LabelEncoder, StandardScaler


class ModelType(str, Enum):
    """Supported model types."""

    LOGISTIC_REGRESSION = "logistic_regression"
    RANDOM_FOREST = "random_forest"
    ISOLATION_FOREST = "isolation_forest"
    XGBOOST = "xgboost"  # To be implemented


@dataclass
class ModelMetrics:
    """Model evaluation metrics."""

    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    precision_per_class: dict[str, float]
    recall_per_class: dict[str, float]
    f1_per_class: dict[str, float]
    confusion_matrix: np.ndarray

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "accuracy": self.accuracy,
            "precision_macro": self.precision_macro,
            "recall_macro": self.recall_macro,
            "f1_macro": self.f1_macro,
            "precision_per_class": self.precision_per_class,
            "recall_per_class": self.recall_per_class,
            "f1_per_class": self.f1_per_class,
            "confusion_matrix": self.confusion_matrix.tolist(),
        }


@dataclass
class TrainedModel:
    """Container for trained model and preprocessing."""

    model: Any
    scaler: StandardScaler | None
    label_encoder: LabelEncoder
    model_type: ModelType
    feature_names: list[str]
    metrics: ModelMetrics | None = None
    training_metadata: dict[str, Any] = field(default_factory=dict)

    def save(self, path: Path) -> None:
        """Save model to disk.

        Args:
            path: Path to save model
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        joblib.dump(self, path)
        print(f"Model saved to {path}")

    @classmethod
    def load(cls, path: Path) -> TrainedModel:
        """Load model from disk.

        Args:
            path: Path to load model from

        Returns:
            TrainedModel instance
        """
        return joblib.load(path)


class BaselineModel:
    """Baseline models for C4 behavioral classification."""

    def __init__(
        self,
        model_type: ModelType = ModelType.LOGISTIC_REGRESSION,
        random_state: int = 42,
    ) -> None:
        """Initialize baseline model.

        Args:
            model_type: Type of model to use
            random_state: Random seed for reproducibility
        """
        self.model_type = model_type
        self.random_state = random_state
        self.model: Any = None
        self.scaler: StandardScaler | None = None
        self.label_encoder: LabelEncoder = LabelEncoder()
        self.feature_names: list[str] = []

        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the underlying model."""
        if self.model_type == ModelType.LOGISTIC_REGRESSION:
            self.model = LogisticRegression(
                random_state=self.random_state,
                max_iter=1000,
            )
            self.scaler = StandardScaler()
        elif self.model_type == ModelType.RANDOM_FOREST:
            self.model = RandomForestClassifier(
                n_estimators=100,
                random_state=self.random_state,
                n_jobs=-1,
            )
            self.scaler = None
        elif self.model_type == ModelType.ISOLATION_FOREST:
            self.model = IsolationForest(
                n_estimators=100,
                random_state=self.random_state,
                contamination=0.1,
            )
            self.scaler = None
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,
        y_val: pd.Series | None = None,
    ) -> TrainedModel:
        """Train the model.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features (optional)
            y_val: Validation labels (optional)

        Returns:
            TrainedModel instance
        """
        self.feature_names = list(X_train.columns)

        # Encode labels
        y_train_encoded = self.label_encoder.fit_transform(y_train)

        # Scale features if needed
        if self.scaler is not None:
            X_train_scaled = self.scaler.fit_transform(X_train)
        else:
            X_train_scaled = X_train.values

        # Train model
        if self.model_type == ModelType.ISOLATION_FOREST:
            # Isolation Forest is unsupervised, fit on features only
            self.model.fit(X_train_scaled)
            # Predictions: -1 (anomaly) or 1 (normal)
            # Map to labels: -1 -> Untrusted/Suspicious, 1 -> Trusted
        else:
            self.model.fit(X_train_scaled, y_train_encoded)

        # Evaluate on validation set if provided
        metrics = None
        if X_val is not None and y_val is not None:
            metrics = self.evaluate(X_val, y_val)

        # Create trained model container
        trained = TrainedModel(
            model=self.model,
            scaler=self.scaler,
            label_encoder=self.label_encoder,
            model_type=self.model_type,
            feature_names=self.feature_names,
            metrics=metrics,
            training_metadata={
                "random_state": self.random_state,
                "n_train_samples": len(X_train),
                "n_features": len(self.feature_names),
            },
        )

        return trained

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions.

        Args:
            X: Features

        Returns:
            Predicted labels
        """
        if self.scaler is not None:
            X_scaled = self.scaler.transform(X)
        else:
            X_scaled = X.values

        if self.model_type == ModelType.ISOLATION_FOREST:
            # Isolation Forest returns -1 (anomaly) or 1 (normal)
            predictions = self.model.predict(X_scaled)
            # Map: 1 -> Trusted (label 0), -1 -> Untrusted (label 1)
            # This is a simplification; in practice, map based on anomaly score
            encoded_pred = np.where(predictions == 1, 0, 1)
        else:
            encoded_pred = self.model.predict(X_scaled)

        # Decode labels
        labels = self.label_encoder.inverse_transform(encoded_pred)
        return labels

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Get prediction probabilities.

        Args:
            X: Features

        Returns:
            Prediction probabilities
        """
        if self.model_type == ModelType.ISOLATION_FOREST:
            # Isolation Forest has anomaly scores, not probabilities
            # Return dummy probabilities for now
            predictions = self.predict(X)
            n_classes = len(self.label_encoder.classes_)
            proba = np.zeros((len(X), n_classes))
            for i, pred in enumerate(predictions):
                idx = np.where(self.label_encoder.classes_ == pred)[0][0]
                proba[i, idx] = 1.0
            return proba
        else:
            if self.scaler is not None:
                X_scaled = self.scaler.transform(X)
            else:
                X_scaled = X.values

            return self.model.predict_proba(X_scaled)

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> ModelMetrics:
        """Evaluate model on dataset.

        Args:
            X: Features
            y: True labels

        Returns:
            ModelMetrics
        """
        y_pred = self.predict(X)

        # Compute metrics
        accuracy = (y_pred == y).mean()

        precision, recall, f1, support = precision_recall_fscore_support(
            y, y_pred, average=None, zero_division=0
        )

        precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
            y, y_pred, average="macro", zero_division=0
        )

        # Per-class metrics
        classes = self.label_encoder.classes_
        precision_per_class = {cls: prec for cls, prec in zip(classes, precision)}
        recall_per_class = {cls: rec for cls, rec in zip(classes, recall)}
        f1_per_class = {cls: f for cls, f in zip(classes, f1)}

        # Confusion matrix
        cm = confusion_matrix(y, y_pred, labels=classes)

        return ModelMetrics(
            accuracy=accuracy,
            precision_macro=precision_macro,
            recall_macro=recall_macro,
            f1_macro=f1_macro,
            precision_per_class=precision_per_class,
            recall_per_class=recall_per_class,
            f1_per_class=f1_per_class,
            confusion_matrix=cm,
        )

    def get_feature_importance(self) -> dict[str, float] | None:
        """Get feature importance if available.

        Returns:
            Dictionary of feature names to importance scores, or None
        """
        if self.model_type == ModelType.RANDOM_FOREST:
            importances = self.model.feature_importances_
            return dict(zip(self.feature_names, importances))
        elif self.model_type == ModelType.LOGISTIC_REGRESSION:
            # For multi-class, get mean absolute coefficient across classes
            coef = np.abs(self.model.coef_)
            if coef.ndim > 1:
                importances = coef.mean(axis=0)
            else:
                importances = coef
            return dict(zip(self.feature_names, importances))
        else:
            return None


def train_baseline_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    model_type: ModelType = ModelType.LOGISTIC_REGRESSION,
    output_path: Path | None = None,
) -> TrainedModel:
    """Train a baseline model.

    Args:
        X_train: Training features
        y_train: Training labels
        X_val: Validation features
        y_val: Validation labels
        model_type: Type of model to train
        output_path: Path to save model (optional)

    Returns:
        TrainedModel instance
    """
    print(f"Training {model_type.value} model...")

    model = BaselineModel(model_type=model_type)
    trained = model.fit(X_train, y_train, X_val, y_val)

    if trained.metrics:
        print("\nValidation Metrics:")
        print(f"  Accuracy: {trained.metrics.accuracy:.4f}")
        print(f"  Macro F1: {trained.metrics.f1_macro:.4f}")
        print("\nPer-class F1:")
        for cls, f1 in trained.metrics.f1_per_class.items():
            print(f"  {cls}: {f1:.4f}")

    if output_path:
        trained.save(output_path)

    return trained
