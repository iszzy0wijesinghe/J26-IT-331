from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd


class ScenarioAwareSplitter:
    """Create scenario-aware train/val/test splits for C4 dataset.

    Ensures that all records from the same scenario stay in the same split
    to prevent scenario leakage during model evaluation.
    """

    def __init__(
        self,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42,
    ) -> None:
        """Initialize splitter.

        Args:
            train_ratio: Proportion of data for training
            val_ratio: Proportion of data for validation
            test_ratio: Proportion of data for testing
            random_seed: Random seed for reproducibility
        """
        if not abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6:
            raise ValueError("Split ratios must sum to 1.0")

        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_seed = random_seed

    def split_by_scenario(
        self,
        df: pd.DataFrame,
        scenario_col: str = "scenario",
    ) -> dict[Literal["train", "val", "test"], pd.DataFrame]:
        """Split dataset by scenario.

        All records from the same scenario will be in the same split.

        Args:
            df: Input dataframe
            scenario_col: Name of scenario column

        Returns:
            Dictionary with train, val, test dataframes
        """
        # Get unique scenarios
        scenarios = df[scenario_col].unique()
        rng = None

        # Shuffle scenarios
        if self.random_seed is not None:
            import random

            random.seed(self.random_seed)
            rng = random.Random(self.random_seed)
            scenarios = rng.sample(list(scenarios), len(scenarios))

        # Calculate split indices
        n_scenarios = len(scenarios)
        n_train = int(n_scenarios * self.train_ratio)
        n_val = int(n_scenarios * self.val_ratio)

        train_scenarios = scenarios[:n_train]
        val_scenarios = scenarios[n_train : n_train + n_val]
        test_scenarios = scenarios[n_train + n_val :]

        # Split dataframe
        train_df = df[df[scenario_col].isin(train_scenarios)].copy()
        val_df = df[df[scenario_col].isin(val_scenarios)].copy()
        test_df = df[df[scenario_col].isin(test_scenarios)].copy()

        return {
            "train": train_df,
            "val": val_df,
            "test": test_df,
        }

    def split_by_device(
        self,
        df: pd.DataFrame,
        device_id_col: str = "device_id",
    ) -> dict[Literal["train", "val", "test"], pd.DataFrame]:
        """Split dataset by device ID.

        All records from the same device will be in the same split.
        This prevents device shortcut leakage.

        Args:
            df: Input dataframe
            device_id_col: Name of device_id column

        Returns:
            Dictionary with train, val, test dataframes
        """
        # Get unique devices
        devices = df[device_id_col].unique()
        rng = None

        # Shuffle devices
        if self.random_seed is not None:
            import random

            random.seed(self.random_seed)
            rng = random.Random(self.random_seed)
            devices = rng.sample(list(devices), len(devices))

        # Calculate split indices
        n_devices = len(devices)
        n_train = int(n_devices * self.train_ratio)
        n_val = int(n_devices * self.val_ratio)

        train_devices = devices[:n_train]
        val_devices = devices[n_train : n_train + n_val]
        test_devices = devices[n_train + n_val :]

        # Split dataframe
        train_df = df[df[device_id_col].isin(train_devices)].copy()
        val_df = df[df[device_id_col].isin(val_devices)].copy()
        test_df = df[df[device_id_col].isin(test_devices)].copy()

        return {
            "train": train_df,
            "val": val_df,
            "test": test_df,
        }

    def split_by_scenario_and_device(
        self,
        df: pd.DataFrame,
        scenario_col: str = "scenario",
        device_id_col: str = "device_id",
    ) -> dict[Literal["train", "val", "test"], pd.DataFrame]:
        """Split dataset by both scenario and device.

        This is the most conservative split to prevent both scenario
        and device shortcuts.

        Args:
            df: Input dataframe
            scenario_col: Name of scenario column
            device_id_col: Name of device_id column

        Returns:
            Dictionary with train, val, test dataframes
        """
        # Create unique (scenario, device) pairs
        df["_scenario_device"] = df[scenario_col] + "_" + df[device_id_col]
        unique_pairs = df["_scenario_device"].unique()

        # Shuffle pairs
        if self.random_seed is not None:
            import random

            random.seed(self.random_seed)
            rng = random.Random(self.random_seed)
            unique_pairs = rng.sample(list(unique_pairs), len(unique_pairs))

        # Calculate split indices
        n_pairs = len(unique_pairs)
        n_train = int(n_pairs * self.train_ratio)
        n_val = int(n_pairs * self.val_ratio)

        train_pairs = unique_pairs[:n_train]
        val_pairs = unique_pairs[n_train : n_train + n_val]
        test_pairs = unique_pairs[n_train + n_val :]

        # Split dataframe
        train_df = df[df["_scenario_device"].isin(train_pairs)].copy()
        val_df = df[df["_scenario_device"].isin(val_pairs)].copy()
        test_df = df[df["_scenario_device"].isin(test_pairs)].copy()

        # Clean up temporary column
        train_df = train_df.drop(columns=["_scenario_device"])
        val_df = val_df.drop(columns=["_scenario_device"])
        test_df = test_df.drop(columns=["_scenario_device"])

        return {
            "train": train_df,
            "val": val_df,
            "test": test_df,
        }

    def save_splits(
        self,
        splits: dict[Literal["train", "val", "test"], pd.DataFrame],
        output_dir: Path,
        prefix: str = "C4",
    ) -> None:
        """Save splits to CSV files.

        Args:
            splits: Dictionary with train, val, test dataframes
            output_dir: Directory to save files
            prefix: Prefix for filenames
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for split_name, split_df in splits.items():
            output_path = output_dir / f"{prefix}_{split_name}.csv"
            split_df.to_csv(output_path, index=False)
            print(f"Saved {split_name} split to {output_path}")
            print(f"  Shape: {split_df.shape}")
            print(f"  Scenarios: {split_df['scenario'].unique()}")
            print(f"  Label distribution:\n{split_df['trust_label'].value_counts()}\n")


def create_c4_splits(
    input_path: str,
    output_dir: str,
    split_type: Literal["scenario", "device", "both"] = "scenario",
) -> None:
    """Create C4 dataset splits.

    Args:
        input_path: Path to behavioral dataset
        output_dir: Directory to save splits
        split_type: Type of split (scenario, device, or both)
    """
    # Load dataset
    df = pd.read_csv(input_path)

    # Create splitter
    splitter = ScenarioAwareSplitter(
        train_ratio=0.7,
        val_ratio=0.15,
        test_ratio=0.15,
        random_seed=42,
    )

    # Create splits
    if split_type == "scenario":
        splits = splitter.split_by_scenario(df)
    elif split_type == "device":
        splits = splitter.split_by_device(df)
    elif split_type == "both":
        splits = splitter.split_by_scenario_and_device(df)
    else:
        raise ValueError(f"Unknown split_type: {split_type}")

    # Save splits
    output_path = Path(output_dir)
    splitter.save_splits(splits, output_path, prefix=f"C4_{split_type}")

    print(f"\nSplit type: {split_type}")
    print(f"Total records: {len(df)}")
    print(f"Train: {len(splits['train'])} ({len(splits['train'])/len(df)*100:.1f}%)")
    print(f"Val: {len(splits['val'])} ({len(splits['val'])/len(df)*100:.1f}%)")
    print(f"Test: {len(splits['test'])} ({len(splits['test'])/len(df)*100:.1f}%)")



if __name__ == "__main__":
    # Example usage
    base_dir = r"C:\Users\User\Desktop\FInal_GeoNex_Repo\J26-IT-331"
    input_path = (
        base_dir + r"\experiments\c4\data\C4_Behavioral_Dataset.csv"
    )
    output_dir = base_dir + r"\experiments\c4\data"

    create_c4_splits(input_path, output_dir, split_type="scenario")
