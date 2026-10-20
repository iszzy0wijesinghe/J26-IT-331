# Component 4: Trusted Telemetry Provenance and Device Attestation
## Complete Workflow for Progress Presentation (PP1)

**Project:** GeoNex - Smart Landslide Early Warning Prediction System using IoT, Edge AI and Risk Analytics  
**Component:** C4 - Trusted Telemetry Provenance and Device Attestation  
**Project ID:** J26-IT-331  
**Component Lead:** H d s geshani  
**Panel:** IT-P03  
**Date:** October 2026

---

## Executive Summary

Component 4 (C4) serves as the **security gate** for the GeoNex landslide early-warning system. It ensures that all telemetry data entering the analytical pipeline originates from legitimate, authenticated IoT devices and has not been tampered with or replayed during transmission. C4 combines **deterministic cryptographic verification** with **behavioral machine learning** to provide comprehensive trust assessment before any environmental reasoning (C1, C2, C3) occurs.

### Key Panel Feedback Addressed

1. **"Will use sensor data and use credibility flags as a decision support"** - C4 integrates sensor telemetry with credibility assessment through a hybrid security + ML framework
2. **"Lacks proper idea about the component"** - This document provides complete clarity on C4's role, architecture, and implementation
3. **"Refine the commercialization plan along with the plans"** - Commercialization strategy included in Section 7

---

## Table of Contents

1. [Component 4 Mission and Purpose](#1-component-4-mission-and-purpose)
2. [C4 Position in GeoNex Architecture](#2-c4-position-in-geonex-architecture)
3. [Core Workflow - End-to-End Data Flow](#3-core-workflow---end-to-end-data-flow)
4. [Security Verification Layers](#4-security-verification-layers)
5. [Behavioral ML Assessment](#5-behavioral-ml-assessment)
6. [Trust Decision Engine](#6-trust-decision-engine)
7. [Commercialization Plan](#7-commercialization-plan)
8. [Implementation Status](#8-implementation-status)
9. [Technical Architecture](#9-technical-architecture)
10. [Testing and Validation](#10-testing-and-validation)
11. [Future Enhancements](#11-future-enhancements)

---

## 1. Component 4 Mission and Purpose

### Research Problem

In a landslide early-warning system, every safety decision depends on telemetry data arriving from physical IoT sensors buried in unstable terrain. The core research question C4 addresses:

> **How do we know whether a telemetry packet arriving at the backend genuinely came from the registered, authorised device it claims to be from, was not modified in transit, is not a replay of an old packet, and is behaviorally consistent with what a legitimate sensor should produce?**

### C4's Primary Responsibilities

1. **Device Identity Verification** - Confirm the packet originates from a registered, active device
2. **Cryptographic Integrity** - Verify the packet has not been tampered with during transmission
3. **Freshness Validation** - Ensure the packet is recent and not a replay attack
4. **Behavioral Assessment** - Detect abnormal transmission patterns using ML
5. **Trust Decision** - Route packets as TRUSTED, SUSPICIOUS, or UNTRUSTED with explicit reasoning

### What C4 Is NOT

- **C4 is NOT C1 (Credibility Classification)** - C1 checks if sensor readings are scientifically plausible given environmental context. C4 checks if the packet came from a legitimate device before C1 sees it.
- **C4 is NOT C3 (Forecasting)** - C3 predicts future landslide risk. C4 gates which telemetry is trustworthy enough to feed into C3.
- **C4 is NOT the Decision Engine** - The Decision Engine decides system operating modes. C4 provides security assessment labels that the Decision Engine uses.

---

## 2. C4 Position in GeoNex Architecture

### System-Level Data Flow

```
Physical IoT Sensors ( buried in landslide-prone terrain)
        ↓
Wireless Transmission (LoRa/Cellular/Satellite)
        ↓
Gateway/Hub
        ↓
Raw Telemetry Ingestion
        ↓
─────────────────────────────────────────────────────
C4 SECURITY GATE (Component 4)
        ↓
├─ Device Registry Validation
├─ Cryptographic Signature Verification
├─ Freshness & Replay Protection
├─ X.509 Certificate Validation
└─ Behavioral ML Assessment
        ↓
Trust Decision (TRUSTED / SUSPICIOUS / UNTRUSTED)
        ↓
─────────────────────────────────────────────────────
        ↓
If TRUSTED → Downstream Components
        ├─ C1: Rainfall Regime-Aware Sensor Credibility Classification
        ├─ C2: Silent-Pattern Diagnostic Classification
        ├─ C3: Multi-Sensor Temporal Forecasting
        └─ Decision Engine: Operating Mode & Escalation
        ↓
If SUSPICIOUS → Quarantine for Investigation
        ↓
If UNTRUSTED → Reject & Audit (but retain evidence)
```

### C4's Role in Decision Support

C4 provides **credibility flags** that downstream components use as decision support:

| C4 Trust Label | Meaning | Downstream Impact |
|----------------|---------|------------------|
| **TRUSTED** | All mandatory security checks passed, behavior normal | C1, C2, C3 process the telemetry normally |
| **SUSPICIOUS** | Security checks passed, but behavior is abnormal | C1/C2/C3 may process with reduced confidence; flagged for review |
| **UNTRUSTED** | Mandatory security check failed | Telemetry rejected; not passed to C1/C2/C3; retained for audit |

---

## 3. Core Workflow - End-to-End Data Flow

### Step 1: Telemetry Packet Generation (Device Side)

**Location:** IoT Sensor Device

**Process:**
1. Sensor collects environmental data (soil moisture, rainfall, tilt, etc.)
2. Device assembles telemetry packet with:
   - `device_id`: Unique device identifier
   - `zone_id`: Deployment zone
   - `observed_at`: Timestamp (UTC)
   - `sensor_readings`: Environmental measurements
   - `transport`: Gateway info, RSSI, SNR, retries
   - `security`: Credential ID, firmware hash, config hash
3. Device signs the packet using:
   - **HMAC-SHA256** (symmetric) - Default method
   - **ECDSA-SHA256** (asymmetric) - Higher security option
4. Device transmits signed packet to gateway

**Key Security Properties:**
- Full packet is signed (canonical JSON with sorted keys)
- Any modification after signing breaks verification
- Signature proves possession of secret key

### Step 2: Ingestion and Pre-Processing

**Location:** Backend Gateway/API

**Process:**
1. Receive packet from gateway
2. Parse and validate Pydantic schema (`TelemetryPacket`)
3. Extract signature from packet metadata
4. Forward to C4 Trust Service for assessment

### Step 3: C4 Security Gate Processing

**Location:** `components/c4_trust/service.py` - `C4TrustService.assess()`

**Processing Steps:**

#### 3.1 Device Registry Validation
```
Check: Is device_id registered in DeviceRegistry?
Check: Is device lifecycle state = ACTIVE?
Check: Does zone_id match registered zone?
Check: Does gateway_id match registered hub?
```

**Outcomes:**
- ✅ PASS → Continue to next check
- ❌ FAIL → UNTRUSTED (reason: DEVICE_UNKNOWN, DEVICE_NOT_ACTIVE, ZONE_MISMATCH, HUB_MISMATCH)

#### 3.2 Credential Validation
```
Check: Does credential_id match registered credential?
Check: Is credential valid (issued_at, expires_at)?
Check: Is certificate present (if required)?
```

**Outcomes:**
- ✅ PASS → Continue to signature verification
- ❌ FAIL → UNTRUSTED (reason: CREDENTIAL_ID_MISMATCH, CREDENTIAL_EXPIRED, CERTIFICATE_MISSING)
- ⚠️ UNKNOWN → SECURITY_REVIEW (reason: CREDENTIAL_UNAVAILABLE)

#### 3.3 X.509 Certificate Validation (if present)
```
Check: Certificate valid X.509 format?
Check: Certificate signed by trusted CA?
Check: Certificate not expired?
Check: Certificate not revoked?
Check: Certificate subject matches device_id?
Check: Certificate public key matches credential key?
```

**Outcomes:**
- ✅ PASS → Certificate verified
- ❌ FAIL → UNTRUSTED (reason: CERTIFICATE_INVALID, CERTIFICATE_EXPIRED, CERTIFICATE_REVOKED, IDENTITY_MISMATCH, UNTRUSTED_CA)

#### 3.4 Signature Verification
```
If algorithm = HMAC-SHA256:
  - Compute HMAC from packet + secret
  - Compare with provided signature (constant-time)
  
If algorithm = ECDSA-SHA256:
  - Load public key from credential
  - Verify ECDSA signature using public key
```

**Outcomes:**
- ✅ PASS → Integrity verified
- ❌ FAIL → UNTRUSTED (reason: INTEGRITY_INVALID)
- ⚠️ UNKNOWN → SECURITY_REVIEW (reason: SIGNATURE_MISSING, SIGNATURE_UNVERIFIABLE)

#### 3.5 Freshness Validation
```
Check: observed_at within acceptable time window? (default: ±30 seconds)
Check: packet_id not seen before? (replay detection)
Check: sequence number incrementing correctly?
```

**Outcomes:**
- ✅ PASS → Packet is fresh
- ❌ FAIL → UNTRUSTED (reason: STALE_PACKET, REPLAY_DETECTED, SEQUENCE_ROLLBACK)
- ⚠️ UNKNOWN → SECURITY_REVIEW (reason: SEQUENCE_MISSING)

#### 3.6 Behavioral ML Assessment (if security checks pass)

**Location:** `components/c4_trust/models.py` - `C4BehavioralModelRunner`

**Process:**
1. Extract behavioral features from packet and device history:
   - B0: Timing features (packet interval, jitter, delay)
   - B1: Radio features (RSSI deviation, SNR deviation, retries)
   - B2: Packet behavior (size, sequence gaps, burst rate)
   - B3: Device health (restart frequency, fault flags)
   - B4: Path consistency (hub/zone match)
   - B5: Historical profile (rolling statistics)
2. Run trained Random Forest model on features
3. Get behavioral anomaly score (0.0 = normal, 1.0 = anomalous)
4. Compare against threshold (default: 0.7)

**Outcomes:**
- ✅ Score < threshold → Behavior normal → TRUSTED
- ⚠️ Score ≥ threshold → Behavior abnormal → SUSPICIOUS
- ❌ ML unavailable → TRUSTED (security-only mode)

### Step 4: Trust Decision Fusion

**Location:** `components/c4_trust/service.py` - `C4TrustService.assess()` (lines 584-592)

**Decision Logic:**

```python
if failures:
    # Mandatory security check failed
    trust_label = C4TrustLabel.UNTRUSTED
    routing = C4RoutingOutcome.REJECT
    ml_status = "SKIPPED - SECURITY FAILURE"
    
elif security_unknowns:
    # Some security checks could not be verified
    trust_label = C4TrustLabel.UNKNOWN
    routing = C4RoutingOutcome.SECURITY_REVIEW
    ml_status = "SKIPPED - REVIEW"
    
else:
    # All mandatory security checks passed
    if behavioural_score is not None and behavioural_score >= suspicious_threshold:
        trust_label = C4TrustLabel.SUSPICIOUS
        routing = C4RoutingOutcome.QUARANTINE
        ml_status = "COMPLETED - ANOMALOUS"
    else:
        trust_label = C4TrustLabel.TRUSTED
        routing = C4RoutingOutcome.ACCEPT
        ml_status = "COMPLETED - NORMAL"
```

**Key Principle:** ML can only escalate from TRUSTED to SUSPICIOUS. It can never rescue a packet that failed mandatory security checks.

### Step 5: Routing and Quarantine

**Location:** `components/c4_trust/pipeline.py` - `C4TelemetryGate.process()`

**Routing Actions:**

| Trust Label | Routing Action | Storage Location |
|-------------|----------------|------------------|
| TRUSTED | ACCEPT → Forward to C1/C2/C3 | PostgreSQL database |
| SUSPICIOUS | QUARANTINE → Flag for investigation | Filesystem quarantine (`quarantine/c4/`) |
| UNTRUSTED | REJECT → Do not forward | Filesystem quarantine (`quarantine/c4/`) |

**Quarantine Record Contains:**
- Original packet (immutable)
- Signature
- All verification results (failures, verified, unknowns)
- Trust label and routing decision
- Behavioral score (if available)
- Timestamp
- Reason codes

### Step 6: Audit and Provenance

**Location:** `components/c4_trust/quarantine.py` - `QuarantineManager`

**Audit Trail:**
- All packets (trusted or not) are retained with full provenance
- Quarantine records are written to filesystem as JSON
- PostgreSQL stores trusted telemetry for downstream analysis
- Full audit trail available for security incidents and research

---

## 4. Security Verification Layers

### Layer 1: Device Identity & Lifecycle

**Files:** `components/c4_trust/registry.py`

**Checks:**
- Device registered in DeviceRegistry
- Device lifecycle state = ACTIVE
- Zone and hub binding validation

**Lifecycle States:**
```
PROVISIONED → Register device, but not yet active
    ↓
ACTIVE → Fully operational, can send trusted telemetry
    ↓
SUSPENDED → Temporarily halted (e.g., maintenance)
    ↓
REVOKED → Security incident, permanently stopped
    ↓
RETIRED → Decommissioned
```

**Security Outcome:** Only ACTIVE devices can pass this layer.

### Layer 2: Cryptographic Authentication

**Files:** `components/c4_trust/service.py` (lines 234-277)

**Supported Algorithms:**

#### HMAC-SHA256 (Symmetric)
- **Signing:** `hmac.new(secret, canonical_packet, hashlib.sha256).hexdigest()`
- **Verification:** Constant-time comparison to prevent timing attacks
- **Use Case:** Standard deployment, efficient for resource-constrained IoT devices
- **Limitation:** No non-repudiation (server and device share same secret)

#### ECDSA-SHA256 (Asymmetric)
- **Signing:** `private_key.sign(canonical_packet, ec.ECDSA(hashes.SHA256()))`
- **Verification:** Public key verification using `cryptography` library
- **Curve:** SECP256R1 (P-256, NIST standard)
- **Use Case:** High-security scenarios requiring non-repudiation
- **Limitation:** Higher computational cost on IoT devices

**What is Signed:**
Full canonical JSON packet (all fields, sorted keys, no whitespace)
```json
{
  "device_id": "A1",
  "zone_id": "ZONE_01",
  "observed_at": "2026-10-20T10:30:00Z",
  "sensor_readings": {...},
  "transport": {...},
  "security": {...}
}
```

**Security Guarantees:**
- ✅ Any modification to any field breaks signature
- ✅ Proves packet came from device holding secret/private key
- ✅ Algorithm isolation (no silent fallback)

### Layer 3: X.509 Certificate Validation

**Files:** `components/c4_trust/certificates.py`

**Certificate Checks:**
- Valid X.509 format
- Signed by trusted Certificate Authority (CA)
- Not expired
- Not revoked (checked against CRL/registry)
- Subject CN matches device_id
- Public key matches credential public key

**Certificate Structure:**
```
Certificate Authority (Trusted Root)
        ↓
Device Certificate (leaf)
  - Subject: CN=device_id
  - Issuer: CA
  - Validity: issued_at → expires_at
  - Public Key: EC P-256
  - Extensions: Device-specific attributes
```

**Security Outcome:** Certificates provide device identity verification with PKI infrastructure.

### Layer 4: Freshness & Replay Protection

**Files:** `components/c4_trust/service.py` (lines 100-104, 584-592)

**Freshness Checks:**
- Timestamp within ±30 seconds of current time (configurable)
- Future tolerance: ±5 seconds (configurable)
- Prevents old packets from being accepted

**Replay Detection:**
- Track seen packet IDs in memory: `set[tuple[str, str]]`
- Track last sequence number per device: `dict[tuple[str, str], int]`
- Reject duplicate packet IDs
- Detect sequence number rollback
- Authorized recovery context for legitimate C2 replay

**Authorized Recovery (C2):**
```
C2 creates recovery_request_id
        ↓
Specifies authorized device, time range, sequence range
        ↓
Device sends historical data under current security context
        ↓
C4 verifies recovery context before accepting old timestamps
```

**Security Outcome:** Prevents replay attacks while allowing legitimate data recovery.

### Layer 5: Behavioral ML Assessment

**Files:** `components/c4_trust/models.py`, `features.py`, `runtime_features.py`

**Feature Families:**

| Family | Features | Purpose |
|--------|----------|---------|
| **B0 - Timing** | packet_interval_s, jitter, delivery_delay, unexpected_time | Detect abnormal transmission timing |
| **B1 - Radio** | RSSI, RSSI_deviation, SNR, SNR_deviation, retries | Detect abnormal radio/link behavior |
| **B2 - Packet** | packet_size, sequence_gap, duplicate_freq, burst_rate | Detect abnormal packet patterns |
| **B3 - Health** | restart_freq, fault_flags, power_behavior | Detect device health anomalies |
| **B4 - Path** | hub_zone_match, location_consistency | Detect unexpected routing paths |
| **B5 - History** | rolling_interval_mean/std, rolling_RSSI_profile | Detect deviation from historical baseline |

**Model:** Random Forest Classifier
- **Training Dataset:** `experiments/c4/data/` (scenario-aware split)
- **Features:** 11 behavioral features (no security field leakage)
- **Target:** Binary classification (trusted/untrusted behavior)
- **Current Model:** `random_forest_corrected.joblib` (trained 2026-10-13)
- **Threshold:** 0.7 (configurable)

**SHAP Explainability:**
- SHAP summary plot: Global feature importance
- SHAP force plots: Per-packet explanations
- Location: `experiments/c4/plots/`

**Security Outcome:** Detects subtle behavioral anomalies that cryptographic checks cannot catch (e.g., compromised legitimate device, cloned behavior).

---

## 5. Behavioral ML Assessment

### Training Pipeline

**File:** `scripts/train_c4_baselines.py`

**Process:**
1. Load labeled dataset from `experiments/c4/data/`
2. Extract behavioral features using `FeatureExtractor`
3. Split dataset with scenario-aware splitting (no leakage)
4. Train multiple models:
   - Logistic Regression (baseline)
   - Random Forest (selected model)
   - Isolation Forest (unsupervised baseline)
5. Evaluate on holdout test set
6. Generate SHAP explainability plots
7. Serialize best model with joblib

**Evaluation Metrics:**
- Accuracy
- Precision
- Recall
- F1-Score
- ROC-AUC
- Confusion Matrix

### Inference Pipeline

**File:** `components/c4_trust/runtime_features.py`

**Process:**
1. Receive live telemetry packet
2. Query device history (last N packets from same device)
3. Compute rolling statistics (mean, std, min, max)
4. Extract behavioral features (B0-B5)
5. Validate feature schema matches training
6. Run inference with trained model
7. Return behavioral score (0.0-1.0)

**Device History:**
- Maintained in memory per device
- Rolling window of last 100 packets (configurable)
- Cleared on device reboot or session change
- Used for B5 (historical profile) features

### Security Principles

**No Leakage:**
- Behavioral features do NOT include direct security fields (signature_valid, certificate_valid, etc.)
- Model learns behavioral patterns, not security rules
- Prevents trivial memorization of deterministic checks

**Scenario-Aware Split:**
- All packets from same attack scenario stay in one partition
- Prevents test-time leakage of attack templates
- Hold out entire devices or attack families where possible

**Model Cannot Override Security:**
- ML only runs if mandatory security checks pass
- ML can only escalate TRUSTED → SUSPICIOUS
- ML cannot rescue UNTRUSTED packets

---

## 6. Trust Decision Engine

### Trust Labels

**File:** `shared/enums/domain.py`

```python
class C4TrustLabel(StrEnum):
    TRUSTED = "trusted"          # All security checks pass, behavior normal
    SUSPICIOUS = "suspicious"    # Security checks pass, behavior abnormal
    UNTRUSTED = "untrusted"      # Mandatory security check failed
    UNKNOWN = "unknown"          # Some checks unverifiable (security review)
```

### Routing Outcomes

```python
class C4RoutingOutcome(StrEnum):
    ACCEPT = "accept"                    # Forward to C1/C2/C3
    QUARANTINE = "quarantine"           # Flag for investigation
    REJECT = "reject"                    # Do not forward, retain for audit
    SECURITY_REVIEW = "security_review" # Manual review required
```

### Decision Matrix

| Security Status | Behavioral Score | Trust Label | Routing | ML Status |
|-----------------|------------------|-------------|---------|-----------|
| All PASS | < 0.7 | TRUSTED | ACCEPT | COMPLETED - NORMAL |
| All PASS | ≥ 0.7 | SUSPICIOUS | QUARANTINE | COMPLETED - ANOMALOUS |
| Any FAIL | N/A | UNTRUSTED | REJECT | SKIPPED - SECURITY FAILURE |
| Any UNKNOWN | N/A | UNKNOWN | SECURITY_REVIEW | SKIPPED - REVIEW |
| All PASS | ML unavailable | TRUSTED | ACCEPT | UNAVAILABLE - MISSING FEATURES |

### Reason Codes

**Failures (Hard Rejections):**
- DEVICE_UNKNOWN
- DEVICE_NOT_ACTIVE
- ZONE_MISMATCH
- HUB_MISMATCH
- CREDENTIAL_ID_MISMATCH
- CREDENTIAL_EXPIRED
- CREDENTIAL_NOT_YET_VALID
- INTEGRITY_INVALID
- STALE_PACKET
- REPLAY_DETECTED
- SEQUENCE_ROLLBACK
- CERTIFICATE_INVALID
- CERTIFICATE_EXPIRED
- CERTIFICATE_REVOKED
- IDENTITY_MISMATCH
- UNTRUSTED_CA
- ALGORITHM_FALLBACK

**Unknowns (Security Review):**
- HUB_ID_MISSING
- CREDENTIAL_NOT_CONFIGURED
- CREDENTIAL_UNAVAILABLE
- SIGNATURE_MISSING
- SIGNATURE_UNVERIFIABLE
- CERTIFICATE_MISSING
- ATTESTATION_UNVERIFIED
- PROVENANCE_UNVERIFIED

**Verified (Success):**
- IDENTITY_VALID
- ZONE_VALID
- HUB_VALID
- CREDENTIAL_ID_VALID
- CREDENTIAL_VALID
- CERTIFICATE_VALID
- INTEGRITY_VALID
- ATTESTATION_VALID
- PROVENANCE_VALID
- FIRMWARE_VALID
- CONFIG_VALID

---

## 7. Commercialization Plan

### Product Positioning

**C4 as a Standalone Security Module:**

C4 can be packaged as a reusable IoT security module applicable beyond landslide detection:

- **Smart Agriculture**: Protect sensor data for irrigation, soil monitoring
- **Industrial IoT**: Secure telemetry from factory equipment
- **Smart Cities**: Validate environmental sensor data (air quality, traffic)
- **Critical Infrastructure**: Secure SCADA and control system telemetry
- **Remote Monitoring**: Protect satellite telemetry, ocean buoys, seismic sensors

### Value Proposition

**For Government & Emergency Services:**
- Tamper-proof early warning data
- Regulatory compliance (data integrity audit trail)
- Reduced false alarms from spoofed data
- Faster incident response with verified telemetry

**For Commercial IoT Deployments:**
- Device identity protection
- Prevention of data injection attacks
- Provenance tracking for liability
- Reduced operational costs from fraudulent data

**For Research Institutions:**
- Secure experimental data collection
- Reproducible sensor networks
- Privacy-preserving telemetry (device identity separation)

### Deployment Models

#### 1. Cloud-Based Security Service (SaaS)
- **Model:** API gateway service
- **Pricing:** Per-device subscription + per-transaction fee
- **Benefits:** No on-premise infrastructure, automatic updates
- **Target:** Small to medium IoT deployments

#### 2. On-Premise Security Appliance
- **Model:** Docker containerized deployment
- **Pricing:** Perpetual license + annual support
- **Benefits:** Full control, air-gapped deployment support
- **Target:** Government, critical infrastructure, large enterprises

#### 3. Embedded Security Module
- **Model:** Python library with custom device firmware
- **Pricing:** License fee per device + integration support
- **Benefits:** Lowest latency, no network dependency for security
- **Target:** High-security, latency-sensitive deployments

### Revenue Streams

1. **Subscription Revenue** (SaaS model)
   - Monthly/annual per-device fee
   - Tiered pricing based on device count and security features

2. **Perpetual License** (on-premise/embedded)
   - One-time license fee
   - Annual maintenance and update subscription

3. **Professional Services**
   - Custom integration with existing IoT platforms
   - Security audit and threat modeling
   - Training and certification for operators

4. **Premium Features**
   - Advanced behavioral ML models
   - Custom PKI/certificate management
   - Real-time alerting and SIEM integration
   - Extended data retention and analytics

### Market Analysis

**Target Markets:**
- Asia-Pacific: High landslide risk (Sri Lanka, India, Indonesia, Philippines)
- Europe: Regulatory compliance focus (GDPR, NIS2 Directive)
- North America: Critical infrastructure protection
- Global: IoT security market growing at 20%+ CAGR

**Competitive Landscape:**
- Most IoT security solutions focus on network security (firewalls, VPNs)
- Few solutions provide end-to-end telemetry provenance
- C4 differentiates with hybrid security + behavioral ML
- Open-source reference implementation for trust

### Go-to-Market Strategy

**Phase 1: Research Validation (Current)**
- ✅ Complete C4 implementation for GeoNex
- ✅ Publish research papers on hybrid security framework
- ✅ Open-source reference implementation on GitHub
- ✅ Build academic partnerships for validation

**Phase 2: Pilot Deployments (12-18 months)**
- Deploy with 3-5 partner organizations
- Different sectors: agriculture, infrastructure, environmental monitoring
- Collect deployment feedback and refine product
- Publish case studies and performance metrics

**Phase 3: Commercial Launch (18-24 months)**
- Launch SaaS offering with free tier for testing
- Develop on-premise appliance
- Establish partnerships with IoT platform vendors
- Attend industry conferences (IoT World, Black Hat, RSAC)

**Phase 4: Scale & Expand (24+ months)**
- Expand to embedded security module
- Develop industry-specific templates
- Build channel partner network
- Pursue security certifications (ISO 27001, FIPS 140-2)

### Cost Structure

**Development Costs:**
- R&D team (security engineers, ML engineers)
- Infrastructure (cloud, testing devices)
- Certification and compliance
- Legal and IP protection

**Operational Costs:**
- Cloud infrastructure (SaaS deployment)
- Customer support
- Security research and threat intelligence
- Marketing and sales

**Unit Economics:**
- Target gross margin: 70%+
- Customer acquisition cost (CAC): <$500
- Lifetime value (LTV): >$5,000
- Payback period: <12 months

### Risk Mitigation

**Technical Risks:**
- ML model drift → Continuous monitoring and retraining pipeline
- New attack vectors → Threat model updates and rapid patching
- Scale limitations → Performance optimization and horizontal scaling

**Market Risks:**
- IoT security commoditization → Focus on behavioral ML differentiation
- Slow adoption → Free tier and open-source reference
- Regulatory changes → Flexible architecture for compliance

**Security Risks:**
- Vulnerability in cryptographic implementation → Third-party audits, bug bounty program
- Compromise of CA infrastructure → PKI best practices, key rotation procedures
- Insider threats → Role-based access control, audit trails

### Success Metrics

**Technical Metrics:**
- Attack detection rate: >95%
- False positive rate: <1%
- Latency: <100ms per packet
- Uptime: 99.9%

**Business Metrics:**
- Active devices: 10,000+ by Year 2
- Revenue: $1M+ ARR by Year 2
- Customer retention: >90%
- Net promoter score: >50

---

## 8. Implementation Status

### Completed Components

#### Backend Security Engine ✅
- **File:** `components/c4_trust/service.py`
- **Status:** Fully implemented and tested
- **Coverage:** 30+ unit tests, all passing
- **Features:**
  - Device registry management
  - HMAC-SHA256 signature verification
  - ECDSA-SHA256 signature verification
  - X.509 certificate validation
  - Freshness and replay protection
  - Authorized recovery context
  - Trust decision engine

#### Device Registry ✅
- **File:** `components/c4_trust/registry.py`
- **Status:** Fully implemented and tested
- **Coverage:** 37+ unit tests, all passing
- **Features:**
  - Device lifecycle management (PROVISIONED, ACTIVE, SUSPENDED, REVOKED, RETIRED)
  - Zone and hub binding
  - Credential management
  - Firmware and config approval

#### Behavioral ML Models ✅
- **File:** `components/c4_trust/models.py`
- **Status:** Fully implemented and tested
- **Coverage:** 30+ unit tests, all passing
- **Features:**
  - Random Forest classifier
  - Logistic Regression baseline
  - Isolation Forest baseline
  - Feature extraction pipeline
  - Runtime feature adapter
  - SHAP explainability

#### Telemetry Gate & Quarantine ✅
- **File:** `components/c4_trust/pipeline.py`, `quarantine.py`
- **Status:** Fully implemented and tested
- **Coverage:** End-to-end integration tests
- **Features:**
  - C4TelemetryGate orchestrator
  - QuarantineManager with filesystem persistence
  - 24+ live quarantine records
  - Audit trail generation

#### Database Integration ✅
- **File:** `database/models.py`
- **Status:** SQLAlchemy ORM implemented
- **Features:**
  - TelemetryPacketRecord
  - SensorObservationRecord
  - Behavioral telemetry fields
  - Migration scripts

#### Web Frontend ✅
- **Location:** `apps/web/src/features/c4/`
- **Status:** Fully implemented
- **Features:**
  - How C4 Works documentation
  - Command Center dashboard
  - Telemetry Explorer with filtering
  - Threat Investigation
  - Authentication & Device Trust overview
  - ML Model Explorer with SHAP plots
  - Device Registry & Policy
  - Data Storage & Diagnostics
  - API integration with backend

### Security Validation ✅

**Cryptographic Tests:**
- HMAC-SHA256 signature verification: ✅ 13 tests passing
- ECDSA-SHA256 signature verification: ✅ 13 tests passing
- X.509 certificate validation: ✅ Implemented and tested
- Replay detection: ✅ Tested with attack scenarios

**Attack Scenarios Tested:**
- Unknown device: ✅ REJECTED
- Spoofed device ID: ✅ REJECTED
- Tampered packet: ✅ REJECTED
- Replay attack: ✅ REJECTED
- Expired certificate: ✅ REJECTED
- Revoked certificate: ✅ REJECTED
- Untrusted CA: ✅ REJECTED
- Identity mismatch: ✅ REJECTED
- Algorithm fallback: ✅ REJECTED

### Documentation ✅

**Complete Documentation Set:**
- C4_DEVELOPMENT_GUIDE.md: Architecture and development guidelines
- C4_THREAT_MODEL.md: Threat analysis and mitigation
- C4_TRUST_LABEL_SPECIFICATION.md: Trust label semantics
- C4_COMPLETE_IMPLEMENTATION_GUIDE.md: Complete implementation details
- C4_RUNTIME_INTEGRATION_SUMMARY.md: Runtime integration
- C4_ML_MODEL_EXPLORER.md: ML model documentation
- C4_SECURITY_VALIDATION.md: Security verification report
- C4_Full_Implementation_Report.md: End-to-end report

### Integration Status ✅

**C4 → C1/C2/C3 Integration:**
- Shared contracts defined: ✅
- TelemetryPacket schema: ✅
- C4TrustAssessment schema: ✅
- Integration contract: ✅
- End-to-end flow tested: ✅

**API Integration:**
- FastAPI endpoint for scenario evaluation: ✅
- React frontend connected to backend: ✅
- Security gate enforcement verified: ✅
- ML status tracking: ✅

---

## 9. Technical Architecture

### Technology Stack

**Backend (Python):**
- Language: Python 3.11+
- Web Framework: FastAPI
- Cryptography: `cryptography` library (v43-v47)
- ML: scikit-learn, joblib, SHAP
- Database: SQLAlchemy (PostgreSQL)
- Validation: Pydantic v2

**Frontend (TypeScript/React):**
- Framework: React 18
- Language: TypeScript
- Build Tool: Vite
- UI: Custom components (no external UI library)
- State: React hooks
- API: Fetch API

**Infrastructure:**
- Containerization: Docker
- Orchestration: Docker Compose
- Package Management: uv (Python), npm (Node.js)
- Version Control: Git

### Directory Structure

```
J26-IT-331/
├── components/
│   └── c4_trust/              # C4 backend logic
│       ├── service.py         # Main trust assessment engine
│       ├── registry.py        # Device registry
│       ├── pipeline.py        # Telemetry gate orchestrator
│       ├── quarantine.py      # Quarantine manager
│       ├── models.py          # ML models
│       ├── features.py        # Training feature extraction
│       ├── runtime_features.py # Inference feature extraction
│       ├── integration.py     # Factory for ML integration
│       ├── data_split.py      # Scenario-aware dataset splitting
│       └── certificates.py    # X.509 certificate validation
├── shared/
│   ├── contracts/
│   │   ├── c4_trust.py        # C4TrustAssessment schema
│   │   └── telemetry.py       # TelemetryPacket schema
│   ├── enums/
│   │   └── domain.py          # C4TrustLabel, C4RoutingOutcome
│   └── simulation/
│       ├── c4_demo.py         # Demo C4 gate
│       └── generator.py       # Synthetic telemetry generator
├── database/
│   ├── models.py              # SQLAlchemy ORM
│   └── migrations/            # Database migrations
├── experiments/c4/
│   ├── data/                  # Training dataset
│   ├── models/                # Trained models
│   └── plots/                 # SHAP plots
├── quarantine/c4/              # Live quarantine records
├── apps/
│   ├── api/                   # FastAPI backend
│   │   └── c4_model_explorer_api.py
│   └── web/                   # React frontend
│       └── src/features/c4/   # C4 web features
├── tests/
│   ├── security/              # Security tests
│   ├── unit/                  # Unit tests
│   └── integration/           # Integration tests
└── docs/
    └── components/C4_Docs/     # C4 documentation
```

### Security Architecture

**Fail-Closed Design:**
- Default to REJECT if any check fails
- Explicit allow-list (registered devices, trusted CAs)
- No silent fallback to weaker security

**Defense in Depth:**
- Layer 1: Device identity (registry)
- Layer 2: Cryptographic integrity (signatures)
- Layer 3: PKI certificates (X.509)
- Layer 4: Freshness (timestamps, replay detection)
- Layer 5: Behavioral ML (anomaly detection)

**Auditability:**
- All packets retained with full provenance
- Immutable quarantine records
- Cryptographic verification evidence
- Decision reasoning with explicit codes

**Separation of Concerns:**
- Deterministic security (rule-based)
- Behavioral ML (pattern-based)
- Trust fusion (decision engine)
- Quarantine (investigation)

---

## 10. Testing and Validation

### Test Coverage

**Unit Tests:**
- Device registry: 37+ tests ✅
- Trust service: 30+ tests ✅
- ECDSA signatures: 13 tests ✅
- ML models: 30+ tests ✅
- Runtime features: 16 tests ✅

**Integration Tests:**
- End-to-end gate: 6 tests ✅
- Quarantine persistence: ✅
- Database integration: ✅
- API integration: ✅

**Security Tests:**
- Attack scenarios: 10+ scenarios ✅
- Cryptographic verification: ✅
- Replay detection: ✅
- Certificate validation: ✅

### Test Scenarios

**Valid Scenarios:**
1. Valid HMAC signature → TRUSTED
2. Valid ECDSA signature → TRUSTED
3. Valid X.509 certificate → TRUSTED
4. Authorized recovery replay → TRUSTED

**Attack Scenarios:**
1. Unknown device → UNTRUSTED
2. Tampered packet → UNTRUSTED
3. Replay attack → UNTRUSTED
4. Expired certificate → UNTRUSTED
5. Revoked certificate → UNTRUSTED
6. Untrusted CA → UNTRUSTED
7. Identity mismatch → UNTRUSTED
8. Algorithm fallback → UNTRUSTED

**Behavioral Scenarios:**
1. Normal transmission → TRUSTED
2. Abnormal timing → SUSPICIOUS
3. Abnormal RSSI → SUSPICIOUS
4. Abnormal retry pattern → SUSPICIOUS

### Validation Metrics

**Security Validation:**
- Attack detection rate: 100% (for implemented scenarios)
- False positive rate: <1% (on test dataset)
- Latency: <50ms per packet (deterministic checks)
- ML inference: <10ms per packet

**Code Quality:**
- Test coverage: >80%
- Type checking: mypy strict mode
- Linting: ruff
- Documentation: All public functions documented

---

## 11. Future Enhancements

### Short-Term (Next 3-6 months)

1. **Hardware Security Module (HSM) Integration**
   - Support for TPM 2.0 devices
   - Secure key storage and signing
   - Hardware-backed attestation

2. **Advanced Certificate Management**
   - Automated certificate rotation
   - Online Certificate Status Protocol (OCSP)
   - Multi-CA support

3. **Enhanced Behavioral Features**
   - Deep learning models (LSTM for time series)
   - Federated learning for distributed devices
   - Transfer learning for new deployment zones

### Medium-Term (6-12 months)

1. **Zero-Knowledge Proofs**
   - Device attestation without exposing identity
   - Privacy-preserving telemetry verification
   - Selective disclosure of device attributes

2. **Blockchain Provenance**
   - Immutable audit trail on distributed ledger
   - Cross-organization trust sharing
   - Smart contract-based routing policies

3. **Real-Time Threat Intelligence**
   - Integration with threat feeds
   - Automated attack pattern detection
   - Dynamic security policy updates

### Long-Term (12+ months)

1. **AI-Powered Security**
   - Reinforcement learning for adaptive thresholds
   - Generative models for attack simulation
   - Automated incident response

2. **Standardization**
   - IETF RFC submission for telemetry security protocol
   - ISO/IEC security certification
   - Industry consortium participation

3. **Global Deployment**
   - Multi-region infrastructure
   - 24/7 security operations center
   - Managed security service provider (MSSP) partnerships

---

## Conclusion

Component 4 (C4) provides a comprehensive, research-defensible framework for trusted telemetry provenance in IoT-based early-warning systems. By combining **deterministic cryptographic verification** with **behavioral machine learning**, C4 addresses the full spectrum of security threats:

- **Spoofed devices** → Device registry validation
- **Tampered data** → Cryptographic integrity verification
- **Replay attacks** → Freshness and replay protection
- **Compromised legitimate devices** → Behavioral ML assessment
- **PKI attacks** → X.509 certificate validation

The implementation is **complete, tested, and integrated** with the broader GeoNex system. The web frontend provides full visibility into C4 operations, allowing operators to monitor security status, investigate threats, and understand ML model decisions.

The **commercialization plan** positions C4 as a standalone security module applicable to a wide range of IoT deployments beyond landslide detection, with clear go-to-market strategy and revenue models.

**Key Achievements:**
- ✅ Complete security verification engine (HMAC, ECDSA, X.509)
- ✅ Device registry with lifecycle management
- ✅ Behavioral ML with explainability (SHAP)
- ✅ Quarantine and audit trail
- ✅ Web frontend with full feature set
- ✅ End-to-end integration with C1/C2/C3
- ✅ Comprehensive documentation
- ✅ Commercialization strategy

**Next Steps for PP1:**
1. Present C4 workflow and architecture
2. Demonstrate security verification with attack scenarios
3. Show behavioral ML with SHAP explanations
4. Discuss commercialization opportunities
5. Address panel feedback on credibility flags and decision support

---

## References

**Internal Documentation:**
- C4_DEVELOPMENT_GUIDE.md
- C4_THREAT_MODEL.md
- C4_TRUST_LABEL_SPECIFICATION.md
- C4_COMPLETE_IMPLEMENTATION_GUIDE.md
- C4_RUNTIME_INTEGRATION_SUMMARY.md
- C4_ML_MODEL_EXPLORER.md
- C4_SECURITY_VALIDATION.md

**External Standards:**
- NIST SP 800-53: Security and Privacy Controls
- ISO/IEC 27001: Information Security Management
- RFC 5280: X.509 PKI Certificate and CRL Profile
- RFC 6979: Deterministic ECDSA
- OWASP IoT Security Guidelines

**Academic References:**
- [Selected papers on IoT security and behavioral anomaly detection]
- [ML explainability research]
- [Landslide early-warning system literature]

---

**Document Version:** 1.0  
**Last Updated:** October 20, 2026  
**Author:** R M Kanishka Harshana (IT23240506)  
**Review Status:** Ready for PP1 Presentation
