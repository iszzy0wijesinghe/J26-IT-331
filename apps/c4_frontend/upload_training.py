
from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path
import uuid

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from components.c4_trust.models import BaselineModel, ModelType, TrainedModel

from collections.abc import Callable

FEATURES = [
    "tx_interval_s",
    "rx_delay_s",
    "freshness_status_encoded",
    "rssi_dbm",
    "rssi_deviation_db",
    "snr_db",
    "retry_count",
    "packet_size_bytes",
    "battery_pct",
    "battery_voltage_v",
    "current_ma",
    "reboot_count_24h",
    "sensor_fault_flag",
    "rolling_interval_mean",
    "rolling_interval_std",
    "rolling_rssi_mean",
    "rolling_rssi_std",
    "rolling_retry_mean",
]

LABELS = ["Trusted", "Untrusted", "Suspicious"]

RAW_COLUMNS = [
    "device_id",
    "device_timestamp",
    "received_timestamp",
    "tx_interval_s",
    "rssi_dbm",
    "freshness_status",
    "snr_db",
    "retry_count",
    "packet_size_bytes",
    "battery_pct",
    "battery_voltage_v",
    "current_ma",
    "reboot_count_24h",
    "sensor_fault_flag",
    "trust_label",
]


def prepare_uploaded_dataset(uploaded_df: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in RAW_COLUMNS if column not in uploaded_df.columns]
    if missing:
        raise ValueError(
            "The CSV is missing required columns: " + ", ".join(missing)
        )

    df = uploaded_df.copy()
    df.columns = [str(column).strip() for column in df.columns]

    missing = [column for column in RAW_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(
            "The CSV is missing required columns: " + ", ".join(missing)
        )

    df["device_id"] = df["device_id"].astype("string").str.strip()
    df["device_timestamp"] = pd.to_datetime(
        df["device_timestamp"], errors="coerce", utc=True
    )
    df["received_timestamp"] = pd.to_datetime(
        df["received_timestamp"], errors="coerce", utc=True
    )

    df["trust_label"] = (
        df["trust_label"].astype("string").str.strip().str.title()
    )
    df["freshness_status"] = (
        df["freshness_status"].astype("string").str.strip().str.lower()
    )

    df = df.dropna(
        subset=[
            "device_id",
            "device_timestamp",
            "received_timestamp",
            "trust_label",
        ]
    )
    df = df[df["device_id"] != ""]
    df = df[df["trust_label"].isin(LABELS)].copy()

    if df.empty:
        raise ValueError(
            "No valid rows remain. Labels must be Trusted, Untrusted, "
            "or Suspicious, and device/timestamp values must be valid."
        )

    df = df.sort_values(
        ["device_id", "device_timestamp"], kind="stable"
    ).reset_index(drop=True)

    numeric_columns = [
        "tx_interval_s",
        "rssi_dbm",
        "snr_db",
        "retry_count",
        "packet_size_bytes",
        "battery_pct",
        "battery_voltage_v",
        "current_ma",
        "reboot_count_24h",
        "sensor_fault_flag",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["rx_delay_s"] = (
        df["received_timestamp"] - df["device_timestamp"]
    ).dt.total_seconds()

    freshness_map = {"fresh": 0, "delayed": 1, "stale": 2}
    df["freshness_status_encoded"] = df["freshness_status"].map(
        freshness_map
    )

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(
        subset=numeric_columns
        + ["rx_delay_s", "freshness_status_encoded"]
    )
    df = df[df["rx_delay_s"] >= 0].copy()

    if df.empty:
        raise ValueError("No valid numeric telemetry rows remain after cleaning.")

    history_size = 10
    histories = defaultdict(
        lambda: {
            "intervals": deque(maxlen=history_size),
            "rssis": deque(maxlen=history_size),
            "retries": deque(maxlen=history_size),
        }
    )

    derived = {
        name: []
        for name in [
            "rssi_deviation_db",
            "rolling_interval_mean",
            "rolling_interval_std",
            "rolling_rssi_mean",
            "rolling_rssi_std",
            "rolling_retry_mean",
        ]
    }

    for row in df.itertuples(index=False):
        history = histories[str(row.device_id)]
        intervals = list(history["intervals"])
        rssis = list(history["rssis"])
        retries = list(history["retries"])

        derived["rssi_deviation_db"].append(
            float(row.rssi_dbm - np.mean(rssis)) if rssis else 0.0
        )
        derived["rolling_interval_mean"].append(
            float(np.mean(intervals)) if intervals else 0.0
        )
        derived["rolling_interval_std"].append(
            float(np.std(intervals)) if len(intervals) > 1 else 0.0
        )
        derived["rolling_rssi_mean"].append(
            float(np.mean(rssis)) if rssis else 0.0
        )
        derived["rolling_rssi_std"].append(
            float(np.std(rssis)) if len(rssis) > 1 else 0.0
        )
        derived["rolling_retry_mean"].append(
            float(np.mean(retries)) if retries else 0.0
        )

        history["intervals"].append(float(row.tx_interval_s))
        history["rssis"].append(float(row.rssi_dbm))
        history["retries"].append(float(row.retry_count))

    for column, values in derived.items():
        df[column] = values

    for column in FEATURES:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=FEATURES + ["trust_label", "device_id"])

    if df["trust_label"].nunique() < 2:
        raise ValueError("At least two different trust labels are required.")

    if df["device_id"].nunique() < 10:
        raise ValueError(
            "At least 10 unique devices are required for device-aware splitting."
        )

    return df.reset_index(drop=True)


def create_device_aware_splits(
    df: pd.DataFrame,
    seed: int = 42,
) -> dict[str, pd.DataFrame]:
    devices = df["device_id"].drop_duplicates().to_numpy()
    if len(devices) < 10:
        raise ValueError("At least 10 unique devices are required.")

    rng = np.random.default_rng(seed)
    labels = set(df["trust_label"].unique())

    for _ in range(1000):
        shuffled = rng.permutation(devices)
        n_train = max(1, int(len(shuffled) * 0.70))
        n_val = max(1, int(len(shuffled) * 0.15))

        train_devices = set(shuffled[:n_train])
        val_devices = set(shuffled[n_train:n_train + n_val])
        test_devices = set(shuffled[n_train + n_val:])

        if not test_devices or not val_devices:
            continue

        train = df[df["device_id"].isin(train_devices)].copy()
        val = df[df["device_id"].isin(val_devices)].copy()
        test = df[df["device_id"].isin(test_devices)].copy()

        if (
            set(train["trust_label"].unique()) == labels
            and set(val["trust_label"].unique()) == labels
            and set(test["trust_label"].unique()) == labels
        ):
            return {"train": train, "validation": val, "test": test}

    raise ValueError(
        "Could not create device-disjoint splits containing every trust "
        "label in all three sets. Upload a dataset with more devices and "
        "better label coverage across devices."
    )



def train_uploaded_random_forest(
    uploaded_df: pd.DataFrame,
    progress_callback: Callable[[str, str], None] | None = None,
) -> dict:
    def report_progress(stage: str, message: str) -> None:
        if progress_callback is not None:
            progress_callback(stage, message)

    report_progress("preparing_data", "Validating telemetry and preparing features.")
    prepared = prepare_uploaded_dataset(uploaded_df)

    report_progress(
        "splitting_devices",
        "Creating device-disjoint training, validation and test sets.",
    )
    splits = create_device_aware_splits(prepared)

    X_train = splits["train"][FEATURES]
    y_train = splits["train"]["trust_label"]
    X_val = splits["validation"][FEATURES]
    y_val = splits["validation"]["trust_label"]
    X_test = splits["test"][FEATURES]
    y_test = splits["test"]["trust_label"]

    report_progress(
        "training_model",
        "Fitting the Random Forest with the training and validation datasets.",
    )
    trainer = BaselineModel(ModelType.RANDOM_FOREST, random_state=42)
    trained = trainer.fit(X_train, y_train, X_val, y_val)

    report_progress(
        "evaluating_model",
        "Evaluating held-out test data and calculating model metrics.",
    )
    predictions = trained.predict(X_test)
    probabilities = trained.predict_proba(X_test)
    classes = list(trained.label_encoder.classes_)

    report = classification_report(
        y_test,
        predictions,
        labels=classes,
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(y_test, predictions, labels=classes)

    scored = splits["test"][
        ["device_id", "device_timestamp", "trust_label"]
    ].copy()
    scored["predicted_label"] = predictions
    scored["prediction_correct"] = (
        scored["trust_label"] == scored["predicted_label"]
    ).to_numpy()

    for index, label in enumerate(classes):
        scored[f"probability_{label.lower()}"] = probabilities[:, index]

    trained.training_metadata.update(
        {
            "training_source": "uploaded_csv_candidate",
            "split_strategy": "device_disjoint_70_15_15",
            "n_validation_samples": len(X_val),
            "n_test_samples": len(X_test),
            "n_unique_devices": int(prepared["device_id"].nunique()),
            "feature_schema": FEATURES,
            "runtime_compatibility_verified": False,
        }
    )

    importances = getattr(trained.model, "feature_importances_", None)
    importance_table = (
        pd.DataFrame(
            {"feature": FEATURES, "importance": importances}
        ).sort_values("importance", ascending=False)
        if importances is not None
        else pd.DataFrame(columns=["feature", "importance"])
    )

    result = {
        "trained_model": trained,
        "prepared": prepared,
        "splits": splits,
        "accuracy": float(accuracy_score(y_test, predictions)),
        "report": report,
        "classes": classes,
        "confusion_matrix": matrix,
        "predictions": scored.reset_index(drop=True),
        "feature_importance": importance_table,
    }

    report_progress("completed", "Training and evaluation completed.")
    return result

def save_candidate_model(result: dict) -> Path:
    trained_model = result.get("trained_model")

    if not isinstance(trained_model, TrainedModel):
        raise ValueError(
            "The training result does not contain a valid GeoNex trained model."
        )

    trained_model.validate_feature_schema(FEATURES)

    repo_root = Path(__file__).resolve().parents[2]
    candidate_dir = repo_root / "experiments" / "c4" / "models" / "uploads"
    candidate_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    filename = f"random_forest_candidate_{timestamp}_{uuid.uuid4().hex[:8]}.joblib"
    candidate_path = candidate_dir / filename

    trained_model.training_metadata["candidate_only"] = True
    trained_model.training_metadata["runtime_compatibility_verified"] = False

    trained_model.save(candidate_path)

    return candidate_path