
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from shared.enums import DeviceLifecycleState


class DeviceKind(StrEnum):
    """Device type classification."""

    TYPE_A = "type_a"
    TYPE_B = "type_b"
    BACKUP = "backup"


@dataclass(frozen=True)
class DeviceCredential:
    """Device security credential."""

    credential_id: str
    secret: bytes
    signature_algorithm: str = "hmac-sha256"
    public_key_pem: bytes | str | None = None
    issued_at: datetime | None = None
    expires_at: datetime | None = None


@dataclass
class DeviceRecord:
    """Device registry record."""

    device_id: str
    device_kind: DeviceKind
    zone_id: str
    hub_id: str
    lifecycle_state: DeviceLifecycleState = DeviceLifecycleState.PROVISIONED
    credential: DeviceCredential | None = None
    firmware_hash: str | None = None
    config_hash: str | None = None
    approved_firmware: bool = False
    approved_config: bool = False
    registered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.device_id:
            raise ValueError("device_id cannot be empty")
        if not self.zone_id:
            raise ValueError("zone_id cannot be empty")
        if not self.hub_id:
            raise ValueError("hub_id cannot be empty")


class DeviceRegistry:
    """Device registry for C4 trust assessment."""

    def __init__(self) -> None:
        self._devices: dict[str, DeviceRecord] = {}

    def register(
        self,
        device_id: str,
        device_kind: DeviceKind,
        zone_id: str,
        hub_id: str,
        credential: DeviceCredential | None = None,
        firmware_hash: str | None = None,
        config_hash: str | None = None,
        approved_firmware: bool = False,
        approved_config: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> DeviceRecord:
        if device_id in self._devices:
            raise ValueError(f"Device {device_id} already registered")

        record = DeviceRecord(
            device_id=device_id,
            device_kind=device_kind,
            zone_id=zone_id,
            hub_id=hub_id,
            credential=credential,
            firmware_hash=firmware_hash,
            config_hash=config_hash,
            approved_firmware=approved_firmware,
            approved_config=approved_config,
            metadata=dict(metadata) if metadata is not None else {},
        )
        self._devices[device_id] = record
        return record

    def get(self, device_id: str) -> DeviceRecord | None:
        return self._devices.get(device_id)

    def count(self) -> int:
        return len(self._devices)

    def is_registered(self, device_id: str) -> bool:
        record = self.get(device_id)
        return record is not None and record.lifecycle_state not in {
            DeviceLifecycleState.REVOKED,
            DeviceLifecycleState.RETIRED,
        }

    def is_active(self, device_id: str) -> bool:
        record = self.get(device_id)
        return (
            record is not None
            and record.lifecycle_state == DeviceLifecycleState.ACTIVE
        )

    def get_credential(self, device_id: str) -> DeviceCredential | None:
        record = self.get(device_id)
        return record.credential if record is not None else None

    def list_devices(
        self,
        zone_id: str | None = None,
        lifecycle_state: DeviceLifecycleState | None = None,
        device_kind: DeviceKind | None = None,
    ) -> list[DeviceRecord]:
        records = list(self._devices.values())

        if zone_id is not None:
            records = [record for record in records if record.zone_id == zone_id]

        if lifecycle_state is not None:
            records = [
                record
                for record in records
                if record.lifecycle_state == lifecycle_state
            ]

        if device_kind is not None:
            records = [
                record for record in records if record.device_kind == device_kind
            ]

        return records

    def count_by_state(self) -> dict[DeviceLifecycleState, int]:
        counts = {state: 0 for state in DeviceLifecycleState}
        for record in self._devices.values():
            counts[record.lifecycle_state] += 1
        return counts

    def update_lifecycle_state(
        self,
        device_id: str,
        state: DeviceLifecycleState,
    ) -> DeviceRecord:
        record = self.get(device_id)
        if record is None:
            raise ValueError(f"Device {device_id} not found")

        record.lifecycle_state = state
        record.last_updated = datetime.now(UTC)
        return record

    def activate(self, device_id: str) -> DeviceRecord:
        record = self._require_device(device_id)
        if record.lifecycle_state not in {
            DeviceLifecycleState.PROVISIONED,
            DeviceLifecycleState.SUSPENDED,
        }:
            raise ValueError(
                f"Cannot activate device in state {record.lifecycle_state}"
            )
        return self.update_lifecycle_state(
            device_id, DeviceLifecycleState.ACTIVE
        )

    def suspend(self, device_id: str) -> DeviceRecord:
        record = self._require_device(device_id)
        if record.lifecycle_state not in {
            DeviceLifecycleState.PROVISIONED,
            DeviceLifecycleState.ACTIVE,
        }:
            raise ValueError(
                f"Cannot suspend device in state {record.lifecycle_state}"
            )
        return self.update_lifecycle_state(
            device_id, DeviceLifecycleState.SUSPENDED
        )

    def revoke(self, device_id: str) -> DeviceRecord:
        self._require_device(device_id)
        return self.update_lifecycle_state(
            device_id, DeviceLifecycleState.REVOKED
        )

    def retire(self, device_id: str) -> DeviceRecord:
        self._require_device(device_id)
        return self.update_lifecycle_state(
            device_id, DeviceLifecycleState.RETIRED
        )

    def update_credential(
        self,
        device_id: str,
        credential: DeviceCredential,
    ) -> DeviceRecord:
        record = self._require_device(device_id)
        record.credential = credential
        record.last_updated = datetime.now(UTC)
        return record

    def approve_firmware(
        self,
        device_id: str,
        firmware_hash: str,
    ) -> DeviceRecord:
        record = self._require_device(device_id)
        if not firmware_hash:
            raise ValueError("firmware_hash cannot be empty")
        record.firmware_hash = firmware_hash
        record.approved_firmware = True
        record.last_updated = datetime.now(UTC)
        return record

    def approve_config(
        self,
        device_id: str,
        config_hash: str,
    ) -> DeviceRecord:
        record = self._require_device(device_id)
        if not config_hash:
            raise ValueError("config_hash cannot be empty")
        record.config_hash = config_hash
        record.approved_config = True
        record.last_updated = datetime.now(UTC)
        return record

    def _require_device(self, device_id: str) -> DeviceRecord:
        record = self.get(device_id)
        if record is None:
            raise KeyError(f"Device {device_id} is not registered")
        return record


def create_test_registry() -> DeviceRegistry:
    registry = DeviceRegistry()

    test_devices = [
        ("GNX-DEVICE-001", DeviceKind.TYPE_A, "ZONE-001", "GNX-HUB-001"),
        ("Z1-A01", DeviceKind.TYPE_A, "Z1", "H001"),
        ("Z2-A01", DeviceKind.TYPE_A, "Z2", "H002"),
        ("Z1-B01", DeviceKind.TYPE_B, "Z1", "H001"),
        ("Z2-B01", DeviceKind.TYPE_B, "Z2", "H002"),
        ("Z1-BACKUP-01", DeviceKind.BACKUP, "Z1", "H001"),
        ("Z2-BACKUP-01", DeviceKind.BACKUP, "Z2", "H002"),
        ("Z3-A01", DeviceKind.TYPE_A, "Z3", "H003"),
        ("Z3-B01", DeviceKind.TYPE_B, "Z3", "H003"),
    ]

    for device_id, device_kind, zone_id, hub_id in test_devices:
        registry.register(
            device_id=device_id,
            device_kind=device_kind,
            zone_id=zone_id,
            hub_id=hub_id,
            credential=DeviceCredential(
                credential_id=f"cred-{device_id}",
                secret=b"test-device-secret",
            ),
            firmware_hash="approved-firmware-hash",
            config_hash="approved-config-hash",
            approved_firmware=True,
            approved_config=True,
        )
        registry.activate(device_id)

    return registry
