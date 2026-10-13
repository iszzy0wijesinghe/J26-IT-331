"""Retrain C4 model with corrected feature semantics.

This script addresses the semantic issues identified in the audit:
1. tx_interval_s: Use actual derived interval, not constant 30
2. rssi_deviation_db: Use deviation from device mean
3. freshness_status: Do not fill missing with 0
4. Duplicate timestamps: Group by timestamp before rolling calculations
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to Python path (required for script imports)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from components.c4_trust.models import BaselineModel, ModelType  # noqa: E402


def load_and_preprocess_dataset(dataset_path: str) -> pd.DataFrame:
    """Load and preprocess the C4 dataset with corrected semantics.

    Args:
        dataset_path: Path to C4_Trust.csv

    Returns:
        Preprocessed DataFrame with corrected features
    """
    print(f"Loading dataset from {dataset_path}...")
    df = pd.read_csv(dataset_path, low_memory=False)

    print(f"Loaded {len(df)} rows from {df['device_id'].nunique()} devices")

    # Convert timestamps
    df["device_timestamp"] = pd.to_datetime(df["device_timestamp"], utc=True, errors="coerce")
    df["received_timestamp"] = pd.to_datetime(df["received_timestamp"], utc=True, errors="coerce")

    # Filter rows with invalid timestamps
    valid_timestamps = df["device_timestamp"].notna() & df["received_timestamp"].notna()
    df = df[valid_timestamps].copy()
    print(f"Rows with valid timestamps: {len(df)}")

    # Calculate derived tx_interval_s (actual interval between packets)
    df = df.sort_values(["device_id", "device_timestamp"], kind="stable")
    df["derived_tx_interval_s"] = (
        df.groupby("device_id")["device_timestamp"].diff().dt.total_seconds()
    )

    # For first packet per device, use the recorded tx_interval_s as fallback
    first_packet_mask = df["derived_tx_interval_s"].isna()
    df.loc[first_packet_mask, "derived_tx_interval_s"] = df.loc[first_packet_mask, "tx_interval_s"]

    # Replace constant tx_interval_s with derived interval
    df["tx_interval_s"] = df["derived_tx_interval_s"]

    # Calculate rx_delay_s from timestamps (should match recorded)
    df["derived_rx_delay_s"] = (
        df["received_timestamp"] - df["device_timestamp"]
    ).dt.total_seconds()
    df["rx_delay_s"] = df["derived_rx_delay_s"]

    # Calculate rssi_deviation_db as deviation from device mean
    df["device_rssi_mean"] = df.groupby("device_id")["rssi_dbm"].transform("mean")
    df["rssi_deviation_db"] = df["rssi_dbm"] - df["device_rssi_mean"]

    # Encode freshness_status, but DO NOT fill missing with 0
    freshness_encoding = {"fresh": 0, "delayed": 1, "stale": 2}
    df["freshness_status_encoded"] = df["freshness_status"].map(freshness_encoding)

    # Remove rows with missing freshness status (cannot assume fresh)
    df = df[df["freshness_status_encoded"].notna()].copy()
    print(f"Rows with valid freshness status: {len(df)}")

    # Remove other required fields with missing values
    required_cols = [
        "tx_interval_s",
        "rx_delay_s",
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
    ]
    for col in required_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df[df[col].notna()].copy()

    print(f"Rows with all required features: {len(df)}")

    return df


def add_corrected_historical_features(
    df: pd.DataFrame,
    device_id_col: str = "device_id",
    timestamp_col: str = "device_timestamp",
    window: int = 10,
) -> pd.DataFrame:
    """Add rolling historical features with corrected semantics.

    Key correction: Group by timestamp before calculating rolling features
    to handle duplicate timestamps correctly (treated as one observation).

    Args:
        df: Input dataframe
        device_id_col: Device ID column name
        timestamp_col: Timestamp column name
        window: Rolling window size

    Returns:
        DataFrame with added historical features
    """
    df = df.copy()

    # Sort by device and timestamp
    df = df.sort_values([device_id_col, timestamp_col], kind="stable")

    # Group by (device_id, timestamp) to handle duplicates
    # Take mean of values at the same timestamp
    feature_sources = {
        "tx_interval_s": ("rolling_interval_mean", "rolling_interval_std"),
        "rssi_dbm": ("rolling_rssi_mean", "rolling_rssi_std"),
        "retry_count": ("rolling_retry_mean", None),
    }

    for _device_id, device_group in df.groupby(device_id_col, sort=False):
        # Group by timestamp to handle duplicates
        timestamp_groups = device_group.groupby(timestamp_col, sort=True)

        for source_column, (mean_column, std_column) in feature_sources.items():
            if source_column not in df.columns:
                continue

            # Calculate mean per timestamp (handles duplicates)
            timestamp_means = timestamp_groups[source_column].mean()

            # Shift to get previous timestamp values
            previous_values = timestamp_means.shift(1)

            # Rolling statistics on previous values
            rolling_mean = previous_values.rolling(window=window, min_periods=1).mean()
            df.loc[device_group.index, mean_column] = (
                device_group[timestamp_col].map(rolling_mean).to_numpy()
            )

            if std_column is not None:
                rolling_std = previous_values.rolling(window=window, min_periods=1).std()
                df.loc[device_group.index, std_column] = (
                    device_group[timestamp_col].map(rolling_std).to_numpy()
                )

    # Fill NaN with 0 for first rows (matching training semantics)
    historical_cols = [
        "rolling_interval_mean",
        "rolling_interval_std",
        "rolling_rssi_mean",
        "rolling_rssi_std",
        "rolling_retry_mean",
    ]
    for col in historical_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    return df


def create_device_aware_splits(
    df: pd.DataFrame,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_seed: int = 42,
) -> dict[str, pd.DataFrame]:
    """Create train/val/test splits held out by device.

    This prevents device shortcut leakage in evaluation.

    Args:
        df: Input dataframe
        train_ratio: Training proportion
        val_ratio: Validation proportion
        test_ratio: Test proportion
        random_seed: Random seed

    Returns:
        Dictionary with train, val, test dataframes
    """
    if not abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6:
        raise ValueError("Split ratios must sum to 1.0")

    devices = df["device_id"].unique()
    np.random.seed(random_seed)
    np.random.shuffle(devices)

    n_devices = len(devices)
    n_train = int(n_devices * train_ratio)
    n_val = int(n_devices * val_ratio)

    train_devices = devices[:n_train]
    val_devices = devices[n_train : n_train + n_val]
    test_devices = devices[n_train + n_val :]

    train_df = df[df["device_id"].isin(train_devices)].copy()
    val_df = df[df["device_id"].isin(val_devices)].copy()
    test_df = df[df["device_id"].isin(test_devices)].copy()

    return {
        "train": train_df,
        "val": val_df,
        "test": test_df,
    }


def prepare_features_labels(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Separate features and labels.

    Args:
        df: Input dataframe

    Returns:
        Tuple of (features DataFrame, labels Series)
    """
    # Select only the 18 training features
    feature_cols = [
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

    X = df[feature_cols].copy()
    y = df["trust_label"].copy()

    return X, y


def main() -> None:
    # Paths
    dataset_path = r"c:\Users\User\Desktop\Dataset\all datasets\C4_Trust.csv"
    output_dir = Path(r"C:\Users\User\Desktop\FInal_GeoNex_Repo\J26-IT-331\experiments\c4")
    models_dir = output_dir / "models"
    data_dir = output_dir / "data"
    models_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    # Load and preprocess with corrected semantics
    print("=" * 60)
    print("Step 1: Load and preprocess dataset with corrected semantics")
    print("=" * 60)
    df = load_and_preprocess_dataset(dataset_path)

    # Add historical features with corrected duplicate handling
    print("\n" + "=" * 60)
    print("Step 2: Add historical features (corrected duplicate handling)")
    print("=" * 60)
    df = add_corrected_historical_features(df, window=10)

    # Create device-aware splits
    print("\n" + "=" * 60)
    print("Step 3: Create device-aware train/val/test splits")
    print("=" * 60)
    splits = create_device_aware_splits(df)
    print(f"Train: {len(splits['train'])} ({splits['train']['device_id'].nunique()} devices)")
    print(f"Val: {len(splits['val'])} ({splits['val']['device_id'].nunique()} devices)")
    print(f"Test: {len(splits['test'])} ({splits['test']['device_id'].nunique()} devices)")

    # Prepare features and labels
    print("\n" + "=" * 60)
    print("Step 4: Prepare features and labels")
    print("=" * 60)
    X_train, y_train = prepare_features_labels(splits["train"])
    X_val, y_val = prepare_features_labels(splits["val"])
    X_test, y_test = prepare_features_labels(splits["test"])

    print(f"Train features: {X_train.shape}")
    print(f"Val features: {X_val.shape}")
    print(f"Test features: {X_test.shape}")

    # Train Random Forest model
    print("\n" + "=" * 60)
    print("Step 5: Train Random Forest model")
    print("=" * 60)
    rf_baseline = BaselineModel(model_type=ModelType.RANDOM_FOREST)
    rf_trained = rf_baseline.fit(X_train, y_train, X_val, y_val)

    # Evaluate on test set
    print("\n" + "=" * 60)
    print("Step 6: Evaluate on test set")
    print("=" * 60)
    test_metrics = rf_baseline.evaluate(X_test, y_test)

    print("\nTest Metrics:")
    print(f"  Accuracy: {test_metrics.accuracy:.4f}")
    print(f"  Macro Precision: {test_metrics.precision_macro:.4f}")
    print(f"  Macro Recall: {test_metrics.recall_macro:.4f}")
    print(f"  Macro F1: {test_metrics.f1_macro:.4f}")

    print("\nPer-Class Metrics:")
    for label in test_metrics.f1_per_class:
        print(f"  {label}:")
        print(f"    Precision: {test_metrics.precision_per_class[label]:.4f}")
        print(f"    Recall: {test_metrics.recall_per_class[label]:.4f}")
        print(f"    F1: {test_metrics.f1_per_class[label]:.4f}")

    print("\nConfusion Matrix:")
    print(test_metrics.confusion_matrix)

    # Feature importance
    print("\nTop 10 Feature Importances:")
    importance = rf_baseline.get_feature_importance()
    if importance:
        for feat, imp in sorted(importance.items(), key=lambda x: -x[1])[:10]:
            print(f"  {feat}: {imp:.4f}")

    # Save model
    print("\n" + "=" * 60)
    print("Step 7: Save trained model")
    print("=" * 60)
    model_path = models_dir / "random_forest_corrected.joblib"
    rf_trained.save(model_path)
    print(f"Model saved to {model_path}")

    # Save splits for reference
    print("\n" + "=" * 60)
    print("Step 8: Save splits for reference")
    print("=" * 60)
    splits["train"].to_csv(data_dir / "C4_train_corrected.csv", index=False)
    splits["val"].to_csv(data_dir / "C4_val_corrected.csv", index=False)
    splits["test"].to_csv(data_dir / "C4_test_corrected.csv", index=False)
    print(f"Splits saved to {data_dir}")

    print("\n" + "=" * 60)
    print("Retraining Complete!")
    print("=" * 60)
    print("\nSummary:")
    print(f"- Preprocessed dataset: {len(df)} rows")
    print(
        f"- Device-aware splits: {splits['train']['device_id'].nunique()} / "
        f"{splits['val']['device_id'].nunique()} / "
        f"{splits['test']['device_id'].nunique()} devices"
    )
    print(f"- Test Macro F1: {test_metrics.f1_macro:.4f}")
    print(f"- Untrusted Recall: {test_metrics.recall_per_class.get('Untrusted', 0):.4f}")
    print("\nNote: The corrected model uses:")
    print("- Derived tx_interval_s (actual intervals, not constant 30)")
    print("- rssi_deviation_db as deviation from device mean")
    print("- Freshness encoding without filling missing with 0")
    print("- Corrected duplicate timestamp handling")
    print("- Device-aware splits to prevent leakage")


if __name__ == "__main__":
    main()
