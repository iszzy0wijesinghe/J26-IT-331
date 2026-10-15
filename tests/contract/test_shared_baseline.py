from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from shared.contracts import MeasurementEntry, SensorObservation, TelemetryPacket
from shared.enums import OperatingMode, SourceOrigin


def utc_now() -> datetime:
    return datetime.now(UTC)


def test_modes_are_frozen():
    assert [mode.value for mode in OperatingMode] == [
        "DEEP_SLEEP",
        "IDLE",
        "RISK",
        "WARNING",
        "EMERGENCY",
    ]


def test_packet_accepts_valid_normalized_telemetry():
    now = utc_now()

    packet = TelemetryPacket(
        schema_version="1.0",
        packet_id="PKT_001",
        zone_id="ZONE_01",
        device_id="PIPE_A1",
        boot_id="BOOT_001",
        sequence_no=1254,
        observed_at=now,
        received_at=now,
        source_origin=SourceOrigin.SIMULATED,
        measurements=[
            MeasurementEntry(
                sensor_instance_id="SM_A1_01",
                sensor_type="SOIL_MOISTURE",
                channel="CH1",
                raw_value=2310,
                value=67.4,
                unit="CALIBRATED_UNIT",
                calibration_version="CAL_001",
            )
        ],
    )

    assert packet.packet_id == "PKT_001"
    assert packet.sequence_no == 1254
    assert len(packet.measurements) == 1


def test_packet_rejects_unknown_fields():
    now = utc_now()

    with pytest.raises(ValidationError):
        TelemetryPacket(
            schema_version="1.0",
            packet_id="PKT_001",
            zone_id="ZONE_01",
            device_id="PIPE_A1",
            observed_at=now,
            received_at=now,
            source_origin=SourceOrigin.SIMULATED,
            unexpected="bad",
        )


def test_measurement_allows_zero():
    measurement = MeasurementEntry(
        sensor_instance_id="SM_A1_01",
        sensor_type="SOIL_MOISTURE",
        value=0.0,
    )

    assert measurement.value == 0.0


def test_measurement_rejects_missing_raw_and_calibrated_value():
    with pytest.raises(ValidationError):
        MeasurementEntry(
            sensor_instance_id="SM_A1_01",
            sensor_type="SOIL_MOISTURE",
        )


def test_sensor_observation_preserves_packet_identity():
    now = utc_now()

    observation = SensorObservation(
        schema_version="1.0",
        observation_id="OBS_001",
        packet_id="PKT_001",
        zone_id="ZONE_01",
        device_id="PIPE_A1",
        sensor_instance_id="SM_A1_01",
        observed_at=now,
        received_at=now,
        raw_value=2310,
        value=67.4,
        unit="CALIBRATED_UNIT",
        calibration_version="CAL_001",
        source_origin=SourceOrigin.SIMULATED,
    )

    assert observation.observation_id != observation.packet_id
    assert observation.packet_id == "PKT_001"


def test_packet_rejects_naive_timestamp():
    with pytest.raises(ValidationError):
        TelemetryPacket(
            schema_version="1.0",
            packet_id="PKT_001",
            zone_id="ZONE_01",
            device_id="PIPE_A1",
            observed_at=datetime.now(),
            received_at=utc_now(),
            source_origin=SourceOrigin.SIMULATED,
        )
