# C4 Threat Model

**Project:** GeoNex - Smart Landslide Early Warning Prediction System
**Component:** C4 - Trusted Telemetry Provenance and Device Attestation
**Document:** Threat Model
**Version:** 1.0
**Date:** 2026-10-11

---

## 1. Overview

This threat model identifies the assets that C4 must protect, potential adversaries, attack paths, observable evidence, deterministic protections, ML-relevant evidence, expected responses, and limitations for the GeoNex landslide early warning system.

---

## 2. Assets to Protect

### 2.1 Primary Assets

| Asset | Description | Impact if Compromised |
|-------|-------------|----------------------|
| **Device Identity** | Stable device identifier linked to registration | Spoofed devices can inject false telemetry |
| **Telemetry Integrity** | Assurance that payload has not been modified | Tampered measurements can cause false/missed warnings |
| **Telemetry Freshness** | Assurance that data is current, not stale replay | Stale data can mask current landslide risk |
| **Sequence Continuity** | Monotonic progression of packet sequence numbers | Replay attacks or rollback can conceal device issues |
| **Sensor Provenance** | Traceability from observation through pipeline | Loss of audit trail prevents incident analysis |
| **Mode/Control Messages** | Commands sent to devices (sampling, backup activation) | Unauthorized commands can disrupt monitoring |
| **Recovery Requests** | C2 requests for historical data replay | Unauthorized replay can flood system with stale data |
| **Historical Replay Authorization** | Legitimate C2 recovery context | Must distinguish from malicious replay |
| **Model/Decision Input Eligibility** | Which packets are allowed into C1/C3 | Untrusted data entering models corrupts predictions |
| **Audit Records** | Security event logs and provenance | Loss prevents forensic analysis and improvement |

---

## 3. Adversary Capabilities

### 3.1 Threat Actors

| Actor | Capability | Motivation |
|-------|------------|------------|
| **Unauthorized Device** | Can transmit packets, spoof device IDs | Inject false data, disrupt monitoring |
| **Compromised Legitimate Device** | Has valid credentials, can modify behavior | Inject plausible false data, evade detection |
| **Network Attacker** | Can intercept, replay, modify packets in transit | Man-in-the-middle, replay, payload tampering |
| **Insider/Social Engineering** | May obtain credentials, configuration | Misuse legitimate access for malicious purposes |
| **Environmental/RF Interference** | Can degrade radio conditions naturally | Mimics attack patterns in RSSI/SNR behavior |

### 3.2 Assumptions

- Adversary can capture and analyze legitimate telemetry packets
- Adversary may obtain device credentials through compromise or poor secret management
- Adversary cannot easily compromise hardware TPM/secure element (not implemented in prototype)
- Adversary has no physical access to devices in production deployment
- Network between gateway and main computing system is trusted (simplifying assumption for prototype)

---

## 4. Threat Scenarios

### 4.1 T1: Unknown/Unregistered Device

**Asset:** Device Identity
**Adversary:** Unauthorized Device
**Attack Path:**
1. Attacker crafts packet with unregistered device_id
2. Packet claims to be from legitimate zone
3. No credential exists in registry

**Observable Evidence:**
- `device_id` not in device registry
- `zone_registered` mismatch with expected zone
- `cert_registered` = False
- `hub_registered` = False

**Deterministic Protection:**
- Device registry lookup
- Reject packets from unknown devices
- Log security event

**ML-Relevant Evidence:**
- Device identity is primarily a deterministic check
- ML features: `zone_registered`, `hub_registered` flags
- Risk: Model may learn device_id shortcuts if not excluded

**Expected Response:**
- Trust label: UNTRUSTED
- Routing outcome: REJECT
- Reason codes: DEVICE_UNKNOWN
- Quarantine packet for audit

**Limitations:**
- None for this threat (deterministic check is sufficient)

---

### 4.2 T2: Spoofed Device Identifier

**Asset:** Device Identity
**Adversary:** Unauthorized Device / Network Attacker
**Attack Path:**
1. Attacker observes legitimate device_id from packet capture
2. Attacker crafts new packet with spoofed device_id
3. Attacker may lack valid credentials or uses stolen credentials

**Observable Evidence:**
- Correct device_id but invalid credential_id
- Signature verification fails if credentials stolen
- Unexpected transmission pattern (timing, RSSI)
- Path/location mismatch

**Deterministic Protection:**
- Credential verification
- HMAC signature validation
- Sequence number validation

**ML-Relevant Evidence:**
- RSSI deviation from device baseline
- Unexpected packet timing/interval
- Path/location inconsistency
- Historical behavioral profile deviation

**Expected Response:**
- If credentials invalid: UNTRUSTED (deterministic)
- If credentials valid but behavior anomalous: SUSPICIOUS (behavioral)

**Limitations:**
- If attacker obtains valid credentials, deterministic checks pass
- Behavioral ML may detect but requires sufficient behavioral diversity
- RF environment changes can mimic spoofing

---

### 4.3 T3: Invalid Authentication / Integrity Failure

**Asset:** Telemetry Integrity
**Adversary:** Compromised Device / Network Attacker
**Attack Path:**
1. Attacker modifies payload after signing
2. Attacker uses invalid credential
3. Attacker fails to provide signature

**Observable Evidence:**
- `signature_valid` = False
- `channel_auth_ok` = False
- HMAC verification fails
- Payload hash mismatch

**Deterministic Protection:**
- HMAC signature verification
- Credential ID validation
- Integrity present check

**ML-Relevant Evidence:**
- Not applicable (purely deterministic)
- Risk: If signature_valid is used as ML feature, creates leakage

**Expected Response:**
- Trust label: UNTRUSTED
- Routing outcome: REJECT
- Reason codes: INTEGRITY_INVALID, CREDENTIAL_ID_MISMATCH

**Limitations:**
- None (cryptographic verification is authoritative)

---

### 4.4 T4: Payload Tampering

**Asset:** Telemetry Integrity
**Adversary:** Network Attacker / Compromised Device
**Attack Path:**
1. Attacker intercepts legitimate packet
2. Attacker modifies sensor readings (e.g., soil moisture, rainfall)
3. Attacker attempts to bypass integrity check

**Observable Evidence:**
- `payload_hash_match` = False
- Sudden implausible sensor value changes
- Inconsistent with neighboring devices
- Signature verification fails

**Deterministic Protection:**
- Payload hash verification
- HMAC signature validation

**ML-Relevant Evidence:**
- If attacker bypasses signature (unlikely): value plausibility
- Behavioral: sudden measurement deviation
- Cross-device consistency

**Expected Response:**
- Trust label: UNTRUSTED
- Routing outcome: REJECT
- Reason codes: INTEGRITY_INVALID, PAYLOAD_TAMPER

**Limitations:**
- If attacker has valid credentials and signature key, tampering may pass deterministic checks
- C1 (credibility) should catch implausible measurements that pass C4

---

### 4.5 T5: Unauthorized Replay Attack

**Asset:** Telemetry Freshness, Sequence Continuity
**Adversary:** Network Attacker
**Attack Path:**
1. Attacker captures legitimate historical packet
2. Attacker resends packet without authorization
3. Goal: Flood system with stale data, mask current conditions

**Observable Evidence:**
- Duplicate packet_id or nonce
- Sequence number rollback or duplicate
- Old `observed_at` timestamp
- Counter reuse

**Deterministic Protection:**
- Nonce/replay detection
- Sequence number monotonicity check
- Timestamp freshness window
- Packet deduplication by (device_id, packet_id)

**ML-Relevant Evidence:**
- If attacker varies nonce but uses old timestamp: freshness analysis
- Interval deviation patterns
- Burst of replayed packets

**Expected Response:**
- Trust label: UNTRUSTED
- Routing outcome: REJECT
- Reason codes: REPLAY_DETECTED, NONCE_REUSED, SEQUENCE_REPLAY_DETECTED

**Limitations:**
- Attacker may generate new nonces if protocol allows
- Clock drift may cause false positives if tolerance too tight
- Authorized C2 replay must be distinguished (see T10)

---

### 4.6 T6: Duplicate Sequence

**Asset:** Sequence Continuity
**Adversary:** Network Attacker
**Attack Path:**
1. Attacker resends packet with same sequence number
2. May be simple duplicate or malicious replay

**Observable Evidence:**
- Same sequence_no from same (device_id, boot_id)
- Sequence number does not increase

**Deterministic Protection:**
- Sequence number state tracking per (device_id, boot_id)
- Reject non-incrementing sequences

**ML-Relevant Evidence:**
- Not applicable (deterministic check)
- Behavioral: frequency of duplicate attempts

**Expected Response:**
- Trust label: UNTRUSTED
- Routing outcome: REJECT
- Reason codes: SEQUENCE_REPLAY_DETECTED

**Limitations:**
- Legitimate device reboot resets sequence
- Must handle boot_id changes correctly

---

### 4.7 T7: Stale Packet / Clock Delay

**Asset:** Telemetry Freshness
**Adversary:** Network Attacker / Natural Network Issues
**Attack Path:**
1. Attacker delays packet transmission intentionally
2. Or legitimate network latency causes delay
3. Packet arrives outside freshness window

**Observable Evidence:**
- `rx_delay_s` exceeds threshold
- `observed_at` is too old relative to current time
- `freshness_status` = delayed

**Deterministic Protection:**
- Timestamp freshness window check
- Configurable max_age_seconds

**ML-Relevant Evidence:**
- Pattern of delayed packets
- Correlation with network conditions
- Mode-aware interval expectations

**Expected Response:**
- If malicious delay: UNTRUSTED
- If network degradation: SUSPICIOUS (behavioral)
- Reason codes: FRESHNESS_EXPIRED, CLOCK_DELAY

**Limitations:**
- Clock uncertainty on low-cost IoT devices
- Network jitter may cause false positives
- Must balance security vs availability

---

### 4.8 T8: Counter Rollback

**Asset:** Sequence Continuity
**Adversary:** Compromised Device
**Attack Path:**
1. Attacker resets device counter to previous value
2. Attempt to replay old packets with "fresh" sequence

**Observable Evidence:**
- Sequence number decreases
- Counter delta negative
- Previously seen sequence number reappears

**Deterministic Protection:**
- Sequence number monotonicity enforcement
- Reject rollback sequences

**ML-Relevant Evidence:**
- Not applicable (deterministic check)
- Behavioral: pattern of rollbacks

**Expected Response:**
- Trust label: UNTRUSTED
- Routing outcome: REJECT
- Reason codes: SEQUENCE_REPLAY_DETECTED, COUNTER_ROLLBACK

**Limitations:**
- Legitimate device reboot may reset counter
- Must track boot_id to distinguish

---

### 4.9 T9: Cloned Identity Behavior

**Asset:** Device Identity, Behavioral Profile
**Adversary:** Compromised Device / Sophisticated Attacker
**Attack Path:**
1. Attacker obtains valid credentials
2. Attacker mimics legitimate device behavior
3. But subtle behavioral differences exist (timing, RF, path)

**Observable Evidence:**
- Valid credentials (passes deterministic checks)
- RSSI/SNR differs from expected location
- Packet timing differs from device baseline
- Path through unexpected gateway
- Historical profile deviation

**Deterministic Protection:**
- Limited (credentials valid)
- Path/location registration checks if implemented

**ML-Relevant Evidence:**
- RSSI deviation from device baseline
- Interval deviation from expected mode
- SNR deviation
- Path/location mismatch
- Historical behavioral profile comparison
- Mode-aware expected interval

**Expected Response:**
- Trust label: SUSPICIOUS
- Routing outcome: QUARANTINE
- Reason codes: BEHAVIOURAL_ANOMALY, PATH_MISMATCH, RSSI_PROFILE_ANOMALY

**Limitations:**
- RF environment changes can mimic clone behavior
- Requires sufficient baseline data per device
- May produce false positives during legitimate reconfiguration

---

### 4.10 T10: Authorized C2 Recovery Replay

**Asset:** Historical Replay Authorization
**Adversary:** N/A (Legitimate Operation)
**Attack Path:**
1. C2 detects missing data in Golden Timeline
2. C2 requests device to replay historical observations
3. Device sends old data under current security context
4. Must NOT be classified as malicious replay

**Observable Evidence:**
- Old `observed_at` timestamp
- Authorized recovery request ID present
- Current authentication/integrity valid
- Recovery context metadata

**Deterministic Protection:**
- Recovery request context validation
- Authorized replay flag
- Check against authorized recovery window

**ML-Relevant Evidence:**
- Should exclude from behavioral anomaly training
- Mark with `source_origin` = AUTHORIZED_REPLAY

**Expected Response:**
- Trust label: TRUSTED
- Routing outcome: ACCEPT
- Reason codes: AUTHORIZED_REPLAY, IDENTITY_VALID, INTEGRITY_VALID
- Provenance: LATE_ORIGINAL in Golden Timeline

**Limitations:**
- Must implement recovery context tracking
- Recovery window must be time-bounded
- Audit trail required for all authorized replays

---

### 4.11 T11: Unexpected Gateway/Location Path

**Asset:** Sensor Provenance
**Adversary:** Network Attacker / Spoofed Device
**Attack Path:**
1. Packet arrives through unexpected gateway
2. Location inconsistent with registered zone
3. Path does not match expected topology

**Observable Evidence:**
- `hub_registered` mismatch
- `location_match` = False
- `path_valid` = False
- `zone_reported` != `zone_registered`

**Deterministic Protection:**
- Hub registration check
- Zone registration check
- Path validation if topology known

**ML-Relevant Evidence:**
- If partial path info: RF characteristics deviation
- Timing anomaly for expected path

**Expected Response:**
- Trust label: UNTRUSTED
- Routing outcome: REJECT
- Reason codes: PATH_MISMATCH, HUB_MISMATCH, ZONE_MISMATCH

**Limitations:**
- RF propagation can cause unexpected paths
- Device mobility (if applicable) must be accounted for
- Requires accurate topology configuration

---

### 4.12 T12: Abnormal Packet Interval

**Asset:** Behavioral Profile
**Adversary:** Compromised Device / Network Attacker
**Attack Path:**
1. Attacker sends packets at unusual rate
2. Bursts or gaps deviate from expected mode
3. Attempt to overwhelm or starve system

**Observable Evidence:**
- `tx_interval_s` deviation from expected
- Burst pattern
- Missing expected packets

**Deterministic Protection:**
- Limited (interval is behavioral)
- Rate limiting at gateway level

**ML-Relevant Evidence:**
- Interval deviation from mode-aware expected
- Historical interval profile
- Burst detection
- Missing packet detection

**Expected Response:**
- Trust label: SUSPICIOUS
- Routing outcome: QUARANTINE
- Reason codes: INTERVAL_ANOMALY, BEHAVIOURAL_ANOMALY

**Limitations:**
- Mode transitions (IDLE → WARNING) legitimately change intervals
- Network conditions can cause variable intervals
- Must be mode-aware

---

### 4.13 T13: Abnormal Packet Size

**Asset:** Behavioral Profile
**Adversary:** Compromised Device
**Attack Path:**
1. Attacker sends unusually large/small packets
2. May indicate data exfiltration or tampering

**Observable Evidence:**
- `packet_size_bytes` deviation from expected
- Unexpected message type

**Deterministic Protection:**
- Packet size limits at gateway

**ML-Relevant Evidence:**
- Size deviation from device baseline
- Historical size distribution

**Expected Response:**
- Trust label: SUSPICIOUS
- Routing outcome: QUARANTINE
- Reason codes: PACKET_SIZE_ANOMALY, BEHAVIOURAL_ANOMALY

**Limitations:**
- Firmware updates may change packet structure
- Mode changes may affect size

---

### 4.14 T14: Abnormal Retry Behavior

**Asset:** Behavioral Profile
**Adversary:** Network Attacker / Compromised Device
**Attack Path:**
1. Attacker causes excessive retries
2. May indicate jamming or manipulation

**Observable Evidence:**
- High `retry_count`
- Excessive retransmission pattern

**Deterministic Protection:**
- Retry limits at protocol level

**ML-Relevant Evidence:**
- Retry count deviation from baseline
- Retry pattern analysis
- Correlation with RSSI/SNR

**Expected Response:**
- Trust label: SUSPICIOUS
- Routing outcome: QUARANTINE
- Reason codes: RETRY_ANOMALY, BEHAVIOURAL_ANOMALY

**Limitations:**
- Network degradation causes legitimate retries
- Must distinguish network issues from attack

---

### 4.15 T15: Abnormal RSSI/SNR Pattern

**Asset:** Behavioral Profile
**Adversary:** Sophisticated Attacker (location spoofing)
**Attack Path:**
1. Attacker transmits from unexpected location
2. RF characteristics differ from expected

**Observable Evidence:**
- `rssi_dbm` deviation from device baseline
- `rssi_deviation_db` high
- `snr_db` deviation
- Sudden RF pattern change

**Deterministic Protection:**
- Limited (RF is noisy)

**ML-Relevant Evidence:**
- RSSI deviation from rolling baseline
- SNR deviation
- Historical RF profile
- Cross-device RF correlation

**Expected Response:**
- Trust label: SUSPICIOUS
- Routing outcome: QUARANTINE
- Reason codes: RSSI_PROFILE_ANOMALY, BEHAVIOURAL_ANOMALY

**Limitations:**
- RSSI/SNR highly environment-dependent
- Weather, obstacles, antenna orientation affect RF
- Cannot prove physical identity from RSSI alone
- Risk of false positives during legitimate RF changes

---

### 4.16 T16: Firmware/Config Inconsistency

**Asset:** Device Integrity
**Adversary:** Compromised Device
**Attack Path:**
1. Attacker loads unauthorized firmware
2. Attacker modifies device configuration

**Observable Evidence:**
- `firmware_hash` mismatch with approved
- `firmware_approved` = False
- `config_hash` mismatch
- `config_hash_match` = False

**Deterministic Protection:**
- Firmware hash verification
- Config hash verification
- Approved firmware registry

**ML-Relevant Evidence:**
- If attacker bypasses hash check: behavioral anomalies
- Unexpected operational behavior

**Expected Response:**
- Trust label: UNTRUSTED
- Routing outcome: REJECT
- Reason codes: FIRMWARE_UNAPPROVED, CONFIG_MISMATCH

**Limitations:**
- Requires approved firmware registry
- May not detect subtle firmware modifications
- Device may be operating correctly with older firmware

---

### 4.17 T17: Device Health Degradation

**Asset:** Behavioral Profile
**Adversary:** N/A (Natural Fault)
**Attack Path:**
1. Device experiences hardware fault
2. High reboot count, fault flags set
3. Not malicious but affects trust

**Observable Evidence:**
- High `reboot_count_24h`
- `sensor_fault_flag` = True
- Low battery voltage
- High current draw

**Deterministic Protection:**
- Fault flag check
- Reboot count threshold

**ML-Relevant Evidence:**
- Reboot frequency deviation
- Power behavior anomaly
- Fault flag pattern

**Expected Response:**
- Trust label: SUSPICIOUS
- Routing outcome: QUARANTINE (or reduced eligibility)
- Reason codes: DEVICE_HEALTH_DEGRADED, BEHAVIOURAL_ANOMALY

**Limitations:**
- Legitimate restarts (power cycles) occur
- Environmental stress may cause faults
- May be operational issue, not security threat

---

## 5. Deterministic vs Behavioral Classification

### 5.1 Mandatory Deterministic Checks (Hard Failures)

These MUST cause UNTRUSTED/REJECT regardless of ML:

- Unknown device
- Invalid authentication
- Integrity/signature failure
- Unauthorized replay
- Firmware/config not approved
- Revoked device

### 5.2 Behavioral ML Evidence (Soft Indicators)

These contribute to SUSPICIOUS classification:

- RSSI/SNR deviation
- Interval anomaly
- Retry anomaly
- Path/location mismatch (if not hard rule)
- Packet size anomaly
- Device health degradation
- Historical profile deviation

### 5.3 Hybrid Trust Fusion

```
IF mandatory_security_pass = False:
    UNTRUSTED (cannot be overridden by ML)
ELSE:
    behavioral_score = ML_model(behavioral_features)
    IF behavioral_score >= suspicious_threshold:
        SUSPICIOUS
    ELSE:
        TRUSTED
```

---

## 6. Threat Mitigation Summary

| Threat | Deterministic Check | Behavioral ML | Primary Response |
|--------|-------------------|---------------|------------------|
| T1: Unknown Device | Device registry | N/A | UNTRUSTED/REJECT |
| T2: Spoofed Device | Credentials | RF/timing/path | Mixed |
| T3: Invalid Auth | HMAC validation | N/A | UNTRUSTED/REJECT |
| T4: Payload Tamper | Hash/HMAC | N/A | UNTRUSTED/REJECT |
| T5: Unauthorized Replay | Nonce/sequence | N/A | UNTRUSTED/REJECT |
| T6: Duplicate Sequence | Sequence check | N/A | UNTRUSTED/REJECT |
| T7: Stale Packet | Freshness window | Pattern | Mixed |
| T8: Counter Rollback | Monotonicity | N/A | UNTRUSTED/REJECT |
| T9: Cloned Identity | Path/zone | RF/timing/profile | SUSPICIOUS |
| T10: Authorized Replay | Recovery context | Exclude | TRUSTED/ACCEPT |
| T11: Path Mismatch | Hub/zone check | RF/timing | UNTRUSTED/REJECT |
| T12: Interval Anomaly | Rate limit | Mode-aware interval | SUSPICIOUS |
| T13: Packet Size | Size limit | Size distribution | SUSPICIOUS |
| T14: Retry Anomaly | Retry limit | Retry pattern | SUSPICIOUS |
| T15: RSSI/SNR Anomaly | N/A | RF profile | SUSPICIOUS |
| T16: Firmware Mismatch | Hash check | N/A | UNTRUSTED/REJECT |
| T17: Health Degraded | Fault flag | Reboot pattern | SUSPICIOUS |

---

## 7. Limitations and Assumptions

### 7.1 Implementation Limitations

- Hardware TPM/secure element not implemented in prototype
- Limited RF environment diversity in test data
- Synthetic attack scenarios may not reflect real adversary behavior
- Device registry lifecycle may be simplified for prototype

### 7.2 ML Limitations

- Behavioral ML requires sufficient baseline data per device
- RF environment changes can cause false positives
- Model may not generalize to unseen attack types
- Cannot distinguish all sophisticated clones from legitimate reconfiguration

### 7.3 Operational Limitations

- Clock drift on low-cost IoT devices affects freshness checks
- Network degradation can mimic attack patterns
- Mode transitions legitimately change behavioral expectations
- Geographic mobility (if applicable) affects path/location checks

### 7.4 Security Assumptions

- Network between gateway and main computing system is trusted
- Secret keys are properly managed (not in source control)
- Device-to-gateway link has basic physical security
- Insider threats with full system access are out of scope

---

## 8. Threat Model Maintenance

This threat model should be reviewed and updated when:

- New attack scenarios are identified
- Security protocols are modified
- Device capabilities change
- New behavioral features are added
- After security incidents or near-misses
- Before major deployment changes

---

## 9. References

- GeoNex Development Guide: Document 08 - C4_DEVELOPMENT_GUIDE.md
- C4 Dataset: C4_Trust.csv
- Shared Contracts: shared/contracts/c4_trust.py
