"""Train the C1 credibility model using XGBoost."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import classification_report, confusion_matrix, f1_score, recall_score

# Paths
DATASET_PATH = Path("data/synthetic/c1/C1_CREDIBILITY_V1_REALISTIC_4Y/c1_credibility_4y_V1.0.0.csv")
MODEL_DIR = Path("models/c1")
MODEL_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = MODEL_DIR / "c1_xgboost_v2_realistic.json"
MANIFEST_PATH = MODEL_DIR / "c1_xgboost_v2_realistic_manifest.json"
HISTORY_PATH = MODEL_DIR / "c1_xgboost_v2_training_history.json"

# Target
TARGET = "credibility_label"
CLASSES = ["CLEAN", "ANOMALY", "VALID_EVENT"]

# Explicit allowlist: the ONLY columns the model may use as features
# rainfall_regime removed from features because it is all NaN in the new dataset
FEATURES = [
    "value",
    "delta_prev_pct_per_min",
    "baseline_mean",
    "baseline_std",
    "value_minus_baseline",
    "stuck_run_len",
    "rain_15m_mm",
    "rain_1h_mm",
    "rain_3h_mm",
    "steps_since_rain",
    "n_neighbours_fresh",
    "neighbour_consensus_change",
    "target_minus_consensus",
    "neighbour_change_spread",
    "neighbour_rise_agree_frac",
    "device_voltage",
    "history_obs",
]

assert len(FEATURES) == 17, f"Expected 17 features, got {len(FEATURES)}"

def validate_dataset(df: pd.DataFrame) -> None:
    """Run integrity checks before training."""
    required = set(FEATURES) | {
        TARGET, "train_eligible", "split", "scenario_id", "observation_id"
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    df = df.dropna(subset=[TARGET])
    unexpected_labels = set(df[TARGET].unique()) - set(CLASSES)
    if unexpected_labels:
        raise ValueError(f"Unexpected labels: {unexpected_labels}")
    print(f"Rows with valid labels: {len(df)}")

    if df["split"].isna().any():
        raise ValueError("Missing split assignments")
    unexpected_splits = set(df["split"].unique()) - {"train", "val", "test"}
    if unexpected_splits:
        raise ValueError(f"Unexpected splits: {unexpected_splits}")

    crossings = df.groupby("scenario_id")["split"].nunique()
    crossing_scenarios = crossings[crossings > 1]
    if len(crossing_scenarios) > 0:
        print(f"WARNING: {len(crossing_scenarios)} scenarios cross splits. First 5: {list(crossing_scenarios.index[:5])}")

    if df["observation_id"].duplicated().any():
        print(f"WARNING: {df['observation_id'].duplicated().sum()} duplicate observation IDs found. Dropping duplicates.")
        df = df.drop_duplicates(subset=["observation_id"], keep="first")

    if not df["train_eligible"].isin([True, False, 0, 1]).all():
        raise ValueError("Unexpected train_eligible encoding")

    print("✓ Dataset validation passed")


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the dataset and split into train/val/test."""
    df = pd.read_csv(DATASET_PATH, low_memory=False)
    print(f"Total rows: {len(df)}")

    df = df.dropna(subset=[TARGET])
    print(f"After dropping rows with missing labels: {len(df)}")

    validate_dataset(df)

    print("\nEligibility filter impact per split:")
    for split in ["train", "val", "test"]:
        split_df = df[df["split"] == split]
        eligible = split_df[split_df["train_eligible"] == True]
        print(f"  {split}: {len(eligible)}/{len(split_df)} rows eligible")

    df = df[df["train_eligible"] == True]
    print(f"\nAfter eligibility filter: {len(df)} rows")

    train = df[df["split"] == "train"].copy()
    val = df[df["split"] == "val"].copy()
    test = df[df["split"] == "test"].copy()

    print(f"\nTrain: {len(train)} rows")
    print(f"Val: {len(val)} rows")
    print(f"Test: {len(test)} rows")

    for name, split_df in [("train", train), ("val", val), ("test", test)]:
        present = set(split_df[TARGET].unique())
        missing_classes = set(CLASSES) - present
        if missing_classes:
            print(f"WARNING: {name} split missing classes: {missing_classes}")

    return train, val, test


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Select only the allowed features and encode the target."""
    missing = [c for c in FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required features: {missing}")

    X = df[FEATURES].copy()

    label_map = {cls: i for i, cls in enumerate(CLASSES)}
    y = df[TARGET].map(label_map)

    if y.isna().any():
        raise ValueError("Target encoding produced NaN")

    return X, y


def train_model(X_train, y_train, X_val, y_val):
    """Train XGBoost model with custom class weights."""
    weight_dict = {0: 1.0, 1: 10.0, 2: 2.0}
    sample_weights = y_train.map(weight_dict)

    print(f"\nClass weights: {weight_dict}")
    print(f"Train class counts: {y_train.value_counts().to_dict()}")

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
        "early_stopping_rounds": 20,
    }

    model = xgb.XGBClassifier(**params)
    model.fit(
        X_train, y_train,
        sample_weight=sample_weights,
        eval_set=[(X_train, y_train), (X_val, y_val)], # Added train set for chart
        verbose=True,
    )

    # Save training history for the dashboard charts
    history = model.evals_result()
    HISTORY_PATH.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"\nTraining history saved to {HISTORY_PATH}")

    print(f"\nBest iteration: {model.best_iteration}")

    return model


def evaluate_model(model, X, y, model_name="Test"):
    """Evaluate model performance."""
    y_pred = model.predict(X)

    print(f"\n=== {model_name} Evaluation ===")
    print("\nClassification Report:")
    print(classification_report(
        y, y_pred,
        labels=list(range(len(CLASSES))),
        target_names=CLASSES,
        zero_division=0,
    ))

    print("\nConfusion Matrix:")
    cm = confusion_matrix(y, y_pred, labels=list(range(len(CLASSES))))
    print(pd.DataFrame(cm, index=CLASSES, columns=CLASSES).to_string())

    ve_to_anomaly = cm[2][1] / cm[2].sum() if cm[2].sum() > 0 else 0.0
    anomaly_to_ve = cm[1][2] / cm[1].sum() if cm[1].sum() > 0 else 0.0

    print(f"\nCritical errors:")
    print(f"  VALID_EVENT → ANOMALY: {ve_to_anomaly:.2%}")
    print(f"  ANOMALY → VALID_EVENT: {anomaly_to_ve:.2%}")

    # Return metrics for the manifest
    return {
        "macro_f1": f1_score(y, y_pred, average="macro", zero_division=0),
        "anomaly_recall": recall_score(y, y_pred, labels=[1], average=None, zero_division=0)[0],
        "valid_event_recall": recall_score(y, y_pred, labels=[2], average=None, zero_division=0)[0],
        "evaluated_on": f"{model_name.lower()} split, realistic 4-year synthetic"
    }


def save_manifest(model, X_train, y_train, metrics):
    """Save model manifest with feature list, mappings, and metadata."""
    manifest = {
        "model_version": "c1_xgboost_v2_realistic",
        "features": FEATURES,
        "n_features": len(FEATURES),
        "target_classes": CLASSES,
        "label_mapping": {cls: i for i, cls in enumerate(CLASSES)},
        "dataset_path": str(DATASET_PATH),
        "best_iteration": int(model.best_iteration),
        "train_size": len(X_train),
        "train_class_distribution": {CLASSES[i]: int(c) for i, c in enumerate(y_train.value_counts().sort_index())},
        "class_weights": {0: 1.0, 1: 10.0, 2: 2.0},
        "metrics": metrics
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest saved to {MANIFEST_PATH}")


def main():
    """Main training function."""
    print("Loading data...")
    train, val, test = load_data()

    print("\nPreparing features...")
    X_train, y_train = prepare_features(train)
    X_val, y_val = prepare_features(val)
    X_test, y_test = prepare_features(test)

    print(f"\nFeature count: {len(FEATURES)}")

    print("\nTraining model...")
    model = train_model(X_train, y_train, X_val, y_val)

    print("\nEvaluating on validation set...")
    evaluate_model(model, X_val, y_val, "Validation")

    print("\nEvaluating on test set...")
    test_metrics = evaluate_model(model, X_test, y_test, "Test")

    print(f"\nSaving model to {MODEL_PATH}...")
    model.save_model(MODEL_PATH)
    print("Model saved successfully!")

    save_manifest(model, X_train, y_train, test_metrics)


if __name__ == "__main__":
    main()