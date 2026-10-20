"""Validation for the one-zone, hardware-aligned C3 PP1 simulator."""

from collections import Counter
from datetime import timedelta

import pytest

from components.c3_forecasting.data.simulated_devices import (
    DEVICE_IDS,
    GATEWAY_ID,
    DemoNetworkConfig,
    generate_one_zone_demo,
)
from shared.enums.domain import OperatingMode, SourceOrigin


def test_one_zone_four_nodes_and_forty_samples():
    records = generate_one_zone_demo()
    assert len(records) == 160
    assert set(row.packet.device_id for row in records) == set(DEVICE_IDS)
    assert {row.packet.zone_id for row in records} == {"ZONE_01"}
    assert Counter(row.packet.device_id for row in records) == dict.fromkeys(DEVICE_IDS, 40)


def test_all_records_are_explicitly_simulated():
    for row in generate_one_zone_demo():
        assert row.packet.source_origin == SourceOrigin.SIMULATED
        assert row.packet.test_run_id.startswith("SIM_HW_")
        assert row.packet.transport.gateway_id == GATEWAY_ID
        assert row.packet.transport.extra_metadata["simulation"] is True


def test_power_hub_and_black_box_are_not_sensor_nodes():
    records = generate_one_zone_demo()
    assert "POWER_HUB" not in {row.packet.device_id for row in records}
    assert GATEWAY_ID not in {row.packet.device_id for row in records}


def test_sensor_profiles_do_not_claim_fsr_pressure_or_calibrated_rain():
    first = {}
    for row in generate_one_zone_demo():
        first.setdefault(row.packet.device_id, row.packet)
    a_types = [entry.sensor_type for entry in first["PIPE_A1"].measurements]
    b_types = [entry.sensor_type for entry in first["PIPE_B1"].measurements]
    assert a_types.count("SOIL_MOISTURE") == 2
    assert a_types.count("FSR402_RAW_ADC") == 2
    assert b_types.count("SOIL_MOISTURE") == 2
    assert b_types.count("FSR402_RAW_ADC") == 1
    raw_rain = first["HUB_01"].measurements[0]
    assert raw_rain.sensor_type == "RAIN_MECHANISM_RAW"
    assert raw_rain.value is None
    assert raw_rain.raw_value is not None
    assert raw_rain.unit == "simulated_count"


def test_device_clock_and_variable_rate_are_preserved():
    records = [r for r in generate_one_zone_demo() if r.packet.device_id == "PIPE_A1"]
    assert records[0].delta_t_seconds is None
    assert records[1].delta_t_seconds == 900.0
    assert any(r.operating_mode == OperatingMode.EMERGENCY for r in records)
    for earlier, later in zip(records, records[1:], strict=False):
        assert later.packet.observed_at > earlier.packet.observed_at
        assert later.packet.received_at == later.packet.observed_at + timedelta(seconds=2)


def test_scenarios_are_reproducible():
    config = DemoNetworkConfig(seed=731, scenario="rapid_wetting_tilt")
    first = [r.packet.model_dump(mode="json") for r in generate_one_zone_demo(config)]
    second = [r.packet.model_dump(mode="json") for r in generate_one_zone_demo(config)]
    assert first == second


def test_scenarios_produce_temporal_changes():
    records = generate_one_zone_demo(DemoNetworkConfig(scenario="rapid_wetting_tilt"))
    soil = [
        next(m.value for m in row.packet.measurements if m.sensor_type == "SOIL_MOISTURE")
        for row in records
        if row.packet.device_id == "PIPE_A1"
    ]
    assert soil[-1] > soil[0] + 30


def test_rejects_unknown_scenario_and_naive_timestamp():
    with pytest.raises(ValueError, match="Unknown scenario"):
        generate_one_zone_demo(DemoNetworkConfig(scenario="made_up"))
    from datetime import datetime
    with pytest.raises(ValueError, match="timezone-aware"):
        generate_one_zone_demo(DemoNetworkConfig(start_time=datetime(2026, 10, 16)))


def test_measurement_channels_have_distinct_instance_ids():
    for row in generate_one_zone_demo():
        names = [m.sensor_instance_id for m in row.packet.measurements]
        assert len(names) == len(set(names))


def test_export_does_not_overwrite(tmp_path):
    import json

    from scripts.data.export_c3_simulated_devices import export_demo

    output = tmp_path / "recordings"
    manifest = export_demo(output, scenario="stable", seed=18)
    assert manifest["source_origin"] == "SIMULATED"
    assert manifest["packet_count"] == 160
    assert (output / "manifest.json").exists()
    packets = (output / "telemetry.jsonl").read_text().splitlines()
    assert len(packets) == 160
    assert json.loads(packets[0])["packet"]["source_origin"] == "SIMULATED"
    with pytest.raises(FileExistsError, match="already exists"):
        export_demo(output, scenario="stable", seed=18)
