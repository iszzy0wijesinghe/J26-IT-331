"""Train the C1 credibility model using XGBoost."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight

# Paths
DATASET_PATH = Path("data/synthetic/c1/C1_CREDIBILITY_V0.2.0/dataset.csv")
MODEL_DIR = Path("models/c1")
MODEL_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = MODEL_DIR / "c1_xgboost_v1.json"

# Target and Features
TARGET = "credibility_label"
CLASSES = ["CLEAN", "ANOMALY", "VALID_EVENT"]

# These are NOT features (metadata, leakage, etc.)
DROP_COLS = [
    "record_id", "observation_id", "scenario_id", "zone_id", "device_id",
    "sensor_instance_id", "observed_at", "source_origin", "test_run_id",
    "dataset_version", "credibility_label", "label_source", "event_id",
    "calibration_version", "context_status", "ambiguous", "ambiguity_reason",
    "borderline_extreme", "train_eligible", "split", "split_temporal",
    "split_device", "mode", "rainfall_regime", "scenario_type",
    # Leakage features (C2's job)
    "value_present", "obs_gap_steps", "recent_read_failures",
]

def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the dataset and split into train/val/test."""
    df = pd.read_csv(DATASET_PATH, low_memory=False)
    
    # Filter only eligible rows for training
    df = df[df["train_eligible"] == True]
    
    train = df[df["split"] == "train"].copy()
    val = df[df["split"] == "val"].copy()
    test = df[df["split"] == "test"].copy()
    
    print(f"Train: {len(train)} rows")
    print(f"Val: {len(val)} rows")
    print(f"Test: {len(test)} rows")
    
    return train, val, test

def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Separate features and target."""
    # Drop non-feature columns
    feature_cols = [c for c in df.columns if c not in DROP_COLS]
    
    X = df[feature_cols].copy()
    y = df[TARGET].copy()
    
    # Encode target to numeric
    label_map = {cls: i for i, cls in enumerate(CLASSES)}
    y_encoded = y.map(label_map)
    
    return X, y_encoded

def train_model(X_train, y_train, X_val, y_val):
    """Train XGBoost model with custom class weights."""
    # Manual class weights to boost ANOMALY detection
    # CLEAN=0, ANOMALY=1, VALID_EVENT=2
    weight_dict = {
        0: 1.0,      # CLEAN (majority, no boost needed)
        1: 10.0,     # ANOMALY (boost 10x to fix low recall)
        2: 2.0,      # VALID_EVENT (slight boost)
    }
    sample_weights = y_train.map(weight_dict)
    
    print(f"Class weights: {weight_dict}")
    
    # XGBoost parameters
    params = {
        "objective": "multi:softprob",
        "num_class": 3,
        "eval_metric": "mlogloss",
        "max_depth": 6,
        "learning_rate": 0.1,
        "n_estimators": 100,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "n_jobs": -1,
    }
    
    # Train
    model = xgb.XGBClassifier(**params)
    model.fit(
        X_train, y_train,
        sample_weight=sample_weights,
        eval_set=[(X_val, y_val)],
        verbose=True,
    )
    
    return model

def evaluate_model(model, X_test, y_test, model_name="Test"):
    """Evaluate model performance."""
    y_pred = model.predict(X_test)
    
    print(f"\n=== {model_name} Evaluation ===")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=CLASSES))
    
    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(pd.DataFrame(cm, index=CLASSES, columns=CLASSES).to_string())
    
    return y_pred

def main():
    """Main training function."""
    print("Loading data...")
    train, val, test = load_data()
    
    print("\nPreparing features...")
    X_train, y_train = prepare_features(train)
    X_val, y_val = prepare_features(val)
    X_test, y_test = prepare_features(test)
    
    print(f"\nFeature columns: {list(X_train.columns)}")
    print(f"Number of features: {len(X_train.columns)}")
    
    print("\nTraining model...")
    model = train_model(X_train, y_train, X_val, y_val)
    
    # Evaluate
    print("\nEvaluating on validation set...")
    evaluate_model(model, X_val, y_val, "Validation")
    
    print("\nEvaluating on test set...")
    evaluate_model(model, X_test, y_test, "Test")
    
    # Save model
    print(f"\nSaving model to {MODEL_PATH}...")
    model.save_model(MODEL_PATH)
    print("Model saved successfully!")

if __name__ == "__main__":
    main()