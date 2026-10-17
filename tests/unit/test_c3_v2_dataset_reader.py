"""Tests for the GeoNex C3 V2 dataset reader."""

from copy import deepcopy

import pytest

from components.c3_forecasting.v2_dataset_reader import (
    C3V2DatasetError,
    group_v2_by_episode_device,
    iter_v2_records,
    validate_v2_record,
)

DATASET_DIR = "data/synthetic/c3_v2"


@pytest.fixture(scope="module")
def sample_record():
    return next(iter_v2_records(DATASET_DIR))


def test_valid_v2_record(sample_record):
    validate_v2_record(sample_record)


def test_rejects_wrong_schema(sample_record):
    record = deepcopy(sample_record)
    record["schema_version"] = "unknown"

    with pytest.raises(C3V2DatasetError):
        validate_v2_record(record)


def test_rejects_non_finite_sensor_value(sample_record):
    record = deepcopy(sample_record)
    record["features"]["soil_moisture_pct"] = float("nan")

    with pytest.raises(C3V2DatasetError):
        validate_v2_record(record)


def test_rejects_invalid_mode(sample_record):
    record = deepcopy(sample_record)
    record["effective_mode"] = "UNKNOWN"

    with pytest.raises(C3V2DatasetError):
        validate_v2_record(record)


def test_preserves_missingness_metadata(sample_record):
    assert sample_record["masks"]["soil_moisture_pct"] is False

    assert (
        sample_record["imputation_methods"]["soil_moisture_pct"]
        == "NO_OBSERVATION_PLACEHOLDER"
    )


def test_reads_all_telemetry_records():
    records = list(iter_v2_records(DATASET_DIR))

    assert len(records) == 31469


def test_episode_device_grouping():
    groups = group_v2_by_episode_device(DATASET_DIR)

    assert groups

    for (episode_id, device_id), records in groups.items():
        assert all(
            record["scenario_id"] == episode_id
            and record["device_id"] == device_id
            for record in records
        )

        timestamps = [
            record["observed_at"]
            for record in records
        ]

        assert timestamps == sorted(timestamps)