"""Tests for GeoNex multi-pipe and variable-rate simulation."""

from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest

from shared.enums.domain import OperatingMode, SourceOrigin
from shared.simulation.mode_schedule import ModeSegment, generate_mode_schedule
from shared.simulation.runner import (
    MultiPipeSimulationConfig,
    derive_device_seed,
    generate_demo_packets,
)
from shared.simulation.scheduled_telemetry import (
    ScheduledTelemetryConfig,
    generate_scheduled_demo_telemetry,
)
from shared.simulation.topology import (
    GEONEX_DEMO_ZONES,
    PipeRole,
    get_all_demo_pipes,
    get_demo_zone,
)


def test_demonstration_topology_has_two_zones_and_six_pipes():
    assert len(GEONEX_DEMO_ZONES) == 2

    pipes = get_all_demo_pipes()

    assert len(pipes) == 6
    assert len({pipe.device_id for pipe in pipes}) == 6

    assert {pipe.device_id for pipe in pipes} == {
        "PIPE_A1",
        "PIPE_B1",
        "PIPE_BK1",
        "PIPE_A2",
        "PIPE_B2",
        "PIPE_BK2",
    }

    for zone in GEONEX_DEMO_ZONES:
        assert len(zone.pipes) == 3
        assert all(pipe.zone_id == zone.zone_id for pipe in zone.pipes)

        roles = {pipe.role for pipe in zone.pipes}

        assert roles == {
            PipeRole.TYPE_A,
            PipeRole.TYPE_B,
            PipeRole.BACKUP,
        }


def test_zone_lookup():
    zone = get_demo_zone("ZONE_01")

    assert zone.zone_id == "ZONE_01"
    assert len(zone.pipes) == 3

    with pytest.raises(ValueError):
        get_demo_zone("UNKNOWN_ZONE")


def test_device_seeds_are_stable_and_device_specific():
    first = derive_device_seed(42, "ZONE_01", "PIPE_A1")
    repeated = derive_device_seed(42, "ZONE_01", "PIPE_A1")
    different = derive_device_seed(42, "ZONE_01", "PIPE_B1")

    assert first == repeated
    assert first != different


def test_multi_pipe_generation_is_deterministic():
    config = MultiPipeSimulationConfig(
        seed=42,
        packets_per_pipe=5,
    )

    first = generate_demo_packets(config)
    second = generate_demo_packets(config)

    assert first == second
    assert len(first) == 30

    assert len({packet.packet_id for packet in first}) == 30

    counts = Counter(packet.device_id for packet in first)

    assert len(counts) == 6
    assert all(count == 5 for count in counts.values())


def test_multi_pipe_generation_has_independent_readings():
    packets = generate_demo_packets(
        MultiPipeSimulationConfig(
            seed=42,
            packets_per_pipe=3,
        )
    )

    readings = {
        packet.device_id: packet.measurements[0].value
        for packet in packets
        if packet.sequence_no == 0
    }

    assert len(readings) == 6
    assert len(set(readings.values())) == 6


def test_multi_pipe_packets_are_chronologically_sorted():
    packets = generate_demo_packets(
        MultiPipeSimulationConfig(packets_per_pipe=3)
    )

    assert packets == sorted(
        packets,
        key=lambda packet: (
            packet.observed_at,
            packet.zone_id,
            packet.device_id,
            packet.sequence_no,
        ),
    )


def test_mode_schedule_generates_variable_intervals():
    segments = (
        ModeSegment(OperatingMode.DEEP_SLEEP, 2),
        ModeSegment(OperatingMode.IDLE, 2),
        ModeSegment(OperatingMode.RISK, 2),
        ModeSegment(OperatingMode.WARNING, 2),
        ModeSegment(OperatingMode.EMERGENCY, 2),
    )

    samples = generate_mode_schedule(
        datetime(2026, 10, 10, tzinfo=UTC),
        segments,
    )

    assert len(samples) == 10

    assert [sample.delta_t_seconds for sample in samples] == [
        None,
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

    for previous, current in zip(samples, samples[1:], strict=False):
        assert current.observed_at > previous.observed_at

        assert current.observed_at - previous.observed_at == timedelta(
            seconds=current.delta_t_seconds
        )


@pytest.mark.parametrize(
    "segments",
    [
        (),
        (ModeSegment(OperatingMode.IDLE, 0),),
        (ModeSegment(OperatingMode.RISK, -1),),
    ],
)
def test_invalid_mode_segments_are_rejected(segments):
    with pytest.raises(ValueError):
        generate_mode_schedule(
            datetime(2026, 10, 10, tzinfo=UTC),
            segments,
        )


def test_scheduled_telemetry_is_deterministic():
    config = ScheduledTelemetryConfig(seed=42)

    first = generate_scheduled_demo_telemetry(config)
    second = generate_scheduled_demo_telemetry(config)

    assert first == second
    assert len(first) == 60

    assert len({item.packet.packet_id for item in first}) == 60

    assert all(
        item.packet.source_origin is SourceOrigin.SIMULATED
        for item in first
    )


def test_scheduled_telemetry_preserves_mode_context():
    packets = generate_scheduled_demo_telemetry(
        ScheduledTelemetryConfig()
    )

    pipe_a1 = [
        item
        for item in packets
        if item.packet.device_id == "PIPE_A1"
    ]

    assert len(pipe_a1) == 10

    assert [item.operating_mode for item in pipe_a1] == [
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

    assert [item.packet.sequence_no for item in pipe_a1] == list(range(10))


def test_scheduled_telemetry_uses_expected_timestamps():
    packets = generate_scheduled_demo_telemetry(
        ScheduledTelemetryConfig()
    )

    pipe_a1 = [
        item
        for item in packets
        if item.packet.device_id == "PIPE_A1"
    ]

    for index, item in enumerate(pipe_a1):
        assert item.packet.received_at == item.packet.observed_at

        if index == 0:
            assert item.delta_t_seconds is None
        else:
            previous = pipe_a1[index - 1]

            assert (
                item.packet.observed_at - previous.packet.observed_at
            ).total_seconds() == item.delta_t_seconds