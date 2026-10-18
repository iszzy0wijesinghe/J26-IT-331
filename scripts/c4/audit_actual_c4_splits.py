from pathlib import Path

import pandas as pd

data_dir = Path("experiments/c4/data")
names = ("train", "val", "test")
splits = {name: pd.read_csv(data_dir / f"C4_{name}.csv") for name in names}

for name, df in splits.items():
    print(f"\n{name.upper()}: {len(df)} rows")
    print(f"Unique devices: {df['device_id'].nunique()}")
    print(f"Unique scenarios: {df['scenario'].nunique()}")
    print("Labels:")
    print(df["trust_label"].value_counts().to_string())

print("\nDEVICE OVERLAP")
for first, second in (("train", "val"), ("train", "test"), ("val", "test")):
    overlap = set(splits[first]["device_id"]) & set(splits[second]["device_id"])
    print(f"{first} vs {second}: {len(overlap)} overlapping devices")
    if overlap:
        print("Examples:", sorted(overlap)[:10])

print("\nSCENARIO OVERLAP")
for first, second in (("train", "val"), ("train", "test"), ("val", "test")):
    overlap = set(splits[first]["scenario"]) & set(splits[second]["scenario"])
    print(f"{first} vs {second}: {len(overlap)} overlapping scenarios")

print("\nSOURCE DATASET")
source = data_dir / "C4_Behavioral_Dataset.csv"
if source.exists():
    df = pd.read_csv(source)
    print(f"Source rows: {len(df)}")
    print(f"Source devices: {df['device_id'].nunique()}")
    print(f"Source labels:\n{df['trust_label'].value_counts().to_string()}")
    print(f"Split rows total: {sum(len(df) for df in splits.values())}")
    print(f"Split rows match source: {sum(len(df) for df in splits.values()) == len(df)}")
else:
    print(f"Source file not found: {source}")
