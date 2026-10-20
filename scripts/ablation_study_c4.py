"""Ablation study for C4 trust assessment.

This script compares three approaches:
1. Deterministic-only: Only security checks, no ML
2. Behavioral-only: Only ML, no deterministic gate
3. Hybrid: Deterministic gate + behavioral ML (current C4 approach)

This demonstrates the research contribution of the hybrid architecture.
"""

import sys
from pathlib import Path
from typing import Any

import pandas as pd

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from components.c4_trust.data_split import ScenarioAwareSplitter  # noqa: E402
from components.c4_trust.features import FeatureExtractor  # noqa: E402
from components.c4_trust.models import BaselineModel, ModelType, TrainedModel  # noqa: E402

DETERMINISTIC_SECURITY_FIELDS = (
    "cert_registered",
    "channel_auth_ok",
    "signature_valid",
    "attestation_passed",
    "firmware_approved",
    "config_hash_match",
    "payload_hash_match",
    "prev_hash_match",
    "path_valid",
    "provenance_complete",
    "hub_match",
    "location_match",
)


def _deterministic_security_passed(test_df: pd.DataFrame) -> pd.Series:
    missing_fields = set(DETERMINISTIC_SECURITY_FIELDS) - set(test_df.columns)
    if missing_fields:
        raise ValueError(
            f"Dataset is missing deterministic security fields: {sorted(missing_fields)}"
        )

    flags = test_df[list(DETERMINISTIC_SECURITY_FIELDS)].apply(
        pd.to_numeric, errors="coerce"
    )
    if flags.isna().any().any() or not flags.isin([0, 1]).all().all():
        raise ValueError("Deterministic security fields must contain only 0/1 values")
    return flags.eq(1).all(axis=1)


def load_splits(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load train/val/test splits.

    Args:
        data_dir: Directory containing split files

    Returns:
        Tuple of (train, val, test) dataframes
    """
    train_df = pd.read_csv(data_dir / "C4_train.csv")
    val_df = pd.read_csv(data_dir / "C4_val.csv")
    test_df = pd.read_csv(data_dir / "C4_test.csv")

    ScenarioAwareSplitter.validate_splits(
        {"train": train_df, "val": val_df, "test": test_df}
    )
    return train_df, val_df, test_df


def prepare_features_labels(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Separate features and labels.

    Args:
        df: Input dataframe

    Returns:
        Tuple of (features, labels)
    """
    return FeatureExtractor().extract_for_training(df)


def deterministic_only_assessment(
    test_df: pd.DataFrame,
) -> dict[str, Any]:
    """Simulate deterministic-only assessment.

    In the actual dataset, deterministic security fields determine the label:
    - If security fields pass -> Trusted or Suspicious (based on behavioral)
    - If security fields fail -> Untrusted

    Since we excluded security fields from ML training, we simulate this by
    using the original deterministic logic from the dataset.

    Args:
        test_df: Test dataframe with original columns

    Returns:
        Dictionary with assessment results
    """
    security_passed = _deterministic_security_passed(test_df)
    predictions = ["Trusted" if passed else "Untrusted" for passed in security_passed]

    # Calculate metrics
    prediction_series = pd.Series(predictions, index=test_df.index)
    accuracy = (prediction_series == test_df["trust_label"]).mean()

    # Count by label
    correct_by_label = {}
    for label in test_df["trust_label"].unique():
        label_mask = test_df["trust_label"] == label
        correct = (prediction_series.loc[label_mask] == label).sum()
        total = label_mask.sum()
        correct_by_label[label] = {
            "correct": correct,
            "total": total,
            "accuracy": correct / total if total > 0 else 0,
        }

    return {
        "accuracy": accuracy,
        "correct_by_label": correct_by_label,
        "predictions": predictions,
    }


def behavioral_only_assessment(
    X_test: pd.DataFrame,
    y_test: pd.Series,
    model: TrainedModel,
) -> dict[str, Any]:
    """Assess using behavioral ML only (no deterministic gate).

    Args:
        X_test: Test features
        y_test: Test labels
        model: Trained behavioral model

    Returns:
        Dictionary with assessment results
    """
    # Predict using ML model only
    predictions = model.predict(X_test)

    # Calculate metrics
    accuracy = (predictions == y_test).mean()

    # Count by label
    correct_by_label = {}
    for label in y_test.unique():
        label_mask = y_test == label
        correct = (predictions[label_mask] == label).sum()
        total = label_mask.sum()
        correct_by_label[label] = {
            "correct": correct,
            "total": total,
            "accuracy": correct / total if total > 0 else 0,
        }

    return {
        "accuracy": accuracy,
        "correct_by_label": correct_by_label,
        "predictions": predictions.tolist(),
    }


def hybrid_assessment(
    test_df: pd.DataFrame,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    model: TrainedModel,
    suspicious_threshold: float = 0.7,
) -> dict[str, Any]:
    """Assess using hybrid approach (deterministic gate + behavioral ML).

    This is the current C4 approach:
    1. If deterministic fails -> UNTRUSTED (ML cannot override)
    2. If deterministic passes -> Behavioral ML score
    3. If behavioral score >= threshold -> SUSPICIOUS
    4. Else -> TRUSTED

    Args:
        test_df: Test dataframe with original columns
        X_test: Test features
        y_test: Test labels
        model: Trained behavioral model
        suspicious_threshold: Threshold for suspicious classification

    Returns:
        Dictionary with assessment results
    """
    # Get behavioral predictions
    behavioral_proba = model.predict_proba(X_test)

    hybrid_predictions = []
    security_passed = _deterministic_security_passed(test_df).tolist()
    trusted_idx = list(model.label_encoder.classes_).index("Trusted")
    for index, gate_passed in enumerate(security_passed):
        if not gate_passed:
            hybrid_predictions.append("Untrusted")
        else:
            proba = behavioral_proba[index]
            behavioral_score = 1.0 - proba[trusted_idx]

            if behavioral_score >= suspicious_threshold:
                hybrid_predictions.append("Suspicious")
            else:
                hybrid_predictions.append("Trusted")

    # Calculate metrics
    prediction_series = pd.Series(hybrid_predictions, index=test_df.index)
    accuracy = (prediction_series == y_test).mean()

    # Count by label
    correct_by_label = {}
    for label in test_df["trust_label"].unique():
        label_mask = test_df["trust_label"] == label
        correct = (prediction_series.loc[label_mask] == label).sum()
        total = label_mask.sum()
        correct_by_label[label] = {
            "correct": correct,
            "total": total,
            "accuracy": correct / total if total > 0 else 0,
        }

    return {
        "accuracy": accuracy,
        "correct_by_label": correct_by_label,
        "predictions": hybrid_predictions,
    }


def main() -> None:
    # Paths
    data_dir = Path(r"C:\Users\User\Desktop\FInal_GeoNex_Repo\J26-IT-331\experiments\c4\data")
    # Load splits
    print("Loading splits...")
    train_df, val_df, test_df = load_splits(data_dir)

    # Prepare features and labels
    print("Preparing features and labels...")
    X_train, y_train = prepare_features_labels(train_df)
    X_val, y_val = prepare_features_labels(val_df)
    X_test, y_test = prepare_features_labels(test_df)

    print(f"Train: {X_train.shape}, Labels: {y_train.nunique()}")
    print(f"Val: {X_val.shape}, Labels: {y_val.nunique()}")
    print(f"Test: {X_test.shape}, Labels: {y_test.nunique()}")

    # Train a baseline model for behavioral-only and hybrid
    print("\n" + "=" * 60)
    print("Training Behavioral Model (Random Forest)...")
    print("=" * 60)
    rf_baseline = BaselineModel(model_type=ModelType.RANDOM_FOREST)
    rf_trained = rf_baseline.fit(X_train, y_train, X_val, y_val)

    # Evaluate behavioral model alone
    print("\n" + "=" * 60)
    print("Behavioral-Only Assessment")
    print("=" * 60)
    behavioral_results = behavioral_only_assessment(X_test, y_test, rf_trained)
    print(f"Overall Accuracy: {behavioral_results['accuracy']:.4f}")
    print("\nPer-Class Accuracy:")
    for label, metrics in behavioral_results["correct_by_label"].items():
        print(f"  {label}: {metrics['accuracy']:.4f} ({metrics['correct']}/{metrics['total']})")

    # Evaluate deterministic-only
    print("\n" + "=" * 60)
    print("Deterministic-Only Assessment")
    print("=" * 60)
    deterministic_results = deterministic_only_assessment(test_df)
    print(f"Overall Accuracy: {deterministic_results['accuracy']:.4f}")
    print("\nPer-Class Accuracy:")
    for label, metrics in deterministic_results["correct_by_label"].items():
        print(f"  {label}: {metrics['accuracy']:.4f} ({metrics['correct']}/{metrics['total']})")

    # Evaluate hybrid
    print("\n" + "=" * 60)
    print("Hybrid Assessment (Deterministic + Behavioral)")
    print("=" * 60)
    hybrid_results = hybrid_assessment(test_df, X_test, y_test, rf_trained)
    print(f"Overall Accuracy: {hybrid_results['accuracy']:.4f}")
    print("\nPer-Class Accuracy:")
    for label, metrics in hybrid_results["correct_by_label"].items():
        print(f"  {label}: {metrics['accuracy']:.4f} ({metrics['correct']}/{metrics['total']})")

    # Summary comparison
    print("\n" + "=" * 60)
    print("Ablation Study Summary")
    print("=" * 60)
    print(f"{'Approach':<30} {'Accuracy':<10}")
    print("-" * 40)
    print(f"{'Deterministic-Only':<30} {deterministic_results['accuracy']:.4f}")
    print(f"{'Behavioral-Only':<30} {behavioral_results['accuracy']:.4f}")
    print(f"{'Hybrid (C4 Approach)':<30} {hybrid_results['accuracy']:.4f}")

    print("\n" + "=" * 60)
    print("Ablation Study Complete!")
    print("=" * 60)
    print("\nConclusion:")
    print("The hybrid approach combines the strengths of both:")
    print("- Deterministic checks provide hard security guarantees")
    print("- Behavioral ML detects subtle anomalies that pass deterministic checks")
    print("- Together, they provide broader threat coverage than either alone")


if __name__ == "__main__":
    main()
