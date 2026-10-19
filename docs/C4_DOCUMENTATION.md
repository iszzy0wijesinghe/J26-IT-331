# C4: Trusted Telemetry Provenance and Device Attestation

## Overview

C4 is the trust gate for GeoNex telemetry. It decides whether a packet is authentic enough to enter C1 (the Rainfall Regime-Aware Sensor Credibility Classification component). C4 implements cryptographic verification, device identity validation, and behavioral machine learning to ensure telemetry integrity and authenticity.

## Architecture

### Core Components

1. **C4TrustService** - Manages device credentials, cryptographic signatures, and trust assessments
2. **C4TelemetryGate** - The main pipeline that processes telemetry packets through security checks
3. **C4BehavioralModelRunner** - Optional ML component that analyzes device behavior patterns
4. **QuarantineManager** - Handles isolation of suspicious packets and evidence collection
5. **DeviceRegistry** - Maintains device lifecycle states and credential mappings

### Runtime Path

```
Sidebar button → C4DemoBackend.run_simulation()
→ generate_scheduled_demo_telemetry()
→ C4TrustService.sign_packet() or sign_packet_ecdsa()
→ C4TelemetryGate.process()
→ C4TrustService.assess()
→ optional C4BehavioralModelRunner
→ QuarantineManager
→ Streamlit session_state.c4_results
```

## Security Controls

### Mandatory Security Checks

These checks must pass for a packet to be considered for C1 processing:

| Control | Description | Code Location | Status |
|---------|-------------|---------------|--------|
| Device Identity | Device must be registered and in ACTIVE lifecycle state | DeviceRegistry.is_active | Mandatory |
| Zone/Hub Binding | Packet zone_id must match device registration, gateway_id must match hub | Compare packet.zone_id and transport.gateway_id | Mandatory |
| Credential Verification | Credential ID must be valid and associated with device | C4TrustService._verify_credential | Mandatory |
| HMAC-SHA256 | Symmetric shared secret integrity verification | C4TrustService.sign_packet / _verify_signature | Conditional |
| ECDSA-SHA256 P-256 | Asymmetric public-key signature verification | sign_packet_ecdsa / _verify_signature | Conditional |
| X.509 Certificate | Certificate validation, CA trust, expiration check | X509CertificateValidator.validate | Conditional |
| Freshness | Packet age must be within max_age_seconds (default: 30s) | C4TrustService.assess | Mandatory |
| Replay Protection | Packet ID must be unique, sequence must be monotonic | C4TrustService.assess | Mandatory |
| Attestation | Device attestation evidence must be verifiable | Custom verifier in C4DemoBackend | Mandatory |
| Provenance | Telemetry provenance evidence must be verifiable | Custom verifier in C4DemoBackend | Mandatory |

### Advisory Security Checks

These checks can influence routing but cannot override mandatory failures:

| Control | Description | Threshold |
|---------|-------------|-----------|
| Behavioral ML | Random Forest anomaly score analysis | Score < 0.70 for TRUSTED |

## Cryptographic Mechanisms

### HMAC-SHA256

- **Purpose**: Symmetric integrity verification using shared secrets
- **Implementation**: `C4TrustService.sign_packet()` and `_verify_signature()`
- **Use Case**: When credential algorithm is HMAC
- **Key Management**: Secrets stored in DeviceCredential, never exposed in UI
- **Performance**: Fast symmetric operation, suitable for high-throughput scenarios

### ECDSA-SHA256 (P-256)

- **Purpose**: Asymmetric signature verification using public-key cryptography
- **Implementation**: `C4TrustService.sign_packet_ecdsa()` and `_verify_signature()`
- **Use Case**: When credential algorithm is ECDSA
- **Key Management**: Private keys generated in-memory for demo, public keys in DeviceCredential
- **Certificate Binding**: Typically paired with X.509 device certificates
- **Performance**: Slower than HMAC but provides non-repudiation

### X.509 Certificates

- **Purpose**: Identity binding and PKI trust chain validation
- **Implementation**: `X509CertificateValidator.validate()`
- **Validation Checks**:
  - Certificate signature verification against trusted CA
  - Certificate validity period (not before / not after)
  - Certificate revocation status (CRL or OCSP)
  - Subject identity matching device_id
  - Chain of trust to root CA
- **Demo Setup**: Test CA and device certificates generated in-memory

## Trust Labels and Routing Outcomes

### Trust Labels

| Label | Meaning | ML Influence |
|-------|---------|--------------|
| TRUSTED | All mandatory checks passed, ML score below threshold | Acceptable for C1 |
| UNTRUSTED | One or more mandatory checks failed | ML not consulted, rejected |
| SUSPICIOUS | Mandatory checks passed, ML score above threshold | Requires quarantine/review |
| UNKNOWN | Insufficient evidence or ML unavailable | Requires manual review |

### Routing Outcomes

| Outcome | Description | Eligible for C1 |
|---------|-------------|-----------------|
| ACCEPT | All checks passed, trusted routing | Yes |
| REJECT | Mandatory check failed | No |
| QUARANTINE | Suspicious pattern detected, requires review | No (pending review) |
| SECURITY_REVIEW | Insufficient evidence, requires manual investigation | No (pending review) |

## Behavioral Machine Learning

### Model Details

- **Model Type**: Random Forest Classifier
- **Features**: 18 behavioral features spanning communication, health, timing, and identity
- **Training Data**: Offline C4 dataset in `experiments/c4/data/`
- **Threshold**: Anomaly score >= 0.70 triggers SUSPICIOUS/QUARANTINE routing
- **Runtime Path**: `C4BehavioralModelRunner` (optional, only runs after mandatory checks pass)

### Feature Schema

| Feature Family | Features | Description |
|---------------|----------|-------------|
| Communication | rssi_dbm, snr_db, retry_count, tx_interval_s | Signal quality and transmission metrics |
| Health | battery_pct, battery_voltage, sensor_fault_flag | Device health indicators |
| Timing | freshness_age_s, observed_at, received_at | Packet timing and freshness |
| Sequence | sequence_no, boot_id | Packet ordering and device sessions |
| Identity | zone_id, hub_id, device_kind | Device topology and classification |
| Behavioral | recent_score_history, variance | Aggregated behavioral patterns |

### ML Constraints

- ML can only influence packets that already passed mandatory security checks
- ML cannot override cryptographic failures
- ML cannot override identity mismatches
- ML cannot override certificate validation failures
- ML is advisory in nature, not a primary security control

## Device Lifecycle Management

### Lifecycle States

| State | Description | Can Send Telemetry? |
|-------|-------------|---------------------|
| PROVISIONED | Registered but not yet authorized | No |
| ACTIVE | Authorized and operational | Yes |
| SUSPENDED | Temporarily blocked (e.g., maintenance) | No |
| REVOKED | Permanently untrusted (e.g., compromise) | No |
| RETIRED | Decommissioned device | No |

### Registry Operations

- **register()**: Add device to registry with credential
- **activate()**: Transition to ACTIVE state
- **suspend()**: Transition to SUSPENDED state
- **revoke()**: Transition to REVOKED state
- **update_credential()**: Update device credential
- **update_lifecycle_state()**: Change lifecycle state
- **list_devices()**: Query all registered devices

## Quarantine Management

### Quarantine Triggers

- ML anomaly score >= 0.70
- Suspicious pattern detected (configurable rules)
- Manual quarantine request
- Evidence collection for investigation

### Quarantine Data

Quarantine records include:
- Full packet data (TelemetryPacket)
- Trust assessment (C4TrustAssessment)
- Reason codes for quarantine
- Timestamp and source information
- ML model predictions (if applicable)

### Quarantine Storage

- **Demo UI**: Temporary directory, deleted on session close
- **Production**: `quarantine/c4/` directory with JSON files
- **Database**: Optional PostgreSQL integration for persistent audit trail

## Scenarios and Test Cases

### HMAC Scenarios

1. **Valid Telemetry (HMAC)** - Properly signed packet with valid HMAC
2. **Tampered (HMAC)** - Packet modified after signing, signature invalid
3. **Replay Attack (HMAC)** - Duplicate packet_id or non-increasing sequence

### ECDSA Scenarios

1. **Valid X.509 + ECDSA** - Properly signed packet with valid certificate
2. **Tampered (ECDSA)** - Packet modified after signing, signature invalid
3. **Expired Certificate** - Certificate past validity period
4. **Untrusted CA** - Certificate from untrusted certificate authority
5. **Identity Mismatch** - Certificate subject does not match device_id
6. **Revoked Certificate** - Certificate present in revocation list
7. **Algorithm Fallback** - ECDSA credential with HMAC signature (rejected)

## Data Storage

### Storage Locations

| Data Item | Location | Persistence | Access Method |
|-----------|----------|--------------|---------------|
| Dashboard assessments | Streamlit session_state (React state) | No (session only) | UI memory |
| Dashboard quarantine files | TemporaryDirectory | No (deleted on close) | File system |
| Default quarantine JSON | quarantine/c4/ | Yes (disk) | File system |
| Offline C4 dataset | experiments/c4/data/*.csv | Yes (disk) | Pandas/ML Explorer |
| Saved models | experiments/c4/models/*.joblib | Yes (disk) | TrainedModel.load |
| Demo registry | In-memory DeviceRegistry | No (runtime only) | API calls |
| PostgreSQL telemetry | geonex.telemetry_packets | Yes (database) | SQLAlchemy |

### Database Schema

**telemetry_packets table**:
- packet_id (PK)
- device_id
- zone_id
- hub_id
- observed_at
- received_at
- trust_label
- routing_outcome
- behavioural_score
- reason_codes (JSONB)
- quarantine_id (FK)
- persisted_at

## Web Application

### Frontend Features

The C4 web application provides the following pages:

1. **How C4 Works** - Documentation of architecture, runtime path, and glossary
2. **Command Center** - Security operations summary with real-time metrics
3. **Telemetry Explorer** - Detailed packet inspection with filtering
4. **Threat Investigation** - Analysis of flagged packets and reason codes
5. **Authentication & Device Trust** - Overview of cryptographic controls
6. **ML Model Explorer** - Model inspection, feature importance, SHAP explanations
7. **Device Registry & Policy** - Device lifecycle and policy documentation
8. **Data Storage & Diagnostics** - System diagnostics and storage inventory
9. **Model & Policy** - Security policy reference and routing decisions

### Running the Web Application

```bash
cd apps/web
npm install
npm run dev
```

The development server runs at `http://127.0.0.1:5173/`

### API Integration

The React components currently use mock data. To integrate with the Python backend:

1. Create FastAPI/Flask endpoints for:
   - `/api/c4/run-scenario` - Execute simulation scenarios
   - `/api/c4/diagnostics` - System diagnostics
   - `/api/c4/registry` - Device registry data
   - `/api/c4/ml-profile` - ML model information
   - `/api/c4/results` - Query assessment results

2. Update React components to call these APIs
3. Implement proper error handling and loading states
4. Add authentication/authorization if needed

## Security Policy (C4_POLICY_1.1)

### Policy Principles

1. **Defense in Depth**: Multiple independent security controls
2. **Fail Secure**: Default to reject on uncertainty
3. **Explicit Trust**: Trust must be explicitly established and verified
4. **Audit Trail**: All decisions must be logged with evidence
5. **Non-Repudiation**: Cryptographic signatures provide accountability

### Policy Enforcement

- Mandatory checks are enforced by C4TelemetryGate
- ML scoring is advisory and cannot override mandatory failures
- Quarantine is automatic for suspicious patterns
- Manual review required for UNKNOWN/SECURITY_REVIEW outcomes
- Audit logs stored in quarantine records and optionally in database

## Development Guidelines

### Adding New Security Controls

1. Implement check in `C4TrustService.assess()`
2. Add appropriate reason codes
3. Update documentation
4. Add test scenarios
5. Update policy documentation

### Training New ML Models

1. Prepare dataset in `experiments/c4/data/`
2. Use training scripts in `scripts/`
3. Save model to `experiments/c4/models/`
4. Update model catalog in ML Explorer
5. Validate holdout performance
6. Generate SHAP explanations with `scripts/explain_c4_model.py`

### Modifying Device Registry

1. Update `DeviceRegistry` class
2. Ensure backward compatibility
3. Add migration scripts if needed
4. Update topology in `shared/simulation/topology.py`
5. Test with demo scenarios

## Troubleshooting

### Common Issues

**Issue**: Packets rejected with INTEGRITY_INVALID
- **Cause**: Signature verification failed
- **Solution**: Check credential secret/key, verify signing algorithm

**Issue**: Packets rejected with REPLAY_DETECTED
- **Cause**: Duplicate packet_id or non-increasing sequence
- **Solution**: Ensure unique packet IDs and monotonic sequences

**Issue**: ML not running
- **Cause**: Model file missing or mandatory checks failed
- **Solution**: Check model path, verify mandatory checks pass

**Issue**: Certificate validation failed
- **Cause**: Expired, untrusted CA, or identity mismatch
- **Solution**: Check certificate validity, CA trust chain, subject matching

## References

- **Code Locations**:
  - Trust service: `components/c4_trust/`
  - Pipeline: `components/c4_trust/pipeline.py`
  - ML models: `experiments/c4/models/`
  - Web frontend: `apps/web/src/features/c4/`

- **Documentation**:
  - Architecture specs: `docs/`
  - API documentation: To be added
  - Training guides: `experiments/c4/README.md`

- **External Standards**:
  - X.509: RFC 5280
  - ECDSA: FIPS 186-4
  - HMAC: FIPS 198-1
  - PKI: NIST SP 800-57

## Glossary

| Term | Meaning |
|------|---------|
| TelemetryPacket | Normalized packet contract in shared/contracts/telemetry.py |
| Mandatory security | Identity, zone/hub, cert, signature, freshness, replay, attestation, provenance |
| Behavioral score | Anomaly score 1 - P(Trusted) from the Random Forest |
| Session result | A row in UI memory; lost on refresh or Clear Session |
| Quarantine JSON | Evidence file; demo uses temp folder deleted after each run |
| Trust label | Classification: TRUSTED, UNTRUSTED, SUSPICIOUS, UNKNOWN |
| Routing outcome | Decision: ACCEPT, REJECT, QUARANTINE, SECURITY_REVIEW |
| Reason code | Specific security check result (e.g., INTEGRITY_VALID, ZONE_INVALID) |
| Credential | Secret material (HMAC secret or ECDSA private key) for signing |
| Certificate | X.509 certificate binding public key to device identity |
| CA | Certificate Authority that issues and signs device certificates |

## Version History

- **v1.1** - Current version with ECDSA, X.509, and ML integration
- **v1.0** - Initial version with HMAC-only support
