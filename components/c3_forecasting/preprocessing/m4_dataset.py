"""Dataset loading and batching for GeoNex C3 M4 forecasting."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import Dataset

from components.c3_forecasting.preprocessing.m4_features import (
    M4_INPUT_FEATURE_COUNT,
    extract_m4_sequence,
)

VALID_SPLITS = frozenset({"train", "validation", "test"})
VALID_HORIZONS = frozenset({15, 30, 60})


def load_m4_split(
    dataset_dir: str | Path,
    split: str,
) -> list[dict[str, Any]]:
    """Load M4 forecasting examples from one dataset split."""

    if split not in VALID_SPLITS:
        raise ValueError(f"Unsupported split: {split}")

    path = Path(dataset_dir) / f"{split}.jsonl.gz"

    if not path.is_file():
        raise FileNotFoundError(f"M4 dataset file not found: {path}")

    examples: list[dict[str, Any]] = []

    with gzip.open(path, "rt", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            record = json.loads(line)

            if record["split"] != split:
                raise ValueError(f"Record split mismatch at line {line_number}")

            horizon = record["target"]["requested_horizon_minutes"]

            if horizon not in VALID_HORIZONS:
                raise ValueError(f"Unsupported horizon at line {line_number}: {horizon}")

            sequence = extract_m4_sequence(
                record["input_sequence"],
                include_time=True,
                include_mode=True,
            )

            target = float(record["target"]["value"])

            if not np.isfinite(target):
                raise ValueError(f"Non-finite M4 target at line {line_number}")

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
        raise ValueError(f"No M4 examples found in {path}")

    return examples


class C3M4Dataset(Dataset):
    """Horizon-specific M4 forecasting dataset."""

    def __init__(
        self,
        dataset_dir: str | Path,
        split: str,
        horizon_minutes: int,
        *,
        preloaded_examples: list[dict[str, Any]] | None = None,
    ) -> None:
        if split not in VALID_SPLITS:
            raise ValueError(f"Unsupported split: {split}")

        if horizon_minutes not in VALID_HORIZONS:
            raise ValueError(f"Unsupported horizon: {horizon_minutes}")

        self.split = split
        self.horizon_minutes = horizon_minutes

        if preloaded_examples is None:
            preloaded_examples = load_m4_split(dataset_dir, split)

        self.examples = [
            example
            for example in preloaded_examples
            if example["horizon_minutes"] == horizon_minutes
        ]

        if not self.examples:
            raise ValueError(f"No M4 examples for {split}/{horizon_minutes} minutes")

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, index: int) -> dict[str, Any]:
        return self.examples[index]


def collate_m4_batch(
    batch: list[dict[str, Any]],
) -> dict[str, torch.Tensor]:
    """Pad variable-length M4 sequences into a 20-feature batch."""

    if not batch:
        raise ValueError("Cannot collate an empty M4 batch")

    lengths = torch.tensor(
        [len(item["sequence"]) for item in batch],
        dtype=torch.long,
    )

    if torch.any(lengths <= 0).item():
        raise ValueError("M4 batch contains an empty sequence")

    batch_size = len(batch)
    max_length = int(lengths.max().item())

    inputs = torch.zeros(
        batch_size,
        max_length,
        M4_INPUT_FEATURE_COUNT,
        dtype=torch.float32,
    )

    targets = torch.tensor(
        [item["target"] for item in batch],
        dtype=torch.float32,
    )

    for index, item in enumerate(batch):
        sequence = torch.as_tensor(
            item["sequence"],
            dtype=torch.float32,
        )

        if sequence.ndim != 2:
            raise ValueError("M4 sequence must be two-dimensional")

        if sequence.shape[1] != M4_INPUT_FEATURE_COUNT:
            raise ValueError("Invalid M4 sequence feature count")

        inputs[index, : sequence.shape[0], :] = sequence

    if not torch.isfinite(inputs).all().item():
        raise ValueError("M4 batch contains non-finite inputs")

    if not torch.isfinite(targets).all().item():
        raise ValueError("M4 batch contains non-finite targets")

    return {
        "inputs": inputs,
        "lengths": lengths,
        "targets": targets,
    }
