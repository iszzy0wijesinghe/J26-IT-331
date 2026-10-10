# 03_GEONEX_DATASET_ARCHITECTURE.md

**Project:** GeoNex --- Smart Landslide Early Warning Prediction System
using IoT, Edge AI and Risk Analytics\
**Document:** Research Dataset Architecture\
**Status:** Dataset Architecture Baseline\
**Depends on:** `00_GEONEX_SYSTEM_DEVELOPMENT_PLAN.md`,
`01_GEONEX_END_TO_END_ARCHITECTURE.md`,
`02_GEONEX_DATA_DATABASE_ARCHITECTURE.md`\
**Purpose:** Define how reproducible ML datasets for C1, C2, C3 and C4
are constructed, versioned, split, validated and mapped to the shared
GeoNex operational data architecture.

------------------------------------------------------------------------

# 1. Why This Document Exists

GeoNex has four research components with different learning problems:

``` text
C1 → measurement credibility classification
C2 → silence/failure diagnosis and recovery support
C3 → temporal future-risk forecasting
C4 → telemetry/device trust assessment
```

They must not be trained from arbitrary spreadsheets independently
created by four developers.

This document defines the shared dataset rules and the
component-specific dataset contracts that development must follow.

The central principle is:

> **Operational data is evidence. A research dataset is a reproducible,
> versioned transformation of that evidence for a specific research
> question.**

------------------------------------------------------------------------

# 2. Dataset Architecture Overview

``` text
Operational Database
        │
        ├── raw packets
        ├── observations
        ├── device/network metadata
        ├── component assessments
        ├── recovery provenance
        ├── Golden Timeline
        └── ground-truth annotations
                 │
                 ▼
          Dataset Builders
                 │
       ┌─────────┼─────────┬─────────┐
       ↓         ↓         ↓         ↓
      C1        C2        C3        C4
   Dataset   Dataset   Dataset   Dataset
       │         │         │         │
       ▼         ▼         ▼         ▼
 Versioned Parquet / CSV + Manifest
       │         │         │         │
       ▼         ▼         ▼         ▼
 Training → Validation → Testing → Evaluation
```

Each component receives its own dataset because the unit of prediction
and research question differ.

------------------------------------------------------------------------

# 3. CSV and Parquet Policy

CSV remains useful for:

-   human inspection;
-   small controlled exports;
-   interoperability;
-   supervisor/research review.

Parquet is recommended for larger experimental datasets because it
preserves types better and is more efficient for analytical workflows.

Recommended pattern:

``` text
canonical research export → Parquet
optional inspection export → CSV
manifest → YAML/JSON
```

Neither format is the live GeoNex database.

------------------------------------------------------------------------

# 4. Every Dataset Must Have a Manifest

Each frozen dataset version must have metadata similar to:

``` yaml
dataset_code: C3_TEMPORAL
version: 1
schema_version: 1
created_at: <timestamp>
source_cutoff_at: <timestamp>
source_types:
  - SYNTHETIC
builder_version: <git/version identifier>
split_strategy: temporal_event_zone_aware
random_seed: 42
row_count: <generated value>
file_hash: <generated hash>
```

Values must be generated from the actual build and must not be manually
invented.

------------------------------------------------------------------------

# 5. Common Dataset Metadata

Where relevant, exported records/windows should retain metadata such as:

``` text
record_id
dataset_version
source_origin
test_run_id
zone_id
device_id
observed_at / window_end
```

These fields are primarily for lineage and splitting.

They are **not automatically ML features**.

------------------------------------------------------------------------

# 6. Field Roles

Every dataset field must be assigned a role.

Allowed conceptual roles:

``` text
IDENTIFIER
METADATA
FEATURE
TARGET
PROVENANCE
QUALITY
SPLIT_KEY
DEBUG_ONLY
```

One field may serve multiple non-model roles, but every field used by a
model must explicitly be marked `FEATURE`.

This prevents accidental feature leakage.

------------------------------------------------------------------------

# 7. Feature Registry

Each component should maintain a machine-readable feature specification.

Example:

``` yaml
feature_name: soil_moisture_mean
role: FEATURE
dtype: float32
unit: "%"
source: golden_observations
derivation: mean over approved soil-moisture channels
causal_availability: runtime
nullable: true
```

This is preferable to allowing training code to select every numeric
column automatically.

------------------------------------------------------------------------

# 8. Mandatory Rule --- Never Train on "All Columns Except Label"

Code such as:

``` python
X = df.drop(columns=["label"])
```

is unsafe for GeoNex unless the schema has already guaranteed that every
remaining field is a valid feature.

Datasets contain identifiers, timestamps, provenance and potentially
target-derived fields.

Feature selection must be explicit.

------------------------------------------------------------------------

# 9. Ground Truth Is Separate From Prediction

The following must remain conceptually separate:

``` text
ground_truth_label
model_prediction
```

A prediction from C1 v1 cannot silently become the ground-truth label
used to train C1 v2.

Pseudo-labeling, if ever investigated, must be explicitly identified as
such and evaluated separately.

------------------------------------------------------------------------

# 10. Source-Origin Policy

Dataset records must identify origin where applicable:

``` text
SYNTHETIC
PHYSICAL_DEMO
EXTERNAL
SIMULATED
RECOVERED
DERIVED
```

`RECOVERED` and `DERIVED` may also be value-level provenance rather than
entire-dataset origin.

The critical requirement is that physical, synthetic and external
evidence remain distinguishable.

------------------------------------------------------------------------

# 11. Dataset Splitting Principles

The default research split must not simply be:

``` text
random row split
```

when rows are correlated by time, event, device or generated scenario.

Potential grouping dimensions include:

``` text
scenario/event
time block
zone
device
storm episode
failure episode
attack episode
simulation seed/run
```

The correct split is component-specific.

------------------------------------------------------------------------

# 12. Train / Validation / Test Roles

``` text
TRAIN
→ fit model parameters

VALIDATION
→ tune hyperparameters / select model / thresholds

TEST
→ final unbiased evaluation
```

The test set must not be repeatedly used to make design decisions.

Final ratios are not universally frozen here; they must be selected
based on available data and grouping constraints.

------------------------------------------------------------------------

# 13. Scaling and Preprocessing Leakage

Transformations such as:

``` text
normalization
standardization
imputation statistics
categorical encoders
feature selection
```

must be fitted on training data only when they learn statistics from
data.

Then the fitted transformation is applied to validation/test.

Do not calculate global mean/std before splitting.

------------------------------------------------------------------------

# 14. Dataset Builder Pattern

Each component should implement:

``` text
source query/input
      ↓
eligibility filters
      ↓
feature derivation
      ↓
ground-truth attachment
      ↓
leakage checks
      ↓
schema validation
      ↓
group-aware split
      ↓
dataset export
      ↓
manifest + hash
```

Dataset generation must be code-driven and reproducible.

------------------------------------------------------------------------

# 15. C1 Research Question

**C1 --- Rainfall Regime-Aware Sensor Credibility Classification**

Main question:

> Is a sensor observation credible, anomalous/faulty, or a genuine
> unusual environmental event when environmental and neighbouring
> context are considered?

The key research challenge is avoiding:

``` text
unusual measurement
      ↓
automatically classify as fault
```

because a genuine landslide precursor may itself be unusual.

------------------------------------------------------------------------

# 16. C1 Unit of Prediction

Recommended C1 unit:

``` text
one target sensor observation
+
context available at that time
```

Therefore a C1 dataset row represents a target observation and
contextual features derived without using future information.

------------------------------------------------------------------------

# 17. C1 Target

Current research labels:

``` text
CLEAN
ANOMALY
VALID_EVENT
```

These are the baseline dataset target concepts.

Before final physical-data training, the team must document how each
label is obtained.

The target field should be:

``` text
credibility_label
```

The exact numeric encoding is a training implementation detail.

------------------------------------------------------------------------

# 18. C1 Core Metadata Fields

Recommended non-feature fields:

``` text
record_id
observation_id
zone_id
device_id
sensor_instance_id
observed_at
source_origin
test_run_id
dataset_version
```

These support traceability and split construction.

Do not automatically feed IDs into the model.

------------------------------------------------------------------------

# 19. C1 Candidate Direct-Measurement Features

Depending on the sensor being assessed:

``` text
target_value
target_raw_value
sensor_type
```

For generic multi-sensor C1 models, `sensor_type` may be encoded
appropriately.

Alternatively, separate models can be investigated for sensor families.

This choice must be experimentally justified.

------------------------------------------------------------------------

# 20. C1 Historical Features

Only using information available at the prediction time, possible
features include:

``` text
previous_value
delta_from_previous
rolling_mean
rolling_std
rolling_median
rolling_min
rolling_max
rate_of_change
time_since_previous_s
```

Window sizes must be explicitly defined and versioned.

------------------------------------------------------------------------

# 21. C1 Rainfall-Regime Features

Because rainfall context is central to C1's research contribution,
candidate features include:

``` text
rain_recent
rain_15m_sum
rain_1h_sum
rain_6h_sum
rainfall_rate
rainfall_regime
time_since_rain_started
```

Only features supported by the implemented rainfall measurement and
dataset source may be used.

Do not fabricate unavailable rainfall measurements.

------------------------------------------------------------------------

# 22. C1 Neighbour Features

Candidate spatial/context features:

``` text
neighbour_mean
neighbour_median
neighbour_std
target_minus_neighbour_mean
neighbour_agreement_count
neighbour_trend
```

The neighbour definition must be deterministic.

Example:

``` text
same sensor family
+
same zone / explicitly configured adjacent zone
+
valid observations within permitted time tolerance
```

Do not use arbitrary future-nearest rows.

------------------------------------------------------------------------

# 23. C1 Device-Health Context

Possible supporting features:

``` text
device_voltage
sensor_read_error_recent
restart_recent
communication_quality
```

These can help distinguish environmental extremes from hardware
problems.

Their contribution should be evaluated rather than assumed.

------------------------------------------------------------------------

# 24. C1 C4 Dependency

At runtime, C1 should normally operate on packets that satisfy the
approved C4 policy.

C4 trust metadata may additionally be retained for research.

However:

> C1 must not simply learn "C4 untrusted = C1 anomaly."

That would collapse two different research problems.

C1's target remains measurement credibility.

------------------------------------------------------------------------

# 25. C1 Proposed Dataset Schema

A baseline logical schema:

  Field                           Role
  ------------------------------- --------------------
  `record_id`                     IDENTIFIER
  `observation_id`                PROVENANCE
  `zone_id`                       SPLIT_KEY/METADATA
  `device_id`                     SPLIT_KEY/METADATA
  `sensor_instance_id`            METADATA
  `observed_at`                   SPLIT_KEY/METADATA
  `source_origin`                 PROVENANCE
  `sensor_type`                   FEATURE candidate
  `target_value`                  FEATURE
  `previous_value`                FEATURE
  `delta_from_previous`           FEATURE
  `rolling_mean`                  FEATURE
  `rolling_std`                   FEATURE
  `time_since_previous_s`         FEATURE
  `rain_15m_sum`                  FEATURE
  `rain_1h_sum`                   FEATURE
  `rainfall_regime`               FEATURE
  `neighbour_mean`                FEATURE
  `neighbour_std`                 FEATURE
  `target_minus_neighbour_mean`   FEATURE
  `device_voltage`                FEATURE candidate
  `credibility_label`             TARGET

The final feature list will be frozen in the C1 member specification
after availability checks.

------------------------------------------------------------------------

# 26. C1 Example Row

Illustrative only:

``` csv
record_id,zone_id,device_id,sensor_type,target_value,previous_value,delta_from_previous,rain_1h_sum,neighbour_mean,target_minus_neighbour_mean,credibility_label
c1_example_001,Z01,Z01-A01,SOIL_MOISTURE,86.2,78.1,8.1,24.5,84.9,1.3,VALID_EVENT
```

The values are illustrative and are not physical GeoNex measurements.

------------------------------------------------------------------------

# 27. C1 Leakage Rules

C1 must not use:

-   its own predicted credibility score as ground truth;
-   future target-sensor observations;
-   neighbour observations that arrived after the simulated decision
    time;
-   labels encoded indirectly in scenario names;
-   manually injected anomaly flags that directly reveal the target
    unless intentionally used only to create ground truth.

------------------------------------------------------------------------

# 28. C1 Split Strategy

Recommended hierarchy:

1.  keep strongly related scenario/event records together;
2.  where possible, test temporal generalization;
3.  consider device/zone holdout experiments to test spatial/device
    generalization;
4.  stratify at the group level where feasible to preserve class
    coverage.

A random row split can be retained only as a secondary baseline if
clearly identified.

------------------------------------------------------------------------

# 29. C1 Evaluation Dataset Requirements

The held-out C1 test set should include:

``` text
normal observations
true sensor anomalies/faults
genuine environmental extremes
different rainfall regimes
neighbour disagreement cases
```

The important error is not only missing anomalies.

A dangerous error is:

``` text
VALID_EVENT → ANOMALY
```

because genuine warning evidence could be discarded.

------------------------------------------------------------------------

# 30. C2 Research Question

**C2 --- Silent-Pattern Diagnostic Classification via Backup Pipe
Verification**

Main question:

> When expected telemetry becomes silent, what is the likely cause and
> what recovery/escalation action is appropriate?

C2 is event-oriented rather than ordinary per-reading classification.

------------------------------------------------------------------------

# 31. C2 Unit of Prediction

Recommended unit:

``` text
one silence/failure episode
```

A C2 dataset row should describe the state around a detected silence
event.

It should not simply classify every normal telemetry row.

------------------------------------------------------------------------

# 32. C2 Stage A --- Failure Diagnosis Target

Current target taxonomy from existing work:

``` text
normal
communication_failure
hardware_failure
possible_zone_damage
```

For a dataset built specifically from already-triggered abnormal silence
events, `normal` may not belong in the diagnostic stage.

Therefore C2 should conceptually separate:

``` text
Stage 0 → is silence abnormal?
Stage A → if abnormal, what is the cause?
Stage B → what recovery/escalation action?
```

This prevents task ambiguity.

------------------------------------------------------------------------

# 33. C2 Existing Research Data

Existing C2 work includes:

``` text
landslide_silence_dataset_20000.csv
```

with target:

``` text
Label
```

and:

``` text
C2_Recovery.csv
```

with targets/concepts:

``` text
failure_type
c2_target_action
```

Existing action mappings include:

``` text
sensor_link_gap       → REQUEST_SD_REPLAY
primary_sensor_failure→ ACTIVATE_BACKUP_SENSOR
multi_sensor_gap      → USE_NEIGHBOR_FUSION
hub_failure           → SWITCH_BACKUP_HUB
zone_network_failure  → ESCALATE
```

These existing datasets must be mapped into the canonical schema rather
than discarded.

------------------------------------------------------------------------

# 34. C2 Event Metadata

Recommended metadata:

``` text
silence_event_id
zone_id
device_id
sensor_instance_id
expected_at
detected_at
current_mode
sampling_policy_id
source_origin
test_run_id
failure_episode_id
```

------------------------------------------------------------------------

# 35. C2 Timing Features

C2 requires mode-aware timing.

Candidate features:

``` text
expected_interval_s
grace_interval_s
time_since_last_packet_s
missed_expected_reports
last_packet_delay_s
recent_mean_delay_s
recent_delay_std_s
recent_packet_loss_rate
```

A fixed silence threshold across all modes is incorrect.

------------------------------------------------------------------------

# 36. C2 Device-Health Features

Possible features:

``` text
last_known_voltage
voltage_trend
restart_recent
sensor_read_failures_recent
sd_available
device_health_error_count
```

Only telemetry actually available from the hardware/firmware should
enter the final dataset.

------------------------------------------------------------------------

# 37. C2 Communication Features

Possible features:

``` text
last_rssi_dbm
last_snr_db
recent_rssi_mean
recent_snr_mean
retry_count
gateway_received_other_devices
neighbour_devices_reporting
```

These can help distinguish:

``` text
single-device communication problem
```

from:

``` text
wider network/zone disruption
```

------------------------------------------------------------------------

# 38. C2 Backup Verification Features

Because independent backup verification is central to C2:

``` text
backup_available
backup_query_sent
backup_response_received
backup_response_latency_s
backup_measurement_available
backup_environment_abnormal
backup_device_health_ok
```

Important:

Features obtained only after a backup query cannot be used by a model
intended to make the pre-query decision.

Therefore C2 may need two feature stages:

``` text
pre-verification diagnosis
post-verification diagnosis
```

or a sequential diagnostic workflow.

------------------------------------------------------------------------

# 39. C2 Neighbour/Hub Context

Candidate features:

``` text
same_zone_reporting_fraction
neighbour_pipe_status
hub_status
other_zone_status
same_zone_environment_abnormality
```

These can support zone-level diagnosis.

------------------------------------------------------------------------

# 40. C2 Diagnostic Dataset Schema

Baseline logical schema:

  Field                            Role
  -------------------------------- ------------------------------------
  `silence_event_id`               IDENTIFIER
  `failure_episode_id`             SPLIT_KEY
  `zone_id`                        SPLIT_KEY
  `device_id`                      METADATA
  `detected_at`                    METADATA/SPLIT_KEY
  `current_mode`                   FEATURE
  `expected_interval_s`            FEATURE
  `time_since_last_packet_s`       FEATURE
  `missed_expected_reports`        FEATURE
  `recent_packet_loss_rate`        FEATURE
  `last_rssi_dbm`                  FEATURE candidate
  `last_snr_db`                    FEATURE candidate
  `last_known_voltage`             FEATURE candidate
  `restart_recent`                 FEATURE candidate
  `same_zone_reporting_fraction`   FEATURE
  `hub_status`                     FEATURE
  `backup_response_received`       FEATURE in post-verification model
  `backup_environment_abnormal`    FEATURE in post-verification model
  `failure_class`                  TARGET

------------------------------------------------------------------------

# 41. C2 Example Diagnostic Row

Illustrative:

``` csv
silence_event_id,zone_id,device_id,current_mode,expected_interval_s,time_since_last_packet_s,missed_expected_reports,same_zone_reporting_fraction,backup_response_received,failure_class
c2_example_001,Z01,Z01-A01,RISK,30,95,3,0.75,true,communication_failure
```

Values are illustrative, not measured prototype results.

------------------------------------------------------------------------

# 42. C2 Recovery Dataset

The recovery decision is a related but separate problem.

Possible schema:

  Field                    Role
  ------------------------ ------------------------------------------
  `silence_event_id`       PROVENANCE
  `failure_class`          FEATURE if known before action
  `backup_available`       FEATURE
  `sd_replay_available`    FEATURE
  `neighbour_coverage`     FEATURE
  `backup_hub_available`   FEATURE
  `risk_context`           FEATURE candidate
  `target_action`          TARGET
  `recovery_success`       OUTCOME, not necessarily training target
  `recovery_latency_s`     OUTCOME
  `recovery_confidence`    OUTCOME

------------------------------------------------------------------------

# 43. C2 Lookup-Table Risk

If:

``` text
failure_class → target_action
```

is always one-to-one by design, training an ML model to learn that
mapping has little research value.

Therefore C2 must compare:

``` text
deterministic recovery policy baseline
```

against any learned action-selection approach.

ML is justified only if contextual evidence makes action selection
non-trivial and measurable.

------------------------------------------------------------------------

# 44. C2 Outcome Leakage

Do not use:

``` text
recovery_success
recovery_latency
post-recovery sensor state
```

as input features when predicting which recovery action to choose before
the action occurs.

They are future outcomes.

They may be used for evaluation or later policy-learning research only
under a correctly defined causal setup.

------------------------------------------------------------------------

# 45. C2 Split Strategy

Keep all rows from the same induced/real failure episode in one split.

Otherwise:

``` text
same failure episode
→ train rows
+
test rows
```

can create severe leakage.

Also consider holding out:

``` text
device
zone
failure scenario
```

for robustness experiments.

------------------------------------------------------------------------

# 46. C3 Research Question

**C3 --- Mode-Conditioned Variable-Rate Multi-Sensor Temporal
Forecasting**

Main question:

> Given the trustworthy/recovered multivariate history available now,
> what is the probability that dangerous landslide-related conditions
> will develop within a future horizon?

C3 is fundamentally temporal.

------------------------------------------------------------------------

# 47. C3 Unit of Prediction

C3's natural sample is not one isolated row.

It is:

``` text
historical temporal window
        ↓
forecast origin t
        ↓
future horizon H
        ↓
target outcome
```

Example:

``` text
history available through 10:00
        ↓
predict whether target event occurs by 10:30
```

------------------------------------------------------------------------

# 48. C3 Forecast Origin

Each sample requires:

``` text
forecast_at
```

All model inputs must represent information available at or before this
forecast origin according to the experiment's as-of policy.

------------------------------------------------------------------------

# 49. C3 Horizon

C3 should support explicit forecast horizons.

Conceptually:

``` text
15 min
30 min
60 min
```

These are examples, not frozen final horizons.

The final horizons must be justified by:

-   warning usefulness;
-   data characteristics;
-   physical process;
-   available labels;
-   experimental feasibility.

------------------------------------------------------------------------

# 50. C3 Input Sources

Primary C3 input should come from the Golden Timeline or a frozen
equivalent generated under a documented policy.

Potential information:

``` text
rainfall
soil moisture
ground force/FSR response where scientifically justified
tilt
vibration
temperature/humidity where useful
neighbour-zone context
current mode
Δt
missingness
recovery provenance
credibility summaries
```

Not every available sensor must be included simply because it exists.

------------------------------------------------------------------------

# 51. C3 Sequence Representation

A sequence should preserve:

``` text
value
time
Δt
mode
missingness
provenance/quality
```

A conceptual step:

``` text
x_t = [
    soil_moisture,
    rainfall,
    tilt,
    vibration,
    ...
    delta_t,
    mode_encoding,
    missingness indicators,
    recovery indicators
]
```

The exact tensor design depends on the selected model.

------------------------------------------------------------------------

# 52. Δt Definition

At sequence step `t`:

``` text
Δt_t = effective_time_t - effective_time_(t-1)
```

If the model uses per-feature irregular timing, it may instead require:

``` text
Δt for each feature since last observed value
```

GRU-D-style architectures often model
missingness/time-since-last-observation explicitly.

The chosen representation must match the selected architecture.

------------------------------------------------------------------------

# 53. C3 Mode Feature

Candidate:

``` text
current_system_mode
```

Mode may be encoded as:

-   one-hot;
-   embedding;
-   ordinal representation only if scientifically justified.

Because the modes have operational ordering, ordinal information exists,
but assuming equal numeric distance between modes is not automatically
justified.

------------------------------------------------------------------------

# 54. C3 Missingness Features

Missingness itself may contain information.

Candidate masks:

``` text
soil_moisture_observed
rainfall_observed
tilt_observed
vibration_observed
```

and time-since-last-valid observation.

Do not silently forward-fill everything before the model without
preserving that information was missing.

------------------------------------------------------------------------

# 55. C3 Recovery Features

Candidate:

``` text
recovered_flag
recovery_method
recovery_confidence
recovered_fraction_in_window
```

This lets the model know that a value came from recovery rather than
direct sensing.

An ablation should test whether provenance information improves
robustness.

------------------------------------------------------------------------

# 56. C3 Credibility Features

Candidate window-level or step-level information:

``` text
credibility_class
credibility_score
anomaly_fraction_in_window
valid_event_fraction
```

Care is required because C1 outputs are model-derived features.

Experiments should compare:

``` text
without C1 context
vs
with C1 context
```

as already planned.

------------------------------------------------------------------------

# 57. C3 Existing Dataset Fields

Existing C3 work has used fields such as:

``` text
rain_15m_sum
rain_1h_sum
rain_6h_sum
soil_moisture_mean
soil_moisture_trend_30m
tilt_mean_deg
tilt_rate_deg_h
vibration_mean_g
estimated_input_pct
mean_repair_confidence
current_system_mode
horizon_min
risk_probability
risk_level
recommended_mode
target_landslide_within_horizon
```

These must now be audited by role and provenance before reuse.

------------------------------------------------------------------------

# 58. C3 Critical Target-Leakage Audit

The following fields are dangerous until their provenance is proven:

``` text
risk_probability
risk_level
recommended_mode
```

Questions that must be answered:

``` text
Was risk_probability generated from target_landslide_within_horizon?
Was risk_level derived from risk_probability?
Was recommended_mode derived from risk_level?
```

If yes, these cannot be used as input features for predicting the same
underlying target.

They may instead be:

-   targets;
-   downstream decision outputs;
-   synthetic-generator helper variables;
-   debug-only fields.

------------------------------------------------------------------------

# 59. C3 Primary Target Design

A strong baseline target is:

``` text
target_landslide_within_horizon
```

where:

``` text
0 = no target event within horizon
1 = target event within horizon
```

But this is valid only if the event definition is independently
grounded.

For synthetic data, the generator must define the event-generation
mechanism explicitly.

For physical/external data, event labels require defensible ground
truth.

------------------------------------------------------------------------

# 60. C3 Risk Class

A categorical:

``` text
LOW
WATCH
HIGH
CRITICAL
```

can be useful operationally.

However it must be clear whether this is:

``` text
a model target
```

or:

``` text
a deterministic mapping from predicted probability
```

Do not train and evaluate it as independent ground truth if it is merely
derived from the same model probability.

------------------------------------------------------------------------

# 61. C3 Time-to-Danger

`time_to_danger` is a possible secondary target.

It requires:

-   a clearly defined danger/event time;
-   censoring treatment when no event occurs;
-   appropriate loss/evaluation method.

It should not be added casually as ordinary regression if the label is
not valid.

A survival/time-to-event formulation may eventually be considered, but
only if supported by data and research scope.

------------------------------------------------------------------------

# 62. C3 Wide Window Metadata

Each sequence/window should have metadata such as:

``` text
sample_id
zone_id
scenario_id
forecast_at
window_start
window_end
horizon_min
source_origin
dataset_version
```

These are not automatically model inputs.

------------------------------------------------------------------------

# 63. C3 Sequence Storage Formats

Two useful exported forms are:

## Long sequence form

``` text
sample_id
step
effective_at
feature_code
value
observed_mask
delta_t
...
```

## Tensor-ready/wide form

Generated by the training loader.

The canonical dataset can use Parquet tables plus a deterministic
sequence builder rather than storing enormous CSV arrays.

------------------------------------------------------------------------

# 64. C3 Baseline Tabular Dataset

For LightGBM/XGBoost baselines, temporal windows can be summarized into
engineered features:

``` text
latest value
mean
std
min
max
slope
recent change
rainfall accumulations
missing fraction
recovered fraction
```

This provides a strong non-deep-learning baseline.

------------------------------------------------------------------------

# 65. C3 Recurrent Dataset

For GRU/LSTM/time-aware models, retain ordered steps.

Conceptually:

``` text
X.shape = [samples, timesteps, features]
```

plus potentially:

``` text
mask.shape
delta_t.shape
mode.shape
```

Variable-length sequences should use appropriate padding/masking or
packed sequence handling.

------------------------------------------------------------------------

# 66. C3 Ablation Plan

The dataset architecture must support the planned sequence:

``` text
A0 — Sensors
A1 — Sensors + History
A2 — + Δt
A3 — + Mode
A4 — + C1 credibility
A5 — + C2 recovery/provenance
```

This is important because it tests the research contribution
incrementally.

The same split should be reused across ablations where possible.

------------------------------------------------------------------------

# 67. C3 Split Strategy

C3 must not use naive random row/window splitting.

Recommended grouping:

``` text
storm/event/scenario
+
time
```

Potential robust evaluation:

``` text
train → earlier events/scenarios
validation → separate events
test → unseen later events/scenarios
```

Zone holdout can additionally test spatial generalization if enough
zones/data exist.

With only two physical demo zones, claims about geographic
generalization must remain conservative.

------------------------------------------------------------------------

# 68. Overlapping Window Leakage

Suppose:

``` text
Window A = 09:00–10:00
Window B = 09:01–10:01
```

These windows share almost all observations.

If A is in training and B is in test, reported performance can be
misleading.

Therefore split the underlying event/time blocks **before** generating
overlapping windows whenever practical.

------------------------------------------------------------------------

# 69. C3 As-Of-Time Rule

For a forecast at time `T`, runtime-equivalent features may only use
information actually available by `T`.

A late replay:

``` text
observed_at = 09:50
received_at = 10:10
```

must not be used for a forecast made at:

``` text
T = 10:00
```

even though its observation timestamp is before 10:00.

This rule is essential.

------------------------------------------------------------------------

# 70. C3 Example Tabular Baseline Row

Illustrative:

``` csv
sample_id,zone_id,forecast_at,horizon_min,rain_15m_sum,rain_1h_sum,soil_moisture_mean,soil_moisture_trend_30m,tilt_mean_deg,tilt_rate_deg_h,vibration_mean_g,current_system_mode,recovered_fraction,target_landslide_within_horizon
c3_example_001,Z01,2026-10-10T04:30:00Z,30,12.4,31.8,78.2,4.6,3.1,0.7,0.12,WARNING,0.08,1
```

All numeric values are illustrative.

------------------------------------------------------------------------

# 71. C3 Dataset Output Contract

Recommended exported artifacts:

``` text
c3_windows.parquet
c3_labels.parquet
c3_split_manifest.parquet
dataset_manifest.yaml
feature_schema.yaml
```

Optional:

``` text
c3_preview.csv
```

This is preferable to a single uncontrolled CSV containing everything.

------------------------------------------------------------------------

# 72. C4 Research Question

**C4 --- Trusted Telemetry Provenance and Device Attestation**

Main question:

> Is telemetry from an expected legitimate device and does the
> source/transmission behaviour remain trustworthy?

C4 combines deterministic security verification and behavioural ML.

------------------------------------------------------------------------

# 73. C4 Unit of Prediction

The ML behavioural unit may be:

``` text
packet
```

or:

``` text
packet + recent device behaviour window
```

depending on the experiment.

Mandatory cryptographic/identity checks remain deterministic.

------------------------------------------------------------------------

# 74. C4 Deterministic Fields

Examples:

``` text
device_registered
identity_valid
signature_valid
payload_hash_valid
counter_valid
freshness_valid
nonce_reused
firmware_approved
```

These are security verification outcomes.

Some may be features/context for analysis, but the final security gate
must not rely solely on ML.

------------------------------------------------------------------------

# 75. C4 Behavioural Features

Candidate features:

``` text
packet_interval_s
packet_interval_deviation
packet_delay_s
packet_size_bytes
retry_count
rssi_dbm
snr_db
rssi_deviation
snr_deviation
restart_count_recent
counter_jump
location/hub_consistency
```

Only fields available from the implemented protocol/hardware should be
retained in the final production feature set.

------------------------------------------------------------------------

# 76. C4 Target

Current conceptual classes:

``` text
TRUSTED
SUSPICIOUS
UNTRUSTED
```

Existing data may also contain:

``` text
label_untrusted_binary
```

The multi-class and binary tasks must not be mixed without documenting
which experiment is being run.

------------------------------------------------------------------------

# 77. C4 Dataset Schema

Baseline logical schema:

  Field                      Role
  -------------------------- ---------------------------------
  `record_id`                IDENTIFIER
  `packet_id`                PROVENANCE
  `device_id`                SPLIT_KEY/METADATA
  `zone_id`                  SPLIT_KEY/METADATA
  `observed_at`              METADATA
  `received_at`              METADATA
  `source_origin`            PROVENANCE
  `device_registered`        DETERMINISTIC/FEATURE candidate
  `identity_valid`           DETERMINISTIC/FEATURE candidate
  `signature_valid`          DETERMINISTIC
  `freshness_valid`          DETERMINISTIC
  `nonce_reused`             DETERMINISTIC
  `packet_interval_s`        FEATURE
  `packet_delay_s`           FEATURE
  `rssi_dbm`                 FEATURE
  `snr_db`                   FEATURE
  `retry_count`              FEATURE
  `restart_count_recent`     FEATURE
  `hub_consistency`          FEATURE candidate
  `trust_label`              TARGET
  `label_untrusted_binary`   TARGET for binary experiment

------------------------------------------------------------------------

# 78. C4 Example Row

Illustrative:

``` csv
record_id,device_id,device_registered,signature_valid,freshness_valid,nonce_reused,packet_interval_s,rssi_dbm,snr_db,retry_count,trust_label
c4_example_001,Z01-A01,true,true,true,false,30.4,-72,8.1,0,TRUSTED
```

Values are illustrative.

------------------------------------------------------------------------

# 79. C4 ML Must Not Re-Learn Cryptography

A classifier should not be presented as replacing signature
verification.

Correct architecture:

``` text
Mandatory deterministic verification
          │
          ├── fail → reject/quarantine according to policy
          │
          └── pass
               ↓
       Behavioural ML assessment
               ↓
       trust/anomaly evidence
```

ML adds behavioural detection; it does not mathematically prove
authenticity.

------------------------------------------------------------------------

# 80. C4 Attack/Anomaly Scenario Grouping

Synthetic/simulated C4 data should be grouped by attack/scenario run.

Examples:

``` text
replay episode
spoofing episode
timing manipulation episode
radio-behaviour anomaly episode
normal device session
```

Packets from the same attack episode should not be randomly split across
train/test.

------------------------------------------------------------------------

# 81. C4 Novelty Evaluation

If an anomaly detector such as Isolation Forest is tested, evaluation
should distinguish:

``` text
known labelled attack classification
```

from:

``` text
novel/unseen behavioural anomaly detection
```

These are different claims.

------------------------------------------------------------------------

# 82. Cross-Component Dataset Boundaries

The four datasets are related but not identical.

``` text
C4
packet/source level

C1
measurement level

C2
silence/failure episode level

C3
temporal window/forecast level
```

This distinction must remain visible in implementation.

------------------------------------------------------------------------

# 83. Cross-Component Feature Use

Downstream components may use upstream outputs only when:

1.  those outputs would exist at runtime;
2.  their processing time is before the downstream decision time;
3.  their model/version is recorded;
4.  the experiment explicitly includes them.

Example:

``` text
C3 + C1 experiment
```

may use C1 credibility.

The baseline C3 experiment should remain possible without it.

------------------------------------------------------------------------

# 84. Out-of-Fold Upstream Predictions

When a downstream model is trained using predictions from an upstream
learned model, a subtle leakage risk appears.

Bad approach:

``` text
train C1 on all training records
predict those same records
use overfitted C1 predictions to train C3
```

Preferred research approach:

``` text
generate out-of-fold C1 predictions
```

for downstream training, or use a separately trained upstream model that
has not fitted the downstream sample being scored.

The same principle applies where learned C2/C4 outputs become downstream
ML features.

------------------------------------------------------------------------

# 85. Why Out-of-Fold Predictions Matter

Otherwise C3 may see unrealistically perfect upstream outputs during
training but noisier outputs at runtime.

That produces train/serve mismatch and optimistic results.

Therefore upstream model-derived features require explicit generation
methodology.

------------------------------------------------------------------------

# 86. Dataset Schema Versioning

Any breaking change to:

``` text
field name
dtype
unit
meaning
target definition
window definition
```

requires a schema-version update.

Adding a field does not automatically mean it should become a model
feature.

------------------------------------------------------------------------

# 87. Feature Schema Versioning

Dataset schema and feature schema are different.

Example:

``` text
dataset schema v3
```

may contain 40 columns.

Experiment:

``` text
feature schema C3_A2_v1
```

may intentionally use only 18 of them.

This supports ablation studies without generating unrelated datasets
unnecessarily.

------------------------------------------------------------------------

# 88. Label Schema Versioning

If the definition of a label changes, version it.

Example:

``` text
C1 credibility label v1
```

must not be silently replaced by a different anomaly definition while
keeping the same dataset version.

------------------------------------------------------------------------

# 89. Synthetic Generator Versioning

Synthetic datasets must record:

``` text
generator_version
configuration_version
random_seed
scenario_id
```

A generator change can alter the statistical problem even when column
names stay identical.

------------------------------------------------------------------------

# 90. Current C3 Synthetic Dataset History

Existing research work has included:

``` text
basic_c3_sensor_data.csv
c3_temporal_synthetic_v2.csv
c3_temporal_synthetic_v3.csv
```

and later generator work toward v4.

These are historical experimental artifacts.

They should be registered/migrated into the new dataset registry rather
than treated as the final canonical C3 dataset automatically.

------------------------------------------------------------------------

# 91. Historical Dataset Migration

For every existing dataset:

``` text
inspect schema
identify generator/source
identify target construction
identify leakage risks
identify units
identify scenario grouping
assign dataset version
create manifest
```

Only then should it enter the new standardized experimentation pipeline.

------------------------------------------------------------------------

# 92. Dataset Validation

Every builder must validate:

``` text
required fields exist
dtypes correct
units correct
enums valid
timestamps valid
IDs resolvable
target present
no impossible duplicate keys
feature ranges plausible
split keys present
source origin known
```

Validation failure should stop the build rather than silently produce a
questionable dataset.

------------------------------------------------------------------------

# 93. Statistical Dataset Report

Each generated dataset version should automatically produce a report
containing at least:

``` text
row/sample count
class distribution
missingness
source-origin distribution
zone/device distribution
time range
scenario count
feature summary
split distribution
```

C3 should additionally report:

``` text
window count
event count
horizon distribution
positive-event rate
mode distribution
```

------------------------------------------------------------------------

# 94. Class Imbalance

GeoNex is likely to contain imbalanced events.

Do not solve imbalance by blindly oversampling before the split.

Correct order:

``` text
group-aware split
      ↓
training set only
      ↓
class weighting / resampling / specialized loss if justified
```

Validation/test distributions should remain representative of the
intended evaluation.

------------------------------------------------------------------------

# 95. SMOTE and Temporal Data

SMOTE may be investigated for appropriate tabular tasks, but it should
not be automatically applied to C3 temporal sequences.

Synthetic interpolation between temporal windows can produce physically
questionable sequences.

For C3, alternatives include:

-   class-weighted loss;
-   event-aware sampling;
-   focal loss where justified;
-   scenario generation improvements.

Any method must be experimentally evaluated.

------------------------------------------------------------------------

# 96. Feature Scaling

Tree models such as Random Forest/XGBoost generally do not require
standardization in the same way neural networks often do.

GRU/LSTM models commonly benefit from appropriately scaled continuous
inputs.

Scaling parameters must be fitted on training data only and saved with
the model pipeline.

------------------------------------------------------------------------

# 97. Categorical Encoding

Examples:

``` text
mode
sensor_type
recovery_method
```

Encoding choices may include:

``` text
one-hot
embedding
ordinal
```

The choice depends on model family and semantic meaning.

Do not assign arbitrary integers and assume numeric distance is
meaningful.

------------------------------------------------------------------------

# 98. Missingness Handling

Each component must document:

``` text
what causes missingness
how missingness is represented
whether imputation is used
which imputation method
whether a missingness mask is preserved
```

C3 in particular should preserve missingness/time information when
evaluating GRU-D/time-aware approaches.

------------------------------------------------------------------------

# 99. Calibration and Dataset Generation

For physical sensor data:

``` text
raw sensor value
      ↓
calibration version
      ↓
engineering value
      ↓
dataset feature
```

Dataset manifests should record relevant calibration versions or a
reproducible source snapshot.

Do not manually edit exported CSV values to "fix" calibration.

------------------------------------------------------------------------

# 100. FSR Research Caution

FSR402 values should initially be treated as:

``` text
raw ADC / voltage / resistance-derived response
```

unless the team performs a defensible calibration.

Do not label an arbitrary FSR ADC value as:

``` text
pressure
stress
force in N
```

without the required calibration and mechanical assumptions.

------------------------------------------------------------------------

# 101. Rainfall Research Caution

The Centralized Sensor Hub rainfall mechanism must be calibrated before
raw load/level/distance measurements are treated as physically
meaningful rainfall quantities.

The dataset must distinguish:

``` text
raw mechanism signal
```

from:

``` text
calibrated rainfall amount/rate
```

------------------------------------------------------------------------

# 102. IMU Derived Features

Raw IMU channels may include:

``` text
accel_x/y/z
gyro_x/y/z
```

and, for MPU9250 where used:

``` text
mag_x/y/z
```

Derived features such as:

``` text
tilt
vibration magnitude
RMS vibration
orientation change
```

must record the derivation algorithm/version.

------------------------------------------------------------------------

# 103. Power Measurements

INA219/INA226 measurements primarily represent device/system health.

Examples:

``` text
voltage
current
power
```

They may be useful to C2/C4.

They should not automatically become C3 landslide-risk features unless a
defensible relationship/research reason exists.

------------------------------------------------------------------------

# 104. LoRa Metadata

Possible:

``` text
RSSI
SNR
packet timing
retry information
```

These are primarily communication/trust/diagnostic features for C2/C4.

They should not automatically become environmental forecasting features
for C3.

------------------------------------------------------------------------

# 105. Centralized Power Hub Data

The Centralized Power Hub is demonstration power infrastructure.

Unless its electrical meter becomes digitally integrated into the data
pipeline, it contributes no ML telemetry dataset.

Do not create fake Power Hub sensor columns merely because a display
exists physically.

------------------------------------------------------------------------

# 106. Dataset Folder Structure

Recommended:

``` text
data/
├── README.md
├── registry/
│   └── dataset_registry.yaml
│
├── raw_external/
│
├── synthetic/
│   ├── c1/
│   ├── c2/
│   ├── c3/
│   └── c4/
│
├── interim/
│
├── processed/
│   ├── c1/
│   ├── c2/
│   ├── c3/
│   └── c4/
│
└── manifests/
    ├── c1/
    ├── c2/
    ├── c3/
    └── c4/
```

Large datasets may be excluded from Git while manifests/schemas remain
version-controlled.

------------------------------------------------------------------------

# 107. Dataset Version Directory

Example:

``` text
processed/c3/C3_TEMPORAL_V001/
├── c3_windows.parquet
├── c3_labels.parquet
├── splits.parquet
├── manifest.yaml
├── feature_schema.yaml
└── validation_report.json
```

Optional small preview:

``` text
preview.csv
```

------------------------------------------------------------------------

# 108. Dataset Builder Code Structure

Recommended:

``` text
components/
└── c3_forecasting/
    └── datasets/
        ├── build.py
        ├── queries.py
        ├── features.py
        ├── labels.py
        ├── splits.py
        ├── validate.py
        └── schemas.py
```

Equivalent structure should exist for each component.

Shared dataset utilities belong under:

``` text
shared/data/
```

------------------------------------------------------------------------

# 109. Reproducible Build Command

Eventually each dataset should be buildable through a predictable
command.

Conceptually:

``` bash
python -m components.c3_forecasting.datasets.build \
  --config configs/datasets/c3_v1.yaml
```

The command should create:

``` text
dataset artifact
manifest
split file
validation report
hash
```

The exact CLI is finalized with repository implementation.

------------------------------------------------------------------------

# 110. Dataset Fingerprinting

A dataset version should have a cryptographic hash/fingerprint.

This lets a paper result state:

``` text
trained on C3_TEMPORAL_V001
hash = ...
```

and prevents two different files from silently sharing one version name.

------------------------------------------------------------------------

# 111. Split Manifest

Splits should be stored explicitly.

Example:

``` text
sample_id,split
S001,TRAIN
S002,TRAIN
S003,VALIDATION
S004,TEST
```

This ensures all competing models and ablations use the same evaluation
partition.

------------------------------------------------------------------------

# 112. No Manual Test-Set Cleaning

After the test set is frozen, developers must not manually remove
difficult test examples because they lower performance.

If a record is objectively invalid, removal requires:

``` text
documented reason
dataset version change
rebuild
```

------------------------------------------------------------------------

# 113. Evaluation Metrics --- C1

Recommended metrics include:

``` text
macro F1
per-class precision
per-class recall
confusion matrix
balanced accuracy where useful
```

Special attention:

``` text
VALID_EVENT recall
ANOMALY recall
VALID_EVENT → ANOMALY error rate
```

Accuracy alone is insufficient.

------------------------------------------------------------------------

# 114. Evaluation Metrics --- C2

For diagnosis:

``` text
macro F1
per-class recall
confusion matrix
```

For recovery:

``` text
recovery success rate
recovery latency
recovered-value error where ground truth exists
recovery confidence calibration
escalation correctness
```

Safety-relevant zone-damage misses should be reported separately.

------------------------------------------------------------------------

# 115. Evaluation Metrics --- C3

Depending on final target formulation:

For binary future-event forecasting:

``` text
ROC-AUC
PR-AUC
precision
recall
F1
Brier score
calibration metrics/plots
```

Operational metrics:

``` text
warning lead time
false alarms per unit time
missed-event rate
```

AUC alone is not enough for an early-warning system.

------------------------------------------------------------------------

# 116. Evaluation Metrics --- C4

For classification:

``` text
macro F1
per-class recall
false acceptance
false rejection
confusion matrix
```

For anomaly detection:

``` text
PR-AUC
ROC-AUC
detection rate
false-positive rate
```

Security evaluation should additionally report performance by
attack/anomaly scenario.

------------------------------------------------------------------------

# 117. Probability Calibration

C1/C2/C3/C4 outputs called "probability" or "confidence" must have
defined semantics.

For C3 especially:

``` text
P(event within H)
```

should be evaluated for calibration.

If calibration methods are applied, they must be fitted without test-set
leakage and versioned with the deployed model pipeline.

------------------------------------------------------------------------

# 118. Threshold Selection

Operational thresholds must be selected using training/validation
evidence and system objectives.

Do not choose a threshold after inspecting final test performance.

Decision Engine thresholds are separate from the underlying model
probability.

------------------------------------------------------------------------

# 119. Baseline Requirement

Every research component must compare against meaningful baselines.

Suggested candidate families:

``` text
C1:
simple/rule baseline
Random Forest
XGBoost/LightGBM
context-enhanced model

C2:
timeout/rule baseline
Random Forest
XGBoost
hybrid backup-verification approach

C3:
persistence/simple threshold baseline
tabular LightGBM/XGBoost
standard GRU/LSTM
time-aware/GRU-D candidate

C4:
deterministic security baseline
simple statistical anomaly baseline
Isolation Forest / boosted-tree candidate
hybrid approach
```

These are candidate experiment directions, not claims that a final
winner has already been selected.

------------------------------------------------------------------------

# 120. Hyperparameter Tuning

Hyperparameter search must use training/validation only.

Possible approaches:

``` text
random search
Bayesian/Optuna-style optimization
limited grid search
```

The exact tool is secondary to maintaining a fair test set and recording
every experiment.

------------------------------------------------------------------------

# 121. Random Seeds

Where algorithms contain randomness, record seeds.

However:

> A fixed seed does not replace robust evaluation.

Important models should ideally be evaluated across multiple seeds where
compute allows, especially neural models.

------------------------------------------------------------------------

# 122. Statistical Comparison

Where practical, compare candidate models using repeated runs,
confidence intervals or appropriate paired/statistical analysis rather
than interpreting tiny metric differences as definitive.

The exact statistical method depends on the metric and dataset
structure.

------------------------------------------------------------------------

# 123. Error Analysis

Each component must produce error-analysis artifacts.

Examples:

``` text
C1 false VALID_EVENT rejection cases
C2 zone damage misclassified as communication failure
C3 missed high-risk events
C3 false alarms
C4 trusted packets falsely quarantined
```

Research contribution is strengthened by explaining failure modes, not
only reporting the best score.

------------------------------------------------------------------------

# 124. Stress-Test Dataset Variants

The dataset system should support controlled stress variants.

Examples:

``` text
long gaps
short gaps
missing sensors
stale readings
packet delay
packet loss
abrupt mode changes
backup unavailable
noisy sensor
suspicious telemetry
```

Stress-test records must be identified as such.

------------------------------------------------------------------------

# 125. C3 Robustness Experiments

Planned C3 stress tests include:

``` text
long gaps
short gaps
missing sensors
abrupt mode changes
stale readings
```

The same base scenarios should be perturbed systematically so results
can be compared.

------------------------------------------------------------------------

# 126. Physical vs Synthetic Evaluation

When sufficient physical data exists, report separately:

``` text
Synthetic evaluation
Physical-demo evaluation
External-data evaluation
```

Do not combine them into one metric without explanation.

This prevents inflated synthetic performance from being mistaken for
field validation.

------------------------------------------------------------------------

# 127. Dataset Quality Levels

A useful internal classification:

``` text
D0 — synthetic development
D1 — controlled simulation
D2 — hardware-in-the-loop
D3 — physical demo
D4 — external/real-world annotated data
```

This is an internal organizational proposal, not a universal scientific
standard.

If adopted, its definitions must remain fixed.

------------------------------------------------------------------------

# 128. Training Dataset vs Integration Fixture

Do not use the full research training dataset as an integration-test
dependency.

Maintain small deterministic fixtures such as:

``` text
tests/fixtures/c1_valid_event.json
tests/fixtures/c2_silence_failure.json
tests/fixtures/c3_window.json
tests/fixtures/c4_replay_packet.json
```

These test contracts, not model quality.

------------------------------------------------------------------------

# 129. Mock Upstream Outputs

During concurrent development:

``` text
mock C4 assessment
mock C1 assessment
mock C2 recovery
```

may be generated.

They must:

-   follow the exact contract;
-   be marked simulated/mock;
-   never be mixed into research evaluation as real upstream
    predictions.

------------------------------------------------------------------------

# 130. Dataset Builder Tests

Each builder requires unit tests for:

``` text
feature calculation
window boundaries
no-future-data rule
label construction
group split integrity
unit conversion
missingness handling
provenance
schema validation
```

C3 should explicitly test overlapping-window split leakage.

------------------------------------------------------------------------

# 131. Example Leakage Test

Conceptual assertion:

``` text
max(train.event_ids ∩ test.event_ids) = empty
```

and:

``` text
for every forecast:
    all runtime features.available_at <= forecast_at
```

Automated checks are preferable to relying only on manual inspection.

------------------------------------------------------------------------

# 132. Data Contract Validation

Use typed schemas where practical.

Potential Python mechanisms:

``` text
Pydantic
Pandera
PyArrow schema
```

The final library will be selected in repository implementation.

The important rule is that invalid datasets fail loudly.

------------------------------------------------------------------------

# 133. Dataset Documentation

Every component dataset directory must contain:

``` text
README.md
```

describing:

``` text
research question
unit of prediction
source data
feature definitions
target definition
provenance
split strategy
known limitations
build command
```

------------------------------------------------------------------------

# 134. Member Responsibilities

Each member owns their component's:

``` text
dataset builder
feature definitions
target construction
validation
split implementation
dataset documentation
```

but must not independently redefine:

``` text
shared IDs
operational database semantics
source-origin taxonomy
cross-component contracts
Golden Timeline semantics
```

------------------------------------------------------------------------

# 135. C1 Developer Must Deliver

At minimum:

``` text
C1 dataset builder
C1 feature schema
label specification
group-aware split
baseline dataset report
rainfall-context ablation
neighbour-context ablation
leakage tests
```

------------------------------------------------------------------------

# 136. C2 Developer Must Deliver

At minimum:

``` text
silence-event dataset builder
failure-diagnosis schema
backup-verification feature stage
recovery-policy dataset/evaluation
episode-aware split
rule baseline
ML baseline
recovery outcome evaluation
```

------------------------------------------------------------------------

# 137. C3 Developer Must Deliver

At minimum:

``` text
Golden Timeline window builder
as-of-time filtering
sequence builder
tabular baseline feature builder
Δt representation
mode representation
missingness representation
C1/C2 provenance integration
event/time-aware split
ablation-ready feature sets
multi-horizon support if retained
```

------------------------------------------------------------------------

# 138. C4 Developer Must Deliver

At minimum:

``` text
packet/behaviour dataset builder
deterministic verification fields
behavioural feature builder
attack/scenario grouping
classification/anomaly baselines
hybrid evaluation
security false-positive/false-negative analysis
```

------------------------------------------------------------------------

# 139. Cross-Team Dataset Freeze

Before an experiment is used in the thesis/paper:

``` text
dataset version frozen
      ↓
manifest generated
      ↓
hash generated
      ↓
split frozen
      ↓
feature schema frozen
      ↓
experiments executed
```

If data changes afterward, create a new dataset version.

------------------------------------------------------------------------

# 140. Data Changes During Development

Allowed:

``` text
C3_TEMPORAL_V001
→ identify generator defect
→ fix builder
→ C3_TEMPORAL_V002
```

Not allowed:

``` text
edit C3_TEMPORAL_V001.csv manually
keep same version
rerun experiment
```

------------------------------------------------------------------------

# 141. Dataset Review Checklist

Before a dataset is approved:

-   [ ] Research question defined
-   [ ] Unit of prediction defined
-   [ ] Target independently defined
-   [ ] Feature roles explicit
-   [ ] Units documented
-   [ ] Provenance documented
-   [ ] Synthetic/physical sources distinguishable
-   [ ] Future-data leakage checked
-   [ ] Group leakage checked
-   [ ] Missingness documented
-   [ ] Split frozen
-   [ ] Manifest generated
-   [ ] Hash generated
-   [ ] Validation report generated
-   [ ] Sample records manually inspected
-   [ ] Baseline can load dataset
-   [ ] Dataset README complete

------------------------------------------------------------------------

# 142. Decisions Frozen by Document 03

The following become GeoNex dataset-baseline decisions:

1.  Each component has a separate research dataset contract.
2.  Datasets are reproducibly generated, not manually maintained
    spreadsheets.
3.  Parquet is the recommended canonical analytical export; CSV may be
    provided for inspection/interoperability.
4.  Every frozen dataset has a manifest and fingerprint.
5.  Every field has an explicit role.
6.  Feature selection is explicit.
7.  Ground truth is separate from predictions.
8.  Source origin is retained.
9.  Group/time/event-aware splitting is required where dependency
    exists.
10. Data-dependent preprocessing is fitted on training data only.
11. C1 uses target observation + environmental/spatial/history context.
12. C2 uses silence/failure episodes and mode-aware expected timing.
13. C2 diagnosis and recovery-action problems remain distinguishable.
14. C3 samples are temporal windows with explicit forecast origins and
    horizons.
15. C3 preserves real timing/Δt and missingness information.
16. C3's existing `risk_probability`, `risk_level` and
    `recommended_mode` require provenance audit before feature use.
17. C4 deterministic security checks and behavioural ML remain separate.
18. Cross-component learned outputs require leakage-safe generation for
    downstream training.
19. Overlapping temporal windows cannot be naively split across
    train/test.
20. Runtime-equivalent evaluation obeys as-of-time availability.
21. Existing synthetic datasets are historical artifacts until
    audited/migrated.
22. Synthetic, physical-demo and external evaluations should be reported
    distinctly.
23. Dataset builders require automated validation and leakage tests.
24. Research-used dataset versions and splits become immutable
    artifacts.

------------------------------------------------------------------------

# 143. Decisions Intentionally Not Frozen Yet

These require component specifications and experiments:

``` text
exact final C1 feature list
exact C1 window lengths
exact C2 silence tolerances
exact C2 failure taxonomy refinements
whether C2 action selection needs ML
exact C3 history-window length
exact C3 forecast horizons
exact C3 final targets
exact C3 tensor representation
exact C3 model architecture
exact C4 behavioural window
exact C4 final attack taxonomy
exact train/validation/test ratios
exact class-balancing method
exact hyperparameter ranges
exact probability thresholds
```

These must be justified experimentally rather than guessed now.

------------------------------------------------------------------------

# 144. Next Documentation Stage

With Documents 00--03, GeoNex now has:

``` text
00 → system development strategy
01 → end-to-end architecture
02 → operational data/database architecture
03 → research dataset architecture
```

The next document should define **mode-conditioned sampling, timing,
silence detection and control mechanics**, because C2 and C3 cannot be
implemented correctly until the timing model is frozen.

It must define:

-   acquisition vs aggregation vs transmission rate;
-   mode profiles;
-   how modes transition;
-   hysteresis;
-   minimum dwell times;
-   emergency/event-triggered sampling;
-   expected-report deadlines;
-   C2 silence tolerances;
-   command/ACK behaviour;
-   fallback when commands are lost;
-   timestamp/clock handling;
-   latency budget;
-   LoRa implications;
-   what is configurable vs experimentally selected.

------------------------------------------------------------------------

# Document 03 Status

**`03_GEONEX_DATASET_ARCHITECTURE.md` --- DATASET ARCHITECTURE BASELINE
READY**

**Next document:**

`04_GEONEX_MODE_SAMPLING_AND_TIMING_SPECIFICATION.md`

That document will freeze the mechanics needed for GeoNex's
variable-rate sensing loop before the individual C1--C4 development
guides and repository implementation are issued.
