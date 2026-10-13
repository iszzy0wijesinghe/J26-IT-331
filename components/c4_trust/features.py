from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class BehavioralFeatures:
    """Behavioral features for C4 ML models (B0-B5)."""

    # B0 - Timing Features
    tx_interval_s: float
    rx_delay_s: float
    freshness_status_encoded: int

    # B1 - Radio Features
    rssi_dbm: float
    rssi_deviation_db: float
    snr_db: float
    retry_count: int

    # B2 - Packet Behavior
    packet_size_bytes: int
    counter_delta: int

    # B3 - Device Health
    battery_pct: float
    battery_voltage_v: float
    current_ma: float
    reboot_count_24h: int
    sensor_fault_flag: int

    # B4 - Path/Location (comparison flags)
    zone_match: int
    hub_match_flag: int

    # B5 - Historical Features (to be computed per device)
    rolling_interval_mean: float | None = None
    rolling_interval_std: float | None = None
    rolling_rssi_mean: float | None = None
    rolling_rssi_std: float | None = None
    rolling_retry_mean: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for ML input."""
        return {
            # B0 - Timing
            "tx_interval_s": self.tx_interval_s,
            "rx_delay_s": self.rx_delay_s,
            "freshness_status_encoded": self.freshness_status_encoded,
            # B1 - Radio
            "rssi_dbm": self.rssi_dbm,
            "rssi_deviation_db": self.rssi_deviation_db,
            "snr_db": self.snr_db,
            "retry_count": self.retry_count,
            # B2 - Packet
            "packet_size_bytes": self.packet_size_bytes,
            "counter_delta": self.counter_delta,
            # B3 - Health
            "battery_pct": self.battery_pct,
            "battery_voltage_v": self.battery_voltage_v,
            "current_ma": self.current_ma,
            "reboot_count_24h": self.reboot_count_24h,
            "sensor_fault_flag": self.sensor_fault_flag,
            # B4 - Path
            "zone_match": self.zone_match,
            "hub_match_flag": self.hub_match_flag,
            # B5 - Historical (if available)
            "rolling_interval_mean": self.rolling_interval_mean,
            "rolling_interval_std": self.rolling_interval_std,
            "rolling_rssi_mean": self.rolling_rssi_mean,
            "rolling_rssi_std": self.rolling_rssi_std,
            "rolling_retry_mean": self.rolling_retry_mean,
        }


class FeatureExtractor:
    """Extract behavioral features from C4 dataset.

    This extracts only behavioral features (B0-B5) and excludes
    deterministic security fields to prevent leakage.
    """

    # Fields to EXCLUDE (deterministic security fields that cause leakage)
    EXCLUDED_FIELDS = {
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
        # Also exclude metadata fields
        "packet_id",
        "device_id",
        "device_timestamp",
        "received_timestamp",
        "device_kind",
        "cert_fingerprint",
        "firmware_hash",
        "config_hash",
        "prev_hash",
        "record_hash",
        "nonce",
        "scenario",
        "trust_label",
        "label_id",
        "is_malicious",
        "label_untrusted_binary",
        "c4_decision",
        "c4_trust_score",
        "reason_code",
        "split",
    }

    # Behavioral feature fields to INCLUDE
    BEHAVIORAL_FIELDS = {
        # B0 - Timing
        "tx_interval_s",
        "rx_delay_s",
        "freshness_status",
        # B1 - Radio
        "rssi_dbm",
        "rssi_deviation_db",
        "snr_db",
        "retry_count",
        # B2 - Packet
        "packet_size_bytes",
        "counter_delta",
        # B3 - Health
        "battery_pct",
        "battery_voltage_v",
        "current_ma",
        "reboot_count_24h",
        "sensor_fault_flag",
        # B4 - Path (derived from comparison)
        "zone_registered",
        "zone_reported",
        "hub_registered",
        "hub_id",
    }

    def __init__(self) -> None:
        self._freshness_status_encoding = {
            "fresh": 0,
            "delayed": 1,
            "stale": 2,
        }

    def extract_from_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract behavioral features from dataframe.

        Args:
            df: Input dataframe with C4 dataset columns

        Returns:
            DataFrame with only behavioral features
        """
        # Create a copy to avoid modifying original
        features_df = df.copy()

        # Encode freshness_status
        features_df["freshness_status_encoded"] = features_df[
            "freshness_status"
        ].map(self._freshness_status_encoding).fillna(0)

        # Create comparison flags for path/location
        features_df["zone_match"] = (
            features_df["zone_registered"] == features_df["zone_reported"]
        ).astype(int)
        features_df["hub_match_flag"] = (
            features_df["hub_registered"] == features_df["hub_id"]
        ).astype(int)

        # Select only behavioral fields
        selected_columns = [
            # B0 - Timing
            "tx_interval_s",
            "rx_delay_s",
            "freshness_status_encoded",
            # B1 - Radio
            "rssi_dbm",
            "rssi_deviation_db",
            "snr_db",
            "retry_count",
            # B2 - Packet
            "packet_size_bytes",
            "counter_delta",
            # B3 - Health
            "battery_pct",
            "battery_voltage_v",
            "current_ma",
            "reboot_count_24h",
            "sensor_fault_flag",
            # B4 - Path
            "zone_match",
            "hub_match_flag",
        ]

        features_df = features_df[selected_columns]

        return features_df

    def add_historical_features(
        self,
        df: pd.DataFrame,
        device_id_col: str = "device_id",
        window: int = 10,
    ) -> pd.DataFrame:
        """Add rolling historical features per device.

        Args:
            df: Input dataframe with device_id and behavioral features
            device_id_col: Name of device_id column
            window: Rolling window size

        Returns:
            DataFrame with added historical features
        """
        df = df.copy()

        # Sort by device_id and timestamp if available
        if "device_timestamp" in df.columns:
            df = df.sort_values([device_id_col, "device_timestamp"])
        else:
            df = df.sort_values(device_id_col)

        # Compute rolling features per device
        for device_id, group in df.groupby(device_id_col):
            device_idx = df[device_id_col] == device_id

            # Rolling interval statistics
            if "tx_interval_s" in df.columns:
                df.loc[device_idx, "rolling_interval_mean"] = group[
                    "tx_interval_s"
                ].rolling(window=window, min_periods=1).mean()
                df.loc[device_idx, "rolling_interval_std"] = group[
                    "tx_interval_s"
                ].rolling(window=window, min_periods=1).std()

            # Rolling RSSI statistics
            if "rssi_dbm" in df.columns:
                df.loc[device_idx, "rolling_rssi_mean"] = group[
                    "rssi_dbm"
                ].rolling(window=window, min_periods=1).mean()
                df.loc[device_idx, "rolling_rssi_std"] = group[
                    "rssi_dbm"
                ].rolling(window=window, min_periods=1).std()

            # Rolling retry statistics
            if "retry_count" in df.columns:
                df.loc[device_idx, "rolling_retry_mean"] = group[
                    "retry_count"
                ].rolling(window=window, min_periods=1).mean()

        # Fill NaN values with 0 for first rows
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

    def extract_for_training(
        self,
        df: pd.DataFrame,
        add_historical: bool = True,
        historical_window: int = 10,
    ) -> tuple[pd.DataFrame, pd.Series]:
        """Extract features and labels for ML training.

        Args:
            df: Input C4 dataset
            add_historical: Whether to add rolling historical features
            historical_window: Window size for historical features

        Returns:
            Tuple of (features DataFrame, labels Series)
        """
        # Extract behavioral features
        features_df = self.extract_from_dataframe(df)

        # Add historical features if requested
        if add_historical:
            features_df = self.add_historical_features(
                df,
                device_id_col="device_id",
                window=historical_window,
            )

        # Extract labels
        labels = df["trust_label"].copy()

        return features_df, labels

    def create_behavioral_dataset(
        self,
        input_path: str,
        output_path: str,
        add_historical: bool = True,
        historical_window: int = 10,
    ) -> None:
        """Create clean behavioral dataset from C4_Trust.csv.

        Args:
            input_path: Path to C4_Trust.csv
            output_path: Path to save behavioral dataset
            add_historical: Whether to add historical features
            historical_window: Window size for historical features
        """
        # Load dataset
        df = pd.read_csv(input_path)

        # Extract features and labels
        features_df, labels = self.extract_for_training(
            df,
            add_historical=add_historical,
            historical_window=historical_window,
        )

        # Combine features with labels and metadata
        output_df = features_df.copy()
        output_df["trust_label"] = labels
        output_df["split"] = df["split"]
        output_df["scenario"] = df["scenario"]
        output_df["device_id"] = df["device_id"]

        # Save to CSV
        output_df.to_csv(output_path, index=False)

        print(f"Behavioral dataset saved to {output_path}")
        print(f"Shape: {output_df.shape}")
        print(f"Features: {len(features_df.columns)}")
        print(f"Label distribution:\n{labels.value_counts()}")


def load_and_extract_features(
    dataset_path: str,
    add_historical: bool = True,
    historical_window: int = 10,
) -> tuple[pd.DataFrame, pd.Series]:
    """Load C4 dataset and extract behavioral features.

    Args:
        dataset_path: Path to C4_Trust.csv
        add_historical: Whether to add historical features
        historical_window: Window size for historical features

    Returns:
        Tuple of (features DataFrame, labels Series)
    """
    df = pd.read_csv(dataset_path)
    extractor = FeatureExtractor()
    return extractor.extract_for_training(
        df,
        add_historical=add_historical,
        historical_window=historical_window,
    )
