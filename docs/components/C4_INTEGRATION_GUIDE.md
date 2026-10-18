# C4 Runtime Integration Guide

## Overview

Component 4 (C4) - Trusted Telemetry Provenance and Device Attestation - is implemented and ready for runtime integration. This guide explains how to integrate C4 into the GeoNex telemetry ingestion pipeline.

## Current Status

**Completed Components:**
- ✅ Security decision policy with mandatory checks (identity, integrity, freshness, replay, attestation, provenance)
- ✅ Device registry with lifecycle management
- ✅ Trust service with configurable policy (deterministic-only vs ML-augmented)
- ✅ Quarantine manager with safe release workflow
- ✅ C4 telemetry gate (C4TelemetryGate) for routing decisions
- ✅ Feature schema correction (20 behavioral features)
- ✅ Comprehensive unit and contract tests

**Incomplete/Blocked:**
- ⚠️ ML model artifacts are incompatible with corrected schema (require retraining in environment without sklearn DLL restrictions)
- ⚠️ No demonstrated runtime ingestion caller exists (requires integration in apps/ingestion or apps/runtime_orchestrator)

## Integration Point

C4 should be integrated **before** C1 (credibility assessment) in the telemetry pipeline:

```
Incoming Telemetry → C4 Trust Gate → (TRUSTED) → C1 Credibility → Golden Timeline
                         ↓
                 (UNTRUSTED/UNKNOWN/SUSPICIOUS)
                         ↓
                   Quarantine → Security Review
```

## Recommended Integration Pattern

### Option 1: Integration in apps/ingestion

Modify the ingestion service to include C4 assessment before persistence:

```python
from components.c4_trust import (
    C4TelemetryGate,
    C4TrustService,
    DeviceRegistry,
    QuarantineManager,
)
from shared.contracts import TelemetryPacket

# Initialize C4 components
registry = DeviceRegistry()
# Register devices...
registry.activate("DEVICE-001")

trust_service = C4TrustService(
    registry,
    attestation_verifier=your_attestation_verifier,
    provenance_verifier=your_provenance_verifier,
    allow_deterministic_only=True,  # or False for ML-augmented
)

quarantine = QuarantineManager()  # Uses default quarantine/c4 directory
gate = C4TelemetryGate(trust_service, quarantine)

# In ingestion handler
def process_telemetry(packet: TelemetryPacket, signature: str | None):
    # Assess with C4
    result = gate.process(packet, signature)

    if result.eligible_for_c1:
        # Forward to C1 and persistence
        persist_telemetry_packet(session, result.eligible_packet)
        forward_to_c1(result.eligible_packet)
    else:
        # Packet quarantined - do not persist or forward
        log_security_event(result.assessment, result.quarantine_record)
```

### Option 2: Integration in apps/runtime_orchestrator

Integrate C4 as a pre-processing step in the runtime orchestrator:

```python
class RuntimeOrchestrator:
    def __init__(self):
        self.c4_gate = C4TelemetryGate(
            trust_service=self._init_c4_service(),
            quarantine_manager=QuarantineManager(),
        )

    def handle_telemetry(self, packet: TelemetryPacket, signature: str | None):
        result = self.c4_gate.process(packet, signature)

        if result.eligible_for_c1:
            return self._process_trusted_packet(result.eligible_packet)
        else:
            return self._handle_security_failure(result)
```

## Required Configuration

### 1. Device Registry Setup

```python
from components.c4_trust import DeviceCredential, DeviceKind, DeviceRegistry

registry = DeviceRegistry()

# Register each device
registry.register(
    device_id="Z1-A01",
    device_kind=DeviceKind.TYPE_A,
    zone_id="Z1",
    hub_id="H001",
    credential=DeviceCredential(
        credential_id="cred-Z1-A01",
        secret=b"<device-secret-key>",
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=365),
    ),
    approved_firmware=True,
    approved_config=True,
)

# Activate devices
registry.activate("Z1-A01")
```

### 2. Evidence Verifiers

Configure attestation and provenance verifiers based on your protocol:

```python
def attestation_verifier(packet: TelemetryPacket, device: DeviceRecord | None) -> bool | None:
    """Verify device attestation evidence."""
    if packet.security.attestation_evidence is None:
        return None  # Evidence missing

    # Implement your attestation verification logic
    # Example: check TPM quote, secure boot measurement, etc.
    return verify_tpm_attestation(packet.security.attestation_evidence)

def provenance_verifier(packet: TelemetryPacket, device: DeviceRecord | None) -> bool | None:
    """Verify telemetry provenance evidence."""
    if packet.security.provenance_evidence is None:
        return None  # Evidence missing

    # Implement your provenance verification logic
    # Example: check hash chain, path validation, etc.
    return verify_provenance_chain(packet.security.provenance_evidence)
```

### 3. ML Behavioral Scoring (Optional)

If using ML-augmented mode (allow_deterministic_only=False):

```python
from components.c4_trust.models import C4BehavioralModelRunner
from components.c4_trust.features import FeatureExtractor

# Load trained model
feature_extractor = FeatureExtractor()

def feature_builder(packet: TelemetryPacket) -> pd.DataFrame:
    """Extract behavioral features from a packet."""
    # Convert packet to feature DataFrame
    # This requires mapping packet fields to feature columns
    features = extract_features_from_packet(packet)
    return features

model_runner = C4BehavioralModelRunner.load(
    path=Path("experiments/c4/models/logistic_regression.joblib"),
    expected_feature_names=FeatureExtractor.TRAINING_FEATURE_FIELDS,
    feature_builder=feature_builder,
)

trust_service = C4TrustService(
    registry,
    attestation_verifier=attestation_verifier,
    provenance_verifier=provenance_verifier,
    behavioural_scorer=model_runner,  # Pass model runner
    allow_deterministic_only=False,
)
```

## Decision Policy

The C4 service implements the following decision policy:

### TRUSTED
- All mandatory security checks pass
- Behavioral score (if available) below suspicious threshold
- Routing: ACCEPT → Forward to C1

### SUSPICIOUS
- All mandatory security checks pass
- Behavioral score at or above suspicious threshold
- Routing: QUARANTINE → Security review required

### UNTRUSTED
- Any mandatory security check fails (identity, integrity, freshness, replay, etc.)
- Routing: REJECT → Quarantine, not eligible for C1

### UNKNOWN
- Required evidence missing or cannot be verified
- If allow_deterministic_only=True and all mandatory checks pass → TRUSTED
- Otherwise → SECURITY_REVIEW → Quarantine, not eligible for C1

## Security Policy Parameters

```python
trust_service = C4TrustService(
    registry,
    max_age_seconds=30.0,              # Freshness window
    future_tolerance_seconds=5.0,      # Clock skew tolerance
    suspicious_score_threshold=0.7,     # Behavioral anomaly threshold
    attestation_verifier=attestation_verifier,
    provenance_verifier=provenance_verifier,
    behavioural_scorer=model_runner,   # Optional
    allow_deterministic_only=True,     # Policy mode
    require_sequence=True,             # Require sequence numbers
    require_firmware_approval=False,   # Optional policy
    require_config_approval=False,     # Optional policy
)
```

## Quarantine Management

### Default Location
- Directory: `quarantine/c4/` (relative to project root)
- Format: One JSON file per quarantined packet

### Release Workflow
1. Security operator reviews quarantined packet
2. Performs fresh C4 assessment with updated context
3. Calls `quarantine.release()` with:
   - Fresh TRUSTED assessment
   - Authorized reviewer ID
   - Release reason

### Monitoring
```python
report = quarantine.generate_report()
print(f"Total quarantined: {report['total_quarantined']}")
print(f"Unreleased: {report['unreleased_count']}")
print(f"By reason: {report['by_reason']}")
```

## Testing the Integration

Use the provided end-to-end test as a template:

```bash
pytest test_c4_e2e.py -v
```

This tests:
- Device registry setup
- C4 trust service assessment
- C4 gate routing decisions
- Quarantine persistence and release
- Report generation

## Known Limitations

1. **ML Model Incompatibility**: Existing model artifacts under `experiments/c4/models/` were trained with a 24-feature schema including mode-aware features. The corrected schema uses 20 features. Models must be retrained.

2. **Sklearn DLL Restrictions**: The current environment blocks sklearn imports due to Application Control policy. Model retraining must be done in an environment without this restriction.

3. **No Runtime Integration**: There is currently no demonstrated runtime caller of C4TrustService. Integration must be added to `apps/ingestion` or `apps/runtime_orchestrator`.

## Next Steps

1. Choose integration point (ingestion or runtime orchestrator)
2. Implement device registry initialization with actual device credentials
3. Implement attestation and provenance verifiers based on your protocol
4. Add C4 gate to telemetry processing pipeline
5. Configure quarantine release authorization
6. Test integration with end-to-end scenarios
7. Retrain ML models with corrected 20-feature schema (optional, for ML-augmented mode)
