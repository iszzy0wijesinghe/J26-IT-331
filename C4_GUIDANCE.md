# Component 4 (C4 Trust Assessment) - Complete Guidance

## Overview

Component 4 (C4 Trust Assessment) is a comprehensive security trust evaluation system for IoT telemetry. It validates the authenticity, integrity, and behavioral patterns of incoming telemetry packets before routing them through the system.

## Dashboard Access

- **URL**: http://127.0.0.1:5173/c4
- **Backend API**: http://localhost:8000
- **Frontend Port**: 5173 (Vite dev server)

## Available Test Scenarios

The C4 dashboard provides multiple test scenarios to validate different security aspects. Each scenario generates **1 assessment result** when run.

### HMAC-based Scenarios

#### 1. Run Valid Telemetry (HMAC)
- **Backend Key**: `valid_hmac`
- **Description**: Tests valid telemetry packets signed with HMAC-SHA256
- **Expected Result**: 1 assessment - Should PASS all security checks
- **Signature Algorithm**: hmac-sha256
- **Use Case**: Validates that properly signed HMAC packets are accepted

#### 2. Test Tampered (HMAC)
- **Backend Key**: `tampered_hmac`
- **Description**: Tests tampered packets with valid HMAC signature
- **Expected Result**: 1 assessment - Should FAIL due to tampering
- **Signature Algorithm**: hmac-sha256
- **Use Case**: Detects message tampering even with valid signature

#### 3. Test Replay Attack (HMAC)
- **Backend Key**: `replay_hmac`
- **Description**: Tests replay attack with duplicate packet
- **Expected Result**: 2 assessments - First packet ACCEPT, second packet REJECTED
- **Signature Algorithm**: hmac-sha256
- **Use Case**: Validates replay attack detection mechanism

### ECDSA-based Scenarios

#### 4. Run Valid X.509 + ECDSA
- **Backend Key**: `valid_ecdsa`
- **Description**: Tests valid telemetry with X.509 certificate and ECDSA signature
- **Expected Result**: 1 assessment - Should PASS all security checks
- **Signature Algorithm**: ecdsa-sha256
- **Use Case**: Validates PKI-based authentication with certificates

#### 5. Test Tampered ECDSA
- **Backend Key**: `tampered_ecdsa`
- **Description**: Tests tampered packet with valid ECDSA signature
- **Expected Result**: 1 assessment - Should FAIL due to tampering
- **Signature Algorithm**: ecdsa-sha256
- **Use Case**: Detects tampering in PKI-protected packets

#### 6. Test Alg Fallback Rejection
- **Backend Key**: `fallback_rejection`
- **Description**: Tests algorithm fallback rejection
- **Expected Result**: 1 assessment - Should FAIL due to algorithm rejection
- **Use Case**: Validates cryptographic algorithm downgrade protection

### Certificate-based Scenarios

#### 7. Test Expired (X.509)
- **Backend Key**: `expired_x509`
- **Description**: Tests packet with expired X.509 certificate
- **Expected Result**: 1 assessment - Should FAIL due to expired certificate
- **Use Case**: Validates certificate expiration checking

#### 8. Test Untrusted CA (X.509)
- **Backend Key**: `untrusted_ca_x509`
- **Description**: Tests packet signed by untrusted certificate authority
- **Expected Result**: 1 assessment - Should FAIL due to untrusted CA
- **Use Case**: Validates certificate chain of trust verification

#### 9. Test Identity Mismatch Cert (X.509)
- **Backend Key**: `mismatched_identity_x509`
- **Description**: Tests certificate identity mismatch
- **Expected Result**: 1 assessment - Should FAIL due to identity mismatch
- **Use Case**: Validates certificate identity verification

#### 10. Test Revoked (X.509)
- **Backend Key**: `revoked_x509`
- **Description**: Tests packet with revoked certificate
- **Expected Result**: 1 assessment - Should FAIL due to revoked certificate
- **Use Case**: Validates certificate revocation checking

## How to Run Scenarios

### Via Web Dashboard
1. Navigate to http://127.0.0.1:5173/c4
2. In the sidebar, expand the desired scenario category (HMAC, ECDSA, or CERT)
3. Click the scenario button
4. View results in Command Center, Telemetry Explorer, or Threat Investigation

### Via API
```bash
# Run a specific scenario
curl -X POST http://localhost:8000/api/c4/scenarios/run \
  -H "Content-Type: application/json" \
  -d '{"scenario": "valid_hmac"}'

# List all available scenarios
curl http://localhost:8000/api/c4/scenarios
```

## Command Center Metrics

The Command Center displays session metrics based on assessment results:

### Key Metrics
- **Assessed**: Total number of assessment results in current session
- **Trusted**: Number of packets with trust_label == TRUSTED
- **Accepted**: Number of packets with routing_outcome == ACCEPT
- **Auth failures**: Number of packets where mandatory_security_pass is false
- **Rejected**: Number of packets with trust_label == UNTRUSTED
- **Suspicious**: Number of packets with trust_label == SUSPICIOUS
- **Unknown**: Number of packets with trust_label == UNKNOWN
- **Quarantined**: Number of packets quarantined
- **ML ran**: Number of packets where behavioral_score was generated

### Trust Labels
- **TRUSTED**: Packet passed all security checks
- **UNTRUSTED**: Packet failed critical security checks
- **SUSPICIOUS**: Packet has concerning patterns but not critical failures
- **UNKNOWN**: Insufficient information to determine trust level

### Routing Outcomes
- **ACCEPT**: Packet passed security gate and was accepted
- **REJECT**: Packet failed security gate and was rejected
- **QUARANTINE**: Packet was quarantined for further investigation
- **UNKNOWN**: Routing decision could not be determined

## Security Check Categories

### 1. Authentication Checks
- Device registration validation
- Credential verification
- Certificate chain validation (for ECDSA)
- Signature verification (HMAC or ECDSA)

### 2. Integrity Checks
- Message tampering detection
- Signature integrity validation
- Firmware hash verification (if configured)
- Configuration hash verification (if configured)

### 3. Freshness Checks
- Sequence number validation
- Replay attack detection
- Timestamp validation
- Clock skew tolerance

### 4. Authorization Checks
- Zone membership verification
- Hub assignment validation
- Device lifecycle state check
- Role-based access control

### 5. Behavioral Analysis
- ML-based anomaly detection
- Behavioral scoring (0.0 to 1.0)
- Pattern recognition
- Historical behavior comparison

## Technical Architecture

### Backend Components
- **C4DemoBackend**: Simulation backend for demo scenarios
- **C4TrustService**: Core trust assessment logic
- **C4TelemetryGate**: Security gate for packet processing
- **DeviceRegistry**: Device and credential management
- **QuarantineManager**: Quarantine handling for suspicious packets

### Frontend Components
- **CommandCenter**: Session metrics and overview
- **TelemetryExplorer**: Detailed packet inspection
- **ThreatInvestigation**: Security analysis and threat detection
- **ScenarioButtons**: Scenario execution interface
- **Authentication**: Authentication status display

### Data Flow
1. User clicks scenario button
2. Frontend sends request to backend API
3. Backend generates synthetic telemetry packet
4. Packet is signed (HMAC or ECDSA)
5. Packet is processed through C4TelemetryGate
6. Security checks are performed
7. ML inference runs if security PASS
8. Assessment result is generated
9. Result is returned to frontend
10. Frontend displays results in Command Center

## ML-only-if-PASS Rule

The security gate enforces a strict rule: **ML inference only runs if mandatory security checks pass**.

- If security PASS → ML runs → behavioral score generated
- If security FAIL → ML skipped → behavioral_score is null
- This ensures resources are not wasted on obviously malicious packets

## Session vs Database

### Session Assessments
- Stored in browser session state
- Cleared when browser session ends
- Used for dashboard metrics
- NOT persisted to PostgreSQL

### Database Records
- Real telemetry from ESP32 devices
- Persisted in PostgreSQL
- Separate from demo scenarios
- Requires separate ingestion script

## Troubleshooting

### Issue: Assessment count is not 1
- **Fix**: Modified `c4_backend.py` to process only first item for `valid_hmac` scenario
- **Location**: `apps/c4_frontend/c4_backend.py` line 421-439

### Issue: Backend not responding
- Check if FastAPI server is running on port 8000
- Verify no firewall blocking localhost:8000
- Check backend logs for errors

### Issue: Frontend not loading
- Check if Vite dev server is running on port 5173
- Verify no firewall blocking localhost:5173
- Check browser console for errors

### Issue: ML model not found
- Verify model path: `experiments/c4/models/random_forest_corrected.joblib`
- Check if model file exists
- Verify model permissions

## File Locations

### Backend
- **Main Backend**: `apps/c4_frontend/c4_backend.py`
- **Trust Service**: `components/c4_trust/service.py`
- **Pipeline**: `components/c4_trust/pipeline.py`
- **API Endpoints**: `apps/api/c4_model_explorer_api.py`

### Frontend
- **Main Page**: `apps/web/src/features/c4/pages/C4Page.tsx`
- **Command Center**: `apps/web/src/features/c4/components/CommandCenter.tsx`
- **Scenario Buttons**: `apps/web/src/features/c4/components/ScenarioButtons.tsx`
- **Telemetry Explorer**: `apps/web/src/features/c4/components/TelemetryExplorer.tsx`
- **Threat Investigation**: `apps/web/src/features/c4/components/ThreatInvestigation.tsx`
- **Types**: `apps/web/src/features/c4/types/index.ts`

### Models
- **ML Model**: `experiments/c4/models/random_forest_corrected.joblib`
- **Test Data**: `experiments/c4/data/C4_test_corrected.csv`

## API Endpoints

### Run Scenario
```
POST /api/c4/scenarios/run
Body: {"scenario": "valid_hmac"}
Response: {"scenario": "valid_hmac", "results": [...], "count": 1, "message": "..."}
```

### List Scenarios
```
GET /api/c4/scenarios
Response: {"scenarios": [{"key": "valid_hmac", "description": "..."}, ...]}
```

## Best Practices

1. **Clear Results**: Click "Clear Results" button before testing new scenarios to avoid mixing results
2. **Test Incrementally**: Start with valid scenarios, then test failure scenarios
3. **Review Metrics**: Check Command Center metrics after each scenario to understand impact
4. **Inspect Details**: Use Telemetry Explorer to view detailed packet information
5. **Investigate Threats**: Use Threat Investigation to analyze security failures
6. **Verify Expected**: Compare actual results with expected outcomes listed above

## Security Features Demonstrated

1. **Cryptographic Authentication**: HMAC-SHA256 and ECDSA-SHA256 signatures
2. **PKI Infrastructure**: X.509 certificates with CA chain validation
3. **Integrity Protection**: Tampering detection via signature verification
4. **Replay Protection**: Duplicate packet detection and rejection
5. **Certificate Validation**: Expiration, revocation, and identity checks
6. **Behavioral Analysis**: ML-based anomaly detection
7. **Security Gate Enforcement**: ML-only-if-PASS rule
8. **Quarantine System**: Suspicious packet isolation
9. **Multi-layer Security**: Authentication, integrity, freshness, authorization, behavioral

## Summary

Component 4 provides a comprehensive security assessment framework for IoT telemetry. The 10 available scenarios cover all major security aspects:
- 3 HMAC scenarios (valid, tampered, replay)
- 3 ECDSA scenarios (valid, tampered, algorithm fallback)
- 4 Certificate scenarios (expired, untrusted CA, identity mismatch, revoked)

Each scenario generates exactly **1 assessment result** (except replay which generates 2 to demonstrate the mechanism). Use this guidance to systematically test and verify all security features of the C4 Trust Assessment system.
