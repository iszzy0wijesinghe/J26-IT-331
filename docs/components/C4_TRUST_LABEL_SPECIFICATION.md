# C4 Trust Label Specification

**Project:** GeoNex - Smart Landslide Early Warning Prediction System
**Component:** C4 - Trusted Telemetry Provenance and Device Attestation
**Document:** Trust Label Specification
**Version:** 1.0
**Date:** 2026-10-11

---

## 1. Overview

This document defines the trust labels used by Component 4 (C4) to classify telemetry packets based on source and transmission trustworthiness. Trust labels are distinct from environmental credibility (C1) and landslide risk (C3).

**Trust Labels:**
- **TRUSTED**: Mandatory security checks pass, behavioral evidence is normal
- **SUSPICIOUS**: Mandatory checks pass, but behavioral/contextual evidence is anomalous
- **UNTRUSTED**: Mandatory security condition failed or strong evidence determines ineligibility
- **UNKNOWN**: Required security or behavioral evidence is missing or cannot be verified

UNKNOWN telemetry must use the `SECURITY_REVIEW` routing outcome and must not
be forwarded to C1 or the Golden Timeline. A configured deterministic-only
policy may accept telemetry without behavioral ML only after all mandatory
security evidence has been verified.

---

## 2. Trust Label Taxonomy

```
C4 Trust Classification
├── TRUSTED
│   ├── Identity valid
│   ├── Integrity valid
│   ├── Freshness valid
│   ├── Replay check valid
│   └── Behavioral assessment normal
│
├── SUSPICIOUS
│   ├── Identity valid
│   ├── Integrity valid
│   ├── Freshness valid
│   ├── Replay check valid
│   └── Behavioral/contextual anomaly detected
│
├── UNTRUSTED
    ├── Unregistered device
    ├── Invalid authentication
    ├── Integrity failure
    ├── Unauthorized replay
    ├── Firmware/config not approved
    ├── Path/location mismatch
    └── Revoked device
└── UNKNOWN
    ├── Required attestation/provenance evidence unavailable
    ├── Freshness or sequence evidence unavailable
    └── Behavioral model unavailable when deterministic-only policy is disabled
        → SECURITY_REVIEW; never eligible for C1/Golden Timeline
```

---

## 3. TRUSTED Label

### 3.1 Definition

> **TRUSTED**: Mandatory security checks pass and available behavioral evidence is consistent with expected legitimate operation.

### 3.2 Conditions

A packet is labeled TRUSTED when **ALL** of the following are true:

#### Mandatory Deterministic Checks
- [ ] Device is registered in device registry
- [ ] Device lifecycle state is ACTIVE (not SUSPENDED, REVOKED, or RETIRED)
- [ ] Credential ID matches registered credential
- [ ] Authentication/credential verification succeeds
- [ ] HMAC signature verification succeeds
- [ ] Packet freshness is within acceptable window
- [ ] No replay detected (nonce not reused, sequence not duplicated)
- [ ] Firmware hash matches approved version (if implemented)
- [ ] Config hash matches expected (if implemented)
- [ ] Path/location matches expected (if implemented)

#### Behavioral Assessment
- [ ] Behavioral anomaly score is below suspicious threshold
- [ ] Timing (interval, delay) is within expected range for current mode
- [ ] Radio characteristics (RSSI, SNR) are within expected range
- [ ] Packet behavior (size, retry count) is normal
- [ ] Device health indicators are normal
- [ ] No historical profile deviation detected

### 3.3 Expected Routing Outcome

- **Routing Outcome:** ACCEPT
- **Downstream Eligibility:** Eligible for C1 credibility assessment and Golden Timeline
- **Trust Score:** 1.0 (or very close to 1.0)

### 3.4 Reason Codes

When TRUSTED, reason codes should include:
- `IDENTITY_VALID`
- `INTEGRITY_VALID`
- `FRESHNESS_VALID`
- `REPLAY_CHECK_VALID`
- `BEHAVIOUR_NORMAL` (if behavioral assessment performed)

### 3.5 Examples

#### Example 1: Normal Operation
```
Device: Z1-A01 (registered, ACTIVE)
Signature: Valid
Freshness: observed_at 2 seconds ago
Sequence: Monotonically increasing
Behavioral Score: 0.12 (below threshold 0.7)
→ TRUSTED
```

#### Example 2: Legitimate Device Reboot
```
Device: Z2-BK01 (registered, ACTIVE)
Signature: Valid
Freshness: observed_at 1 second ago
Sequence: Reset (new boot_id)
Behavioral Score: 0.08 (below threshold)
→ TRUSTED (with reason: SEQUENCE_RESET_LEGITIMATE)
```

#### Example 3: Mode Transition
```
Device: Z3-B01 (registered, ACTIVE)
Signature: Valid
Freshness: observed_at 3 seconds ago
Sequence: Monotonically increasing
Mode: WARNING (high reporting rate)
Behavioral Score: 0.15 (mode-aware interval expected)
→ TRUSTED
```

### 3.6 Important Notes

- **TRUSTED does NOT mean the environmental measurement is correct.** C1 (credibility) evaluates measurement plausibility.
- **TRUSTED does NOT guarantee physical device identity.** RF spoofing with valid credentials is theoretically possible.
- TRUSTED packets are eligible for downstream processing but may still be flagged by C1 as anomalous.

---

## 4. SUSPICIOUS Label

### 4.1 Definition

> **SUSPICIOUS**: Mandatory checks have not established a hard rejection, but behavioral or contextual evidence is sufficiently abnormal to require caution, further verification, reduced eligibility, or investigation.

### 4.2 Conditions

A packet is labeled SUSPICIOUS when **ALL** of the following are true:

#### Mandatory Deterministic Checks
- [ ] Device is registered in device registry
- [ ] Device lifecycle state is ACTIVE
- [ ] Credential ID matches registered credential
- [ ] Authentication/credential verification succeeds
- [ ] HMAC signature verification succeeds
- [ ] Packet freshness is within acceptable window
- [ ] No replay detected
- [ ] Firmware/config approval checks pass (if implemented)

#### Behavioral Anomaly
- [ ] Behavioral anomaly score is at or above suspicious threshold
- [ ] AND/OR one or more of the following:
    - Timing anomaly (interval deviation, unexpected delay)
    - Radio anomaly (RSSI/SNR deviation from baseline)
    - Packet behavior anomaly (unusual size, high retries)
    - Device health degradation (high reboot count, fault flags)
    - Path/location inconsistency (if not hard rule)
    - Historical profile deviation

### 4.3 Expected Routing Outcome

- **Routing Outcome:** QUARANTINE
- **Downstream Eligibility:** Restricted or delayed entry to C1/Golden Timeline
- **Trust Score:** 1.0 - behavioral_score (or policy-defined formula)

### 4.4 Reason Codes

When SUSPICIOUS, reason codes should include:
- `IDENTITY_VALID`
- `INTEGRITY_VALID`
- `FRESHNESS_VALID`
- `REPLAY_CHECK_VALID`
- Plus one or more behavioral reason codes:
    - `BEHAVIOURAL_ANOMALY`
    - `INTERVAL_ANOMALY`
    - `RSSI_PROFILE_ANOMALY`
    - `PACKET_SIZE_ANOMALY`
    - `RETRY_ANOMALY`
    - `DEVICE_HEALTH_DEGRADED`
    - `PATH_MISMATCH` (if not hard rule)
    - `HISTORICAL_PROFILE_DEVIATION`

### 4.5 Examples

#### Example 1: Clock Delay
```
Device: Z1-A01 (registered, ACTIVE)
Signature: Valid
Freshness: observed_at 25 seconds ago (max_age: 30s)
Sequence: Monotonically increasing
Behavioral: rx_delay_s = 25s (abnormally high)
→ SUSPICIOUS
Reason: CLOCK_DELAY, BEHAVIOURAL_ANOMALY
```

#### Example 2: Device Health Degraded
```
Device: Z2-BK01 (registered, ACTIVE)
Signature: Valid
Freshness: observed_at 1 second ago
Sequence: Monotonically increasing
Behavioral: reboot_count_24h = 13, sensor_fault_flag = True
→ SUSPICIOUS
Reason: DEVICE_HEALTH_DEGRADED, BEHAVIOURAL_ANOMALY
```

#### Example 3: Weak Signal
```
Device: Z3-B01 (registered, ACTIVE)
Signature: Valid
Freshness: observed_at 2 seconds ago
Sequence: Monotonically increasing
Behavioral: rssi_dbm = -110 (very weak), rssi_deviation_db = -10.9
→ SUSPICIOUS
Reason: WEAK_SIGNAL, RSSI_PROFILE_ANOMALY, BEHAVIOURAL_ANOMALY
```

#### Example 4: Interval Anomaly
```
Device: Z1-B01 (registered, ACTIVE)
Signature: Valid
Freshness: observed_at 0.5 seconds ago
Sequence: Monotonically increasing
Mode: IDLE (expected interval: 30s)
Behavioral: tx_interval_s = 0.5s (bursting unexpectedly)
→ SUSPICIOUS
Reason: INTERVAL_ANOMALY, BEHAVIOURAL_ANOMALY
```

### 4.6 Important Notes

- SUSPICIOUS packets **may still be used** for environmental analysis depending on policy.
- Suspicious packets should be **flagged for audit** and **investigated**.
- The decision on whether to allow SUSPICIOUS packets into C1 is a policy choice balancing security vs availability.
- Behavioral thresholds should be tuned to minimize false positives on legitimate RF environment changes.

---

## 5. UNTRUSTED Label

### 5.1 Definition

> **UNTRUSTED**: A mandatory security condition failed or sufficiently strong evidence/policy determines the telemetry is not eligible for normal downstream environmental use.

### 5.2 Conditions

A packet is labeled UNTRUSTED when **ANY** of the following is true:

#### Mandatory Security Failures (Hard Failures)
- [ ] Device is **NOT** registered in device registry
- [ ] Device lifecycle state is SUSPENDED, REVOKED, or RETIRED
- [ ] Credential ID does not match registered credential
- [ ] Authentication/credential verification fails
- [ ] HMAC signature verification fails
- [ ] Packet freshness is **NOT** within acceptable window (stale)
- [ ] Replay detected (nonce reused, sequence duplicated/rolled back)
- [ ] Firmware hash does **NOT** match approved version
- [ ] Config hash does **NOT** match expected
- [ ] Path/location does **NOT** match expected (if hard rule)

#### Strong Evidence-Based Rejection
- [ ] Payload tampering detected (hash mismatch)
- [ ] Provenance chain broken
- [ ] Hub mismatch (if hard rule)
- [ ] Unauthorized replay detected
- [ ] Rogue device pattern detected

### 5.3 Expected Routing Outcome

- **Routing Outcome:** REJECT
- **Downstream Eligibility:** Ineligible for C1 credibility assessment and Golden Timeline
- **Trust Score:** 0.0 (or very close to 0.0)

### 5.4 Reason Codes

When UNTRUSTED, reason codes should include one or more:
- `DEVICE_UNKNOWN`
- `DEVICE_REVOKED`
- `CREDENTIAL_ID_MISMATCH`
- `CREDENTIAL_ID_MISSING`
- `SIGNATURE_MISSING`
- `INTEGRITY_INVALID`
- `FRESHNESS_EXPIRED`
- `TIMESTAMP_IN_FUTURE`
- `REPLAY_DETECTED`
- `NONCE_REUSED`
- `SEQUENCE_REPLAY_DETECTED`
- `COUNTER_ROLLBACK`
- `FIRMWARE_UNAPPROVED`
- `CONFIG_MISMATCH`
- `PAYLOAD_TAMPER`
- `PROVENANCE_BREAK`
- `PATH_MISMATCH`
- `HUB_MISMATCH`
- `LOCATION_MISMATCH`
- `ROGUE_DEVICE`
- `UNAUTHORIZED_REPLAY`

### 5.5 Examples

#### Example 1: Unknown Device
```
Device: X-6780 (NOT registered)
Credential: None
→ UNTRUSTED
Reason: DEVICE_UNKNOWN
```

#### Example 2: Invalid Signature
```
Device: Z1-A01 (registered)
Credential ID: Valid
Signature: Invalid (HMAC verification fails)
→ UNTRUSTED
Reason: INTEGRITY_INVALID
```

#### Example 3: Replay Attack
```
Device: Z2-B01 (registered)
Signature: Valid
Nonce: d0dc763caa6d4fdd (previously seen)
→ UNTRUSTED
Reason: REPLAY_DETECTED, NONCE_REUSED
```

#### Example 4: Unauthorized Sequence Replay
```
Device: Z3-A01 (registered)
Signature: Valid
Sequence: 15 (previously seen for this boot_id)
→ UNTRUSTED
Reason: SEQUENCE_REPLAY_DETECTED
```

#### Example 5: Stale Packet
```
Device: Z1-BK01 (registered)
Signature: Valid
observed_at: 40 seconds ago (max_age: 30s)
→ UNTRUSTED
Reason: FRESHNESS_EXPIRED
```

#### Example 6: Payload Tampering
```
Device: Z2-A01 (registered)
Signature: Valid
Payload hash: Mismatch with calculated hash
→ UNTRUSTED
Reason: PAYLOAD_TAMPER, INTEGRITY_INVALID
```

#### Example 7: Provenance Break
```
Device: Z1-A01 (registered)
Signature: Valid
prev_hash_match: False
path_valid: False
provenance_complete: False
→ UNTRUSTED
Reason: PROVENANCE_BREAK, PATH_MISMATCH
```

#### Example 8: Rogue Firmware
```
Device: Z3-B01 (registered)
Signature: Valid
firmware_approved: False
firmware_hash: Not in approved registry
→ UNTRUSTED
Reason: FIRMWARE_UNAPPROVED
```

### 5.6 Important Notes

- **ML cannot override UNTRUSTED classification.** Even if a behavioral model outputs 0.99 "trusted", a failed mandatory security check must result in UNTRUSTED.
- UNtrusted packets are **retained for audit** but **not used for environmental analysis**.
- The raw packet and C4 assessment are both stored for incident analysis and model improvement.
- Authorized C2 recovery replay is a special case that should be labeled TRUSTED despite historical observed_at (see Section 7).

---

## 6. Binary Label Mapping

### 6.1 label_untrusted_binary

The binary label `label_untrusted_binary` is used for binary classification experiments:

| Trust Label | label_untrusted_binary |
|-------------|------------------------|
| TRUSTED | 0 |
| SUSPICIOUS | **Policy-dependent** (see below) |
| UNTRUSTED | 1 |

### 6.2 SUSPICIOUS Binary Mapping Policy

The mapping of SUSPICIOUS to binary label is policy-dependent and must be explicitly documented for each experiment:

**Option A: Conservative (Security-First)**
- SUSPICIOUS → 1 (treat as untrusted)
- Rationale: Better to reject legitimate packets than accept suspicious ones

**Option B: Permissive (Availability-First)**
- SUSPICIOUS → 0 (treat as trusted)
- Rationale: Maximize data availability, rely on C1 to catch measurement issues

**Option C: Hybrid (Score-Based)**
- Use continuous trust_score threshold instead of binary label
- Rationale: More nuanced decision boundary

**Recommendation:** For baseline C4 experiments, use Option A (Conservative) to evaluate security-focused performance. Document the mapping choice in experiment metadata.

---

## 7. Special Cases

### 7.1 Authorized C2 Recovery Replay

**Scenario:** C2 requests missing historical data, device replays under current security context.

**Classification:** TRUSTED

**Conditions:**
- Current authentication/integrity valid
- Authorized recovery request context present
- Recovery within authorized time window
- Historical observed_at preserved in Golden Timeline as LATE_ORIGINAL

**Reason Codes:**
- `IDENTITY_VALID`
- `INTEGRITY_VALID`
- `FRESHNESS_VALID` (for current transfer)
- `AUTHORIZED_REPLAY`

**Important:** Authorized replay must be distinguished from malicious replay. This requires tracking recovery request context.

---

### 7.2 Legitimate Device Reboot

**Scenario:** Device power-cycles or reboots, sequence number resets.

**Classification:** TRUSTED (if other checks pass)

**Conditions:**
- Device registered and ACTIVE
- Signature valid
- New boot_id detected
- Sequence number reset is expected for new boot_id

**Reason Codes:**
- `IDENTITY_VALID`
- `INTEGRITY_VALID`
- `FRESHNESS_VALID`
- `SEQUENCE_RESET_LEGITIMATE`

**Important:** Sequence reset is not automatically an attack. Boot_id tracking is required to distinguish from rollback.

---

### 7.3 Mode Transition

**Scenario:** Device transitions from IDLE to WARNING, reporting rate increases.

**Classification:** TRUSTED (if behavior matches expected mode)

**Conditions:**
- Device registered and ACTIVE
- Signature valid
- Packet interval matches expected interval for current mode
- Behavioral assessment is mode-aware

**Reason Codes:**
- `IDENTITY_VALID`
- `INTEGRITY_VALID`
- `FRESHNESS_VALID`
- `MODE_TRANSITION_DETECTED`

**Important:** Behavioral features must be mode-aware to avoid false positives during legitimate mode changes.

---

### 7.4 Network Degradation

**Scenario:** RF environment changes, RSSI/SNR degrade temporarily.

**Classification:** TRUSTED or SUSPICIOUS (policy-dependent)

**Conditions:**
- Device registered and ACTIVE
- Signature valid
- RSSI/SNR outside normal range but within plausible range
- No other anomalies

**Reason Codes (if SUSPICIOUS):**
- `IDENTITY_VALID`
- `INTEGRITY_VALID`
- `FRESHNESS_VALID`
- `RSSI_PROFILE_ANOMALY`
- `NETWORK_DEGRADATION_SUSPECTED`

**Important:** RF characteristics are noisy and environment-dependent. Thresholds should be tuned to avoid false positives during legitimate network issues.

---

## 8. Label Provenance

Every labeled record should include:

| Field | Description |
|-------|-------------|
| label_source | Source of label (rule-based, manual, synthetic generator) |
| scenario_id | Attack/fault scenario identifier |
| manual_review | Whether manual review was performed |
| confidence | Label confidence (if applicable) |
| generator_version | Version of synthetic data generator (if applicable) |
| attack_type | Type of attack simulation (if applicable) |

---

## 9. Label Usage in ML Training

### 9.1 Supervised Classification

**Target:** trust_label (multi-class: TRUSTED, SUSPICIOUS, UNTRUSTED)

**Feature Set:** Behavioral features only (B0-B5)
- Exclude deterministic security fields to prevent leakage
- Exclude device_id, scenario, c4_trust_score

**Evaluation Metrics:**
- Per-class precision, recall, F1
- Macro-averaged F1
- Confusion matrix
- ROC-AUC and PR-AUC (for binary variants)

### 9.2 Anomaly Detection

**Training Data:** Primarily TRUSTED (normal behavior)

**Evaluation:** TRUSTED + UNTRUSTED/SUSPICIOUS (anomalies)

**Approach:**
- Train anomaly detector on normal behavioral patterns
- Evaluate on held-out normal data and attack data
- Tune threshold on validation set

**Evaluation Metrics:**
- Precision, recall, F1 on anomaly class
- False positive rate on normal data
- Anomaly score distributions

### 9.3 Hybrid Fusion

**Approach:**
1. Deterministic gate produces mandatory_security_pass (True/False)
2. If False → UNTRUSTED (cannot be overridden)
3. If True → Behavioral ML produces anomaly_score
4. If anomaly_score >= threshold → SUSPICIOUS
5. Else → TRUSTED

**Ablation Studies:**
- Deterministic-only
- Behavioral-only
- Hybrid (deterministic + behavioral)
- Hybrid + mode-aware features

---

## 10. Consistency with C4_Trust.csv

The current C4_Trust.csv dataset uses the following label mapping:

| Scenario | Trust Label | Count |
|----------|------------|-------|
| normal | TRUSTED | 7,757 |
| clock_delay | SUSPICIOUS | 208 |
| device_health_degraded | SUSPICIOUS | 211 |
| weak_signal | SUSPICIOUS | 236 |
| replay_attack | UNTRUSTED | 306 |
| rogue_device | UNTRUSTED | 292 |
| spoofing | UNTRUSTED | 272 |
| provenance_break | UNTRUSTED | 250 |
| payload_tamper | UNTRUSTED | 241 |
| rogue_firmware | UNTRUSTED | 227 |

**Assessment:** The dataset label assignment is consistent with this specification. However, note the perfect 1:1 scenario-to-label mapping identified in the dataset audit, which should be addressed in feature engineering.

---

## 11. Future Enhancements

Potential future label refinements:

### 11.1 Granular Suspicious Subclasses

- SUSPICIOUS_TIMING
- SUSPICIOUS_RF
- SUSPICIOUS_HEALTH
- SUSPICIOUS_PATH
- SUSPICIOUS_PROFILE

### 11.2 Granular Untrusted Subclasses

- UNTRUSTED_IDENTITY
- UNTRUSTED_INTEGRITY
- UNTRUSTED_FRESHNESS
- UNTRUSTED_REPLAY
- UNTRUSTED_FIRMWARE
- UNTRUSTED_PROVENANCE

### 11.3 Continuous Trust Score

Replace discrete labels with continuous trust score (0.0 to 1.0) with policy-defined thresholds for routing decisions.

---

## 12. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-10-11 | Initial specification |

---

## 13. References

- GeoNex Development Guide: Document 08 - C4_DEVELOPMENT_GUIDE.md
- C4 Threat Model: C4_THREAT_MODEL.md
- C4 Dataset Audit: C4_DATASET_AUDIT.md
- C4 Contract: shared/contracts/c4_trust.py
