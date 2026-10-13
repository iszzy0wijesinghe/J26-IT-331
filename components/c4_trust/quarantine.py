from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from shared.contracts import C4TrustAssessment
from shared.enums import C4RoutingOutcome, C4TrustLabel


class QuarantineReason(str, Enum):
    """Reasons for quarantining telemetry."""

    BEHAVIOURAL_ANOMALY = "BEHAVIOURAL_ANOMALY"
    WEAK_SIGNAL = "WEAK_SIGNAL"
    DEVICE_HEALTH_DEGRADED = "DEVICE_HEALTH_DEGRADED"
    CLOCK_DELAY = "CLOCK_DELAY"
    INTERVAL_ANOMALY = "INTERVAL_ANOMALY"
    RSSI_PROFILE_ANOMALY = "RSSI_PROFILE_ANOMALY"
    PATH_MISMATCH = "PATH_MISMATCH"
    CUSTOM = "CUSTOM"


@dataclass
class QuarantineRecord:
    """Record of quarantined telemetry."""

    quarantine_id: str
    packet_id: str
    device_id: str
    trust_label: C4TrustLabel
    routing_outcome: C4RoutingOutcome
    reason_codes: list[str]
    quarantine_reason: QuarantineReason
    quarantined_at: datetime
    packet_data: dict[str, Any] = field(default_factory=dict)
    assessment: C4TrustAssessment | None = None
    released: bool = False
    released_at: datetime | None = None
    release_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class QuarantineManager:
    """Manage quarantined telemetry for audit and investigation.

    Quarantined packets are retained but not eligible for normal
    downstream environmental use until reviewed and released.
    """

    def __init__(self, quarantine_dir: Path | None = None) -> None:
        """Initialize quarantine manager.

        Args:
            quarantine_dir: Directory to store quarantine records
        """
        self._quarantine_dir = quarantine_dir or Path("quarantine")
        self._quarantine_dir.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, QuarantineRecord] = {}

    def quarantine(
        self,
        packet_id: str,
        device_id: str,
        trust_label: C4TrustLabel,
        routing_outcome: C4RoutingOutcome,
        reason_codes: list[str],
        quarantine_reason: QuarantineReason,
        packet_data: dict[str, Any] | None = None,
        assessment: C4TrustAssessment | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> QuarantineRecord:
        """Quarantine a telemetry packet.

        Args:
            packet_id: Packet identifier
            device_id: Device identifier
            trust_label: Trust label
            routing_outcome: Routing outcome
            reason_codes: Reason codes for trust decision
            quarantine_reason: Specific quarantine reason
            packet_data: Raw packet data
            assessment: C4 trust assessment
            metadata: Additional metadata

        Returns:
            QuarantineRecord
        """
        quarantine_id = f"Q_{uuid4().hex[:12]}"
        record = QuarantineRecord(
            quarantine_id=quarantine_id,
            packet_id=packet_id,
            device_id=device_id,
            trust_label=trust_label,
            routing_outcome=routing_outcome,
            reason_codes=reason_codes,
            quarantine_reason=quarantine_reason,
            quarantined_at=datetime.now(UTC),
            packet_data=packet_data or {},
            assessment=assessment,
            metadata=metadata or {},
        )

        self._records[quarantine_id] = record
        self._save_record(record)

        return record

    def release(
        self,
        quarantine_id: str,
        release_reason: str,
    ) -> QuarantineRecord:
        """Release a quarantined packet.

        Args:
            quarantine_id: Quarantine record ID
            release_reason: Reason for release

        Returns:
            Updated QuarantineRecord

        Raises:
            ValueError: If quarantine_id not found
        """
        record = self._records.get(quarantine_id)
        if record is None:
            raise ValueError(f"Quarantine record {quarantine_id} not found")

        if record.released:
            raise ValueError(f"Quarantine record {quarantine_id} already released")

        # Create updated record
        updated_record = QuarantineRecord(
            quarantine_id=record.quarantine_id,
            packet_id=record.packet_id,
            device_id=record.device_id,
            trust_label=record.trust_label,
            routing_outcome=C4RoutingOutcome.ACCEPT,  # Released packets are accepted
            reason_codes=record.reason_codes,
            quarantine_reason=record.quarantine_reason,
            quarantined_at=record.quarantined_at,
            packet_data=record.packet_data,
            assessment=record.assessment,
            released=True,
            released_at=datetime.now(UTC),
            release_reason=release_reason,
            metadata=record.metadata,
        )

        self._records[quarantine_id] = updated_record
        self._save_record(updated_record)

        return updated_record

    def get(self, quarantine_id: str) -> QuarantineRecord | None:
        """Get quarantine record by ID.

        Args:
            quarantine_id: Quarantine record ID

        Returns:
            QuarantineRecord if found, None otherwise
        """
        return self._records.get(quarantine_id)

    def list_by_device(self, device_id: str) -> list[QuarantineRecord]:
        """List quarantine records for a device.

        Args:
            device_id: Device identifier

        Returns:
            List of quarantine records
        """
        return [
            record
            for record in self._records.values()
            if record.device_id == device_id
        ]

    def list_unreleased(self) -> list[QuarantineRecord]:
        """List all unreleased quarantine records.

        Returns:
            List of unreleased quarantine records
        """
        return [record for record in self._records.values() if not record.released]

    def count(self) -> int:
        """Get total number of quarantine records."""
        return len(self._records)

    def count_by_reason(self) -> dict[QuarantineReason, int]:
        """Get quarantine count by reason.

        Returns:
            Dictionary of quarantine reason to count
        """
        counts: dict[QuarantineReason, int] = {reason: 0 for reason in QuarantineReason}
        for record in self._records.values():
            counts[record.quarantine_reason] += 1
        return counts

    def _save_record(self, record: QuarantineRecord) -> None:
        """Save quarantine record to disk.

        Args:
            record: Quarantine record to save
        """
        import json

        record_path = self._quarantine_dir / f"{record.quarantine_id}.json"

        # Convert to dict for JSON serialization
        record_dict = {
            "quarantine_id": record.quarantine_id,
            "packet_id": record.packet_id,
            "device_id": record.device_id,
            "trust_label": record.trust_label.value,
            "routing_outcome": record.routing_outcome.value,
            "reason_codes": record.reason_codes,
            "quarantine_reason": record.quarantine_reason.value,
            "quarantined_at": record.quarantined_at.isoformat(),
            "packet_data": record.packet_data,
            "assessment": record.assessment.model_dump() if record.assessment else None,
            "released": record.released,
            "released_at": record.released_at.isoformat() if record.released_at else None,
            "release_reason": record.release_reason,
            "metadata": record.metadata,
        }

        with open(record_path, "w") as f:
            json.dump(record_dict, f, indent=2)

    def generate_report(self) -> dict[str, Any]:
        """Generate quarantine report.

        Returns:
            Dictionary with quarantine statistics
        """
        return {
            "total_quarantined": self.count(),
            "unreleased_count": len(self.list_unreleased()),
            "released_count": self.count() - len(self.list_unreleased()),
            "by_reason": {
                reason.value: count
                for reason, count in self.count_by_reason().items()
                if count > 0
            },
            "by_device": {
                device_id: len(self.list_by_device(device_id))
                for device_id in set(record.device_id for record in self._records.values())
            },
        }
