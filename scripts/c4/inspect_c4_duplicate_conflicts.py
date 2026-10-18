from pathlib import Path

import pandas as pd

path = Path(r"C:\Users\User\Desktop\Dataset\all datasets\C4_Trust.csv")
df = pd.read_csv(path, low_memory=False)

df["device_timestamp"] = pd.to_datetime(
    df["device_timestamp"], utc=True, errors="coerce"
)

valid = df.dropna(subset=["device_id", "device_timestamp"]).copy()
key = ["device_id", "device_timestamp"]

duplicate_mask = valid.duplicated(key, keep=False)
duplicates = valid.loc[duplicate_mask].copy()

print("=== Exact duplicate row audit ===")
print(f"Rows in timestamp duplicate groups: {len(duplicates)}")

exact_duplicate_mask = duplicates.duplicated(keep=False)
print(
    "Rows participating in exact duplicate rows:",
    int(exact_duplicate_mask.sum()),
)

print("\n=== Duplicate groups with different labels ===")
label_counts = duplicates.groupby(key)["trust_label"].nunique()
conflicting_keys = label_counts[label_counts > 1].index

if len(conflicting_keys):
    conflicting = duplicates.set_index(key).loc[conflicting_keys].reset_index()
    print(f"Groups with conflicting labels: {len(conflicting_keys)}")
    print(
        conflicting[
            [
                "device_id",
                "device_timestamp",
                "received_timestamp",
                "trust_label",
                "rx_delay_s",
                "rssi_dbm",
                "rssi_deviation_db",
                "retry_count",
            ]
        ].head(30).to_string(index=False)
    )
else:
    print("No conflicting-label groups found.")

print("\n=== Feature variation within duplicate groups ===")
feature_columns = [
    column
    for column in [
        "received_timestamp",
        "trust_label",
        "rx_delay_s",
        "rssi_dbm",
        "rssi_deviation_db",
        "packet_size_bytes",
        "battery_pct",
        "current_ma",
        "snr_db",
        "retry_count",
        "freshness_status",
    ]
    if column in duplicates.columns
]

variation = duplicates.groupby(key)[feature_columns].nunique(dropna=False)
for column in feature_columns:
    print(
        f"{column}: groups with multiple values = "
        f"{int((variation[column] > 1).sum())}"
    )

print("\nAudit complete. Source data was not modified.")
