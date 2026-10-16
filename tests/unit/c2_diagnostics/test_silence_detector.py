from datetime import datetime, timedelta, timezone

import pytest

from components.c2_diagnostics.monitoring.silence_detector import (
    detect_silence,
)
from shared.contracts.c2_diagnostics import ExpectedObservation
from shared.enums import OperatingMode, SilenceState


@pytest.fixture
def expected_observation():
    last_report = datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)

    return ExpectedObservation(
        schema_version="1.0",
        device_id="sensor-001",
        zone_id="zone-001",
        policy_version="policy-1",
        operating_mode=OperatingMode.RISK,
        last_accepted_report_at=last_report,
        expected_next_report_at=last_report + timedelta(seconds=60),
        deadline_at=last_report + timedelta(seconds=90),
    )


def test_no_event_before_expected_time(expected_observation):
    now = datetime(2026, 10, 16, 10, 0, 30, tzinfo=timezone.utc)

    result = detect_silence(expected_observation, now)

    assert result is None


def test_late_report_detection(expected_observation):
    now = datetime(2026, 10, 16, 10, 1, 15, tzinfo=timezone.utc)

    result = detect_silence(
        expected_observation,
        now,
        silence_event_id="silence-test-001",
    )

    assert result is not None
    assert result.state == SilenceState.LATE
    assert result.device_id == "sensor-001"
    assert result.zone_id == "zone-001"


def test_confirmed_silence_after_deadline(expected_observation):
    now = datetime(2026, 10, 16, 10, 2, tzinfo=timezone.utc)

    result = detect_silence(
        expected_observation,
        now,
        silence_event_id="silence-test-002",
    )

    assert result is not None
    assert result.state == SilenceState.CONFIRMED_SILENCE


def test_naive_datetime_is_rejected(expected_observation):
    now = datetime(2026, 10, 16, 10, 2)

    with pytest.raises(ValueError, match="timezone-aware"):
        detect_silence(expected_observation, now)
