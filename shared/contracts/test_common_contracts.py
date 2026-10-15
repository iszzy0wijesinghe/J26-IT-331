from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from shared.contracts.common import (
    EventEnvelope,
    EventSource,
    ProcessingError,
)
from shared.enums import ProcessingStatus


def test_event_envelope_accepts_timezone_aware_timestamp():
    envelope = EventEnvelope(
        schema_version="1.0",
        event_type="TEST_EVENT",
        event_id="EVT_001",
        generated_at=datetime.now(UTC),
        source=EventSource(
            service="test-service",
            component="TEST",
        ),
        correlation_id="CORR_001",
        payload={"value": 1},
    )

    assert envelope.event_id == "EVT_001"


def test_event_envelope_rejects_naive_timestamp():
    with pytest.raises(ValidationError):
        EventEnvelope(
            schema_version="1.0",
            event_type="TEST_EVENT",
            event_id="EVT_001",
            generated_at=datetime.now(),
            source=EventSource(service="test-service"),
            payload={},
        )


def test_event_envelope_rejects_unknown_field():
    with pytest.raises(ValidationError):
        EventEnvelope(
            schema_version="1.0",
            event_type="TEST_EVENT",
            event_id="EVT_001",
            generated_at=datetime.now(UTC),
            source=EventSource(service="test-service"),
            payload={},
            undocumented_field="should-fail",
        )


def test_processing_error_accepts_explicit_failure():
    error = ProcessingError(
        status=ProcessingStatus.MODEL_UNAVAILABLE,
        error_code="C3_MODEL_NOT_LOADED",
        retryable=False,
        correlation_id="CORR_001",
        generated_at=datetime.now(UTC),
    )

    assert error.status is ProcessingStatus.MODEL_UNAVAILABLE


@pytest.mark.parametrize(
    "status",
    [
        ProcessingStatus.OK,
        ProcessingStatus.PARTIAL,
    ],
)
def test_processing_error_rejects_non_failure_status(status):
    with pytest.raises(ValidationError):
        ProcessingError(
            status=status,
            error_code="INVALID_ERROR_STATE",
            retryable=False,
            generated_at=datetime.now(UTC),
        )
