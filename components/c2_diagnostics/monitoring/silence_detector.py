from datetime import datetime, timezone

from shared.contracts.c2_diagnostics import (
    ExpectedObservation,
    SilenceEvent,
)
from shared.enums import SilenceState


def detect_silence(
    expected: ExpectedObservation,
    now: datetime,
    schema_version: str = "1.0",
    silence_event_id: str | None = None,
    correlation_id: str | None = None,
    test_run_id: str | None = None,
) -> SilenceEvent | None:
    """Detect a late or missing report using the active reporting schedule.

    Returns None when the next report is not yet due.
    Returns a SilenceEvent when the expected report is late.

    The caller must supply the schedule derived from the active sampling
    policy. This function does not independently invent reporting intervals.
    """

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    now = now.astimezone(timezone.utc)
    expected_at = expected.expected_next_report_at.astimezone(
        timezone.utc
    )
    deadline_at = expected.deadline_at.astimezone(timezone.utc)

    if now < expected_at:
        return None

    if now < deadline_at:
        state = SilenceState.LATE
    else:
        state = SilenceState.CONFIRMED_SILENCE

    if silence_event_id is None:
        silence_event_id = (
            f"silence-{expected.device_id}-"
            f"{int(now.timestamp())}"
        )

    return SilenceEvent(
        schema_version=schema_version,
        silence_event_id=silence_event_id,
        zone_id=expected.zone_id,
        device_id=expected.device_id,
        detected_at=now,
        expected_at=expected_at,
        deadline_at=deadline_at,
        operating_mode=expected.operating_mode,
        policy_version=expected.policy_version,
        state=state,
        correlation_id=correlation_id,
        test_run_id=test_run_id,
    )
