# C4 Feature Schema Fix Notes

## Issue Summary

The existing C4 model artifacts under `experiments/c4/models/` were trained with a 24-feature schema that included mode-aware features (`mode_aware_interval_deviation`, `expected_interval_s`). However, the actual dataset `C4_Trust.csv` does not contain a `mode` column, making these features impossible to compute from the available data.

## Fix Applied

### Phase 2: Feature Schema Correction

**File Modified:** `components/c4_trust/features.py`

**Changes:**
1. Removed mode-aware features from `TRAINING_FEATURE_FIELDS` (reduced from 22 to 20 features)
2. Removed mode-aware features from `BehavioralFeatures` dataclass
3. Disabled `add_mode_aware_features()` method (reserved for future use when mode information is available)
4. Updated `extract_for_training()` to remove `add_mode_aware` parameter
5. Updated `create_behavioral_dataset()` to remove `add_mode_aware` parameter
6. Kept historical features (5 features: rolling_interval_mean, rolling_interval_std, rolling_rssi_mean, rolling_rssi_std, rolling_retry_mean)

**Final Feature Schema (20 features):**
1. tx_interval_s
2. rx_delay_s
3. freshness_status_encoded
4. rssi_dbm
5. rssi_deviation_db
6. snr_db
7. retry_count
8. packet_size_bytes
9. battery_pct
10. battery_voltage_v
11. current_ma
12. reboot_count_24h
13. sensor_fault_flag
14. rolling_interval_mean
15. rolling_interval_std
16. rolling_rssi_mean
17. rolling_rssi_std
18. rolling_retry_mean

**Updated Scripts:**
- `scripts/prepare_c4_behavioral_dataset.py`: Changed `add_historical=False` to `add_historical=True` to include historical features
- `scripts/create_c4_splits.py`: Updated to use device-held-out splits and added device count/label distribution reporting
- `components/c4_trust/data_split.py`: Updated default split type from "scenario" to "device" for device-held-out evaluation

**Updated Tests:**
- `tests/unit/c4/test_c4_ml_data.py`: Updated test to exclude mode-aware features from forbidden set

## Model Artifact Incompatibility

**Status:** The existing model artifacts (`logistic_regression.joblib`, `random_forest.joblib`, `isolation_forest.joblib`) are **incompatible** with the corrected feature schema.

**Reason:** The models were trained with 24 features including mode-aware features that cannot be computed from the current dataset.

**Action Required:** Models must be regenerated using the corrected 20-feature schema.

**Note:** Due to system Application Control policy blocking sklearn DLL imports, model regeneration cannot be performed in the current environment. This should be done in an environment where sklearn can be imported.

## Dataset Status

**Current Splits:** `experiments/c4/data/C4_train.csv`, `C4_val.csv`, `C4_test.csv`
- These splits contain the full raw dataset with 62 columns
- They include historical features already computed (columns 58-62)
- They use device-held-out evaluation (no device overlap between splits)
- The embedded `split` column has been updated to match the actual split assignment

**Backup:** `experiments/c4/data/backup_before_device_split_20261013_054519/`
- Original split files preserved before device split regeneration

## Remaining Steps

1. **Regenerate behavioral dataset** with corrected schema:
   ```bash
   python scripts/prepare_c4_behavioral_dataset.py
   ```

2. **Regenerate splits** with device-held-out evaluation:
   ```bash
   python scripts/create_c4_splits.py
   ```

3. **Retrain models** with corrected 20-feature schema:
   ```bash
   python scripts/train_c4_baselines.py
   ```

## Verification

After model regeneration, verify:
- Model feature names match `FeatureExtractor.TRAINING_FEATURE_FIELDS`
- Model can be loaded and used for inference without schema errors
- Historical features are computed correctly with no leakage
- Device isolation is maintained across splits
- All label classes appear in all splits
