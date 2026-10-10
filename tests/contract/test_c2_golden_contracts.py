from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from shared.contracts import (
    C2Diagnosis,
    ExpectedObservation,
    GoldenObservation,
    RecoveredObservation,
    RecoveryEvent,
    SilenceEvent,
)
from shared.enums import (
    C1CredibilityLabel,
    C2Action,
    C2FailureType,
    C4TrustLabel,
    OperatingMode,
    RecoveryProvenance,
    RecoveryStatus,
    SilenceState,
    SourceOrigin,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def test_expected_observation_accepts_valid_policy_timing():
    start = utc_now()

    expected = ExpectedObservation(
        schema_version="1.0",
        device_id="PIPE_A1",
        zone_id="ZONE_01",
        policy_version="SP_001",
        operating_mode=OperatingMode.RISK,
        last_accepted_report_at=start,
        expected_next_report_at=start + timedelta(minutes=5),
        deadline_at=start + timedelta(minutes=5, seconds=30),
    )

    assert expected.operating_mode is OperatingMode.RISK


def test_expected_observation_rejects_deadline_before_expected_time():
    start = utc_now()

    with pytest.raises(ValidationError):
        ExpectedObservation(
            schema_version="1.0",
            device_id="PIPE_A1",
            zone_id="ZONE_01",
            policy_version="SP_001",
            operating_mode=OperatingMode.RISK,
            last_accepted_report_at=start,
            expected_next_report_at=start + timedelta(minutes=5),
            deadline_at=start + timedelta(minutes=4),
        )


def test_silence_event_preserves_active_mode_and_policy():
    expected_at = utc_now()
    deadline = expected_at + timedelta(seconds=30)

    event = SilenceEvent(
        schema_version="1.0",
        silence_event_id="SIL_001",
        zone_id="ZONE_01",
        device_id="PIPE_A1",
        detected_at=deadline + timedelta(seconds=1),
        expected_at=expected_at,
        deadline_at=deadline,
        operating_mode=OperatingMode.RISK,
        policy_version="SP_001",
        state=SilenceState.CONFIRMED_SILENCE,
    )

    assert event.state is SilenceState.CONFIRMED_SILENCE


def test_c2_diagnosis_keeps_diagnosis_separate_from_action():
    diagnosis = C2Diagnosis(
        schema_version="1.0",
        diagnosis_id="C2D_001",
        silence_event_id="SIL_001",
        device_id="PIPE_A1",
        failure_type=C2FailureType.HARDWARE_FAILURE,
        confidence=0.88,
        backup_verification_used=True,
        evidence_codes=[
            "PRIMARY_MISSING",
            "HUB_REACHABLE",
            "BACKUP_RESPONDED",
        ],
        recommended_action=C2Action.ACTIVATE_BACKUP_SENSOR,
        model_version="C2_MODEL_001",
        generated_at=utc_now(),
    )

    assert diagnosis.failure_type is C2FailureType.HARDWARE_FAILURE
    assert diagnosis.recommended_action is C2Action.ACTIVATE_BACKUP_SENSOR


def test_recovery_event_rejects_completion_before_start():
    start = utc_now()

    with pytest.raises(ValidationError):
        RecoveryEvent(
            schema_version="1.0",
            recovery_event_id="REC_001",
            silence_event_id="SIL_001",
            diagnosis_id="C2D_001",
            action=C2Action.REQUEST_SD_REPLAY,
            started_at=start,
            completed_at=start - timedelta(seconds=1),
            status=RecoveryStatus.SUCCESS,
            recovered_count=4,
        )


def test_recovered_observation_preserves_old_observed_time():
    received = utc_now()
    observed = received - timedelta(minutes=10)

    recovered = RecoveredObservation(
        schema_version="1.0",
        observation_id="OBS_REC_001",
        zone_id="ZONE_01",
        device_id="PIPE_A1",
        sensor_instance_id="SM_A1_01",
        observed_at=observed,
        received_at=received,
        value=68.1,
        recovery_provenance=RecoveryProvenance.LATE_ORIGINAL,
        recovery_confidence=1.0,
        recovery_event_id="REC_001",
        source_origin=SourceOrigin.PHYSICAL_DEMO,
        original_packet_id="PKT_001",
        original_sequence_no=100,
    )

    assert recovered.observed_at < recovered.received_at


def test_recovered_observation_cannot_claim_direct_provenance():
    now = utc_now()

    with pytest.raises(ValidationError):
        RecoveredObservation(
            schema_version="1.0",
            observation_id="OBS_REC_002",
            zone_id="ZONE_01",
            device_id="PIPE_A1",
            sensor_instance_id="SM_A1_01",
            observed_at=now,
            received_at=now,
            value=68.1,
            recovery_provenance=RecoveryProvenance.DIRECT,
            recovery_event_id="REC_002",
            source_origin=SourceOrigin.PHYSICAL_DEMO,
        )


def test_golden_direct_observation_is_runtime_eligible():
    now = utc_now()

    golden = GoldenObservation(
        schema_version="1.0",
        golden_observation_id="GOBS_001",
        source_observation_id="OBS_001",
        zone_id="ZONE_01",
        device_id="PIPE_A1",
        sensor_instance_id="SM_A1_01",
        observed_at=now,
        available_at=now,
        value=67.4,
        unit="CALIBRATED_UNIT",
        recovery_provenance=RecoveryProvenance.DIRECT,
        trust_label=C4TrustLabel.TRUSTED,
        credibility_label=C1CredibilityLabel.VALID_EVENT,
        quality_score=0.91,
        is_estimated=False,
        c4_assessment_id="C4A_001",
        c1_assessment_id="C1A_001",
    )

    assert golden.is_available_as_of(now + timedelta(seconds=1))


def test_as_of_rule_blocks_future_recovered_information():
    observed = datetime(2026, 10, 10, 10, 0, tzinfo=UTC)
    recovered = datetime(2026, 10, 10, 10, 20, tzinfo=UTC)
    forecast_origin = datetime(2026, 10, 10, 10, 10, tzinfo=UTC)

    golden = GoldenObservation(
        schema_version="1.0",
        golden_observation_id="GOBS_002",
        source_observation_id="OBS_REC_001",
        zone_id="ZONE_01",
        device_id="PIPE_A1",
        sensor_instance_id="SM_A1_01",
        observed_at=observed,
        available_at=recovered,
        value=68.1,
        recovery_provenance=RecoveryProvenance.LATE_ORIGINAL,
        trust_label=C4TrustLabel.TRUSTED,
        credibility_label=C1CredibilityLabel.CLEAN,
        quality_score=0.95,
        is_estimated=False,
        c4_assessment_id="C4A_002",
        c1_assessment_id="C1A_002",
        c2_recovery_event_id="REC_001",
    )

    assert golden.observed_at <= forecast_origin
    assert not golden.is_available_as_of(forecast_origin)
    assert golden.is_available_as_of(recovered)


def test_estimated_golden_value_must_be_marked_estimated():
    now = utc_now()

    with pytest.raises(ValidationError):
        GoldenObservation(
            schema_version="1.0",
            golden_observation_id="GOBS_003",
            source_observation_id="OBS_REC_003",
            zone_id="ZONE_01",
            device_id="PIPE_A1",
            sensor_instance_id="SM_A1_01",
            observed_at=now,
            available_at=now,
            value=67.0,
            recovery_provenance=RecoveryProvenance.FUSED,
            trust_label=C4TrustLabel.TRUSTED,
            credibility_label=C1CredibilityLabel.CLEAN,
            is_estimated=False,
            c4_assessment_id="C4A_003",
            c1_assessment_id="C1A_003",
            c2_recovery_event_id="REC_003",
        )