"""Prepare C4 behavioral dataset from C4_Trust.csv.

This script:
1. Loads the C4_Trust.csv dataset
2. Extracts behavioral features (B0-B5)
3. Excludes deterministic security fields to prevent leakage
4. Adds rolling historical features per device
5. Saves clean behavioral dataset for ML training
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from components.c4_trust.features import FeatureExtractor


def main() -> None:
    # Paths
    input_path = r"c:\Users\User\Desktop\Dataset\all datasets\C4_Trust.csv"
    output_dir = Path(r"C:\Users\User\Desktop\FInal_GeoNex_Repo\J26-IT-331\experiments\c4\data")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "C4_Behavioral_Dataset.csv"

    # Create feature extractor
    extractor = FeatureExtractor()

    # Create behavioral dataset
    print("Creating behavioral dataset from C4_Trust.csv...")
    extractor.create_behavioral_dataset(
        input_path=input_path,
        output_path=str(output_path),
        add_historical=True,
        historical_window=10,
    )

    print("\nDone!")


if __name__ == "__main__":
    main()
