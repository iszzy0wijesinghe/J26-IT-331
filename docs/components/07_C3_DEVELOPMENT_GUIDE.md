# 07_C3_DEVELOPMENT_GUIDE.md

**Project:** GeoNex --- Smart Landslide Early Warning Prediction System
using IoT, Edge AI and Risk Analytics\
**Component:** C3 --- Mode-Conditioned Variable-Rate Multi-Sensor
Temporal Forecasting\
**Document:** Component Development Guide\
**Status:** Implementation Baseline\
**Depends on:** Documents 00--06\
**Primary purpose:** Define a complete, research-defensible path for
developing, training, validating, integrating, and evaluating C3 without
data leakage, circular reasoning, or loss of the variable-rate temporal
information that makes the component valuable.

------------------------------------------------------------------------

# 1. Component Mission

C3 answers:

> **Given the trustworthy information available up to the present time,
> what is the probability of a dangerous landslide-related condition
> occurring within a future prediction horizon?**

C3 is not a current-state threshold detector.

It is a **future-risk forecasting component**.

Its central challenge is that GeoNex deliberately changes
sensing/reporting behaviour according to operating mode:

``` text
DEEP_SLEEP → IDLE → RISK → WARNING → EMERGENCY
```

Therefore the temporal sequence is not naturally fixed-rate.

C3 must reason about:

``` text
multivariate sensor history
+
actual elapsed time Δt
+
operating-mode context
+
missingness
+
C1 credibility
+
C2 recovery provenance
```

while predicting future risk.

------------------------------------------------------------------------

# 2. C3's Place in GeoNex

``` text
Raw telemetry
    ↓
C4 source/security assessment
    ↓
C1 measurement credibility
    ↓
C2 recovery where required
    ↓
Golden Timeline
    ↓
C3 temporal feature/sequence builder
    ↓
C3 forecasting model
    ↓
future risk probability
    ↓
Decision Engine
    ↓
mode / sampling / warning / alert decisions
```

C3 consumes the validated temporal evidence.

It does **not** directly control sensor firmware.

------------------------------------------------------------------------

# 3. C3 and the Decision Engine Are Different

C3 predicts:

``` text
future risk
```

The Decision Engine decides:

``` text
what GeoNex should do about that risk
```

Therefore:

``` text
C3 output
    ≠
system mode command
```

Correct boundary:

``` text
C3
→ risk probability / forecast evidence
→ Decision Engine
→ mode / sampling / alerts
```

This separation prevents policy logic from becoming hidden inside the
predictor.

------------------------------------------------------------------------

# 4. Research Problem

Many temporal prediction systems assume observations arrive at
approximately regular intervals.

GeoNex intentionally violates that assumption because monitoring
frequency changes with operating mode.

A sequence such as:

``` text
10:00
10:10
10:20
10:21
10:22
```

cannot safely be interpreted as five equally spaced observations.

C3 therefore investigates whether explicit temporal-gap and mode context
improve forecasting under adaptive variable-rate sensing.

------------------------------------------------------------------------

# 5. Principal Research Question

Recommended:

> **To what extent can mode-conditioned, time-aware multivariate
> temporal modeling improve near-future landslide-risk forecasting under
> variable-rate IoT sensing, particularly when measurement credibility
> and recovery provenance are incorporated into the temporal
> representation?**

This wording may later be adapted for the final paper/thesis.

------------------------------------------------------------------------

# 6. Research Hypothesis

A defensible hypothesis:

> **A temporal model that explicitly represents elapsed time, operating
> mode, measurement quality and recovery provenance will produce more
> reliable future-risk forecasts under variable-rate sensing than models
> that treat observations as uniformly sampled and equally
> trustworthy.**

This must be tested experimentally.

------------------------------------------------------------------------

# 7. What Makes C3 Valuable

C3 should not be presented as:

``` text
"We used GRU for landslide prediction."
```

That is too weak.

The stronger contribution is:

``` text
VARIABLE-RATE MULTI-SENSOR HISTORY
        +
EXPLICIT Δt
        +
MODE CONTEXT
        +
CREDIBILITY
        +
RECOVERY/MISSINGNESS PROVENANCE
        ↓
FUTURE-RISK FORECAST
```

and then proving which parts improve forecasting.

------------------------------------------------------------------------

# 8. C3 Must Not Claim

Do not claim that C3:

-   confirms that a landslide will occur;
-   directly diagnoses failed sensors;
-   authenticates telemetry;
-   controls operating mode by itself;
-   eliminates uncertainty;
-   proves that every high-risk forecast is a future landslide;
-   self-modifies continuously in production without validation.

C3 produces probabilistic predictive evidence.

------------------------------------------------------------------------

# 9. Forecasting Time

Define:

``` text
t = forecast origin
```

At `t`, C3 may use only evidence available by that time.

It predicts an event occurring after `t`.

This is the fundamental anti-leakage boundary.

------------------------------------------------------------------------

# 10. Forecast Horizon

Let:

``` text
H = future forecast horizon
```

For binary event forecasting:

``` text
y(t,H) = 1
```

if a validated target event occurs within:

``` text
(t, t + H]
```

otherwise:

``` text
y(t,H) = 0
```

provided the future interval has adequate ground-truth coverage.

------------------------------------------------------------------------

# 11. Multi-Horizon Forecasting

C3 should support research across multiple horizons.

Conceptually:

``` text
P(event within 15 min)
P(event within 30 min)
P(event within 60 min)
...
```

The exact horizons must be justified by:

``` text
warning usefulness
available data
event dynamics
literature/domain evidence
```

They are not frozen in this guide.

------------------------------------------------------------------------

# 12. Primary Target

The cleanest baseline target is:

``` text
target_landslide_within_horizon
```

or an equivalently named binary event target.

This should be independently derived from ground-truth event
annotations.

------------------------------------------------------------------------

# 13. Ground Truth Is Critical

A forecasting model cannot be scientifically validated if the target is
merely another formula generated from its own input variables.

Preferred target sources, in descending evidential strength, may
include:

``` text
validated real event annotations
controlled physical event/condition annotations
trusted external historical event labels
clearly documented synthetic scenario truth
```

Synthetic labels remain synthetic evidence.

------------------------------------------------------------------------

# 14. Existing C3 Dataset Assets

Existing work includes:

``` text
basic_c3_sensor_data.csv
```

approximately:

``` text
60 × 28
```

and synthetic temporal datasets including:

``` text
c3_temporal_synthetic_v2.csv
c3_temporal_synthetic_v3.csv
```

with later generator work toward v4.

These are development/research artifacts.

They must not be presented as physical field measurements.

------------------------------------------------------------------------

# 15. Existing Synthetic v2

Recorded development state:

``` text
20,000 rows
```

with heavily risk-oriented class/mode distributions in that version.

This dataset should remain versioned rather than silently overwritten.

------------------------------------------------------------------------

# 16. Existing Synthetic v3

Recorded development state:

``` text
42,000 rows
6 zones
12 pipes
```

with a substantially different operating-mode/risk distribution.

Again:

``` text
v2 ≠ v3
```

They represent different generator versions/experiments.

------------------------------------------------------------------------

# 17. Synthetic v4

Generator development included correction of the:

``` text
storm_steps_remaining
```

logic/indentation.

Any dataset produced before and after a generator bug fix must receive a
different version/hash.

Never silently replace old experimental data.

------------------------------------------------------------------------

# 18. Audit Before Further Training

Before building the final C3 pipeline, audit all existing C3 datasets
for:

``` text
schema
units
data origin
generator version
target-generation logic
class distribution
mode distribution
zone/device distribution
duplicate sequences
future leakage
target-derived features
event grouping
timestamp correctness
```

Produce:

``` text
C3_DATASET_AUDIT.md
```

------------------------------------------------------------------------

# 19. Existing C3 Forecasting Fields

Previously identified candidate inputs include:

``` text
rain_15m_sum
rain_1h_sum
rain_6h_sum
soil_moisture_mean
soil_moisture_trend_30m
tilt_mean_deg
tilt_rate_deg_h
vibration_mean_g
neighbour-zone soil moisture
neighbour-zone rainfall
estimated_input_pct
mean_repair_confidence
current_system_mode
horizon_min
```

Existing/generated datasets have also contained:

``` text
risk_probability
risk_level
recommended_mode
target_landslide_within_horizon
```

These fields must not all be treated as ordinary input features.

------------------------------------------------------------------------

# 20. Leakage Audit of Existing Fields

Recommended initial classification:

  -----------------------------------------------------------------------
  Field                               Default role
  ----------------------------------- -----------------------------------
  rainfall histories                  candidate feature

  soil moisture history/trend         candidate feature

  tilt history/rate                   candidate feature

  vibration                           candidate feature

  neighbour environmental context     candidate feature

  estimated/recovered input           candidate quality/provenance
  percentage                          feature

  mean repair confidence              candidate quality feature

  current system mode                 candidate context feature requiring
                                      bias/leakage analysis

  horizon_min                         model/task context for
                                      horizon-conditioned design

  target_landslide_within_horizon     target

  risk_probability                    **exclude from model input by
                                      default**

  risk_level                          **exclude until provenance is
                                      established**

  recommended_mode                    **exclude from C3 input/target by
                                      default**
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 21. Risk Probability

`risk_probability` should normally be:

``` text
C3 model output
```

not a training input.

If an existing synthetic generator created a `risk_probability`
mathematically from the same variables used to define the target,
feeding it to the model creates a shortcut.

Audit and exclude unless independent provenance justifies otherwise.

------------------------------------------------------------------------

# 22. Risk Level

A label such as:

``` text
LOW / WATCH / HIGH / CRITICAL
```

may be useful for presentation.

But determine whether it is:

``` text
independently annotated
```

or simply:

``` text
threshold(risk_probability)
```

If derived from C3 probability, it is a downstream presentation/decision
label, not independent ground truth.

------------------------------------------------------------------------

# 23. Recommended Mode

`recommended_mode` belongs primarily to:

``` text
Decision Engine policy
```

unless an independent expert annotation dataset exists.

Do not train C3 to predict a mode that was itself generated from a risk
formula and then claim it learned independent landslide forecasting.

------------------------------------------------------------------------

# 24. Time-to-Danger

`time_to_danger` is only valid when event timing is independently known.

It also introduces censoring:

``` text
no event observed before dataset ends
```

does not necessarily mean:

``` text
infinite time to danger
```

Therefore time-to-event modeling should be treated as an advanced
extension unless ground truth supports it.

------------------------------------------------------------------------

# 25. C3 Data Source

The preferred runtime source is:

``` text
Golden Timeline
```

not arbitrary raw packets.

The Golden Timeline provides:

``` text
eligible environmental observations
+
credibility metadata
+
recovery provenance
+
timing
+
quality information
```

while raw data remains preserved elsewhere.

------------------------------------------------------------------------

# 26. Golden Timeline Is Not Automatically Perfect

C3 should not assume every Golden Timeline value is equally certain.

Inputs may be:

``` text
DIRECT
LATE_ORIGINAL
BACKUP
FUSED/DERIVED
```

with different confidence.

C3 should preserve that information.

------------------------------------------------------------------------

# 27. Sequence Definition

For forecast origin `t`, construct a history window:

``` text
[t - W, t]
```

where:

``` text
W = history duration
```

Only observations available by the forecast origin may enter the
runtime-equivalent sequence.

Exact `W` is experimental.

------------------------------------------------------------------------

# 28. Why Duration-Based Windows Matter

Under variable-rate sampling:

``` text
last 20 observations
```

can represent radically different real-world durations.

Therefore C3 should primarily reason in:

``` text
time duration
```

rather than only:

``` text
number of rows
```

Sequence implementation may still cap/pad timestep count for batching.

------------------------------------------------------------------------

# 29. Variable-Length Sequences

Possible representations:

``` text
variable-length packed sequences
padding + mask
event sequence
decision-grid representation + timing metadata
```

The final representation depends on the selected model.

Do not discard actual timing merely to make tensors rectangular.

------------------------------------------------------------------------

# 30. Δt

For observation step `i`:

``` text
Δt_i = t_i - t_(i-1)
```

C3 should explicitly represent elapsed time where the model architecture
permits.

This tells the model whether a change occurred over:

``` text
seconds
minutes
hours
```

------------------------------------------------------------------------

# 31. Per-Channel Time Since Last Observation

For multivariate irregular data, a stronger representation may include:

``` text
δ_i,j
```

where `j` is a feature/sensor channel and `δ` is time since that channel
was last observed.

This is particularly relevant to GRU-D-style handling.

------------------------------------------------------------------------

# 32. Missingness Mask

For each variable/channel:

``` text
m_i,j = 1 if observed
m_i,j = 0 if missing/not observed
```

Missingness itself may carry information.

Do not replace every missing value with zero without a mask.

------------------------------------------------------------------------

# 33. Value Age

If a value is carried forward for a decision-grid representation, also
preserve:

``` text
age_since_last_observation
```

Otherwise the model cannot distinguish:

``` text
fresh 65%
```

from:

``` text
65% copied from 30 minutes ago
```

------------------------------------------------------------------------

# 34. Acquisition vs Reporting

C3 must not confuse:

``` text
sensor acquisition frequency
```

with:

``` text
packet reporting frequency
```

An IMU may be sampled rapidly locally and transmitted as aggregated
statistics.

C3 uses the semantic measurement/aggregation stream provided by the
telemetry contract.

------------------------------------------------------------------------

# 35. Candidate Environmental Feature Families

Organize features as:

``` text
F0 — current environmental values
F1 — temporal history/trends
F2 — rainfall accumulation/regime
F3 — motion/deformation
F4 — spatial/neighbour context
F5 — timing/missingness
F6 — operating mode
F7 — C1 credibility
F8 — C2 recovery provenance
```

This directly supports ablation.

------------------------------------------------------------------------

# 36. F0 --- Current Environmental State

Potential:

``` text
soil moisture
temperature/humidity where justified
FSR response where calibrated/meaningful
rainfall
tilt
vibration
```

Do not include a sensor simply because hardware exposes it.

Each feature needs physical/research justification.

------------------------------------------------------------------------

# 37. F1 --- Temporal Features

Possible engineered summaries:

``` text
rolling mean
rolling median
rolling std
slope
rate of change
short/long trend
recent extrema
```

Sequence models may also learn temporal patterns directly.

Engineered features can still be useful for baselines.

------------------------------------------------------------------------

# 38. F2 --- Rainfall

Candidate causal features:

``` text
rain_15m_sum
rain_1h_sum
rain_6h_sum
current rainfall rate
rainfall trend
```

Only past/current rainfall belongs in the forecast input.

------------------------------------------------------------------------

# 39. F3 --- Motion / Deformation

Potential:

``` text
tilt
tilt rate
acceleration summaries
vibration RMS/energy
FSR response/trend
```

Raw high-frequency IMU streams should usually be aggregated into
meaningful features before the main temporal model unless a separate
high-frequency architecture is justified.

------------------------------------------------------------------------

# 40. F4 --- Spatial Context

Potential:

``` text
same-zone sensor summaries
neighbour-zone soil moisture
neighbour-zone rainfall
neighbour movement indicators
spatial disagreement/agreement
```

Neighbour definitions must be configured, not selected after seeing the
target.

------------------------------------------------------------------------

# 41. F5 --- Timing and Missingness

Critical:

``` text
Δt
per-channel age
missingness mask
observation density
gap statistics
```

These features are central to C3's variable-rate research claim.

------------------------------------------------------------------------

# 42. F6 --- Operating Mode

Represent:

``` text
DEEP_SLEEP
IDLE
RISK
WARNING
EMERGENCY
```

using an appropriate encoding.

However mode requires special causal analysis.

------------------------------------------------------------------------

# 43. Mode Is a Context Variable, Not Ground Truth

Mode is influenced by the system's previous risk state.

Therefore:

``` text
WARNING mode
```

may itself imply that earlier logic already considered the environment
dangerous.

If C3 simply learns:

``` text
WARNING → landslide
```

performance can appear strong without learning environmental dynamics.

This is feedback-induced bias.

------------------------------------------------------------------------

# 44. Mode Leakage Investigation

Mandatory experiments:

``` text
C3 without mode
vs
C3 with mode
```

and analyze:

``` text
performance improvement
feature dependence
performance within each mode
mode-only baseline
```

If a mode-only model performs extremely well, investigate circularity.

------------------------------------------------------------------------

# 45. Mode-Only Baseline

Train/evaluate a trivial model using only:

``` text
current_mode
```

This establishes how much predictive information the operational policy
already encodes.

The full C3 must demonstrate value beyond this shortcut.

------------------------------------------------------------------------

# 46. Historical Mode

Depending on the final representation, C3 may use:

``` text
mode at each timestep
```

rather than only the current mode.

This can describe why sampling density changed through the sequence.

------------------------------------------------------------------------

# 47. Requested vs Applied Mode

Use the mode/policy actually applied by the device when known.

Do not assume a requested mode became active before acknowledgement.

This matters for interpreting Δt and sampling density.

------------------------------------------------------------------------

# 48. F7 --- C1 Credibility

Candidate representations:

``` text
credibility class
probability/confidence
anomaly fraction in window
VALID_EVENT fraction
per-value quality mask
```

C1 information should tell C3:

``` text
how much to trust the evidence
```

not replace environmental values.

------------------------------------------------------------------------

# 49. F8 --- C2 Recovery Provenance

Candidate:

``` text
was_recovered
recovery_method
repair_confidence
estimated_input_pct
fraction_direct
fraction_backup
fraction_derived
```

This allows C3 to distinguish:

``` text
direct measurement
```

from:

``` text
reconstructed evidence
```

------------------------------------------------------------------------

# 50. Define `estimated_input_pct`

If retained, explicitly define it.

Recommended semantic concept:

> Percentage/fraction of model inputs in the forecast window that were
> not direct original observations and instead came from an approved
> recovery/estimation process.

The exact numerator/denominator must be fixed in the feature
specification.

------------------------------------------------------------------------

# 51. C1/C2 Outputs Must Be Runtime-Like

For offline C3 training:

``` text
do not use perfect ground-truth C1/C2 labels
```

if runtime C3 would receive predicted C1/C2 outputs.

Use:

``` text
out-of-fold upstream predictions
```

or predictions from models trained on disjoint data.

Otherwise integrated performance is inflated.

------------------------------------------------------------------------

# 52. Sequence Dataset Architecture

Recommended separation:

``` text
observation-level Golden snapshot
+
sequence manifest
+
labels
```

rather than storing giant serialized arrays inside CSV.

------------------------------------------------------------------------

# 53. Sequence Manifest

Conceptual:

``` text
sequence_id
zone_id
forecast_time
window_start
window_end
horizon_min
target
split
source_dataset_version
golden_policy_version
feature_schema_version
```

The training loader reconstructs the sequence from the frozen snapshot.

------------------------------------------------------------------------

# 54. Why a Sequence Manifest Is Valuable

It makes each training example reproducible.

Given:

``` text
sequence_id
```

the team should be able to determine:

``` text
which observations were used
which forecast time
which horizon
which target
which split
```

------------------------------------------------------------------------

# 55. Multiple Horizons --- Long Form

Recommended initial research representation:

``` text
same forecast origin
+
different horizon_min
```

as separate manifest records.

Example:

``` text
SEQ100 / 15
SEQ100 / 30
SEQ100 / 60
```

This is transparent and model-agnostic.

------------------------------------------------------------------------

# 56. Multi-Output Alternative

Later, one model may output:

``` text
p15
p30
p60
```

simultaneously.

This can exploit relationships between horizons but increases
architecture complexity.

Establish single/long-form horizon baselines first.

------------------------------------------------------------------------

# 57. Horizon Consistency

For cumulative event probability, ideally:

``` text
P(event ≤ 15m)
≤
P(event ≤ 30m)
≤
P(event ≤ 60m)
```

Independent horizon models may violate this.

Measure such violations if using separate models.

A future multi-horizon architecture may explicitly encourage
consistency.

------------------------------------------------------------------------

# 58. Label Construction

For forecast origin `t`:

``` text
target = 1
if validated event occurs in (t, t+H]
```

Negative target requires:

``` text
adequate future observation/annotation coverage
```

through `t+H`.

------------------------------------------------------------------------

# 59. Right Censoring

If dataset ends at:

``` text
t + 10 minutes
```

you cannot safely label a:

``` text
60-minute horizon
```

as negative.

Exclude/censor that sequence.

------------------------------------------------------------------------

# 60. Event Exclusion After Onset

If C3 is intended for **early warning**, sequences after a confirmed
event has already begun may not represent meaningful forecasting.

Define event onset and an exclusion policy.

Do not inflate performance by predicting an event after obvious
event-state measurements are already present unless that is explicitly
the task.

------------------------------------------------------------------------

# 61. Warning Lead Time

For each correctly predicted event, calculate how early useful warning
became available.

Possible event-level metric:

``` text
lead_time
=
event_onset
-
first qualifying forecast time
```

with a predefined probability threshold/persistence rule.

This is more meaningful than accuracy alone.

------------------------------------------------------------------------

# 62. Split Before Window Generation

Preferred:

``` text
assign event/time blocks/zones to split
        ↓
generate windows inside each split
```

not:

``` text
generate thousands of overlapping windows
        ↓
randomly split windows
```

The latter causes severe leakage.

------------------------------------------------------------------------

# 63. Overlapping-Window Leakage

Example:

``` text
window A: 10:00–11:00
window B: 10:01–11:01
```

They share nearly all data.

If one is training and the other testing, evaluation is invalid.

Group by event/time block before window generation.

------------------------------------------------------------------------

# 64. Event Grouping

All windows associated with the same synthetic/physical hazard episode
should remain in one partition.

This prevents the model from seeing the same event pattern during
training and testing.

------------------------------------------------------------------------

# 65. Zone Holdout

Where data volume permits:

``` text
train on some zones
test on unseen zone
```

can evaluate spatial generalization.

With only a small physical prototype, interpret results conservatively.

------------------------------------------------------------------------

# 66. Time Holdout

A deployment-like split:

``` text
earlier period → training
later period → validation/test
```

is valuable when enough real temporal data exists.

------------------------------------------------------------------------

# 67. Synthetic Scenario Holdout

For synthetic data:

``` text
generator scenario/event ID
```

must be the grouping unit.

Do not let variations of the same storm/failure event cross splits.

------------------------------------------------------------------------

# 68. Physical vs Synthetic Evaluation

Report separately:

``` text
synthetic test performance
physical-demo performance
external-data performance
```

if available.

Do not report one combined number as though all evidence has equal
realism.

------------------------------------------------------------------------

# 69. Preprocessing

Any learned preprocessing:

``` text
mean/std scaling
imputation statistics
category mapping learned from data
```

must be fitted on:

``` text
TRAIN only
```

then applied unchanged to validation/test.

------------------------------------------------------------------------

# 70. Normalization Across Sensor Types

Physical units differ greatly.

Potential scaling:

``` text
standardization
robust scaling
sensor-specific normalization
```

but retain physical-unit versions for interpretation.

Never normalize using full-dataset statistics.

------------------------------------------------------------------------

# 71. Missing-Value Strategy

Compare appropriate approaches:

``` text
simple imputation + mask
forward fill + age
learned decay
GRU-D style handling
```

Do not hide missingness.

------------------------------------------------------------------------

# 72. Baseline 0 --- Persistence / Simple Rule

A non-ML baseline can use:

``` text
current/rolling hazard indicators
```

with documented thresholds where defensible.

This tests whether advanced forecasting beats simple current-state
logic.

------------------------------------------------------------------------

# 73. Baseline 1 --- Logistic Regression

Using engineered features:

``` text
rainfall
soil moisture
tilt
vibration
trends
```

provides an interpretable linear baseline.

------------------------------------------------------------------------

# 74. Baseline 2 --- LightGBM / XGBoost

A strong tabular baseline using engineered historical summaries.

This is essential.

If a complex sequence model cannot outperform a strong boosted-tree
baseline meaningfully, its added complexity must be questioned.

------------------------------------------------------------------------

# 75. Baseline 3 --- Standard GRU

A standard GRU provides the key sequence-model baseline.

However standard GRU alone does not explicitly solve irregular timing.

------------------------------------------------------------------------

# 76. Optional LSTM Baseline

LSTM can be included as a classical recurrent comparison if compute/time
allows.

It is not mandatory if it adds little scientific value beyond GRU.

------------------------------------------------------------------------

# 77. Candidate Proposed Model --- Time-Aware GRU

A time-aware GRU modifies the temporal representation/state update using
elapsed time.

This directly targets C3's irregular-sampling problem.

It is a strong candidate because the research question specifically
concerns:

``` text
variable-rate temporal dynamics
```

------------------------------------------------------------------------

# 78. Candidate Proposed Model --- GRU-D

GRU-D is especially relevant when data contains:

``` text
missingness
irregular observations
time since last observation
```

It incorporates masks and time gaps/decay mechanisms.

This aligns well with C3's intended inputs.

------------------------------------------------------------------------

# 79. Time-Aware GRU vs GRU-D

Do not choose by name.

Compare based on:

``` text
data representation
missingness pattern
Δt handling
performance
calibration
robustness
runtime cost
implementation complexity
```

The final proposed model is selected experimentally.

------------------------------------------------------------------------

# 80. Attention

Attention may be added only after a strong recurrent baseline is
established.

Potential benefit:

``` text
highlight influential timesteps/features
```

but it adds complexity and does not automatically improve accuracy or
interpretability.

------------------------------------------------------------------------

# 81. Transformer Models

A Transformer is not required merely because it is modern.

For a relatively small research dataset, recurrent/tree approaches may
be more appropriate.

A Transformer should only be added if:

``` text
data volume
sequence length
research question
compute
```

justify it.

------------------------------------------------------------------------

# 82. Recommended Model Comparison

Core comparison:

``` text
simple rule/persistence
logistic regression
LightGBM/XGBoost
standard GRU
Time-Aware GRU
GRU-D
```

Optional:

``` text
LSTM
attention extension
```

This is sufficient for a strong study.

------------------------------------------------------------------------

# 83. Mandatory C3 Ablation

The agreed core ablation is:

``` text
A0 — Sensors/current state
A1 — + History
A2 — + Δt
A3 — + Mode
A4 — + C1 credibility
A5 — + C2 recovery/provenance
```

This is central to proving the component's value.

------------------------------------------------------------------------

# 84. Meaning of A0

Use only current/current-window sensor state without explicit historical
sequence.

This answers:

> Does temporal forecasting add value beyond a snapshot?

------------------------------------------------------------------------

# 85. Meaning of A1

Add temporal history but treat intervals conventionally.

This tests:

``` text
snapshot
vs
sequence
```

------------------------------------------------------------------------

# 86. Meaning of A2

Add explicit elapsed-time information.

This tests C3's key claim:

``` text
Does knowing actual Δt improve variable-rate forecasting?
```

------------------------------------------------------------------------

# 87. Meaning of A3

Add mode context.

This tests whether:

``` text
operating state
```

adds information beyond Δt.

Also compare against the mode-only baseline to detect circular
shortcuts.

------------------------------------------------------------------------

# 88. Meaning of A4

Add C1 credibility information.

This tests:

``` text
Does knowing measurement quality improve forecast reliability?
```

Use leakage-safe upstream predictions.

------------------------------------------------------------------------

# 89. Meaning of A5

Add C2 recovery/missingness provenance.

This tests:

``` text
Does distinguishing direct vs recovered evidence improve forecasting under degraded telemetry?
```

This is an important integrated-system contribution.

------------------------------------------------------------------------

# 90. Keep the Ablation Fair

Across A0--A5:

``` text
same data split
same target definition
same evaluation periods
same model family where comparison requires it
same tuning budget where practical
```

Otherwise improvement cannot be attributed cleanly.

------------------------------------------------------------------------

# 91. Additional Architecture Ablation

After feature ablation:

``` text
standard GRU
vs
Time-Aware GRU
vs
GRU-D
```

on the same mature feature representation.

This separates:

``` text
feature/context contribution
```

from:

``` text
architecture contribution
```

------------------------------------------------------------------------

# 92. Primary Metrics

At minimum:

``` text
ROC-AUC
PR-AUC
precision
recall/sensitivity
F1
specificity
confusion matrix at selected threshold
```

For rare hazards, PR-AUC and event recall may be particularly
informative.

------------------------------------------------------------------------

# 93. Accuracy Is Not Enough

A model predicting:

``` text
no landslide
```

almost all the time can obtain high accuracy if events are rare.

Therefore do not use accuracy as the headline metric.

------------------------------------------------------------------------

# 94. Probability Calibration

Because C3 produces risk probability, calibration is essential.

Evaluate:

``` text
Brier score
reliability diagram
ECE or another documented calibration statistic
```

where appropriate.

------------------------------------------------------------------------

# 95. Why Calibration Matters

Suppose C3 outputs:

``` text
0.80
```

The Decision Engine may interpret that as strong evidence.

If predictions near 0.80 correspond to events only 30% of the time, the
probability is misleading even if ranking performance is good.

------------------------------------------------------------------------

# 96. Calibration Methods

If needed, compare:

``` text
Platt/sigmoid
isotonic
temperature scaling for neural outputs where appropriate
```

Fit calibration using validation/calibration data only.

Never calibrate on the final test set.

------------------------------------------------------------------------

# 97. Event-Level Recall

Besides row/window metrics, measure:

``` text
fraction of hazard events that received a qualifying warning before onset
```

This better reflects early-warning usefulness.

------------------------------------------------------------------------

# 98. False Alarms Per Time

Measure operational burden:

``` text
false warnings per day
```

or another appropriate time-normalized metric.

This is more meaningful than false-positive percentage alone.

------------------------------------------------------------------------

# 99. Warning Lead Time

Report distribution:

``` text
median lead time
quartiles/range
event-by-event lead time
```

for detected events.

A forecast that detects risk 30 seconds before onset differs
operationally from one providing substantial earlier warning.

------------------------------------------------------------------------

# 100. Threshold Selection

Prediction threshold should be selected using:

``` text
validation data
+
documented safety/operational objective
```

not the final test set.

Decision Engine thresholds remain separately configurable.

------------------------------------------------------------------------

# 101. Hysteresis Belongs to Decision Engine

C3 can produce fluctuating probabilities:

``` text
0.69
0.71
0.68
0.72
```

The Decision Engine handles:

``` text
persistence
hysteresis
minimum dwell
mode transition rules
```

Do not force these operational rules into model labels.

------------------------------------------------------------------------

# 102. Stress Test --- Long Gaps

Create/evaluate:

``` text
larger-than-normal observation gaps
```

Measure degradation for:

``` text
standard GRU
Time-Aware GRU
GRU-D
```

This directly tests the variable-rate claim.

------------------------------------------------------------------------

# 103. Stress Test --- Short Gaps

Evaluate bursts of dense observations.

The model should not interpret:

``` text
many samples
```

as:

``` text
large elapsed time
```

when Δt is small.

------------------------------------------------------------------------

# 104. Stress Test --- Missing Sensors

Remove selected channels during test:

``` text
soil sensor missing
rainfall missing
motion missing
neighbour missing
```

Measure graceful degradation.

------------------------------------------------------------------------

# 105. Stress Test --- Recovered Inputs

Replace a controlled fraction of direct inputs with:

``` text
Backup Pipe
neighbour fusion
other approved recovery
```

and compare models:

``` text
without provenance
vs
with provenance/confidence
```

------------------------------------------------------------------------

# 106. Stress Test --- Abrupt Mode Change

Evaluate sequences:

``` text
IDLE → RISK
RISK → WARNING
WARNING → EMERGENCY
```

The model must handle the resulting change in observation density.

------------------------------------------------------------------------

# 107. Stress Test --- Stale Readings

Carry old values forward while increasing:

``` text
age_since_last_observation
```

A time-aware model should not treat stale and fresh values identically.

------------------------------------------------------------------------

# 108. Stress Test --- C1 Errors

Inject realistic upstream credibility errors:

``` text
valid event incorrectly marked anomalous
anomaly incorrectly accepted
```

and measure C3 sensitivity.

Integrated AI components must be tested with imperfect upstream models,
not only perfect labels.

------------------------------------------------------------------------

# 109. Stress Test --- C2 Errors

Inject:

``` text
incorrect recovery provenance
low-quality reconstruction
delayed recovery
```

and measure forecast robustness.

------------------------------------------------------------------------

# 110. Stress Test --- Mode Shortcut

Shuffle or mask mode at test time.

If performance collapses while environmental signals remain strong,
investigate whether the model over-relies on mode.

------------------------------------------------------------------------

# 111. Stress Test --- Distribution Shift

Test conditions not heavily represented in training:

``` text
different rainfall intensity
different missingness rate
different mode distribution
different sensor noise
```

Report degradation.

------------------------------------------------------------------------

# 112. Class Imbalance

Handle event rarity only after splitting.

Potential:

``` text
class weighting
focal loss
careful training sampling
```

Avoid naive SMOTE over temporal sequences.

------------------------------------------------------------------------

# 113. Sequence Sampling

During training, event-rich windows may be sampled more often.

But evaluation must retain the natural/frozen test distribution.

Do not report metrics on artificially balanced test data as deployment
performance.

------------------------------------------------------------------------

# 114. Loss Function

Baseline:

``` text
binary cross-entropy
```

Potential alternatives:

``` text
weighted BCE
focal loss
```

Selection must be experimental.

------------------------------------------------------------------------

# 115. Multi-Horizon Loss

If one model predicts multiple horizons:

``` text
L = Σ w_h L_h
```

where horizon weights are documented.

Do not arbitrarily weight horizons without justification.

------------------------------------------------------------------------

# 116. Model Input Tensor

Conceptually:

``` text
X: [batch, time, features]
M: [batch, time, features]  # masks
Δ: [batch, time, features or time]
Mode: [batch, time, encoding]
```

Exact structure depends on architecture.

------------------------------------------------------------------------

# 117. Sequence Padding

For batches:

``` text
pad to maximum/capped length
+
mask padded steps
```

Padded zeros must never be interpreted as real measurements.

------------------------------------------------------------------------

# 118. Sequence Length Limits

Set a maximum based on:

``` text
history duration
highest expected sampling density
memory
runtime latency
```

If truncating, define whether the most recent observations are retained.

------------------------------------------------------------------------

# 119. Data Loader

The loader should:

``` text
read sequence manifest
retrieve frozen Golden records
construct feature channels
construct masks/Δt
apply train-fitted preprocessing
pad/batch
return target + metadata
```

------------------------------------------------------------------------

# 120. Dataset Builder Tests

Verify:

``` text
no observation after forecast_time
no target event included in input
window bounds correct
horizon label correct
censored windows excluded
split membership preserved
mode timestamps correct
recovery provenance correct
```

------------------------------------------------------------------------

# 121. Sequence Visualization

Before training, visualize random sequences showing:

``` text
rainfall
soil moisture
tilt
mode
Δt
missingness
target event time
```

This catches dataset errors that statistics may miss.

------------------------------------------------------------------------

# 122. Training Pipeline

``` text
load frozen dataset/manifest
        ↓
validate
        ↓
load TRAIN split
        ↓
fit preprocessing
        ↓
train baseline/model
        ↓
evaluate VALIDATION
        ↓
tune
        ↓
select architecture
        ↓
calibrate
        ↓
freeze model
        ↓
evaluate TEST once
        ↓
save artifact + metadata
```

------------------------------------------------------------------------

# 123. Hyperparameter Tuning

Candidate parameters:

``` text
history duration
hidden size
number of recurrent layers
dropout
learning rate
batch size
class weights
decay parameters
```

Tune using validation data.

Do not conduct uncontrolled manual tuning against test results.

------------------------------------------------------------------------

# 124. Early Stopping

Use validation metric/loss.

Save:

``` text
best epoch
best validation score
training curves
```

This improves reproducibility.

------------------------------------------------------------------------

# 125. Random Seeds

Record seeds for:

``` text
data generation
split
model initialization
training sampler
```

where supported.

Run multiple seeds for final neural comparisons where feasible.

------------------------------------------------------------------------

# 126. Model Artifact

Save:

``` text
model weights
architecture config
preprocessing
feature schema
mode encoding
label/horizon definition
calibration model
dataset version
split version
code revision
```

------------------------------------------------------------------------

# 127. Model Registry

Approved C3 model metadata should identify:

``` text
model_version
status
training dataset
metrics
supported horizons
feature schema
approved_at
```

Only promoted models run in production.

------------------------------------------------------------------------

# 128. Runtime Forecasting

``` text
forecast scheduler/event
        ↓
select forecast origin
        ↓
query Golden Timeline as-of origin
        ↓
build history sequence
        ↓
construct Δt/masks/mode/provenance
        ↓
preprocess
        ↓
model inference
        ↓
calibration
        ↓
store C3 forecast
        ↓
Decision Engine
```

------------------------------------------------------------------------

# 129. Forecast Trigger

C3 may run:

``` text
on scheduled decision ticks
on meaningful new validated evidence
on mode transitions
```

depending on final runtime design.

Do not retrigger wastefully for every internal high-frequency raw IMU
sample.

------------------------------------------------------------------------

# 130. Runtime As-Of Semantics

At inference time, query:

``` text
what GeoNex knew at forecast time
```

not retrospective best data that arrived later.

Late data can improve future forecasts, but must not rewrite historical
model inputs when evaluating original runtime performance.

------------------------------------------------------------------------

# 131. Forecast Record

Conceptually:

``` json
{
  "forecast_id": "...",
  "zone_id": "Z01",
  "forecast_time": "...",
  "horizon_min": 30,
  "risk_probability": 0.73,
  "model_version": "...",
  "input_manifest_id": "...",
  "generated_at": "..."
}
```

Risk level/mode can be added downstream according to policy.

------------------------------------------------------------------------

# 132. Forecast Input Manifest

For auditability, store or reconstruct:

``` text
forecast_id
input observation IDs
Golden policy version
feature schema
history bounds
mode history
quality summary
```

This enables forensic explanation.

------------------------------------------------------------------------

# 133. Inference Latency

Measure:

``` text
Golden query time
feature construction time
model inference time
calibration time
total C3 processing time
```

But remember total warning latency also includes sensing/reporting and
upstream processing.

------------------------------------------------------------------------

# 134. End-to-End Warning Latency

Conceptually:

``` text
environment changes
+
sensor acquisition delay
+
aggregation delay
+
reporting delay
+
LoRa/retry delay
+
gateway/ingestion
+
C4/C1/C2
+
C3
+
Decision Engine
+
alert delivery
```

Do not claim C3 inference latency equals total system warning latency.

------------------------------------------------------------------------

# 135. Edge Placement

Recommended initial placement:

``` text
C3 inference on Lenovo ThinkCentre Main Computing System
```

rather than ESP32.

This provides:

``` text
sufficient memory
sequence processing
model management
database access
local operation
```

It remains local/edge-site computing relative to remote cloud services.

------------------------------------------------------------------------

# 136. Explainability

Potential approaches:

``` text
permutation importance for tabular baseline
SHAP for tree baseline
temporal occlusion
feature ablation
integrated gradients where appropriate
attention visualization only if attention exists
```

Do not rely on one explanation method.

------------------------------------------------------------------------

# 137. Temporal Occlusion

Example:

``` text
mask recent rainfall segment
re-run forecast
observe probability change
```

Repeat for:

``` text
soil moisture
tilt
mode
C1 quality
C2 provenance
```

This helps explain temporal dependence.

------------------------------------------------------------------------

# 138. Attention Is Not Explanation by Default

If an attention mechanism assigns high weight to a timestep, that does
not automatically prove causal importance.

Use perturbation/ablation evidence as well.

------------------------------------------------------------------------

# 139. Error Analysis

Categorize:

``` text
false negative before event
false alarm during heavy rain
mode-shortcut error
missing-sensor error
recovery-related error
late-warning event
overconfident error
underconfident correct prediction
```

This is more valuable than reporting only aggregate metrics.

------------------------------------------------------------------------

# 140. Event-Level Case Studies

Select representative:

``` text
successful early warning
missed event
false alarm
degraded-data event
```

For each, plot:

``` text
sensor history
mode
C1/C2 quality
risk probability
event onset
Decision Engine state
```

------------------------------------------------------------------------

# 141. Research Figure --- Variable Rate

A key figure should visually show:

``` text
DEEP_SLEEP     IDLE      RISK      WARNING
  ●------●------●---●---●-●-●-●-●
```

along with Δt.

Then compare how:

``` text
standard fixed-step interpretation
```

differs from:

``` text
time-aware interpretation
```

------------------------------------------------------------------------

# 142. Research Figure --- Ablation

Show improvement/degradation across:

``` text
Sensors
+ History
+ Δt
+ Mode
+ C1
+ C2
```

using a meaningful metric such as:

``` text
PR-AUC
event recall
Brier score
```

rather than accuracy only.

------------------------------------------------------------------------

# 143. Research Figure --- Calibration

Plot:

``` text
predicted probability
vs
observed event frequency
```

before/after calibration if used.

This supports risk-probability credibility.

------------------------------------------------------------------------

# 144. Research Figure --- Lead Time

For each test event:

``` text
event onset
risk probability trajectory
warning threshold
first qualifying warning
```

This demonstrates actual early-warning value.

------------------------------------------------------------------------

# 145. Research Success Criteria

C3 becomes a strong research contribution if experiments support claims
such as:

``` text
temporal history improves forecasting over snapshot features
explicit Δt improves robustness/performance under variable-rate sensing
mode context provides additional value without dominating via circular leakage
C1 quality metadata improves forecasts under corrupted measurements
C2 provenance improves forecasts under recovered/missing data
time-aware recurrent modeling improves over standard GRU under irregular sampling
probabilities can be meaningfully calibrated
useful warning lead time is achieved on held-out events
```

Not all must succeed.

------------------------------------------------------------------------

# 146. System-Level Value

C3 should also support the broader GeoNex hypothesis:

``` text
adaptive sensing
can reduce unnecessary monitoring/communication
while
time-aware forecasting retains useful risk awareness
```

This is evaluated jointly with Document 04's sampling/resource
experiments.

C3 alone should not claim energy savings.

------------------------------------------------------------------------

# 147. Resource/Accuracy Trade-Off Experiment

Compare simulated/measured policies such as:

``` text
always-high-rate monitoring
vs
GeoNex adaptive variable-rate monitoring
```

Measure:

``` text
forecast quality
warning lead time
number of transmitted reports
radio activity
energy proxy or measured consumption
```

This can provide strong system-level evidence.

------------------------------------------------------------------------

# 148. Avoid Unfair Comparison

An always-high-rate system naturally has more information.

The question is not necessarily:

``` text
Can adaptive sensing beat unlimited high-rate sensing?
```

A more meaningful question is:

> How much forecasting performance is retained or improved relative to
> the reduction in communication/resource use?

------------------------------------------------------------------------

# 149. Controlled Cumulative Retraining

C3 "self-learning" must mean:

``` text
collect new observations
        ↓
C1/C2 validated/provenance-aware data
        ↓
build candidate dataset version
        ↓
train candidate model
        ↓
evaluate against current approved model
        ↓
promotion gate
        ├── better/acceptable → promote
        └── worse/unsafe → reject
```

No uncontrolled online weight updates.

------------------------------------------------------------------------

# 150. Retraining Trigger

Potential triggers:

``` text
scheduled data-volume threshold
detected distribution shift
new physical-event evidence
periodic research retraining
```

Exact policy is deferred.

------------------------------------------------------------------------

# 151. Promotion Gate

Candidate model should satisfy predefined criteria such as:

``` text
no unacceptable event-recall degradation
calibration acceptable
false alarm burden acceptable
latency acceptable
stress tests pass
```

A candidate is not promoted merely because validation loss is slightly
lower.

------------------------------------------------------------------------

# 152. Rollback

Retain:

``` text
current approved model
previous approved model
configuration
artifacts
```

so deployment can roll back if the new model causes problems.

------------------------------------------------------------------------

# 153. Drift Monitoring

Monitor runtime distributions such as:

``` text
rainfall
soil moisture
Δt
mode
missingness
C1 credibility
C2 recovery fraction
predicted probability
```

Distribution change does not automatically mean model failure, but can
trigger review.

------------------------------------------------------------------------

# 154. No Self-Labeling Loop

Do not:

``` text
use C3's own prediction
as the ground-truth label
for retraining C3
```

Ground truth must come from independent event evidence.

------------------------------------------------------------------------

# 155. Suggested Code Structure

``` text
components/
└── c3_forecasting/
    ├── README.md
    ├── configs/
    ├── datasets/
    ├── features/
    ├── sequences/
    ├── models/
    │   ├── baselines/
    │   ├── gru/
    │   ├── time_aware_gru/
    │   └── grud/
    ├── training/
    ├── evaluation/
    ├── calibration/
    ├── inference/
    ├── monitoring/
    └── tests/
```

------------------------------------------------------------------------

# 156. Shared Code Rule

Do not create private copies of:

``` text
mode enums
telemetry schemas
C1/C2 contracts
Golden provenance enums
zone/device definitions
```

Use shared GeoNex modules.

------------------------------------------------------------------------

# 157. Configuration

Version:

``` text
history duration
forecast horizons
feature schema
model architecture
hidden size
scaling
missingness handling
mode encoding
calibration
thresholds used for evaluation
```

Do not hard-code them across scripts.

------------------------------------------------------------------------

# 158. Example Experiment Configuration

``` yaml
experiment_id: c3_a5_grud_001

dataset:
  version: C3_TEMPORAL_V001

task:
  history_window: <configured>
  horizon_min: <configured>

features:
  schema: C3_A5_V001
  include_delta_t: true
  include_mode: true
  include_c1: true
  include_c2: true

model:
  family: grud

seed: 42
```

Actual durations/hyperparameters are generated by the approved
experiment design.

------------------------------------------------------------------------

# 159. Experiment Registry

Every run records:

``` text
experiment ID
dataset version
split
feature schema
model
hyperparameters
seed
training epochs
best epoch
metrics
calibration
artifact
code revision
```

------------------------------------------------------------------------

# 160. Reproducibility

Eventually a command similar to:

``` bash
python -m components.c3_forecasting.training.train \
  --config components/c3_forecasting/configs/experiments/c3_a5_grud_001.yaml
```

should reproduce a run from frozen data.

------------------------------------------------------------------------

# 161. Unit Tests

Required examples:

``` text
Δt calculation correct
future observations excluded
mask correct
stale-value age correct
mode join is as-of
C1/C2 metadata join is as-of
padding ignored
horizon label correct
censored sequence excluded
```

------------------------------------------------------------------------

# 162. Leakage Tests

Automate:

``` text
max(input.observed_at) <= forecast_time
max(input.available_at) <= forecast_time
target event time > forecast_time
event/scenario group does not cross splits
risk_probability excluded
recommended_mode excluded
future C1/C2 result excluded
```

------------------------------------------------------------------------

# 163. Model Tests

``` text
model loads
expected feature count
variable sequence lengths handled
mask accepted
Δt finite/nonnegative
output probability finite
batch/single inference consistent
```

------------------------------------------------------------------------

# 164. Integration Tests

Minimum:

### Normal direct-data forecast

``` text
Golden Timeline
→ C3
→ forecast
→ Decision Engine
```

### C1 anomaly context

``` text
low-credibility observation
→ quality-aware sequence
→ forecast
```

### C2 recovered data

``` text
missing primary
→ recovery
→ provenance-aware sequence
→ forecast
```

### Mode transition

``` text
IDLE → RISK
→ changed sampling density
→ correct Δt/mode sequence
```

------------------------------------------------------------------------

# 165. Hardware-in-the-Loop Evaluation

The physical prototype should generate sequences under:

``` text
normal stable condition
rainfall change
sensor-value trend
mode transitions
communication gaps
Backup Pipe recovery
```

C3 processing should be exercised end-to-end.

Physical prototype tests do not need to create a real landslide.

They validate the data/timing/integration mechanisms.

------------------------------------------------------------------------

# 166. Real Landslide Prediction Validation

Claims of real-world predictive accuracy require suitable real or
externally validated landslide-event data.

The two-zone prototype alone cannot establish broad geological
generalization.

Keep:

``` text
system/prototype validation
```

separate from:

``` text
real-world landslide predictive validation
```

------------------------------------------------------------------------

# 167. External Dataset Adaptation

If an external landslide dataset is used:

``` text
document source
license
location
sensor definitions
sampling frequency
label definition
units
missingness
mapping to GeoNex features
```

Do not pretend its sensors/modes are identical to GeoNex.

------------------------------------------------------------------------

# 168. Domain Gap

Potential differences:

``` text
soil type
slope
climate
sensor placement
sensor calibration
sampling frequency
event definition
```

must be discussed.

External data can strengthen algorithm evaluation but does not
automatically validate the exact deployment.

------------------------------------------------------------------------

# 169. Synthetic Generator Validation

The synthetic generator itself should be checked for:

``` text
plausible temporal trends
plausible cross-sensor relationships
no direct target leakage
reasonable noise
mode-transition logic
storm/event diversity
missingness diversity
```

A model cannot be stronger than the simulation assumptions used to
train/evaluate it.

------------------------------------------------------------------------

# 170. Avoid Formula-Recovery Research

If synthetic target is generated as:

``` text
target = f(rain, moisture, tilt)
```

and the model receives exactly those variables, very high performance
may simply mean:

``` text
the network rediscovered f()
```

This is useful for pipeline testing but weak evidence of real predictive
capability.

Clearly separate:

``` text
simulation verification
```

from:

``` text
scientific predictive validation
```

------------------------------------------------------------------------

# 171. Strong C3 Thesis Narrative

A defensible narrative:

> Conventional temporal models often assume regularly sampled
> observations, while GeoNex deliberately changes monitoring frequency
> according to operating risk. C3 therefore models landslide-related
> sensor history together with elapsed time, operating mode,
> missingness, measurement credibility and recovery provenance.
> Controlled ablations determine whether each context source improves
> future-risk forecasting, and time-aware recurrent architectures are
> compared against fixed-step and strong tabular baselines.

------------------------------------------------------------------------

# 172. Candidate Contribution Statement

> **A mode-conditioned, time-aware multivariate forecasting framework
> for adaptive IoT landslide monitoring that explicitly represents
> irregular observation intervals and upstream data-quality/recovery
> provenance for near-future risk estimation.**

Final wording must follow actual results.

------------------------------------------------------------------------

# 173. What Would Make C3 Weak

Avoid a study that only does:

``` text
generate synthetic CSV
random 80/20 split
train GRU
report 99% accuracy
```

This would be vulnerable to:

``` text
temporal leakage
overlapping-window leakage
synthetic formula recovery
mode shortcut
class imbalance
no calibration
no real baseline
no ablation
no physical integration evidence
```

------------------------------------------------------------------------

# 174. What Makes C3 Strong

A stronger study demonstrates:

``` text
clean independent targets
event-aware splits
strong tabular baseline
standard GRU baseline
explicit Δt experiment
mode shortcut analysis
C1/C2 ablations
irregular-gap stress tests
calibration
event-level warning lead time
false alarms/time
physical end-to-end integration
honest synthetic/real separation
```

------------------------------------------------------------------------

# 175. C3 Definition of Done --- Data

-   [ ] Existing datasets audited
-   [ ] Target provenance documented
-   [ ] Leakage-risk fields removed
-   [ ] Ground-truth/event specification written
-   [ ] Event/scenario groups defined
-   [ ] Split frozen before window generation
-   [ ] Sequence manifest implemented
-   [ ] Δt/masks generated
-   [ ] Censoring handled
-   [ ] Synthetic/physical/external origins separated
-   [ ] Dataset manifest generated

------------------------------------------------------------------------

# 176. C3 Definition of Done --- Baselines

-   [ ] Simple persistence/rule baseline
-   [ ] Logistic regression baseline
-   [ ] Boosted-tree baseline
-   [ ] Mode-only baseline
-   [ ] Standard GRU baseline
-   [ ] Optional LSTM if justified

------------------------------------------------------------------------

# 177. C3 Definition of Done --- Proposed Modeling

-   [ ] Time-Aware GRU implemented/evaluated
-   [ ] GRU-D implemented/evaluated
-   [ ] Architecture comparison fair
-   [ ] Hyperparameters recorded
-   [ ] Multiple seeds where feasible
-   [ ] Final model selected by documented criteria
-   [ ] Probability calibration evaluated

------------------------------------------------------------------------

# 178. C3 Definition of Done --- Research

-   [ ] Sensors → +History ablation
-   [ ] +Δt ablation
-   [ ] +Mode ablation
-   [ ] mode-only shortcut test
-   [ ] +C1 ablation
-   [ ] +C2 ablation
-   [ ] long-gap stress test
-   [ ] missing-sensor stress test
-   [ ] mode-transition stress test
-   [ ] stale-reading stress test
-   [ ] recovered-data stress test
-   [ ] event-level recall measured
-   [ ] false alarms/time measured
-   [ ] warning lead time measured
-   [ ] calibration measured
-   [ ] limitations documented

------------------------------------------------------------------------

# 179. C3 Definition of Done --- Integration

-   [ ] Golden Timeline query implemented
-   [ ] runtime sequence builder implemented
-   [ ] C1 metadata integrated
-   [ ] C2 provenance integrated
-   [ ] model registry integration complete
-   [ ] forecast persisted
-   [ ] input manifest persisted/reconstructable
-   [ ] Decision Engine contract validated
-   [ ] mode transition test passes
-   [ ] hardware-in-the-loop pipeline passes
-   [ ] inference latency measured

------------------------------------------------------------------------

# 180. C3 Definition of Done --- Controlled Retraining

-   [ ] candidate dataset versioning implemented
-   [ ] retraining command reproducible
-   [ ] current-vs-candidate evaluation implemented
-   [ ] promotion criteria documented
-   [ ] rollback possible
-   [ ] no self-labeling
-   [ ] no automatic uncontrolled production updates

------------------------------------------------------------------------

# 181. Rules for the C3 Developer's AI Assistant

The C3 developer may paste this guide into another AI development chat.

That assistant must obey:

> **Do not redesign GeoNex shared architecture, database semantics,
> Golden Timeline, operating modes, sampling-policy contract, C1/C2/C4
> responsibilities, or Decision Engine boundary. Implement C3 within
> Documents 00--07. If a shared contract is insufficient, propose a
> versioned change for team review rather than silently changing it.**

Additionally:

-   never random-split overlapping temporal windows;
-   never use future data in a feature;
-   never treat generated risk probability as independent ground truth;
-   never use recommended mode as an ordinary C3 target/input without
    provenance;
-   never hide synthetic origin;
-   never assume equal timestep duration;
-   never erase missingness/recovery provenance;
-   never call uncontrolled online retraining "self-learning";
-   always compare against strong simpler baselines.

------------------------------------------------------------------------

# 182. Recommended C3 Implementation Order

``` text
1. Audit all existing C3 datasets/generators
2. Freeze target/event semantics
3. Remove leakage-risk fields
4. Define event/scenario grouping
5. Freeze train/validation/test split
6. Implement Golden Timeline snapshot builder
7. Implement sequence manifest
8. Implement Δt/missingness/provenance features
9. Implement snapshot/simple baseline
10. Implement logistic regression
11. Implement boosted-tree baseline
12. Implement mode-only baseline
13. Implement standard GRU
14. Run Sensors → +History
15. Add/test Δt
16. Add/test Mode
17. Implement Time-Aware GRU
18. Implement GRU-D
19. Generate leakage-safe C1 features
20. Run +C1 ablation
21. Generate leakage-safe C2 features
22. Run +C2 ablation
23. Run gap/missingness/mode stress tests
24. Evaluate calibration
25. Evaluate event recall / false alarms / lead time
26. Freeze approved model
27. Build runtime inference service
28. Integrate Decision Engine
29. Implement controlled retraining pipeline
30. Run hardware-in-the-loop evaluation
31. Generate thesis/paper evidence
```

------------------------------------------------------------------------

# 183. First Coding Milestone

Before advanced neural modeling, produce:

``` text
C3_DATASET_AUDIT.md
+
C3_TARGET_SPECIFICATION.md
+
frozen event/scenario split
+
sequence manifest builder
+
leakage tests
+
simple baseline
+
boosted-tree baseline
```

Only then begin GRU/time-aware architecture work.

------------------------------------------------------------------------

# 184. Immediate Existing-Data Questions to Resolve

For every current C3 CSV:

1.  How exactly was `target_landslide_within_horizon` generated?
2.  Is `risk_probability` derived from the same generator formula?
3.  Is `risk_level` derived from `risk_probability`?
4.  Is `recommended_mode` derived from risk?
5.  Are timestamps genuine sequential timestamps?
6.  Can rows from one storm/event cross the current split?
7.  Are rolling features causal?
8.  Are neighbour features computed using future values?
9.  What does `estimated_input_pct` exactly mean?
10. What does `mean_repair_confidence` exactly mean?
11. Are C1/C2 values true runtime-like predictions or synthetic ground
    truth?
12. Does the dataset contain post-event rows?
13. Is there adequate future coverage for each horizon?

Until these are answered, extremely high model scores should not be
treated as final evidence.

------------------------------------------------------------------------

# 185. Recommended Experimental Story

The cleanest final experimental story is:

``` text
Experiment 1
Can current sensors predict future event risk?

Experiment 2
Does temporal history help?

Experiment 3
Does explicit Δt help when sampling is irregular?

Experiment 4
Does operating mode add useful context beyond Δt?

Experiment 5
Does measurement credibility from C1 improve robustness?

Experiment 6
Does recovery provenance from C2 improve robustness?

Experiment 7
Does Time-Aware GRU / GRU-D outperform standard GRU
under variable-rate and missing-data stress?

Experiment 8
Are probabilities calibrated and warnings early enough?

Experiment 9
What resource/forecast trade-off results from
adaptive sampling compared with always-high-rate monitoring?
```

This tells one coherent research story instead of presenting
disconnected model scores.

------------------------------------------------------------------------

# 186. Component Success in One Sentence

> **C3 succeeds when GeoNex can demonstrate, on leakage-safe held-out
> temporal events, that explicitly understanding when observations
> occurred and how trustworthy/recovered they are produces useful,
> calibrated future-risk forecasts under adaptive variable-rate sensing,
> with measurable warning lead time and robustness to missing or
> irregular data.**

------------------------------------------------------------------------

# 187. Decisions Frozen by Document 07

1.  C3 is a future-risk forecasting component.
2.  C3 and the Decision Engine remain separate.
3.  C3's principal runtime source is the Golden Timeline.
4.  The baseline primary target is an independently derived
    event-within-horizon label.
5.  `risk_probability` is excluded as an ordinary input by default.
6.  `risk_level` requires provenance analysis and is not assumed to be
    independent ground truth.
7.  `recommended_mode` belongs to downstream policy by default.
8.  Time-to-danger is deferred unless event timing/censoring supports
    it.
9.  History windows are time-based conceptually.
10. Actual elapsed time Δt must be preserved.
11. Missingness masks/value age are explicit where relevant.
12. Operating mode is contextual and must be tested for circular
    shortcut behaviour.
13. A mode-only baseline is mandatory.
14. C1 and C2 features must be generated leakage-safely.
15. C2 recovery provenance is retained rather than hiding reconstructed
    inputs.
16. Event/scenario-aware splitting occurs before overlapping window
    generation.
17. Synthetic, physical-demo and external evidence are reported
    separately.
18. Strong tabular and standard GRU baselines are mandatory.
19. Time-Aware GRU and GRU-D are candidate proposed architectures, not
    predetermined winners.
20. The Sensors → +History → +Δt → +Mode → +C1 → +C2 ablation is
    mandatory.
21. Probability calibration is part of evaluation.
22. Event-level recall, false alarms/time and warning lead time are
    required.
23. Irregular-gap, missing-sensor, stale-reading and mode-transition
    stress tests are required.
24. C3 does not directly control sampling/mode.
25. Controlled cumulative retraining requires evaluate/promote/rollback.
26. C3 cannot use its own predictions as ground truth.
27. Physical prototype integration and real-world predictive validation
    are distinct claims.

------------------------------------------------------------------------

# 188. Decisions Intentionally Deferred

Still experimental:

``` text
exact forecast horizons
exact history-window duration
exact forecast trigger frequency
final target-event source
final feature subset
exact neighbour representation
exact mode encoding
exact C1/C2 feature representation
final missingness strategy
final architecture
final hidden dimensions/layers
final loss
final class weighting
final calibration method
final operating threshold
exact retraining trigger
exact promotion thresholds
```

These must be frozen from evidence, not convenience.

------------------------------------------------------------------------

# 189. Next Component Guide

The next document is:

``` text
08_C4_DEVELOPMENT_GUIDE.md
```

It will define:

``` text
device identity
registration
authentication/integrity
freshness and replay protection
authorized C2 replay
deterministic security gate
behavioural telemetry features
supervised/unsupervised anomaly models
trust fusion
quarantine
attack/test scenarios
C4 ablations
C1/C2 integration
security audit evidence
runtime performance
```

------------------------------------------------------------------------

# Document 07 Status

**`07_C3_DEVELOPMENT_GUIDE.md` --- C3 IMPLEMENTATION BASELINE READY**

The intended C3 contribution is deliberately stronger than simply
applying a recurrent neural network to a synthetic CSV. Its value must
be demonstrated through **leakage-safe temporal forecasting, explicit
irregular-time representation, mode-shortcut analysis, upstream
quality/provenance integration, calibrated probabilities, event-level
warning performance, and controlled comparison against strong simpler
baselines.**
