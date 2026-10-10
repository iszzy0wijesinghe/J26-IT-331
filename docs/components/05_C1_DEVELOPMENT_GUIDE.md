# 05_C1_DEVELOPMENT_GUIDE.md

**Project:** GeoNex --- Smart Landslide Early Warning Prediction System
using IoT, Edge AI and Risk Analytics\
**Component:** C1 --- Rainfall Regime-Aware Sensor Credibility
Classification\
**Document:** Component Development Guide\
**Status:** Implementation Baseline\
**Depends on:** Documents 00--04\
**Primary purpose:** Provide the C1 researcher/developer with a
complete, research-defensible implementation path while preserving
GeoNex shared architecture and contracts.

------------------------------------------------------------------------

# 1. Component Mission

C1 determines whether an environmental sensor observation should be
treated as credible evidence.

Its central problem is not merely anomaly detection.

A landslide-monitoring system naturally encounters unusual values during
genuine hazardous environmental change. Therefore:

``` text
unusual value ≠ faulty sensor
```

C1 must distinguish, as far as the available evidence permits:

``` text
CLEAN
ANOMALY
VALID_EVENT
```

using the target measurement together with temporal, rainfall,
spatial/neighbour and relevant device context.

------------------------------------------------------------------------

# 2. C1's Place in GeoNex

``` text
Field Device
    ↓
Raw Packet / Observation
    ↓
C4 source/security assessment
    ↓
C1 measurement credibility
    ↓
validated/annotated observation
    ├── normal downstream path
    └── evidence for diagnostics where required
          ↓
Golden Timeline
          ↓
C3 forecasting
```

C1 must never overwrite or delete the original raw observation.

Its output is an assessment attached to that observation.

------------------------------------------------------------------------

# 3. C1 and C4 Are Different

C4 asks:

> Can the source/transmission be trusted?

C1 asks:

> Does this measurement credibly represent the environment?

Example:

``` text
valid registered A1
valid packet/security checks
        ↓
C4 = trusted
        ↓
soil moisture suddenly produces
a physically/contextually inconsistent value
        ↓
C1 may classify ANOMALY
```

Therefore:

``` text
source trust ≠ measurement credibility
```

C1 must not become a duplicate C4 classifier.

------------------------------------------------------------------------

# 4. Research Problem

A conventional anomaly detector may learn that rare/extreme observations
are abnormal.

That is dangerous for environmental early warning because genuine
precursor conditions may be:

``` text
rare
extreme
rapidly changing
```

C1 therefore investigates whether environmental and spatial context can
distinguish:

``` text
sensor abnormality
```

from:

``` text
genuine environmental abnormality
```

more reliably than value-only anomaly detection.

------------------------------------------------------------------------

# 5. Research Question

Recommended principal research question:

> **To what extent can rainfall-regime, temporal and neighbouring-sensor
> context improve sensor-measurement credibility classification while
> reducing the false rejection of genuine environmental events in an IoT
> landslide-monitoring system?**

This wording can later be adapted to faculty/paper style without
changing the technical experiment.

------------------------------------------------------------------------

# 6. Research Hypothesis

A defensible hypothesis is:

> A context-aware credibility classifier using rainfall regime, temporal
> behaviour and neighbouring-sensor consistency will distinguish sensor
> anomalies from genuine environmental events more effectively than
> classifiers using isolated sensor measurements alone.

This must be tested rather than assumed.

------------------------------------------------------------------------

# 7. What Makes C1 Valuable

C1 becomes valuable if it demonstrates that a downstream warning system
should not blindly use either:

``` text
all measurements
```

or:

``` text
simple statistical anomaly rejection
```

Instead it can attach credibility evidence based on multiple independent
contexts.

The strongest C1 contribution is therefore:

``` text
measurement
+
temporal context
+
rainfall regime
+
spatial/neighbour context
        ↓
credibility assessment
```

------------------------------------------------------------------------

# 8. C1 Must Not Claim

Do not claim that C1:

-   proves a sensor is physically broken;
-   predicts a landslide;
-   authenticates devices;
-   diagnoses communication silence;
-   guarantees that every extreme value is valid;
-   replaces calibration;
-   establishes causality between rainfall and landslides.

Those belong to different problems or require stronger evidence.

------------------------------------------------------------------------

# 9. Unit of Prediction

The preferred C1 prediction unit is:

``` text
one target sensor observation
+
only context available at that decision time
```

Conceptually:

``` text
observation O_i at time T
        ↓
construct contextual features available by T
        ↓
predict credibility class for O_i
```

------------------------------------------------------------------------

# 10. Target Classes

Current baseline taxonomy:

``` text
CLEAN
ANOMALY
VALID_EVENT
```

Interpretation:

### CLEAN

Measurement is consistent with expected sensor/environmental behaviour.

### ANOMALY

Evidence indicates that the measurement is likely unreliable, erroneous
or sensor-related abnormality.

### VALID_EVENT

Measurement is unusual/extreme but contextual evidence supports it as a
genuine environmental change/event rather than a sensor anomaly.

These definitions must be converted into a precise labeling
specification before final training.

------------------------------------------------------------------------

# 11. Why VALID_EVENT Is Essential

Without `VALID_EVENT`, a binary system such as:

``` text
NORMAL / ANOMALY
```

may treat genuine hazard-related extremes as anomalies.

The third class explicitly represents the central research challenge.

Therefore evaluation must pay special attention to:

``` text
VALID_EVENT → ANOMALY
```

errors.

------------------------------------------------------------------------

# 12. Labeling Specification Required

Before final experiments, create:

``` text
C1_LABELING_SPECIFICATION.md
```

It must define:

-   exact evidence required for CLEAN;
-   exact anomaly-generation/annotation criteria;
-   exact VALID_EVENT criteria;
-   ambiguous cases;
-   multi-sensor event handling;
-   synthetic-label construction;
-   physical-demo labeling;
-   external-data labeling if used.

No final model result is scientifically stronger than its ground truth.

------------------------------------------------------------------------

# 13. Current Data Asset

Existing C1 work includes:

``` text
C1_Validation.csv
```

with classes:

``` text
CLEAN
ANOMALY
VALID_EVENT
```

This file should be treated as an existing research artifact, not
automatically as the final production training dataset.

Before reuse:

``` text
inspect schema
inspect class balance
identify source
identify how labels were generated
identify leakage fields
identify scenario/event grouping
identify units
create manifest
register dataset version
```

------------------------------------------------------------------------

# 14. Data Sources

C1 may eventually use:

``` text
SYNTHETIC
PHYSICAL_DEMO
EXTERNAL
```

data.

They must remain distinguishable.

Do not combine them into one reported performance metric without
explicit justification.

------------------------------------------------------------------------

# 15. Relevant GeoNex Measurements

Depending on implemented hardware and calibration, C1 may receive
measurements involving:

``` text
soil moisture
FSR response
temperature
humidity
ground/device motion
tilt
vibration
rainfall
```

Not every sensor requires the same credibility model or feature set.

------------------------------------------------------------------------

# 16. Sensor-Family Strategy

Two architectures may be experimentally considered.

## Strategy A --- Shared classifier

``` text
sensor_type
+
sensor-specific normalized/context features
        ↓
one C1 model
```

Advantages: - shared learning; - simpler deployment.

Risks: - heterogeneous sensor physics; - one model may learn sensor
identity shortcuts.

## Strategy B --- Sensor-family classifiers

``` text
soil moisture model
FSR model
motion model
...
```

Advantages: - sensor-specific feature semantics.

Risks: - less data per model; - more deployment complexity.

The final choice must be experimentally justified.

------------------------------------------------------------------------

# 17. Minimum Viable C1 Scope

Do not begin by supporting every sensor.

Start with a sensor family where:

``` text
credible ground truth exists
+
rainfall/neighbour context is meaningful
+
sufficient examples can be generated/collected
```

Soil moisture is a natural initial candidate because rainfall and
spatial consistency have interpretable relationships.

Expand only after the baseline pipeline works.

------------------------------------------------------------------------

# 18. Input Contract

C1 should receive normalized observation/context data, not arbitrary CSV
rows.

Conceptual input:

``` json
{
  "observation_id": "...",
  "zone_id": "Z01",
  "device_id": "Z01-A01",
  "sensor_instance_id": "...",
  "sensor_type": "SOIL_MOISTURE",
  "observed_at": "...",
  "value": 67.4,
  "unit": "%",
  "mode": "RISK"
}
```

Context is constructed by the C1 feature service/builder.

------------------------------------------------------------------------

# 19. C4 Gate

C1 should not treat mandatory C4 failures as ordinary measurement
anomalies.

Conceptually:

``` text
C4 mandatory security failure
        ↓
quarantine/reject according to security policy
```

versus:

``` text
C4 accepted
        ↓
C1 evaluates measurement credibility
```

This preserves component boundaries.

------------------------------------------------------------------------

# 20. C1 Output Contract

Conceptually:

``` json
{
  "observation_id": "...",
  "credibility_class": "VALID_EVENT",
  "credibility_score": 0.94,
  "model_name": "c1_credibility",
  "model_version": "...",
  "generated_at": "...",
  "status": "SUCCESS"
}
```

The exact schema is frozen later in the integration contract.

------------------------------------------------------------------------

# 21. Confidence Semantics

`credibility_score` must have a defined meaning.

Possible interpretation:

``` text
probability assigned to predicted class
```

If probability calibration is poor, do not market raw softmax/tree
probabilities as reliable confidence.

Calibration must be evaluated.

------------------------------------------------------------------------

# 22. Insufficient Context

C1 must support situations such as:

``` text
target observation exists
but
rainfall unavailable
neighbours unavailable
history too short
```

Do not fabricate context.

The model/pipeline should either:

``` text
use explicit missingness handling
```

or return:

``` text
INSUFFICIENT_CONTEXT
```

depending on the selected design.

------------------------------------------------------------------------

# 23. Feature Families

C1 should organize features into explicit families:

``` text
F0 — target measurement
F1 — temporal
F2 — rainfall
F3 — neighbour/spatial
F4 — device-health
F5 — optional operational context
```

This organization enables clean ablation experiments.

------------------------------------------------------------------------

# 24. F0 --- Target Measurement

Candidate features:

``` text
target_value
raw_value where meaningful
sensor_type
```

A value-only model is an important baseline.

------------------------------------------------------------------------

# 25. F1 --- Temporal Context

Candidate features using only past/current data:

``` text
previous_value
delta_from_previous
absolute_delta
time_since_previous_s
rolling_mean
rolling_median
rolling_std
rolling_min
rolling_max
rolling_range
short_term_slope
rate_of_change
```

Window lengths are hyperparameters/design choices and must be
documented.

------------------------------------------------------------------------

# 26. Irregular Timing

If:

``` text
previous = 50
current = 60
```

a change of 10 means something different over:

``` text
10 seconds
```

versus:

``` text
30 minutes
```

Therefore rate features should use actual elapsed time where relevant.

Example:

``` text
rate_of_change
=
(current - previous) / Δt
```

with safe handling of zero/invalid Δt.

------------------------------------------------------------------------

# 27. F2 --- Rainfall Context

Candidate features:

``` text
rain_recent
rainfall_rate
rain_15m_sum
rain_1h_sum
rain_6h_sum
time_since_rain_started
rainfall_regime
```

Only features supported by the calibrated rainfall system or approved
dataset may be used.

------------------------------------------------------------------------

# 28. Rainfall Regime

Rather than using rainfall only as one continuous number, C1 may
investigate a contextual regime representation.

Conceptually:

``` text
DRY
LIGHT
MODERATE
HEAVY
EXTREME
```

These labels are examples only.

The final regime definition must be based on:

``` text
literature/domain evidence
and/or
data-driven defensible thresholds
```

not arbitrary values invented during coding.

------------------------------------------------------------------------

# 29. Alternative Rainfall-Regime Representation

Instead of hard categories, C1 may compare:

``` text
continuous rainfall features
```

against:

``` text
continuous + regime
```

or a learned representation.

This can become part of the research ablation.

------------------------------------------------------------------------

# 30. Why Rainfall Context Can Help

Illustrative reasoning:

``` text
soil moisture jumps strongly
+
heavy recent rainfall
+
nearby soil sensors also rise
        ↓
plausible genuine environmental change
```

versus:

``` text
one soil sensor jumps strongly
+
little/no supporting rainfall
+
neighbours remain stable
        ↓
greater suspicion of sensor anomaly
```

This is a research hypothesis, not a deterministic truth.

C1 must learn/evaluate the relationship rather than hard-code every
case.

------------------------------------------------------------------------

# 31. F3 --- Neighbour Context

Candidate features:

``` text
neighbour_count
neighbour_mean
neighbour_median
neighbour_std
neighbour_min
neighbour_max
target_minus_neighbour_mean
target_z_relative_to_neighbours
neighbour_agreement_fraction
neighbour_trend_mean
```

------------------------------------------------------------------------

# 32. Define "Neighbour"

Neighbour must be configuration-driven.

Potential hierarchy:

``` text
same sensor family
+
same zone
```

and, if justified:

``` text
explicitly configured adjacent zone/device
```

Do not dynamically choose whichever sensor value is most similar to the
target; that would bias the feature.

------------------------------------------------------------------------

# 33. Temporal Alignment of Neighbours

Neighbour values may not occur at exactly the same time.

C1 needs an as-of join policy:

``` text
use most recent eligible neighbour observation
available by target decision time
within maximum staleness tolerance
```

Never use a future neighbour value merely because it is temporally
closest.

------------------------------------------------------------------------

# 34. Neighbour Staleness

Include:

``` text
neighbour_age_s
```

or aggregated staleness information where useful.

A neighbour reading from long ago should not be treated as equivalent to
a fresh one.

------------------------------------------------------------------------

# 35. F4 --- Device Health

Candidate features:

``` text
device_voltage
recent_read_failures
recent_restart
sensor_error_count
power_abnormality
```

These can support sensor-fault inference.

But avoid letting C1 become C2/C4.

Only measurement-relevant health evidence should be included.

------------------------------------------------------------------------

# 36. F5 --- Operational Context

Potential:

``` text
current_mode
```

may affect expected observation patterns.

However mode must pass leakage analysis before becoming a C1 feature.

C1's central research contribution should remain environmental
credibility, not merely learning Decision Engine state.

------------------------------------------------------------------------

# 37. Features C1 Should Generally Not Use

Do not automatically include:

``` text
packet_id
observation_id
device serial number
dataset row number
scenario label
injected_fault flag
ground_truth event flag
future values
C3 risk probability
future operating mode
```

These can create shortcuts/leakage.

------------------------------------------------------------------------

# 38. Device ID Leakage

If all anomalies in synthetic data happen on:

``` text
A1
```

and all clean data on:

``` text
B1
```

then including device ID lets the model memorize:

``` text
A1 = anomaly
```

rather than learning credibility.

Device IDs should normally remain metadata/split keys.

------------------------------------------------------------------------

# 39. Synthetic Fault Generation

Synthetic anomalies should represent plausible sensor/data failures
rather than arbitrary random noise only.

Candidate fault families:

``` text
spike
stuck-at
drift
bias
dropout
out-of-range
excessive noise
quantization/ADC issue
```

Only fault types relevant to the selected sensors should be used.

------------------------------------------------------------------------

# 40. Genuine Event Generation

VALID_EVENT synthetic scenarios should produce coherent environmental
change.

For example:

``` text
rainfall increases
        ↓
soil response evolves
        ↓
multiple nearby sensors respond
```

The generator should preserve plausible temporal/spatial relationships.

Do not create VALID_EVENT simply by assigning the label to random
extreme values.

------------------------------------------------------------------------

# 41. Synthetic Generator Separation

The generator must use hidden scenario truth to create labels.

The model must not receive those hidden generator variables unless they
correspond to real runtime-observable evidence.

Example:

``` text
generator_fault_type
```

may define the label but must not become a feature.

------------------------------------------------------------------------

# 42. Physical Data Collection

Controlled prototype experiments should record:

``` text
known normal condition
controlled sensor disturbance/fault
controlled environmental changes where safe
rainfall mechanism response
neighbour sensor responses
timestamps
experiment/test-run ID
```

This provides physical-demo evidence separate from synthetic evaluation.

------------------------------------------------------------------------

# 43. Calibration Before C1

C1 must not be forced to learn avoidable calibration errors.

Pipeline:

``` text
raw sensor response
        ↓
calibration
        ↓
engineering value
        ↓
C1 credibility
```

Calibration version should remain traceable.

------------------------------------------------------------------------

# 44. FSR Caution

For FSR402:

``` text
raw ADC / voltage / resistance-derived response
```

is valid before force calibration.

Do not create a C1 feature named:

``` text
ground_pressure_kpa
```

unless calibration and effective contact-area assumptions justify it.

------------------------------------------------------------------------

# 45. Dataset Builder

Recommended code responsibility:

``` text
components/
└── c1_credibility/
    └── datasets/
        ├── build.py
        ├── features.py
        ├── labels.py
        ├── neighbours.py
        ├── rainfall.py
        ├── splits.py
        ├── validate.py
        └── schemas.py
```

Shared utilities remain in shared modules.

------------------------------------------------------------------------

# 46. Dataset Build Flow

``` text
approved source records
        ↓
eligible target observations
        ↓
as-of temporal context
        ↓
as-of rainfall context
        ↓
as-of neighbour context
        ↓
device-health context
        ↓
attach independent label
        ↓
leakage validation
        ↓
group-aware split
        ↓
export + manifest
```

------------------------------------------------------------------------

# 47. Dataset Schema

A baseline C1 analytical record can contain:

``` text
record_id
observation_id
zone_id
device_id
sensor_instance_id
sensor_type
observed_at
source_origin

target_value
previous_value
delta_from_previous
time_since_previous_s

rolling_mean
rolling_std
rolling_min
rolling_max
short_term_slope

rain_15m_sum
rain_1h_sum
rain_6h_sum
rainfall_regime

neighbour_count
neighbour_mean
neighbour_std
target_minus_neighbour_mean
neighbour_agreement_fraction
neighbour_age_s

device_voltage
recent_read_failures

credibility_label
```

Not every field is guaranteed to remain in the final feature set.

------------------------------------------------------------------------

# 48. Dataset Manifest

Example:

``` yaml
dataset_code: C1_CREDIBILITY
version: 1
schema_version: 1
source_types:
  - SYNTHETIC
builder_version: <generated>
label_schema_version: 1
split_strategy: scenario_grouped
random_seed: 42
row_count: <generated>
file_hash: <generated>
```

Actual values must be generated from the build.

------------------------------------------------------------------------

# 49. Split Strategy

Do not randomly split correlated rows from one scenario across
train/test.

Preferred:

``` text
scenario/event grouped split
```

with temporal/device holdout experiments where data permits.

------------------------------------------------------------------------

# 50. Why Grouping Matters

Suppose one synthetic rainfall event generates 1,000 highly similar
rows.

A random row split may put:

``` text
800 in training
200 in testing
```

The model then sees nearly the same event in both sets.

Reported performance becomes overly optimistic.

Keep the entire event/scenario together.

------------------------------------------------------------------------

# 51. Device Holdout

A useful robustness experiment:

``` text
train on selected devices
test on another compatible device
```

where enough devices/data exist.

This tests whether the model learned sensor behaviour rather than device
identity.

With a small prototype, claims must remain conservative.

------------------------------------------------------------------------

# 52. Temporal Holdout

Another experiment:

``` text
earlier scenarios → training
later scenarios → testing
```

This better resembles deployment than random row splitting.

------------------------------------------------------------------------

# 53. Baseline 0 --- Simple Plausibility Rules

Implement a deterministic baseline such as:

``` text
physical range
rate-of-change limit
simple deviation threshold
```

This answers:

> Does ML actually outperform basic engineering checks?

------------------------------------------------------------------------

# 54. Baseline 1 --- Value-Only Classifier

Features:

``` text
target_value
```

possibly plus sensor type for a shared model.

This provides the weakest ML baseline.

------------------------------------------------------------------------

# 55. Baseline 2 --- Temporal Classifier

Features:

``` text
target
+
history
```

This tests whether past behaviour helps.

------------------------------------------------------------------------

# 56. Baseline 3 --- Random Forest

Random Forest is a useful baseline because it:

-   handles nonlinear tabular relationships;
-   requires relatively little preprocessing;
-   provides a strong classical comparison;
-   can expose feature importance.

It should not automatically be the final model.

------------------------------------------------------------------------

# 57. Candidate --- XGBoost

XGBoost is a strong candidate for structured/tabular contextual data.

Advantages:

-   nonlinear interactions;
-   robust tabular performance;
-   missing-value handling capabilities;
-   interpretable feature contribution tools.

Its inclusion must be justified by experiment.

------------------------------------------------------------------------

# 58. Candidate --- LightGBM

LightGBM is another strong boosted-tree candidate.

Advantages:

-   efficient training;
-   strong tabular performance;
-   supports complex interactions.

There is no need to use both XGBoost and LightGBM in production.

They may be compared during research and one selected.

------------------------------------------------------------------------

# 59. Why Deep Learning Is Not Automatically Required

C1's feature representation may be predominantly tabular/contextual.

A neural network is not automatically superior.

If tree models provide equal/better:

``` text
performance
calibration
interpretability
runtime simplicity
```

they may be more appropriate.

Research quality comes from the question and evidence, not model
complexity.

------------------------------------------------------------------------

# 60. Optional Temporal Model Extension

If sufficient sequential data exists, an optional sequence model may be
investigated.

However this should be secondary unless it clearly contributes beyond
engineered temporal features.

C3 remains the main temporal forecasting component.

C1 should not expand until it duplicates C3.

------------------------------------------------------------------------

# 61. Proposed Research Approach

A strong proposed C1 can be defined as:

``` text
Context-Aware Credibility Classification
        =
target measurement
+
temporal consistency
+
rainfall regime
+
neighbour consistency
+
selected health context
```

implemented using the experimentally strongest appropriate classifier.

The novelty/value lies primarily in **contextual credibility
reasoning**, not the brand name of the classifier.

------------------------------------------------------------------------

# 62. Core Ablation

Use one frozen test split.

``` text
A0 — Target value only
A1 — + temporal context
A2 — + neighbour context
A3 — + rainfall continuous features
A4 — + rainfall regime
A5 — + selected device-health context
```

This reveals where performance improvements actually come from.

------------------------------------------------------------------------

# 63. Alternative Ablation Order

Because the primary research claim emphasizes rainfall and neighbours,
also report:

``` text
Full model
minus rainfall
minus neighbours
minus temporal
```

This tests the necessity of each context family.

------------------------------------------------------------------------

# 64. Critical C1 Metric

A headline metric should include:

``` text
VALID_EVENT incorrectly classified as ANOMALY
```

because this error can suppress genuine environmental evidence.

Also report:

``` text
ANOMALY incorrectly classified as VALID_EVENT
```

because accepting bad sensor data is also dangerous.

The system has asymmetric costs.

------------------------------------------------------------------------

# 65. Evaluation Metrics

At minimum:

``` text
macro precision
macro recall
macro F1
per-class precision
per-class recall
per-class F1
confusion matrix
balanced accuracy where useful
```

Accuracy alone is not sufficient.

------------------------------------------------------------------------

# 66. PR Curves / One-vs-Rest

For imbalanced classes, one-vs-rest precision-recall analysis can
provide useful evidence, especially for:

``` text
ANOMALY
VALID_EVENT
```

where probability outputs are available.

------------------------------------------------------------------------

# 67. Probability Calibration

If C1 sends probabilities/confidence downstream, evaluate:

``` text
reliability/calibration plot
Brier-style probability quality where applicable
ECE or another documented calibration metric
```

If calibration is poor, investigate:

``` text
Platt/sigmoid calibration
isotonic calibration
```

using validation data only.

------------------------------------------------------------------------

# 68. Cost-Sensitive Evaluation

Because error costs differ, consider a cost matrix for analysis.

Example concept:

``` text
VALID_EVENT → ANOMALY = high concern
ANOMALY → VALID_EVENT = high concern
CLEAN ↔ nearby class = lower/different concern
```

Do not invent monetary costs.

Use qualitative or normalized research weights unless defensible costs
exist.

------------------------------------------------------------------------

# 69. Class Imbalance

Handle imbalance only after group-aware splitting.

Candidate training approaches:

``` text
class weights
balanced sampling
careful oversampling
```

SMOTE may be tested for tabular features but must not create unrealistic
context combinations.

Always compare against unmodified data.

------------------------------------------------------------------------

# 70. Hyperparameter Tuning

Use validation data only.

Record:

``` text
algorithm
search space
best parameters
seed
validation metric
runtime
```

Do not tune on the final test set.

------------------------------------------------------------------------

# 71. Model Selection Criterion

Do not simply select the model with highest accuracy.

Selection should consider:

``` text
macro F1
critical per-class recall
calibration
robustness
inference latency
complexity
interpretability
```

A slightly lower aggregate score may be preferable if it protects
VALID_EVENT substantially better.

------------------------------------------------------------------------

# 72. Explainability

Tree-based C1 models should support explainability analysis.

Possible tools:

``` text
feature importance
permutation importance
SHAP
```

The objective is to investigate whether the model is using
scientifically plausible contextual signals.

------------------------------------------------------------------------

# 73. Explainability Is Not Proof of Causality

A high SHAP value for rainfall means:

``` text
the model relied on rainfall for that prediction
```

not:

``` text
rainfall scientifically caused the event
```

Keep this distinction in the thesis.

------------------------------------------------------------------------

# 74. Global Explanation

Report which feature families matter across the test data.

Example questions:

``` text
Does rainfall context materially contribute?
Do neighbour features dominate?
Does the model rely excessively on target value?
```

------------------------------------------------------------------------

# 75. Local Explanation

Inspect representative:

``` text
CLEAN
ANOMALY
VALID_EVENT
```

predictions.

For a VALID_EVENT example, demonstrate whether:

``` text
rainfall
neighbour agreement
temporal trend
```

supported the decision.

------------------------------------------------------------------------

# 76. Failure Analysis

Create categorized error cases:

``` text
isolated spike accepted
valid event rejected
slow drift missed
neighbour disagreement misread
rainfall context misleading
insufficient neighbour coverage
stale context
```

This should become part of the research results.

------------------------------------------------------------------------

# 77. Stress Tests

C1 should be tested under:

``` text
missing rainfall
missing neighbour
stale neighbour
sensor drift
single spike
sustained bias
rapid genuine environmental change
extreme rainfall
mode transition
irregular timing
```

The goal is to characterize degradation.

------------------------------------------------------------------------

# 78. Missing Context Experiment

Compare:

``` text
full context
vs
one neighbour unavailable
vs
all neighbours unavailable
vs
rainfall unavailable
```

This is operationally important because C1 itself must tolerate
imperfect monitoring.

------------------------------------------------------------------------

# 79. Noise Robustness

Inject controlled additional sensor noise into test copies.

Do not retrain on the test perturbation unless explicitly running a
separate robustness-training experiment.

Measure degradation.

------------------------------------------------------------------------

# 80. Drift Robustness

Simulate gradual bias/drift.

This is important because slow sensor degradation can be harder to
detect than isolated spikes.

------------------------------------------------------------------------

# 81. Genuine Extreme Test

Construct/identify examples where:

``` text
target is extreme
+
environmental context supports it
```

C1 should preserve these better than a simple outlier detector.

This is one of the strongest demonstrations of C1's value.

------------------------------------------------------------------------

# 82. Neighbour Failure Test

If several neighbouring sensors fail together, neighbour agreement can
become misleading.

Test:

``` text
one faulty sensor
multiple correlated faulty sensors
```

and document limitations.

C1 should not claim that neighbour agreement guarantees correctness.

------------------------------------------------------------------------

# 83. Rainfall Sensor Failure

Rainfall itself can be wrong.

Therefore C1 should not assume rainfall context is infallible.

The integrated system can use credibility/health mechanisms for hub
measurements as well.

Stress-test incorrect/missing rainfall context where feasible.

------------------------------------------------------------------------

# 84. Training Pipeline

Recommended:

``` text
load frozen dataset
        ↓
validate schema
        ↓
load frozen split
        ↓
select feature schema
        ↓
fit preprocessing on TRAIN
        ↓
train model
        ↓
evaluate VALIDATION
        ↓
tune/select
        ↓
optional calibration
        ↓
freeze candidate
        ↓
evaluate TEST once
        ↓
save artifact + metadata
```

------------------------------------------------------------------------

# 85. Model Artifact

Saved artifact should include or reference:

``` text
model
preprocessing pipeline
feature schema version
label mapping
calibration object if used
model metadata
training dataset version
```

Avoid saving only:

``` text
model.pkl
```

without context.

------------------------------------------------------------------------

# 86. Model Metadata

Example:

``` yaml
model_name: c1_credibility
model_version: 1
algorithm: <selected after experiment>
dataset_version: C1_CREDIBILITY_V001
feature_schema: C1_FEATURES_A4_V001
label_schema: C1_LABELS_V001
trained_at: <generated>
git_commit: <generated where practical>
```

------------------------------------------------------------------------

# 87. Inference Pipeline

Runtime:

``` text
new accepted observation
        ↓
retrieve as-of context
        ↓
construct same feature schema
        ↓
validate
        ↓
load approved C1 model
        ↓
predict
        ↓
optional probability calibration
        ↓
store C1 result
        ↓
forward credibility metadata
```

Training and runtime feature engineering must use the same
implementation where practical.

------------------------------------------------------------------------

# 88. Train/Serve Skew

A major risk is:

``` text
training features calculated one way
runtime features calculated another way
```

Avoid duplicated feature logic.

Prefer shared functions used by both:

``` text
offline builder
online inference
```

with explicit as-of behaviour.

------------------------------------------------------------------------

# 89. Runtime As-Of Rule

For target observation at time `T`, context must obey runtime
availability.

No feature may use evidence that had not arrived/been processed by the
C1 decision time.

This matters especially for delayed LoRa packets.

------------------------------------------------------------------------

# 90. Inference Status

Possible statuses:

``` text
SUCCESS
INSUFFICIENT_CONTEXT
MODEL_UNAVAILABLE
INVALID_INPUT
SECURITY_REJECTED_UPSTREAM
```

Exact enums will be frozen in integration contracts.

------------------------------------------------------------------------

# 91. Database Interaction

C1 should conceptually:

``` text
READ
normalized observations
eligible rainfall context
eligible neighbour context
device-health context

WRITE
c1 credibility result
model/version metadata
processing timestamp
```

It must not modify raw telemetry.

------------------------------------------------------------------------

# 92. Golden Timeline Interaction

C1 does not directly erase an anomalous observation.

Its result becomes one input to the Golden Timeline policy.

Conceptually:

``` text
raw observation = preserved
C1 assessment = ANOMALY
        ↓
Golden Timeline builder decides
how the observation is represented/eligible
according to shared policy
```

------------------------------------------------------------------------

# 93. C2 Interaction

C1 should not diagnose silence.

However its recent results can provide context to C2.

Example:

``` text
sensor produces repeated anomalies
then becomes silent
```

may be useful diagnostic history.

The exact cross-component fields will be defined in the integration
contract.

------------------------------------------------------------------------

# 94. C3 Interaction

C3 may use C1 outputs in the planned `+C1` ablation.

Possible representations:

``` text
credibility class
credibility probability
fraction anomalous in window
fraction valid-event in window
```

But C3 training must use leakage-safe upstream predictions.

------------------------------------------------------------------------

# 95. Out-of-Fold C1 Predictions for C3

When C1 outputs become C3 training features:

``` text
do not
train C1 on row/event
then feed its in-sample prediction
to C3 as though it were runtime evidence
```

Use:

``` text
out-of-fold predictions
```

or an upstream model trained without those samples.

This keeps the integrated experiment honest.

------------------------------------------------------------------------

# 96. Runtime Performance

Measure:

``` text
feature-construction latency
model inference latency
total C1 latency
memory usage where relevant
```

C1 should be lightweight enough not to become a major warning-pipeline
bottleneck.

------------------------------------------------------------------------

# 97. Edge vs Main Computer

Initial recommended deployment:

``` text
sensor acquisition/calibration → ESP32
C1 model inference → Main Computing System
```

because the main computer provides easier:

``` text
context retrieval
model management
database access
experimentation
```

A later edge deployment can be evaluated if research requires it.

Do not force model inference onto ESP32 merely to call the system "Edge
AI."

------------------------------------------------------------------------

# 98. Edge-AI Interpretation

GeoNex can legitimately contain edge processing through:

``` text
sensor acquisition
local filtering/aggregation
event triggers
local health checks
gateway processing
```

while heavier ML runs on the local Main Computing System.

Deployment terminology should accurately describe where inference
actually occurs.

------------------------------------------------------------------------

# 99. C1 Service Boundary

Recommended runtime abstraction:

``` text
C1CredibilityService
```

with conceptual method:

``` text
assess(observation_id)
    → CredibilityAssessment
```

The service handles feature construction and approved-model inference.

------------------------------------------------------------------------

# 100. Suggested Code Structure

``` text
components/
└── c1_credibility/
    ├── README.md
    ├── configs/
    ├── datasets/
    ├── features/
    ├── models/
    ├── training/
    ├── evaluation/
    ├── inference/
    ├── service/
    └── tests/
```

Exact repository naming will be reconciled with the final monorepo
specification.

------------------------------------------------------------------------

# 101. Configuration

Do not hard-code:

``` text
window length
neighbour tolerance
rainfall regime thresholds
model path
confidence threshold
```

inside model code.

Use versioned configuration.

------------------------------------------------------------------------

# 102. Example Experiment Config

``` yaml
experiment_id: c1_a4_xgb_001

dataset:
  version: C1_CREDIBILITY_V001

features:
  schema: C1_FEATURES_A4_V001

model:
  family: xgboost

split:
  manifest: C1_SPLIT_V001

seed: 42
```

Actual hyperparameters are recorded after experiment design.

------------------------------------------------------------------------

# 103. Experiment Registry

Every run should record:

``` text
experiment_id
dataset
feature schema
algorithm
hyperparameters
seed
metrics
artifact path
git version
notes
```

------------------------------------------------------------------------

# 104. Reproducibility Command

Eventually:

``` bash
python -m components.c1_credibility.training.train \
  --config components/c1_credibility/configs/experiments/c1_a4_xgb_001.yaml
```

should reproduce an experiment from frozen inputs.

Exact CLI implementation may change, but reproducibility must not.

------------------------------------------------------------------------

# 105. Unit Tests

Required examples:

``` text
rolling features use only past/current data
rate-of-change uses actual Δt
neighbour join never uses future observation
rainfall window boundaries correct
missing neighbour handled
invalid unit rejected
label mapping valid
```

------------------------------------------------------------------------

# 106. Dataset Leakage Tests

Automated assertions should verify:

``` text
scenario groups do not cross splits
future context not used
target/hidden generator fields excluded
test preprocessing statistics not used
```

------------------------------------------------------------------------

# 107. Model Tests

Test:

``` text
model loads
feature schema matches
prediction class valid
probabilities finite
probabilities sum appropriately
missing allowed fields handled
unknown category policy works
```

------------------------------------------------------------------------

# 108. Service Tests

Test:

``` text
valid observation → result
missing observation → error/status
C4 rejected packet → not ordinarily scored
model unavailable → degraded response
database failure → handled
```

------------------------------------------------------------------------

# 109. Contract Tests

C1 output must validate against the shared GeoNex contract.

A C1 developer cannot silently add or rename fields consumed by
C3/Golden Timeline.

------------------------------------------------------------------------

# 110. Integration Test

Minimum integration scenario:

``` text
raw packet
→ C4 accepted
→ observation normalized
→ C1 feature context constructed
→ C1 prediction
→ result stored
→ Golden Timeline receives credibility metadata
```

------------------------------------------------------------------------

# 111. Hardware Test

Using actual prototype sensors:

``` text
collect normal readings
introduce controlled sensor disturbance
produce controlled environmental change where feasible
observe neighbour/rainfall context
run C1
compare with known experiment condition
```

Record the experiment protocol.

------------------------------------------------------------------------

# 112. Research Tables Required

Final C1 results should include tables such as:

### Model comparison

``` text
Rule baseline
Random Forest
XGBoost
LightGBM
Selected model
```

### Context ablation

``` text
Target
+ Temporal
+ Neighbour
+ Rainfall
+ Rainfall Regime
+ Health
```

### Class performance

``` text
CLEAN
ANOMALY
VALID_EVENT
```

------------------------------------------------------------------------

# 113. Research Figures Required

Useful figures:

``` text
confusion matrix
feature-family ablation chart
precision-recall curves
calibration plot
feature importance/SHAP summary
representative event timeline
```

Do not create decorative plots with no research question.

------------------------------------------------------------------------

# 114. Representative Timeline Figure

A particularly valuable figure can show:

``` text
rainfall
soil moisture target
neighbour moisture
C1 predicted class
ground truth
```

across one event.

This visually demonstrates why context matters.

------------------------------------------------------------------------

# 115. Statistical Evidence

Where feasible, report uncertainty across:

``` text
multiple scenarios
multiple seeds
or appropriate resampling
```

Do not interpret a tiny difference such as 0.1% as meaningful without
uncertainty analysis.

------------------------------------------------------------------------

# 116. Research Success Criteria

C1 should be considered scientifically successful if evidence supports
at least one defensible contribution such as:

``` text
rainfall regime improves VALID_EVENT protection
neighbour context improves anomaly discrimination
combined context improves macro-F1
context improves robustness under extreme values
```

while limitations are honestly reported.

The result need not prove every proposed feature is useful.

------------------------------------------------------------------------

# 117. Negative Results Are Valid

If:

``` text
rainfall regime adds no measurable benefit
```

that should not be hidden.

Investigate:

``` text
poor regime definition?
insufficient data?
continuous rainfall already captures it?
sensor target not rainfall-sensitive?
```

Research value comes from a correct experiment, not forcing the
hypothesis to win.

------------------------------------------------------------------------

# 118. Strongest C1 Thesis Narrative

A strong narrative is:

``` text
Traditional outlier logic can reject rare but valid
environmental changes.

GeoNex C1 therefore evaluates measurement credibility
using environmental and spatial context.

Experiments progressively add temporal, neighbour and
rainfall-regime evidence and measure whether genuine
events are protected while sensor anomalies remain
detectable.
```

------------------------------------------------------------------------

# 119. Paper Contribution Statement

A cautious candidate contribution statement:

> A context-aware sensor credibility framework for IoT landslide
> monitoring that incorporates rainfall regime, temporal behaviour and
> neighbouring-sensor consistency to distinguish sensor anomalies from
> genuine unusual environmental events.

Use final wording only after experiments support it.

------------------------------------------------------------------------

# 120. Limitations to Report

Potential limitations:

``` text
limited physical deployment scale
synthetic-data dependence
only two prototype zones
sensor calibration uncertainty
limited fault types
neighbour correlation assumptions
rainfall mechanism calibration
domain transfer to other terrain
```

Reporting limitations strengthens scientific credibility.

------------------------------------------------------------------------

# 121. Do Not Optimize for "95% Accuracy"

A model with:

``` text
95% accuracy
```

can still fail badly if the minority VALID_EVENT class is consistently
rejected.

C1 optimization/evaluation must reflect the actual research problem.

------------------------------------------------------------------------

# 122. Avoid Dataset Shortcuts

Before trusting high performance, deliberately check:

``` text
Does timestamp reveal scenario?
Does device ID reveal label?
Does rainfall regime directly encode synthetic label?
Does a generator column reveal fault type?
Are duplicate rows crossing splits?
```

Unexpectedly near-perfect performance should trigger investigation.

------------------------------------------------------------------------

# 123. C1 Definition of Done --- Data

-   [ ] Existing C1 dataset audited
-   [ ] Label specification documented
-   [ ] Canonical builder implemented
-   [ ] Feature schema versioned
-   [ ] Group-aware split frozen
-   [ ] Dataset manifest generated
-   [ ] Leakage tests passing
-   [ ] Synthetic/physical origin traceable

------------------------------------------------------------------------

# 124. C1 Definition of Done --- Modeling

-   [ ] Rule baseline implemented
-   [ ] Value-only baseline implemented
-   [ ] Random Forest baseline evaluated
-   [ ] Boosted-tree candidates evaluated
-   [ ] Proposed contextual model evaluated
-   [ ] Hyperparameters recorded
-   [ ] Calibration evaluated
-   [ ] Final model selected using documented criteria

------------------------------------------------------------------------

# 125. C1 Definition of Done --- Research

-   [ ] Temporal ablation completed
-   [ ] Neighbour ablation completed
-   [ ] Rainfall-context ablation completed
-   [ ] Rainfall-regime contribution tested
-   [ ] Critical class errors analyzed
-   [ ] Stress tests completed
-   [ ] Physical-demo evaluation separated
-   [ ] Limitations documented
-   [ ] Tables/figures generated reproducibly

------------------------------------------------------------------------

# 126. C1 Definition of Done --- Integration

-   [ ] Runtime inference service implemented
-   [ ] Shared input contract validated
-   [ ] Shared output contract validated
-   [ ] Database read/write path implemented
-   [ ] C4 gate respected
-   [ ] Golden Timeline integration tested
-   [ ] C3 mock/real integration fixture available
-   [ ] Model/version provenance stored
-   [ ] Failure/degraded states handled

------------------------------------------------------------------------

# 127. Rules for the C1 Member's AI Assistant

The C1 developer may paste this document into their own AI development
chat.

That assistant must follow:

> **Do not redesign the GeoNex shared architecture, operational database
> semantics, identifiers, operating modes, Golden Timeline concept, or
> cross-component contracts. Implement C1 within Documents 00--05. If a
> shared contract appears insufficient, identify the issue and propose a
> versioned change for team review rather than silently modifying it.**

The AI assistant must also:

-   distinguish proposed from finalized algorithms;
-   never invent physical sensor data;
-   preserve synthetic/physical provenance;
-   prevent temporal leakage;
-   provide reproducible code;
-   explain why each modeling choice is made;
-   keep C1 distinct from C2/C3/C4.

------------------------------------------------------------------------

# 128. Recommended C1 Implementation Order

``` text
1. Audit C1_Validation.csv
2. Write label specification
3. Freeze initial sensor-family scope
4. Implement canonical dataset builder
5. Implement leakage-safe split
6. Implement rule baseline
7. Implement value-only ML baseline
8. Add temporal context
9. Add neighbour context
10. Add rainfall context
11. Define/test rainfall regime
12. Compare RF/XGBoost/LightGBM
13. Run ablations
14. Run stress tests
15. Perform calibration/error analysis
16. Freeze approved model
17. Build runtime inference service
18. Integrate database
19. Integrate C4/Golden Timeline
20. Run hardware/integration evaluation
21. Generate thesis/paper evidence
```

Do not begin with the final advanced model.

------------------------------------------------------------------------

# 129. First Coding Milestone

The first implementation milestone should produce:

``` text
C1_Validation.csv audit report
+
C1_LABELING_SPECIFICATION.md
+
canonical schema
+
dataset builder
+
frozen split
+
rule/value-only baseline
```

Only after this foundation should model optimization begin.

------------------------------------------------------------------------

# 130. Component Success in One Sentence

> **C1 succeeds when GeoNex can demonstrate, with reproducible evidence,
> that contextual environmental reasoning helps distinguish unreliable
> sensor measurements from genuine unusual conditions without treating
> every extreme observation as a fault.**

------------------------------------------------------------------------

# 131. Decisions Frozen by Document 05

1.  C1 is measurement-credibility classification, not source
    authentication.
2.  `CLEAN`, `ANOMALY`, and `VALID_EVENT` form the baseline target
    taxonomy.
3.  The target unit is a sensor observation with as-of contextual
    evidence.
4.  Raw observations remain immutable.
5.  C4 mandatory security policy is respected upstream.
6.  Feature families are explicitly separated into target, temporal,
    rainfall, neighbour, health and optional operational context.
7.  Neighbour context uses configured relationships and past/current
    as-of joins only.
8.  Rainfall regime is a research feature requiring justified
    definition.
9.  C1's central value is protecting genuine unusual environmental
    evidence while detecting measurement anomalies.
10. Rule and value-only baselines are mandatory.
11. Random Forest and boosted trees are candidate models, not
    predetermined winners.
12. Deep learning is not required unless experiments justify it.
13. Group-aware splitting is mandatory where scenarios/events create
    correlated rows.
14. `VALID_EVENT → ANOMALY` is a critical error that must be reported.
15. Context-family ablation is mandatory.
16. Missing/stale context robustness must be evaluated.
17. Confidence/probability calibration must be evaluated if
    probabilities are consumed downstream.
18. Runtime and training feature logic should be shared where practical.
19. C3 use of learned C1 outputs requires leakage-safe upstream
    predictions.
20. Final research claims must distinguish synthetic, physical-demo and
    external evidence.

------------------------------------------------------------------------

# 132. Decisions Intentionally Deferred

The following remain experimental:

``` text
final sensor-family scope
exact rolling-window durations
exact neighbour staleness tolerance
exact rainfall-regime thresholds/algorithm
final feature subset
final classifier
final hyperparameters
class-weighting strategy
probability calibration method
operational credibility thresholds
whether separate sensor-family models outperform one shared model
```

They will be frozen only after evidence is available.

------------------------------------------------------------------------

# 133. Next Component Guide

The next document is:

``` text
06_C2_DEVELOPMENT_GUIDE.md
```

It must define in comparable depth:

``` text
mode-aware silence detection
failure-episode construction
communication vs hardware vs zone diagnosis
Backup Pipe verification
SD replay
neighbour fusion
backup-hub handling
recovery provenance
rule baseline
ML diagnostic baseline
recovery policy
outcome evaluation
failure injection
hardware experiments
integration with C1/C3/C4
```

------------------------------------------------------------------------

# Document 05 Status

**`05_C1_DEVELOPMENT_GUIDE.md` --- C1 IMPLEMENTATION BASELINE READY**

This guide deliberately makes C1's research contribution depend on
**demonstrated contextual value**, not merely on obtaining a high
classifier accuracy or choosing a sophisticated algorithm.
