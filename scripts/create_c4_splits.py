"""Create device-held-out train/val/test splits for the C4 dataset.

This script:
1. Loads the behavioral C4 dataset
2. Keeps each device in exactly one partition
3. Saves train/val/test splits to CSV files
"""

import sys
from pathlib import Path

import pandas as pd

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from components.c4_trust.data_split import ScenarioAwareSplitter  # noqa: E402


def main() -> None:
    # Paths
    input_path = (
        r"C:\Users\User\Desktop\FInal_GeoNex_Repo\J26-IT-331"
        r"\experiments\c4\data\C4_Behavioral_Dataset.csv"
    )
    output_dir = Path(r"C:\Users\User\Desktop\FInal_GeoNex_Repo\J26-IT-331\experiments\c4\data")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load dataset
    print("Loading behavioral dataset...")
    df = pd.read_csv(input_path)

    print("Splitting by device (device-held-out evaluation)...")
    splitter = ScenarioAwareSplitter(random_seed=42)
    splits = splitter.split_by_device(df)
    splitter.validate_splits(splits, device_id_col="device_id")
    splitter.save_splits(splits, output_dir, prefix="C4")

    print(f"\nTotal records: {len(df)}")
    for split_name, split_df in splits.items():
        print(f"{split_name.title()}: {len(split_df)} ({len(split_df)/len(df)*100:.1f}%)")
        print(f"  Devices: {split_df['device_id'].nunique()}")
        print(f"  Label distribution: {dict(split_df['trust_label'].value_counts())}")

    print("\nDone!")


if __name__ == "__main__":
    main()
