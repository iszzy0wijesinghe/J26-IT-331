from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from components.c4_trust import (
    C4TrustService,
    DeviceCredential,
    DeviceKind,
    DeviceRegistry,
)
from components.c4_trust.integration import (
    create_c4_service_with_behavioral_ml,
)
from components.c4_trust.pipeline import C4TelemetryGate
from components.c4_trust.quarantine import QuarantineManager
from shared.contracts.telemetry import SecurityMetadata
from shared.simulation.scheduled_telemetry import (
    ScheduledTelemetryConfig,
    generate_scheduled_demo_telemetry,
)
from shared.simulation.topology import get_all_demo_pipes

MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "c4"
    / "models"
    / "random_forest_corrected.joblib"
)

HUB_BY_ZONE = {
    "ZONE_01": "H001",
    "ZONE_02": "H002",
}

KIND_BY_ROLE = {
    "TYPE_A": DeviceKind.TYPE_A,
    "TYPE_B": DeviceKind.TYPE_B,
    "BACKUP": DeviceKind.BACKUP,
}

SUPPORTED_SCENARIOS = {
    "valid",
    "valid_hmac",
    "tampered",
    "tampered_hmac",
    "replay",
    "replay_hmac",
    "valid_ecdsa",
    "tampered_ecdsa",
    "unverifiable_ecdsa",
    "fallback_rejection",
}


class C4DemoBackend:
    """Isolated dashboard demo using the actual C4 trust and ML pipeline.

    Supports HMAC-SHA256 and ECDSA-SHA256 signature verification demonstrations.
    Temporary EC keys are generated safely in memory and are never exposed.
    """

    def __init__(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory(
            prefix="geonex-c4-dashboard-"
        )
        self._quarantine_directory = (
            Path(self._temporary_directory.name) / "quarantine"
        )
        # Generate temporary EC key pair in memory (private key kept in memory only)
        self._ec_private_key = ec.generate_private_key(ec.SECP256R1())
        self._ec_public_pem = self._ec_private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self._registry = DeviceRegistry()
        self._credentials: dict[str, DeviceCredential] = {}
        self._ecdsa_credentials: dict[str, DeviceCredential] = {}
        self._gate = self._build_gate()

    def _build_gate(self) -> C4TelemetryGate:
        for pipe in get_all_demo_pipes():
            hmac_credential = DeviceCredential(
                credential_id=f"DEMO-CRED-{pipe.device_id}",
                secret=f"dashboard-demo-only-{pipe.device_id}".encode(),
                signature_algorithm="hmac-sha256",
            )
            ecdsa_credential = DeviceCredential(
                credential_id=f"DEMO-ECDSA-{pipe.device_id}",
                secret=f"dashboard-demo-only-{pipe.device_id}".encode(),
                signature_algorithm="ecdsa-sha256",
                public_key_pem=self._ec_public_pem,
            )
            self._credentials[pipe.device_id] = hmac_credential
            self._ecdsa_credentials[pipe.device_id] = ecdsa_credential

            self._registry.register(
                device_id=pipe.device_id,
                device_kind=KIND_BY_ROLE[pipe.role.value],
                zone_id=pipe.zone_id,
                hub_id=HUB_BY_ZONE[pipe.zone_id],
                credential=hmac_credential,
            )
            self._registry.activate(pipe.device_id)

        # Demonstration-only evidence verifiers (clearly labeled as simulation)
        def verify_attestation(packet: Any, device: Any) -> bool:
            return packet.security.attestation_evidence == {
                "test_attestation": packet.device_id
            }

        def verify_provenance(packet: Any, device: Any) -> bool:
            return packet.security.provenance_evidence == {
                "test_provenance": packet.packet_id
            }

        service = create_c4_service_with_behavioral_ml(
            registry=self._registry,
            model_path=MODEL_PATH,
            max_age_seconds=30,
            future_tolerance_seconds=5,
            attestation_verifier=verify_attestation,
            provenance_verifier=verify_provenance,
        )

        return C4TelemetryGate(
            trust_service=service,
            quarantine_manager=QuarantineManager(
                quarantine_dir=self._quarantine_directory
            ),
        )

    def _prepare_packet(
        self,
        item: Any,
        credential: DeviceCredential,
        scenario_tag: str | None = None,
    ) -> Any:
        packet = item.packet
        hub_id = HUB_BY_ZONE[packet.zone_id]

        packet_id = (
            f"{packet.packet_id}_{scenario_tag}"
            if scenario_tag
            else packet.packet_id
        )
        boot_id = (
            f"{packet.boot_id}_{scenario_tag}"
            if scenario_tag and packet.boot_id
            else packet.boot_id
        )

        transport = packet.transport.model_copy(
            update={"gateway_id": hub_id}
        )
        security = SecurityMetadata(
            credential_id=credential.credential_id,
            integrity_present=True,
            freshness_counter=packet.sequence_no,
            session_id=f"DEMO-SESSION-{packet.device_id}",
            attestation_evidence={
                "test_attestation": packet.device_id
            },
            provenance_evidence={
                "test_provenance": packet_id
            },
        )

        return packet.model_copy(
            update={
                "packet_id": packet_id,
                "boot_id": boot_id,
                "transport": transport,
                "security": security,
            }
        )

    @staticmethod
    def _result_row(
        result: Any,
        scenario: str,
        signature_algorithm: str,
    ) -> dict[str, Any]:
        assessment = result.assessment
        reason_codes = assessment.reason_codes

        if "INTEGRITY_VALID" in reason_codes:
            sig_verification = "VALID"
        elif "INTEGRITY_INVALID" in reason_codes:
            sig_verification = "INVALID"
        elif any(
            code in reason_codes
            for code in ("SIGNATURE_UNVERIFIABLE", "SIGNATURE_MISSING")
        ):
            sig_verification = "UNVERIFIABLE"
        else:
            sig_verification = "NOT_EVALUATED"

        return {
            "scenario": scenario,
            "signature_algorithm": signature_algorithm,
            "packet_id": assessment.packet_id,
            "device_id": assessment.device_id,
            "signature_verification": sig_verification,
            "mandatory_security_pass": assessment.mandatory_security_pass,
            "trust_label": assessment.trust_label.value,
            "routing_outcome": (
                assessment.routing_outcome.value
                if assessment.routing_outcome
                else "UNKNOWN"
            ),
            "behavioural_score": assessment.behavioural_score,
            "eligible_for_c1": result.eligible_for_c1,
            "reason_codes": assessment.reason_codes,
            "quarantined": result.quarantine_record is not None,
        }

    def run_simulation(self, scenario: str = "valid") -> list[dict[str, Any]]:
        if scenario not in SUPPORTED_SCENARIOS:
            raise ValueError(f"Unsupported scenario: {scenario}")

        items = generate_scheduled_demo_telemetry(
            ScheduledTelemetryConfig(seed=20261010)
        )
        if not items:
            raise RuntimeError("The telemetry simulator returned no packets.")

        rows: list[dict[str, Any]] = []

        if scenario in {"valid", "valid_hmac"}:
            for item in items:
                hmac_cred = self._credentials[item.packet.device_id]
                self._registry.update_credential(item.packet.device_id, hmac_cred)
                packet = self._prepare_packet(item, hmac_cred)
                signature = C4TrustService.sign_packet(packet, hmac_cred.secret)
                result = self._gate.process(
                    packet,
                    signature,
                    now=packet.observed_at,
                )
                rows.append(
                    self._result_row(result, "Valid Telemetry (HMAC)", "hmac-sha256")
                )

        elif scenario in {"tampered", "tampered_hmac"}:
            item = items[0]
            hmac_cred = self._credentials[item.packet.device_id]
            self._registry.update_credential(item.packet.device_id, hmac_cred)
            packet = self._prepare_packet(item, hmac_cred, "tampered")
            signature = C4TrustService.sign_packet(packet, hmac_cred.secret)
            tampered_packet = packet.model_copy(
                update={"message_type": "TAMPERED_TELEMETRY"}
            )
            result = self._gate.process(
                tampered_packet,
                signature,
                now=tampered_packet.observed_at,
            )
            rows.append(
                self._result_row(result, "Tampered Telemetry (HMAC)", "hmac-sha256")
            )

        elif scenario in {"replay", "replay_hmac"}:
            item = items[0]
            hmac_cred = self._credentials[item.packet.device_id]
            self._registry.update_credential(item.packet.device_id, hmac_cred)
            packet = self._prepare_packet(item, hmac_cred, "replay")
            signature = C4TrustService.sign_packet(packet, hmac_cred.secret)
            first = self._gate.process(
                packet,
                signature,
                now=packet.observed_at,
            )
            second = self._gate.process(
                packet,
                signature,
                now=packet.observed_at,
            )
            rows.extend(
                [
                    self._result_row(
                        first,
                        "Replay Attack - Initial (HMAC)",
                        "hmac-sha256",
                    ),
                    self._result_row(
                        second,
                        "Replay Attack - Duplicate (HMAC)",
                        "hmac-sha256",
                    ),
                ]
            )

        elif scenario == "valid_ecdsa":
            item = items[0]
            ecdsa_cred = self._ecdsa_credentials[item.packet.device_id]
            self._registry.update_credential(item.packet.device_id, ecdsa_cred)
            packet = self._prepare_packet(item, ecdsa_cred, "ecdsa_valid")
            signature = C4TrustService.sign_packet_ecdsa(
                packet,
                self._ec_private_key,
            )
            result = self._gate.process(
                packet,
                signature,
                now=packet.observed_at,
            )
            rows.append(
                self._result_row(
                    result,
                    "Valid Telemetry (ECDSA)",
                    "ecdsa-sha256",
                )
            )

        elif scenario == "tampered_ecdsa":
            item = items[0]
            ecdsa_cred = self._ecdsa_credentials[item.packet.device_id]
            self._registry.update_credential(item.packet.device_id, ecdsa_cred)
            packet = self._prepare_packet(item, ecdsa_cred, "ecdsa_tampered")
            signature = C4TrustService.sign_packet_ecdsa(
                packet,
                self._ec_private_key,
            )
            tampered_packet = packet.model_copy(
                update={"zone_id": "ZONE_02"}
            )
            result = self._gate.process(
                tampered_packet,
                signature,
                now=tampered_packet.observed_at,
            )
            rows.append(
                self._result_row(
                    result,
                    "Tampered Telemetry (ECDSA)",
                    "ecdsa-sha256",
                )
            )

        elif scenario == "unverifiable_ecdsa":
            item = items[0]
            unverifiable_cred = DeviceCredential(
                credential_id=f"DEMO-UNVERIFIABLE-{item.packet.device_id}",
                secret=b"dashboard-demo-only",
                signature_algorithm="ecdsa-sha256",
                public_key_pem=None,
            )
            self._registry.update_credential(item.packet.device_id, unverifiable_cred)
            packet = self._prepare_packet(item, unverifiable_cred, "ecdsa_unverifiable")
            signature = C4TrustService.sign_packet_ecdsa(
                packet,
                self._ec_private_key,
            )
            result = self._gate.process(
                packet,
                signature,
                now=packet.observed_at,
            )
            rows.append(
                self._result_row(
                    result,
                    "Unavailable Public Key (ECDSA)",
                    "ecdsa-sha256",
                )
            )

        elif scenario == "fallback_rejection":
            item = items[0]
            ecdsa_cred = self._ecdsa_credentials[item.packet.device_id]
            self._registry.update_credential(item.packet.device_id, ecdsa_cred)
            packet = self._prepare_packet(item, ecdsa_cred, "ecdsa_fallback")
            # Present an HMAC signature for an ECDSA-configured device
            hmac_signature = C4TrustService.sign_packet(
                packet,
                ecdsa_cred.secret,
            )
            result = self._gate.process(
                packet,
                hmac_signature,
                now=packet.observed_at,
            )
            rows.append(
                self._result_row(
                    result,
                    "Fallback Rejection (ECDSA with HMAC signature)",
                    "ecdsa-sha256",
                )
            )

        return rows

    def close(self) -> None:
        self._temporary_directory.cleanup()
