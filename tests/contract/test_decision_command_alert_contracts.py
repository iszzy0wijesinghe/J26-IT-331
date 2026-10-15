from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from shared.contracts import (
    Alert,
    CommandAcknowledgement,
    Decision,
    DeviceCommand,
    ModeEvent,
    SamplingPolicy,
)
from shared.enums import (
    AlertSeverity,
    AlertStatus,
    CommandStatus,
    CommandType,
    DecisionType,
    OperatingMode,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def test_decision_engine_can_escalate_mode():
    now = utc_now()

    decision = Decision(
        schema_version="1.0",
        decision_id="DEC_001",
        zone_id="ZONE_01",
        decision_type=DecisionType.MODE_CHANGE,
        previous_mode=OperatingMode.RISK,
        selected_mode=OperatingMode.WARNING,
        forecast_id="FC_001",
        policy_version="DP_001",
        reason_codes=[
            "FORECAST_RISK_THRESHOLD",
            "PERSISTENCE_MET",
        ],
        generated_at=now,
    )

    assert decision.selected_mode is OperatingMode.WARNING


def test_mode_change_rejects_identical_modes():
    now = utc_now()

    with pytest.raises(ValidationError):
        Decision(
            schema_version="1.0",
            decision_id="DEC_002",
            zone_id="ZONE_01",
            decision_type=DecisionType.MODE_CHANGE,
            previous_mode=OperatingMode.RISK,
            selected_mode=OperatingMode.RISK,
            policy_version="DP_001",
            generated_at=now,
        )


def test_maintain_mode_requires_same_mode():
    now = utc_now()

    with pytest.raises(ValidationError):
        Decision(
            schema_version="1.0",
            decision_id="DEC_003",
            zone_id="ZONE_01",
            decision_type=DecisionType.MAINTAIN_MODE,
            previous_mode=OperatingMode.IDLE,
            selected_mode=OperatingMode.RISK,
            policy_version="DP_001",
            generated_at=now,
        )


def test_mode_event_preserves_decision_trace():
    now = utc_now()

    event = ModeEvent(
        schema_version="1.0",
        mode_event_id="MODE_001",
        zone_id="ZONE_01",
        previous_mode=OperatingMode.RISK,
        new_mode=OperatingMode.WARNING,
        effective_at=now,
        decision_id="DEC_001",
        policy_version="DP_001",
        reason_codes=["FORECAST_RISK_THRESHOLD"],
    )

    assert event.decision_id == "DEC_001"


def test_sampling_policy_keeps_rates_configurable():
    policy = SamplingPolicy(
        schema_version="1.0",
        policy_version="SP_001",
        mode=OperatingMode.RISK,
        device_profile="TYPE_A",
        acquisition_profile={
            "profile_name": "RISK_ACQUISITION",
        },
        aggregation_profile={
            "profile_name": "RISK_AGGREGATION",
        },
        report_interval_seconds=None,
    )

    assert policy.report_interval_seconds is None


def test_apply_mode_command_requires_requested_mode():
    now = utc_now()

    with pytest.raises(ValidationError):
        DeviceCommand(
            schema_version="1.0",
            command_id="CMD_001",
            target_device_id="PIPE_A1",
            zone_id="ZONE_01",
            command_type=CommandType.APPLY_MODE,
            requested_mode=None,
            policy_version="SP_001",
            issued_at=now,
            expires_at=now + timedelta(minutes=1),
            decision_id="DEC_001",
        )


def test_valid_apply_mode_command():
    now = utc_now()

    command = DeviceCommand(
        schema_version="1.0",
        command_id="CMD_002",
        target_device_id="PIPE_A1",
        zone_id="ZONE_01",
        command_type=CommandType.APPLY_MODE,
        requested_mode=OperatingMode.WARNING,
        policy_version="SP_001",
        issued_at=now,
        expires_at=now + timedelta(minutes=1),
        decision_id="DEC_001",
    )

    assert command.requested_mode is OperatingMode.WARNING


def test_command_expiry_must_follow_issue_time():
    now = utc_now()

    with pytest.raises(ValidationError):
        DeviceCommand(
            schema_version="1.0",
            command_id="CMD_003",
            target_device_id="PIPE_A1",
            zone_id="ZONE_01",
            command_type=CommandType.REQUEST_STATUS,
            issued_at=now,
            expires_at=now,
        )


def test_received_ack_does_not_require_applied_time():
    now = utc_now()

    ack = CommandAcknowledgement(
        schema_version="1.0",
        command_id="CMD_002",
        device_id="PIPE_A1",
        received_at=now,
        status=CommandStatus.RECEIVED,
    )

    assert ack.applied_at is None


def test_applied_ack_requires_applied_time():
    now = utc_now()

    with pytest.raises(ValidationError):
        CommandAcknowledgement(
            schema_version="1.0",
            command_id="CMD_002",
            device_id="PIPE_A1",
            received_at=now,
            status=CommandStatus.APPLIED,
            active_mode=OperatingMode.WARNING,
        )


def test_applied_ack_accepts_confirmed_application():
    now = utc_now()

    ack = CommandAcknowledgement(
        schema_version="1.0",
        command_id="CMD_002",
        device_id="PIPE_A1",
        received_at=now,
        applied_at=now + timedelta(milliseconds=50),
        status=CommandStatus.APPLIED,
        active_mode=OperatingMode.WARNING,
        active_policy_version="SP_001",
    )

    assert ack.status is CommandStatus.APPLIED


def test_alert_severity_is_separate_from_operating_mode():
    now = utc_now()

    alert = Alert(
        schema_version="1.0",
        alert_id="ALT_001",
        zone_id="ZONE_01",
        severity=AlertSeverity.WARNING,
        alert_type="LANDSLIDE_RISK",
        decision_id="DEC_001",
        message_code="HIGH_NEAR_TERM_RISK",
        created_at=now,
        status=AlertStatus.ACTIVE,
    )

    assert alert.severity is AlertSeverity.WARNING
    assert not isinstance(alert.severity, OperatingMode)
