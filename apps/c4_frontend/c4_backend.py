from __future__ import annotations

import tempfile
from datetime import timedelta
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from components.c4_trust import (
    C4TrustService,
    DeviceCredential,
    DeviceKind,
    DeviceRegistry,
    create_ca,
    create_device_certificate,
)
from components.c4_trust.integration import (
    create_c4_service_with_behavioral_ml,
)
from components.c4_trust.pipeline import C4TelemetryGate
from components.c4_trust.quarantine import QuarantineManager
from shared.contracts.telemetry import SecurityMetadata, TelemetryPacket
from shared.enums import DeviceLifecycleState
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

DEMO_SIMULATION_CONFIG = ScheduledTelemetryConfig(seed=20261010)
DEMO_PKI_ISSUED_AT = DEMO_SIMULATION_CONFIG.start_time - timedelta(hours=1)

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
    "expired_x509",
    "untrusted_ca_x509",
    "mismatched_identity_x509",
    "revoked_x509",
    "unverifiable_ecdsa",
    "fallback_rejection",
}


class C4DemoBackend:
    """Dashboard simulation backend using the real C4 trust and ML pipeline.

    Uses a local test CA and test X.509 certificates for demonstration.
    Private keys are generated safely in memory and are used only for signing
    in the simulation sender. Public keys and certificates are validated by
    the C4 gate against the trusted test CA.
    """

    def __init__(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory(
            prefix="geonex-c4-dashboard-"
        )
        self._quarantine_directory = (
            Path(self._temporary_directory.name) / "quarantine"
        )

        self._ca_key, self._ca_cert, self._ca_pem = create_ca(
            "GeoNex Simulation Root CA",
            issued_at=DEMO_PKI_ISSUED_AT,
        )
        self._device_keys: dict[str, ec.EllipticCurvePrivateKey] = {}
        self._device_certs: dict[str, Any] = {}
        self._device_cert_pems: dict[str, bytes] = {}

        self._registry = DeviceRegistry()
        self._credentials: dict[str, DeviceCredential] = {}
        self._ecdsa_credentials: dict[str, DeviceCredential] = {}
        self._gate = self._build_gate()

    def _build_gate(self) -> C4TelemetryGate:
        for pipe in get_all_demo_pipes():
            pipe_key = ec.generate_private_key(ec.SECP256R1())
            self._device_keys[pipe.device_id] = pipe_key

            _, pipe_cert, pipe_cert_pem = create_device_certificate(
                pipe.device_id,
                self._ca_cert,
                self._ca_key,
                private_key=pipe_key,
                issued_at=DEMO_PKI_ISSUED_AT,
            )
            self._device_certs[pipe.device_id] = pipe_cert
            self._device_cert_pems[pipe.device_id] = pipe_cert_pem

            hmac_credential = DeviceCredential(
                credential_id=f"DEMO-CRED-{pipe.device_id}",
                secret=f"dashboard-demo-only-{pipe.device_id}".encode(),
                signature_algorithm="hmac-sha256",
            )
            ecdsa_credential = DeviceCredential(
                credential_id=f"DEMO-ECDSA-{pipe.device_id}",
                secret=f"dashboard-demo-only-{pipe.device_id}".encode(),
                signature_algorithm="ecdsa-sha256",
                certificate_pem=pipe_cert_pem,
                public_key_pem=pipe_key.public_key().public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                ),
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
            trusted_ca_certificates=[self._ca_cert],
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
        custom_cert_pem: str | None = None,
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

        cert_str = custom_cert_pem
        if cert_str is None and credential.certificate_pem is not None:
            cert_pem = credential.certificate_pem
            cert_str = cert_pem.decode("utf-8") if isinstance(cert_pem, bytes) else cert_pem

        transport = packet.transport.model_copy(
            update={"gateway_id": hub_id}
        )
        security = SecurityMetadata(
            credential_id=credential.credential_id,
            integrity_present=True,
            freshness_counter=packet.sequence_no,
            session_id=f"DEMO-SESSION-{packet.device_id}",
            certificate_pem=cert_str,
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
    def _measurement_rows(packet: TelemetryPacket) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for measurement in packet.measurements:
            rows.append(
                {
                    "sensor_instance_id": measurement.sensor_instance_id,
                    "sensor_type": measurement.sensor_type,
                    "value": measurement.value,
                    "raw_value": measurement.raw_value,
                    "unit": measurement.unit,
                }
            )
        return rows

    @staticmethod
    def _result_row(
        result: Any,
        scenario: str,
        signature_algorithm: str,
        packet: TelemetryPacket,
    ) -> dict[str, Any]:
        assessment = result.assessment
        reason_codes = assessment.reason_codes
        quarantine = result.quarantine_record

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

        ml_ran = any(
            code.startswith("BEHAVIOURAL_") for code in reason_codes
        ) or assessment.behavioural_score is not None

        return {
            "scenario": scenario,
            "signature_algorithm": signature_algorithm,
            "packet_id": assessment.packet_id,
            "device_id": assessment.device_id,
            "assessment_id": assessment.assessment_id,
            "data_origin": "FRONTEND_SIMULATION",
            "source_origin": packet.source_origin.value,
            "origin_explanation": (
                "Synthetic demonstration packet from "
                "generate_scheduled_demo_telemetry(). Not live ESP32, "
                "LoRa, CSV, or database telemetry."
            ),
            "zone_id": packet.zone_id,
            "hub_id": packet.transport.gateway_id,
            "sequence_no": packet.sequence_no,
            "boot_id": packet.boot_id,
            "message_type": packet.message_type,
            "observed_at": packet.observed_at.isoformat(),
            "received_at": packet.received_at.isoformat(),
            "tx_interval_s": packet.tx_interval_s,
            "freshness_status": packet.freshness_status,
            "rssi_dbm": packet.transport.rssi_dbm,
            "snr_db": packet.transport.snr_db,
            "retry_count": packet.transport.retry_count,
            "battery_pct": packet.device_health.battery_pct,
            "battery_voltage": packet.device_health.battery_voltage,
            "sensor_fault_flag": packet.device_health.sensor_fault_flag,
            "measurements": C4DemoBackend._measurement_rows(packet),
            "credential_id": packet.security.credential_id,
            "certificate_present": packet.security.certificate_pem is not None,
            "signature_verification": sig_verification,
            "mandatory_security_pass": assessment.mandatory_security_pass,
            "ml_ran": ml_ran,
            "trust_label": assessment.trust_label.value,
            "routing_outcome": (
                assessment.routing_outcome.value
                if assessment.routing_outcome
                else "UNKNOWN"
            ),
            "behavioural_score": assessment.behavioural_score,
            "trust_score": assessment.trust_score,
            "eligible_for_c1": result.eligible_for_c1,
            "reason_codes": assessment.reason_codes,
            "quarantined": quarantine is not None,
            "quarantine_id": (
                quarantine.quarantine_id if quarantine is not None else None
            ),
            "storage": "streamlit_session_state",
            "persisted_to_database": False,
            "storage_explanation": (
                "This assessment is kept in Streamlit session_state until "
                "the browser session is cleared. Dashboard quarantine files "
                "are written to a temporary directory and deleted when the "
                "scenario backend closes. They are not written to PostgreSQL."
            ),
        }

    def list_safe_devices(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for record in self._registry.list_devices():
            credential = record.credential
            rows.append(
                {
                    "device_id": record.device_id,
                    "device_kind": record.device_kind.value,
                    "zone_id": record.zone_id,
                    "hub_id": record.hub_id,
                    "lifecycle_state": record.lifecycle_state.value,
                    "credential_id": (
                        credential.credential_id if credential else None
                    ),
                    "signature_algorithm": (
                        credential.signature_algorithm if credential else None
                    ),
                    "has_certificate": bool(
                        credential and credential.certificate_pem
                    ),
                    "has_public_key": bool(
                        credential and credential.public_key_pem
                    ),
                    "secret_material_present": bool(
                        credential and credential.secret
                    ),
                }
            )
        return rows

    @staticmethod
    def system_diagnostics() -> dict[str, Any]:
        model_exists = MODEL_PATH.exists()
        database: dict[str, Any] = {
            "configured": True,
            "reachable": False,
            "host": None,
            "port": None,
            "name": None,
            "user": None,
            "telemetry_packets": None,
            "error": None,
        }
        try:
            from sqlalchemy import func, select, text

            from database.models import TelemetryPacketRecord
            from database.session import create_database_engine
            from shared.config.settings import get_settings

            settings = get_settings()
            database.update(
                {
                    "host": settings.db_host,
                    "port": settings.db_port,
                    "name": settings.db_name,
                    "user": settings.db_user,
                }
            )
            engine = create_database_engine(settings)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                packet_count = connection.execute(
                    select(func.count()).select_from(TelemetryPacketRecord)
                ).scalar_one()
            database["reachable"] = True
            database["telemetry_packets"] = int(packet_count)
            engine.dispose()
        except Exception as exc:
            database["error"] = f"{type(exc).__name__}: {exc}"

        return {
            "model_path": str(MODEL_PATH),
            "model_available": model_exists,
            "holdout_path": str(
                Path(__file__).resolve().parents[2]
                / "experiments"
                / "c4"
                / "data"
                / "C4_test_corrected.csv"
            ),
            "database": database,
        }

    def run_simulation(self, scenario: str = "valid") -> list[dict[str, Any]]:
        if scenario not in SUPPORTED_SCENARIOS:
            raise ValueError(f"Unsupported scenario: {scenario}")

        items = generate_scheduled_demo_telemetry(DEMO_SIMULATION_CONFIG)
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
                    self._result_row(
                        result,
                        "Valid Telemetry (HMAC)",
                        "hmac-sha256",
                        packet,
                    )
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
                self._result_row(
                    result,
                    "Tampered Telemetry (HMAC)",
                    "hmac-sha256",
                    tampered_packet,
                )
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
                        packet,
                    ),
                    self._result_row(
                        second,
                        "Replay Attack - Duplicate (HMAC)",
                        "hmac-sha256",
                        packet,
                    ),
                ]
            )

        elif scenario == "valid_ecdsa":
            item = items[0]
            dev_id = item.packet.device_id
            ecdsa_cred = self._ecdsa_credentials[dev_id]
            dev_key = self._device_keys[dev_id]

            self._registry.update_credential(dev_id, ecdsa_cred)
            packet = self._prepare_packet(item, ecdsa_cred, "ecdsa_valid")
            signature = C4TrustService.sign_packet_ecdsa(packet, dev_key)
            result = self._gate.process(
                packet,
                signature,
                now=packet.observed_at,
            )
            rows.append(
                self._result_row(
                    result,
                    "Valid Telemetry (X.509 + ECDSA)",
                    "ecdsa-sha256",
                    packet,
                )
            )

        elif scenario == "tampered_ecdsa":
            item = items[0]
            dev_id = item.packet.device_id
            ecdsa_cred = self._ecdsa_credentials[dev_id]
            dev_key = self._device_keys[dev_id]

            self._registry.update_credential(dev_id, ecdsa_cred)
            packet = self._prepare_packet(item, ecdsa_cred, "ecdsa_tampered")
            signature = C4TrustService.sign_packet_ecdsa(packet, dev_key)
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
                    tampered_packet,
                )
            )

        elif scenario == "expired_x509":
            item = items[0]
            dev_id = item.packet.device_id
            dev_key = self._device_keys[dev_id]

            # Generate expired certificate
            _, _, expired_pem = create_device_certificate(
                dev_id,
                self._ca_cert,
                self._ca_key,
                valid_days=5,
                not_before_offset_days=-20,
                private_key=dev_key,
                issued_at=DEMO_PKI_ISSUED_AT,
            )
            expired_cred = DeviceCredential(
                credential_id=f"EXPIRED-CRED-{dev_id}",
                secret=b"unused",
                signature_algorithm="ecdsa-sha256",
                certificate_pem=expired_pem,
            )
            self._registry.update_credential(dev_id, expired_cred)
            packet = self._prepare_packet(
                item,
                expired_cred,
                "x509_expired",
                custom_cert_pem=expired_pem.decode("utf-8"),
            )
            signature = C4TrustService.sign_packet_ecdsa(packet, dev_key)
            result = self._gate.process(
                packet,
                signature,
                now=packet.observed_at,
            )
            rows.append(
                self._result_row(
                    result,
                    "Expired Certificate (X.509)",
                    "ecdsa-sha256",
                    packet,
                )
            )

        elif scenario == "untrusted_ca_x509":
            item = items[0]
            dev_id = item.packet.device_id
            dev_key = self._device_keys[dev_id]

            rogue_key, rogue_cert, _ = create_ca(
                "Rogue Imposter Root CA",
                issued_at=DEMO_PKI_ISSUED_AT,
            )
            _, _, rogue_dev_pem = create_device_certificate(
                dev_id,
                rogue_cert,
                rogue_key,
                private_key=dev_key,
                issued_at=DEMO_PKI_ISSUED_AT,
            )
            rogue_cred = DeviceCredential(
                credential_id=f"ROGUE-CRED-{dev_id}",
                secret=b"unused",
                signature_algorithm="ecdsa-sha256",
                certificate_pem=rogue_dev_pem,
            )
            self._registry.update_credential(dev_id, rogue_cred)
            packet = self._prepare_packet(
                item,
                rogue_cred,
                "x509_untrusted_ca",
                custom_cert_pem=rogue_dev_pem.decode("utf-8"),
            )
            signature = C4TrustService.sign_packet_ecdsa(packet, dev_key)
            result = self._gate.process(
                packet,
                signature,
                now=packet.observed_at,
            )
            rows.append(
                self._result_row(
                    result,
                    "Untrusted CA Certificate (X.509)",
                    "ecdsa-sha256",
                    packet,
                )
            )

        elif scenario == "mismatched_identity_x509":
            item = items[0]
            dev_id = item.packet.device_id
            dev_key = self._device_keys[dev_id]

            # Issue certificate for a completely different device
            _, _, mismatch_pem = create_device_certificate(
                "GNX-IMPOSTER-SENSOR-999",
                self._ca_cert,
                self._ca_key,
                private_key=dev_key,
                issued_at=DEMO_PKI_ISSUED_AT,
            )
            mismatch_cred = DeviceCredential(
                credential_id=f"MISMATCH-CRED-{dev_id}",
                secret=b"unused",
                signature_algorithm="ecdsa-sha256",
                certificate_pem=mismatch_pem,
            )
            self._registry.update_credential(dev_id, mismatch_cred)
            packet = self._prepare_packet(
                item,
                mismatch_cred,
                "x509_mismatch",
                custom_cert_pem=mismatch_pem.decode("utf-8"),
            )
            signature = C4TrustService.sign_packet_ecdsa(packet, dev_key)
            result = self._gate.process(
                packet,
                signature,
                now=packet.observed_at,
            )
            rows.append(
                self._result_row(
                    result,
                    "Identity Mismatch Certificate (X.509)",
                    "ecdsa-sha256",
                    packet,
                )
            )

        elif scenario == "revoked_x509":
            item = items[0]
            dev_id = item.packet.device_id
            dev_key = self._device_keys[dev_id]
            ecdsa_cred = self._ecdsa_credentials[dev_id]

            self._registry.update_credential(dev_id, ecdsa_cred)
            self._registry.revoke(dev_id)

            packet = self._prepare_packet(item, ecdsa_cred, "x509_revoked")
            signature = C4TrustService.sign_packet_ecdsa(packet, dev_key)
            result = self._gate.process(
                packet,
                signature,
                now=packet.observed_at,
            )
            rows.append(
                self._result_row(
                    result,
                    "Revoked Device (X.509)",
                    "ecdsa-sha256",
                    packet,
                )
            )
            # Re-activate for subsequent runs
            self._registry.update_lifecycle_state(dev_id, DeviceLifecycleState.ACTIVE)

        elif scenario == "unverifiable_ecdsa":
            item = items[0]
            dev_id = item.packet.device_id
            dev_key = self._device_keys[dev_id]
            unverifiable_cred = DeviceCredential(
                credential_id=f"DEMO-UNVERIFIABLE-{dev_id}",
                secret=b"dashboard-demo-only",
                signature_algorithm="ecdsa-sha256",
                public_key_pem=None,
                certificate_pem=None,
            )
            self._registry.update_credential(dev_id, unverifiable_cred)
            packet = self._prepare_packet(item, unverifiable_cred, "ecdsa_unverifiable")
            signature = C4TrustService.sign_packet_ecdsa(packet, dev_key)
            result = self._gate.process(
                packet,
                signature,
                now=packet.observed_at,
            )
            rows.append(
                self._result_row(
                    result,
                    "Unavailable Key/Certificate (ECDSA)",
                    "ecdsa-sha256",
                    packet,
                )
            )

        elif scenario == "fallback_rejection":
            item = items[0]
            dev_id = item.packet.device_id
            ecdsa_cred = self._ecdsa_credentials[dev_id]

            self._registry.update_credential(dev_id, ecdsa_cred)
            packet = self._prepare_packet(item, ecdsa_cred, "ecdsa_fallback")
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
                    packet,
                )
            )

        return rows

    def close(self) -> None:
        self._temporary_directory.cleanup()
