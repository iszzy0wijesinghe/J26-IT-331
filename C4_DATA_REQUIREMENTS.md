# Component 4 (C4 Trust Assessment) - Complete System Documentation

## Overview

Component 4 (C4 Trust Assessment) is a comprehensive security trust evaluation system for IoT telemetry. It validates the authenticity, integrity, and behavioral patterns of incoming telemetry packets before routing them through the system using both deterministic security checks and ML-based behavioral analysis.

**Project**: GeoNex Landslide Early Warning System
**Component**: C4 Trust Assessment
**Model Type**: Random Forest Classifier
**Required Dataset Size**: 400,000 rows (4 lakh)

---

## System Architecture

### Security Layers

Component 4 implements a multi-layer security approach:

1. **Authentication Layer**
   - Device registration validation
   - Credential verification (HMAC-SHA256 or ECDSA-SHA256)
   - Certificate chain validation (X.509 for ECDSA)
   - Signature verification

2. **Integrity Layer**
   - Message tampering detection
   - Signature integrity validation
   - Firmware hash verification
   - Configuration hash verification

3. **Freshness Layer**
   - Sequence number validation
   - Replay attack detection
   - Timestamp validation
   - Clock skew tolerance (30 seconds max age, 5 seconds future tolerance)

4. **Authorization Layer**
   - Zone membership verification
   - Hub assignment validation
   - Device lifecycle state check
   - Role-based access control

5. **Behavioral Analysis Layer (ML)**
   - ML-based anomaly detection
   - Behavioral scoring (0.0 to 1.0)
   - Pattern recognition
   - Historical behavior comparison

### ML-Only-if-PASS Rule

The security gate enforces a strict rule: **ML inference only runs if mandatory security checks pass**.

- If security PASS → ML runs → behavioral score generated
- If security FAIL → ML skipped → behavioral_score is null
- This ensures resources are not wasted on obviously malicious packets

---

## ML Model Requirements

### Model Details

- **Model Type**: Random Forest Classifier
- **Feature Count**: 18 features
- **Target Classes**: 4 classes (TRUSTED, UNTRUSTED, SUSPICIOUS, UNKNOWN)
- **Model Path**: `experiments/c4/models/random_forest_corrected.joblib`
- **Feature Schema**: Defined in `components/c4_trust/runtime_features.py`

### Required Features (18 Total)

#### B0: Timing Features (3 features)

| Feature Name | Data Type | Range | Description | Example |
|-------------|-----------|-------|-------------|---------|
| `tx_interval_s` | float | > 0 | Seconds between this packet and the previous packet from the same device | 300.0 |
| `rx_delay_s` | float | ≥ 0 | Delay between device observation time and hub receive time | 5.0 |
| `freshness_status_encoded` | int | 0, 1, 2 | Encoded freshness: 0=fresh, 1=delayed, 2=stale | 0 |

#### B1: Radio Features (4 features)

| Feature Name | Data Type | Range | Description | Example |
|-------------|-----------|-------|-------------|---------|
| `rssi_dbm` | float | -150 to 0 | Received signal strength indicator in dBm | -75.0 |
| `rssi_deviation_db` | float | Any | Deviation of RSSI from the device rolling mean | 0.0 |
| `snr_db` | float | -50 to 50 | Signal-to-noise ratio in dB | 10.0 |
| `retry_count` | int | ≥ 0 | Radio retry count for the packet | 0 |

#### B2: Packet Features (1 feature)

| Feature Name | Data Type | Range | Description | Example |
|-------------|-----------|-------|-------------|---------|
| `packet_size_bytes` | int | > 0 | Serialized packet size in bytes | 256 |

#### B3: Device Health Features (5 features)

| Feature Name | Data Type | Range | Description | Example |
|-------------|-----------|-------|-------------|---------|
| `battery_pct` | float | 0 to 100 | Reported battery percentage | 85.0 |
| `battery_voltage_v` | float | 0 to 20 | Reported battery voltage in volts | 3.7 |
| `current_ma` | float | 0 to 1000 | Reported current draw in milliamps | 15.0 |
| `reboot_count_24h` | int | ≥ 0 | Reboots observed in the last 24 hours | 0 |
| `sensor_fault_flag` | int | 0 or 1 | Device-reported sensor fault flag (0=no, 1=yes) | 0 |

#### B5: Historical/Rolling Features (5 features)

| Feature Name | Data Type | Range | Description | Example |
|-------------|-----------|-------|-------------|---------|
| `rolling_interval_mean` | float | > 0 | Rolling mean of recent transmit intervals (window=10) | 300.0 |
| `rolling_interval_std` | float | ≥ 0 | Rolling standard deviation of recent transmit intervals | 0.0 |
| `rolling_rssi_mean` | float | -150 to 0 | Rolling mean of recent RSSI values | -75.0 |
| `rolling_rssi_std` | float | ≥ 0 | Rolling standard deviation of recent RSSI values | 0.0 |
| `rolling_retry_mean` | float | ≥ 0 | Rolling mean of recent retry counts | 0.0 |

---

## Dataset Generation Requirements

### CSV File Format

**File Path**: `experiments/c4/data/C4_training_dataset.csv`

**Required Columns** (in any order, but all must be present):

```csv
device_id,packet_id,device_timestamp,tx_interval_s,rx_delay_s,freshness_status_encoded,rssi_dbm,rssi_deviation_db,snr_db,retry_count,packet_size_bytes,battery_pct,battery_voltage_v,current_ma,reboot_count_24h,sensor_fault_flag,rolling_interval_mean,rolling_interval_std,rolling_rssi_mean,rolling_rssi_std,rolling_retry_mean,trust_label
```

### Column Specifications

#### Identifier Columns

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `device_id` | string | Unique device identifier | `PIPE_A1`, `PIPE_A2`, `ZONE_01_SENSOR_01` |
| `packet_id` | string | Unique packet identifier | `SIM_10217482221903389204_ZONE_01_PIPE_A1_000000` |
| `device_timestamp` | string/datetime | ISO 8601 timestamp when packet was observed | `2026-10-20T10:30:00Z` |

#### Feature Columns (18 total)

See the "Required Features" section above for detailed specifications.

#### Target Column

| Column | Type | Values | Description |
|--------|------|--------|-------------|
| `trust_label` | string | `TRUSTED`, `UNTRUSTED`, `SUSPICIOUS`, `UNKNOWN` | The ground truth trust classification |

### Data Distribution Requirements

For a balanced 400,000 row dataset, aim for:

| Class | Target Count | Percentage | Characteristics |
|-------|--------------|------------|-----------------|
| TRUSTED | 200,000 | 50% | Normal behavior, all security checks pass |
| UNTRUSTED | 100,000 | 25% | Security failures (tampering, replay, invalid credentials) |
| SUSPICIOUS | 80,000 | 20% | Behavioral anomalies (unusual patterns but security passes) |
| UNKNOWN | 20,000 | 5% | Insufficient information or ambiguous cases |

### Feature Value Guidelines

#### TRUSTED Class (Normal Behavior)

```python
tx_interval_s: 250-350 (consistent timing)
rx_delay_s: 2-10 (normal latency)
freshness_status_encoded: 0 (fresh)
rssi_dbm: -60 to -80 (good signal)
rssi_deviation_db: -5 to 5 (stable signal)
snr_db: 8 to 20 (good SNR)
retry_count: 0-2 (few retries)
packet_size_bytes: 200-300 (normal size)
battery_pct: 70-100 (good battery)
battery_voltage_v: 3.3-4.2 (normal voltage)
current_ma: 10-50 (normal current)
reboot_count_24h: 0-1 (stable)
sensor_fault_flag: 0 (no faults)
rolling_*: low variance, consistent with means
```

#### UNTRUSTED Class (Security Failures)

```python
# Security violation patterns (any combination):
- Invalid signatures
- Replay attacks (duplicate packet_id or sequence_no)
- Tampered data (zone_id mismatch, hub_id mismatch)
- Expired credentials
- Unknown device_id
- Negative RSSI or extreme values (> -120 or > 0)
- battery_pct < 10 (critical battery)
- retry_count > 10 (excessive retries)
- reboot_count_24h > 5 (unstable device)
- sensor_fault_flag: 1 (faulty sensors)
```

#### SUSPICIOUS Class (Behavioral Anomalies)

```python
# Anomalous but technically valid:
tx_interval_s: highly variable (std > 50)
rssi_deviation_db: > 20 (signal degradation)
rolling_rssi_std: > 15 (unstable signal)
rolling_retry_mean: > 3 (increasing retries)
rolling_interval_std: > 30 (timing instability)
# But security checks still pass
```

#### UNKNOWN Class (Ambiguous Cases)

```python
# Missing or borderline values:
- Some features near thresholds
- Mixed normal and anomalous patterns
- Insufficient historical data (rolling features = 0)
- Edge cases that don't clearly fit other classes
```

### Rolling Features Calculation

For the 5 rolling features, simulate a 10-packet sliding window:

```python
# For each device, maintain last 10 packets:
window_size = 10

rolling_interval_mean = mean(last_10_tx_intervals)
rolling_interval_std = std(last_10_tx_intervals)
rolling_rssi_mean = mean(last_10_rssi_values)
rolling_rssi_std = std(last_10_rssi_values)
rolling_retry_mean = mean(last_10_retry_counts)

# For first few packets per device, use available data
# If no history, set to 0 or the current value
```

### Freshness Status Encoding

Map freshness status to encoded values:

| Status | Encoded Value | Condition |
|--------|---------------|-----------|
| Fresh | 0 | rx_delay_s < 10 seconds |
| Delayed | 10 ≤ rx_delay_s < 30 seconds |
| Stale | rx_delay_s ≥ 30 seconds |

---

## Example Data Row

```csv
device_id,packet_id,device_timestamp,tx_interval_s,rx_delay_s,freshness_status_encoded,rssi_dbm,rssi_deviation_db,snr_db,retry_count,packet_size_bytes,battery_pct,battery_voltage_v,current_ma,reboot_count_24h,sensor_fault_flag,rolling_interval_mean,rolling_interval_std,rolling_rssi_mean,rolling_rssi_std,rolling_retry_mean,trust_label
PIPE_A1,SIM_10217482221903389204_ZONE_01_PIPE_A1_000000,2026-10-20T10:30:00Z,300.0,5.0,0,-75.0,0.0,10.0,0,256,85.0,3.7,15.0,0,0,300.0,0.0,-75.0,0.0,0.0,TRUSTED
```

### Example of Each Class

#### TRUSTED (Normal)
```csv
PIPE_A1,SIM_TRAFFIC_NORMAL_001,2026-10-20T10:30:00Z,300.0,5.0,0,-75.0,0.0,10.0,0,256,85.0,3.7,15.0,0,0,300.0,0.0,-75.0,0.0,0.0,TRUSTED
```

#### UNTRUSTED (Tampered)
```csv
PIPE_A1,SIM_TAMPERED_001,2026-10-20T10:30:00Z,300.0,5.0,0,-75.0,0.0,10.0,0,256,85.0,3.7,15.0,0,0,300.0,0.0,-75.0,0.0,0.0,UNTRUSTED
# Note: In real data, UNTRUSTED would have actual security violations
# This example shows feature values, but UNTRUSTED classification
# would come from security check failures, not feature values alone
```

#### SUSPICIOUS (Anomalous)
```csv
PIPE_A1,SIM_ANOMALY_001,2026-10-20T10:30:00Z,300.0,5.0,0,-75.0,0.0,10.0,0,256,85.0,3.7,15.0,0,0,300.0,50.0,-75.0,15.0,3.0,SUSPICIOUS
# High rolling_interval_std and rolling_rssi_std indicate instability
```

#### UNKNOWN (Ambiguous)
```csv
PIPE_A1,SIM_UNKNOWN_001,2026-10-20T10:30:00Z,300.0,5.0,0,-75.0,0.0,10.0,0,256,85.0,3.7,15.0,0,0,0.0,0.0,0.0,0.0,0.0,UNKNOWN
# All rolling features = 0 indicates no historical data
```

---

## Data Quality Requirements

### Validation Rules

1. **No Missing Values**: All 18 feature columns must have valid values
2. **Finite Values**: No NaN, Inf, or -Inf values
3. **Numeric Types**: All features must be numeric (int or float)
4. **Valid Ranges**: Values must be within specified ranges
5. **Consistent Device IDs**: Device IDs should be consistent across packets
6. **Timestamp Order**: device_timestamp should be monotonically increasing per device
7. **Unique Packet IDs**: Each packet_id should be unique in the dataset

### CSV Format Requirements

- **Encoding**: UTF-8
- **Delimiter**: Comma (`,`)
- **Header Row**: Required, with exact column names
- **Quote Character**: Double quote (`"`) for strings containing commas
- **Line Ending**: CRLF (`\r\n`) or LF (`\n`)
- **No BOM**: No byte order mark at start of file

### File Size Estimate

For 400,000 rows with 22 columns:
- Approximate row size: ~200 bytes
- Total file size: ~80 MB
- This is well within the 10 MB upload limit for individual files, so may need to split

---

## Integration with Component 4

### How the Dataset Will Be Used

1. **Training Phase**
   - Load CSV into pandas DataFrame
   - Split into train/validation/test (e.g., 70%/15%/15%)
   - Train Random Forest model
   - Evaluate metrics (accuracy, precision, recall, F1)
   - Save trained model to `experiments/c4/models/random_forest_corrected.joblib`

2. **Runtime Phase**
   - ML model is loaded by C4TrustService
   - For each incoming telemetry packet:
     - Extract 18 features from TelemetryPacket
     - Predict trust label using loaded model
     - Get behavioral anomaly score (0.0 to 1.0)
     - Combine with deterministic security checks
     - Make final routing decision (ACCEPT/REJECT/QUARANTINE)

3. **Testing Phase**
   - Use the model in demo scenarios
   - Test with various attack patterns
   - Verify security gate enforcement
   - Validate ML-only-if-PASS rule

### Feature Extraction in Runtime

The system automatically extracts features from live telemetry packets:

```python
# From components/c4_trust/runtime_features.py
def extract_features(packet: TelemetryPacket) -> pd.DataFrame:
    # Extract basic features from packet
    tx_interval_s = packet.tx_interval_s
    rx_delay_s = (packet.received_at - packet.observed_at).total_seconds()
    freshness_status_encoded = encode_freshness(packet.freshness_status)
    rssi_dbm = packet.transport.rssi_dbm
    rssi_deviation_db = calculate_rssi_deviation(rssi_dbm, device_history)
    snr_db = packet.transport.snr_db
    retry_count = packet.transport.retry_count
    packet_size_bytes = calculate_packet_size(packet)
    battery_pct = packet.device_health.battery_pct
    battery_voltage_v = packet.device_health.battery_voltage
    current_ma = packet.device_health.supply_current
    reboot_count_24h = packet.device_health.reboot_count_24h
    sensor_fault_flag = 1 if packet.device_health.sensor_fault_flag else 0
    
    # Calculate rolling features from device history (window=10)
    rolling_features = device_history.get_rolling_features()
    
    # Return DataFrame with all 18 features
    return pd.DataFrame([feature_row], columns=C4_MODEL_FEATURE_SCHEMA)
```

---

## Model Performance Expectations

### Target Metrics

For a well-trained model on 400,000 rows:

| Metric | Target Value | Description |
|--------|--------------|-------------|
| Overall Accuracy | > 90% | Correct predictions across all classes |
| TRUSTED Recall | > 95% | Correctly identify trusted packets |
| UNTRUSTED Recall | > 85% | Correctly identify malicious packets |
| SUSPICIOUS Recall | > 80% | Correctly identify anomalous packets |
| Macro F1 Score | > 85% | Balanced performance across classes |

### Confusion Matrix Goal

```
                Predicted
             TRUSTED UNTRUSTED SUSPICIOUS UNKNOWN
Actual
TRUSTED         190000    5000      3000      2000
UNTRUSTED        5000   85000      5000      5000
SUSPICIOUS       3000    5000     68000      4000
UNKNOWN          2000    5000      4000      9000
```

---

## Additional Notes

### Device Simulation

For realistic data generation:

1. **Device Types**: Simulate different device types (TYPE_A, TYPE_B, BACKUP)
2. **Zones**: Distribute devices across zones (ZONE_01, ZONE_02, etc.)
3. **Hubs**: Assign devices to hubs based on zone
4. **Temporal Patterns**: Include time-of-day and day-of-week variations
5. **Environmental Factors**: Simulate weather-related signal variations

### Attack Simulation

For UNTRUSTED class, include realistic attack patterns:

1. **Replay Attacks**: Duplicate packet_id with different timestamps
2. **Tampering**: Slight modifications to critical fields
3. **Spoofing**: Valid device_id with wrong credentials
4. **Jamming**: Extreme RSSI/SNR values
5. **Battery Drain**: Rapid battery depletion patterns
6. **Sensor Faults**: Faulty sensor readings over time

### Rolling Window Implementation

When generating data, maintain per-device rolling windows:

```python
device_histories = {}  # device_id -> deque of last 10 packets

for each packet:
    device_id = packet.device_id
    
    if device_id not in device_histories:
        device_histories[device_id] = {
            'intervals': deque(maxlen=10),
            'rssi': deque(maxlen=10),
            'retries': deque(maxlen=10)
        }
    
    history = device_histories[device_id]
    history['intervals'].append(packet.tx_interval_s)
    history['rssi'].append(packet.rssi_dbm)
    history['retries'].append(packet.retry_count)
    
    # Calculate rolling features
    rolling_interval_mean = mean(history['intervals'])
    rolling_interval_std = std(history['intervals'])
    rolling_rssi_mean = mean(history['rssi'])
    rolling_rssi_std = std(history['rssi'])
    rolling_retry_mean = mean(history['retries'])
```

---

## Deliverables Checklist

### From Data Generator

- [ ] CSV file with 400,000 rows
- [ ] All 18 feature columns present
- [ ] trust_label column with 4 classes
- [ ] Device ID and packet ID columns
- [ ] Timestamp column (ISO 8601 format)
- [ ] No missing or invalid values
- [ ] Balanced class distribution (approximate)
- [ ] Realistic rolling feature calculations
- [ ] Proper freshness status encoding

### After Receipt

- [ ] Validate CSV structure
- [ ] Check data quality (no NaN, Inf, out-of-range)
- [ ] Verify class distribution
- [ ] Test feature extraction
- [ ] Train model on dataset
- [ ] Evaluate model performance
- [ ] Save trained model
- [ ] Test in C4 system
- [ ] Document results

---

## Contact & Support

For questions about:
- **Data format**: Component 4 developer
- **Feature definitions**: See `components/c4_trust/runtime_features.py`
- **Model training**: See `apps/c4_frontend/upload_training.py`
- **Model evaluation**: See `apps/c4_frontend/ml_explorer.py`
- **System integration**: See `components/c4_trust/integration.py`

---

## Appendix: Complete Feature Schema Reference

```python
C4_MODEL_FEATURE_SCHEMA = (
    "tx_interval_s",
    "rx_delay_s",
    "freshness_status_encoded",
    "rssi_dbm",
    "rssi_deviation_db",
    "snr_db",
    "retry_count",
    "packet_size_bytes",
    "battery_pct",
    "battery_voltage_v",
    "current_ma",
    "reboot_count_24h",
    "sensor_fault_flag",
    "rolling_interval_mean",
    "rolling_interval_std",
    "rolling_rssi_mean",
    "rolling_rssi_std",
    "rolling_retry_mean",
)
```

**Total Features**: 18
**Target Classes**: 4 (TRUSTED, UNTRUSTED, SUSPICIOUS, UNKNOWN)
**Model Type**: Random Forest Classifier
**Training Data Size**: 400,000 rows
**Feature Families**: 5 (Timing, Radio, Packet, Device Health, Historical)

---

**Document Version**: 1.0
**Last Updated**: 2026-10-20
**Component**: C4 Trust Assessment
**Project**: GeoNex Landslide Early Warning System
