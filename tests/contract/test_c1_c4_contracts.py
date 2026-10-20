from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from shared.contracts import C1CredibilityAssessment, C4TrustAssessment
from shared.enums import (
    C1ContextStatus,
    C1CredibilityLabel,
    C4RoutingOutcome,
    C4TrustLabel,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def test_c4_accepts_trusted_packet():
    assessment = C4TrustAssessment(
        schema_version="1.0",
        assessment_id="C4A_001",
        packet_id="PKT_001",
        device_id="PIPE_A1",
        trust_label=C4TrustLabel.TRUSTED,
        trust_score=0.97,
        mandatory_security_pass=True,
        reason_codes=[
            "IDENTITY_VALID",
            "INTEGRITY_VALID",
            "FRESHNESS_VALID",
        ],
        behavioural_score=0.08,
        routing_outcome=C4RoutingOutcome.ACCEPT,
        model_version="C4_MODEL_001",
        generated_at=utc_now(),
    )

    assert assessment.trust_label is C4TrustLabel.TRUSTED


def test_c4_mandatory_security_failure_cannot_be_trusted():
    with pytest.raises(ValidationError):
        C4TrustAssessment(
            schema_version="1.0",
            assessment_id="C4A_002",
            packet_id="PKT_002",
            device_id="PIPE_A1",
            trust_label=C4TrustLabel.TRUSTED,
            mandatory_security_pass=False,
            generated_at=utc_now(),
        )


def test_c4_allows_untrusted_security_failure():
    assessment = C4TrustAssessment(
        schema_version="1.0",
        assessment_id="C4A_003",
        packet_id="PKT_003",
        device_id="PIPE_A1",
        trust_label=C4TrustLabel.UNTRUSTED,
        mandatory_security_pass=False,
        routing_outcome=C4RoutingOutcome.REJECT,
        generated_at=utc_now(),
    )

    assert assessment.mandatory_security_pass is False


def test_c4_unknown_requires_security_review_routing():
    assessment = C4TrustAssessment(
        schema_version="1.0",
        assessment_id="C4A_UNKNOWN",
        packet_id="PKT_UNKNOWN",
        device_id="PIPE_A1",
        trust_label=C4TrustLabel.UNKNOWN,
        mandatory_security_pass=False,
        routing_outcome=C4RoutingOutcome.SECURITY_REVIEW,
        reason_codes=["ATTESTATION_UNVERIFIED"],
        generated_at=utc_now(),
    )

    assert assessment.routing_outcome is C4RoutingOutcome.SECURITY_REVIEW


def test_c4_rejects_unknown_telemetry_marked_accepted():
    with pytest.raises(ValidationError):
        C4TrustAssessment(
            schema_version="1.0",
            assessment_id="C4A_UNKNOWN_ACCEPTED",
            packet_id="PKT_UNKNOWN_ACCEPTED",
            device_id="PIPE_A1",
            trust_label=C4TrustLabel.UNKNOWN,
            mandatory_security_pass=False,
            routing_outcome=C4RoutingOutcome.ACCEPT,
            generated_at=utc_now(),
        )


def test_c1_accepts_valid_event():
    assessment = C1CredibilityAssessment(
        schema_version="1.0",
        assessment_id="C1A_001",
        observation_id="OBS_001",
        credibility_label=C1CredibilityLabel.VALID_EVENT,
        confidence=0.91,
        class_probabilities={
            C1CredibilityLabel.CLEAN: 0.06,
            C1CredibilityLabel.ANOMALY: 0.03,
            C1CredibilityLabel.VALID_EVENT: 0.91,
        },
        context_status=C1ContextStatus.COMPLETE,
        reason_codes=[
            "RAINFALL_CONTEXT_SUPPORTS_CHANGE",
            "NEIGHBOURS_AGREE",
        ],
        model_version="C1_MODEL_001",
        generated_at=utc_now(),
    )

    assert assessment.credibility_label is C1CredibilityLabel.VALID_EVENT


def test_c1_rejects_probability_outside_valid_range():
    with pytest.raises(ValidationError):
        C1CredibilityAssessment(
            schema_version="1.0",
            assessment_id="C1A_002",
            observation_id="OBS_002",
            credibility_label=C1CredibilityLabel.CLEAN,
            class_probabilities={
                C1CredibilityLabel.CLEAN: 1.2,
                C1CredibilityLabel.ANOMALY: -0.1,
                C1CredibilityLabel.VALID_EVENT: -0.1,
            },
            context_status=C1ContextStatus.COMPLETE,
            generated_at=utc_now(),
        )


def test_c1_rejects_probabilities_that_do_not_sum_to_one():
    with pytest.raises(ValidationError):
        C1CredibilityAssessment(
            schema_version="1.0",
            assessment_id="C1A_003",
            observation_id="OBS_003",
            credibility_label=C1CredibilityLabel.CLEAN,
            class_probabilities={
                C1CredibilityLabel.CLEAN: 0.50,
                C1CredibilityLabel.ANOMALY: 0.10,
                C1CredibilityLabel.VALID_EVENT: 0.10,
            },
            context_status=C1ContextStatus.COMPLETE,
            generated_at=utc_now(),
        )


def test_c1_allows_model_without_probability_output():
    assessment = C1CredibilityAssessment(
        schema_version="1.0",
        assessment_id="C1A_004",
        observation_id="OBS_004",
        credibility_label=C1CredibilityLabel.ANOMALY,
        confidence=None,
        class_probabilities=None,
        context_status=C1ContextStatus.PARTIAL,
        model_version="C1_RULE_BASELINE_001",
        generated_at=utc_now(),
    )

    assert assessment.class_probabilities is None
