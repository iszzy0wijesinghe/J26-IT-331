"""Create train/val/test splits for C4 dataset using existing split column.

This script:
1. Loads the behavioral C4 dataset
2. Uses the existing split column (already has good distribution)
3. Saves train/val/test splits to CSV files
"""

import sys
from pathlib import Path

import pandas as pd

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main() -> None:
    # Paths
    input_path = r"C:\Users\User\Desktop\FInal_GeoNex_Repo\J26-IT-331\experiments\c4\data\C4_Behavioral_Dataset.csv"
    output_dir = Path(r"C:\Users\User\Desktop\FInal_GeoNex_Repo\J26-IT-331\experiments\c4\data")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load dataset
    print("Loading behavioral dataset...")
    df = pd.read_csv(input_path)

    # Split by existing split column
    print("Splitting by existing split column...")
    train_df = df[df["split"] == "train"].copy()
    val_df = df[df["split"] == "val"].copy()
    test_df = df[df["split"] == "test"].copy()

    # Save splits
    for split_name, split_df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        output_path = output_dir / f"C4_{split_name}.csv"
        split_df.to_csv(output_path, index=False)
        print(f"\nSaved {split_name} split to {output_path}")
        print(f"  Shape: {split_df.shape}")
        print(f"  Scenarios: {split_df['scenario'].unique()}")
        print(f"  Label distribution:\n{split_df['trust_label'].value_counts()}")

    print(f"\nTotal records: {len(df)}")
    print(f"Train: {len(train_df)} ({len(train_df)/len(df)*100:.1f}%)")
    print(f"Val: {len(val_df)} ({len(val_df)/len(df)*100:.1f}%)")
    print(f"Test: {len(test_df)} ({len(test_df)/len(df)*100:.1f}%)")

    print("\nDone!")


if __name__ == "__main__":
    main()
