"""Tests for C3 V2 fixed-horizon training targets."""

from collections import Counter

import pytest

from components.c3_forecasting.data.v2_target_builder import (
    build_v2_fixed_horizon_examples,
)

DATASET_DIR = "data/synthetic/c3_v2"


@pytest.fixture(scope="module")
def examples():
    return build_v2_fixed_horizon_examples(DATASET_DIR)


def test_generates_training_examples(examples):
    assert len(examples) > 0


def test_preserves_dataset_splits(examples):
    assert all(
        example.split in {"train", "validation", "test"}
        for example in examples
    )

    episode_splits = {}

    for example in examples:
        existing = episode_splits.setdefault(
            example.episode_id,
            example.split,
        )

        assert existing == example.split


def test_targets_are_in_the_future(examples):
    for example in examples:
        assert example.target_observed_at > example.forecast_origin


def test_horizon_tolerance(examples):
    for example in examples:
        requested_seconds = (
            example.requested_horizon_minutes * 60
        )

        assert (
            abs(
                example.actual_horizon_seconds
                - requested_seconds
            )
            <= 120
        )


def test_input_sequences_are_as_of_safe(examples):
    for example in examples:
        assert all(
            step.time <= example.forecast_origin
            for step in example.input_sequence.steps
        )


def test_has_multiple_horizons(examples):
    horizons = {
        example.requested_horizon_minutes
        for example in examples
    }

    assert horizons == {15, 30, 60}


def test_has_multiple_splits(examples):
    splits = {example.split for example in examples}

    assert splits == {"train", "validation", "test"}


def test_training_example_serialization(examples):
    record = examples[0].to_record()

    assert record["dataset_version"] == "c3-fixed-horizon-v2"
    assert "input_sequence" in record
    assert "target" in record


def test_target_distribution(examples):
    counts = Counter(
        example.requested_horizon_minutes
        for example in examples
    )

    print("\nC3 V2 fixed-horizon examples:")
    for horizon, count in sorted(counts.items()):
        print(f"  {horizon} minutes: {count}")

    assert all(counts[horizon] > 0 for horizon in (15, 30, 60))


def test_rejects_invalid_horizons():
    with pytest.raises(ValueError):
        build_v2_fixed_horizon_examples(
            DATASET_DIR,
            horizons_minutes=(0,),
        )


def test_rejects_invalid_history_length():
    with pytest.raises(ValueError):
        build_v2_fixed_horizon_examples(
            DATASET_DIR,
            min_history_steps=10,
            max_history_steps=5,
        )