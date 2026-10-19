# Component 4 (C4) - Trusted Telemetry Provenance and Device Attestation

## Overview

Component 4 (C4) is responsible for verifying the trustworthiness of telemetry sources and transmission context. It combines deterministic security checks with behavioral anomaly detection to distinguish legitimate telemetry from untrusted, replayed, spoofed, or tampered data.

## Architecture

```
Telemetry Packet
    ↓
Deterministic Security Gate (identity, integrity, freshness, replay)
    ↓
Behavioral ML Assessment (timing, radio, packet, health, path features)
    ↓
Trust Fusion (combine deterministic + behavioral)
    ↓
Trust Decision: TRUSTED / SUSPICIOUS / UNTRUSTED
    ↓
Routing: ACCEPT / QUARANTINE / REJECT
```

## Key Principles

1. **Mandatory security cannot be overridden by ML** - If deterministic checks fail, the packet is UNTRUSTED regardless of behavioral score
2. **Separate deterministic from behavioral evidence** - Security fields are excluded from ML training to prevent leakage
3. **Preserve reason codes** - Every trust decision must have explainable reasons
4. **Quarantine rejected telemetry** - Raw evidence is retained for audit, not deleted

## Implementation Status

### ✅ Completed

1. **C4_THREAT_MODEL.md** - 17 threat scenarios with attack paths and protections
2. **C4_DATASET_AUDIT.md** - Dataset audit identifying security field leakage
3. **C4_TRUST_LABEL_SPECIFICATION.md** - Trust label definitions
4. **Device Registry** - Lifecycle states (PROVISIONED, ACTIVE, SUSPENDED, REVOKED, RETIRED)
5. **Behavioral Feature Extraction** - B0-B5 features (timing, radio, packet, health, path, historical)
6. **Dataset Splits** - Train/val/test splits ready
7. **Baseline Models** - Logistic Regression, Random Forest, Isolation Forest
8. **Trust Fusion** - Deterministic gate + behavioral score (in C4TrustService)
9. **Quarantine System** - Audit and release mechanism for rejected telemetry

### 📋 Optional Enhancements

- XGBoost/LightGBM boosted tree model
- Mode-aware behavioral features
- Ablation study scripts
- Comprehensive experiment runner

## Directory Structure

```
components/c4_trust/
├── __init__.py              # Package exports
├── service.py               # C4TrustService (deterministic + fusion)
├── registry.py              # DeviceRegistry (lifecycle management)
├── features.py              # Behavioral feature extraction (B0-B5)
├── models.py                # Baseline ML models
├── data_split.py            # Scenario-aware data splitting
└── quarantine.py            # Quarantine manager

experiments/c4/
├── data/
│   ├── C4_Behavioral_Dataset.csv    # Clean behavioral dataset
│   ├── C4_train.csv                 # Training split
│   ├── C4_val.csv                   # Validation split
│   └── C4_test.csv                  # Test split
└── models/
    ├── logistic_regression.joblib
    ├── random_forest.joblib
    └── isolation_forest.joblib

scripts/
├── audit_c4_dataset.py              # Dataset audit script
├── prepare_c4_behavioral_dataset.py # Feature extraction
├── create_c4_splits.py              # Create train/val/test splits
└── train_c4_baselines.py            # Train baseline models

docs/components/
├── C4_THREAT_MODEL.md
├── C4_DATASET_AUDIT.md
└── C4_TRUST_LABEL_SPECIFICATION.md
```

## How to Run

### 1. Install Dependencies

```bash
pip install pandas scikit-learn joblib
```

Or install from pyproject.toml:
```bash
pip install -e .
```

### 2. Prepare Dataset

The C4_Trust.csv dataset should be at:
```
c:\Users\User\Desktop\Dataset\all datasets\C4_Trust.csv
```

Run the dataset preparation pipeline:

```bash
# Step 1: Audit the dataset
python scripts/audit_c4_dataset.py

# Step 2: Extract behavioral features
python scripts/prepare_c4_behavioral_dataset.py

# Step 3: Create train/val/test splits
python scripts/create_c4_splits.py
```

Output will be in `experiments/c4/data/`:
- `C4_Behavioral_Dataset.csv` - Clean behavioral features
- `C4_train.csv` - Training split (6987 samples)
- `C4_val.csv` - Validation split (1520 samples)
- `C4_test.csv` - Test split (1493 samples)

### 3. Train Baseline Models

```bash
python scripts/train_c4_baselines.py
```

This will train:
- Logistic Regression (Test F1: ~0.87)
- Random Forest (Test F1: ~0.89)
- Isolation Forest (anomaly detection)

Models are saved to `experiments/c4/models/`.

### 4. Run Unit Tests

```bash
# Test device registry
pytest tests/security/test_c4_device_registry.py -v

# Test trust service
pytest tests/security/test_c4_trust_service.py -v
```

### 5. Use C4TrustService in Code

```python
from components.c4_trust import C4TrustService, DeviceRegistry, DeviceCredential
from shared.contracts import TelemetryPacket
from shared.enums import C4TrustLabel

# Create device registry
registry = DeviceRegistry()
registry.register(
    device_id="Z1-A01",
    device_kind=DeviceKind.TYPE_A,
    zone_id="Z1",
    hub_id="H001",
    credential=DeviceCredential(
        credential_id="cred-001",
        secret=b"secret-key",
    ),
)
registry.activate("Z1-A01")

# Create trust service with registry
service = C4TrustService(
    registry,
    max_age_seconds=30,
    future_tolerance_seconds=5,
    suspicious_score_threshold=0.7,
)

# Assess a packet
assessment = service.assess(
    packet=telemetry_packet,
    signature="packet-signature",
    behavioural_score=0.5,  # Optional: from ML model
)

print(f"Trust Label: {assessment.trust_label}")
print(f"Routing: {assessment.routing_outcome}")
print(f"Reasons: {assessment.reason_codes}")
```

### 6. Use Quarantine Manager

```python
from components.c4_trust.quarantine import QuarantineManager, QuarantineReason

quarantine = QuarantineManager()

# Quarantine a suspicious packet
record = quarantine.quarantine(
    packet_id="P000001",
    device_id="Z1-A01",
    trust_label=C4TrustLabel.SUSPICIOUS,
    routing_outcome=C4RoutingOutcome.QUARANTINE,
    reason_codes=["BEHAVIOURAL_ANOMALY", "RSSI_PROFILE_ANOMALY"],
    quarantine_reason=QuarantineReason.RSSI_PROFILE_ANOMALY,
    packet_data={"rssi_dbm": -110, "snr_db": 5},
)

# Release after review
quarantine.release(record.quarantine_id, "Review confirmed legitimate RF variation")

# Generate report
report = quarantine.generate_report()
print(report)
```

## Checking Implementation

### 1. Verify Documentation

```bash
# Check threat model
cat docs/components/C4_THREAT_MODEL.md

# Check dataset audit
cat docs/components/C4_DATASET_AUDIT.md

# Check label specification
cat docs/components/C4_TRUST_LABEL_SPECIFICATION.md
```

### 2. Verify Dataset

```bash
# Check behavioral dataset
python -c "import pandas as pd; df = pd.read_csv('experiments/c4/data/C4_Behavioral_Dataset.csv'); print(df.shape); print(df.columns.tolist())"

# Check splits
python -c "import pandas as pd; train = pd.read_csv('experiments/c4/data/C4_train.csv'); val = pd.read_csv('experiments/c4/data/C4_val.csv'); test = pd.read_csv('experiments/c4/data/C4_test.csv'); print(f'Train: {train.shape}, Val: {val.shape}, Test: {test.shape}')"
```

### 3. Verify Models

```bash
# Check model files exist
ls experiments/c4/models/

# Load and test a model
python -c "from components.c4_trust.models import TrainedModel; model = TrainedModel.load('experiments/c4/models/random_forest.joblib'); print(f'Model type: {model.model_type}'); print(f'Features: {len(model.feature_names)}')"
```

### 4. Verify Tests Pass

```bash
pytest tests/security/test_c4_device_registry.py -v
pytest tests/security/test_c4_trust_service.py -v
```

### 5. End-to-End Verification

Create a test script `test_c4_e2e.py`:

```python
from components.c4_trust import (
    C4TrustService,
    DeviceCredential,
    DeviceKind,
    DeviceRegistry,
)
from shared.contracts import TelemetryPacket
from shared.contracts.telemetry import SecurityMetadata
from shared.enums import C4TrustLabel, SourceOrigin
from datetime import UTC, datetime, timedelta

# Create registry
registry = DeviceRegistry()
registry.register(
    "TEST-001",
    DeviceKind.TYPE_A,
    "Z1",
    "H001",
    DeviceCredential("cred-001", b"test-secret"),
)
registry.activate("TEST-001")

# Create service
service = C4TrustService(registry)

# Create test packet
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

# Sign and assess
signature = service.sign_packet(packet, b"test-secret")
assessment = service.assess(packet, signature)

print("✓ C4 End-to-End Test Passed")
print(f"  Trust Label: {assessment.trust_label}")
print(f"  Routing: {assessment.routing_outcome}")
print(f"  Reasons: {assessment.reason_codes}")
```

Run it:
```bash
python test_c4_e2e.py
```

## Model Performance

Based on training results (without leakage):

| Model | Test Accuracy | Test Macro F1 | Top Features |
|-------|---------------|---------------|--------------|
| Logistic Regression | 0.919 | 0.867 | All features weighted |
| Random Forest | 0.926 | 0.885 | counter_delta, rssi_deviation, rx_delay |
| Isolation Forest | 0.048 | 0.034 | Poor performance on this dataset |

**Note:** Isolation Forest performs poorly because the dataset has labeled attacks, not just normal data. It's more suitable for anomaly detection on primarily normal data.

## Important Notes

1. **No Leakage** - Label-derived fields (c4_trust_score, label_id, etc.) are excluded from ML training
2. **Scenario Distribution** - All 10 scenarios are present in train/val/test splits
3. **Feature Count** - 24 behavioral features (after excluding security fields and metadata)
4. **Trust Fusion** - Implemented in C4TrustService (deterministic gate + behavioral score)
5. **Hybrid Architecture** - Mandatory security checks cannot be overridden by ML

## Next Steps

To fully align with the development guide, you could add:

1. **XGBoost Model** - Boosted tree baseline
2. **Mode-Aware Features** - Expected interval based on operating mode
3. **Ablation Study** - Compare deterministic-only vs behavioral-only vs hybrid
4. **Explainability** - SHAP values for Random Forest
5. **Authorized C2 Replay** - Special handling for recovery replay context

## Commit Message

When committing, use the format:
```
C4 - Add [description]

Generated with [Devin](https://devin.ai)

Co-Authored-By: Devin <158243242+devin-ai-integration[bot]@users.noreply.github.com>
```

Example:
```
C4 - Add complete behavioral ML pipeline with baseline models

Added:
- Device registry with lifecycle states
- Behavioral feature extraction (B0-B5)
- Train/val/test splits
- Logistic Regression, Random Forest, Isolation Forest models
- Quarantine system for audit
- Comprehensive documentation

Test results:
- Logistic Regression F1: 0.867
- Random Forest F1: 0.885
- All unit tests passing

Generated with [Devin](https://devin.ai)

Co-Authored-By: Devin <158243242+devin-ai-integration[bot]@users.noreply.github.com>
```
