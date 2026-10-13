"""Runtime feature adapter for C4 behavioral ML scoring.

This module extracts behavioral features from live TelemetryPacket instances
for use with trained C4 models. It enforces the same semantics used during
training and fails closed when required features are unavailable or invalid.
"""

from __future__ import annotations

import json
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from components.c4_trust.models import ModelSchemaError
from shared.contracts.telemetry import TelemetryPacket


@dataclass
class FeatureError(ValueError):
    """A required feature could not be extracted or is invalid."""

    packet_id: str
    device_id: str
    reason: str


C4_MODEL_FEATURE_SCHEMA = (
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

FRESHNESS_ENCODING = {
    "fresh": 0,
    "delayed": 1,
    "stale": 2,
}


@dataclass
class DeviceHistory:
    """Per-device rolling history for behavioral features."""

    device_id: str
    window_size: int = 10

    intervals: deque[float] = field(default_factory=deque)
    rssi_values: deque[float] = field(default_factory=deque)
    retry_counts: deque[int] = field(default_factory=deque)
    timestamps: deque[datetime] = field(default_factory=deque)

    def add_observation(
        self,
        observed_at: datetime,
        tx_interval_s: float | None,
        rssi_dbm: float | None,
        retry_count: int | None,
    ) -> None:
        """Add a new observation to the device history."""
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")

        if observed_at.tzinfo != UTC:
            observed_at = observed_at.astimezone(UTC)

        self.timestamps.append(observed_at)

        if tx_interval_s is not None:
            self.intervals.append(tx_interval_s)

        if rssi_dbm is not None:
            self.rssi_values.append(rssi_dbm)

        if retry_count is not None:
            self.retry_counts.append(retry_count)

        while len(self.timestamps) > self.window_size:
            self.timestamps.popleft()

        while len(self.intervals) > self.window_size:
            self.intervals.popleft()

        while len(self.rssi_values) > self.window_size:
            self.rssi_values.popleft()

        while len(self.retry_counts) > self.window_size:
            self.retry_counts.popleft()

    def get_rolling_features(self) -> dict[str, float]:
        """Calculate rolling features from current history."""
        features = {
            "rolling_interval_mean": 0.0,
            "rolling_interval_std": 0.0,
            "rolling_rssi_mean": 0.0,
            "rolling_rssi_std": 0.0,
            "rolling_retry_mean": 0.0,
        }

        if len(self.intervals) > 0:
            features["rolling_interval_mean"] = float(np.mean(self.intervals))
            if len(self.intervals) > 1:
                features["rolling_interval_std"] = float(np.std(self.intervals))

        if len(self.rssi_values) > 0:
            features["rolling_rssi_mean"] = float(np.mean(self.rssi_values))
            if len(self.rssi_values) > 1:
                features["rolling_rssi_std"] = float(np.std(self.rssi_values))

        if len(self.retry_counts) > 0:
            features["rolling_retry_mean"] = float(np.mean(self.retry_counts))

        return features

    def clear(self) -> None:
        """Clear all history, for example after a device reboot."""
        self.intervals.clear()
        self.rssi_values.clear()
        self.retry_counts.clear()
        self.timestamps.clear()


class RuntimeFeatureAdapter:
    """Extract behavioral features from TelemetryPacket for C4 inference.

    Per-device history is bounded to a rolling window and is lost on restart.
    This is acceptable for the prototype but should be noted for production.
    """

    def __init__(self, history_window: int = 10) -> None:
        """Initialize the adapter."""
        if history_window < 1:
            raise ValueError("history_window must be at least 1")

        self._history_window = history_window
        self._device_histories: dict[str, DeviceHistory] = {}

    def _get_or_create_history(self, device_id: str) -> DeviceHistory:
        """Get or create device history."""
        if device_id not in self._device_histories:
            self._device_histories[device_id] = DeviceHistory(
                device_id=device_id,
                window_size=self._history_window,
            )

        return self._device_histories[device_id]

    def _validate_numeric(
        self,
        value: float | None,
        name: str,
        packet_id: str,
        device_id: str,
        *,
        allow_zero: bool = True,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> float:
        """Validate a numeric feature value."""
        if value is None:
            raise FeatureError(
                packet_id=packet_id,
                device_id=device_id,
                reason=f"Required feature {name} is missing",
            )

        if not isinstance(value, (int, float)):
            raise FeatureError(
                packet_id=packet_id,
                device_id=device_id,
                reason=f"Feature {name} is not numeric: {type(value)}",
            )

        if not math.isfinite(value):
            raise FeatureError(
                packet_id=packet_id,
                device_id=device_id,
                reason=f"Feature {name} is not finite: {value}",
            )

        if not allow_zero and value == 0:
            raise FeatureError(
                packet_id=packet_id,
                device_id=device_id,
                reason=f"Feature {name} is zero but zero is not valid",
            )

        if min_value is not None and value < min_value:
            raise FeatureError(
                packet_id=packet_id,
                device_id=device_id,
                reason=f"Feature {name} {value} is below minimum {min_value}",
            )

        if max_value is not None and value > max_value:
            raise FeatureError(
                packet_id=packet_id,
                device_id=device_id,
                reason=f"Feature {name} {value} exceeds maximum {max_value}",
            )

        return float(value)

    def _encode_freshness(
        self,
        freshness_status: str | None,
        packet_id: str,
        device_id: str,
    ) -> int:
        """Encode freshness status to a numeric value."""
        if freshness_status is None:
            raise FeatureError(
                packet_id=packet_id,
                device_id=device_id,
                reason="Freshness status is missing - cannot assume 'fresh'",
            )

        if freshness_status not in FRESHNESS_ENCODING:
            raise FeatureError(
                packet_id=packet_id,
                device_id=device_id,
                reason=f"Invalid freshness status: {freshness_status}",
            )

        return FRESHNESS_ENCODING[freshness_status]

    def _extract_packet_size(
        self,
        packet: TelemetryPacket,
        packet_id: str,
        device_id: str,
    ) -> int:
        """Calculate serialized JSON size of the telemetry packet."""
        payload = packet.model_dump(mode="json")
        serialized = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        size_bytes = len(serialized.encode("utf-8"))

        if size_bytes <= 0:
            raise FeatureError(
                packet_id=packet_id,
                device_id=device_id,
                reason=f"Invalid packet size: {size_bytes}",
            )

        return size_bytes

    def _calculate_rssi_deviation(
        self,
        rssi_dbm: float,
        packet_id: str,
        device_id: str,
    ) -> float:
        """Calculate RSSI deviation from the device's rolling mean.

        The training data's rssi_deviation_db semantics have not been
        established confidently. This implementation uses deviation from the
        device's rolling mean, which may not match the training semantics.
        """
        history = self._get_or_create_history(device_id)

        if history.rssi_values:
            rolling_mean = float(np.mean(history.rssi_values))
            return rssi_dbm - rolling_mean

        return 0.0

    def extract_features(self, packet: TelemetryPacket) -> pd.DataFrame:
        """Extract features matching the trained C4 model schema."""
        packet_id = packet.packet_id
        device_id = packet.device_id

        try:
            tx_interval_s = self._validate_numeric(
                packet.tx_interval_s,
                "tx_interval_s",
                packet_id,
                device_id,
                allow_zero=False,
                min_value=0.0,
            )

            rx_delay_s = self._validate_numeric(
                (packet.received_at - packet.observed_at).total_seconds(),
                "rx_delay_s",
                packet_id,
                device_id,
                min_value=0.0,
            )

            freshness_status_encoded = self._encode_freshness(
                packet.freshness_status,
                packet_id,
                device_id,
            )

            rssi_dbm = self._validate_numeric(
                packet.transport.rssi_dbm,
                "rssi_dbm",
                packet_id,
                device_id,
                min_value=-150.0,
                max_value=0.0,
            )

            rssi_deviation_db = self._calculate_rssi_deviation(
                rssi_dbm,
                packet_id,
                device_id,
            )

            snr_db = self._validate_numeric(
                packet.transport.snr_db,
                "snr_db",
                packet_id,
                device_id,
                min_value=-50.0,
                max_value=50.0,
            )

            retry_count = int(
                self._validate_numeric(
                    packet.transport.retry_count,
                    "retry_count",
                    packet_id,
                    device_id,
                    min_value=0,
                )
            )

            packet_size_bytes = self._extract_packet_size(
                packet,
                packet_id,
                device_id,
            )

            battery_pct = self._validate_numeric(
                packet.device_health.battery_pct,
                "battery_pct",
                packet_id,
                device_id,
                min_value=0.0,
                max_value=100.0,
            )

            battery_voltage_v = self._validate_numeric(
                packet.device_health.battery_voltage,
                "battery_voltage_v",
                packet_id,
                device_id,
                min_value=0.0,
                max_value=20.0,
            )

            current_ma = self._validate_numeric(
                packet.device_health.supply_current,
                "current_ma",
                packet_id,
                device_id,
                min_value=0.0,
                max_value=1000.0,
            )

            reboot_count_24h = int(
                self._validate_numeric(
                    packet.device_health.reboot_count_24h,
                    "reboot_count_24h",
                    packet_id,
                    device_id,
                    min_value=0,
                )
            )

            sensor_fault_flag = 1 if packet.device_health.sensor_fault_flag else 0

        except FeatureError as exc:
            raise FeatureError(
                packet_id=packet_id,
                device_id=device_id,
                reason=exc.reason,
            ) from exc

        history = self._get_or_create_history(device_id)
        history.add_observation(
            observed_at=packet.observed_at,
            tx_interval_s=tx_interval_s,
            rssi_dbm=rssi_dbm,
            retry_count=retry_count,
        )

        rolling_features = history.get_rolling_features()

        feature_row = {
            "tx_interval_s": tx_interval_s,
            "rx_delay_s": rx_delay_s,
            "freshness_status_encoded": freshness_status_encoded,
            "rssi_dbm": rssi_dbm,
            "rssi_deviation_db": rssi_deviation_db,
            "snr_db": snr_db,
            "retry_count": retry_count,
            "packet_size_bytes": packet_size_bytes,
            "battery_pct": battery_pct,
            "battery_voltage_v": battery_voltage_v,
            "current_ma": current_ma,
            "reboot_count_24h": reboot_count_24h,
            "sensor_fault_flag": sensor_fault_flag,
            **rolling_features,
        }

        if set(feature_row) != set(C4_MODEL_FEATURE_SCHEMA):
            raise ModelSchemaError(
                "Feature extraction produced unexpected columns: "
                f"{set(feature_row)} vs expected "
                f"{set(C4_MODEL_FEATURE_SCHEMA)}"
            )

        return pd.DataFrame([feature_row], columns=C4_MODEL_FEATURE_SCHEMA)

    def clear_device_history(self, device_id: str) -> None:
        """Clear history for a specific device."""
        if device_id in self._device_histories:
            self._device_histories[device_id].clear()

    def clear_all_history(self) -> None:
        """Clear history for all devices."""
        self._device_histories.clear()
