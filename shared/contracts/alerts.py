from datetime import datetime

from pydantic import Field

from shared.contracts.common import TimeAwareContractModel
from shared.enums import AlertSeverity, AlertStatus


class Alert(TimeAwareContractModel):
    """Operational alert generated from an approved system decision."""

    schema_version: str = Field(min_length=1)

    alert_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)

    severity: AlertSeverity

    alert_type: str = Field(min_length=1)

    decision_id: str | None = None

    message_code: str = Field(min_length=1)

    created_at: datetime

    status: AlertStatus

    correlation_id: str | None = None
    test_run_id: str | None = None
