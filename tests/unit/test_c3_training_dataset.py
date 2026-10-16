
"""Tests for C3 next-observation supervised dataset construction."""

import json
from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from components.c3_forecasting.feature_extractor import FEATURE_NAMES
from components.c3_forecasting.training_dataset import (
    build_next_observation_examples,
    split_examples_by_device,
)
from shared.simulation.scheduled_telemetry import (
    ScheduledTelemetryConfig,
    generate_scheduled_demo_telemetry,
)


@pytest.fixture
def demo_items():
    return generate_scheduled_demo_telemetry(
        ScheduledTelemetryConfig(seed=20261016)
    )


def test_generates_examples_from_all_six_pipes(demo_items):
    examples = build_next_observation_examples(demo_items)

    assert len(examples) == 42

    device_keys = {
        (example.zone_id, example.device_id)
        for example in examples
    }

    assert len(device_keys) == 6


def test_each_example_contains_real_simulator_features(demo_items):
    examples = build_next_observation_examples(demo_items)

    for example in examples:
        assert len(example.input_sequence.steps) >= 3
        assert all(
            set(step.features) == set(FEATURE_NAMES)
            for step in example.input_sequence.steps
        )


def test_targets_are_strictly_after_forecast_origin(demo_items):
    examples = build_next_observation_examples(demo_items)

    for example in examples:
        assert example.target_observed_at > example.forecast_origin
        assert example.horizon_seconds > 0

        expected_horizon = (
            example.target_observed_at - example.forecast_origin
        ).total_seconds()

        assert example.horizon_seconds == expected_horizon


def test_input_never_contains_future_or_unavailable_data(demo_items):
    examples = build_next_observation_examples(demo_items)

    for example in examples:
        for step in example.input_sequence.steps:
            assert step.time <= example.forecast_origin

            received_at = datetime.fromisoformat(
                step.provenance["received_at"]
            )

            assert received_at <= example.forecast_origin


def test_targets_match_actual_future_packet_values(demo_items):
    packets_by_id = {
        item.packet.packet_id: item.packet
        for item in demo_items
    }

    examples = build_next_observation_examples(demo_items)

    for example in examples:
        future_packet = packets_by_id[example.target_packet_id]

        soil = next(
            measurement
            for measurement in future_packet.measurements
            if measurement.sensor_type == "SOIL_MOISTURE"
        )

        assert example.target_value == soil.value


def test_repeated_generation_is_deterministic(demo_items):
    first = build_next_observation_examples(demo_items)
    second = build_next_observation_examples(demo_items)

    assert [item.to_record() for item in first] == [
        item.to_record() for item in second
    ]


def test_skips_missing_future_target(demo_items):
    selected = demo_items[0].packet
    device_items = [
        item
        for item in demo_items
        if item.packet.device_id == selected.device_id
        and item.packet.zone_id == selected.zone_id
    ]

    target_item = device_items[3]

    changed_packet = target_item.packet.model_copy(
        update={
            "measurements": [
                measurement
                for measurement in target_item.packet.measurements
                if measurement.sensor_type != "SOIL_MOISTURE"
            ]
        }
    )

    changed_items = [
        replace(item, packet=changed_packet)
        if item.packet.packet_id == target_item.packet.packet_id
        else item
        for item in demo_items
    ]

    examples = build_next_observation_examples(changed_items)

    assert len(examples) == 41


def test_late_history_packet_is_excluded(demo_items):
    device = demo_items[0].packet.device_id
    zone = demo_items[0].packet.zone_id

    device_items = [
        item
        for item in demo_items
        if item.packet.device_id == device
        and item.packet.zone_id == zone
    ]

    delayed_item = device_items[1]

    delayed_packet = delayed_item.packet.model_copy(
        update={
            "received_at": (
                device_items[-1].packet.observed_at
                + timedelta(hours=1)
            )
        }
    )

    changed_items = [
        replace(item, packet=delayed_packet)
        if item.packet.packet_id == delayed_item.packet.packet_id
        else item
        for item in demo_items
    ]

    examples = build_next_observation_examples(changed_items)

    assert not any(
        example.device_id == device
        and example.zone_id == zone
        and example.forecast_origin
        == device_items[2].packet.received_at
        for example in examples
    )


def test_rejects_invalid_history_configuration(demo_items):
    with pytest.raises(ValueError, match="min_history_steps"):
        build_next_observation_examples(
            demo_items,
            min_history_steps=0,
        )

    with pytest.raises(ValueError, match="max_history_steps"):
        build_next_observation_examples(
            demo_items,
            min_history_steps=5,
            max_history_steps=4,
        )


def test_device_splits_are_disjoint(demo_items):
    examples = build_next_observation_examples(demo_items)

    split = split_examples_by_device(examples)

    def devices(items):
        return {
            (item.zone_id, item.device_id)
            for item in items
        }

    train = devices(split.train)
    validation = devices(split.validation)
    test = devices(split.test)

    assert not train.intersection(validation)
    assert not train.intersection(test)
    assert not validation.intersection(test)

    assert len(split.train) == 28
    assert len(split.validation) == 7
    assert len(split.test) == 7


def test_dataset_records_are_json_serializable(demo_items):
    examples = build_next_observation_examples(demo_items)

    record = examples[0].to_record()
    encoded = json.dumps(record)
    decoded = json.loads(encoded)

    assert decoded["target"]["feature"] == "soil_moisture_pct"
    assert decoded["input_sequence"]["steps"]
    assert "target" not in decoded["input_sequence"]
