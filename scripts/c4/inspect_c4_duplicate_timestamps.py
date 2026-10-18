from pathlib import Path

import pandas as pd

path = Path(r"C:\Users\User\Desktop\Dataset\all datasets\C4_Trust.csv")
df = pd.read_csv(path, low_memory=False)

df["device_timestamp"] = pd.to_datetime(
    df["device_timestamp"], utc=True, errors="coerce"
)

valid = df.dropna(subset=["device_id", "device_timestamp"]).copy()

duplicate_mask = valid.duplicated(
    ["device_id", "device_timestamp"], keep=False
)
duplicates = valid.loc[duplicate_mask].sort_values(
    ["device_id", "device_timestamp"], kind="stable"
)

print("=== Duplicate Device Timestamps ===")
print(f"Rows involved in duplicate groups: {len(duplicates)}")
print(
    "Distinct device/timestamp groups:",
    duplicates.groupby(["device_id", "device_timestamp"]).ngroups,
)

print("\n=== Duplicate group sizes ===")
group_sizes = duplicates.groupby(
    ["device_id", "device_timestamp"]
).size()
print(group_sizes.value_counts().sort_index().to_string())

print("\n=== Labels within duplicate groups ===")
label_counts = duplicates.groupby(
    ["device_id", "device_timestamp"]
)["trust_label"].nunique()
print("Groups containing multiple labels:", int((label_counts > 1).sum()))
print("Groups containing one label:", int((label_counts == 1).sum()))

print("\n=== Example duplicate records ===")
columns = [
    "device_id",
    "device_timestamp",
    "received_timestamp",
    "trust_label",
    "tx_interval_s",
    "rx_delay_s",
    "rssi_dbm",
    "retry_count",
]
print(duplicates[[c for c in columns if c in duplicates.columns]].head(20).to_string(index=False))

print("\nInspection complete. Source data was not modified.")

