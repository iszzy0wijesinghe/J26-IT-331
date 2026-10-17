"""Tests for the C3 V2 reliability-aware temporal adapter."""

from copy import deepcopy
from datetime import datetime, timedelta

import pytest

from components.c3_forecasting.v2_dataset_reader import (
    iter_v2_records,
)
from components.c3_forecasting.v2_temporal_adapter import (
    build_v2_temporal_sequence,
)

DATASET_DIR = "data/synthetic/c3_v2"


@pytest.fixture(scope="module")
def sample_record():
    return next(iter_v2_records(DATASET_DIR))


def make_record(sample, index, seconds):
    record = deepcopy(sample)

    observed = datetime.fromisoformat(sample["observed_at"])
    observed += timedelta(seconds=seconds)

    received = observed + timedelta(seconds=1)

    record["packet_id"] = f"TEST_PACKET_{index}"
    record["observed_at"] = observed.isoformat()
    record["received_at"] = received.isoformat()

    return record


def test_builds_valid_temporal_sequence(sample_record):
    records = [
        make_record(sample_record, 1, 0),
        make_record(sample_record, 2, 60),
        make_record(sample_record, 3, 180),
    ]

    origin = datetime.fromisoformat(records[-1]["received_at"])

    sequence = build_v2_temporal_sequence(
        records,
        forecast_origin=origin,
    )

    assert len(sequence.steps) == 3
    assert sequence.steps[0].delta_t_seconds == 0
    assert sequence.steps[1].delta_t_seconds == 60
    assert sequence.steps[2].delta_t_seconds == 120


def test_preserves_observation_masks(sample_record):
    record = make_record(sample_record, 1, 0)

    origin = datetime.fromisoformat(record["received_at"])

    sequence = build_v2_temporal_sequence(
        [record],
        forecast_origin=origin,
    )

    step = sequence.steps[0]

    assert step.masks == record["masks"]

    assert step.features["soil_moisture_pct"] == 0.0
    assert step.masks["soil_moisture_pct"] is False


def test_converts_unavailable_age_to_none(sample_record):
    record = make_record(sample_record, 1, 0)

    origin = datetime.fromisoformat(record["received_at"])

    sequence = build_v2_temporal_sequence(
        [record],
        forecast_origin=origin,
    )

    assert sequence.steps[0].ages_seconds["soil_moisture_pct"] is None


def test_excludes_future_observations(sample_record):
    records = [
        make_record(sample_record, 1, 0),
        make_record(sample_record, 2, 60),
    ]

    origin = datetime.fromisoformat(records[0]["received_at"])

    sequence = build_v2_temporal_sequence(
        records,
        forecast_origin=origin,
    )

    assert len(sequence.steps) == 1


def test_excludes_delayed_packets(sample_record):
    records = [
        make_record(sample_record, 1, 0),
        make_record(sample_record, 2, 60),
    ]

    first_received = datetime.fromisoformat(
        records[0]["received_at"]
    )

    records[1]["received_at"] = (
        first_received + timedelta(minutes=10)
    ).isoformat()

    origin = first_received + timedelta(minutes=2)

    sequence = build_v2_temporal_sequence(
        records,
        forecast_origin=origin,
    )

    assert len(sequence.steps) == 1


def test_rejects_mixed_episodes(sample_record):
    first = make_record(sample_record, 1, 0)
    second = make_record(sample_record, 2, 60)

    second["scenario_id"] = "DIFFERENT_EPISODE"

    origin = datetime.fromisoformat(second["received_at"])

    with pytest.raises(ValueError, match="Cannot mix"):
        build_v2_temporal_sequence(
            [first, second],
            forecast_origin=origin,
        )


def test_rejects_duplicate_packet_ids(sample_record):
    first = make_record(sample_record, 1, 0)
    second = deepcopy(first)

    origin = datetime.fromisoformat(first["received_at"])

    with pytest.raises(ValueError, match="Duplicate"):
        build_v2_temporal_sequence(
            [first, second],
            forecast_origin=origin,
        )


def test_preserves_operating_mode(sample_record):
    record = make_record(sample_record, 1, 0)

    record["effective_mode"] = "WARNING"

    origin = datetime.fromisoformat(record["received_at"])

    sequence = build_v2_temporal_sequence(
        [record],
        forecast_origin=origin,
    )

    assert sequence.steps[0].operating_mode.value == "WARNING"


def test_preserves_reliability_metadata(sample_record):
    record = make_record(sample_record, 1, 0)

    origin = datetime.fromisoformat(record["received_at"])

    sequence = build_v2_temporal_sequence(
        [record],
        forecast_origin=origin,
    )

    quality = sequence.steps[0].quality

    assert quality["imputed_flags"] == record["imputed_flags"]
    assert quality["corrected_flags"] == record["corrected_flags"]
    assert (
        quality["imputation_methods"]
        == record["imputation_methods"]
    )