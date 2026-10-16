# C4 Complete Implementation Guide
## GeoNex — Trusted Telemetry Provenance, Device Authentication, and Security Verification

**Project:** GeoNex IoT Landslide Early-Warning System
**Module:** Component 4 (C4) — Trusted Telemetry Provenance
**Repository:** `J26-IT-331` | **Branch:** `feature/c4`
**Audit Date:** 2026-10-15
**Author:** IT4010 Research — Component 4

---

## Table of Contents

1. [Component 4 Research Problem and Purpose](#1-component-4-research-problem-and-purpose)
2. [Repository Structure and File Inventory](#2-repository-structure-and-file-inventory)
3. [Device Registry and Lifecycle Management](#3-device-registry-and-lifecycle-management)
4. [Cryptographic Authentication and Telemetry Integrity](#4-cryptographic-authentication-and-telemetry-integrity)
5. [Freshness Validation and Replay Protection](#5-freshness-validation-and-replay-protection)
6. [Behavioral Trust and Machine-Learning Assessment](#6-behavioral-trust-and-machine-learning-assessment)
7. [Trust Decision Engine and Fail-Closed Behavior](#7-trust-decision-engine-and-fail-closed-behavior)
8. [Telemetry Quarantine and Auditability](#8-telemetry-quarantine-and-auditability)
9. [Frontend Status](#9-frontend-status)
10. [End-to-End Telemetry Flow](#10-end-to-end-telemetry-flow)
11. [Database and Persistence](#11-database-and-persistence)
12. [Machine-Learning Dataset and Evaluation](#12-machine-learning-dataset-and-evaluation)
13. [Testing and Verification](#13-testing-and-verification)
14. [IoT Hardware and System Architecture](#14-iot-hardware-and-system-architecture)
15. [Architecture Diagrams](#15-architecture-diagrams)
16. [Security Limitations and Research Gaps](#16-security-limitations-and-research-gaps)
17. [PP1 and Viva Preparation](#17-pp1-and-viva-preparation)
18. [Implementation Status and Next Steps](#18-implementation-status-and-next-steps)
19. [Audit Summary](#19-audit-summary)

---

## 1. Component 4 Research Problem and Purpose

### Why C4 Exists

In a landslide early-warning system, every safety decision depends on telemetry data arriving from physical IoT sensors buried in unstable terrain. If even one forged or tampered data packet triggers an incorrect alert—or worse, suppresses a genuine warning—people's lives are at risk.

**The core research question C4 addresses:** *How do we know whether a telemetry packet arriving at the backend genuinely came from the registered, authorised device it claims to be from, was not modified in transit, is not a replay of an old packet, and is behaviorally consistent with what a legitimate sensor should produce?*

A packet that is correctly formatted (valid JSON, correct field types) is **not** necessarily trustworthy. An attacker can craft a valid packet from scratch. A compromised sensor can send manipulated data. A packet captured from the network can be replayed later to trigger false alerts. C4 exists to detect and reject all of these scenarios before any downstream component (C1 credibility scoring, C3 forecasting, the Decision Engine) consumes the data.

### What C4 Is Not

- **C4 is not the rainfall credibility component.** C1 examines whether sensor readings are scientifically plausible given the current environmental context. C4 examines whether the packet itself came from a legitimate, authorised device before C1 ever sees it.
- **C4 is not the temporal forecasting component.** C3 predicts future landslide risk from historical telemetry. C4 gates which telemetry is trustworthy enough to feed into C3.
- **C4 is not the Decision Engine.** The Decision Engine decides the system operating mode and escalation actions based on fused assessments from C1, C2, C3. C4 provides a security assessment label that the Decision Engine can use, but C4 does not decide mode changes or alerts.

### What C4 Implements

C4 performs five layers of security and behavioral validation:

| Layer | What is checked | Decision if failed |
|---|---|---|
| **Device Identity** | Is this device registered? Is it in the ACTIVE lifecycle state? | UNTRUSTED → REJECT |
| **Cryptographic Integrity** | Does the HMAC-SHA256 or ECDSA-SHA256 signature verify? | UNTRUSTED → REJECT |
| **Credential and Zone** | Does the credential ID match? Is the zone correct? Is the hub correct? | UNTRUSTED → REJECT |
| **Freshness and Replay** | Is the packet recent? Has this packet_id been seen before? | UNTRUSTED → REJECT |
| **Behavioral Assessment** | Does the packet's behavior match the ML model's learned normal patterns? | SUSPICIOUS → QUARANTINE |

All five layers run in sequence. A failure in any mandatory layer immediately marks the packet UNTRUSTED and rejects it. The ML behavioral layer can only escalate from TRUSTED to SUSPICIOUS—it can never rescue a packet that failed a mandatory security check.

---

## 2. Repository Structure and File Inventory

### Key Directory Layout

```
J26-IT-331/
├── components/
│   └── c4_trust/           ← All C4 backend logic
│       ├── service.py       ← Main trust assessment engine
│       ├── registry.py      ← Device registry and credential store
│       ├── pipeline.py      ← C4TelemetryGate (orchestrates assess + quarantine)
│       ├── quarantine.py    ← Quarantine manager (filesystem persistence)
│       ├── models.py        ← ML model classes (Random Forest, LR, Isolation Forest)
│       ├── features.py      ← Dataset feature extraction for training
│       ├── runtime_features.py ← Live packet feature extraction for inference
│       ├── integration.py   ← Factory to create C4TrustService with ML wired in
│       └── data_split.py    ← Scenario/device-aware dataset splitting
├── shared/
│   ├── contracts/
│   │   ├── c4_trust.py      ← C4TrustAssessment Pydantic schema
│   │   ├── telemetry.py     ← TelemetryPacket schema
│   │   └── common.py        ← Base contract model
│   ├── enums/domain.py      ← C4TrustLabel, C4RoutingOutcome, DeviceLifecycleState
│   └── simulation/
│       ├── c4_demo.py       ← Demo: builds a full C4 gate for demo telemetry
│       └── generator.py     ← Deterministic synthetic telemetry generator
├── database/
│   ├── models.py            ← SQLAlchemy ORM: TelemetryPacketRecord, SensorObservationRecord
│   └── migrations/versions/
│       ├── 70edc0f1d309_create_initial_telemetry_tables.py
│       └── b7c2e9a41d6f_add_behavioral_telemetry_fields.py
├── experiments/c4/
│   ├── data/                ← C4_SPLIT_REVIEW_NOTES.md, C4 split CSVs
│   ├── models/              ← random_forest_corrected.joblib (trained artifact)
│   └── plots/               ← SHAP summary and force plots (PNG)
├── quarantine/c4/           ← Live quarantine JSON records (24 files)
├── scripts/                 ← Training, audit, retrain, explain scripts
└── tests/
    ├── security/            ← Device registry, ECDSA, trust service tests
    ├── unit/test_c4_runtime_features.py
    ├── unit/c4/test_c4_ml_data.py
    ├── integration/         ← Simulation gate, persistence tests
    └── test_c4_e2e.py       ← End-to-end gate and quarantine test
```

### File Inventory

| File Path | Responsibility | Key Classes / Functions | Status |
|---|---|---|---|
| `components/c4_trust/service.py` | Core trust assessment engine | `C4TrustService`, `RecoveryContext`, `sign_packet`, `sign_packet_ecdsa`, `assess` | Implemented and verified |
| `components/c4_trust/registry.py` | Device registry and credential management | `DeviceRegistry`, `DeviceRecord`, `DeviceCredential`, `DeviceKind`, `create_test_registry` | Implemented and verified |
| `components/c4_trust/pipeline.py` | Gate orchestrating assess + quarantine | `C4TelemetryGate`, `C4GateResult` | Implemented and verified |
| `components/c4_trust/quarantine.py` | Quarantine record management | `QuarantineManager`, `QuarantineRecord`, `QuarantineReason` | Implemented and verified |
| `components/c4_trust/models.py` | ML model training and inference containers | `BaselineModel`, `TrainedModel`, `C4BehavioralModelRunner`, `ModelType`, `ModelMetrics` | Implemented and verified |
| `components/c4_trust/features.py` | Dataset feature extraction for training | `FeatureExtractor`, `BehavioralFeatures`, `load_and_extract_features` | Implemented and verified |
| `components/c4_trust/runtime_features.py` | Live packet feature extraction | `RuntimeFeatureAdapter`, `DeviceHistory`, `FeatureError`, `C4_MODEL_FEATURE_SCHEMA` | Implemented and verified |
| `components/c4_trust/integration.py` | Factory: wire ML into C4TrustService | `create_c4_service_with_behavioral_ml`, `create_c4_service_deterministic_only` | Implemented and verified |
| `components/c4_trust/data_split.py` | Device-aware dataset splitting | `ScenarioAwareSplitter`, `create_c4_splits` | Implemented and verified |
| `shared/contracts/c4_trust.py` | C4TrustAssessment Pydantic model | `C4TrustAssessment` | Implemented and verified |
| `shared/contracts/telemetry.py` | TelemetryPacket, DeviceHealth, TransportMetadata, SecurityMetadata | All contract models | Implemented and verified |
| `shared/enums/domain.py` | All shared domain enums | `C4TrustLabel`, `C4RoutingOutcome`, `DeviceLifecycleState` | Implemented and verified |
| `shared/simulation/c4_demo.py` | Demo C4 gate with HMAC signing | `build_demo_c4_gate`, `prepare_and_sign_demo_packet` | Implemented but deterministic-only (no ML) |
| `shared/simulation/generator.py` | Synthetic telemetry generation | `generate_baseline_packets`, `SimulationConfig` | Implemented and verified |
| `database/models.py` | ORM models for PostgreSQL persistence | `TelemetryPacketRecord`, `SensorObservationRecord` | Implemented but not fully tested end-to-end |
| `database/migrations/versions/b7c2e9a41d6f_add_behavioral_telemetry_fields.py` | Adds `tx_interval_s`, `freshness_status` columns | Migration upgrade/downgrade | Implemented |
| `experiments/c4/models/random_forest_corrected.joblib` | Trained Random Forest artifact | `TrainedModel` serialised by joblib | Implemented (trained 2026-10-13) |
| `tests/security/test_c4_device_registry.py` | Device registry unit tests | 37+ test functions | Implemented and verified (all pass) |
| `tests/security/test_c4_ecdsa_signatures.py` | ECDSA and HMAC signature tests | 13 test functions | Implemented and verified (all pass) |
| `tests/security/test_c4_trust_service.py` | Full trust service scenario tests | 30+ test functions | Implemented and verified (all pass) |
| `tests/unit/test_c4_runtime_features.py` | Runtime feature extraction tests | 16 tests + 4 skipped (Pydantic layer) | Implemented and verified |
| `tests/unit/c4/test_c4_ml_data.py` | ML data pipeline and model tests | 30+ test functions | Implemented and verified |
| `test_c4_e2e.py` | End-to-end gate + quarantine tests | 6 test functions | Implemented and verified |
| `scripts/retrain_c4_corrected.py` | Retrains RF with corrected features | Standalone script | Implemented |
| `scripts/train_c4_baselines.py` | Trains LR, RF, IF baselines | Standalone script | Implemented |
| `scripts/explain_c4_model.py` | SHAP explainability | Standalone script | Implemented |
| `docs/components/C4_DEVELOPMENT_GUIDE.md` | Architecture documentation | — | Implemented |
| `docs/components/C4_THREAT_MODEL.md` | Threat model documentation | — | Implemented |
| `docs/components/C4_TRUST_LABEL_SPECIFICATION.md` | Trust label semantics | — | Implemented |
| `quarantine/c4/` | Live quarantine records (24 JSON files) | — | Implemented and active |
| `components/c4_trust/__init__.py` | Public exports for c4_trust package | All main classes | Implemented |
| No frontend exists | C4 frontend | — | **Not implemented** |

---

## 3. Device Registry and Lifecycle Management

### Overview

The Device Registry (`components/c4_trust/registry.py`) is a Python in-memory data store that tracks every GeoNex IoT sensor device and controls whether telemetry from that device is eligible for trust assessment. There is no separate database table for the registry in the current implementation; it is re-initialised in memory at service startup using the factory pattern.

### Device Kinds

```python
class DeviceKind(StrEnum):
    TYPE_A = "type_a"    # Primary environmental sensor
    TYPE_B = "type_b"    # Secondary sensor type
    BACKUP = "backup"    # Backup/failover sensor
```

### Lifecycle States

The five states come from `shared/enums/domain.py`:

| State | Meaning | Can send accepted telemetry |
|---|---|---|
| `PROVISIONED` | Registered but not yet activated | No — UNTRUSTED |
| `ACTIVE` | Fully operational | Yes — eligible for trust assessment |
| `SUSPENDED` | Temporarily halted | No — UNTRUSTED |
| `REVOKED` | Security-revoked, permanently stopped | No — UNTRUSTED |
| `RETIRED` | Decommissioned | No — UNTRUSTED |

Only a device in the `ACTIVE` state will pass the device lifecycle check in `C4TrustService.assess()`. Any other state causes the assessment to fail immediately with `DEVICE_NOT_ACTIVE` in the reason codes.

### Device Record Structure

```python
@dataclass
class DeviceRecord:
    device_id: str                             # Unique device identifier
    device_kind: DeviceKind                    # TYPE_A, TYPE_B, or BACKUP
    zone_id: str                               # Registered deployment zone
    hub_id: str                                # Registered gateway hub
    lifecycle_state: DeviceLifecycleState      # Current state (default: PROVISIONED)
    credential: DeviceCredential | None        # Security credential
    firmware_hash: str | None                  # Expected firmware hash
    config_hash: str | None                    # Expected configuration hash
    approved_firmware: bool                    # Whether firmware approval is required and set
    approved_config: bool                      # Whether config approval is required and set
    registered_at: datetime
    last_updated: datetime
    metadata: dict[str, Any]
```

### Device Credential Structure

```python
@dataclass(frozen=True)
class DeviceCredential:
    credential_id: str             # Unique credential identifier
    secret: bytes                  # HMAC-SHA256 secret key
    signature_algorithm: str       # "hmac-sha256" (default) or "ecdsa-sha256"
    public_key_pem: bytes | None   # EC public key PEM for ECDSA (None for HMAC)
    issued_at: datetime | None     # Credential validity start
    expires_at: datetime | None    # Credential expiry time
```

### DeviceRegistry Methods

| Method | Purpose | Side effects |
|---|---|---|
| `register(...)` | Register a new device. Raises `ValueError` if device_id already exists. | Creates `DeviceRecord` with `PROVISIONED` state |
| `activate(device_id)` | Move from `PROVISIONED` or `SUSPENDED` to `ACTIVE` | Updates `lifecycle_state` and `last_updated` |
| `suspend(device_id)` | Move from `PROVISIONED` or `ACTIVE` to `SUSPENDED` | Updates state |
| `revoke(device_id)` | Move to `REVOKED` (any state). Permanent for security incidents. | Updates state |
| `retire(device_id)` | Move to `RETIRED` (decommissioned). | Updates state |
| `is_active(device_id)` | Returns `True` only if state is exactly `ACTIVE` | Read-only |
| `is_registered(device_id)` | Returns `True` if registered and not REVOKED or RETIRED | Read-only |
| `update_credential(device_id, credential)` | Replace device credential | Updates credential field |
| `approve_firmware(device_id, firmware_hash)` | Approve a specific firmware version | Sets `firmware_hash` and `approved_firmware=True` |
| `approve_config(device_id, config_hash)` | Approve a specific configuration | Sets `config_hash` and `approved_config=True` |
| `list_devices(zone_id, lifecycle_state, device_kind)` | Filter and list devices | Read-only |
| `count_by_state()` | Returns count per lifecycle state | Read-only |

### Zone and Hub Enforcement

When a `DeviceRegistry` is used (as opposed to a simple credential dictionary), the trust service also verifies:
- **ZONE_MISMATCH**: The `packet.zone_id` must match `device_record.zone_id`.
- **HUB_MISMATCH**: The `packet.transport.gateway_id` must match `device_record.hub_id`.
- **HUB_ID_MISSING**: If the packet's transport carries no gateway_id, this is treated as an unknown (not a hard failure).

These checks prevent a device from claiming to be in a zone or using a hub it is not registered to.

### Firmware and Configuration Approval

If `require_firmware_approval=True` is set on the trust service:
- The registry must have `approved_firmware=True` and a stored `firmware_hash`.
- The incoming packet's `security.firmware_hash` must match the registry's stored hash.
- Mismatches generate `FIRMWARE_UNAPPROVED` (hard failure). Missing evidence generates `FIRMWARE_EVIDENCE_MISSING` (unknown).

Similarly for `require_config_approval=True`.

> **Current state:** Firmware and config approval are implemented and tested but are disabled by default (`require_firmware_approval=False`, `require_config_approval=False`). The demo configuration (`c4_demo.py`) uses `allow_deterministic_only=True` and does not enable these optional checks.

---

## 4. Cryptographic Authentication and Telemetry Integrity

### Purpose

Cryptographic authentication proves that a telemetry packet was produced by a device holding a specific secret key. It also proves that the packet was not modified in transit, because any modification to any field changes the digest and makes signature verification fail.

### What is Signed

The canonical packet is the full JSON representation of the `TelemetryPacket` Pydantic model, serialised with `sort_keys=True, separators=(",",":")`, UTF-8 encoded. This means **every field in the packet is included in the integrity check**. If even one field is changed after signing, verification fails.

```python
@staticmethod
def _canonical_packet(packet: TelemetryPacket) -> bytes:
    payload = packet.model_dump(mode="json")
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
```

### HMAC-SHA256 (Default Algorithm)

When `credential.signature_algorithm == "hmac-sha256"`:

- **Signing:** `hmac.new(secret, canonical_packet, hashlib.sha256).hexdigest()`
- **Verification:** `hmac.compare_digest(expected, signature.lower())` — constant-time comparison to prevent timing attacks.
- The `secret` is a byte string stored in the `DeviceCredential`.
- This is symmetric: both the device and the server hold the same secret. It proves the packet came from someone with access to the secret, but does not provide non-repudiation.

### ECDSA-SHA256 (Asymmetric Alternative)

When `credential.signature_algorithm == "ecdsa-sha256"`:

- **Signing:** `private_key.sign(canonical_packet, ec.ECDSA(hashes.SHA256()))`. The result is hex-encoded.
- **Verification:** The server loads the EC public key PEM stored in `DeviceCredential.public_key_pem`, then calls `public_key.verify(signature_bytes, canonical_packet, ec.ECDSA(hashes.SHA256()))`.
- Uses the `cryptography` Python library (≥43,<47).
- The curve used in tests is `SECP256R1` (P-256), which is a NIST standard curve.
- ECDSA is asymmetric: the device holds the private key, the server holds only the public key. This provides non-repudiation.
- If the public key PEM is missing, malformed, or is not an EC key (e.g., RSA), the result is `SIGNATURE_UNVERIFIABLE` (UNKNOWN), **not** acceptance.

### Important Security Properties

1. **Algorithm isolation:** An ECDSA credential never silently falls back to HMAC. If the algorithm is `ecdsa-sha256` but the public key is missing, the result is UNKNOWN, not acceptance.
2. **Unknown algorithms:** Any `signature_algorithm` value other than `hmac-sha256` or `ecdsa-sha256` yields `SIGNATURE_UNVERIFIABLE` (UNKNOWN/SECURITY_REVIEW). This is fail-safe.
3. **Malformed signatures:** Invalid hex, invalid DER encoding, or truncated ECDSA signatures are caught and result in `INTEGRITY_INVALID` (UNTRUSTED/REJECT), not an unhandled exception.
4. **Tampered packets:** Any change to any field after signing causes verification failure → `INTEGRITY_INVALID`.
5. **Wrong key pair:** Signing with private key A but verifying with public key B correctly fails → `INTEGRITY_INVALID`.

> **Hardware note:** The implementation is entirely software-based. No ATECC608A or hardware secure element is integrated. The private key exists as a Python object (`ec.EllipticCurvePrivateKey`) or as a byte secret in memory. In a production deployment, the private key should reside in a hardware security module or secure element on the device, and the signing should happen on-device. This is a known limitation documented under Security Gaps.

---

## 5. Freshness Validation and Replay Protection

### Why Both are Needed

- **Freshness validation** ensures a packet is recent. An attacker who stores a legitimate old packet and submits it later cannot deceive the system even with a valid signature, because the timestamp falls outside the allowed window.
- **Replay protection** prevents the exact same packet from being submitted twice. Even if a packet is fresh enough to pass the timestamp check (e.g., submitted one second after capture), submitting the same `packet_id` a second time is caught.

These are complementary: freshness catches stale replays; replay detection catches duplicate-submission attacks within the freshness window.

### Freshness Configuration

| Parameter | Default | Source |
|---|---|---|
| `max_age_seconds` | `30.0` | `C4TrustService.__init__` |
| `future_tolerance_seconds` | `5.0` | `C4TrustService.__init__` |

- A packet is **fresh** if: `observed_at` is within the past 30 seconds relative to assessment time.
- A packet with `observed_at` more than 5 seconds in the future is rejected as `TIMESTAMP_IN_FUTURE`.
- A packet with `observed_at` more than 30 seconds in the past is rejected as `FRESHNESS_EXPIRED`.
- A naive (timezone-unaware) timestamp on a packet results in `TIMESTAMP_UNVERIFIABLE` (UNKNOWN).

> **Note:** The runtime integration summary mentions a "30-second soft threshold and 300-second hard threshold." After inspecting the actual code, the implementation uses only `max_age_seconds=30` as a single freshness window. There is no separate 300-second hard threshold in the current source. The demo configuration uses `max_age_seconds=30`.

### Replay Detection

The trust service maintains two in-memory data structures:

```python
self._seen_packets: set[tuple[str, str]]   # {(device_id, packet_id)}
self._last_sequence: dict[tuple[str, str | None], int]  # {(device_id, boot_id): last_seq_no}
```

**Packet-ID replay detection:**
- The `(device_id, packet_id)` tuple is added to `_seen_packets` after a successful first assessment.
- If the same packet is submitted again, `REPLAY_DETECTED` is added to failures → UNTRUSTED.

**Sequence-number replay detection:**
- Each device+boot_id pair tracks the highest seen `sequence_no`.
- A packet with `sequence_no <= previous` (with the same boot_id) triggers `SEQUENCE_REPLAY_DETECTED` → UNTRUSTED.
- This catches attackers injecting older packets with valid signatures but out-of-order sequence numbers.

**Sequence evidence requirement:**
- If `require_sequence=True` (default) and the packet has no `boot_id` or `sequence_no`, the result is `SEQUENCE_EVIDENCE_MISSING` (UNKNOWN/SECURITY_REVIEW).

**Thread safety:**
- All access to `_seen_packets` and `_last_sequence` is protected by a `threading.Lock()`.

**State persistence:**
- The replay state is **in-memory only** and lost on service restart. This is a documented limitation.
- After a restart, the same packet can be replayed for new packets until the `_seen_packets` set is repopulated.

### Authorized Recovery Replay

C4 supports a controlled exception for C2 recovery scenarios (e.g., replaying buffered packets from SD-card after a connectivity outage):

```python
context = service.create_recovery_context(
    recovery_request_id="RECOVERY-1",
    authorized_device_id="GNX-DEVICE-001",
    authorized_start_time=...,
    authorized_end_time=...,
)
result = service.assess(packet, signature, recovery_request_id="RECOVERY-1")
```

When an active recovery context exists, freshness expiry is bypassed for packets within the authorized time window, and replay detection is also bypassed. The reason code `AUTHORIZED_REPLAY_FRESHNESS_EXCEPTION` is recorded. The recovery context can be revoked by calling `service.revoke_recovery_context("RECOVERY-1")`.

---

## 6. Behavioral Trust and Machine-Learning Assessment

### Overview

After all mandatory security checks pass (identity, integrity, freshness, replay), C4 optionally calls a **behavioral scorer** — a trained ML model that assesses whether the packet's behavioral features (transmission timing, radio quality, device health) are consistent with legitimate sensor operation.

The behavioral scorer is optional. If no scorer is configured, the service can operate in **deterministic-only mode** (`allow_deterministic_only=True`), where trusted packets are accepted without ML scoring.

### Feature Schema (18 features)

All features are defined in `C4_MODEL_FEATURE_SCHEMA` in `components/c4_trust/runtime_features.py`:

| Feature | Source | Group |
|---|---|---|
| `tx_interval_s` | `packet.tx_interval_s` | B0 — Timing |
| `rx_delay_s` | `(packet.received_at - packet.observed_at).total_seconds()` | B0 — Timing |
| `freshness_status_encoded` | `{"fresh":0, "delayed":1, "stale":2}[packet.freshness_status]` | B0 — Timing |
| `rssi_dbm` | `packet.transport.rssi_dbm` | B1 — Radio |
| `rssi_deviation_db` | `rssi_dbm - rolling_mean(device rssi history)` | B1 — Radio |
| `snr_db` | `packet.transport.snr_db` | B1 — Radio |
| `retry_count` | `packet.transport.retry_count` | B1 — Radio |
| `packet_size_bytes` | JSON serialised size of the full packet | B2 — Packet |
| `battery_pct` | `packet.device_health.battery_pct` | B3 — Health |
| `battery_voltage_v` | `packet.device_health.battery_voltage` | B3 — Health |
| `current_ma` | `packet.device_health.supply_current` | B3 — Health |
| `reboot_count_24h` | `packet.device_health.reboot_count_24h` | B3 — Health |
| `sensor_fault_flag` | `1 if packet.device_health.sensor_fault_flag else 0` | B3 — Health |
| `rolling_interval_mean` | Mean of last 10 tx intervals for this device | B5 — Historical |
| `rolling_interval_std` | Std of last 10 tx intervals for this device | B5 — Historical |
| `rolling_rssi_mean` | Mean of last 10 RSSI values for this device | B5 — Historical |
| `rolling_rssi_std` | Std of last 10 RSSI values for this device | B5 — Historical |
| `rolling_retry_mean` | Mean of last 10 retry counts for this device | B5 — Historical |

Features **intentionally excluded** from the model input (to prevent label leakage):
`cert_registered`, `channel_auth_ok`, `signature_valid`, `attestation_passed`, `firmware_approved`, `config_hash_match`, `payload_hash_match`, `trust_label`, `is_malicious`, `c4_decision`, `reason_code`, and all metadata fields.

### RuntimeFeatureAdapter (`runtime_features.py`)

This class extracts the 18 features from a live `TelemetryPacket` for real-time inference.

**Key behaviours:**
- **Fail-closed:** Any missing required feature raises `FeatureError`, which causes the behavioral scorer to return `None`, which causes the assessment to return UNKNOWN/SECURITY_REVIEW. The system never silently defaults to zero for a missing required feature.
- **Per-device history:** Each device maintains a `DeviceHistory` object with bounded `deque` structures (default window=10). History is isolated between devices.
- **History is in-memory:** Lost on service restart. Initial rolling features start at 0.0 until the window fills.
- **Packet size:** Calculated dynamically from the JSON-serialised packet at inference time.
- **RSSI deviation:** Calculated as deviation from the device's rolling RSSI mean. For the first packet, deviation is 0.0.
- **Freshness encoding:** `"fresh"→0`, `"delayed"→1`, `"stale"→2`. A `None` freshness_status raises `FeatureError` — it is never assumed to be "fresh".

### ML Models: Roles and Usage

Three model types are implemented in `components/c4_trust/models.py`. Their runtime roles differ significantly:

#### Random Forest (Production Inference Model)

- **Class:** `BaselineModel(model_type=ModelType.RANDOM_FOREST)`
- **Artifact:** `experiments/c4/models/random_forest_corrected.joblib`
- **Runtime role:** The **only model used for production trust scoring**. It is the classifier whose output becomes the behavioral anomaly score.
- **No feature scaling:** Random Forest does not require a `StandardScaler` (`scaler=None`).
- **Hyperparameters:** `n_estimators=100`, `random_state=42`, `n_jobs=-1`.
- **Labels:** `Trusted`, `Suspicious`, `Untrusted` (3-class classification).
- **Score derivation:** `behavioural_anomaly_score = 1.0 - P(Trusted)`. A score close to 0.0 means the model is confident the packet is normal; a score close to 1.0 means the model finds it anomalous.
- **Threshold:** If `score >= 0.7` (configurable `suspicious_score_threshold`), the packet is classified as SUSPICIOUS/QUARANTINE. Otherwise TRUSTED/ACCEPT.

#### Logistic Regression (Baseline Comparison — Not Used at Runtime)

- **Class:** `BaselineModel(model_type=ModelType.LOGISTIC_REGRESSION)`
- **Runtime role:** **Not used for production inference.** Used in `scripts/train_c4_baselines.py` as a simpler baseline to compare against Random Forest.
- **Feature scaling:** Uses `StandardScaler` (required for LR).
- **Hyperparameters:** `max_iter=1000`, `random_state=42`.
- **Labels:** Same 3-class classification.

#### Isolation Forest (Anomaly Detection — Not Used at Runtime)

- **Class:** `BaselineModel(model_type=ModelType.ISOLATION_FOREST)`
- **Runtime role:** **Cannot be used for production trust-score fusion.** Isolation Forest has no calibrated class probabilities. `predict_proba` raises `ModelSchemaError`.
- **`C4BehavioralModelRunner` explicitly rejects Isolation Forest** at construction: `"Isolation Forest is not calibrated for C4 trust-score fusion"`.
- **Training role:** Used in baseline experiments to detect anomalies as unsupervised outlier detection. Fit on training features only (no labels used). Maps `predict=1` (inlier) → `Trusted`; `predict=-1` (outlier) → `Suspicious`.
- **Hyperparameters:** `n_estimators=100`, `contamination=0.1`, `random_state=42`.

> **Summary:** Only the Random Forest (`random_forest_corrected.joblib`) is used at runtime. Logistic Regression and Isolation Forest are training/evaluation baselines.

### C4BehavioralModelRunner (`models.py`)

This is the runtime inference wrapper around a loaded `TrainedModel`:

```python
runner = C4BehavioralModelRunner.load(
    path=model_path,
    expected_feature_names=C4_MODEL_FEATURE_SCHEMA,
    feature_builder=feature_builder,
)
score = runner(packet)  # Returns float [0.0, 1.0]
```

- **Schema validation:** At load time, the artifact's `feature_names` must exactly match `C4_MODEL_FEATURE_SCHEMA` in order and content. A mismatch raises `ModelSchemaError`.
- **Runtime scoring:** Calls `feature_builder(packet)` to get a one-row DataFrame, then calls `model.behavioural_anomaly_score()` to get `1.0 - P(Trusted)`.
- **Error isolation:** Any exception during scoring propagates as `ModelSchemaError`, which the integration factory catches and converts to `score=None` → UNKNOWN.

### Integration Factory (`integration.py`)

`create_c4_service_with_behavioral_ml()` wires everything together:

1. Creates a `RuntimeFeatureAdapter` with the configured `history_window`.
2. Wraps the feature adapter in a `feature_builder` closure that translates `FeatureError` to `ModelSchemaError`.
3. Loads the model from disk with schema validation via `C4BehavioralModelRunner.load()`.
4. Creates a `behavioural_scorer` closure that catches all exceptions and returns `None` on failure.
5. Passes `behavioural_scorer` to `C4TrustService(...)`.

If the model file does not exist or has an incompatible schema, the factory raises `FileNotFoundError` or `ModelSchemaError` at startup — the service does not start with a broken model.

---

## 7. Trust Decision Engine and Fail-Closed Behavior

### Check Order in `C4TrustService.assess()`

All checks run in this sequence per packet:

```
1. Device registry lookup  → DEVICE_UNKNOWN (fail) or proceed
2. Device lifecycle state  → DEVICE_NOT_ACTIVE (fail) or proceed
3. Zone validation         → ZONE_MISMATCH (fail) or ZONE_VALID
4. Hub/gateway validation  → HUB_MISMATCH (fail) or HUB_VALID or HUB_ID_MISSING (unknown)
5. Firmware approval check → FIRMWARE_UNAPPROVED (fail) or FIRMWARE_EVIDENCE_MISSING (unknown) or FIRMWARE_VALID
6. Config approval check   → CONFIG_MISMATCH (fail) or CONFIG_EVIDENCE_MISSING (unknown) or CONFIG_VALID
7. Credential check        → CREDENTIAL_NOT_CONFIGURED (unknown) or proceed
8. Credential ID match     → CREDENTIAL_ID_MISMATCH (fail) or CREDENTIAL_ID_MISSING (unknown) or CREDENTIAL_ID_VALID
9. Credential validity window → CREDENTIAL_NOT_YET_VALID (fail) or CREDENTIAL_EXPIRED (fail) or CREDENTIAL_VALID
10. Signature verification → INTEGRITY_INVALID (fail) or SIGNATURE_MISSING (unknown) or SIGNATURE_UNVERIFIABLE (unknown) or INTEGRITY_VALID
11. Attestation verification → ATTESTATION_INVALID (fail) or ATTESTATION_UNVERIFIED (unknown) or ATTESTATION_VALID
12. Provenance verification → PROVENANCE_INVALID (fail) or PROVENANCE_UNVERIFIED (unknown) or PROVENANCE_VALID
13. Timestamp freshness    → TIMESTAMP_IN_FUTURE (fail) or TIMESTAMP_UNVERIFIABLE (unknown) or FRESHNESS_EXPIRED (fail) or FRESHNESS_VALID
14. Replay detection        → REPLAY_DETECTED (fail) or SEQUENCE_REPLAY_DETECTED (fail) or REPLAY_CHECK_VALID
```

**Then, only if all 14 checks produce no failures and no unknowns:**

```
15. Behavioral ML scoring  → score=None (unknown) or score >= threshold (SUSPICIOUS) or score < threshold (TRUSTED)
```

### Trust Label Decision Table

| Failures | Unknowns | ML Result | Trust Label | Routing |
|---|---|---|---|---|
| ≥1 failure | any | any | `UNTRUSTED` | `REJECT` |
| 0 | ≥1 unknown | any | `UNKNOWN` | `SECURITY_REVIEW` |
| 0 | 0 | score unavailable, `allow_deterministic_only=False` | `UNKNOWN` | `SECURITY_REVIEW` |
| 0 | 0 | score unavailable, `allow_deterministic_only=True` | `TRUSTED` | `ACCEPT` |
| 0 | 0 | `score >= 0.7` | `SUSPICIOUS` | `QUARANTINE` |
| 0 | 0 | `score < 0.7` | `TRUSTED` | `ACCEPT` |

### Routing Outcomes

| `C4RoutingOutcome` | Meaning |
|---|---|
| `ACCEPT` | Packet is trusted. Forward to C1 credibility scoring. |
| `REJECT` | Packet has failed a mandatory security check. Discard. |
| `QUARANTINE` | Packet is behaviorally suspicious. Store in quarantine for review. |
| `SECURITY_REVIEW` | Evidence was unavailable or ambiguous. Store for manual review. |

### Contract-Level Enforcement (`C4TrustAssessment.enforce_mandatory_security_override`)

The `C4TrustAssessment` Pydantic model includes a `@model_validator` that enforces these invariants at the contract level:

- A packet cannot be `TRUSTED` or `SUSPICIOUS` if `mandatory_security_pass=False`.
- A `TRUSTED` packet must use `ACCEPT` as the routing outcome.
- An `UNKNOWN` packet must use `SECURITY_REVIEW`.
- An `UNTRUSTED` packet cannot use `ACCEPT`.
- A `SUSPICIOUS` packet must use `QUARANTINE` or `SECURITY_REVIEW`.

These validators run every time a `C4TrustAssessment` is created. If the service logic somehow produced an inconsistent result, the Pydantic validator would raise a `ValueError` before the object is returned. This provides a contractual guarantee that complements the service-level logic.

### `C4TelemetryGate` (`pipeline.py`)

The gate is the primary orchestration layer that connects assessment to quarantine:

```python
gate = C4TelemetryGate(trust_service, quarantine_manager)
result = gate.process(packet, signature)
```

- If the result is `TRUSTED + mandatory_security_pass=True + ACCEPT`, the packet is returned as `eligible_packet` for downstream use (C1).
- For any other result (UNTRUSTED, UNKNOWN, SUSPICIOUS), the original packet is quarantined and `eligible_packet=None`.

The `C4GateResult` dataclass exposes `eligible_for_c1` as a boolean property. Only when this is `True` should downstream components consume the packet.

### `mandatory_security_pass` Field

This boolean in `C4TrustAssessment` is `True` only when both `failures` and `security_unknowns` are empty at the time of assessment. A `SUSPICIOUS` packet that passed all mandatory checks has `mandatory_security_pass=True`, which is correct — its suspicion is behavioral, not cryptographic.

---

## 8. Telemetry Quarantine and Auditability

### Why Quarantine Exists

Rejected or suspicious packets are not simply discarded. They are preserved in a quarantine store so that:
- Security incidents can be investigated.
- False positives (good packets incorrectly flagged) can be identified and released.
- Audit trails are maintained.
- Patterns of attack can be analysed across multiple quarantined packets.

### Default Storage Location

```python
# Default: J26-IT-331/quarantine/c4/
default_dir = Path(__file__).resolve().parents[2] / "quarantine" / "c4"
```

The `QuarantineManager` creates this directory if it does not exist. There are currently **24 quarantine JSON files** in `quarantine/c4/` from previous test runs.

### What is Stored

Each quarantine file is a JSON document named `Q_{12_hex_chars}.json` containing:

```json
{
  "quarantine_id": "Q_035c99398f19",
  "packet_id": "test-002",
  "device_id": "TEST-001",
  "trust_label": "SUSPICIOUS",
  "routing_outcome": "ACCEPT",
  "reason_codes": ["BEHAVIOURAL_ANOMALY"],
  "quarantine_reason": "BEHAVIOURAL_ANOMALY",
  "quarantined_at": "2026-10-12T23:55:31.675040+00:00",
  "packet_data": { ... },
  "assessment": { ... full C4TrustAssessment ... },
  "review_assessment": null,
  "reviewed_by": null,
  "released": true,
  "released_at": "2026-10-12T23:55:31.675502+00:00",
  "release_reason": "Review confirmed legitimate",
  "metadata": {}
}
```

Fields stored:
- **Full original packet data** (`packet_data`): preserved as-is for forensic use.
- **Full assessment object** (`assessment`): all reason codes, scores, trust label.
- **Quarantine reason**: one of `BEHAVIOURAL_ANOMALY`, `SECURITY_FAILURE`, `EVIDENCE_UNAVAILABLE`, `WEAK_SIGNAL`, `DEVICE_HEALTH_DEGRADED`, `CLOCK_DELAY`, `INTERVAL_ANOMALY`, `RSSI_PROFILE_ANOMALY`, `PATH_MISMATCH`, `CUSTOM`.
- **Release information**: whether the packet was later released, by whom, and with what justification.

### Atomic File Writing

The `QuarantineManager` uses Python's `tempfile.NamedTemporaryFile` + `os.replace()` for atomic writes. This prevents partial or corrupt JSON files from appearing on disk if the process crashes during a write.

### Quarantine Release Process

Releasing a quarantined packet requires:
1. A `release_authorizer` function to be configured (validates reviewer identity).
2. A `reviewer_id` that passes the authorizer.
3. A fresh `C4TrustAssessment` with `trust_label=TRUSTED`, `mandatory_security_pass=True`, and `routing_outcome=ACCEPT` — newer than the quarantine timestamp.

This prevents automated or unauthorized release. The release creates an updated record with both the original assessment and the review assessment stored.

### Loading Existing Records

On startup, `QuarantineManager` loads all existing JSON files from the quarantine directory. Files that fail to parse are tracked in `self._load_errors` (filename → error type) without modifying them — preserving evidence.

### Limitations

- **No access control on the quarantine directory.** Any process with filesystem access can read quarantine files. In production, the quarantine directory should be access-controlled.
- **No retention policy.** Quarantine records accumulate indefinitely. A production system would need a retention and archival policy.
- **In-memory index.** The `_records` dictionary is rebuilt at startup by loading all JSON files. For large deployments, this could be slow.
- **No database-backed quarantine.** Quarantine is filesystem-based, separate from the PostgreSQL database.

---

## 9. Frontend Status

> **There is no C4 frontend in the current repository.**

A `c4_frontend` directory was referenced in the `pyproject.toml` package list as `apps.api` and other app packages, but no frontend code exists for C4 specifically. The repository has `apps/api`, `apps/ingestion`, `apps/decision_engine`, and `apps/runtime_orchestrator` in the package registration, but these directories contain only `__init__.py` files (stub packages).

**What this means:**
- C4 has no web dashboard, form, table, or UI component.
- There is no browser-based way to submit telemetry, view trust assessments, or manage the quarantine.
- All interaction with C4 currently happens through:
  - **Python tests** (the main interface during development).
  - **Simulation scripts** (`shared/simulation/c4_demo.py`, `scripts/load_demo_simulation.py`).
  - **Direct Python API** (importing and calling `C4TelemetryGate.process()`).

**For PP1 presentation:** C4 can be demonstrated by running the test suite or by running the simulation scripts directly in a terminal. The quarantine JSON files in `quarantine/c4/` can be shown as evidence of the system working.

---

## 10. End-to-End Telemetry Flow

### Real Flow (Verified in Code)

```
1. Telemetry Packet Created
   └─ TelemetryPacket Pydantic object with all required fields
      ├─ packet_id, device_id, zone_id, boot_id, sequence_no
      ├─ observed_at, received_at, freshness_status, tx_interval_s
      ├─ measurements: [MeasurementEntry, ...]
      ├─ device_health: {battery_pct, battery_voltage, supply_current, reboot_count_24h, sensor_fault_flag}
      ├─ transport: {gateway_id, rssi_dbm, snr_db, retry_count}
      └─ security: {credential_id, integrity_present, firmware_hash?, config_hash?}

2. Signing (device-side, software-simulated)
   └─ C4TrustService.sign_packet(packet, secret)  [HMAC-SHA256]
   OR C4TrustService.sign_packet_ecdsa(packet, private_key)  [ECDSA-SHA256]
   └─ Returns hex-encoded signature string

3. Gateway → Backend (simulated, no real network layer implemented)
   └─ In tests: directly call gate.process(packet, signature)
   └─ In production intent: HTTP ingestion endpoint would receive packet+signature

4. C4TelemetryGate.process(packet, signature)
   └─ Calls C4TrustService.assess(packet, signature, now=...)

5. C4TrustService.assess() — Mandatory Security Checks
   ├─ Device registry lookup + lifecycle state
   ├─ Zone and hub validation
   ├─ Firmware and config approval (if configured)
   ├─ Credential ID validation and expiry
   ├─ Signature verification (HMAC or ECDSA)
   ├─ Attestation and provenance verification
   ├─ Timestamp freshness check
   └─ Replay and sequence-number detection

6. If any failure → UNTRUSTED/REJECT (skip steps 7-9)
   If any unknown → UNKNOWN/SECURITY_REVIEW (skip steps 7-9)
   If all pass → proceed to step 7

7. Behavioral ML Scoring (if ML mode is configured)
   ├─ RuntimeFeatureAdapter.extract_features(packet) → pd.DataFrame (1 row, 18 cols)
   │   ├─ Extracts and validates all 18 features
   │   ├─ Updates per-device rolling history
   │   └─ Raises FeatureError if any required feature is missing/invalid
   ├─ C4BehavioralModelRunner(packet) → float [0.0, 1.0]
   │   ├─ Calls feature_builder(packet)
   │   └─ Returns 1.0 - P(Trusted) from Random Forest
   └─ Score returned to trust service

8. Trust Label Decision
   ├─ score >= 0.7 → SUSPICIOUS / QUARANTINE
   └─ score < 0.7  → TRUSTED / ACCEPT
   (score=None with allow_deterministic_only=True → TRUSTED/ACCEPT)
   (score=None with allow_deterministic_only=False → UNKNOWN/SECURITY_REVIEW)

9. C4TrustAssessment Created
   └─ Assessment ID: "C4A_{uuid4().hex}"
   └─ trust_label, trust_score, mandatory_security_pass, reason_codes
   └─ behavioural_score, routing_outcome, model_version, security_policy_version
   └─ generated_at, packet_id, device_id

10. C4TelemetryGate Routes the Result
    ├─ TRUSTED + mandatory_security_pass=True + ACCEPT:
    │   └─ C4GateResult(eligible_packet=packet, quarantine_record=None)
    │   └─ eligible_for_c1=True → packet forwarded to C1 (or downstream)
    └─ Any other outcome:
        └─ QuarantineManager.quarantine(packet_id, device_id, trust_label, ...)
        └─ Saves JSON to quarantine/c4/Q_{id}.json
        └─ C4GateResult(eligible_packet=None, quarantine_record=record)
        └─ eligible_for_c1=False

11. Downstream (C1, C3, Decision Engine)
    └─ Receive only packets that passed step 10 with eligible_for_c1=True
    └─ C4TrustAssessment is available for logging and audit
```

### Stages That Are Synchronous vs. Planned

| Stage | Synchronous | Notes |
|---|---|---|
| Telemetry creation | Yes | Pydantic validates at object creation |
| Signing | Yes | In-process |
| Network transport | Not implemented | Simulated by direct function call |
| C4 assessment | Yes | All checks in a single `assess()` call |
| ML feature extraction | Yes | Synchronous in-process call |
| ML inference | Yes | Synchronous in-process call |
| Quarantine write | Yes | Atomic filesystem write |
| Database persistence | Partially implemented | SQLAlchemy models exist; persistence wiring not shown in current integration path |
| Frontend display | Not implemented | No frontend exists |

---

## 11. Database and Persistence

### Database Technology

- **Database:** PostgreSQL (via `psycopg[binary]` ≥3.2)
- **ORM:** SQLAlchemy ≥2.0
- **Migrations:** Alembic ≥1.14
- **Connection:** Configured in `shared/config/settings.py` via environment variables (not shown to avoid exposing credentials)

### Tables

#### `telemetry_packets`

Primary persistence table for normalized telemetry packets.

| Column | Type | Notes |
|---|---|---|
| `packet_id` | VARCHAR(128) PK | Unique packet identifier |
| `schema_version` | VARCHAR(32) | Protocol schema version |
| `device_id` | VARCHAR(128) | Sensor device identifier |
| `zone_id` | VARCHAR(128) | Deployment zone |
| `boot_id` | VARCHAR(128) nullable | Boot cycle identifier |
| `sequence_no` | BIGINT nullable | Packet sequence number (≥0) |
| `observed_at` | TIMESTAMP WITH TZ | When the sensor observed the reading |
| `received_at` | TIMESTAMP WITH TZ | When the gateway received the packet |
| `message_type` | VARCHAR(64) | e.g., "TELEMETRY" |
| `tx_interval_s` | FLOAT nullable | Transmission interval (added by migration b7c2e9a41d6f) |
| `freshness_status` | VARCHAR(16) nullable | "fresh", "delayed", or "stale" (added by migration b7c2e9a41d6f) |
| `measurements` | JSONB | Array of measurement entries |
| `device_health` | JSONB | Device health metrics |
| `transport` | JSONB | Radio transport metadata |
| `security` | JSONB | Non-secret security metadata |
| `source_origin` | VARCHAR(32) | "SIMULATED", "SYNTHETIC", etc. |
| `test_run_id` | VARCHAR(128) nullable | For test isolation |
| `correlation_id` | VARCHAR(128) nullable | Correlation across components |
| `stored_at` | TIMESTAMP WITH TZ | Database insertion time (auto) |

**Indexes:**
- `ix_telemetry_packets_zone_observed_at` (zone_id, observed_at)
- `ix_telemetry_packets_device_received_at` (device_id, received_at)

#### `sensor_observations`

Child table, one row per measurement extracted from a telemetry packet.

| Column | Type | Notes |
|---|---|---|
| `observation_id` | VARCHAR(128) PK | Unique observation ID |
| `packet_id` | FK → telemetry_packets | Parent packet |
| `zone_id`, `device_id`, `sensor_instance_id` | VARCHAR(128) | Sensor identification |
| `observed_at`, `received_at` | TIMESTAMP WITH TZ | Timestamps |
| `raw_value` | FLOAT nullable | Raw sensor value |
| `value` | FLOAT nullable | Processed/calibrated value |
| `unit` | VARCHAR(64) nullable | Unit of measurement |
| `calibration_version` | VARCHAR(128) nullable | Calibration applied |
| `source_origin` | VARCHAR(32) | Origin tag |
| `stored_at` | TIMESTAMP WITH TZ | Auto-generated |

**Constraint:** At least one of `raw_value` or `value` must be non-NULL.

### Migration History

| Revision ID | Description |
|---|---|
| `70edc0f1d309` | Initial migration — creates `telemetry_packets` and `sensor_observations` tables |
| `b7c2e9a41d6f` | Adds `tx_interval_s` (FLOAT) and `freshness_status` (VARCHAR(16)) to `telemetry_packets` |

### What is NOT Stored in the Database

- **C4TrustAssessment results** are not stored in any database table. There is no `c4_assessments` table.
- **Quarantine records** are stored as filesystem JSON, not in PostgreSQL.
- **Device registry records** are in-memory only, not persisted to the database.
- **ML model predictions / behavioral scores** are not persisted to the database.
- **Replay detection state** (`_seen_packets`, `_last_sequence`) is in-memory only.

### Missing Persistence Capabilities

This is a significant gap: the C4 assessment results, reason codes, and behavioral scores are computed per-packet but not written to any persistent store (database or otherwise). This means:
- There is no historical audit trail of trust assessments.
- Trend analysis (e.g., how often a device is SUSPICIOUS) is not possible without re-processing.
- Assessment results are only visible at runtime (in the returned object) and in quarantine files (for non-accepted packets).

---

## 12. Machine-Learning Dataset and Evaluation

### Dataset Overview

- **Primary dataset:** `C4_Behavioral_Dataset.csv` (referenced in scripts; actual file in `experiments/c4/data/`)
- **Total records:** 10,000 rows
- **Feature columns:** 62 columns in the full dataset (including metadata and security fields)
- **Behavioral feature columns:** 18 (see Section 6 for the list)
- **Target variable:** `trust_label` with three classes

### Label Classes

| Label | Meaning |
|---|---|
| `Trusted` | Packet originates from a legitimate, authorized device behaving normally |
| `Suspicious` | Packet may be from a legitimate device but exhibits anomalous behavioral patterns |
| `Untrusted` | Packet originates from an unauthorized, compromised, or malicious source |

### Label Distribution (Current Device-Held-Out Splits)

| Split | Trusted | Untrusted | Suspicious | Total |
|---|---|---|---|---|
| **Training** | 4,275 | 945 | 364 | 5,584 |
| **Validation** | 2,595 | 436 | 221 | 3,252 |
| **Testing** | 887 | 207 | 70 | 1,164 |

**Key observations:**
- The dataset is imbalanced: Trusted is the majority class.
- Suspicious is the rarest class, especially in test (70 samples).
- Class imbalance affects the model's ability to detect Untrusted packets.

### Dataset Splitting Strategy

The `ScenarioAwareSplitter` (in `data_split.py`) implements **device-held-out splitting**:
- All records from the same `device_id` go into the same split (train, val, or test).
- No device_id appears in more than one split.
- The splitter also verifies that all three classes appear in all splits.

**Why device-held-out splitting matters:**
- If a device's records appear in both train and test, the model might memorise device-specific patterns rather than learning generalizable behavioral signatures.
- Device-held-out splitting provides a more realistic evaluation of generalization to new/unseen devices.
- The backup splits (before device-aware splitting) had device overlap, which would inflate test accuracy.

### Corrected Model Training (`scripts/retrain_c4_corrected.py`)

The corrected retraining addressed these issues:
1. `tx_interval_s` was constant at 30.0 → now uses actual derived intervals.
2. `rssi_deviation_db` semantics were unclear → now deviation from device rolling mean.
3. Missing freshness was filled with 0 → now rows with missing freshness are removed.
4. Duplicate timestamps (5,505 rows) → grouped before rolling calculations.
5. Device leakage → device-aware splits (388/83/84 device groups).

### Model Performance (from `C4_RUNTIME_INTEGRATION_SUMMARY.md`)

> **Important:** These metrics were reported from the retraining run on 2026-10-13 using scikit-learn 1.9.0. They have not been independently re-verified in the current audit. The model artifact exists at `experiments/c4/models/random_forest_corrected.joblib`.

| Metric | Value |
|---|---|
| Test Accuracy | 88.89% |
| Macro F1 | 74.84% |
| F1 — Suspicious | 99.31% |
| F1 — Trusted | 93.50% |
| F1 — Untrusted | 31.72% |
| Untrusted Recall | 19.07% |

**Critical limitation:** The Untrusted recall is only 19.07%. This means the model misses approximately 81% of Untrusted behavioral patterns. The model is not reliable for detecting behaviorally untrusted packets. However, recall that the **mandatory deterministic security gate** (not the ML model) is the primary mechanism for detecting UNTRUSTED packets — ECDSA/HMAC failure, unknown device, revoked device, stale packet, replay, etc. The ML model's job is to catch *behavioral* anomalies that pass the cryptographic gate, not to replace it.

### SHAP Explainability

SHAP explainability plots exist in `experiments/c4/plots/`:
- `shap_bar.png` — global feature importance
- `shap_summary.png` — summary beeswarm plot
- `shap_force_example_1/2/3.png` — per-instance force plots

These were generated by `scripts/explain_c4_model.py`. The runtime integration summary mentions `rssi_deviation_db` has 6.63% SHAP importance, suggesting the deviation-from-rolling-mean semantics chosen at runtime are reasonable.

### Dataset Limitations

1. **Synthetic/simulated data.** The dataset was generated synthetically, not collected from physical GeoNex sensors. The behavioral patterns may not fully represent real-world sensor noise, environmental interference, or attack scenarios.
2. **Low Untrusted class representation.** The Untrusted class is minority and may not contain representative patterns for all attack types.
3. **RSSI deviation semantics.** The training-time definition of `rssi_deviation_db` could not be confirmed from the dataset generation code. The runtime implementation uses deviation from the device's rolling mean as the best interpretation.
4. **Scikit-learn version mismatch.** Model trained with sklearn 1.9.0; environment may have 1.9.1. Minor version mismatches are generally backward-compatible.

---

## 13. Testing and Verification

### Test Results (Actual Run — 2026-10-15)

**Command run:**
```bash
python -m pytest tests/security/ tests/unit/test_c4_runtime_features.py tests/unit/c4/ test_c4_e2e.py -v --tb=short
```

**Result:** ✅ **142 passed, 0 failed, 0 skipped** (completed in 24.22 seconds)

> Note: The runtime integration summary states "211 passed, 4 skipped" for the full test suite. The 142 count above covers only the C4-specific tests. Additional tests exist in `tests/contract/`, `tests/integration/`, and `tests/unit/` for shared infrastructure.

### C4 Test Groups

#### Security Tests (`tests/security/`)

| Test File | # Tests | Coverage |
|---|---|---|
| `test_c4_device_registry.py` | 37 | Device registration, lifecycle states, credential management, zone/hub lookup, firmware/config approval |
| `test_c4_ecdsa_signatures.py` | 13 | ECDSA signing/verification, tamper detection, wrong key, malformed PEM, malformed signature, algorithm isolation, HMAC compatibility |
| `test_c4_trust_service.py` | ~30 | Full trust assessment scenarios: valid packet, tampered packet, unknown device, missing credential, expired packet, future timestamp, replay, sequence replay, behavioral override prevention, SUSPENDED/REVOKED/RETIRED devices, zone mismatch, hub enforcement, firmware/config failures, credential validity window, behavioral scorer failures |

#### Unit Tests (`tests/unit/`)

| Test File | # Tests | Coverage |
|---|---|---|
| `test_c4_runtime_features.py` | 16 | Feature adapter initialization, schema constant, complete packet extraction, missing features (fail-closed), invalid freshness, RSSI deviation, rolling history, device isolation, clear history, service creation with missing model, deterministic-only service, ML override prevention |
| `c4/test_c4_ml_data.py` | ~35 | Feature exclusion (no label leakage), historical feature isolation, timestamp handling, model schema validation, model runner loading, Isolation Forest rejection, quarantine serialization/reload, quarantine release enforcement, C4TelemetryGate forwarding/quarantining, split generation and validation |

#### E2E Tests (`test_c4_e2e.py`)

| Test | Coverage |
|---|---|
| `test_device_registry` | Registry is_active check |
| `test_c4_trust_service` | Full assess call with HMAC, TRUSTED result |
| `test_c4_gate_forwards_only_verified_packets_and_quarantines_failures` | Gate forwards trusted, quarantines rejected; quarantine count verified |
| `test_quarantine` | Quarantine record creation and file persistence |
| `test_quarantine_release` | Authorized release with fresh TRUSTED assessment |
| `test_report_generation` | Quarantine statistics report |

### What the Tests Prove

- A valid, signed, fresh, unique packet from an active device is accepted (TRUSTED).
- A tampered packet is rejected with INTEGRITY_INVALID.
- An unknown device is rejected with DEVICE_UNKNOWN.
- A stale packet (60 seconds old) is rejected with FRESHNESS_EXPIRED.
- A future-timestamped packet is rejected with TIMESTAMP_IN_FUTURE.
- A duplicate packet is rejected with REPLAY_DETECTED.
- A duplicate sequence number is rejected with SEQUENCE_REPLAY_DETECTED.
- A high behavioral score (0.9) results in SUSPICIOUS/QUARANTINE.
- A high behavioral score cannot rescue a packet with a bad signature.
- A broken ML scorer causes UNKNOWN/SECURITY_REVIEW, not acceptance.
- A NaN score causes UNKNOWN/SECURITY_REVIEW.
- ECDSA signatures work correctly with EC key pairs.
- ECDSA credentials never fall back to HMAC.
- RSA keys are rejected for ECDSA credentials.
- Malformed signatures are rejected, not swallowed as exceptions.
- SUSPENDED, REVOKED, and RETIRED devices are rejected.
- Zone mismatch and hub mismatch are rejected.
- Firmware hash mismatch is rejected.
- Quarantine records are written atomically to disk.
- Quarantine release requires an authorized reviewer and a fresh TRUSTED assessment.

### What the Tests Do NOT Prove

- End-to-end network ingestion (no HTTP layer tested).
- Database persistence of telemetry or assessments.
- Frontend integration (no frontend exists).
- Real hardware device communication.
- ML model accuracy on real-world data (tests use mocked/synthetic models).
- Performance under load or concurrent multi-device scenarios.
- Replay state persistence across service restarts.

---

## 14. IoT Hardware and System Architecture

### GeoNex IoT Hardware Design (Intended)

The intended hardware architecture involves:
- **ESP32-S3** microcontrollers as sensor nodes
- **Ra-02 / SX1278** LoRa radio modules for long-range, low-power wireless transmission
- **Sensor pipe architecture:** Type-A pipes (primary), Type-B pipes (secondary), and Backup pipes
- **Sensor Hub / Gateway:** Aggregates multiple sensor pipes and forwards telemetry to the backend
- **Backend:** Python backend on a server/cloud

### What is Implemented vs. Simulated

| Function | Implementation Status |
|---|---|
| Telemetry packet schema (TelemetryPacket) | Implemented in Python (shared contracts) |
| HMAC-SHA256 signing | Implemented in Python (software only) |
| ECDSA-SHA256 signing | Implemented in Python (software only) |
| Device identity and credential management | Implemented in Python (in-memory) |
| Trust assessment logic | Implemented in Python |
| Behavioral ML inference | Implemented in Python |
| LoRa radio communication | Not implemented — no firmware code |
| ESP32-S3 firmware | Present in `firmware/` directory but details not audited |
| Gateway-to-backend communication | Not implemented (no HTTP ingestion endpoint) |
| ATECC608A hardware secure element | Not integrated — all crypto is software |
| Physical sensor calibration | Not implemented |
| Real-world deployment | Not tested |

### Firmware Directory

A `firmware/` directory exists with subdirectories `main_gateway/`, `sensor_hub/`, `type_a/`, `type_b/`, `backup_pipe/`, `common/`. These files were not audited in detail. Based on the project structure, they likely contain ESP32/Arduino firmware sketches, but whether they implement C4-compatible signing or credential management is not confirmed.

### Hardware Security Gap

The current implementation stores private keys as Python byte strings (`secret=b"..."`) or as `ec.EllipticCurvePrivateKey` objects in memory. In a production IoT system:
- Private keys should be stored in a hardware secure element (e.g., ATECC608A).
- Signing should happen on-device within the secure element.
- Keys should never leave the secure element in plaintext.

Without hardware-backed key storage, the security of the ECDSA implementation depends entirely on the security of the device's application memory — which is vulnerable to memory extraction attacks on physical hardware.

> **Research note for viva:** Explicitly state that ECDSA is implemented and verified in software. The integration with a hardware secure element (ATECC608A or similar) is the intended next step but has not been implemented. The software prototype proves the cryptographic protocol is correct; hardware integration proves it is physically secure.

---

## 15. Architecture Diagrams

### 1. Overall GeoNex System Architecture

```mermaid
flowchart TD
    subgraph IoT["IoT Field Hardware (Planned)"]
        SA["Type-A Sensor\nESP32-S3 + LoRa"]
        SB["Type-B Sensor\nESP32-S3 + LoRa"]
        BK["Backup Sensor"]
        GW["Sensor Hub / Gateway"]
        SA -->|LoRa| GW
        SB -->|LoRa| GW
        BK -->|LoRa| GW
    end

    subgraph Backend["GeoNex Backend (Python)"]
        ING["Ingestion Layer\n(apps/ingestion — stub)"]
        C4["C4 Trust Gate\nDevice Auth + Integrity\n+ Freshness + Replay + ML"]
        C1["C1 Credibility\nRainfall Anomaly Detection"]
        C2["C2 Diagnostics\nDevice Health Analysis"]
        C3["C3 Forecasting\nTemporal Risk Prediction"]
        DE["Decision Engine\nMode + Alert Management"]
        DB["PostgreSQL\nTelemetry + Observations"]
        QU["Quarantine Store\nFilesystem JSON"]
    end

    GW -->|"HTTP/MQTT\n(planned)"| ING
    ING --> C4
    C4 -->|"TRUSTED + ACCEPT"| C1
    C4 -->|"UNTRUSTED/SUSPICIOUS"| QU
    C1 --> DE
    C2 --> DE
    C3 --> DE
    DE --> C1
    C1 --> DB
    DB -.->|"Historical data"| C3

    style C4 fill:#4CAF50,color:#fff
    style QU fill:#FF9800,color:#fff
    style IoT fill:#E3F2FD
    style Backend fill:#F3E5F5
```

### 2. C4 Backend Module Relationships

```mermaid
flowchart LR
    subgraph c4_trust["components/c4_trust/"]
        SVC["service.py\nC4TrustService\nassess()"]
        REG["registry.py\nDeviceRegistry\nDeviceCredential"]
        PIP["pipeline.py\nC4TelemetryGate\nprocess()"]
        QUA["quarantine.py\nQuarantineManager\nQuarantineRecord"]
        MDL["models.py\nTrainedModel\nC4BehavioralModelRunner"]
        FTR["features.py\nFeatureExtractor\nBehavioralFeatures"]
        RFT["runtime_features.py\nRuntimeFeatureAdapter\nDeviceHistory"]
        INT["integration.py\ncreate_c4_service_with_behavioral_ml()"]
        DSP["data_split.py\nScenarioAwareSplitter"]
    end

    subgraph shared["shared/"]
        CON["contracts/c4_trust.py\nC4TrustAssessment"]
        TEL["contracts/telemetry.py\nTelemetryPacket"]
        ENM["enums/domain.py\nC4TrustLabel\nC4RoutingOutcome"]
    end

    subgraph artifacts["experiments/c4/models/"]
        ART["random_forest_corrected.joblib"]
    end

    INT --> SVC
    INT --> MDL
    INT --> RFT
    PIP --> SVC
    PIP --> QUA
    SVC --> REG
    SVC --> CON
    SVC --> TEL
    SVC --> ENM
    MDL --> TEL
    RFT --> MDL
    RFT --> TEL
    INT --> ART
    FTR -.->|"training only"| DSP
```

### 3. Telemetry Security Verification Flow

```mermaid
flowchart TD
    A["TelemetryPacket + Signature"] --> B{Device\nRegistered?}
    B -->|No| F1["DEVICE_UNKNOWN → UNTRUSTED"]
    B -->|Yes| C{Device\nACTIVE?}
    C -->|No| F2["DEVICE_NOT_ACTIVE → UNTRUSTED"]
    C -->|Yes| D{Zone + Hub\nMatch?}
    D -->|Mismatch| F3["ZONE/HUB_MISMATCH → UNTRUSTED"]
    D -->|Missing hub| U1["HUB_ID_MISSING → UNKNOWN"]
    D -->|Valid| E{Credential ID\n+ Expiry?}
    E -->|Missing/Expired| F4["CREDENTIAL_* → UNTRUSTED"]
    E -->|No credential| U2["CREDENTIAL_NOT_CONFIGURED → UNKNOWN"]
    E -->|Valid| G{Signature\nVerified?}
    G -->|INTEGRITY_INVALID| F5["INTEGRITY_INVALID → UNTRUSTED"]
    G -->|Unverifiable| U3["SIGNATURE_UNVERIFIABLE → UNKNOWN"]
    G -->|INTEGRITY_VALID| H{Timestamp\nFresh?}
    H -->|Stale or Future| F6["FRESHNESS_EXPIRED / TIMESTAMP_IN_FUTURE → UNTRUSTED"]
    H -->|Fresh| I{Replay\nDetected?}
    I -->|Duplicate| F7["REPLAY_DETECTED → UNTRUSTED"]
    I -->|Not seen before| J{ML Behavioral\nScorer?}
    J -->|Score unavailable, ML required| U4["BEHAVIOURAL_SCORE_UNAVAILABLE → UNKNOWN"]
    J -->|Score >= 0.7| S["SUSPICIOUS → QUARANTINE"]
    J -->|Score < 0.7| T["TRUSTED → ACCEPT → C1"]

    F1 & F2 & F3 & F4 & F5 & F6 & F7 --> QR["Quarantine: SECURITY_FAILURE"]
    U1 & U2 & U3 & U4 --> QR2["Quarantine: EVIDENCE_UNAVAILABLE"]
    S --> QR3["Quarantine: BEHAVIOURAL_ANOMALY"]

    style T fill:#4CAF50,color:#fff
    style S fill:#FF9800,color:#fff
    style F1,F2,F3,F4,F5,F6,F7 fill:#F44336,color:#fff
    style U1,U2,U3,U4 fill:#FF9800,color:#fff
```

### 4. ML Training, Artifact Loading, and Runtime Inference

```mermaid
flowchart LR
    subgraph Training["Training (Offline)"]
        DS["C4_Behavioral_Dataset.csv\n10,000 rows, 62 columns"]
        FE["FeatureExtractor\nextract_for_training()"]
        SP["ScenarioAwareSplitter\nsplit_by_device()"]
        TR["BaselineModel\nRandomForestClassifier\nn_estimators=100"]
        ART["random_forest_corrected.joblib\nTrainedModel serialized"]
        DS --> FE --> SP --> TR --> ART
    end

    subgraph Runtime["Runtime (Online)"]
        PKT["TelemetryPacket"]
        RFA["RuntimeFeatureAdapter\nextract_features()"]
        FEAT["pd.DataFrame\n1 row × 18 features"]
        MR["C4BehavioralModelRunner\nbehavioural_anomaly_score()"]
        SC["score = 1.0 - P(Trusted)\n[0.0, 1.0]"]
        PKT --> RFA --> FEAT --> MR --> SC
    end

    ART -->|"TrainedModel.load()\nschema validation"| MR

    style ART fill:#9C27B0,color:#fff
```

### 5. Sequence Diagram — Valid Packet Flow

```mermaid
sequenceDiagram
    participant Dev as IoT Device (Simulated)
    participant Gate as C4TelemetryGate
    participant Svc as C4TrustService
    participant Reg as DeviceRegistry
    participant ML as C4BehavioralModelRunner
    participant QM as QuarantineManager
    participant C1 as C1 (Downstream)

    Dev->>Gate: process(packet, signature)
    Gate->>Svc: assess(packet, signature)
    Svc->>Reg: get(device_id) → DeviceRecord
    Reg-->>Svc: DeviceRecord (ACTIVE)
    Svc->>Svc: verify zone, hub, credential, expiry
    Svc->>Svc: _verify_signature(packet, sig, cred) → True
    Svc->>Svc: check freshness + replay
    Svc->>ML: behavioural_scorer(packet)
    ML->>ML: extract_features(packet) → DataFrame
    ML-->>Svc: score = 0.15
    Svc-->>Gate: C4TrustAssessment(TRUSTED, ACCEPT, score=0.15)
    Gate-->>C1: eligible_packet = packet
```

---

## 16. Security Limitations and Research Gaps

### Verified Issues

| Issue | Evidence | Severity |
|---|---|---|
| **Low Untrusted recall (19.07%)** | `C4_RUNTIME_INTEGRATION_SUMMARY.md` metrics | Medium — behavioral gate is supplementary; deterministic gate handles hard failures |
| **Replay state lost on restart** | `runtime_features.py` uses `dict` and `set` in-memory; no persistence | Medium — window for replay attack immediately after restart |
| **RSSI deviation semantics uncertainty** | Noted in `C4_RUNTIME_INTEGRATION_SUMMARY.md` | Low — SHAP analysis suggests chosen semantics are reasonable |
| **No database-backed C4 assessments** | `database/models.py` has no C4-specific tables | Medium — no historical audit trail |
| **Software-only cryptography** | No ATECC608A integration found | High for production; acceptable for research prototype |
| **Quarantine directory not access-controlled** | QuarantineManager uses plain filesystem | Medium |
| **No frontend / API layer** | No frontend files, API stubs only | Medium — system cannot be demoed via browser |
| **Device registry is in-memory** | `DeviceRegistry` uses Python `dict` | Medium — registry lost on restart |
| **No API authentication** | No JWT, API key, or OAuth found | High for production deployment |

### Possible Risks (Not Confirmed Defects)

- **Clock synchronization:** Freshness checking relies on comparing `observed_at` (device clock) with `assessed_at` (server clock). If device clocks drift significantly, valid packets may be rejected as stale or future-dated. Clock sync via NTP or PPS is not implemented.
- **Model artifact integrity:** The joblib file is loaded from disk without cryptographic verification. A compromised model file would affect all behavioral assessments. Model signing is not implemented.
- **Concurrent device history mutation:** While `C4TrustService` uses a `threading.Lock()`, `RuntimeFeatureAdapter._device_histories` is not locked. If multiple threads call `extract_features()` for the same device simultaneously, there may be a race condition in history updates.

### Future Research Work

- Integrate ATECC608A or equivalent hardware secure element on ESP32-S3.
- Implement persistent replay detection state (Redis or database-backed).
- Implement persistent device registry (database-backed).
- Implement a REST/MQTT API ingestion layer with proper authentication.
- Collect real sensor behavioral data to replace synthetic training data.
- Improve Untrusted class recall (oversampling, cost-sensitive learning, more training data).
- Implement clock synchronization enforcement.
- Add C4TrustAssessment persistence to PostgreSQL.
- Build a security operations dashboard (frontend).

---

## 17. PP1 and Viva Preparation

### 30-Second Explanation

"Component 4 solves a fundamental IoT security problem: just because a packet arrives with correct formatting doesn't mean it's trustworthy. C4 acts as a security gate at the entry point of GeoNex. Before any sensor reading is used for landslide prediction, C4 verifies that the packet genuinely came from a registered, authorized device, that it wasn't modified in transit using cryptographic signatures, that it's recent and hasn't been replayed, and that the device's behavior matches what a legitimate sensor should look like, using a trained Random Forest model. Only packets that pass all of these checks are allowed through to the rest of the system."

### 1-Minute Technical Explanation

"GeoNex Component 4 implements a multi-layer telemetry security gate in Python. Every incoming telemetry packet is evaluated in sequence: first, device identity is checked against an in-memory device registry that tracks lifecycle states — a device must be in the ACTIVE state to have its packets accepted. Second, the packet's cryptographic signature is verified using either HMAC-SHA256 or ECDSA-SHA256, ensuring the packet came from a device with access to the correct key and was not modified in transit. Third, the timestamp is checked for freshness within a 30-second window, and a packet-ID replay detection mechanism catches duplicate submissions.

If and only if all of these mandatory checks pass, a trained Random Forest model evaluates 18 behavioral features extracted from the packet — things like transmission timing, signal strength, battery state, and historical patterns — and produces an anomaly score. If the score exceeds 0.7, the packet is flagged as suspicious and quarantined. Otherwise, it's forwarded as trusted. Failed packets are preserved in a quarantine store for investigation. The system is fail-closed: if anything is ambiguous or missing, the packet goes for security review rather than being accepted."

### 3-Minute Detailed Explanation

"My research component, C4, addresses the problem of trusted telemetry provenance in an IoT-based landslide early-warning system. The core research question is: how do we establish, at the point of data ingestion, that a telemetry packet is genuinely trustworthy — not just correctly formatted?

The challenge is that an attacker with access to the network can craft a perfectly valid JSON packet, replay an old captured packet, or inject data from an unauthorized device. If any of these reach the downstream analysis components, the entire early-warning system's integrity is compromised.

C4 implements five verification layers. The first three are **mandatory deterministic checks**:

One, device identity: every device is registered with a device ID, zone, hub, and lifecycle state. Only ACTIVE devices can transmit accepted telemetry. A PROVISIONED, SUSPENDED, REVOKED, or RETIRED device is immediately rejected.

Two, cryptographic authentication: each packet carries an HMAC-SHA256 or ECDSA-SHA256 signature computed over the entire serialized packet. The server verifies this signature using a stored credential. Any modification to any field — even a single character — changes the digest and makes verification fail. This proves both the packet's origin and its integrity.

Three, freshness and replay protection: the packet's observed timestamp must be within 30 seconds. Packets observed more than 30 seconds ago, or in the future beyond a 5-second tolerance, are rejected. Additionally, each packet's ID is tracked in memory, and any duplicate submission is caught as a replay attack.

If all three mandatory checks pass, a fourth optional layer runs: **behavioral machine-learning assessment**. I trained a Random Forest classifier on 10,000 synthetic behavioral records, with device-held-out splits to prevent device-shortcut leakage. The model evaluates 18 features including transmission timing, RSSI, signal-to-noise ratio, battery state, reboot frequency, and per-device rolling history features. If the model's anomaly score exceeds 0.7, the packet is flagged as SUSPICIOUS and quarantined.

Importantly, the ML model cannot override the mandatory security gate. A packet that fails cryptographic verification is UNTRUSTED regardless of how good its behavioral score is. This is enforced both in the service logic and at the Pydantic contract level.

The final output is a C4TrustAssessment object with a trust label (TRUSTED, SUSPICIOUS, UNTRUSTED, or UNKNOWN), a routing outcome (ACCEPT, QUARANTINE, REJECT, or SECURITY_REVIEW), and a full list of reason codes explaining the decision. Only TRUSTED+ACCEPT packets are forwarded to the downstream components. All others are quarantined as JSON files for investigation and potential release by an authorized reviewer.

The test suite covers 142 test cases across device registry management, ECDSA and HMAC signature tests, full trust service scenarios, runtime feature extraction, ML data pipeline tests, and end-to-end gate tests — all passing."

### Main Research Problem and Contribution

**Problem:** IoT telemetry in safety-critical systems (landslide early warning) cannot be trusted at face value. Data format validity alone does not establish security.

**Contribution:** A layered telemetry authentication and behavioral trust assessment system that:
1. Enforces device identity and lifecycle constraints.
2. Verifies cryptographic authenticity and integrity using HMAC-SHA256 and ECDSA-SHA256.
3. Enforces freshness and detects replay attacks.
4. Applies a behavioral ML model to detect anomalous patterns that pass cryptographic verification.
5. Implements fail-closed semantics throughout — ambiguous cases go for review, not acceptance.

### Cryptographic Verification vs. ML Behavioral Assessment

| Aspect | Cryptographic Verification | ML Behavioral Assessment |
|---|---|---|
| **What it detects** | Forged packets, tampered data, wrong keys, unauthorized devices | Abnormal transmission timing, suspicious RSSI patterns, unusual device health |
| **False positives** | Essentially zero (by design) | Possible — model may flag legitimate devices (19% untrusted recall) |
| **Bypass risk** | Cannot be bypassed without the correct key | An attacker who knows the key can pass the crypto check but may still be caught by behavioral |
| **Overrides** | Hard failures — cannot be overridden by ML | Advisory only — cannot override crypto failures |
| **Algorithm** | HMAC-SHA256, ECDSA-SHA256 | Random Forest (100 trees, 18 features) |

### Why Multiple ML Models Were Evaluated

Three model types were evaluated as baselines:
- **Random Forest:** Best balance of interpretability, performance, and no need for feature scaling. Selected for production inference. Feature importances available.
- **Logistic Regression:** Simpler, faster, interpretable coefficients, but requires feature scaling and assumes linear decision boundaries. Used as a comparison baseline.
- **Isolation Forest:** Unsupervised anomaly detection — does not use labels during training. Cannot produce calibrated probabilities, so it cannot contribute to the trust score fusion. Used for experimental comparison only.

Random Forest was selected because it performs better on the imbalanced multi-class dataset and provides feature importances that can be interpreted for security analysis.

### How Each Packet Type is Handled

| Packet Type | What Happens |
|---|---|
| **Valid (registered, active, correct signature, fresh, unique)** | All checks pass → ML scores it → TRUSTED/ACCEPT if score < 0.7 |
| **Tampered (field modified after signing)** | Signature verification fails → INTEGRITY_INVALID → UNTRUSTED/REJECT |
| **Replayed (same packet submitted twice)** | Second submission → REPLAY_DETECTED → UNTRUSTED/REJECT |
| **Stale (observed 60+ seconds ago)** | Freshness check fails → FRESHNESS_EXPIRED → UNTRUSTED/REJECT |
| **Suspicious (valid crypto, abnormal behavior)** | All mandatory checks pass → ML score >= 0.7 → SUSPICIOUS/QUARANTINE |
| **Unknown device** | Registry lookup fails → DEVICE_UNKNOWN → UNTRUSTED/REJECT |
| **Revoked device** | Lifecycle check fails → DEVICE_NOT_ACTIVE → UNTRUSTED/REJECT |
| **Missing signature** | No signature provided → SIGNATURE_MISSING → UNKNOWN/SECURITY_REVIEW |
| **ML model unavailable** | Feature extraction or inference fails → UNKNOWN/SECURITY_REVIEW |

### What Makes C4 Different from a Normal Data-Validation System

A normal data-validation system checks that incoming data has the right format, types, and value ranges. C4 does something fundamentally different:

1. It verifies **who** sent the data (device identity, lifecycle state).
2. It verifies **that the data was not changed** after it was sent (cryptographic integrity).
3. It verifies **when** the data was sent (freshness, replay detection).
4. It verifies **whether the device is behaving normally** for a legitimate sensor (behavioral ML).

None of these can be achieved by checking data formats or value ranges alone.

### Current Prototype Limitations

1. All cryptography is software-based. No hardware secure element is integrated.
2. Device registry and replay state are in-memory. Restart clears them.
3. The ML model has only 19% recall on the Untrusted class.
4. There is no frontend or API layer.
5. Database persistence for C4 assessments is not implemented.
6. The training data is synthetic, not collected from real sensors.
7. No clock synchronization enforcement.

### 25 Likely Viva Questions and Answers

**Q1: What problem does C4 solve?**
C4 solves the problem of trusting telemetry data from IoT sensors. A correctly formatted packet could be forged, tampered, replayed, or from an unauthorized device. C4 verifies the packet's authenticity, integrity, freshness, and behavioral consistency before allowing it into the rest of the system.

**Q2: Why isn't signature verification alone sufficient?**
Signature verification proves the packet came from a device with the correct key and wasn't tampered with. But it doesn't catch replays (an old signed packet replayed later), stale data (a delayed valid packet), or behavioral anomalies from a compromised device that still holds its key.

**Q3: What is the difference between HMAC-SHA256 and ECDSA-SHA256?**
HMAC-SHA256 is symmetric — both device and server share the same secret key. It's faster but requires secure distribution of the shared secret. ECDSA-SHA256 is asymmetric — the device holds a private key that never leaves it, and the server holds only the corresponding public key. ECDSA provides non-repudiation (the server can prove which device signed the packet), while HMAC only proves someone with the shared secret signed it.

**Q4: What is the `C4_MODEL_FEATURE_SCHEMA` and why does it matter?**
It is a tuple of 18 feature names in a specific order that defines the exact input expected by the trained Random Forest model. Every feature must be present, in the correct order, numeric, and finite. The runtime adapter validates that extracted features match this schema exactly before passing them to the model. A mismatch causes inference to fail closed.

**Q5: Why can't the ML model override a failed security check?**
The Pydantic `C4TrustAssessment` validator enforces that a packet with `mandatory_security_pass=False` cannot have `trust_label=TRUSTED`. This is also enforced in the service logic: the ML scorer is only called after all mandatory checks pass. If any mandatory check fails, the assessment is UNTRUSTED immediately, and the scorer is never called.

**Q6: What happens if the ML model is unavailable?**
The `C4BehavioralModelRunner.load()` raises a `FileNotFoundError` or `ModelSchemaError` at service startup if the model artifact is missing or incompatible. If scoring fails at runtime (exception during inference), the scorer returns `None`. If `allow_deterministic_only=False` and the score is `None`, the result is `UNKNOWN/SECURITY_REVIEW`.

**Q7: What is the `suspicious_score_threshold`?**
The default is 0.7. If the Random Forest returns a behavioral anomaly score (= 1.0 - P(Trusted)) >= 0.7, the packet is SUSPICIOUS. Below 0.7, it is TRUSTED. This threshold is configurable when creating the service.

**Q8: What does `mandatory_security_pass=True` mean?**
It means that all mandatory security checks (identity, integrity, freshness, replay, credentials) passed without any failures or unknowns. A packet can be SUSPICIOUS with `mandatory_security_pass=True` — it passed all security checks but the ML model flagged it as behaviorally anomalous.

**Q9: Why does the system quarantine rather than delete suspicious packets?**
Quarantine preserves the original packet and the full assessment for investigation. False positives (legitimate packets incorrectly flagged) can be reviewed and released. Security incidents require forensic analysis of the original data. Permanent deletion would destroy evidence.

**Q10: How does replay detection work?**
The trust service maintains a set of `(device_id, packet_id)` tuples seen so far. After accepting a packet, its tuple is added to this set. The next time the same packet arrives, the tuple is already in the set, and `REPLAY_DETECTED` is added to failures → UNTRUSTED. Additionally, sequence numbers are tracked per device+boot session to detect out-of-order replays.

**Q11: What is device-held-out splitting and why does it matter?**
Device-held-out splitting ensures no device appears in both training and test data. Without it, the model might memorize device-specific patterns (device shortcut) rather than learning generalizable behavioral features. With device-held-out splits, test performance reflects generalization to devices the model has never seen.

**Q12: Why is the Untrusted recall only 19%?**
The training dataset has relatively few Untrusted samples, and those samples may not represent the full range of untrusted behavioral patterns (since the data is synthetic). The model therefore tends to classify ambiguous packets as Trusted rather than Untrusted. For the research prototype, this is mitigated by the mandatory deterministic security gate, which catches the hard security violations regardless of the ML score.

**Q13: What is the difference between `UNKNOWN` and `UNTRUSTED`?**
`UNTRUSTED` means a mandatory check definitively failed — forged signature, wrong device, stale packet. The system is certain this packet is problematic. `UNKNOWN` means evidence was insufficient — no signature provided, no credential configured, attestation could not be verified. The system cannot make a definitive determination, so the packet is sent for human review.

**Q14: How does the `RecoveryContext` work?**
A `RecoveryContext` authorizes a specific device to replay packets from a specific time window without triggering freshness or replay failures. This is intended for C2 recovery scenarios (e.g., replaying buffered SD-card data after connectivity is restored). The context must be explicitly created by the server and can be revoked. Without it, any old packet is rejected.

**Q15: What is the canonical packet representation used for signing?**
The entire `TelemetryPacket` is serialised to JSON with `sort_keys=True` and minimal separators, then UTF-8 encoded. This ensures the same bytes are used for both signing and verification, regardless of field order in the original object.

**Q16: Can two different devices use the same credential ID?**
No. The credential ID is compared using `hmac.compare_digest()` between the packet's `security.credential_id` and the registry's `credential.credential_id`. A mismatch generates `CREDENTIAL_ID_MISMATCH` → UNTRUSTED. Each device should have a unique credential.

**Q17: What is `allow_deterministic_only` and when is it used?**
When `allow_deterministic_only=True`, the service accepts packets as TRUSTED even if no behavioral scorer is configured or if the scorer returns `None`. When `False`, a `None` score results in `UNKNOWN/SECURITY_REVIEW`. The demo configuration uses `True` for simplicity. Production with ML should use `False`.

**Q18: Where is the trained model artifact stored?**
`experiments/c4/models/random_forest_corrected.joblib` — serialized using joblib. It is a `TrainedModel` object containing the fitted `RandomForestClassifier`, the `LabelEncoder`, the feature names, and the training metadata.

**Q19: How does the C4TelemetryGate connect to C1?**
The `C4GateResult.eligible_packet` property holds the original `TelemetryPacket` if and only if it received `TRUSTED + mandatory_security_pass=True + ACCEPT`. The caller (ingestion layer or orchestrator) checks `gate_result.eligible_for_c1` and forwards the packet to C1 only if `True`. The C4 assessment (`gate_result.assessment`) accompanies the packet for audit.

**Q20: What is SHAP and how is it used in C4?**
SHAP (SHapley Additive exPlanations) is a model interpretability framework. The `explain_c4_model.py` script computes SHAP values for the Random Forest model, showing how much each feature contributed to each individual prediction. SHAP plots are available in `experiments/c4/plots/`. This helps verify that the model is learning from meaningful behavioral features rather than spurious correlations.

**Q21: Why is Isolation Forest not used for runtime trust scoring?**
Isolation Forest is an unsupervised anomaly detection algorithm. It does not produce calibrated class probabilities — it only returns +1 (inlier) or -1 (outlier). The `C4BehavioralModelRunner` requires `predict_proba()` to compute `1.0 - P(Trusted)`. Since Isolation Forest cannot produce this, it explicitly raises `ModelSchemaError` when used with `C4BehavioralModelRunner`. It is only used for experimental comparison.

**Q22: What is the threat model for C4?**
C4 is designed to defend against: (1) unauthorized devices sending forged packets, (2) man-in-the-middle attackers tampering with packets in transit, (3) replay attacks using captured legitimate packets, (4) stale data injection from delayed or replayed legitimate captures, (5) behavioral anomalies from compromised-but-credentialed devices. The threat model documentation is at `docs/components/C4_THREAT_MODEL.md`.

**Q23: What happens to the device rolling history when a device reboots?**
The `boot_id` field changes after a reboot. The sequence number counter for the new `(device_id, boot_id)` pair starts fresh. The `RuntimeFeatureAdapter` also does not automatically detect reboots — its rolling history accumulates across reboots (since it is keyed only by `device_id`, not by `device_id + boot_id`). This is a known limitation. The `clear_device_history()` method exists but is not called automatically on reboot detection.

**Q24: How is the project structured as a Python package?**
The project uses `pyproject.toml` with setuptools. All packages are registered explicitly. The C4 module is `components.c4_trust`. Running `pip install -e .` in the repository root makes all packages importable. The test runner (`pytest`) uses `pythonpath = ["."]` to resolve imports without installation.

**Q25: What is the security_policy_version in the assessment?**
The current policy version is `"C4_POLICY_1.1"`. The model version is `"C4_RULE_BASELINE_001"`. These are hardcoded strings in `service.py` that help track which version of the security policy was used for a given assessment. In a production system, these would be incremented when the policy or model changes, enabling retrospective audit of old assessments.

---

## 18. Implementation Status and Next Steps

### ✅ Completed and Verified (Code + Passing Tests)

- Device registry with full lifecycle state management (PROVISIONED → ACTIVE → SUSPENDED → REVOKED → RETIRED)
- HMAC-SHA256 signing and constant-time verification
- ECDSA-SHA256 signing and verification (P-256 / SECP256R1 curve)
- Canonical packet serialization for signing (sort_keys, minimal separators, UTF-8)
- Algorithm isolation (no ECDSA → HMAC fallback)
- Credential validity window enforcement (issued_at, expires_at)
- Zone and hub enforcement against device registry
- Firmware and configuration hash approval (optional)
- Freshness validation (30-second max_age, 5-second future tolerance)
- Packet-ID replay detection (in-memory set)
- Sequence-number replay detection (in-memory dict per device+boot)
- Authorized recovery replay context
- Behavioral ML assessment via Random Forest (18-feature schema)
- Fail-closed feature extraction (no silent defaults for missing features)
- Per-device rolling history (window=10) for historical features
- C4BehavioralModelRunner with schema validation
- Integration factory (`create_c4_service_with_behavioral_ml`)
- Deterministic-only fallback mode (`create_c4_service_deterministic_only`)
- C4TelemetryGate orchestrating assess + quarantine
- Quarantine manager with atomic filesystem writes
- Quarantine release with authorized reviewer requirement
- C4TrustAssessment Pydantic model with contract-level validators
- Full test suite: 142 tests passing
- SHAP explainability (offline analysis)
- Device-held-out dataset splitting with leakage validation
- Simulation generator with behavioral metadata (freshness_status, device health, gateway_id)
- Database schema: `telemetry_packets` and `sensor_observations` tables
- Migration `b7c2e9a41d6f` adding `tx_interval_s` and `freshness_status` columns

### ⚠️ Implemented but Not Fully Verified

- Firmware and config approval integration in end-to-end flows (unit tests pass; no full system test)
- Database persistence path (ORM models and migrations implemented; not tested with a live PostgreSQL instance in this audit)
- Isolation Forest training baseline (code exists and works; not evaluated on corrected splits)
- Demo simulation gate (`c4_demo.py`) in multi-device scenario (simulation exists; full multi-packet test not verified in this audit)

### 🔧 Partially Implemented

- API/ingestion layer (stub Python packages exist in `apps/`; no actual HTTP endpoints or middleware)
- Firmware (`firmware/` directory exists; C4-compatible signing in firmware not confirmed)
- Mode-aware features (`add_mode_aware_features()` in `features.py` exists but is not wired into runtime feature extraction — reserved for future use)
- C4 assessment database persistence (no `c4_assessments` table; scores not written to DB)

### ❌ Not Implemented

- **Frontend / Web Dashboard** — No UI for C4
- **HTTP ingestion API** — No real network endpoint
- **Hardware-backed cryptography** — No ATECC608A or secure element integration
- **Device registry database persistence** — Registry is in-memory only
- **Replay detection state persistence** — Lost on restart
- **Clock synchronization enforcement** — No NTP/PPS integration
- **Model artifact integrity verification** — No signature on joblib file
- **API authentication** — No JWT, API keys, or OAuth
- **Quarantine access control** — Directory is world-readable
- **C4 assessment retention and audit log** — No database table for assessments

### 🚀 Recommended Next Steps Before PP1/Viva

| Priority | Task | Why It Matters | Relevant File |
|---|---|---|---|
| **High** | Add a simple demo script that shows a complete valid and invalid flow with printed output | Enables terminal-based demonstration without a frontend | `scripts/load_demo_simulation.py` |
| **High** | Verify the demo simulation runs end-to-end with `load_demo_simulation.py` and prints clear assessment results | PP1 presentation needs a working demo | `shared/simulation/c4_demo.py` |
| **High** | Document the full test run command and expected output in `README.md` | Supervisors and examiners need to reproduce results | `README.md` |
| **Medium** | Add a simple Flask or FastAPI endpoint that accepts `TelemetryPacket + signature` and returns `C4TrustAssessment` | Demonstrates real API integration | `apps/api/` |
| **Medium** | Persist `C4TrustAssessment` to a database table | Creates an audit trail; shows complete system thinking | New migration required |
| **Medium** | Test with a live PostgreSQL instance and confirm telemetry persistence | Closes the database verification gap | `database/models.py` |
| **Low** | Improve Untrusted recall (e.g., class weighting in Random Forest, SMOTE oversampling) | Research quality improvement | `scripts/retrain_c4_corrected.py` |
| **Low** | Implement replay state persistence (Redis or database) | Closes the restart vulnerability | `components/c4_trust/service.py` |
| **Low** | Add mode-aware feature support to `RuntimeFeatureAdapter` | Extends behavioral assessment capability | `runtime_features.py` |

---

## 19. Audit Summary

### Files Inspected

| Category | Files Read |
|---|---|
| C4 core backend | `service.py`, `registry.py`, `pipeline.py`, `quarantine.py`, `models.py`, `features.py`, `runtime_features.py`, `integration.py`, `data_split.py`, `__init__.py` |
| Shared contracts and enums | `c4_trust.py`, `telemetry.py`, `common.py`, `domain.py` |
| Simulation | `c4_demo.py`, `generator.py` |
| Database | `models.py`, `base.py` (inferred), migrations `70edc0f1d309`, `b7c2e9a41d6f` |
| Tests | `test_c4_device_registry.py`, `test_c4_ecdsa_signatures.py`, `test_c4_trust_service.py`, `test_c4_runtime_features.py`, `test_c4_ml_data.py`, `test_c4_simulation_gate.py`, `test_telemetry_persistence.py`, `test_c4_e2e.py` |
| Documentation | `C4_RUNTIME_INTEGRATION_SUMMARY.md`, `README.md`, `C4_SPLIT_REVIEW_NOTES.md` |
| Configuration | `pyproject.toml`, `compose.yaml` |
| Quarantine samples | `Q_035c99398f19.json`, `Q_bc73aebf25ff.json` (2 sample files) |
| **Total** | **~40 files read in full** |

### Main Subsystems Covered

- Device registry and lifecycle management ✅
- HMAC-SHA256 and ECDSA-SHA256 cryptographic verification ✅
- Freshness validation and replay protection ✅
- Behavioral ML pipeline (training, runtime inference, integration) ✅
- Trust decision logic and fail-closed behavior ✅
- Quarantine management ✅
- Database schema and migrations ✅
- Test suite ✅
- Simulation infrastructure ✅
- Frontend status (absent) ✅

### Tests Actually Run

```
Command: python -m pytest tests/security/ tests/unit/test_c4_runtime_features.py tests/unit/c4/ test_c4_e2e.py -v --tb=short
Result: 142 passed, 0 failed, 0 skipped (24.22 seconds)
Platform: Windows, Python 3.14.6, pytest 9.0.3
```

### Most Important Gaps Found

1. **No frontend or API layer** — C4 cannot be accessed via a browser or HTTP client.
2. **No C4 assessment database persistence** — Assessments are ephemeral; no historical audit trail.
3. **Device registry and replay state are in-memory** — System restarts clear all state.
4. **Low Untrusted recall (19.07%)** — The ML model is unreliable for detecting untrusted behavioral patterns; deterministic gate compensates.
5. **No hardware cryptography** — All signing and verification is software-based.

---

*Document generated from a full codebase audit on 2026-10-15. All code paths, test results, and metrics are based on the inspected source code and actual test execution. No features have been invented or assumed.*
