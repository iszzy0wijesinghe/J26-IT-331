from pathlib import Path

import numpy as np
import pandas as pd

path = Path(r"C:\Users\User\Desktop\Dataset\all datasets\C4_Trust.csv")
df = pd.read_csv(path, low_memory=False)

print("=== C4 Behavioral Feature Semantics Audit ===")
print(f"Rows: {len(df)}")
print(f"Devices: {df['device_id'].nunique()}")

required = [
    "device_id",
    "device_timestamp",
    "received_timestamp",
    "tx_interval_s",
    "rx_delay_s",
    "freshness_status",
    "rssi_dbm",
    "rssi_deviation_db",
    "packet_size_bytes",
    "battery_pct",
    "battery_voltage_v",
    "current_ma",
    "snr_db",
    "retry_count",
    "trust_label",
]

missing = [column for column in required if column not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

for column in ["device_timestamp", "received_timestamp"]:
    df[column] = pd.to_datetime(df[column], utc=True, errors="coerce")

print("\n=== Invalid or missing values ===")
for column in required:
    print(f"{column}: {df[column].isna().sum()} missing/invalid")

print("\n=== Receive delay vs timestamp difference ===")
valid = df["device_timestamp"].notna() & df["received_timestamp"].notna()
derived_delay = (
    df.loc[valid, "received_timestamp"]
    - df.loc[valid, "device_timestamp"]
).dt.total_seconds()

recorded_delay = pd.to_numeric(df.loc[valid, "rx_delay_s"], errors="coerce")
delay_valid = derived_delay.notna() & recorded_delay.notna()
delay_diff = derived_delay[delay_valid] - recorded_delay[delay_valid]

print("Comparable rows:", len(delay_diff))
print("Exact matches:", int(np.isclose(delay_diff, 0).sum()), "/", len(delay_diff))
print("Absolute difference quantiles:")
print(delay_diff.abs().quantile([0, 0.5, 0.9, 0.99, 1]).to_string())

print("\n=== Transmission interval vs previous packet per device ===")
ordered = df.dropna(subset=["device_id", "device_timestamp"]).copy()
ordered = ordered.sort_values(
    ["device_id", "device_timestamp"], kind="stable"
)

derived_interval = (
    ordered.groupby("device_id")["device_timestamp"]
    .diff()
    .dt.total_seconds()
)
recorded_interval = pd.to_numeric(ordered["tx_interval_s"], errors="coerce")
has_previous = derived_interval.notna()
interval_valid = has_previous & recorded_interval.notna() & derived_interval.notna()
interval_diff = recorded_interval[interval_valid] - derived_interval[interval_valid]

print("Rows with a previous packet:", int(has_previous.sum()))
print("Comparable intervals:", len(interval_diff))
print(
    "Exact matches:",
    int(np.isclose(interval_diff, 0).sum()),
    "/",
    len(interval_diff),
)
print("Recorded interval values:")
print(ordered["tx_interval_s"].value_counts(dropna=False).head(10).to_string())
print("Derived interval quantiles:")
print(
    derived_interval.dropna()
    .quantile([0, 0.25, 0.5, 0.75, 0.9, 1])
    .to_string()
)

print("\n=== RSSI deviation candidate definitions ===")
ordered["previous_rssi"] = ordered.groupby("device_id")["rssi_dbm"].shift(1)
ordered["previous_rssi_delta"] = (
    ordered["rssi_dbm"] - ordered["previous_rssi"]
)
ordered["device_rssi_mean"] = ordered.groupby("device_id")["rssi_dbm"].transform("mean")

candidates = {
    "current minus previous RSSI": ordered["previous_rssi_delta"],
    "current minus whole-device mean RSSI": (
        ordered["rssi_dbm"] - ordered["device_rssi_mean"]
    ),
}

for name, candidate in candidates.items():
    recorded = pd.to_numeric(ordered["rssi_deviation_db"], errors="coerce")
    mask = candidate.notna() & recorded.notna()
    diff = recorded[mask] - candidate[mask]
    print(f"{name}: exact matches {int(np.isclose(diff, 0).sum())}/{len(diff)}")
    if not diff.empty:
        print("  Median absolute difference:", float(diff.abs().median()))

print("\n=== Feature ranges and label distributions ===")
range_columns = [
    "rssi_deviation_db",
    "packet_size_bytes",
    "battery_pct",
    "battery_voltage_v",
    "current_ma",
    "snr_db",
    "retry_count",
    "reboot_count_24h",
    "sensor_fault_flag",
]

for column in range_columns:
    print(f"\n{column}:")
    if column not in df.columns:
        print("Column unavailable")
        continue

    print(
        df.groupby("trust_label", dropna=False)[column]
        .agg(["count", "min", "median", "max"])
        .to_string()
    )

print("\n=== Freshness values by label ===")
print(pd.crosstab(df["trust_label"], df["freshness_status"], dropna=False))

print("\n=== Repeated timestamp counts ===")
print(
    "Duplicate device/timestamp rows:",
    int(df.duplicated(["device_id", "device_timestamp"], keep=False).sum()),
)

print("\nAudit complete. No source data or model files were modified.")

