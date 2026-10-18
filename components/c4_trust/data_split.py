from __future__ import annotations

from pathlib import Path
from random import Random
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
        if min(train_ratio, val_ratio, test_ratio) <= 0:
            raise ValueError("Split ratios must all be greater than zero")
        if not abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6:
            raise ValueError("Split ratios must sum to 1.0")

        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_seed = random_seed

    def _split_by_groups(
        self,
        df: pd.DataFrame,
        group_values: pd.Series,
    ) -> dict[Literal["train", "val", "test"], pd.DataFrame]:
        if group_values.isna().any():
            raise ValueError("Group columns must not contain missing values")

        groups = list(pd.unique(group_values))
        if len(groups) < 3:
            raise ValueError("At least three independent groups are required for train/val/test")
        if self.random_seed is not None:
            Random(self.random_seed).shuffle(groups)

        assignments: dict[str, list[object]] = {"train": [], "val": [], "test": []}
        group_labels: dict[object, set[object]] = {group: set() for group in groups}
        group_sizes = group_values.value_counts().to_dict()
        label_groups: dict[object, set[object]] = {}
        if "trust_label" in df.columns:
            if df["trust_label"].isna().any():
                raise ValueError("Label column 'trust_label' contains missing values")
            for group, label in zip(group_values.tolist(), df["trust_label"].tolist(), strict=True):
                group_labels[group].add(label)
                label_groups.setdefault(label, set()).add(group)

            labels_by_rarity = sorted(label_groups, key=lambda label: len(label_groups[label]))
            for label in labels_by_rarity:
                if any(label in group_labels[group] for group in assignments["train"]):
                    continue
                candidate_groups = [group for group in groups if label in group_labels[group]]
                selected_group = max(
                    candidate_groups,
                    key=lambda group: (
                        len(group_labels[group]),
                        group_sizes[group],
                    ),
                )
                assignments["train"].append(selected_group)

            for split_name in ("val", "test"):
                for label in labels_by_rarity:
                    if len(label_groups[label]) < 3:
                        continue
                    if any(label in group_labels[group] for group in assignments[split_name]):
                        continue
                    assigned_groups = set().union(*assignments.values())
                    candidate_groups = [
                        group
                        for group in groups
                        if group not in assigned_groups and label in group_labels[group]
                    ]
                    if candidate_groups:
                        selected_group = max(
                            candidate_groups,
                            key=lambda group: group_sizes[group],
                        )
                        assignments[split_name].append(selected_group)

        n_groups = len(groups)
        if len(assignments["train"]) > n_groups - 2:
            raise ValueError(
                "Not enough independent groups to keep every label in training "
                "and create non-empty validation and test splits"
            )
        assigned_groups = set().union(*assignments.values())
        for group in groups:
            if group in assigned_groups:
                continue
            split_name = max(
                assignments,
                key=lambda name: (
                    {
                        "train": n_groups * self.train_ratio,
                        "val": n_groups * self.val_ratio,
                        "test": n_groups * self.test_ratio,
                    }[name]
                    - len(assignments[name])
                ),
            )
            assignments[split_name].append(group)

        return {
            split_name: df.loc[group_values.isin(split_groups)].copy()
            for split_name, split_groups in assignments.items()
        }

    @staticmethod
    def validate_splits(
        splits: dict[Literal["train", "val", "test"], pd.DataFrame],
        scenario_col: str = "scenario",
        *,
        device_id_col: str | None = None,
        label_col: str = "trust_label",
        expected_labels: set[object] | None = None,
    ) -> None:
        """Reject group overlap and missing expected labels across persisted splits."""
        group_col = scenario_col if device_id_col is None else device_id_col
        group_sets: dict[str, set[object]] = {}
        for split_name in ("train", "val", "test"):
            if split_name not in splits:
                raise ValueError(f"Missing {split_name!r} dataset split")
            split_df = splits[split_name]
            if group_col not in split_df.columns:
                raise ValueError(f"Split is missing required column {group_col!r}")
            if split_df[group_col].isna().any():
                raise ValueError(f"Split column {group_col!r} contains missing values")
            group_sets[split_name] = set(split_df[group_col].unique())

        for first, second in (("train", "val"), ("train", "test"), ("val", "test")):
            overlap = group_sets[first] & group_sets[second]
            if overlap:
                if device_id_col is None:
                    raise ValueError(
                        f"Scenario leakage between {first} and {second}: {sorted(overlap)}. "
                        "Regenerate the splits by scenario."
                    )
                raise ValueError(
                    f"Device leakage between {first} and {second}: {sorted(overlap)}."
                )

        split_names = ("train", "val", "test")
        label_presence = [label_col in splits[name].columns for name in split_names]
        if any(label_presence) and not all(label_presence):
            missing_splits = [
                name
                for name, present in zip(split_names, label_presence, strict=True)
                if not present
            ]
            raise ValueError(
                f"Label column {label_col!r} must be present in all splits or none; "
                f"missing from {', '.join(missing_splits)}"
            )
        if all(label_presence):
            if any(splits[name][label_col].isna().any() for name in split_names):
                raise ValueError(f"Label column {label_col!r} contains missing values")
            labels_to_check = (
                set(expected_labels)
                if expected_labels is not None
                else set().union(*(set(splits[name][label_col].unique()) for name in split_names))
            )
            for split_name in split_names:
                missing = labels_to_check - set(splits[split_name][label_col].unique())
                if missing:
                    raise ValueError(
                        f"{split_name} split is missing expected {label_col} classes: "
                        f"{sorted(missing)}"
                    )

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
        if scenario_col not in df.columns:
            raise ValueError(f"Input dataframe is missing {scenario_col!r}")
        return self._split_by_groups(df, df[scenario_col])

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
        if device_id_col not in df.columns:
            raise ValueError(f"Input dataframe is missing {device_id_col!r}")
        return self._split_by_groups(df, df[device_id_col])

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
        for column in (scenario_col, device_id_col):
            if column not in df.columns:
                raise ValueError(f"Input dataframe is missing {column!r}")

        row_count = len(df)
        parents = list(range(row_count))

        def find(row_index: int) -> int:
            while parents[row_index] != row_index:
                parents[row_index] = parents[parents[row_index]]
                row_index = parents[row_index]
            return row_index

        def union(first: int, second: int) -> None:
            first_root = find(first)
            second_root = find(second)
            if first_root != second_root:
                parents[second_root] = first_root

        scenario_rows: dict[object, int] = {}
        device_rows: dict[object, int] = {}
        scenarios = df[scenario_col].tolist()
        devices = df[device_id_col].tolist()
        if df[[scenario_col, device_id_col]].isna().any().any():
            raise ValueError("Scenario and device columns must not contain missing values")

        for row_index, (scenario, device) in enumerate(zip(scenarios, devices, strict=True)):
            if scenario in scenario_rows:
                union(row_index, scenario_rows[scenario])
            else:
                scenario_rows[scenario] = row_index
            if device in device_rows:
                union(row_index, device_rows[device])
            else:
                device_rows[device] = row_index

        components = pd.Series(
            [find(row_index) for row_index in range(row_count)], index=df.index
        )
        return self._split_by_groups(df, components)

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
            split_df = split_df.copy()
            split_df["split"] = split_name
            output_path = output_dir / f"{prefix}_{split_name}.csv"
            split_df.to_csv(output_path, index=False)
            print(f"Saved {split_name} split to {output_path}")
            print(f"  Shape: {split_df.shape}")
            print(f"  Scenarios: {split_df['scenario'].unique()}")
            print(f"  Label distribution:\n{split_df['trust_label'].value_counts()}\n")


def create_c4_splits(
    input_path: str,
    output_dir: str,
    split_type: Literal["scenario", "device", "both"] = "device",
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
        splitter.validate_splits(splits)
    elif split_type == "device":
        splits = splitter.split_by_device(df)
        splitter.validate_splits(splits, device_id_col="device_id")
    elif split_type == "both":
        splits = splitter.split_by_scenario_and_device(df)
        splitter.validate_splits(splits)
        splitter.validate_splits(splits, device_id_col="device_id")
    else:
        raise ValueError(f"Unknown split_type: {split_type}")

    # Save splits
    output_path = Path(output_dir)
    prefix = "C4" if split_type == "device" else f"C4_{split_type}"
    splitter.save_splits(splits, output_path, prefix=prefix)

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

    # Use device-held-out splits for proper evaluation
    create_c4_splits(input_path, output_dir, split_type="device")
