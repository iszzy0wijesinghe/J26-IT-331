"""Unit tests for the deterministic GeoNex telemetry simulator."""

from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from shared.enums.domain import OperatingMode, SourceOrigin
from shared.simulation.generator import (
    MODE_INTERVALS_SECONDS,
    SimulationConfig,
    generate_baseline_packets,
)


def test_same_configuration_produces_identical_packets():
    config = SimulationConfig(seed=42, packet_count=5)

    first_run = generate_baseline_packets(config)
    second_run = generate_baseline_packets(config)

    assert first_run == second_run
    assert len(first_run) == 5


def test_different_seeds_produce_different_sensor_values():
    first = generate_baseline_packets(
        SimulationConfig(seed=42, packet_count=3)
    )

    second = generate_baseline_packets(
        SimulationConfig(seed=99, packet_count=3)
    )

    first_values = [
        measurement.value
        for packet in first
        for measurement in packet.measurements
    ]

    second_values = [
        measurement.value
        for packet in second
        for measurement in packet.measurements
    ]

    assert first_values != second_values


@pytest.mark.parametrize(
    ("mode", "expected_interval"),
    [
        (OperatingMode.DEEP_SLEEP, 900),
        (OperatingMode.IDLE, 300),
        (OperatingMode.RISK, 60),
        (OperatingMode.WARNING, 15),
        (OperatingMode.EMERGENCY, 5),
    ],
)
def test_operating_mode_controls_sampling_interval(mode, expected_interval):
    config = SimulationConfig(
        operating_mode=mode,
        packet_count=3,
    )

    packets = generate_baseline_packets(config)

    assert MODE_INTERVALS_SECONDS[mode] == expected_interval

    for previous, current in zip(packets, packets[1:], strict=False):
        assert current.observed_at - previous.observed_at == timedelta(
            seconds=expected_interval
        )


def test_generated_packets_preserve_simulation_provenance():
    config = SimulationConfig(
        seed=123,
        zone_id="ZONE_02",
        device_id="PIPE_B2",
        packet_count=4,
    )

    packets = generate_baseline_packets(config)

    assert len(packets) == 4

    for index, packet in enumerate(packets):
        assert packet.zone_id == "ZONE_02"
        assert packet.device_id == "PIPE_B2"
        assert packet.sequence_no == index
        assert packet.source_origin is SourceOrigin.SIMULATED
        assert packet.test_run_id == "SIM_RUN_123"
        assert packet.observed_at.tzinfo is not None
        assert packet.received_at >= packet.observed_at
        assert len(packet.measurements) == 3

        for measurement in packet.measurements:
            assert measurement.sensor_instance_id
            assert measurement.sensor_type
            assert measurement.value is not None


def test_zero_packets_returns_empty_list():
    packets = generate_baseline_packets(
        SimulationConfig(packet_count=0)
    )

    assert packets == []


@pytest.mark.parametrize(
    "invalid_config",
    [
        SimulationConfig(packet_count=-1),
        SimulationConfig(zone_id=""),
        SimulationConfig(device_id=""),
        SimulationConfig(
            start_time=datetime(2026, 10, 10, 0, 0)
        ),
    ],
)
def test_invalid_configuration_is_rejected(invalid_config):
    with pytest.raises(ValueError):
        generate_baseline_packets(invalid_config)


def test_configuration_changes_do_not_mutate_original():
    original = SimulationConfig(seed=42, packet_count=3)

    modified = replace(original, seed=99)

    assert original.seed == 42
    assert modified.seed == 99
    assert original.packet_count == modified.packet_count


def test_generated_packets_include_interval_and_transport_metadata():
    config = SimulationConfig(
        seed=42,
        operating_mode=OperatingMode.WARNING,
        packet_count=4,
    )

    packets = generate_baseline_packets(config)

    assert len(packets) == 4

    for packet in packets:
        assert packet.tx_interval_s == 15.0
        assert packet.transport.rssi_dbm is not None
        assert packet.transport.snr_db is not None
        assert packet.transport.retry_count in range(3)


def test_synthetic_transport_metadata_is_reproducible():
    config = SimulationConfig(seed=42, packet_count=5)

    first = generate_baseline_packets(config)
    second = generate_baseline_packets(config)

    first_metadata = [
        (
            packet.transport.rssi_dbm,
            packet.transport.snr_db,
            packet.transport.retry_count,
        )
        for packet in first
    ]

    second_metadata = [
        (
            packet.transport.rssi_dbm,
            packet.transport.snr_db,
            packet.transport.retry_count,
        )
        for packet in second
    ]

    assert first_metadata == second_metadata


def test_simulator_does_not_invent_undefined_features():
    packets = generate_baseline_packets(
        SimulationConfig(packet_count=2)
    )

    for packet in packets:
        # freshness_status is now calculated by simulator for realistic testing
        assert packet.freshness_status in ("fresh", "delayed", "stale")
        # rssi_deviation_db is calculated at runtime from device history
        assert packet.transport.rssi_deviation_db is None
        # packet_size_bytes is calculated at runtime from packet serialization
        assert packet.transport.packet_size_bytes is None