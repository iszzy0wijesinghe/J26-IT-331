
from pathlib import Path

import pandas as pd

path = Path(r"C:\Users\User\Desktop\Dataset\all datasets\C4_Trust.csv")
df = pd.read_csv(path, low_memory=False)

print("=== Dataset columns ===")
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")
for column in df.columns:
    print(column)

keywords = (
    "id",
    "sequence",
    "seq",
    "packet",
    "event",
    "scenario",
    "attack",
    "source",
    "label",
    "timestamp",
)

candidates = [
    column
    for column in df.columns
    if any(keyword in column.lower() for keyword in keywords)
]

print("\n=== Candidate identity and provenance columns ===")
for column in candidates:
    series = df[column]
    print(f"\n{column}")
    print(f"  Non-null: {int(series.notna().sum())}")
    print(f"  Unique values: {int(series.nunique(dropna=True))}")
    print(f"  Duplicate non-null values: {int(series.dropna().duplicated().sum())}")
    print(f"  Example values: {series.dropna().head(5).tolist()}")

print("\n=== Dataset identity inspection complete ===")
print("Source data was not modified.")
