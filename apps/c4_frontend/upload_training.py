
from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
import uuid

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from components.c4_trust.models import BaselineModel, ModelType, TrainedModel
from components.c4_trust.runtime_features import C4_MODEL_FEATURE_SCHEMA


FEATURES = list(C4_MODEL_FEATURE_SCHEMA)

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

PREDICTION_RAW_COLUMNS = [
    column for column in RAW_COLUMNS if column != "trust_label"
]


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_candidate_directory() -> Path:
    return (
        get_repo_root()
        / "experiments"
        / "c4"
        / "models"
        / "uploads"
    ).resolve()


def get_runtime_model_path() -> Path:
    return (
        get_repo_root()
        / "experiments"
        / "c4"
        / "models"
        / "random_forest_corrected.joblib"
    ).resolve()


def prepare_uploaded_dataset(
    uploaded_df: pd.DataFrame,
    require_labels: bool = True,
) -> pd.DataFrame:
    if uploaded_df.empty:
        raise ValueError("The uploaded CSV contains no rows.")

    df = uploaded_df.copy()
    df.columns = [str(column).strip() for column in df.columns]

    if len(set(df.columns)) != len(df.columns):
        raise ValueError("The CSV contains duplicate column names.")

    required_columns = RAW_COLUMNS if require_labels else PREDICTION_RAW_COLUMNS
    missing = [column for column in required_columns if column not in df.columns]

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
    df["freshness_status"] = (
        df["freshness_status"].astype("string").str.strip().str.lower()
    )

    if require_labels:
        df["trust_label"] = (
            df["trust_label"].astype("string").str.strip().str.title()
        )

    required_values = [
        "device_id",
        "device_timestamp",
        "received_timestamp",
    ]

    if require_labels:
        required_values.append("trust_label")

    df = df.dropna(subset=required_values)
    df = df[df["device_id"] != ""]

    if require_labels:
        df = df[df["trust_label"].isin(LABELS)].copy()

    if df.empty:
        raise ValueError(
            "No valid rows remain after checking device IDs and timestamps."
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
        subset=numeric_columns + ["rx_delay_s", "freshness_status_encoded"]
    )
    df = df[df["rx_delay_s"] >= 0].copy()

    if df.empty:
        raise ValueError(
            "No valid numeric telemetry rows remain after cleaning."
        )

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
        if column not in df.columns:
            raise ValueError(
                f"Feature generation did not produce required feature: {column}"
            )
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.replace([np.inf, -np.inf], np.nan)

    clean_columns = FEATURES + ["device_id"]
    if require_labels:
        clean_columns.append("trust_label")

    df = df.dropna(subset=clean_columns)

    if df.empty:
        raise ValueError(
            "No rows contain all required model features after cleaning."
        )

    if require_labels and df["trust_label"].nunique() < 2:
        raise ValueError("At least two different trust labels are required.")

    if require_labels and df["device_id"].nunique() < 10:
        raise ValueError(
            "At least 10 unique devices are required for device-aware splitting."
        )

    return df.reset_index(drop=True)



def predict_uploaded_dataset(uploaded_df: pd.DataFrame) -> pd.DataFrame:
    original = uploaded_df.copy()
    original.columns = [str(column).strip() for column in original.columns]

    prepared = prepare_uploaded_dataset(
        original,
        require_labels=False,
    )

    model_path = get_runtime_model_path()

    if not model_path.is_file():
        raise FileNotFoundError(
            f"Configured runtime model does not exist: {model_path}"
        )

    model = TrainedModel.load(
        model_path,
        expected_feature_names=C4_MODEL_FEATURE_SCHEMA,
    )

    X = prepared[FEATURES]
    predictions = np.asarray(model.predict(X)).reshape(-1)

    if len(predictions) != len(prepared):
        raise ValueError(
            "The model returned an unexpected number of predictions."
        )

    results = prepared[original.columns].copy()
    results["predicted_label"] = predictions

    probabilities = np.asarray(model.predict_proba(X))

    expected_shape = (
        len(prepared),
        len(model.label_encoder.classes_),
    )

    if probabilities.shape != expected_shape:
        raise ValueError(
            "The model returned an invalid prediction probability matrix."
        )

    for index, label in enumerate(model.label_encoder.classes_):
        results[f"probability_{str(label).lower()}"] = probabilities[:, index]

    return results.reset_index(drop=True)



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
            return {
                "train": train,
                "validation": val,
                "test": test,
            }

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

    report_progress(
        "preparing_data",
        "Validating telemetry and preparing features.",
    )
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
        "Fitting the Random Forest with training and validation data.",
    )
    trainer = BaselineModel(ModelType.RANDOM_FOREST, random_state=42)
    trained = trainer.fit(X_train, y_train, X_val, y_val)

    report_progress(
        "evaluating_model",
        "Evaluating held-out test data and calculating metrics.",
    )
    predictions = trained.predict(X_test)
    probabilities = np.asarray(trained.predict_proba(X_test))
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
        scored[f"probability_{str(label).lower()}"] = probabilities[:, index]

    trained.training_metadata.update(
        {
            "training_source": "uploaded_csv_candidate",
            "split_strategy": "device_disjoint_70_15_15",
            "n_validation_samples": len(X_val),
            "n_test_samples": len(X_test),
            "n_unique_devices": int(prepared["device_id"].nunique()),
            "feature_schema": FEATURES,
            "candidate_only": True,
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

    candidate_dir = get_candidate_directory()
    candidate_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    filename = (
        f"random_forest_candidate_{timestamp}_{uuid.uuid4().hex[:8]}.joblib"
    )
    candidate_path = candidate_dir / filename

    trained_model.training_metadata["candidate_only"] = True
    trained_model.training_metadata["runtime_compatibility_verified"] = False
    trained_model.save(candidate_path)

    return candidate_path


def verify_candidate_runtime_compatibility(
    candidate_path: Path,
) -> dict:
    checks = {
        "candidate_artifact_loads": False,
        "runtime_artifact_loads": False,
        "feature_schema_matches": False,
        "model_type_matches": False,
        "class_labels_match": False,
        "prediction_output_valid": False,
        "probability_output_valid": False,
    }
    errors: list[str] = []

    try:
        candidate_dir = get_candidate_directory()
        candidate_path = Path(candidate_path).resolve()

        if not candidate_path.is_relative_to(candidate_dir):
            raise ValueError(
                "Candidate artifact must be inside the C4 uploads directory."
            )

        if not candidate_path.is_file():
            raise FileNotFoundError(
                f"Candidate artifact does not exist: {candidate_path}"
            )

        candidate = TrainedModel.load(
            candidate_path,
            expected_feature_names=C4_MODEL_FEATURE_SCHEMA,
        )
        checks["candidate_artifact_loads"] = True

        runtime_path = get_runtime_model_path()

        if not runtime_path.is_file():
            raise FileNotFoundError(
                f"Configured runtime artifact does not exist: {runtime_path}"
            )

        runtime = TrainedModel.load(
            runtime_path,
            expected_feature_names=C4_MODEL_FEATURE_SCHEMA,
        )
        checks["runtime_artifact_loads"] = True

        candidate_features = list(candidate.feature_names)
        runtime_features = list(runtime.feature_names)
        expected_features = list(C4_MODEL_FEATURE_SCHEMA)

        checks["feature_schema_matches"] = (
            candidate_features == runtime_features == expected_features
        )

        checks["model_type_matches"] = (
            candidate.model_type == runtime.model_type
            and candidate.model_type == ModelType.RANDOM_FOREST
        )

        candidate_classes = {
            str(label) for label in candidate.label_encoder.classes_
        }
        runtime_classes = {
            str(label) for label in runtime.label_encoder.classes_
        }

        checks["class_labels_match"] = (
            candidate_classes == runtime_classes == set(LABELS)
        )

        required_interface_checks = (
            "feature_schema_matches",
            "model_type_matches",
            "class_labels_match",
        )

        if not all(checks[key] for key in required_interface_checks):
            raise ValueError(
                "Candidate model interface differs from the configured "
                "C4 runtime model."
            )

        probe = pd.DataFrame(
            np.zeros(
                (3, len(C4_MODEL_FEATURE_SCHEMA)),
                dtype=float,
            ),
            columns=list(C4_MODEL_FEATURE_SCHEMA),
        )

        probe["freshness_status_encoded"] = [0.0, 1.0, 2.0]
        probe["rssi_dbm"] = [-65.0, -80.0, -95.0]
        probe["snr_db"] = [10.0, 5.0, 0.0]
        probe["battery_pct"] = [90.0, 60.0, 30.0]
        probe["battery_voltage_v"] = [4.0, 3.8, 3.5]
        probe["packet_size_bytes"] = [100.0, 120.0, 140.0]

        predictions = np.asarray(candidate.predict(probe)).reshape(-1)

        checks["prediction_output_valid"] = (
            len(predictions) == len(probe)
            and all(str(label) in runtime_classes for label in predictions)
        )

        probabilities = np.asarray(candidate.predict_proba(probe))
        expected_classes = len(candidate.label_encoder.classes_)

        checks["probability_output_valid"] = (
            probabilities.shape == (len(probe), expected_classes)
            and np.isfinite(probabilities).all()
            and (probabilities >= 0).all()
            and (probabilities <= 1).all()
            and np.allclose(
                probabilities.sum(axis=1),
                1.0,
                atol=1e-5,
            )
        )

        if not checks["prediction_output_valid"]:
            errors.append("Candidate returned invalid class predictions.")

        if not checks["probability_output_valid"]:
            errors.append("Candidate returned invalid probability outputs.")

    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")

    verified = all(checks.values()) and not errors

    return {
        "runtime_compatibility_verified": verified,
        "checks": checks,
        "errors": errors,
        "message": (
            "Candidate passed all runtime compatibility checks."
            if verified
            else "Candidate failed or could not complete runtime "
            "compatibility verification."
        ),
    }
