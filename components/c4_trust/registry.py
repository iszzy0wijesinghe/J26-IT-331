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
    # Additional credential metadata can be added here
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
        """Validate device record."""
        if not self.device_id:
            raise ValueError("device_id cannot be empty")
        if not self.zone_id:
            raise ValueError("zone_id cannot be empty")
        if not self.hub_id:
            raise ValueError("hub_id cannot be empty")


class DeviceRegistry:
    """Device registry for C4 trust assessment.

    Maintains device lifecycle state, credentials, and approval status.
    """

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
        """Register a new device in the registry.

        Args:
            device_id: Unique device identifier
            device_kind: Device type (type_a, type_b, backup)
            zone_id: Zone where device is registered
            hub_id: Hub where device is registered
            credential: Device security credential
            firmware_hash: Firmware hash for approval checking
            config_hash: Config hash for approval checking
            approved_firmware: Whether firmware is approved
            approved_config: Whether config is approved
            metadata: Additional device metadata

        Returns:
            DeviceRecord: The registered device record

        Raises:
            ValueError: If device_id already exists
        """
        if device_id in self._devices:
            raise ValueError(f"Device {device_id} already registered")

        record = DeviceRecord(
            device_id=device_id,
            device_kind=device_kind,
            zone_id=zone_id,
            hub_id=hub_id,
            lifecycle_state=DeviceLifecycleState.PROVISIONED,
            credential=credential,
            firmware_hash=firmware_hash,
            config_hash=config_hash,
            approved_firmware=approved_firmware,
            approved_config=approved_config,
            metadata=metadata or {},
        )

        self._devices[device_id] = record
        return record

    def get(self, device_id: str) -> DeviceRecord | None:
        """Get device record by ID.

        Args:
            device_id: Device identifier

        Returns:
            DeviceRecord if found, None otherwise
        """
        return self._devices.get(device_id)

    def update_lifecycle_state(
        self,
        device_id: str,
        new_state: DeviceLifecycleState,
    ) -> DeviceRecord:
        """Update device lifecycle state.

        Args:
            device_id: Device identifier
            new_state: New lifecycle state

        Returns:
            DeviceRecord: Updated device record

        Raises:
            ValueError: If device not found
        """
        record = self.get(device_id)
        if record is None:
            raise ValueError(f"Device {device_id} not found")

        # Create updated record (dataclass is not frozen)
        updated_record = DeviceRecord(
            device_id=record.device_id,
            device_kind=record.device_kind,
            zone_id=record.zone_id,
            hub_id=record.hub_id,
            lifecycle_state=new_state,
            credential=record.credential,
            firmware_hash=record.firmware_hash,
            config_hash=record.config_hash,
            approved_firmware=record.approved_firmware,
            approved_config=record.approved_config,
            registered_at=record.registered_at,
            last_updated=datetime.now(UTC),
            metadata=record.metadata.copy(),
        )

        self._devices[device_id] = updated_record
        return updated_record

    def update_credential(
        self,
        device_id: str,
        credential: DeviceCredential,
    ) -> DeviceRecord:
        """Update device credential.

        Args:
            device_id: Device identifier
            credential: New device credential

        Returns:
            DeviceRecord: Updated device record

        Raises:
            ValueError: If device not found
        """
        record = self.get(device_id)
        if record is None:
            raise ValueError(f"Device {device_id} not found")

        updated_record = DeviceRecord(
            device_id=record.device_id,
            device_kind=record.device_kind,
            zone_id=record.zone_id,
            hub_id=record.hub_id,
            lifecycle_state=record.lifecycle_state,
            credential=credential,
            firmware_hash=record.firmware_hash,
            config_hash=record.config_hash,
            approved_firmware=record.approved_firmware,
            approved_config=record.approved_config,
            registered_at=record.registered_at,
            last_updated=datetime.now(UTC),
            metadata=record.metadata.copy(),
        )

        self._devices[device_id] = updated_record
        return updated_record

    def approve_firmware(
        self,
        device_id: str,
        firmware_hash: str,
    ) -> DeviceRecord:
        """Approve firmware for device.

        Args:
            device_id: Device identifier
            firmware_hash: Approved firmware hash

        Returns:
            DeviceRecord: Updated device record

        Raises:
            ValueError: If device not found
        """
        record = self.get(device_id)
        if record is None:
            raise ValueError(f"Device {device_id} not found")

        updated_record = DeviceRecord(
            device_id=record.device_id,
            device_kind=record.device_kind,
            zone_id=record.zone_id,
            hub_id=record.hub_id,
            lifecycle_state=record.lifecycle_state,
            credential=record.credential,
            firmware_hash=firmware_hash,
            config_hash=record.config_hash,
            approved_firmware=True,
            approved_config=record.approved_config,
            registered_at=record.registered_at,
            last_updated=datetime.now(UTC),
            metadata=record.metadata.copy(),
        )

        self._devices[device_id] = updated_record
        return updated_record

    def approve_config(
        self,
        device_id: str,
        config_hash: str,
    ) -> DeviceRecord:
        """Approve configuration for device.

        Args:
            device_id: Device identifier
            config_hash: Approved config hash

        Returns:
            DeviceRecord: Updated device record

        Raises:
            ValueError: If device not found
        """
        record = self.get(device_id)
        if record is None:
            raise ValueError(f"Device {device_id} not found")

        updated_record = DeviceRecord(
            device_id=record.device_id,
            device_kind=record.device_kind,
            zone_id=record.zone_id,
            hub_id=record.hub_id,
            lifecycle_state=record.lifecycle_state,
            credential=record.credential,
            firmware_hash=record.firmware_hash,
            config_hash=config_hash,
            approved_firmware=record.approved_firmware,
            approved_config=True,
            registered_at=record.registered_at,
            last_updated=datetime.now(UTC),
            metadata=record.metadata.copy(),
        )

        self._devices[device_id] = updated_record
        return updated_record

    def revoke(self, device_id: str) -> DeviceRecord:
        """Revoke device (set lifecycle state to REVOKED).

        Args:
            device_id: Device identifier

        Returns:
            DeviceRecord: Updated device record

        Raises:
            ValueError: If device not found
        """
        return self.update_lifecycle_state(device_id, DeviceLifecycleState.REVOKED)

    def suspend(self, device_id: str) -> DeviceRecord:
        """Suspend device (set lifecycle state to SUSPENDED).

        Args:
            device_id: Device identifier

        Returns:
            DeviceRecord: Updated device record

        Raises:
            ValueError: If device not found
        """
        return self.update_lifecycle_state(device_id, DeviceLifecycleState.SUSPENDED)

    def activate(self, device_id: str) -> DeviceRecord:
        """Activate device (set lifecycle state to ACTIVE).

        Args:
            device_id: Device identifier

        Returns:
            DeviceRecord: Updated device record

        Raises:
            ValueError: If device not found
        """
        return self.update_lifecycle_state(device_id, DeviceLifecycleState.ACTIVE)

    def retire(self, device_id: str) -> DeviceRecord:
        """Retire device (set lifecycle state to RETIRED).

        Args:
            device_id: Device identifier

        Returns:
            DeviceRecord: Updated device record

        Raises:
            ValueError: If device not found
        """
        return self.update_lifecycle_state(device_id, DeviceLifecycleState.RETIRED)

    def is_active(self, device_id: str) -> bool:
        """Check if device is in ACTIVE state.

        Args:
            device_id: Device identifier

        Returns:
            True if device is ACTIVE, False otherwise
        """
        record = self.get(device_id)
        return record is not None and record.lifecycle_state == DeviceLifecycleState.ACTIVE

    def is_registered(self, device_id: str) -> bool:
        """Check if device is registered (any state except RETIRED).

        Args:
            device_id: Device identifier

        Returns:
            True if device is registered, False otherwise
        """
        record = self.get(device_id)
        return record is not None and record.lifecycle_state != DeviceLifecycleState.RETIRED

    def get_credential(self, device_id: str) -> DeviceCredential | None:
        """Get device credential.

        Args:
            device_id: Device identifier

        Returns:
            DeviceCredential if found, None otherwise
        """
        record = self.get(device_id)
        return record.credential if record else None

    def list_devices(
        self,
        lifecycle_state: DeviceLifecycleState | None = None,
        zone_id: str | None = None,
    ) -> list[DeviceRecord]:
        """List devices with optional filters.

        Args:
            lifecycle_state: Filter by lifecycle state
            zone_id: Filter by zone

        Returns:
            List of device records matching filters
        """
        devices = list(self._devices.values())

        if lifecycle_state is not None:
            devices = [d for d in devices if d.lifecycle_state == lifecycle_state]

        if zone_id is not None:
            devices = [d for d in devices if d.zone_id == zone_id]

        return devices

    def count(self) -> int:
        """Get total number of registered devices."""
        return len(self._devices)

    def count_by_state(self) -> dict[DeviceLifecycleState, int]:
        """Get device count by lifecycle state."""
        counts: dict[DeviceLifecycleState, int] = {
            state: 0 for state in DeviceLifecycleState
        }
        for record in self._devices.values():
            counts[record.lifecycle_state] += 1
        return counts


def create_test_registry() -> DeviceRegistry:
    """Create a test registry with sample devices.

    Returns:
        DeviceRegistry with sample devices for testing
    """
    registry = DeviceRegistry()

    # Register sample devices
    sample_devices = [
        ("Z1-A01", DeviceKind.TYPE_A, "Z1", "H001"),
        ("Z1-B01", DeviceKind.TYPE_B, "Z1", "H001"),
        ("Z1-BK01", DeviceKind.BACKUP, "Z1", "H001"),
        ("Z2-A01", DeviceKind.TYPE_A, "Z2", "H002"),
        ("Z2-B01", DeviceKind.TYPE_B, "Z2", "H002"),
        ("Z2-BK01", DeviceKind.BACKUP, "Z2", "H002"),
        ("Z3-A01", DeviceKind.TYPE_A, "Z3", "H003"),
        ("Z3-B01", DeviceKind.TYPE_B, "Z3", "H003"),
        ("Z3-BK01", DeviceKind.BACKUP, "Z3", "H003"),
    ]

    for device_id, kind, zone, hub in sample_devices:
        registry.register(
            device_id=device_id,
            device_kind=kind,
            zone_id=zone,
            hub_id=hub,
            credential=DeviceCredential(
                credential_id=f"cred-{device_id}",
                secret=f"secret-{device_id}".encode(),
            ),
            approved_firmware=True,
            approved_config=True,
        )
        # Activate device
        registry.activate(device_id)

    return registry
