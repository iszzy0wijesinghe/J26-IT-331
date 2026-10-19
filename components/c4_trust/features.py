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
            # B3 - Health
            "battery_pct": self.battery_pct,
            "battery_voltage_v": self.battery_voltage_v,
            "current_ma": self.current_ma,
            "reboot_count_24h": self.reboot_count_24h,
            "sensor_fault_flag": self.sensor_fault_flag,
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

    TRAINING_FEATURE_FIELDS = (
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
    )

    def __init__(self) -> None:
        self._freshness_status_encoding = {
            "fresh": 0,
            "delayed": 1,
            "stale": 2,
        }
        # Expected intervals per mode (in seconds) - reserved for future use
        # These should be configured based on actual sampling policies
        self._mode_expected_intervals = {
            "IDLE": 30.0,  # Normal low-power mode
            "ACTIVE": 10.0,  # Normal active sampling
            "WARNING": 5.0,  # High-risk mode, frequent sampling
            "CRITICAL": 1.0,  # Emergency mode, very frequent sampling
            "DEEP_SLEEP": 300.0,  # Very low power mode
            "UNKNOWN": 10.0,  # Default fallback
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
            # B3 - Health
            "battery_pct",
            "battery_voltage_v",
            "current_ma",
            "reboot_count_24h",
            "sensor_fault_flag",
        ]

        features_df = features_df[selected_columns]

        return features_df

    def add_mode_aware_features(
        self,
        df: pd.DataFrame,
        mode_col: str = "mode",
    ) -> pd.DataFrame:
        """Add mode-aware interval deviation features.

        Reserved for future use when mode information is available.

        Args:
            df: Input dataframe with mode and tx_interval_s columns
            mode_col: Name of mode column

        Returns:
            DataFrame with added mode-aware features (empty for now)
        """
        df = df.copy()

        # Mode-aware features are not currently supported in the dataset
        # This method is reserved for future implementation when mode information
        # is available in the telemetry protocol
        return df

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
        if device_id_col not in df.columns:
            raise ValueError(f"{device_id_col} is required to calculate historical features")
        if "device_timestamp" not in df.columns:
            raise ValueError("device_timestamp is required to calculate historical features")

        timestamps = pd.to_datetime(
            df["device_timestamp"], format="mixed", utc=True, errors="coerce"
        )
        if timestamps.isna().any():
            raise ValueError("device_timestamp contains missing or invalid values")

        original_index = df.index
        timestamp_key = "__c4_history_timestamp"
        position_key = "__c4_history_position"
        while timestamp_key in df.columns:
            timestamp_key = f"_{timestamp_key}"
        while position_key in df.columns or position_key == timestamp_key:
            position_key = f"_{position_key}"

        df = df.copy().reset_index(drop=True)
        df[position_key] = range(len(df))
        df[timestamp_key] = timestamps.array
        df = df.sort_values([device_id_col, timestamp_key], kind="stable")

        # Treat tied timestamps as one step so peers cannot affect one another.
        feature_sources = {
            "tx_interval_s": ("rolling_interval_mean", "rolling_interval_std"),
            "rssi_dbm": ("rolling_rssi_mean", "rolling_rssi_std"),
            "retry_count": ("rolling_retry_mean", None),
        }
        for _, device_group in df.groupby(device_id_col, sort=False):
            timestamp_groups = device_group.groupby(timestamp_key, sort=True)
            for source_column, (mean_column, std_column) in feature_sources.items():
                if source_column not in df.columns:
                    continue

                timestamp_means = timestamp_groups[source_column].mean()
                previous_values = timestamp_means.shift(1)
                rolling_mean = previous_values.rolling(
                    window=window, min_periods=1
                ).mean()
                df.loc[device_group.index, mean_column] = device_group[timestamp_key].map(
                    rolling_mean
                ).to_numpy()

                if std_column is not None:
                    rolling_std = previous_values.rolling(
                        window=window, min_periods=1
                    ).std()
                    df.loc[device_group.index, std_column] = device_group[timestamp_key].map(
                        rolling_std
                    ).to_numpy()

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

        positions = df.pop(position_key).to_numpy()
        df = df.drop(columns=timestamp_key)
        df.index = original_index.take(positions)
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
        # Accept either raw C4 rows or an already-extracted behavioral dataset.
        if self.BEHAVIORAL_FIELDS.issubset(df.columns):
            features_df = self.extract_from_dataframe(df)
        else:
            available_fields = [
                column for column in self.TRAINING_FEATURE_FIELDS if column in df.columns
            ]
            if not available_fields:
                raise ValueError("Input dataframe has no recognized C4 behavioral features")
            features_df = df[available_fields].copy()

        # Add historical features if requested
        history_sources = {"tx_interval_s", "rssi_dbm", "retry_count"} & set(df.columns)
        if add_historical and history_sources:
            if "device_id" not in df.columns:
                raise ValueError("device_id is required to calculate historical features")
            history_input_columns = [
                column
                for column in (
                    "device_id",
                    "device_timestamp",
                    "tx_interval_s",
                    "rssi_dbm",
                    "retry_count",
                )
                if column in df.columns
            ]
            history_features = self.add_historical_features(
                df[history_input_columns],
                device_id_col="device_id",
                window=historical_window,
            )
            historical_columns = [
                "rolling_interval_mean",
                "rolling_interval_std",
                "rolling_rssi_mean",
                "rolling_rssi_std",
                "rolling_retry_mean",
            ]
            features_df = features_df.drop(
                columns=[column for column in historical_columns if column in features_df]
            )
            features_df = features_df.join(
                history_features[
                    [column for column in historical_columns if column in history_features]
                ]
            )

        feature_columns = [
            column for column in self.TRAINING_FEATURE_FIELDS if column in features_df
        ]
        features_df = features_df[feature_columns]

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
        output_df["scenario"] = df["scenario"]
        output_df["device_id"] = df["device_id"]
        output_df["device_timestamp"] = df["device_timestamp"]

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
