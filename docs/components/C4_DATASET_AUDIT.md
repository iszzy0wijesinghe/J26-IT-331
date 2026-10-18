# C4 Dataset Audit

**Project:** GeoNex - Smart Landslide Early Warning Prediction System
**Component:** C4 - Trusted Telemetry Provenance and Device Attestation
**Document:** Dataset Audit Report
**Dataset:** C4_Trust.csv
**Version:** 1.0
**Date:** 2026-10-11
**Auditor:** Automated Audit Script

---

## 1. Executive Summary

The C4_Trust.csv dataset contains 10,000 telemetry packets with 57 features, including sensor readings, security metadata, and trust labels. The dataset is well-structured with no missing values, but **significant security field leakage** exists that must be addressed before ML model training to ensure behavioral models learn genuine patterns rather than trivial deterministic rules.

**Critical Findings:**
- ✅ No missing values, complete dataset
- ✅ Reasonable class distribution (77.6% Trusted, 15.9% Untrusted, 6.6% Suspicious)
- ✅ 10 attack/fault scenarios represented
- ⚠️ **SECURITY FIELD LEAKAGE**: Security fields strongly correlated with labels (-0.36 to -0.68)
- ⚠️ **SCENARIO SHORTCUT**: Each scenario maps 1:1 to trust label
- ⚠️ **DEVICE_ID SHORTCUT**: Rogue devices (X-*) easily distinguishable by pattern

---

## 2. Dataset Overview

### 2.1 Basic Statistics

| Metric | Value |
|--------|-------|
| Total Records | 10,000 |
| Total Features | 57 |
| Missing Values | 0 |
| Unique Devices | 555 |
| Unique Scenarios | 10 |

### 2.2 Feature Categories

| Category | Features | Count |
|----------|----------|-------|
| Identifiers | packet_id, device_id, device_kind, hub_id, zone_registered, zone_reported | 6 |
| Timestamps | device_timestamp, received_timestamp | 2 |
| Sensor Data | soil_moisture_pct, rainfall_mm, tilt_deg, vibration_g, temperature_c | 5 |
| Device State | battery_pct, battery_voltage_v, current_ma, reboot_count_24h, sensor_fault_flag | 5 |
| Transmission | rssi_dbm, snr_db, rssi_deviation_db, packet_size_bytes, tx_interval_s, retry_count, rx_delay_s | 7 |
| Security (Deterministic) | cert_registered, channel_auth_ok, signature_valid, attestation_passed, firmware_approved, config_hash_match, payload_hash_match, prev_hash_match, path_valid, provenance_complete, hub_match, location_match | 12 |
| Sequence/Freshness | counter, counter_delta, nonce, nonce_reused, freshness_status | 5 |
| Labels | scenario, trust_label, label_id, is_malicious, label_untrusted_binary, c4_decision, c4_trust_score, reason_code, split | 9 |
| Hashes | cert_fingerprint, firmware_hash, config_hash, prev_hash, record_hash | 5 |

---

## 3. Label Distribution

### 3.1 Trust Label Distribution

| Trust Label | Count | Percentage |
|-------------|-------|------------|
| Trusted | 7,757 | 77.57% |
| Untrusted | 1,588 | 15.88% |
| Suspicious | 655 | 6.55% |

**Assessment:** Reasonable class distribution. Trusted class is majority (expected in normal operation), but sufficient minority classes for ML training. No severe class imbalance requiring extreme resampling.

### 3.2 Scenario Distribution

| Scenario | Count | Percentage |
|----------|-------|------------|
| normal | 7,757 | 77.57% |
| replay_attack | 306 | 3.06% |
| rogue_device | 292 | 2.92% |
| spoofing | 272 | 2.72% |
| provenance_break | 250 | 2.50% |
| payload_tamper | 241 | 2.41% |
| weak_signal | 236 | 2.36% |
| rogue_firmware | 227 | 2.27% |
| device_health_degraded | 211 | 2.11% |
| clock_delay | 208 | 2.08% |

**Assessment:** Good diversity of attack/fault scenarios. Each attack scenario has sufficient samples (~200-300) for training.

### 3.3 Scenario-to-Label Mapping

| Scenario | Trust Label | Count |
|----------|------------|-------|
| normal | Trusted | 7,757 |
| clock_delay | Suspicious | 208 |
| device_health_degraded | Suspicious | 211 |
| weak_signal | Suspicious | 236 |
| replay_attack | Untrusted | 306 |
| rogue_device | Untrusted | 292 |
| spoofing | Untrusted | 272 |
| provenance_break | Untrusted | 250 |
| payload_tamper | Untrusted | 241 |
| rogue_firmware | Untrusted | 227 |

**⚠️ CRITICAL ISSUE:** Perfect 1:1 mapping between scenario and trust label. This creates a scenario shortcut where ML models could learn the scenario pattern rather than genuine behavioral features.

### 3.4 Train/Validation/Test Split

| Split | Count | Percentage |
|-------|-------|------------|
| train | 6,987 | 69.87% |
| val | 1,520 | 15.20% |
| test | 1,493 | 14.93% |

**Assessment:** Reasonable 70/15/15 split. However, scenario distribution should be checked for scenario leakage across splits.

### 3.5 Scenario Distribution Across Splits

| Scenario | train | val | test | Total |
|----------|-------|-----|------|-------|
| normal | 5,436 | 1,168 | 1,153 | 7,757 |
| replay_attack | 213 | 45 | 48 | 306 |
| rogue_device | 206 | 44 | 42 | 292 |
| spoofing | 190 | 43 | 39 | 272 |
| provenance_break | 171 | 37 | 42 | 250 |
| payload_tamper | 162 | 42 | 37 | 241 |
| weak_signal | 156 | 43 | 37 | 236 |
| rogue_firmware | 166 | 33 | 28 | 227 |
| device_health_degraded | 145 | 32 | 34 | 211 |
| clock_delay | 142 | 33 | 33 | 208 |

**✅ GOOD:** Scenarios are distributed across all splits. No scenario is entirely held out from training, which is acceptable for supervised learning but may limit generalization testing for unseen scenarios.

---

## 4. Security Field Leakage Analysis

### 4.1 Correlation Between Security Fields and Binary Label

| Security Field | Correlation with label_untrusted_binary |
|----------------|------------------------------------------|
| signature_valid | -0.6810 |
| attestation_passed | -0.6745 |
| firmware_approved | -0.6745 |
| path_valid | -0.3685 |
| provenance_complete | -0.3685 |
| prev_hash_match | -0.5584 |
| payload_hash_match | -0.3617 |
| cert_registered | -0.5627 |
| channel_auth_ok | -0.5627 |
| config_hash_match | -0.5627 |
| hub_match | -0.5627 |
| location_match | -0.5627 |

**⚠️ CRITICAL ISSUE:** Strong negative correlations (-0.36 to -0.68) indicate that security fields are highly predictive of the trust label. If these fields are included as ML features, models will trivially learn the deterministic rules (e.g., "if signature_valid=False, predict Untrusted") rather than detecting genuine behavioral anomalies.

### 4.2 Security Field Values by Trust Label

#### For Trusted (7,757 records):
- All security fields: 100% True
- Interpretation: All Trusted records pass all deterministic security checks

#### For Suspicious (655 records):
- All security fields: 100% True
- Interpretation: Suspicious records pass deterministic checks but fail behavioral assessment (clock_delay, device_health_degraded, weak_signal)

#### For Untrusted (1,588 records):
- cert_registered: 64.5% True, 35.5% False
- channel_auth_ok: 64.5% True, 35.5% False
- signature_valid: 49.3% True, 50.7% False
- attestation_passed: 50.2% True, 49.8% False
- firmware_approved: 50.2% True, 49.8% False
- config_hash_match: 64.5% True, 35.5% False
- payload_hash_match: 84.8% True, 15.2% False
- prev_hash_match: 65.0% True, 35.0% False
- path_valid: 84.2% True, 15.8% False
- provenance_complete: 84.2% True, 15.8% False
- hub_match: 64.5% True, 35.5% False
- location_match: 64.5% True, 35.5% False

**Interpretation:** Untrusted is a mixed class. Some records fail deterministic checks (signature_valid=False, etc.), while others pass checks but have other issues (provenance_break, path_valid=False).

---

## 5. Device ID Analysis

### 5.1 Device Distribution

| Device ID | Count | Type |
|-----------|-------|------|
| Z3-B01 | 1,084 | Legitimate |
| Z2-BK01 | 1,084 | Legitimate |
| Z1-B01 | 1,079 | Legitimate |
| Z2-A01 | 1,065 | Legitimate |
| Z1-A01 | 1,045 | Legitimate |
| Z3-BK01 | 1,044 | Legitimate |
| Z1-BK01 | 1,040 | Legitimate |
| Z3-A01 | 1,004 | Legitimate |
| Z2-B01 | 991 | Legitimate |
| X-6780 | 2 | Rogue |
| X-2931 | 2 | Rogue |
| X-7327 | 2 | Rogue |
| X-9371 | 2 | Rogue |
| X-4828 | 2 | Rogue |
| X-2908 | 2 | Rogue |
| X-9082 | 2 | Rogue |
| X-1043 | 2 | Rogue |
| X-4966 | 2 | Rogue |
| X-5752 | 2 | Rogue |
| X-7769 | 2 | Rogue |

**⚠️ DEVICE_ID SHORTCUT:** Rogue devices have clear "X-*" pattern, while legitimate devices have "Z{zone}-{type}{number}" pattern. If device_id is used as an ML feature, the model will trivially learn this pattern.

**Recommendation:** Device_id should be excluded from ML feature set. It should be used only for grouping and provenance tracking.

### 5.2 Device Kind Distribution

- type_a: ~4,000 records
- type_b: ~4,000 records
- backup: ~2,000 records
- UNREGISTERED: Only for rogue devices (X-*)

---

## 6. Trust Score Analysis

### 6.1 Trust Score Distribution by Label

| Trust Label | Mean | Std | Min | 25% | 50% | 75% | Max |
|-------------|------|-----|-----|-----|-----|-----|-----|
| Trusted | 0.969 | 0.017 | 0.903 | 0.958 | 0.969 | 0.984 | 0.999 |
| Suspicious | 0.697 | 0.086 | 0.493 | 0.637 | 0.695 | 0.768 | 0.850 |
| Untrusted | 0.145 | 0.078 | 0.003 | 0.084 | 0.145 | 0.212 | 0.280 |

**Assessment:** Clear separation in trust scores across labels. Trusted scores are tightly clustered around 0.97, Suspicious around 0.70, Untrusted around 0.14. This suggests the trust score is effectively derived from the deterministic/behavioral rules.

**⚠️ LEAKAGE RISK:** If c4_trust_score is used as an ML feature or target, it will trivially predict the label. It should be excluded from ML training.

---

## 7. Critical Issues and Recommendations

### 7.1 Issue #1: Security Field Leakage

**Severity:** CRITICAL

**Description:** Security fields (signature_valid, attestation_passed, etc.) are strongly correlated with trust labels. Including these as ML features will cause models to learn deterministic rules rather than behavioral patterns.

**Impact:** Models will achieve high accuracy by shortcutting to security field values, failing to demonstrate genuine behavioral anomaly detection capabilities.

**Recommendation:**
- **Exclude** all deterministic security fields from ML feature set for behavioral models
- Use security fields only for:
  - Deterministic gate (pre-ML)
  - Trust fusion (post-ML)
  - Ablation studies (to compare deterministic-only vs hybrid)

**Exclude from ML features:**
```
cert_registered, channel_auth_ok, signature_valid, attestation_passed,
firmware_approved, config_hash_match, payload_hash_match, prev_hash_match,
path_valid, provenance_complete, hub_match, location_match
```

---

### 7.2 Issue #2: Scenario Shortcut

**Severity:** HIGH

**Description:** Each scenario maps 1:1 to a trust label. Models could learn the scenario pattern rather than behavioral features.

**Impact:** Overestimation of model capabilities; poor generalization to unseen scenarios.

**Recommendation:**
- **Exclude** scenario field from ML feature set
- Use scenario only for:
  - Group-aware train/val/test splitting
  - Ablation studies (hold out entire scenarios for testing)
  - Error analysis by scenario type

---

### 7.3 Issue #3: Device ID Shortcut

**Severity:** HIGH

**Description:** Rogue devices have clear "X-*" pattern. Including device_id as a feature would allow trivial classification.

**Impact:** Model learns device identity pattern rather than behavioral characteristics.

**Recommendation:**
- **Exclude** device_id from ML feature set
- Use device_id only for:
  - Grouping and time-series features
  - Historical profile construction
  - Provenance tracking

---

### 7.4 Issue #4: Trust Score Leakage

**Severity:** HIGH

**Description:** c4_trust_score is clearly derived from the rules and strongly separates labels.

**Impact:** Using trust_score as a feature or target would trivialize the classification task.

**Recommendation:**
- **Exclude** c4_trust_score from ML feature set
- Trust score should be the output of the fusion model, not an input

---

### 7.5 Issue #5: Deterministic vs Behavioral Evidence Not Separated

**Severity:** MEDIUM

**Description:** The dataset mixes deterministic security evidence with behavioral telemetry in a single file. According to the development guide, these should be conceptually separated (C4-A and C4-B).

**Impact:** Difficulty in training pure behavioral models without leakage.

**Recommendation:**
- Create two derived datasets:
  - **C4-A Deterministic Evidence**: Only deterministic security fields and outcomes
  - **C4-B Behavioral Dataset**: Only behavioral features (timing, radio, packet, health, path) with labels
- Document the transformation pipeline

---

## 8. Recommended Behavioral Feature Set

Based on the audit, the following features should be used for behavioral ML training:

### B0 - Timing Features
- tx_interval_s
- rx_delay_s
- freshness_status (encoded)
- Derived: interval_deviation from expected mode

### B1 - Radio Features
- rssi_dbm
- rssi_deviation_db
- snr_db
- retry_count

### B2 - Packet Behavior
- packet_size_bytes
- counter_delta
- Derived: sequence_gap, duplicate_frequency

### B3 - Device Health
- battery_pct
- battery_voltage_v
- current_ma
- reboot_count_24h
- sensor_fault_flag

### B4 - Path/Location (if not deterministic)
- zone_registered vs zone_reported (comparison flag)
- hub_registered vs hub_id (comparison flag)
- location_match (use cautiously, may be deterministic)

### B5 - Historical Features (to be computed)
- Rolling interval mean/std per device
- Rolling RSSI/SNR profile per device
- Rolling retry distribution per device

**EXCLUDE from ML:**
- All deterministic security fields (see Issue #1)
- device_id
- scenario
- c4_trust_score
- label_untrusted_binary (use trust_label as target)
- Hash fields (cert_fingerprint, firmware_hash, config_hash, prev_hash, record_hash)
- nonce (use nonce_reused flag instead)

---

## 9. Data Quality Checklist

- [x] No missing values
- [x] Consistent data types
- [x] Reasonable value ranges (sensor readings, voltages, etc.)
- [x] No duplicate packet_ids
- [x] Timestamps are parseable
- [x] Label distribution is reasonable
- [x] Scenario distribution is reasonable
- [x] Split distribution is reasonable
- [ ] Security field leakage addressed (requires feature engineering)
- [ ] Scenario shortcut addressed (requires feature exclusion)
- [ ] Device ID shortcut addressed (requires feature exclusion)
- [ ] Deterministic vs behavioral evidence separated (requires data transformation)

---

## 10. Dataset Versioning

**Current Version:** 1.0 (raw dataset)

**Recommended Next Versions:**
- **v1.1**: Behavioral feature extraction (B0-B5)
- **v1.2**: Separated C4-A (deterministic) and C4-B (behavioral) datasets
- **v1.3**: Scenario-aware holdout splits for generalization testing
- **v1.4**: Mode-aware expected interval features

---

## 11. Conclusion

The C4_Trust.csv dataset is well-structured and complete, but **significant leakage issues** must be addressed before ML model training. The primary risks are:

1. Security field leakage: Deterministic fields are too predictive
2. Scenario shortcut: 1:1 mapping to labels
3. Device ID shortcut: Pattern-based identification

By excluding the identified fields and focusing on genuine behavioral features (timing, radio, packet behavior, device health), the dataset can support meaningful behavioral anomaly detection research. The hybrid architecture (deterministic gate + behavioral ML) as specified in the development guide is appropriate for this dataset.

---

## 12. Next Steps

1. Implement behavioral feature extraction pipeline (B0-B5)
2. Create C4-A deterministic evidence dataset
3. Create C4-B behavioral dataset with excluded leakage fields
4. Implement scenario-aware train/val/test splitting
5. Add mode-aware expected interval features
6. Train baseline models on clean behavioral dataset
7. Run ablation studies (deterministic-only vs behavioral-only vs hybrid)
