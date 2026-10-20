
"""DEMO ONLY — synthetic C4 credentials and evidence; not production security."""

from pathlib import Path

from components.c4_trust import (
    C4TrustService,
    DeviceCredential,
    DeviceKind,
    DeviceRegistry,
)
from components.c4_trust.pipeline import C4TelemetryGate
from components.c4_trust.quarantine import QuarantineManager
from shared.contracts.telemetry import SecurityMetadata, TransportMetadata
from shared.simulation.scheduled_telemetry import ScheduledTelemetry
from shared.simulation.topology import get_all_demo_pipes

HUB_BY_ZONE = {
    "ZONE_01": "H001",
    "ZONE_02": "H002",
}


def build_demo_c4_gate(
    quarantine_dir: str | Path = Path("quarantine/c4"),
) -> tuple[C4TelemetryGate, dict[str, DeviceCredential]]:
    """Build an isolated C4 gate for synthetic demonstration telemetry."""

    registry = DeviceRegistry()
    credentials: dict[str, DeviceCredential] = {}

    kind_by_role = {
        "TYPE_A": DeviceKind.TYPE_A,
        "TYPE_B": DeviceKind.TYPE_B,
        "BACKUP": DeviceKind.BACKUP,
    }

    for pipe in get_all_demo_pipes():
        credential = DeviceCredential(
            credential_id=f"DEMO-CRED-{pipe.device_id}",
            secret=f"demo-only-secret-{pipe.device_id}".encode(),
        )
        credentials[pipe.device_id] = credential

        registry.register(
            device_id=pipe.device_id,
            device_kind=kind_by_role[pipe.role.value],
            zone_id=pipe.zone_id,
            hub_id=HUB_BY_ZONE[pipe.zone_id],
            credential=credential,
        )
        registry.activate(pipe.device_id)

    def verify_demo_attestation(packet, device):
        return packet.security.attestation_evidence == {
            "demo_attestation": packet.device_id
        }

    def verify_demo_provenance(packet, device):
        return packet.security.provenance_evidence == {
            "demo_provenance": packet.packet_id
        }

    service = C4TrustService(
        registry,
        attestation_verifier=verify_demo_attestation,
        provenance_verifier=verify_demo_provenance,
        allow_deterministic_only=True,
        max_age_seconds=30,
        future_tolerance_seconds=5,
    )

    gate = C4TelemetryGate(
        trust_service=service,
        quarantine_manager=QuarantineManager(
            quarantine_dir=quarantine_dir,
        ),
    )

    return gate, credentials


def prepare_and_sign_demo_packet(
    item: ScheduledTelemetry,
    credentials: dict[str, DeviceCredential],
) -> tuple:
    """Prepare and sign synthetic telemetry for the isolated C4 demo."""

    packet = item.packet
    credential = credentials[packet.device_id]
    hub_id = HUB_BY_ZONE[packet.zone_id]

    prepared_packet = packet.model_copy(
        update={
            "transport": TransportMetadata(gateway_id=hub_id),
            "security": SecurityMetadata(
                credential_id=credential.credential_id,
                integrity_present=True,
                freshness_counter=packet.sequence_no,
                session_id=f"DEMO-SESSION-{packet.device_id}",
                attestation_evidence={
                    "demo_attestation": packet.device_id
                },
                provenance_evidence={
                    "demo_provenance": packet.packet_id
                },
            ),
        }
    )

    signature = C4TrustService.sign_packet(
        prepared_packet,
        credential.secret,
    )

    return prepared_packet, signature