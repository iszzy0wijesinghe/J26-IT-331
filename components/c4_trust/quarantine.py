from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic_core import to_jsonable_python

from shared.contracts import C4TrustAssessment
from shared.enums import C4RoutingOutcome, C4TrustLabel


class QuarantineReason(StrEnum):
    """Reasons for quarantining telemetry."""

    BEHAVIOURAL_ANOMALY = "BEHAVIOURAL_ANOMALY"
    WEAK_SIGNAL = "WEAK_SIGNAL"
    DEVICE_HEALTH_DEGRADED = "DEVICE_HEALTH_DEGRADED"
    CLOCK_DELAY = "CLOCK_DELAY"
    INTERVAL_ANOMALY = "INTERVAL_ANOMALY"
    RSSI_PROFILE_ANOMALY = "RSSI_PROFILE_ANOMALY"
    PATH_MISMATCH = "PATH_MISMATCH"
    SECURITY_FAILURE = "SECURITY_FAILURE"
    EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
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
    review_assessment: C4TrustAssessment | None = None
    reviewed_by: str | None = None
    released: bool = False
    released_at: datetime | None = None
    release_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class QuarantineManager:
    """Manage quarantined telemetry for audit and investigation.

    Quarantined packets are retained but not eligible for normal
    downstream environmental use until reviewed and released.
    """

    def __init__(
        self,
        quarantine_dir: Path | None = None,
        *,
        release_authorizer: Callable[[str], bool] | None = None,
    ) -> None:
        """Initialize quarantine manager.

        Args:
            quarantine_dir: Directory to store quarantine records
        """
        default_dir = Path(__file__).resolve().parents[2] / "quarantine" / "c4"
        self._quarantine_dir = Path(quarantine_dir) if quarantine_dir is not None else default_dir
        self._quarantine_dir.mkdir(parents=True, exist_ok=True)
        self._release_authorizer = release_authorizer
        self._records: dict[str, QuarantineRecord] = {}
        self._load_errors: dict[str, str] = {}
        self._load_existing_records()

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

        self._save_record(record)
        self._records[quarantine_id] = record

        return record

    def release(
        self,
        quarantine_id: str,
        release_reason: str,
        review_assessment: C4TrustAssessment | None = None,
        reviewer_id: str | None = None,
    ) -> QuarantineRecord:
        """Release a quarantined packet.

        Args:
            quarantine_id: Quarantine record ID
            release_reason: Reason for release
            review_assessment: Fresh C4 assessment proving the packet is now TRUSTED
            reviewer_id: Authenticated reviewer identity authorized by release_authorizer

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

        if not release_reason.strip():
            raise ValueError("release_reason must not be empty")
        if not reviewer_id or self._release_authorizer is None:
            raise ValueError("An authorized reviewer is required to release a packet")
        try:
            reviewer_authorized = self._release_authorizer(reviewer_id)
        except Exception:
            reviewer_authorized = False
        if not reviewer_authorized:
            raise ValueError("Reviewer is not authorized to release quarantine records")
        if review_assessment is None:
            raise ValueError("A fresh TRUSTED assessment is required to release a packet")
        if (
            review_assessment.packet_id != record.packet_id
            or review_assessment.device_id != record.device_id
        ):
            raise ValueError("Release assessment must match the quarantined packet and device")
        if (
            review_assessment.trust_label is not C4TrustLabel.TRUSTED
            or not review_assessment.mandatory_security_pass
            or review_assessment.routing_outcome is not C4RoutingOutcome.ACCEPT
        ):
            raise ValueError(
                "Release requires a fresh TRUSTED assessment with mandatory checks passed"
            )
        if review_assessment.generated_at <= record.quarantined_at:
            raise ValueError("Release assessment must be newer than the quarantine record")

        # Create updated record
        updated_record = QuarantineRecord(
            quarantine_id=record.quarantine_id,
            packet_id=record.packet_id,
            device_id=record.device_id,
            trust_label=C4TrustLabel.TRUSTED,
            routing_outcome=C4RoutingOutcome.ACCEPT,  # Released packets are accepted
            reason_codes=[*record.reason_codes, "RELEASE_REVALIDATED"],
            quarantine_reason=record.quarantine_reason,
            quarantined_at=record.quarantined_at,
            packet_data=record.packet_data,
            assessment=record.assessment,
            review_assessment=review_assessment,
            reviewed_by=reviewer_id,
            released=True,
            released_at=datetime.now(UTC),
            release_reason=release_reason,
            metadata=record.metadata,
        )

        self._save_record(updated_record, overwrite=True)
        self._records[quarantine_id] = updated_record

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

    @property
    def load_errors(self) -> dict[str, str]:
        """Return filenames that could not be loaded, without modifying them."""
        return self._load_errors.copy()

    def count_by_reason(self) -> dict[QuarantineReason, int]:
        """Get quarantine count by reason.

        Returns:
            Dictionary of quarantine reason to count
        """
        counts: dict[QuarantineReason, int] = {reason: 0 for reason in QuarantineReason}
        for record in self._records.values():
            counts[record.quarantine_reason] += 1
        return counts

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if value is None:
            return None
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("Persisted quarantine timestamps must be timezone-aware")
        return parsed

    @classmethod
    def _record_from_dict(cls, data: dict[str, Any]) -> QuarantineRecord:
        quarantined_at = cls._parse_datetime(data["quarantined_at"])
        if quarantined_at is None:
            raise ValueError("quarantined_at is required")
        assessment_data = data.get("assessment")
        review_data = data.get("review_assessment")
        return QuarantineRecord(
            quarantine_id=data["quarantine_id"],
            packet_id=data["packet_id"],
            device_id=data["device_id"],
            trust_label=C4TrustLabel(data["trust_label"]),
            routing_outcome=C4RoutingOutcome(data["routing_outcome"]),
            reason_codes=list(data["reason_codes"]),
            quarantine_reason=QuarantineReason(data["quarantine_reason"]),
            quarantined_at=quarantined_at,
            packet_data=dict(data.get("packet_data") or {}),
            assessment=(
                C4TrustAssessment.model_validate(assessment_data)
                if assessment_data is not None
                else None
            ),
            review_assessment=(
                C4TrustAssessment.model_validate(review_data)
                if review_data is not None
                else None
            ),
            reviewed_by=data.get("reviewed_by"),
            released=bool(data.get("released", False)),
            released_at=cls._parse_datetime(data.get("released_at")),
            release_reason=data.get("release_reason"),
            metadata=dict(data.get("metadata") or {}),
        )

    def _load_existing_records(self) -> None:
        for record_path in sorted(self._quarantine_dir.glob("*.json")):
            try:
                with record_path.open(encoding="utf-8") as file:
                    record = self._record_from_dict(json.load(file))
                if record_path.stem != record.quarantine_id:
                    raise ValueError("Filename does not match quarantine_id")
                self._records[record.quarantine_id] = record
            except (OSError, ValueError, TypeError, KeyError) as exc:
                self._load_errors[record_path.name] = type(exc).__name__

    def _save_record(self, record: QuarantineRecord, *, overwrite: bool = False) -> None:
        """Save quarantine record to disk.

        Args:
            record: Quarantine record to save
        """
        record_path = self._quarantine_dir / f"{record.quarantine_id}.json"
        if record_path.exists() and not overwrite:
            raise FileExistsError(f"Quarantine record already exists: {record_path}")

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
            "assessment": (
                record.assessment.model_dump(mode="json") if record.assessment else None
            ),
            "review_assessment": (
                record.review_assessment.model_dump(mode="json")
                if record.review_assessment
                else None
            ),
            "reviewed_by": record.reviewed_by,
            "released": record.released,
            "released_at": record.released_at.isoformat() if record.released_at else None,
            "release_reason": record.release_reason,
            "metadata": record.metadata,
        }

        json_ready_record = to_jsonable_python(record_dict)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self._quarantine_dir,
                suffix=".tmp",
                delete=False,
            ) as file:
                temporary_path = Path(file.name)
                json.dump(json_ready_record, file, indent=2, allow_nan=False)
                file.write("\n")
            os.replace(temporary_path, record_path)
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise

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
