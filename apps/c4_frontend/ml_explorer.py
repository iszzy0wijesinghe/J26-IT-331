from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from components.c4_trust.models import ModelSchemaError, ModelType, TrainedModel
from components.c4_trust.runtime_features import C4_MODEL_FEATURE_SCHEMA

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "experiments" / "c4" / "models"
DATA_DIR = PROJECT_ROOT / "experiments" / "c4" / "data"
PLOTS_DIR = PROJECT_ROOT / "experiments" / "c4" / "plots"

FEATURE_FAMILIES: dict[str, str] = {
    "tx_interval_s": "B0 Timing",
    "rx_delay_s": "B0 Timing",
    "freshness_status_encoded": "B0 Timing",
    "rssi_dbm": "B1 Radio",
    "rssi_deviation_db": "B1 Radio",
    "snr_db": "B1 Radio",
    "retry_count": "B1 Radio",
    "packet_size_bytes": "B2 Packet",
    "battery_pct": "B3 Device health",
    "battery_voltage_v": "B3 Device health",
    "current_ma": "B3 Device health",
    "reboot_count_24h": "B3 Device health",
    "sensor_fault_flag": "B3 Device health",
    "rolling_interval_mean": "B5 Historical",
    "rolling_interval_std": "B5 Historical",
    "rolling_rssi_mean": "B5 Historical",
    "rolling_rssi_std": "B5 Historical",
    "rolling_retry_mean": "B5 Historical",
}

FEATURE_DESCRIPTIONS: dict[str, str] = {
    "tx_interval_s": "Seconds between this packet and the previous packet from the same device",
    "rx_delay_s": "Delay between device observation time and hub receive time",
    "freshness_status_encoded": "Encoded freshness class: 0 fresh, 1 delayed, 2 stale",
    "rssi_dbm": "Received signal strength",
    "rssi_deviation_db": "Deviation of RSSI from the device rolling mean",
    "snr_db": "Signal-to-noise ratio",
    "retry_count": "Radio retry count for the packet",
    "packet_size_bytes": "Serialized packet size",
    "battery_pct": "Reported battery percentage",
    "battery_voltage_v": "Reported battery voltage",
    "current_ma": "Reported current draw",
    "reboot_count_24h": "Reboots observed in the last 24 hours",
    "sensor_fault_flag": "Device-reported sensor fault flag",
    "rolling_interval_mean": "Rolling mean of recent transmit intervals",
    "rolling_interval_std": "Rolling standard deviation of recent transmit intervals",
    "rolling_rssi_mean": "Rolling mean of recent RSSI values",
    "rolling_rssi_std": "Rolling standard deviation of recent RSSI values",
    "rolling_retry_mean": "Rolling mean of recent retry counts",
}

WHAT_IF_FEATURES = (
    "tx_interval_s",
    "rssi_dbm",
    "snr_db",
    "retry_count",
    "battery_pct",
    "rolling_interval_std",
    "rolling_rssi_mean",
)


@dataclass(frozen=True)
class ModelCatalogEntry:
    key: str
    label: str
    filename: str
    holdout_filename: str
    runtime_default: bool = False
    notes: str = ""


MODEL_CATALOG: tuple[ModelCatalogEntry, ...] = (
    ModelCatalogEntry(
        key="random_forest_corrected",
        label="Random Forest (corrected, runtime)",
        filename="random_forest_corrected.joblib",
        holdout_filename="C4_test_corrected.csv",
        runtime_default=True,
        notes=(
            "Production behavioral scorer used by the C4 trust gate. "
            "Anomaly score is 1 - P(Trusted)."
        ),
    ),
    ModelCatalogEntry(
        key="random_forest",
        label="Random Forest (original baseline)",
        filename="random_forest.joblib",
        holdout_filename="C4_test.csv",
        notes="Earlier baseline trained before the corrected feature semantics.",
    ),
    ModelCatalogEntry(
        key="logistic_regression",
        label="Logistic Regression (baseline)",
        filename="logistic_regression.joblib",
        holdout_filename="C4_test.csv",
        notes="Linear baseline used for comparison. Coefficients are scaled.",
    ),
    ModelCatalogEntry(
        key="isolation_forest",
        label="Isolation Forest (unsupervised)",
        filename="isolation_forest.joblib",
        holdout_filename="C4_test.csv",
        notes=(
            "Unsupervised novelty detector. It is not used as the calibrated "
            "C4 behavioural anomaly score."
        ),
    ),
)

SHAP_PLOT_FILES = (
    ("shap_bar.png", "Global mean absolute SHAP importance"),
    ("shap_summary.png", "SHAP summary for the first class"),
    ("shap_force_example_1.png", "Individual explanation example 1"),
    ("shap_force_example_2.png", "Individual explanation example 2"),
    ("shap_force_example_3.png", "Individual explanation example 3"),
)


def catalog_by_key() -> dict[str, ModelCatalogEntry]:
    return {entry.key: entry for entry in MODEL_CATALOG}


def default_catalog_key() -> str:
    for entry in MODEL_CATALOG:
        if entry.runtime_default:
            return entry.key
    return MODEL_CATALOG[0].key


def available_catalog_entries(
    models_dir: Path | None = None,
) -> list[ModelCatalogEntry]:
    root = models_dir or MODELS_DIR
    return [entry for entry in MODEL_CATALOG if (root / entry.filename).exists()]


def features_from_split(
    frame: pd.DataFrame,
    feature_names: list[str],
) -> tuple[pd.DataFrame, pd.Series]:
    missing = [name for name in feature_names if name not in frame.columns]
    if missing:
        raise ModelSchemaError(
            "Holdout file is missing required model features: "
            + ", ".join(missing)
        )

    features = frame.loc[:, list(feature_names)].apply(
        pd.to_numeric,
        errors="coerce",
    )
    if not np.isfinite(features.to_numpy(dtype=float)).all():
        raise ModelSchemaError(
            "Holdout features contain missing or non-finite values"
        )

    if "trust_label" not in frame.columns:
        raise ModelSchemaError("Holdout file does not contain trust_label")

    return features, frame["trust_label"].astype(str)


def feature_importance_table(model: TrainedModel) -> pd.DataFrame:
    estimator = model.model
    names = list(model.feature_names)

    if hasattr(estimator, "feature_importances_"):
        scores = np.asarray(estimator.feature_importances_, dtype=float)
        source = "Random Forest impurity importance"
    elif hasattr(estimator, "coef_"):
        coefficients = np.abs(np.asarray(estimator.coef_, dtype=float))
        scores = coefficients.mean(axis=0) if coefficients.ndim > 1 else coefficients
        source = "Mean absolute logistic coefficient"
    else:
        return pd.DataFrame(
            columns=["feature", "family", "importance", "source"]
        )

    if len(scores) != len(names):
        raise ModelSchemaError("Feature importance length does not match schema")

    table = pd.DataFrame(
        {
            "feature": names,
            "family": [FEATURE_FAMILIES.get(name, "Other") for name in names],
            "importance": scores,
            "source": source,
        }
    )
    return table.sort_values("importance", ascending=False).reset_index(drop=True)


class C4ModelExplorer:
    """Load a C4 behavioral model artifact and support interactive inspection."""

    def __init__(
        self,
        model: TrainedModel,
        *,
        artifact_path: Path,
        catalog_entry: ModelCatalogEntry | None = None,
        holdout_path: Path | None = None,
        plots_dir: Path | None = None,
    ) -> None:
        model.validate_feature_schema(C4_MODEL_FEATURE_SCHEMA)
        self.model = model
        self.artifact_path = Path(artifact_path)
        self.catalog_entry = catalog_entry
        self.holdout_path = Path(holdout_path) if holdout_path else None
        self.plots_dir = Path(plots_dir) if plots_dir else PLOTS_DIR

    @classmethod
    def from_catalog(
        cls,
        key: str,
        *,
        models_dir: Path | None = None,
        data_dir: Path | None = None,
        plots_dir: Path | None = None,
    ) -> C4ModelExplorer:
        entry = catalog_by_key().get(key)
        if entry is None:
            raise KeyError(f"Unknown model catalog key: {key}")

        artifact_path = (models_dir or MODELS_DIR) / entry.filename
        holdout_path = (data_dir or DATA_DIR) / entry.holdout_filename
        return cls.from_artifact(
            artifact_path,
            holdout_path=holdout_path if holdout_path.exists() else None,
            catalog_entry=entry,
            plots_dir=plots_dir,
        )

    @classmethod
    def from_artifact(
        cls,
        artifact_path: Path,
        *,
        holdout_path: Path | None = None,
        catalog_entry: ModelCatalogEntry | None = None,
        plots_dir: Path | None = None,
    ) -> C4ModelExplorer:
        artifact_path = Path(artifact_path)
        if not artifact_path.exists():
            raise FileNotFoundError(f"Model artifact not found: {artifact_path}")

        model = TrainedModel.load(
            artifact_path,
            expected_feature_names=C4_MODEL_FEATURE_SCHEMA,
        )
        return cls(
            model,
            artifact_path=artifact_path,
            catalog_entry=catalog_entry,
            holdout_path=holdout_path,
            plots_dir=plots_dir,
        )

    def profile(self) -> dict[str, Any]:
        estimator = self.model.model
        classes = [str(item) for item in self.model.label_encoder.classes_]
        metrics = self.model.metrics.to_dict() if self.model.metrics else None
        return {
            "label": (
                self.catalog_entry.label
                if self.catalog_entry
                else self.artifact_path.name
            ),
            "artifact": str(self.artifact_path),
            "model_type": str(self.model.model_type),
            "n_features": len(self.model.feature_names),
            "classes": classes,
            "n_estimators": getattr(estimator, "n_estimators", None),
            "training_metadata": dict(self.model.training_metadata),
            "runtime_default": bool(
                self.catalog_entry.runtime_default if self.catalog_entry else False
            ),
            "notes": self.catalog_entry.notes if self.catalog_entry else "",
            "stored_metrics": metrics,
            "supports_probabilities": self.model.model_type != ModelType.ISOLATION_FOREST,
        }

    def schema_table(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "order": index,
                    "feature": name,
                    "family": FEATURE_FAMILIES.get(name, "Other"),
                    "description": FEATURE_DESCRIPTIONS.get(name, ""),
                }
                for index, name in enumerate(self.model.feature_names, start=1)
            ]
        )

    def importance_table(self) -> pd.DataFrame:
        return feature_importance_table(self.model)

    def shap_plots(self) -> list[tuple[Path, str]]:
        plots: list[tuple[Path, str]] = []
        for filename, caption in SHAP_PLOT_FILES:
            path = self.plots_dir / filename
            if path.exists():
                plots.append((path, caption))
        return plots

    def load_holdout(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
        if self.holdout_path is None or not self.holdout_path.exists():
            raise FileNotFoundError("Holdout dataset is not available for this model")

        raw = pd.read_csv(self.holdout_path)
        features, labels = features_from_split(raw, self.model.feature_names)
        return raw, features, labels

    def score_features(self, features: pd.DataFrame) -> pd.DataFrame:
        predicted = self.model.predict(features)
        scored = pd.DataFrame({"predicted_label": predicted}, index=features.index)

        if self.model.model_type != ModelType.ISOLATION_FOREST:
            probabilities = self.model.predict_proba(features)
            class_names = [str(item) for item in self.model.label_encoder.classes_]
            for index, class_name in enumerate(class_names):
                scored[f"p_{class_name.lower()}"] = probabilities[:, index]
            if "Trusted" not in class_names:
                raise ModelSchemaError("Model artifact has no Trusted class")
            scored["anomaly_score"] = 1.0 - scored["p_trusted"]
            scored["ml_decision"] = np.where(
                scored["anomaly_score"] >= 0.70,
                "SUSPICIOUS",
                "BEHAVIOURAL_NORMAL",
            )
        return scored

    def evaluate_holdout(self, max_rows: int | None = None) -> dict[str, Any]:
        raw, features, labels = self.load_holdout()
        if max_rows is not None:
            features = features.head(max_rows)
            labels = labels.loc[features.index]
            raw = raw.loc[features.index]

        scored = self.score_features(features)
        predicted = scored["predicted_label"].astype(str)
        actual = labels.astype(str)
        classes = sorted(set(actual) | set(predicted))
        confusion = pd.crosstab(
            actual,
            predicted,
            rownames=["Actual"],
            colnames=["Predicted"],
        ).reindex(index=classes, columns=classes, fill_value=0)

        accuracy = float((predicted == actual).mean()) if len(actual) else 0.0
        return {
            "n_rows": int(len(actual)),
            "accuracy": accuracy,
            "label_counts": actual.value_counts().to_dict(),
            "confusion_matrix": confusion,
            "scored": pd.concat(
                [
                    raw[
                        [
                            column
                            for column in (
                                "packet_id",
                                "device_id",
                                "scenario",
                                "trust_label",
                            )
                            if column in raw.columns
                        ]
                    ],
                    scored,
                ],
                axis=1,
            ),
            "features": features,
        }

    def inspector_sample(
        self,
        evaluation: dict[str, Any],
        max_rows: int = 240,
        seed: int = 42,
    ) -> pd.DataFrame:
        scored = evaluation["scored"].copy()
        features = evaluation["features"]
        combined = pd.concat([scored, features], axis=1)

        if len(combined) <= max_rows:
            return combined.reset_index(drop=True)

        parts: list[pd.DataFrame] = []
        remaining = max_rows
        if "trust_label" in combined.columns:
            grouped = combined.groupby("trust_label", sort=False)
            per_class = max(1, max_rows // max(len(grouped), 1))
            for _, group in grouped:
                take = min(len(group), per_class, remaining)
                if take <= 0:
                    break
                parts.append(group.sample(n=take, random_state=seed))
                remaining -= take

        sampled = pd.concat(parts) if parts else combined.head(0)
        leftover = combined.drop(index=sampled.index, errors="ignore")
        if remaining > 0 and not leftover.empty:
            sampled = pd.concat(
                [
                    sampled,
                    leftover.sample(
                        n=min(remaining, len(leftover)),
                        random_state=seed,
                    ),
                ]
            )
        return sampled.head(max_rows).reset_index(drop=True)
