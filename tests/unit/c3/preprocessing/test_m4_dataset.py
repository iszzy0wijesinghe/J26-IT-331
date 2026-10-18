"""Unit tests for GeoNex C3 M4 dataset loading and batching."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import numpy as np
import pytest
import torch

from components.c3_forecasting.preprocessing.m4_dataset import (
    C3M4Dataset,
    collate_m4_batch,
    load_m4_split,
)
from components.c3_forecasting.preprocessing.m4_features import (
    M4_INPUT_FEATURE_COUNT,
)


@pytest.fixture
def sample_examples() -> list[dict]:
    """Create synthetic M4 examples with different sequence lengths."""

    examples = []

    for index, (horizon, length) in enumerate([(15, 3), (15, 5), (30, 2), (60, 4)]):
        sequence = np.zeros(
            (length, M4_INPUT_FEATURE_COUNT),
            dtype=np.float32,
        )

        sequence[:, :7] = float(index + 1)
        sequence[:, 7:14] = 1.0
        sequence[:, 16] = 1.0

        examples.append(
            {
                "sequence": sequence,
                "target": float(20 + index),
                "horizon_minutes": horizon,
                "episode_id": f"episode-{index}",
                "device_id": "device-1",
            }
        )

    return examples


def test_dataset_filters_horizon(
    sample_examples: list[dict],
) -> None:
    dataset = C3M4Dataset(
        ".",
        split="train",
        horizon_minutes=15,
        preloaded_examples=sample_examples,
    )

    assert len(dataset) == 2
    assert all(example["horizon_minutes"] == 15 for example in dataset.examples)


def test_dataset_returns_expected_example(
    sample_examples: list[dict],
) -> None:
    dataset = C3M4Dataset(
        ".",
        split="train",
        horizon_minutes=30,
        preloaded_examples=sample_examples,
    )

    assert dataset[0]["target"] == 22.0
    assert dataset[0]["sequence"].shape == (2, 20)


def test_dataset_rejects_invalid_split(
    sample_examples: list[dict],
) -> None:
    with pytest.raises(ValueError, match="split"):
        C3M4Dataset(
            ".",
            split="invalid",
            horizon_minutes=15,
            preloaded_examples=sample_examples,
        )


def test_dataset_rejects_invalid_horizon(
    sample_examples: list[dict],
) -> None:
    with pytest.raises(ValueError, match="horizon"):
        C3M4Dataset(
            ".",
            split="train",
            horizon_minutes=45,
            preloaded_examples=sample_examples,
        )


def test_dataset_rejects_missing_horizon_examples(
    sample_examples: list[dict],
) -> None:
    with pytest.raises(ValueError, match="No M4 examples"):
        C3M4Dataset(
            ".",
            split="train",
            horizon_minutes=60,
            preloaded_examples=sample_examples[:2],
        )


def test_collate_batch_shape(
    sample_examples: list[dict],
) -> None:
    batch = collate_m4_batch(sample_examples[:2])

    assert batch["inputs"].shape == (2, 5, 20)
    assert batch["lengths"].shape == (2,)
    assert batch["targets"].shape == (2,)


def test_collate_preserves_sequence_lengths(
    sample_examples: list[dict],
) -> None:
    batch = collate_m4_batch(sample_examples[:2])

    torch.testing.assert_close(
        batch["lengths"],
        torch.tensor([3, 5]),
    )


def test_collate_preserves_targets(
    sample_examples: list[dict],
) -> None:
    batch = collate_m4_batch(sample_examples[:2])

    torch.testing.assert_close(
        batch["targets"],
        torch.tensor([20.0, 21.0]),
    )


def test_collate_zero_pads_shorter_sequence(
    sample_examples: list[dict],
) -> None:
    batch = collate_m4_batch(sample_examples[:2])

    assert torch.all(batch["inputs"][0, 3:, :] == 0).item()


def test_collate_preserves_original_features(
    sample_examples: list[dict],
) -> None:
    batch = collate_m4_batch(sample_examples[:2])

    expected = torch.from_numpy(sample_examples[0]["sequence"])

    torch.testing.assert_close(
        batch["inputs"][0, :3, :],
        expected,
    )


def test_collate_rejects_empty_batch() -> None:
    with pytest.raises(ValueError, match="empty"):
        collate_m4_batch([])


def test_collate_rejects_empty_sequence(
    sample_examples: list[dict],
) -> None:
    invalid = {
        **sample_examples[0],
        "sequence": np.zeros(
            (0, M4_INPUT_FEATURE_COUNT),
            dtype=np.float32,
        ),
    }

    with pytest.raises(ValueError, match="empty sequence"):
        collate_m4_batch([invalid])


def test_collate_rejects_wrong_feature_count(
    sample_examples: list[dict],
) -> None:
    invalid = {
        **sample_examples[0],
        "sequence": np.zeros(
            (3, M4_INPUT_FEATURE_COUNT - 1),
            dtype=np.float32,
        ),
    }

    with pytest.raises(ValueError, match="feature count"):
        collate_m4_batch([invalid])


def test_collate_rejects_nonfinite_inputs(
    sample_examples: list[dict],
) -> None:
    invalid_sequence = sample_examples[0]["sequence"].copy()
    invalid_sequence[0, 0] = np.nan

    invalid = {
        **sample_examples[0],
        "sequence": invalid_sequence,
    }

    with pytest.raises(ValueError, match="non-finite inputs"):
        collate_m4_batch([invalid])


def test_collate_rejects_nonfinite_targets(
    sample_examples: list[dict],
) -> None:
    invalid = {
        **sample_examples[0],
        "target": float("nan"),
    }

    with pytest.raises(ValueError, match="non-finite targets"):
        collate_m4_batch([invalid])


def test_load_rejects_invalid_split() -> None:
    with pytest.raises(ValueError, match="split"):
        load_m4_split(".", "invalid")


def test_load_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_m4_split(tmp_path, "train")


def test_load_rejects_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "train.jsonl.gz"

    with gzip.open(path, "wt", encoding="utf-8") as file:
        file.write("")

    with pytest.raises(ValueError, match="No M4 examples"):
        load_m4_split(tmp_path, "train")


def test_load_rejects_split_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "train.jsonl.gz"

    record = {
        "split": "validation",
        "target": {
            "requested_horizon_minutes": 15,
        },
    }

    with gzip.open(path, "wt", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")

    with pytest.raises(ValueError, match="split mismatch"):
        load_m4_split(tmp_path, "train")


def test_load_rejects_invalid_horizon(tmp_path: Path) -> None:
    path = tmp_path / "train.jsonl.gz"

    record = {
        "split": "train",
        "target": {
            "requested_horizon_minutes": 45,
        },
    }

    with gzip.open(path, "wt", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")

    with pytest.raises(ValueError, match="Unsupported horizon"):
        load_m4_split(tmp_path, "train")
