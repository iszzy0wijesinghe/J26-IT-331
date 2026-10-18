
from pathlib import Path

import pandas as pd

path = Path(r"C:\Users\User\Desktop\Dataset\all datasets\C4_Trust.csv")
df = pd.read_csv(path, low_memory=False)

print("=== Packet identity ===")
print("Rows:", len(df))
print("Unique packet IDs:", df["packet_id"].nunique())
print("Missing packet IDs:", int(df["packet_id"].isna().sum()))

print("\n=== Split distribution ===")
print(pd.crosstab(df["split"], df["trust_label"], margins=True))

print("\n=== Devices per split ===")
devices_by_split = df.groupby("split")["device_id"].nunique()
print(devices_by_split.to_string())

device_split_counts = df.groupby("device_id")["split"].nunique()
print(
    "Devices appearing in multiple splits:",
    int((device_split_counts > 1).sum()),
)

print("\n=== Scenarios per split ===")
print(pd.crosstab(df["split"], df["scenario"]))

scenario_split_counts = df.groupby("scenario")["split"].nunique()
print("\nScenarios appearing in multiple splits:")
print(scenario_split_counts.to_string())

print("\n=== Device/timestamp groups spanning scenarios ===")
group_scenarios = df.groupby(
    ["device_id", "device_timestamp"]
)["scenario"].nunique()

print(
    "Groups containing multiple scenarios:",
    int((group_scenarios > 1).sum()),
)

print("\n=== Device/timestamp groups spanning labels ===")
group_labels = df.groupby(
    ["device_id", "device_timestamp"]
)["trust_label"].nunique()

print(
    "Groups containing multiple labels:",
    int((group_labels > 1).sum()),
)

print("\nAudit complete. Source data was not modified.")

