
"""Tests for C3's versioned simulator sensor feature extractor."""

from dataclasses import replace
from datetime import timedelta

import pytest

from components.c3_forecasting.feature_extractor import (
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    extract_simulator_sensor_features,
)
from components.c3_forecasting.sequence_builder import (
    build_pipe_temporal_sequence,
)
from shared.simulation.generator import (
    SimulationConfig,
    generate_baseline_packets,
)
from shared.simulation.scheduled_telemetry import (
    ScheduledTelemetryConfig,
    generate_scheduled_demo_telemetry,
)


@pytest.fixture
def packet():
    return generate_baseline_packets(
        SimulationConfig(packet_count=1)
    )[0]


def replace_measurements(packet, measurements):
    return packet.model_copy(
        update={"measurements": measurements}
    )


def scheduled_pipe_items():
    items = generate_scheduled_demo_telemetry(
        ScheduledTelemetryConfig()
    )

    first = items[0].packet

    return [
        item
        for item in items
        if item.packet.zone_id == first.zone_id
        and item.packet.device_id == first.device_id
    ]


def test_extracts_three_simulator_sensor_values(packet):
    features = extract_simulator_sensor_features(packet)

    assert set(features) == set(FEATURE_NAMES)
    assert len(features) == 3

    assert (
        features["soil_moisture_pct"]
        == packet.measurements[0].value
    )
    assert (
        features["temperature_c"]
        == packet.measurements[1].value
    )
    assert (
        features["atmospheric_pressure_hpa"]
        == packet.measurements[2].value
    )


def test_missing_sensor_preserves_feature_schema(packet):
    updated = replace_measurements(
        packet,
        [
            measurement
            for measurement in packet.measurements
            if measurement.sensor_type != "TEMPERATURE"
        ],
    )

    features = extract_simulator_sensor_features(updated)

    assert set(features) == set(FEATURE_NAMES)
    assert features["temperature_c"] is None
    assert features["soil_moisture_pct"] is not None


def test_raw_only_measurement_is_not_used_as_normalized_value(packet):
    original = packet.measurements[0]

    raw_only = original.model_copy(
        update={
            "raw_value": 1200.0,
            "value": None,
        }
    )

    updated = replace_measurements(
        packet,
        [raw_only, *packet.measurements[1:]],
    )

    features = extract_simulator_sensor_features(updated)

    assert features["soil_moisture_pct"] is None


def test_unknown_sensor_type_does_not_change_schema(packet):
    unknown = packet.measurements[0].model_copy(
        update={
            "sensor_instance_id": "UNKNOWN_SENSOR_01",
            "sensor_type": "UNREGISTERED_SENSOR",
        }
    )

    updated = replace_measurements(
        packet,
        [*packet.measurements, unknown],
    )

    features = extract_simulator_sensor_features(updated)

    assert set(features) == set(FEATURE_NAMES)
    assert (
        features["soil_moisture_pct"]
        == packet.measurements[0].value
    )


def test_rejects_unexpected_unit(packet):
    changed = packet.measurements[0].model_copy(
        update={"unit": "V"}
    )

    updated = replace_measurements(
        packet,
        [changed, *packet.measurements[1:]],
    )

    with pytest.raises(ValueError, match="Unexpected unit"):
        extract_simulator_sensor_features(updated)


def test_rejects_duplicate_sensor_type(packet):
    duplicate = packet.measurements[0].model_copy(
        update={"sensor_instance_id": "SECOND_SOIL_SENSOR"}
    )

    updated = replace_measurements(
        packet,
        [*packet.measurements, duplicate],
    )

    with pytest.raises(ValueError, match="Duplicate sensor type"):
        extract_simulator_sensor_features(updated)


def test_rejects_non_finite_measurement(packet):
    changed = packet.measurements[0].model_copy(
        update={"value": float("nan")}
    )

    updated = replace_measurements(
        packet,
        [changed, *packet.measurements[1:]],
    )

    with pytest.raises(ValueError, match="Non-finite"):
        extract_simulator_sensor_features(updated)


def test_builds_sensor_based_variable_rate_sequence():
    items = scheduled_pipe_items()

    first = items[0].packet

    sequence = build_pipe_temporal_sequence(
        items,
        zone_id=first.zone_id,
        device_id=first.device_id,
        forecast_origin=items[-1].packet.received_at,
        feature_extractor=extract_simulator_sensor_features,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
    )

    assert len(sequence.steps) == 10
    assert sequence.feature_schema_version == FEATURE_SCHEMA_VERSION

    assert all(
        set(step.features) == set(FEATURE_NAMES)
        for step in sequence.steps
    )

    assert sequence.steps[1].delta_t_seconds == 900.0
    assert sequence.steps[-1].delta_t_seconds == 5.0

    assert all(
        all(step.masks.values())
        for step in sequence.steps
    )


def test_delayed_measurement_is_not_available_to_c3():
    items = scheduled_pipe_items()
    origin = items[-1].packet.received_at

    delayed = items[0].packet.model_copy(
        update={
            "received_at": origin + timedelta(minutes=10),
        }
    )

    items[0] = replace(items[0], packet=delayed)

    first = items[0].packet

    sequence = build_pipe_temporal_sequence(
        items,
        zone_id=first.zone_id,
        device_id=first.device_id,
        forecast_origin=origin,
        feature_extractor=extract_simulator_sensor_features,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
    )

    assert len(sequence.steps) == 9
    assert sequence.steps[0].provenance["sequence_no"] == 1


def test_feature_extraction_is_reproducible():
    config = SimulationConfig(
        seed=20261014,
        packet_count=5,
    )

    first_run = generate_baseline_packets(config)
    second_run = generate_baseline_packets(config)

    first_features = [
        extract_simulator_sensor_features(packet)
        for packet in first_run
    ]

    second_features = [
        extract_simulator_sensor_features(packet)
        for packet in second_run
    ]

    assert first_features == second_features
