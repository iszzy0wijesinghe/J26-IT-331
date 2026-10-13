"""C4 behavioral ML runtime integration.

This module provides the factory function to create a C4TrustService with
the behavioral ML model and runtime feature adapter properly wired together.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from components.c4_trust.models import C4BehavioralModelRunner, ModelSchemaError
from components.c4_trust.registry import DeviceRegistry
from components.c4_trust.runtime_features import (
    C4_MODEL_FEATURE_SCHEMA,
    FeatureError,
    RuntimeFeatureAdapter,
)
from components.c4_trust.service import C4TrustService
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
) -> C4TrustService:
    """Create a C4TrustService with behavioral ML integration.

    This factory function:
    1. Loads the trained model artifact with schema validation
    2. Creates a runtime feature adapter
    3. Creates a C4BehavioralModelRunner that connects both
    4. Creates a C4TrustService with the behavioral scorer wired in

    If the model cannot be loaded or has an incompatible schema, this
    function raises ModelSchemaError with a clear error message.

    Args:
        registry: Device registry for deterministic security checks
        model_path: Path to the trained model artifact
        max_age_seconds: Maximum allowed packet age in seconds
        future_tolerance_seconds: Tolerance for future timestamps
        suspicious_score_threshold: Threshold for SUSPICIOUS classification
        history_window: Rolling window size for historical features
        require_sequence: Whether to require sequence numbers
        require_firmware_approval: Whether to require firmware approval
        require_config_approval: Whether to require config approval

    Returns:
        Configured C4TrustService with behavioral ML integration

    Raises:
        FileNotFoundError: If model artifact does not exist
        ModelSchemaError: If model artifact is corrupted or has incompatible schema
    """
    # Create runtime feature adapter
    feature_adapter = RuntimeFeatureAdapter(history_window=history_window)

    # Create feature builder function for the model runner
    def feature_builder(packet: TelemetryPacket) -> Callable[[TelemetryPacket], float]:
        """Extract features from a packet for ML inference."""
        try:
            features_df = feature_adapter.extract_features(packet)
            return features_df
        except FeatureError as exc:
            raise ModelSchemaError(
                f"Feature extraction failed for packet {packet.packet_id}: {exc.reason}"
            ) from exc

    # Load model with schema validation
    model_runner = C4BehavioralModelRunner.load(
        path=model_path,
        expected_feature_names=C4_MODEL_FEATURE_SCHEMA,
        feature_builder=feature_builder,
    )

    # Create behavioral scorer function
    def behavioural_scorer(packet: TelemetryPacket) -> float | None:
        """Score a packet using the behavioral ML model.

        Returns:
            Behavioral anomaly score (0.0 = normal, 1.0 = anomalous)
            Returns None if scoring fails
        """
        try:
            return model_runner(packet)
        except ModelSchemaError:
            # Feature extraction or scoring failed - return None to trigger UNKNOWN
            return None
        except Exception:
            # Unexpected error - return None to trigger UNKNOWN
            return None

    # Create C4TrustService with behavioral scorer
    service = C4TrustService(
        credentials_or_registry=registry,
        max_age_seconds=max_age_seconds,
        future_tolerance_seconds=future_tolerance_seconds,
        suspicious_score_threshold=suspicious_score_threshold,
        behavioural_scorer=behavioural_scorer,
        allow_deterministic_only=False,  # Require behavioral score in production
        require_sequence=require_sequence,
        require_firmware_approval=require_firmware_approval,
        require_config_approval=require_config_approval,
    )

    return service


def create_c4_service_deterministic_only(
    registry: DeviceRegistry,
    *,
    max_age_seconds: float = 30.0,
    future_tolerance_seconds: float = 5.0,
    require_sequence: bool = True,
    require_firmware_approval: bool = False,
    require_config_approval: bool = False,
) -> C4TrustService:
    """Create a C4TrustService without behavioral ML (deterministic-only mode).

    This is useful for testing or when the behavioral model is unavailable.

    Args:
        registry: Device registry for deterministic security checks
        max_age_seconds: Maximum allowed packet age in seconds
        future_tolerance_seconds: Tolerance for future timestamps
        require_sequence: Whether to require sequence numbers
        require_firmware_approval: Whether to require firmware approval
        require_config_approval: Whether to require config approval

    Returns:
        C4TrustService in deterministic-only mode
    """
    return C4TrustService(
        credentials_or_registry=registry,
        max_age_seconds=max_age_seconds,
        future_tolerance_seconds=future_tolerance_seconds,
        behavioural_scorer=None,
        allow_deterministic_only=True,  # Allow deterministic-only operation
        require_sequence=require_sequence,
        require_firmware_approval=require_firmware_approval,
        require_config_approval=require_config_approval,
    )
