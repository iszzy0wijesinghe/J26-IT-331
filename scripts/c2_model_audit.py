"""
GeoNex C2 Diagnostic Model Audit
=================================

Purpose:
    Inspect the existing trained model and dataset to determine
    whether further tuning or retraining may be necessary.

Safety:
    - Does not retrain the model.
    - Does not overwrite the model artifact.
    - Does not modify the dataset.
    - Reports metrics and potential issues for further investigation.

Run from the GeoNex repository root:
    python scripts/c2_model_audit.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


# ============================================================
# 1. CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = ROOT / "models" / "c2_diagnostics" / "random_forest.joblib"

DATASET_PATH = (
    ROOT
    / "data"
    / "c2_diagnostics"
    / "landslide_silence_dataset_20000.csv"
)

TARGET_COLUMN = "Label"

ID_COLUMNS = ["Event_ID", "Timestamp"]

RANDOM_STATE = 42
TEST_SIZE = 0.20


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def section(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def stop(message: str) -> None:
    print(f"\nERROR: {message}")
    sys.exit(1)


def print_metric(name: str, value: float) -> None:
    print(f"{name:<28}: {value:.4f} ({value * 100:.2f}%)")


# ============================================================
# 3. LOAD EXISTING MODEL
# ============================================================

section("1. EXISTING MODEL")

if not MODEL_PATH.exists():
    stop(f"Model artifact not found: {MODEL_PATH}")

print(f"Model path: {MODEL_PATH}")

try:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model = joblib.load(MODEL_PATH)

    for warning in caught:
        print(f"Model loading warning: {warning.message}")

except Exception as exc:
    stop(f"Could not load model: {exc}")

print(f"Model object: {type(model).__name__}")

if not hasattr(model, "predict"):
    stop("Loaded artifact does not expose a predict() method.")

if not hasattr(model, "feature_names_in_"):
    stop(
        "Model does not expose feature_names_in_. "
        "Inspect the training pipeline before continuing."
    )

model_features = list(model.feature_names_in_)
model_classes = [str(value) for value in model.classes_]

print(f"Expected input features: {len(model_features)}")
print(f"Model classes: {model_classes}")

if isinstance(model, Pipeline):
    print("Pipeline steps:")

    for name, step in model.steps:
        print(f"  - {name}: {type(step).__name__}")


# ============================================================
# 4. LOAD EXISTING DATASET
# ============================================================

section("2. DATASET INTEGRITY")

if not DATASET_PATH.exists():
    stop(f"Dataset not found: {DATASET_PATH}")

print(f"Dataset path: {DATASET_PATH}")

try:
    df = pd.read_csv(DATASET_PATH)
except Exception as exc:
    stop(f"Could not read dataset: {exc}")

print(f"Dataset shape: {df.shape}")
print(f"Total records: {len(df):,}")
print(f"Total columns: {len(df.columns)}")

if TARGET_COLUMN not in df.columns:
    stop(f"Target column '{TARGET_COLUMN}' is missing.")

print("\nColumn names:")
print(list(df.columns))

print("\nMissing values per column:")

missing = df.isna().sum()
missing = missing[missing > 0]

if missing.empty:
    print("No missing values detected.")
else:
    print(missing.to_string())

print("\nDuplicate records:", int(df.duplicated().sum()))

print("\nTarget distribution:")

class_counts = df[TARGET_COLUMN].value_counts(dropna=False)
class_percentages = df[TARGET_COLUMN].value_counts(
    normalize=True,
    dropna=False,
) * 100

for label, count in class_counts.items():
    percentage = class_percentages[label]
    print(f"  {label}: {count:,} ({percentage:.2f}%)")

if df[TARGET_COLUMN].isna().any():
    stop("Target column contains missing labels.")

dataset_classes = set(df[TARGET_COLUMN].astype(str))
expected_classes = set(model_classes)

print("\nModel/dataset class compatibility:")

print("Model classes:", sorted(expected_classes))
print("Dataset classes:", sorted(dataset_classes))

if dataset_classes != expected_classes:
    print(
        "WARNING: Dataset and model classes differ. "
        "Investigate before interpreting evaluation results."
    )


# ============================================================
# 5. PREPARE MODEL INPUTS
# ============================================================

section("3. FEATURE SCHEMA")

missing_features = [
    feature
    for feature in model_features
    if feature not in df.columns
]

if missing_features:
    stop(f"Dataset is missing model features: {missing_features}")

X = df[model_features].copy()
y = df[TARGET_COLUMN].astype(str).copy()

non_numeric = X.select_dtypes(exclude=[np.number]).columns.tolist()

if non_numeric:
    stop(f"Non-numeric model features detected: {non_numeric}")

# The existing model includes a SimpleImputer, so missing feature values
# are allowed here and will be handled when model.predict() is called.
missing_cells = int(X.isna().sum().sum())
total_cells = int(X.shape[0] * X.shape[1])

print(f"Missing feature cells: {missing_cells:,}")
print(f"Total feature cells: {total_cells:,}")
print(
    f"Missing feature percentage: "
    f"{(missing_cells / total_cells * 100):.2f}%"
)

if missing_cells:
    print(
        "NOTE: Missing values detected. "
        "The existing model pipeline contains a SimpleImputer."
    )

if np.isinf(X.to_numpy(dtype=float, na_value=np.nan)).any():
    stop(
        "Model features contain infinite values. "
        "Inspect the dataset before evaluation."
    )

print("Feature validation completed.")
print(f"Feature columns used: {len(model_features)}")
print("Feature schema matches the trained model.")

print("\nFeature value summary:")
print(X.describe().round(3).to_string())


# ============================================================
# 6. CHECK POSSIBLE DIRECT LABEL LEAKAGE
# ============================================================

section("4. BASIC LEAKAGE SCREEN")

print(
    "This is a preliminary screen, not proof that the dataset "
    "is free of leakage."
)

print("\nID/time columns excluded from model input when present:")

for column in ID_COLUMNS:
    if column in df.columns:
        print(f"  - {column}")

print("\nFeatures with unique values equal to the number of rows:")

possible_identifiers = [
    column
    for column in X.columns
    if X[column].nunique(dropna=False) == len(X)
]

if possible_identifiers:
    for column in possible_identifiers:
        print(f"  WARNING: {column}")
else:
    print("None detected by this simple check.")

print("\nFeatures that exactly match the label encoding:")

for feature in X.columns:
    if X[feature].nunique(dropna=False) > 100:
        continue

    try:
        feature_as_string = X[feature].astype(str)

        if feature_as_string.equals(y):
            print(f"  WARNING: {feature} matches target labels.")

    except Exception:
        pass

print(
    "\nIMPORTANT: Review feature definitions and the dataset generator. "
    "A feature can leak the label without exactly matching it."
)


# ============================================================
# 7. EVALUATE ON A STRATIFIED HOLDOUT
# ============================================================

section("5. STRATIFIED HOLDOUT EVALUATION")

print(
    "This evaluation uses a random stratified split for an initial "
    "diagnostic check. It is not necessarily an independent-event test."
)

try:
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

except ValueError as exc:
    stop(f"Could not create stratified holdout: {exc}")

print(f"Training records: {len(X_train):,}")
print(f"Testing records: {len(X_test):,}")

print("\nTraining class counts:")
print(y_train.value_counts().to_string())

print("\nTesting class counts:")
print(y_test.value_counts().to_string())

try:
    # Evaluate the existing trained artifact without fitting or modifying it.
    y_pred = model.predict(X_test)

except Exception as exc:
    stop(f"Prediction failed: {exc}")

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

print("\nOVERALL METRICS")

print_metric("Accuracy", accuracy)
print_metric("Macro precision", macro_precision)
print_metric("Macro recall", macro_recall)
print_metric("Macro F1-score", macro_f1)
print_metric("Weighted F1-score", weighted_f1)

print("\nCLASSIFICATION REPORT")

print(
    classification_report(
        y_test,
        y_pred,
        labels=model_classes,
        zero_division=0,
        digits=4,
    )
)

print("\nCONFUSION MATRIX")

matrix = confusion_matrix(
    y_test,
    y_pred,
    labels=model_classes,
)

print("Class order:", model_classes)
print(pd.DataFrame(
    matrix,
    index=[f"Actual: {name}" for name in model_classes],
    columns=[f"Predicted: {name}" for name in model_classes],
).to_string())


# ============================================================
# 8. RANDOM FOREST FEATURE IMPORTANCE
# ============================================================

section("6. FEATURE IMPORTANCE")

estimator = model

if isinstance(model, Pipeline):
    estimator = model.steps[-1][1]

if hasattr(estimator, "feature_importances_"):
    importances = estimator.feature_importances_

    try:
        transformed_names = model[:-1].get_feature_names_out()
    except (AttributeError, ValueError):
        transformed_names = None

    if transformed_names is not None and len(transformed_names) == len(importances):
        feature_names = list(transformed_names)
    elif len(importances) == len(model_features):
        feature_names = model_features
    else:
        feature_names = [
            f"transformed_feature_{index + 1}"
            for index in range(len(importances))
        ]
        print(
            "WARNING: Could not map all transformed features "
            "back to original input features."
        )

    importance_series = pd.Series(
        importances,
        index=feature_names,
    ).sort_values(ascending=False)

    print("Top 15 features by built-in Random Forest importance:")
    print(importance_series.head(15).round(5).to_string())

    print(
        "\nImportance values describe model reliance, "
        "not causation or proof of feature validity."
    )

else:
    print(
        "The final estimator does not expose feature_importances_. "
        "A different explanation method may be needed."
    )


# ============================================================
# 9. EVENT-LEVEL SPLIT AVAILABILITY
# ============================================================

section("7. EVENT-LEVEL GENERALIZATION CHECK")

if "Event_ID" not in df.columns:
    print(
        "Event_ID is unavailable. A group-aware split cannot be "
        "constructed from this dataset as currently loaded."
    )

else:
    event_count = df["Event_ID"].nunique()

    print(f"Unique Event_ID values: {event_count:,}")

    event_classes = df.groupby("Event_ID")[TARGET_COLUMN].nunique()

    mixed_events = int((event_classes > 1).sum())

    print(f"Events containing multiple labels: {mixed_events:,}")

    if event_count < 2:
        print(
            "Not enough unique events for an event-level train/test split."
        )

    else:
        print(
            "An event-aware evaluation is needed before claiming "
            "generalization to unseen simulated events."
        )

        print(
            "Do not interpret the random holdout score as independent-event "
            "performance when related event records can cross the split."
        )


# ============================================================
# 10. PRELIMINARY DECISION GUIDANCE
# ============================================================

section("8. PRELIMINARY RECOMMENDATION")

print(f"Stratified holdout accuracy: {accuracy * 100:.2f}%")
print(f"Macro F1-score: {macro_f1 * 100:.2f}%")
print(f"Macro recall: {macro_recall * 100:.2f}%")

if accuracy >= 0.75 and macro_f1 >= 0.70:
    print(
        "\nINITIAL RESULT: The existing model merits further evaluation "
        "before tuning or retraining."
    )

elif accuracy < 0.60 or macro_f1 < 0.55:
    print(
        "\nINITIAL RESULT: Investigate data quality, feature definitions, "
        "class confusion, and evaluation methodology before deciding "
        "whether tuning or retraining is appropriate."
    )

else:
    print(
        "\nINITIAL RESULT: Review per-class performance and the confusion "
        "matrix before deciding whether tuning is justified."
    )

print(
    "\nThis recommendation is preliminary. It does not establish that "
    "the model is suitable for real-world use."
)

print(
    "\nNEXT STEP: Audit the data-generation process and evaluate using "
    "an event-aware split. Compare baselines before selecting a new model."
)

print("\nAudit completed. No model or dataset files were modified.")