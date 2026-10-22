from pathlib import Path
import json
import time

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost as xgb

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


# ==================================================
# CONFIGURATION
# ==================================================

DATASET_PATH = Path(
    "data/c2_diagnostics/landslide_silence_dataset_20000.csv"
)

OUTPUT_DIR = Path("results/c2_diagnostics/model_comparison")
MODEL_DIR = Path("models/c2_diagnostics/comparison")

TARGET = "Label"
RANDOM_STATE = 42
TEST_SIZE = 0.20


# ==================================================
# LOAD DATA
# ==================================================

def load_data():

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH.resolve()}"
        )

    df = pd.read_csv(DATASET_PATH)

    if TARGET not in df.columns:
        raise ValueError(f"Missing target column: {TARGET}")

    if df[TARGET].isna().any():
        raise ValueError(
            "Target contains missing values. "
            "Investigate them before model comparison."
        )

    print("\n========== DATASET ==========")
    print("Shape:", df.shape)
    print("\nClass distribution:")
    print(df[TARGET].value_counts())

    return df


# ==================================================
# PREPARE FEATURES
# ==================================================

def prepare_features(df):

    # Do not use the target or identifier/time columns
    # as model input features.
    X = df.drop(
        columns=["Label", "Event_ID", "Timestamp"],
        errors="ignore",
    ).copy()

    y = df["Label"].astype(str)

    non_numeric = X.select_dtypes(
        exclude=["number", "bool"]
    ).columns.tolist()

    if non_numeric:
        raise ValueError(
            f"Non-numeric features found: {non_numeric}"
        )

    # Treat infinite values as missing values.
    X = X.replace([np.inf, -np.inf], np.nan)

    print("\nNumber of features:", X.shape[1])
    print("Total missing feature values:", int(X.isna().sum().sum()))

    return X, y


# ==================================================
# SPLIT DATA ONCE
# ==================================================

def split_data(X, y):

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    print("\n========== SHARED DATA SPLIT ==========")
    print("Training samples:", len(X_train))
    print("Testing samples:", len(X_test))

    return X_train, X_test, y_train, y_test


# ==================================================
# DEFINE MODELS
# ==================================================

def create_models():

    random_forest = Pipeline([
        (
            "imputer",
            SimpleImputer(
                strategy="median",
                add_indicator=True,
            ),
        ),
        (
            "classifier",
            RandomForestClassifier(
                n_estimators=200,
                random_state=42,
                class_weight="balanced",
                n_jobs=-1,
            ),
        ),
    ])

    xgboost_model = xgb.XGBClassifier(
        objective="multi:softprob",
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        eval_metric="mlogloss",
        tree_method="hist",
        random_state=42,
        n_jobs=-1,
    )

    return {
        "Random Forest": random_forest,
        "XGBoost": xgboost_model,
    }


# ==================================================
# TRAIN AND EVALUATE
# ==================================================

def train_and_evaluate(
    model_name,
    model,
    X_train,
    X_test,
    y_train,
    y_test,
):

    print(f"\n========== TRAINING {model_name} ==========")

    start = time.perf_counter()

    # XGBoost requires encoded numeric targets.
    # Random Forest can use the original string labels.
    if model_name == "XGBoost":

        model.fit(X_train, y_train_encoded)

    else:

        model.fit(X_train, y_train)

    training_seconds = time.perf_counter() - start

    print(f"Training time: {training_seconds:.2f} seconds")

    start = time.perf_counter()

    predictions = model.predict(X_test)

    prediction_seconds = time.perf_counter() - start

    if model_name == "XGBoost":

        predictions = label_encoder.inverse_transform(
            np.asarray(predictions, dtype=int)
        )

    labels = sorted(y_test.unique())

    accuracy = accuracy_score(y_test, predictions)

    macro_precision = precision_score(
        y_test,
        predictions,
        labels=labels,
        average="macro",
        zero_division=0,
    )

    macro_recall = recall_score(
        y_test,
        predictions,
        labels=labels,
        average="macro",
        zero_division=0,
    )

    macro_f1 = f1_score(
        y_test,
        predictions,
        labels=labels,
        average="macro",
        zero_division=0,
    )

    weighted_f1 = f1_score(
        y_test,
        predictions,
        labels=labels,
        average="weighted",
        zero_division=0,
    )

    print(f"\n{model_name} results:")
    print(f"Accuracy:        {accuracy:.4f}")
    print(f"Macro Precision: {macro_precision:.4f}")
    print(f"Macro Recall:    {macro_recall:.4f}")
    print(f"Macro F1:        {macro_f1:.4f}")
    print(f"Weighted F1:     {weighted_f1:.4f}")

    print("\nClassification report:")

    report = classification_report(
        y_test,
        predictions,
        labels=labels,
        zero_division=0,
        output_dict=True,
    )

    print(
        classification_report(
            y_test,
            predictions,
            labels=labels,
            zero_division=0,
        )
    )

    cm = confusion_matrix(
        y_test,
        predictions,
        labels=labels,
    )

    print("Confusion matrix class order:", labels)
    print(cm)

    metrics = {
        "model": model_name,
        "accuracy": float(accuracy),
        "macro_precision": float(macro_precision),
        "macro_recall": float(macro_recall),
        "macro_f1": float(macro_f1),
        "weighted_f1": float(weighted_f1),
        "training_seconds": float(training_seconds),
        "prediction_seconds_for_test_set": float(
            prediction_seconds
        ),
        "test_samples": int(len(y_test)),
        "class_labels": labels,
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
    }

    return model, metrics


# ==================================================
# MAIN
# ==================================================

def main():

    global label_encoder, y_train_encoded

    df = load_data()

    X, y = prepare_features(df)

    X_train, X_test, y_train, y_test = split_data(X, y)

    # Encode labels consistently for XGBoost.
    from sklearn.preprocessing import LabelEncoder

    label_encoder = LabelEncoder()

    y_train_encoded = label_encoder.fit_transform(y_train)

    y_test_encoded = label_encoder.transform(y_test)

    if not np.array_equal(
        np.sort(np.unique(y_test_encoded)),
        np.arange(len(label_encoder.classes_)),
    ):
        raise ValueError(
            "The test set does not contain every expected class."
        )

    models = create_models()

    all_metrics = []

    for model_name, model in models.items():

        trained_model, metrics = train_and_evaluate(
            model_name,
            model,
            X_train,
            X_test,
            y_train,
            y_test,
        )

        all_metrics.append(metrics)

        # Save comparison models separately.
        MODEL_DIR.mkdir(parents=True, exist_ok=True)

        artifact = {
            "model": trained_model,
            "feature_names": X.columns.tolist(),
            "model_type": model_name,
        }

        if model_name == "XGBoost":
            artifact["label_encoder"] = label_encoder

        filename = (
            "random_forest_comparison.joblib"
            if model_name == "Random Forest"
            else "xgboost_comparison.joblib"
        )

        joblib.dump(artifact, MODEL_DIR / filename)

    # Save comparison metrics.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with (OUTPUT_DIR / "comparison_metrics.json").open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(all_metrics, f, indent=2)

    comparison = pd.DataFrame([
        {
            "Model": m["model"],
            "Accuracy (%)": round(m["accuracy"] * 100, 2),
            "Macro Precision (%)": round(
                m["macro_precision"] * 100, 2
            ),
            "Macro Recall (%)": round(
                m["macro_recall"] * 100, 2
            ),
            "Macro F1 (%)": round(m["macro_f1"] * 100, 2),
            "Weighted F1 (%)": round(
                m["weighted_f1"] * 100, 2
            ),
            "Training time (s)": round(
                m["training_seconds"], 2
            ),
        }
        for m in all_metrics
    ])

    print("\n========== FINAL MODEL COMPARISON ==========")
    print(comparison.to_string(index=False))

    comparison.to_csv(
        OUTPUT_DIR / "comparison_summary.csv",
        index=False,
    )

    print("\nSaved comparison files:")
    print((OUTPUT_DIR / "comparison_metrics.json").resolve())
    print((OUTPUT_DIR / "comparison_summary.csv").resolve())
    print(MODEL_DIR.resolve())

    print(
        "\nNOTE: These are random-split baseline results. "
        "Complete the dataset leakage and scenario-split audit "
        "before treating them as final generalization results."
    )


if __name__ == "__main__":
    main()