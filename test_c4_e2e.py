"""End-to-end test for Component 4 (C4)."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from datetime import UTC, datetime, timedelta

from components.c4_trust import (
    C4TrustService,
    DeviceCredential,
    DeviceKind,
    DeviceRegistry,
    QuarantineManager,
    QuarantineReason,
)
from shared.contracts import TelemetryPacket
from shared.contracts.telemetry import SecurityMetadata
from shared.enums import C4RoutingOutcome, C4TrustLabel, SourceOrigin

print("=" * 60)
print("C4 End-to-End Test")
print("=" * 60)

# Test 1: Device Registry
print("\n1. Testing Device Registry...")
registry = DeviceRegistry()
registry.register(
    "TEST-001",
    DeviceKind.TYPE_A,
    "Z1",
    "H001",
    DeviceCredential("cred-001", b"test-secret"),
)
registry.activate("TEST-001")
assert registry.is_active("TEST-001"), "Device should be active"
print("[OK] Device registry working")

# Test 2: Trust Service
print("\n2. Testing C4TrustService...")
service = C4TrustService(registry)

packet = TelemetryPacket(
    schema_version="1.0",
    packet_id="test-001",
    device_id="TEST-001",
    zone_id="Z1",
    boot_id="boot-001",
    sequence_no=1,
    observed_at=datetime.now(UTC) - timedelta(seconds=1),
    received_at=datetime.now(UTC),
    source_origin=SourceOrigin.SIMULATED,
    security=SecurityMetadata(
        credential_id="cred-001",
        integrity_present=True,
    ),
)

signature = service.sign_packet(packet, b"test-secret")
assessment = service.assess(packet, signature)

assert assessment.trust_label == C4TrustLabel.TRUSTED, "Packet should be trusted"
assert assessment.routing_outcome == C4RoutingOutcome.ACCEPT, "Packet should be accepted"
print("[OK] Trust service working")
print(f"  Trust Label: {assessment.trust_label}")
print(f"  Routing: {assessment.routing_outcome}")
print(f"  Reasons: {assessment.reason_codes}")

# Test 3: Quarantine Manager
print("\n3. Testing QuarantineManager...")
quarantine = QuarantineManager()
record = quarantine.quarantine(
    packet_id="test-002",
    device_id="TEST-001",
    trust_label=C4TrustLabel.SUSPICIOUS,
    routing_outcome=C4RoutingOutcome.QUARANTINE,
    reason_codes=["BEHAVIOURAL_ANOMALY"],
    quarantine_reason=QuarantineReason.BEHAVIOURAL_ANOMALY,
    packet_data={"rssi_dbm": -110},
)

assert not record.released, "Record should not be released initially"
print("[OK] Quarantine manager working")

# Test 4: Release from quarantine
quarantine.release(record.quarantine_id, "Review confirmed legitimate")
updated = quarantine.get(record.quarantine_id)
assert updated.released, "Record should be released"
print("[OK] Release mechanism working")

# Test 5: Generate report
report = quarantine.generate_report()
assert report["total_quarantined"] == 1, "Should have 1 quarantined record"
print("[OK] Report generation working")

print("\n" + "=" * 60)
print("All C4 End-to-End Tests Passed!")
print("=" * 60)
