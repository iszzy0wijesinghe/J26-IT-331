
import pytest

from components.c4_trust import (
    DeviceCredential,
    DeviceKind,
    DeviceRegistry,
    create_test_registry,
)
from shared.enums import DeviceLifecycleState


def test_registry_initialization() -> None:
    registry = DeviceRegistry()
    assert registry.count() == 0


def test_register_device() -> None:
    registry = DeviceRegistry()

    credential = DeviceCredential(
        credential_id="cred-001",
        secret=b"secret-001",
    )

    record = registry.register(
        device_id="Z1-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
        credential=credential,
    )

    assert record.device_id == "Z1-A01"
    assert record.device_kind == DeviceKind.TYPE_A
    assert record.zone_id == "Z1"
    assert record.hub_id == "H001"
    assert record.lifecycle_state == DeviceLifecycleState.PROVISIONED
    assert record.credential == credential
    assert registry.count() == 1


def test_register_duplicate_device_raises_error() -> None:
    registry = DeviceRegistry()

    registry.register(
        device_id="Z1-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
    )

    with pytest.raises(ValueError, match="already registered"):
        registry.register(
            device_id="Z1-A01",
            device_kind=DeviceKind.TYPE_A,
            zone_id="Z1",
            hub_id="H001",
        )


def test_register_with_empty_device_id_raises_error() -> None:
    registry = DeviceRegistry()

    with pytest.raises(ValueError, match="device_id cannot be empty"):
        registry.register(
            device_id="",
            device_kind=DeviceKind.TYPE_A,
            zone_id="Z1",
            hub_id="H001",
        )


def test_get_device() -> None:
    registry = DeviceRegistry()

    registry.register(
        device_id="Z1-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
    )

    record = registry.get("Z1-A01")
    assert record is not None
    assert record.device_id == "Z1-A01"

    # Non-existent device
    assert registry.get("UNKNOWN") is None


def test_update_lifecycle_state() -> None:
    registry = DeviceRegistry()

    registry.register(
        device_id="Z1-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
    )

    updated = registry.update_lifecycle_state(
        "Z1-A01",
        DeviceLifecycleState.ACTIVE,
    )

    assert updated.lifecycle_state == DeviceLifecycleState.ACTIVE
    assert registry.get("Z1-A01").lifecycle_state == DeviceLifecycleState.ACTIVE


def test_update_lifecycle_state_nonexistent_device_raises_error() -> None:
    registry = DeviceRegistry()

    with pytest.raises(ValueError, match="not found"):
        registry.update_lifecycle_state(
            "UNKNOWN",
            DeviceLifecycleState.ACTIVE,
        )


def test_activate_device() -> None:
    registry = DeviceRegistry()

    registry.register(
        device_id="Z1-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
    )

    updated = registry.activate("Z1-A01")

    assert updated.lifecycle_state == DeviceLifecycleState.ACTIVE


def test_suspend_device() -> None:
    registry = DeviceRegistry()

    registry.register(
        device_id="Z1-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
    )

    updated = registry.suspend("Z1-A01")

    assert updated.lifecycle_state == DeviceLifecycleState.SUSPENDED


def test_revoke_device() -> None:
    registry = DeviceRegistry()

    registry.register(
        device_id="Z1-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
    )

    updated = registry.revoke("Z1-A01")

    assert updated.lifecycle_state == DeviceLifecycleState.REVOKED


def test_retire_device() -> None:
    registry = DeviceRegistry()

    registry.register(
        device_id="Z1-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
    )

    updated = registry.retire("Z1-A01")

    assert updated.lifecycle_state == DeviceLifecycleState.RETIRED


def test_is_active() -> None:
    registry = DeviceRegistry()

    registry.register(
        device_id="Z1-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
    )

    assert not registry.is_active("Z1-A01")

    registry.activate("Z1-A01")
    assert registry.is_active("Z1-A01")

    registry.suspend("Z1-A01")
    assert not registry.is_active("Z1-A01")


def test_is_registered() -> None:
    registry = DeviceRegistry()

    registry.register(
        device_id="Z1-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
    )

    assert registry.is_registered("Z1-A01")

    registry.retire("Z1-A01")
    assert not registry.is_registered("Z1-A01")


def test_get_credential() -> None:
    registry = DeviceRegistry()

    credential = DeviceCredential(
        credential_id="cred-001",
        secret=b"secret-001",
    )

    registry.register(
        device_id="Z1-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
        credential=credential,
    )

    assert registry.get_credential("Z1-A01") == credential
    assert registry.get_credential("UNKNOWN") is None


def test_update_credential() -> None:
    registry = DeviceRegistry()

    old_credential = DeviceCredential(
        credential_id="cred-001",
        secret=b"secret-001",
    )

    registry.register(
        device_id="Z1-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
        credential=old_credential,
    )

    new_credential = DeviceCredential(
        credential_id="cred-002",
        secret=b"secret-002",
    )

    updated = registry.update_credential("Z1-A01", new_credential)

    assert updated.credential == new_credential
    assert registry.get_credential("Z1-A01") == new_credential


def test_approve_firmware() -> None:
    registry = DeviceRegistry()

    registry.register(
        device_id="Z1-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
    )

    updated = registry.approve_firmware("Z1-A01", "hash-123")

    assert updated.firmware_hash == "hash-123"
    assert updated.approved_firmware is True


def test_approve_config() -> None:
    registry = DeviceRegistry()

    registry.register(
        device_id="Z1-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
    )

    updated = registry.approve_config("Z1-A01", "config-hash-456")

    assert updated.config_hash == "config-hash-456"
    assert updated.approved_config is True


def test_list_devices() -> None:
    registry = DeviceRegistry()

    registry.register(
        device_id="Z1-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
    )
    registry.register(
        device_id="Z2-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z2",
        hub_id="H002",
    )
    registry.register(
        device_id="Z1-B01",
        device_kind=DeviceKind.TYPE_B,
        zone_id="Z1",
        hub_id="H001",
    )

    # List all
    all_devices = registry.list_devices()
    assert len(all_devices) == 3

    # Filter by zone
    z1_devices = registry.list_devices(zone_id="Z1")
    assert len(z1_devices) == 2

    # Filter by state
    registry.activate("Z1-A01")
    active_devices = registry.list_devices(lifecycle_state=DeviceLifecycleState.ACTIVE)
    assert len(active_devices) == 1


def test_count_by_state() -> None:
    registry = DeviceRegistry()

    registry.register(
        device_id="Z1-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z1",
        hub_id="H001",
    )
    registry.register(
        device_id="Z2-A01",
        device_kind=DeviceKind.TYPE_A,
        zone_id="Z2",
        hub_id="H002",
    )

    registry.activate("Z1-A01")
    registry.suspend("Z2-A01")

    counts = registry.count_by_state()

    assert counts[DeviceLifecycleState.ACTIVE] == 1
    assert counts[DeviceLifecycleState.SUSPENDED] == 1
    assert counts[DeviceLifecycleState.PROVISIONED] == 0


def test_create_test_registry() -> None:
    registry = create_test_registry()

    assert registry.count() == 9

    # All devices should be active
    active_devices = registry.list_devices(lifecycle_state=DeviceLifecycleState.ACTIVE)
    assert len(active_devices) == 9

    # Check specific device
    z1_a01 = registry.get("Z1-A01")
    assert z1_a01 is not None
    assert z1_a01.zone_id == "Z1"
    assert z1_a01.hub_id == "H001"
    assert z1_a01.credential is not None
    assert z1_a01.approved_firmware is True
    assert z1_a01.approved_config is True
