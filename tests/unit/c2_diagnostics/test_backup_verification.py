import pytest

from components.c2_diagnostics.backup_pipe.verification import (
    verify_backup_telemetry,
)


def test_backup_unreachable():
    result = verify_backup_telemetry(
        backup_reachable=False,
        primary_values={"tilt_x": 1.0},
        backup_values={"tilt_x": 1.0},
    )

    assert result.verified is False
    assert result.reason == "backup_unreachable"


def test_matching_telemetry_is_verified():
    result = verify_backup_telemetry(
        backup_reachable=True,
        primary_values={"tilt_x": 1.0, "vibration": 0.2},
        backup_values={"tilt_x": 1.1, "vibration": 0.3},
        tolerance=0.5,
    )

    assert result.verified is True
    assert result.reason == "telemetry_consistent"


def test_large_deviation_is_not_verified():
    result = verify_backup_telemetry(
        backup_reachable=True,
        primary_values={"tilt_x": 1.0},
        backup_values={"tilt_x": 2.0},
        tolerance=0.5,
    )

    assert result.verified is False
    assert result.reason == "telemetry_deviation_exceeded"
    assert result.deviation == pytest.approx(1.0)


def test_missing_telemetry_is_not_verified():
    result = verify_backup_telemetry(
        backup_reachable=True,
        primary_values=None,
        backup_values={"tilt_x": 1.0},
    )

    assert result.verified is False
    assert result.reason == "telemetry_missing"


def test_negative_tolerance_is_rejected():
    with pytest.raises(ValueError):
        verify_backup_telemetry(
            backup_reachable=True,
            primary_values={"tilt_x": 1.0},
            backup_values={"tilt_x": 1.0},
            tolerance=-0.1,
        )