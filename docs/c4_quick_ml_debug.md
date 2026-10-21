# C4 Quick ML Demo investigation

## Root cause and evidence

The reported combination is not a deterministic security or health rule in the
Random Forest. It chooses the largest of three class probabilities; Trusted
does not require P(Trusted) > 0.5. The anomaly score is the combined probability
of the other classes, not the predicted class confidence.

The manual endpoint also fabricated five historical features from the current
packet, including standard deviations of 5% of TX interval and 3% of absolute
RSSI. This differs from corrected training and materially affects prediction.
The UI then described a Trusted prediction as a trusted device with normal
behavior, which the behavioral-only request cannot establish. Its generic
experimental warning omitted depleted battery, sensor faults and stale status.

The stored corrected training split has battery percentage 65–99.99, voltage
11.5–12.8 V, and freshness encodings only 0 and 1. It contains no zero-battery,
zero-voltage or stale examples. A forest prediction on these unseen values
is not a reliable health assessment. Sensor faults do occur in Suspicious
training rows, but they are not a mandatory rule in the classifier.

With unspecified fields at form defaults (RSSI -75, SNR 10, retries 0, current
15 mA, reboots 0), and the five reported unhealthy fields, before changes:

* predict(): Trusted
* predict_proba(): Suspicious 0.26, Trusted 0.40, Untrusted 0.34
* anomaly: 0.6000

The supplied inputs alone do not reproduce exactly 0.6100; the remaining
form values were not supplied. There is no evidence of a forced label or
incorrect Trusted probability column in this artifact.

After correcting history to the training cold-start convention, the same
complete request yields Trusted, probabilities [0.12, 0.49, 0.39], anomaly
0.5100, and five separate input-health warnings. These are observed outputs,
not test expectations or forced predictions.

## Complete inference path

1. `apps/web/src/features/c4/components/MLExplorer.tsx`: ten controlled inputs;
   numeric handlers parse floats/integers and coerce blank/invalid input to 0;
   Yes/No becomes a boolean and freshness is a lower-case string.
2. `predictManualFeatures()` POSTs the input snapshot as JSON to
   `http://127.0.0.1:8000/api/c4/predict-manual`. The button is disabled while
   the request is pending and the previous result is cleared on submission.
3. `apps/api/c4_model_explorer_api.py`: Pydantic `ManualPredictionRequest`,
   finite-value/count/freshness checks, selects the catalog runtime default.
   This quick demo always uses the runtime default, independently of the
   explorer profile's model selector.
4. `C4ModelExplorer.from_catalog()` → `from_artifact()` → `TrainedModel.load()`
   loads `experiments/c4/models/random_forest_corrected.joblib` and validates
   the ordered runtime schema. Artifact SHA256:
   `de199dd8dc5518ce93ae220f4c07d9ea174d57052a3c5e45f3a91d9de28ab94e`.
5. The endpoint constructs an explicitly ordered 18-column numeric DataFrame.
   `score_features()` calls `TrainedModel.predict()` and `predict_proba()` on
   that same frame. The wrapper applies the stored scaler if present and
   invokes the estimator methods. The artifact is a 100-tree forest with
   estimator classes [0, 1, 2] and LabelEncoder classes
   [Suspicious, Trusted, Untrusted]. Thus Trusted is probability column 1.
   `predict()` inverse-transforms the estimator's encoded prediction.
6. The explorer now computes anomaly exactly as `1.0 - p_trusted` from the
   single probability result. Previously it called predict_proba a second
   time through behavioural_anomaly_score; this was redundant, not evidence
   of inconsistent outputs from the deterministic forest. The explorer's
   existing 0.70 threshold is retained independently of predicted class.
7. The endpoint extracts label, score, probabilities and debug fields from
   the same scored row. It no longer substitutes 0.5 if a score is absent.
   Health warnings are independent response fields.
8. React stores the response label, score, warnings and assumptions together
   in one state update. `ManualPredictionResult.tsx` displays that label and
   formats that score to four decimal places. It makes no gateway or device
   health claim based on the label. The result belongs to the last submitted
   request; editing form fields does not rescore until the button is clicked.

## All 18 features, in model order

| # | Feature | Manual construction and training comparison |
|---|---|---|
| 1 | tx_interval_s | Direct form value. Training derives device timestamp differences, falling back to recorded interval for the first row; duplicates can yield zero. Manual zero is allowed for exploration, gateway runtime rejects it. |
| 2 | rx_delay_s | Assumed 5 seconds, now disclosed. Training derives received minus observed timestamps. |
| 3 | freshness_status_encoded | fresh=0, delayed=1, stale=2; matches training encoding. Unknown values are rejected, not silently fresh. |
| 4 | rssi_dbm | Direct form value. |
| 5 | rssi_deviation_db | Assumed zero, now disclosed. Training uses RSSI minus whole-device mean, unavailable from one manual input. |
| 6 | snr_db | Direct form value. |
| 7 | retry_count | Direct form integer. |
| 8 | packet_size_bytes | Assumed 256 bytes, now disclosed. Training uses recorded bytes; actual runtime serializes the packet. |
| 9 | battery_pct | Direct form value, including zero. |
| 10 | battery_voltage_v | Direct form value, including zero. Default form voltage 3.7 V also differs from the saved training range. |
| 11 | current_ma | Direct form value. |
| 12 | reboot_count_24h | Direct form integer. |
| 13 | sensor_fault_flag | Boolean to numeric 0/1, matching training. |
| 14 | rolling_interval_mean | Previously current TX interval; now zero for absent history. |
| 15 | rolling_interval_std | Previously abs(TX interval × 0.05); now zero for absent history. |
| 16 | rolling_rssi_mean | Previously current RSSI; now zero for absent history. |
| 17 | rolling_rssi_std | Previously abs(RSSI × 0.03); now zero for absent history. |
| 18 | rolling_retry_mean | Previously current retries; now zero for absent history. |

Corrected training (`scripts/c4/retrain_c4_corrected.py`) groups duplicate
timestamps, shifts to previous timestamp observations, and takes rolling
statistics over up to 10 values, with sample standard deviation and zero fill
when absent. Zero history in the demo now means cold start; it cannot represent
a device with established history. No ordering or encoding mismatch was found.
The remaining three assumptions cannot be reconstructed from ten inputs and
remain explicitly disclosed rather than claimed as measured values.

Separate pre-existing runtime/training differences: RuntimeFeatureAdapter
computes deviation from prior rolling RSSI rather than whole-device mean,
includes the current observation in rolling statistics, uses population
standard deviation, and calculates serialized packet size. This investigation
does not change the runtime adapter or mandatory gateway security checks.

## Changes and verification

Changed `apps/api/c4_model_explorer_api.py`,
`apps/c4_frontend/ml_explorer.py`,
`apps/web/src/features/c4/components/MLExplorer.tsx`, and
`tests/unit/c4/test_c4_manual_prediction.py`. Added
`apps/web/src/features/c4/components/ManualPredictionResult.tsx`,
`apps/web/tests/manual-prediction.test.cjs`, and this report. Existing local
edits in the API, React component and manual test file were preserved.
No model was retrained, replaced or saved. No gateway code changed.

Commands and actual results:

* `.venv/Scripts/python.exe -m pytest tests/unit/c4/test_c4_manual_prediction.py tests/unit/c4/test_c4_ml_explorer.py tests/unit/c4/test_c4_frontend_backend.py tests/unit/c4/test_c4_runtime_features.py -q -p no:cacheprovider`
  → 43 passed, one existing Starlette/httpx deprecation warning, 4.50 seconds.
  Initial sandbox attempt had 42 passes and one temporary-directory permission
  error; the approved rerun passed all 43.
* `.venv/Scripts/python.exe -m pytest tests/security/c4 tests/integration/c4 tests/contract/test_c1_c4_contracts.py -q -p no:cacheprovider --basetemp=.c4-debug-test-tmp`
  → 106 passed, 0.39 seconds.
* From `apps/web`: `node --test tests/manual-prediction.test.cjs`
  → 4 passed, 0 failed. Tests render the actual React result component for all
  three labels with warnings and for a warning-free result.
* From `apps/web`: `npm.cmd run build`
  → TypeScript and Vite production build passed (63 modules). Initial sandbox
  build could not read parent directories; approved rerun passed.

New backend assertions compare API outputs directly against the loaded
estimator's predict and predict_proba, find Trusted through the estimator's
actual class mapping, assert exact subtraction and all 18 feature values,
check healthy/unhealthy warning separation, response message consistency,
and verify only one probability call is made. No expected artifact prediction
label is hardcoded in these assertions.
