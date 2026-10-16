
"""C4 behavioral ML runtime integration."""

from __future__ import annotations

from pathlib import Path

from components.c4_trust.models import C4BehavioralModelRunner, ModelSchemaError
from components.c4_trust.registry import DeviceRegistry
from components.c4_trust.runtime_features import (
    C4_MODEL_FEATURE_SCHEMA,
    FeatureError,
    RuntimeFeatureAdapter,
)
from components.c4_trust.service import C4TrustService, EvidenceVerifier
from shared.contracts.telemetry import TelemetryPacket


def create_c4_service_with_behavioral_ml(
    registry: DeviceRegistry,
    model_path: Path,
    *,
    max_age_seconds: float = 30.0,
    future_tolerance_seconds: float = 5.0,
    suspicious_score_threshold: float = 0.7,
    history_window: int = 10,
    require_sequence: bool = True,
    require_firmware_approval: bool = False,
    require_config_approval: bool = False,
    attestation_verifier: EvidenceVerifier | None = None,
    provenance_verifier: EvidenceVerifier | None = None,
) -> C4TrustService:
    """Create a C4TrustService with behavioral ML integration.

    Loads and validates the trained model, configures runtime feature
    extraction, and connects the behavioral scorer to the trust service.

    Raises:
        FileNotFoundError: If the model artifact does not exist.
        ModelSchemaError: If the model artifact or feature schema is invalid.
    """
    feature_adapter = RuntimeFeatureAdapter(history_window=history_window)

    def feature_builder(packet: TelemetryPacket):
        """Extract runtime features for model inference."""
        try:
            return feature_adapter.extract_features(packet)
        except FeatureError as exc:
            raise ModelSchemaError(
                f"Feature extraction failed for packet "
                f"{packet.packet_id}: {exc.reason}"
            ) from exc

    model_runner = C4BehavioralModelRunner.load(
        path=model_path,
        expected_feature_names=C4_MODEL_FEATURE_SCHEMA,
        feature_builder=feature_builder,
    )

    def behavioural_scorer(packet: TelemetryPacket) -> float | None:
        """Return the behavioral anomaly score or None if scoring fails."""
        try:
            return model_runner(packet)
        except Exception:
            return None

    return C4TrustService(
        credentials_or_registry=registry,
        max_age_seconds=max_age_seconds,
        future_tolerance_seconds=future_tolerance_seconds,
        suspicious_score_threshold=suspicious_score_threshold,
        attestation_verifier=attestation_verifier,
        provenance_verifier=provenance_verifier,
        behavioural_scorer=behavioural_scorer,
        allow_deterministic_only=False,
        require_sequence=require_sequence,
        require_firmware_approval=require_firmware_approval,
        require_config_approval=require_config_approval,
    )


def create_c4_service_deterministic_only(
    registry: DeviceRegistry,
    *,
    max_age_seconds: float = 30.0,
    future_tolerance_seconds: float = 5.0,
    require_sequence: bool = True,
    require_firmware_approval: bool = False,
    require_config_approval: bool = False,
) -> C4TrustService:
    """Create a C4TrustService without behavioral ML."""
    return C4TrustService(
        credentials_or_registry=registry,
        max_age_seconds=max_age_seconds,
        future_tolerance_seconds=future_tolerance_seconds,
        behavioural_scorer=None,
        allow_deterministic_only=True,
        require_sequence=require_sequence,
        require_firmware_approval=require_firmware_approval,
        require_config_approval=require_config_approval,
    )
