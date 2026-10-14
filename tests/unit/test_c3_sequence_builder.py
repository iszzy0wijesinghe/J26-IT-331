
"""Tests for the initial C3 variable-rate temporal sequence builder."""

from dataclasses import replace
from datetime import timedelta

import pytest

from components.c3_forecasting.sequence_builder import (
    build_pipe_temporal_sequence,
)
from shared.enums.domain import OperatingMode
from shared.simulation.scheduled_telemetry import (
    ScheduledTelemetryConfig,
    generate_scheduled_demo_telemetry,
)


def example_samples():
    """Return one pipe's ten deterministic scheduled packets."""
    items = generate_scheduled_demo_telemetry(
        ScheduledTelemetryConfig()
    )

    first_packet = items[0].packet

    selected = [
        item
        for item in items
        if item.packet.zone_id == first_packet.zone_id
        and item.packet.device_id == first_packet.device_id
    ]

    return selected


def build_sequence(items, *, forecast_origin=None, max_steps=None):
    packet = items[0].packet

    return build_pipe_temporal_sequence(
        items,
        zone_id=packet.zone_id,
        device_id=packet.device_id,
        forecast_origin=forecast_origin or items[-1].packet.received_at,
        feature_extractor=lambda packet: {
            # Test fixture only, not a physical sensor measurement.
            "test_sequence_index": float(packet.sequence_no),
        },
        max_steps=max_steps,
    )


def test_builds_ten_chronological_steps():
    items = example_samples()

    result = build_sequence(items)

    assert len(result.steps) == 10
    assert result.zone_id == items[0].packet.zone_id

    times = [step.time for step in result.steps]
    assert times == sorted(times)


def test_preserves_variable_sampling_intervals():
    result = build_sequence(example_samples())

    actual_intervals = [
        step.delta_t_seconds
        for step in result.steps
    ]

    assert actual_intervals == [
        0.0,
        900.0,
        900.0,
        300.0,
        300.0,
        60.0,
        60.0,
        15.0,
        15.0,
        5.0,
    ]


def test_preserves_operating_mode_transitions():
    result = build_sequence(example_samples())

    assert [step.operating_mode for step in result.steps] == [
        OperatingMode.DEEP_SLEEP,
        OperatingMode.DEEP_SLEEP,
        OperatingMode.IDLE,
        OperatingMode.IDLE,
        OperatingMode.RISK,
        OperatingMode.RISK,
        OperatingMode.WARNING,
        OperatingMode.WARNING,
        OperatingMode.EMERGENCY,
        OperatingMode.EMERGENCY,
    ]


def test_does_not_use_future_observations():
    items = example_samples()

    origin = items[4].packet.received_at
    result = build_sequence(items, forecast_origin=origin)

    assert len(result.steps) == 5

    assert all(
        step.time <= origin
        for step in result.steps
    )


def test_does_not_use_delayed_packets():
    items = example_samples()
    origin = items[-1].packet.received_at

    late_packet = items[0].packet.model_copy(
        update={
            "received_at": origin + timedelta(minutes=10),
        }
    )

    items[0] = replace(items[0], packet=late_packet)

    result = build_sequence(items, forecast_origin=origin)

    assert len(result.steps) == 9
    assert result.steps[0].provenance["sequence_no"] == 1


def test_max_steps_preserves_latest_history():
    result = build_sequence(
        example_samples(),
        max_steps=3,
    )

    assert len(result.steps) == 3
    assert result.steps[0].delta_t_seconds == 0.0
    assert result.steps[0].quality["first_interval_unknown"] is True


def test_missing_feature_has_false_mask_and_no_age():
    items = example_samples()
    packet = items[0].packet

    result = build_pipe_temporal_sequence(
        items,
        zone_id=packet.zone_id,
        device_id=packet.device_id,
        forecast_origin=items[-1].packet.received_at,
        feature_extractor=lambda packet: {
            "example_feature": (
                None if packet.sequence_no == 0
                else float(packet.sequence_no)
            ),
        },
    )

    assert result.steps[0].features["example_feature"] is None
    assert result.steps[0].masks["example_feature"] is False
    assert result.steps[0].ages_seconds["example_feature"] is None

    assert result.steps[1].masks["example_feature"] is True
    assert result.steps[1].ages_seconds["example_feature"] == 0.0


def test_rejects_invalid_history_size():
    with pytest.raises(ValueError, match="max_steps"):
        build_sequence(example_samples(), max_steps=0)


def test_rejects_unavailable_history():
    items = example_samples()

    origin = items[0].packet.observed_at - timedelta(seconds=1)

    with pytest.raises(ValueError, match="No observations"):
        build_sequence(items, forecast_origin=origin)


def test_rejects_empty_feature_mapping():
    items = example_samples()
    packet = items[0].packet

    with pytest.raises(ValueError, match="feature_extractor"):
        build_pipe_temporal_sequence(
            items,
            zone_id=packet.zone_id,
            device_id=packet.device_id,
            forecast_origin=items[-1].packet.received_at,
            feature_extractor=lambda packet: {},
        )
