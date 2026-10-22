from pathlib import Path
import json
import time

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)


# ==========================================
# CONFIGURATION
# ==========================================

DATASET_PATH = Path(
    "data/c2_diagnostics/landslide_silence_dataset_20000.csv"
)

MODEL_DIR = Path("models/c2_diagnostics")
RESULTS_DIR = Path("results/c2_diagnostics")

MODEL_PATH = MODEL_DIR / "xgboost_baseline.joblib"
RESULTS_PATH = RESULTS_DIR / "xgboost_baseline_metrics.json"

TARGET_COLUMN = "Label"

RANDOM_STATE = 42
TEST_SIZE = 0.20


# ==========================================
# LOAD DATASET
# ==========================================

def load_dataset():

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH.resolve()}"
        )

    df = pd.read_csv(DATASET_PATH)

    print("\n========== DATASET INFORMATION ==========")

    print("Dataset shape:", df.shape)

    print("\nClass distribution:")

    print(df[TARGET_COLUMN].value_counts())

    return df


# ==========================================
# PREPARE FEATURES
# ==========================================

def prepare_data(df):

    if TARGET_COLUMN not in df.columns:
        raise ValueError("Label column not found.")

    if df[TARGET_COLUMN].isna().any():
        raise ValueError(
            "Missing target labels found. "
            "Investigate them before training."
        )

    # Exclude target and identifiers.
    X = df.drop(
        columns=["Label", "Event_ID", "Timestamp"],
        errors="ignore",
    ).copy()

    y = df["Label"].astype(str)

    # This baseline expects numeric features.
    non_numeric = X.select_dtypes(
        exclude=["number", "bool"]
    ).columns.tolist()

    if non_numeric:
        raise ValueError(
            f"Non-numeric features found: {non_numeric}"
        )

    # Replace infinite values with missing values.
    X = X.replace([np.inf, -np.inf], np.nan)

    print("\n========== FEATURE INFORMATION ==========")

    print("Number of features:", X.shape[1])

    print("Features:", X.columns.tolist())

    print("Missing feature values:", int(X.isna().sum().sum()))

    return X, y


# ==========================================
# SPLIT DATA
# ==========================================

def split_data(X, y):

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    print("\n========== DATA SPLIT ==========")

    print("Training samples:", len(X_train))

    print("Testing samples:", len(X_test))

    return X_train, X_test, y_train, y_test


# ==========================================
# TRAIN XGBOOST MODEL
# ==========================================

def train_model(X_train, y_train):

    label_encoder = LabelEncoder()

    y_train_encoded = label_encoder.fit_transform(y_train)

    model = xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=len(label_encoder.classes_),
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        eval_metric="mlogloss",
        tree_method="hist",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    print("\n========== TRAINING XGBOOST ==========")

    print("XGBoost version:", xgb.__version__)

    start_time = time.perf_counter()

    model.fit(X_train, y_train_encoded)

    training_seconds = time.perf_counter() - start_time

    print(
        f"Training completed in {training_seconds:.2f} seconds."
    )

    return model, label_encoder, training_seconds


# ==========================================
# EVALUATE MODEL
# ==========================================

def evaluate_model(model, label_encoder, X_test, y_test):

    y_test_encoded = label_encoder.transform(y_test)

    start_time = time.perf_counter()

    predictions_encoded = model.predict(X_test)

    prediction_seconds = time.perf_counter() - start_time

    y_pred = label_encoder.inverse_transform(
        predictions_encoded.astype(int)
    )

    labels = label_encoder.classes_.tolist()

    accuracy = accuracy_score(y_test, y_pred)

    macro_precision = precision_score(
        y_test,
        y_pred,
        average="macro",
        zero_division=0,
    )

    macro_recall = recall_score(
        y_test,
        y_pred,
        average="macro",
        zero_division=0,
    )

    macro_f1 = f1_score(
        y_test,
        y_pred,
        average="macro",
        zero_division=0,
    )

    weighted_f1 = f1_score(
        y_test,
        y_pred,
        average="weighted",
        zero_division=0,
    )

    print("\n========== EVALUATION RESULTS ==========")

    print(f"Accuracy:        {accuracy:.4f}")
    print(f"Macro Precision: {macro_precision:.4f}")
    print(f"Macro Recall:    {macro_recall:.4f}")
    print(f"Macro F1:        {macro_f1:.4f}")
    print(f"Weighted F1:     {weighted_f1:.4f}")

    print("\n========== CLASSIFICATION REPORT ==========")

    report = classification_report(
        y_test,
        y_pred,
        labels=labels,
        zero_division=0,
        output_dict=True,
    )

    print(
        classification_report(
            y_test,
            y_pred,
            labels=labels,
            zero_division=0,
        )
    )

    print("\n========== CONFUSION MATRIX ==========")

    cm = confusion_matrix(
        y_test,
        y_pred,
        labels=labels,
    )

    print("Class order:", labels)

    print(cm)

    metrics = {
        "model": "XGBoost",
        "xgboost_version": xgb.__version__,
        "accuracy": float(accuracy),
        "macro_precision": float(macro_precision),
        "macro_recall": float(macro_recall),
        "macro_f1": float(macro_f1),
        "weighted_f1": float(weighted_f1),
        "training_test_prediction_seconds": float(
            prediction_seconds
        ),
        "test_samples": int(len(y_test)),
        "class_labels": labels,
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "features": X_test.columns.tolist(),
        "split_method": "Stratified random 80/20 split",
    }

    return metrics


# ==========================================
# MAIN
# ==========================================

def main():

    df = load_dataset()

    X, y = prepare_data(df)

    X_train, X_test, y_train, y_test = split_data(X, y)

    model, label_encoder, training_seconds = train_model(
        X_train,
        y_train,
    )

    metrics = evaluate_model(
        model,
        label_encoder,
        X_test,
        y_test,
    )

    metrics["training_seconds"] = float(training_seconds)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    artifact = {
        "model": model,
        "label_encoder": label_encoder,
        "feature_names": X.columns.tolist(),
        "model_type": "XGBoost",
    }

    joblib.dump(artifact, MODEL_PATH)

    with RESULTS_PATH.open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)

    print("\n========== SAVED FILES ==========")

    print("Model:", MODEL_PATH.resolve())

    print("Metrics:", RESULTS_PATH.resolve())

    print("\nXGBoost training completed successfully!")


if __name__ == "__main__":
    main()