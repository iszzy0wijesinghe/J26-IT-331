"""Unit tests for C4 runtime feature adapter and ML integration."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from components.c4_trust.integration import (
    create_c4_service_deterministic_only,
    create_c4_service_with_behavioral_ml,
)
from components.c4_trust.registry import (
    DeviceCredential,
    DeviceKind,
    DeviceRegistry,
)
from components.c4_trust.runtime_features import (
    C4_MODEL_FEATURE_SCHEMA,
    DeviceHistory,
    FeatureError,
    RuntimeFeatureAdapter,
)
from components.c4_trust.service import C4TrustService
from shared.contracts.telemetry import (
    DeviceHealth,
    SecurityMetadata,
    TelemetryPacket,
    TransportMetadata,
)
from shared.enums import C4RoutingOutcome, C4TrustLabel, SourceOrigin


class TestRuntimeFeatureAdapter:
    """Test RuntimeFeatureAdapter."""

    def _make_packet(self) -> TelemetryPacket:
        """Create a valid telemetry packet for feature extraction tests."""
        now = datetime.now(UTC)

        return TelemetryPacket(
            schema_version="1.0",
            packet_id="TEST-INVALID",
            device_id="Z1-A01",
            zone_id="Z1",
            boot_id="BOOT-001",
            sequence_no=1,
            observed_at=now - timedelta(seconds=2),
            received_at=now,
            message_type="TELEMETRY",
            tx_interval_s=30.0,
            freshness_status="fresh",
            measurements=[],
            device_health=DeviceHealth(
                battery_voltage=12.0,
                supply_current=120.0,
                restart_count=0,
                battery_pct=80.0,
                reboot_count_24h=0,
                sensor_fault_flag=False,
            ),
            transport=TransportMetadata(
                rssi_dbm=-75.0,
                snr_db=7.0,
                retry_count=0,
                gateway_id="H001",
            ),
            security=SecurityMetadata(),
            source_origin=SourceOrigin.SIMULATED,
        )

    def test_adapter_initialization(self) -> None:
        """Test adapter initializes with valid parameters."""
        adapter = RuntimeFeatureAdapter(history_window=10)
        assert adapter._history_window == 10
        assert len(adapter._device_histories) == 0

    def test_adapter_invalid_window(self) -> None:
        """Test adapter rejects invalid window size."""
        with pytest.raises(ValueError, match="history_window must be at least 1"):
            RuntimeFeatureAdapter(history_window=0)

    def test_feature_schema_constant(self) -> None:
        """Test C4_MODEL_FEATURE_SCHEMA matches expected model schema."""
        expected = (
            "tx_interval_s",
            "rx_delay_s",
            "freshness_status_encoded",
            "rssi_dbm",
            "rssi_deviation_db",
            "snr_db",
            "retry_count",
            "packet_size_bytes",
            "battery_pct",
            "battery_voltage_v",
            "current_ma",
            "reboot_count_24h",
            "sensor_fault_flag",
            "rolling_interval_mean",
            "rolling_interval_std",
            "rolling_rssi_mean",
            "rolling_rssi_std",
            "rolling_retry_mean",
        )
        assert C4_MODEL_FEATURE_SCHEMA == expected
        assert len(C4_MODEL_FEATURE_SCHEMA) == 18

    def test_extract_features_complete_packet(self) -> None:
        """Test feature extraction from a complete valid packet."""
        adapter = RuntimeFeatureAdapter(history_window=10)
        packet = self._make_packet()

        features_df = adapter.extract_features(packet)

        assert len(features_df) == 1
        assert list(features_df.columns) == list(C4_MODEL_FEATURE_SCHEMA)
        assert features_df["tx_interval_s"].iloc[0] == 30.0
        assert features_df["freshness_status_encoded"].iloc[0] == 0
        assert features_df["rssi_dbm"].iloc[0] == -75.0

    def test_extract_features_missing_tx_interval(self) -> None:
        """Test feature extraction rejects a missing transmission interval."""
        adapter = RuntimeFeatureAdapter()
        packet = self._make_packet().model_copy(update={"tx_interval_s": None})

        with pytest.raises(FeatureError) as exc_info:
            adapter.extract_features(packet)

        assert exc_info.value.reason == "Required feature tx_interval_s is missing"

    def test_extract_features_missing_freshness(self) -> None:
        """Test feature extraction rejects a missing freshness status."""
        adapter = RuntimeFeatureAdapter()
        packet = self._make_packet().model_copy(update={"freshness_status": None})

        with pytest.raises(FeatureError) as exc_info:
            adapter.extract_features(packet)

        assert exc_info.value.reason == ("Freshness status is missing - cannot assume 'fresh'")

    def test_extract_features_invalid_freshness(self) -> None:
        """Test feature extraction rejects an invalid freshness status."""
        adapter = RuntimeFeatureAdapter()
        packet = self._make_packet().model_copy(update={"freshness_status": "unknown"})

        with pytest.raises(FeatureError) as exc_info:
            adapter.extract_features(packet)

        assert exc_info.value.reason == "Invalid freshness status: unknown"

    def test_extract_features_invalid_numeric(self) -> None:
        """Test feature extraction rejects a non-finite transmission interval."""
        adapter = RuntimeFeatureAdapter()
        packet = self._make_packet().model_copy(update={"tx_interval_s": float("nan")})

        with pytest.raises(FeatureError) as exc_info:
            adapter.extract_features(packet)

        assert exc_info.value.reason == "Feature tx_interval_s is not finite: nan"

    def test_extract_features_rssi_deviation_no_history(self) -> None:
        """Test RSSI deviation returns 0.0 when device has no history."""
        adapter = RuntimeFeatureAdapter(history_window=10)
        packet = self._make_packet()

        features_df = adapter.extract_features(packet)

        assert features_df["rssi_deviation_db"].iloc[0] == 0.0

    def test_device_history_rolling_features(self) -> None:
        """Test device history calculates rolling features correctly."""
        history = DeviceHistory(device_id="Z1-A01", window_size=3)

        history.add_observation(
            observed_at=datetime.now(UTC) - timedelta(seconds=60),
            tx_interval_s=30.0,
            rssi_dbm=-75.0,
            retry_count=0,
        )
        history.add_observation(
            observed_at=datetime.now(UTC) - timedelta(seconds=30),
            tx_interval_s=30.0,
            rssi_dbm=-80.0,
            retry_count=1,
        )
        history.add_observation(
            observed_at=datetime.now(UTC),
            tx_interval_s=30.0,
            rssi_dbm=-70.0,
            retry_count=0,
        )

        features = history.get_rolling_features()

        assert features["rolling_interval_mean"] == 30.0
        assert features["rolling_interval_std"] == 0.0
        assert features["rolling_rssi_mean"] == pytest.approx(-75.0)
        assert features["rolling_retry_mean"] == pytest.approx(0.333, rel=0.01)

    def test_device_history_window_trimming(self) -> None:
        """Test device history trims to window size."""
        history = DeviceHistory(device_id="Z1-A01", window_size=2)

        for i in range(5):
            history.add_observation(
                observed_at=datetime.now(UTC) - timedelta(seconds=(5 - i) * 10),
                tx_interval_s=30.0,
                rssi_dbm=-75.0 + i,
                retry_count=i,
            )

        assert len(history.intervals) == 2
        assert len(history.rssi_values) == 2
        assert len(history.retry_counts) == 2

    def test_device_history_clear(self) -> None:
        """Test device history can be cleared."""
        history = DeviceHistory(device_id="Z1-A01", window_size=10)

        history.add_observation(
            observed_at=datetime.now(UTC),
            tx_interval_s=30.0,
            rssi_dbm=-75.0,
            retry_count=0,
        )

        assert len(history.intervals) == 1

        history.clear()

        assert len(history.intervals) == 0
        assert len(history.rssi_values) == 0
        assert len(history.retry_counts) == 0

    def test_adapter_device_isolation(self) -> None:
        """Test device histories are isolated between devices."""
        adapter = RuntimeFeatureAdapter(history_window=10)

        packet1 = self._make_packet()
        packet2 = self._make_packet().model_copy(
            update={
                "packet_id": "TEST-002",
                "device_id": "Z1-A02",
                "transport": TransportMetadata(
                    rssi_dbm=-90.0,
                    snr_db=5.0,
                    retry_count=0,
                    gateway_id="H001",
                ),
            }
        )

        features1 = adapter.extract_features(packet1)
        assert features1["rssi_deviation_db"].iloc[0] == 0.0

        features2 = adapter.extract_features(packet2)
        assert features2["rssi_deviation_db"].iloc[0] == 0.0

        assert len(adapter._device_histories["Z1-A01"].rssi_values) == 1
        assert len(adapter._device_histories["Z1-A02"].rssi_values) == 1
        assert adapter._device_histories["Z1-A01"].rssi_values[0] == -75.0
        assert adapter._device_histories["Z1-A02"].rssi_values[0] == -90.0

    def test_adapter_clear_device_history(self) -> None:
        """Test adapter can clear history for a specific device."""
        adapter = RuntimeFeatureAdapter(history_window=10)
        packet = self._make_packet()

        features_df = adapter.extract_features(packet)
        assert features_df is not None

        adapter.clear_all_history()

        assert "Z1-A01" not in adapter._device_histories


class TestC4Integration:
    """Test C4 behavioral ML integration."""

    def test_create_service_with_missing_model(self) -> None:
        """Test service creation fails when model is missing."""
        registry = DeviceRegistry()
        registry.register(
            "Z1-A01",
            DeviceKind.TYPE_A,
            "Z1",
            "H001",
            DeviceCredential("cred-001", b"secret"),
        )
        registry.activate("Z1-A01")

        model_path = Path("experiments/c4/models/nonexistent.joblib")

        with pytest.raises(FileNotFoundError, match="Model artifact not found"):
            create_c4_service_with_behavioral_ml(registry, model_path)

    def test_create_service_deterministic_only(self) -> None:
        """Test creating deterministic-only service."""
        registry = DeviceRegistry()
        registry.register(
            "Z1-A01",
            DeviceKind.TYPE_A,
            "Z1",
            "H001",
            DeviceCredential("cred-001", b"secret"),
        )
        registry.activate("Z1-A01")

        service = create_c4_service_deterministic_only(registry)

        assert service is not None
        assert service._allow_deterministic_only is True
        assert service._behavioural_scorer is None

    def test_deterministic_gate_overrides_ml(self) -> None:
        """Test that deterministic security failures override ML scores."""
        registry = DeviceRegistry()
        registry.register(
            "Z1-A01",
            DeviceKind.TYPE_A,
            "Z1",
            "H001",
            DeviceCredential("cred-001", b"secret"),
        )
        registry.activate("Z1-A01")

        service = C4TrustService(
            registry,
            behavioural_scorer=lambda packet: 0.99,
            allow_deterministic_only=False,
        )

        packet = TelemetryPacket(
            schema_version="1.0",
            packet_id="TEST-001",
            device_id="UNKNOWN-DEVICE",
            zone_id="Z1",
            boot_id="BOOT-001",
            sequence_no=1,
            observed_at=datetime.now(UTC) - timedelta(seconds=2),
            received_at=datetime.now(UTC),
            message_type="TELEMETRY",
            measurements=[],
            device_health=DeviceHealth(),
            transport=TransportMetadata(),
            security=SecurityMetadata(),
            source_origin=SourceOrigin.SIMULATED,
        )

        assessment = service.assess(packet, signature=None)

        assert assessment.trust_label == C4TrustLabel.UNTRUSTED
        assert assessment.routing_outcome == C4RoutingOutcome.REJECT
        assert "DEVICE_UNKNOWN" in assessment.reason_codes
        assert assessment.mandatory_security_pass is False

    def test_missing_features_trigger_unknown(self) -> None:
        """Test that missing features trigger UNKNOWN/SECURITY_REVIEW."""
        registry = DeviceRegistry()
        registry.register(
            "Z1-A01",
            DeviceKind.TYPE_A,
            "Z1",
            "H001",
            DeviceCredential("cred-001", b"secret"),
        )
        registry.activate("Z1-A01")

        def failing_scorer(packet: TelemetryPacket) -> float | None:
            return None

        def always_verify(packet: TelemetryPacket, device_record: object) -> bool:
            return True

        service = C4TrustService(
            registry,
            behavioural_scorer=failing_scorer,
            attestation_verifier=always_verify,
            provenance_verifier=always_verify,
            allow_deterministic_only=False,
        )

        packet = TelemetryPacket(
            schema_version="1.0",
            packet_id="TEST-001",
            device_id="Z1-A01",
            zone_id="Z1",
            boot_id="BOOT-001",
            sequence_no=1,
            observed_at=datetime.now(UTC) - timedelta(seconds=2),
            received_at=datetime.now(UTC),
            message_type="TELEMETRY",
            tx_interval_s=30.0,
            freshness_status="fresh",
            measurements=[],
            device_health=DeviceHealth(
                battery_voltage=12.0,
                supply_current=120.0,
                restart_count=0,
                battery_pct=80.0,
                reboot_count_24h=0,
                sensor_fault_flag=False,
            ),
            transport=TransportMetadata(
                rssi_dbm=-75.0,
                snr_db=7.0,
                retry_count=0,
                gateway_id="H001",
            ),
            security=SecurityMetadata(credential_id="cred-001"),
            source_origin=SourceOrigin.SIMULATED,
        )

        signature = service.sign_packet(packet, b"secret")
        assessment = service.assess(packet, signature)

        assert assessment.trust_label == C4TrustLabel.UNKNOWN
        assert assessment.routing_outcome == C4RoutingOutcome.SECURITY_REVIEW
        assert "BEHAVIOURAL_SCORE_UNAVAILABLE" in assessment.reason_codes

    def test_invalid_score_triggers_unknown(self) -> None:
        """Test that invalid scores trigger UNKNOWN/SECURITY_REVIEW."""
        registry = DeviceRegistry()
        registry.register(
            "Z1-A01",
            DeviceKind.TYPE_A,
            "Z1",
            "H001",
            DeviceCredential("cred-001", b"secret"),
        )
        registry.activate("Z1-A01")

        def invalid_scorer(packet: TelemetryPacket) -> float | None:
            return 1.5

        def always_verify(packet: TelemetryPacket, device_record: object) -> bool:
            return True

        service = C4TrustService(
            registry,
            behavioural_scorer=invalid_scorer,
            attestation_verifier=always_verify,
            provenance_verifier=always_verify,
            allow_deterministic_only=False,
        )

        packet = TelemetryPacket(
            schema_version="1.0",
            packet_id="TEST-001",
            device_id="Z1-A01",
            zone_id="Z1",
            boot_id="BOOT-001",
            sequence_no=1,
            observed_at=datetime.now(UTC) - timedelta(seconds=2),
            received_at=datetime.now(UTC),
            message_type="TELEMETRY",
            tx_interval_s=30.0,
            freshness_status="fresh",
            measurements=[],
            device_health=DeviceHealth(
                battery_voltage=12.0,
                supply_current=120.0,
                restart_count=0,
                battery_pct=80.0,
                reboot_count_24h=0,
                sensor_fault_flag=False,
            ),
            transport=TransportMetadata(
                rssi_dbm=-75.0,
                snr_db=7.0,
                retry_count=0,
                gateway_id="H001",
            ),
            security=SecurityMetadata(credential_id="cred-001"),
            source_origin=SourceOrigin.SIMULATED,
        )

        signature = service.sign_packet(packet, b"secret")
        assessment = service.assess(packet, signature)

        assert assessment.trust_label == C4TrustLabel.UNKNOWN
        assert assessment.routing_outcome == C4RoutingOutcome.SECURITY_REVIEW
        assert "BEHAVIOURAL_SCORE_INVALID" in assessment.reason_codes

    def test_nan_score_triggers_unknown(self) -> None:
        """Test that NaN scores trigger UNKNOWN/SECURITY_REVIEW."""
        registry = DeviceRegistry()
        registry.register(
            "Z1-A01",
            DeviceKind.TYPE_A,
            "Z1",
            "H001",
            DeviceCredential("cred-001", b"secret"),
        )
        registry.activate("Z1-A01")

        def nan_scorer(packet: TelemetryPacket) -> float | None:
            return float("nan")

        def always_verify(packet: TelemetryPacket, device_record: object) -> bool:
            return True

        service = C4TrustService(
            registry,
            behavioural_scorer=nan_scorer,
            attestation_verifier=always_verify,
            provenance_verifier=always_verify,
            allow_deterministic_only=False,
        )

        packet = TelemetryPacket(
            schema_version="1.0",
            packet_id="TEST-001",
            device_id="Z1-A01",
            zone_id="Z1",
            boot_id="BOOT-001",
            sequence_no=1,
            observed_at=datetime.now(UTC) - timedelta(seconds=2),
            received_at=datetime.now(UTC),
            message_type="TELEMETRY",
            tx_interval_s=30.0,
            freshness_status="fresh",
            measurements=[],
            device_health=DeviceHealth(
                battery_voltage=12.0,
                supply_current=120.0,
                restart_count=0,
                battery_pct=80.0,
                reboot_count_24h=0,
                sensor_fault_flag=False,
            ),
            transport=TransportMetadata(
                rssi_dbm=-75.0,
                snr_db=7.0,
                retry_count=0,
                gateway_id="H001",
            ),
            security=SecurityMetadata(credential_id="cred-001"),
            source_origin=SourceOrigin.SIMULATED,
        )

        signature = service.sign_packet(packet, b"secret")
        assessment = service.assess(packet, signature)

        assert assessment.trust_label == C4TrustLabel.UNKNOWN
        assert assessment.routing_outcome == C4RoutingOutcome.SECURITY_REVIEW
        assert "BEHAVIOURAL_SCORE_INVALID" in assessment.reason_codes
