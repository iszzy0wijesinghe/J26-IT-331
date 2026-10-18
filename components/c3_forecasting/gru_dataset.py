"""Prepare GeoNex C3 temporal sequences for standard GRU training."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import Dataset

from components.c3_forecasting.tabular_features import FEATURE_NAMES

# ============================================================
# GRU Feature Configuration
# ============================================================

SENSOR_NAMES = tuple(FEATURE_NAMES)

# Seven sensor values + seven observation-validity masks.
INPUT_FEATURE_COUNT = len(SENSOR_NAMES) * 2

VALID_SPLITS = frozenset({"train", "validation", "test"})
VALID_HORIZONS = frozenset({15, 30, 60})


# ============================================================
# Temporal Sequence Extraction
# ============================================================

def extract_gru_sequence(
    sequence: dict[str, Any],
) -> np.ndarray:
    """
    Convert a C3 temporal sequence into GRU-ready features.

    Each timestep contains:
        - Seven sensor values
        - Seven observation-validity masks

    Missing, imputed, corrected, or invalid sensor values are
    represented using a zero placeholder with validity mask 0.

    Explicit operating-mode and elapsed-time features are excluded
    from this standard GRU baseline.
    """

    steps = sequence.get("steps", [])

    if not steps:
        raise ValueError(
            "GRU input sequence cannot be empty"
        )

    rows: list[list[float]] = []

    for step in steps:
        features = step["features"]
        masks = step["masks"]

        quality = step.get("quality") or {}

        imputed_flags = quality.get("imputed_flags") or {}
        corrected_flags = quality.get("corrected_flags") or {}

        values: list[float] = []
        valid_masks: list[float] = []

        for sensor in SENSOR_NAMES:
            observed = masks.get(sensor, False) is True

            imputed = (
                imputed_flags.get(sensor, False) is True
            )

            corrected = (
                corrected_flags.get(sensor, False) is True
            )

            raw_value = features.get(sensor)

            valid = (
                observed
                and not imputed
                and not corrected
                and raw_value is not None
                and isinstance(raw_value, (int, float))
                and not isinstance(raw_value, bool)
                and np.isfinite(raw_value)
            )

            if valid:
                value = float(raw_value)

                # Reject values that cannot be represented as
                # finite float32 tensors.
                if not np.isfinite(
                    np.float32(value)
                ):
                    valid = False
                    value = 0.0
            else:
                value = 0.0

            values.append(value)

            valid_masks.append(
                1.0 if valid else 0.0
            )

        rows.append(values + valid_masks)

    result = np.asarray(
        rows,
        dtype=np.float32,
    )

    if result.ndim != 2:
        raise ValueError(
            "GRU sequence must be a 2D array"
        )

    if result.shape[1] != INPUT_FEATURE_COUNT:
        raise ValueError(
            "Unexpected GRU feature count"
        )

    if not np.isfinite(result).all():
        raise ValueError(
            "GRU sequence contains non-finite values"
        )

    return result


# ============================================================
# Single-Pass Dataset Loading
# ============================================================

def load_gru_split(
    dataset_dir: str | Path,
    split: str,
) -> list[dict[str, Any]]:
    """
    Load and convert all forecasting horizons from one dataset split.

    The compressed JSONL file is read once.

    The returned examples can be reused by multiple
    C3GRUDataset instances without reading the file again.
    """

    if split not in VALID_SPLITS:
        raise ValueError(
            f"Unsupported split: {split}"
        )

    dataset_dir = Path(dataset_dir)

    path = dataset_dir / f"{split}.jsonl.gz"

    if not path.is_file():
        raise FileNotFoundError(
            f"GRU dataset file not found: {path}"
        )

    examples: list[dict[str, Any]] = []

    with gzip.open(
        path,
        "rt",
        encoding="utf-8",
    ) as file:
        for line_number, line in enumerate(
            file,
            start=1,
        ):
            if not line.strip():
                continue

            record = json.loads(line)

            if record["split"] != split:
                raise ValueError(
                    "Record split does not match source file "
                    f"at line {line_number}"
                )

            horizon = record["target"][
                "requested_horizon_minutes"
            ]

            if horizon not in VALID_HORIZONS:
                raise ValueError(
                    "Unsupported forecast horizon "
                    f"at line {line_number}: {horizon}"
                )

            sequence = extract_gru_sequence(
                record["input_sequence"]
            )

            target = float(
                record["target"]["value"]
            )

            if not np.isfinite(target):
                raise ValueError(
                    "GRU target must be finite "
                    f"at line {line_number}"
                )

            examples.append(
                {
                    "sequence": sequence,
                    "target": target,
                    "horizon_minutes": horizon,
                    "episode_id": record["episode_id"],
                    "device_id": record["device_id"],
                }
            )

    if not examples:
        raise ValueError(
            f"No GRU examples found in {path}"
        )

    return examples


# ============================================================
# PyTorch Dataset
# ============================================================

class C3GRUDataset(Dataset):
    """
    PyTorch dataset for GeoNex C3 GRU forecasting.

    Supports:
        - 15-minute forecasting
        - 30-minute forecasting
        - 60-minute forecasting

    Preloaded examples can be shared across horizon-specific
    datasets to avoid repeated JSONL decompression and parsing.
    """

    def __init__(
        self,
        dataset_dir: str | Path,
        split: str,
        horizon_minutes: int,
        *,
        preloaded_examples: list[dict[str, Any]] | None = None,
    ):
        if split not in VALID_SPLITS:
            raise ValueError(
                f"Unsupported split: {split}"
            )

        if horizon_minutes not in VALID_HORIZONS:
            raise ValueError(
                f"Unsupported horizon: {horizon_minutes}"
            )

        self.split = split
        self.horizon_minutes = horizon_minutes

        if preloaded_examples is None:
            preloaded_examples = load_gru_split(
                dataset_dir,
                split,
            )

        self.examples = [
            example
            for example in preloaded_examples
            if example["horizon_minutes"] == horizon_minutes
        ]

        if not self.examples:
            raise ValueError(
                "No GRU examples available for "
                f"{split}/{horizon_minutes} minutes"
            )

    def __len__(self) -> int:
        """Return the number of forecasting examples."""

        return len(self.examples)

    def __getitem__(
        self,
        index: int,
    ) -> dict[str, Any]:
        """Return a single GRU forecasting example."""

        return self.examples[index]


# ============================================================
# Variable-Length Batch Padding
# ============================================================

def collate_gru_batch(
    batch: list[dict[str, Any]],
) -> dict[str, torch.Tensor]:
    """
    Convert variable-length GRU sequences into a padded batch.

    Returns:
        inputs:
            Float32 tensor [batch_size, max_steps, 14]

        lengths:
            Int64 tensor containing actual sequence lengths

        targets:
            Float32 tensor containing forecasting targets

    Padding is applied only at the end of shorter sequences.
    """

    if not batch:
        raise ValueError(
            "Cannot collate an empty GRU batch"
        )

    lengths = torch.tensor(
        [
            len(item["sequence"])
            for item in batch
        ],
        dtype=torch.long,
    )

    if torch.any(lengths <= 0).item():
        raise ValueError(
            "GRU batch contains an empty sequence"
        )

    max_length = int(
        lengths.max().item()
    )

    batch_size = len(batch)

    inputs = torch.zeros(
        batch_size,
        max_length,
        INPUT_FEATURE_COUNT,
        dtype=torch.float32,
    )

    targets = torch.tensor(
        [
            item["target"]
            for item in batch
        ],
        dtype=torch.float32,
    )

    for index, item in enumerate(batch):
        sequence = torch.as_tensor(
            item["sequence"],
            dtype=torch.float32,
        )

        if sequence.ndim != 2:
            raise ValueError(
                "Each GRU sequence must be 2D"
            )

        if sequence.shape[1] != INPUT_FEATURE_COUNT:
            raise ValueError(
                "Invalid GRU sequence feature count"
            )

        sequence_length = sequence.shape[0]

        inputs[
            index,
            :sequence_length,
            :,
        ] = sequence

    if not torch.isfinite(inputs).all().item():
        raise ValueError(
            "GRU batch contains non-finite input values"
        )

    if not torch.isfinite(targets).all().item():
        raise ValueError(
            "GRU batch contains non-finite targets"
        )

    return {
        "inputs": inputs,
        "lengths": lengths,
        "targets": targets,
    }