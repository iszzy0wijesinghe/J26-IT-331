"""Train baseline models for C4 behavioral classification.

This script:
1. Loads train/val/test splits
2. Trains Logistic Regression baseline
3. Trains Random Forest baseline
4. Trains Isolation Forest baseline
5. Evaluates all models on test set
6. Saves trained models and metrics
"""

import sys
from pathlib import Path

import pandas as pd

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from components.c4_trust.data_split import ScenarioAwareSplitter  # noqa: E402
from components.c4_trust.features import FeatureExtractor  # noqa: E402
from components.c4_trust.models import (  # noqa: E402
    BaselineModel,
    ModelType,
)


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
        {"train": train_df, "val": val_df, "test": test_df},
        device_id_col="device_id",
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


def main() -> None:
    # Paths
    data_dir = Path(r"C:\Users\User\Desktop\FInal_GeoNex_Repo\J26-IT-331\experiments\c4\data")
    models_dir = Path(r"C:\Users\User\Desktop\FInal_GeoNex_Repo\J26-IT-331\experiments\c4\models")
    models_dir.mkdir(parents=True, exist_ok=True)

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

    # Train Logistic Regression
    print("\n" + "=" * 60)
    print("Training Logistic Regression...")
    print("=" * 60)
    lr_baseline = BaselineModel(model_type=ModelType.LOGISTIC_REGRESSION)
    lr_trained = lr_baseline.fit(X_train, y_train, X_val, y_val)
    lr_trained.save(models_dir / "logistic_regression.joblib")

    # Evaluate on test set
    lr_test_metrics = lr_baseline.evaluate(X_test, y_test)
    print("\nTest Metrics:")
    print(f"  Accuracy: {lr_test_metrics.accuracy:.4f}")
    print(f"  Macro F1: {lr_test_metrics.f1_macro:.4f}")

    # Train Random Forest
    print("\n" + "=" * 60)
    print("Training Random Forest...")
    print("=" * 60)
    rf_baseline = BaselineModel(model_type=ModelType.RANDOM_FOREST)
    rf_trained = rf_baseline.fit(X_train, y_train, X_val, y_val)
    rf_trained.save(models_dir / "random_forest.joblib")

    # Evaluate on test set
    rf_test_metrics = rf_baseline.evaluate(X_test, y_test)
    print("\nTest Metrics:")
    print(f"  Accuracy: {rf_test_metrics.accuracy:.4f}")
    print(f"  Macro F1: {rf_test_metrics.f1_macro:.4f}")

    # Feature importance
    rf_importance = rf_baseline.get_feature_importance()
    if rf_importance:
        print("\nTop 10 Feature Importances:")
        for feat, imp in sorted(rf_importance.items(), key=lambda x: -x[1])[:10]:
            print(f"  {feat}: {imp:.4f}")

    # Train Isolation Forest (anomaly detection)
    print("\n" + "=" * 60)
    print("Training Isolation Forest (Anomaly Detection)...")
    print("=" * 60)
    if_baseline = BaselineModel(model_type=ModelType.ISOLATION_FOREST)
    if_trained = if_baseline.fit(X_train, y_train, X_val, y_val)
    if_trained.save(models_dir / "isolation_forest.joblib")

    # Evaluate on test set
    if_test_metrics = if_baseline.evaluate(X_test, y_test)
    print("\nTest Metrics:")
    print(f"  Accuracy: {if_test_metrics.accuracy:.4f}")
    print(f"  Macro F1: {if_test_metrics.f1_macro:.4f}")

    print("\n" + "=" * 60)
    print("Training complete!")
    print("=" * 60)
    print(f"\nModels saved to: {models_dir}")
    print("\nSummary:")
    print(f"  Logistic Regression Test F1: {lr_test_metrics.f1_macro:.4f}")
    print(f"  Random Forest Test F1: {rf_test_metrics.f1_macro:.4f}")
    print(f"  Isolation Forest Test F1: {if_test_metrics.f1_macro:.4f}")


if __name__ == "__main__":
    main()
