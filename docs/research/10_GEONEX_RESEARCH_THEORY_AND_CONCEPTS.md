# 10_GEONEX_RESEARCH_THEORY_AND_CONCEPTS.md

**Project:** GeoNex --- Smart Landslide Early Warning Prediction System
using IoT, Edge AI and Risk Analytics\
**Document:** Research Theory and Concepts\
**Status:** Technical/Theoretical Baseline\
**Depends on:** Documents 00--09\
**Purpose:** Build the shared scientific and engineering understanding
required to implement, explain and defend GeoNex without confusing
physical landslide processes, sensor behaviour, machine-learning
concepts, system reliability and cybersecurity.

> **Important evidence boundary:** This document is a project-oriented
> theory guide. It explains the concepts required by the approved GeoNex
> architecture. It is not itself the final literature review and does
> not substitute for peer-reviewed citations. Geological thresholds,
> sensor-response claims and literature-derived statements used in the
> thesis/paper must later be supported by appropriate sources and, where
> relevant, local calibration.

------------------------------------------------------------------------

# 1. GeoNex as an Uncertainty-Management System

GeoNex is more than a collection of IoT sensors and classifiers.

The system manages four different uncertainties:

``` text
C4 — SOURCE UNCERTAINTY
Can the source/transmission be trusted?

C1 — MEASUREMENT UNCERTAINTY
Can the environmental measurement be trusted?

C2 — AVAILABILITY/FAILURE UNCERTAINTY
Why is expected information missing and how can it be recovered?

C3 — FUTURE-STATE UNCERTAINTY
Given trustworthy history, what may happen next?
```

The Decision Engine then converts this evidence into operational
behaviour.

------------------------------------------------------------------------

# 2. End-to-End Reasoning Chain

``` text
Physical slope/environment
        ↓
Sensors
        ↓
Telemetry
        ↓
C4 source trust
        ↓
C1 measurement credibility
        ↓
C2 diagnosis/recovery when information is missing
        ↓
Golden Timeline
        ↓
C3 future-risk forecasting
        ↓
Decision Engine
        ↓
Operating mode / sampling / warning
```

Each layer answers a different question.

------------------------------------------------------------------------

# 3. Landslide Early Warning Is Not Landslide Certainty

An early-warning system works under uncertainty.

It observes indicators that may precede or accompany instability and
estimates risk.

Therefore GeoNex should communicate:

``` text
risk
probability
warning state
evidence
```

rather than claim:

``` text
certainty of a future landslide
```

unless the evidence truly supports such certainty, which is generally
not the role of a predictive model.

------------------------------------------------------------------------

# 4. Landslide Precursors

A **precursor** is an observable change that may occur before or during
slope instability.

Candidate precursor families relevant to GeoNex include:

``` text
rainfall
soil moisture
ground/slope movement
tilt
vibration
pressure/contact response
environmental context
```

Not every change is a landslide precursor, and not every landslide
produces the same pattern.

------------------------------------------------------------------------

# 5. Why Rainfall Matters

Rainfall can alter slope conditions through processes such as:

``` text
infiltration
increasing soil water content
changing pore-water conditions
reducing effective resistance to movement
increasing material weight
```

The exact relationship depends on geology, soil, drainage, slope
geometry and antecedent conditions.

Therefore GeoNex should not assume one universal rainfall threshold.

------------------------------------------------------------------------

# 6. Antecedent Rainfall

Current rainfall alone may not describe the state of the slope.

Example:

``` text
5 mm now
```

after prolonged dry weather may differ from:

``` text
5 mm now
```

after many hours/days of sustained rainfall.

This motivates historical rainfall summaries such as:

``` text
recent accumulation
short-term accumulation
longer antecedent accumulation
trend/intensity
```

Exact windows must be scientifically justified.

------------------------------------------------------------------------

# 7. Soil Moisture

Soil-moisture sensors provide an indirect indication of water content
around the sensing location.

Important limitations include:

``` text
sensor calibration
soil composition
temperature
installation contact
depth
local heterogeneity
sensor drift
```

Therefore raw sensor output should not automatically be treated as
universally comparable physical volumetric water content unless properly
calibrated.

------------------------------------------------------------------------

# 8. Soil Moisture as a Temporal Signal

C3 is often more interested in:

``` text
level
+
trend
+
rate of change
+
relationship to rainfall
```

than in one isolated value.

For example:

``` text
stable high moisture
```

and:

``` text
rapidly increasing moisture following rainfall
```

may carry different temporal information.

------------------------------------------------------------------------

# 9. Tilt and Movement

An inertial sensor can provide orientation/motion information.

Potential features include:

``` text
tilt angle
change in tilt
tilt rate
acceleration summaries
vibration statistics
```

But an MPU-type IMU mounted inside a prototype pipe does not
automatically equal a direct measurement of full slope displacement.

Interpret the signal according to actual mechanical coupling and
calibration.

------------------------------------------------------------------------

# 10. Vibration

Vibration can arise from many causes:

``` text
ground movement
human activity
equipment
transport
sensor handling
environmental noise
```

Therefore vibration is contextual evidence rather than a unique
landslide identifier.

------------------------------------------------------------------------

# 11. FSR402 Interpretation

A Force Sensitive Resistor changes electrical resistance in response to
applied force/contact pressure.

Without a validated mechanical calibration, GeoNex should describe
FSR-derived data as:

``` text
FSR response
raw ADC
voltage
resistance-related response
relative pressure/contact trend
```

rather than claiming precise geological stress or force.

------------------------------------------------------------------------

# 12. Temperature and Humidity

DHT22/DS18B20-type measurements can provide environmental/device
context.

Possible uses:

``` text
sensor compensation
environment characterization
fault diagnosis
experimental context
```

Their inclusion in a landslide predictor must be justified by evidence
rather than hardware availability alone.

------------------------------------------------------------------------

# 13. Rainfall Measurement

The Centralized Sensor Hub rainfall mechanism uses a physical collection
arrangement.

The system must distinguish:

``` text
raw load/level measurements
```

from:

``` text
calibrated rainfall quantity
```

A calibration relationship is required before claiming physical rainfall
units.

------------------------------------------------------------------------

# 14. Calibration

Calibration maps sensor output to a meaningful measurement.

Conceptually:

``` text
raw electrical response
        ↓
calibration function
        ↓
physical/standardized value
```

Calibration metadata should include:

``` text
sensor
procedure
date
coefficients
units
valid range
version
```

------------------------------------------------------------------------

# 15. Accuracy vs Precision

**Accuracy**:

> closeness to the true/reference value.

**Precision**:

> repeatability of measurements.

A sensor may be:

``` text
precise but inaccurate
```

if it repeatedly reports the same biased value.

------------------------------------------------------------------------

# 16. Resolution

Resolution is the smallest change the sensing system can meaningfully
distinguish.

High numeric precision in software does not imply high physical sensor
resolution.

------------------------------------------------------------------------

# 17. Drift

Sensor drift is gradual change in output over time unrelated to the
actual environmental variable.

This is one reason C1 cannot rely only on static physical ranges.

------------------------------------------------------------------------

# 18. Noise

Noise is unwanted variation in measurement.

Potential sources:

``` text
electrical noise
mechanical vibration
RF interference
ADC variation
sensor instability
environmental variation
```

Noise should not automatically be labeled as hardware failure.

------------------------------------------------------------------------

# 19. Outlier

An outlier is a value substantially different from surrounding
observations.

But:

``` text
outlier ≠ error
```

A genuine hazard event can produce an extreme value.

This distinction is fundamental to C1.

------------------------------------------------------------------------

# 20. Anomaly

An anomaly is an observation/pattern that deviates from expected
behaviour.

It can represent:

``` text
sensor fault
communication problem
unusual legitimate event
attack
rare operating state
```

The meaning depends on context.

------------------------------------------------------------------------

# 21. C1 Theory --- Measurement Credibility

C1 estimates whether a measurement should be trusted as environmental
evidence.

It uses three broad forms of consistency:

``` text
temporal consistency
spatial consistency
environmental/context consistency
```

------------------------------------------------------------------------

# 22. Temporal Consistency

Question:

> Is the measurement plausible relative to the sensor's recent history?

Possible evidence:

``` text
previous value
rate of change
rolling statistics
stuck-value duration
```

But a rapid change can still be genuine.

------------------------------------------------------------------------

# 23. Spatial Consistency

Question:

> Do nearby sensors observe compatible environmental behaviour?

If one soil sensor jumps while neighbouring sensors remain stable,
suspicion may increase.

If many independent sensors change coherently, a genuine event becomes
more plausible.

------------------------------------------------------------------------

# 24. Spatial Correlation Is Not Equality

Neighbouring sensors do not need identical values.

Different:

``` text
depth
soil
micro-location
calibration
```

can create legitimate differences.

C1 should model agreement/trend context, not require equality.

------------------------------------------------------------------------

# 25. Environmental Context

Example:

``` text
high soil moisture
+
heavy rainfall
+
neighbour moisture increase
```

may support:

``` text
VALID_EVENT
```

whereas the same soil value under dry/stable context may be more
suspicious.

This is the rationale for rainfall regime-aware credibility.

------------------------------------------------------------------------

# 26. Context-Aware Anomaly Detection

Traditional anomaly detection often asks:

``` text
Is x unusual?
```

Context-aware detection asks:

``` text
Is x unusual given context c?
```

Formally:

``` text
P(anomaly | x, context)
```

can differ substantially from:

``` text
P(anomaly | x)
```

------------------------------------------------------------------------

# 27. Classification

Supervised classification learns a mapping:

``` text
f(X) → class
```

For C1:

``` text
X = measurement + history + neighbours + rainfall context
```

and:

``` text
class ∈ {CLEAN, ANOMALY, VALID_EVENT}
```

------------------------------------------------------------------------

# 28. Decision Tree

A decision tree recursively splits the feature space.

Conceptual rule:

``` text
if rainfall high:
    if neighbours increasing:
        VALID_EVENT
    else:
        ...
```

Trees are intuitive but a single deep tree can overfit.

------------------------------------------------------------------------

# 29. Random Forest

Random Forest trains many decision trees using randomized data/features
and aggregates them.

Advantages:

``` text
nonlinear
robust baseline
handles feature interactions
moderate preprocessing
```

It is valuable for C1/C2/C4 baselines.

------------------------------------------------------------------------

# 30. Gradient Boosting

Gradient-boosted trees build trees sequentially, each improving errors
made by the current ensemble.

Popular implementations:

``` text
XGBoost
LightGBM
```

They are powerful for structured/tabular data.

------------------------------------------------------------------------

# 31. Why Trees Fit Contextual Sensor Problems

A contextual relationship may be conditional:

``` text
IF rainfall is high
AND neighbour trend agrees
THEN extreme moisture may be valid
```

Tree ensembles naturally model such nonlinear interactions.

------------------------------------------------------------------------

# 32. Feature Importance

Feature importance estimates how much a model relies on variables.

It does not automatically show:

``` text
causality
```

A feature can be predictive because it correlates with another process.

------------------------------------------------------------------------

# 33. SHAP

SHAP assigns feature contributions to a model prediction relative to a
baseline expectation.

Useful questions:

``` text
Why was this measurement classified VALID_EVENT?
Why was this failure classified communication_failure?
```

SHAP explains model behaviour, not physical causation.

------------------------------------------------------------------------

# 34. C2 Theory --- Expected Observations

A telemetry stream is only "silent" relative to an expectation.

If a device should report every:

``` text
T seconds
```

then the expected next report is approximately:

``` text
t_expected = t_last + T
```

GeoNex complicates this because `T` depends on operating mode/policy.

------------------------------------------------------------------------

# 35. Mode-Aware Silence

Correct concept:

``` text
expected interval = policy(device, sensor, mode)
```

Then:

``` text
deadline = expected_next_report + grace
```

A fixed global timeout would create false failures under variable-rate
sensing.

------------------------------------------------------------------------

# 36. Missing Data Mechanisms

Statistical literature often distinguishes:

``` text
MCAR — Missing Completely At Random
MAR  — Missing At Random conditional on observed data
MNAR — Missing Not At Random
```

GeoNex operational failures do not necessarily satisfy these assumptions
neatly.

The important engineering point is:

> **Why the data is missing can itself contain information.**

------------------------------------------------------------------------

# 37. Informative Missingness

Suppose several sensors in one zone simultaneously disappear.

The absence may indicate:

``` text
network failure
hub failure
power failure
physical zone disturbance
```

Therefore blindly imputing the missing values can destroy important
diagnostic information.

------------------------------------------------------------------------

# 38. Fault Detection vs Fault Diagnosis

**Fault detection** asks:

``` text
Is something wrong?
```

**Fault diagnosis** asks:

``` text
What is wrong?
```

C2 performs both:

``` text
silence detection
→ failure diagnosis
```

------------------------------------------------------------------------

# 39. Fault Isolation

Fault isolation identifies the affected subsystem.

Example:

``` text
one sensor missing
vs
entire pipe missing
vs
hub missing
vs
multiple zone devices missing
```

Topology matters.

------------------------------------------------------------------------

# 40. Redundancy

Redundancy means multiple resources can provide overlapping capability.

GeoNex uses:

``` text
primary sensing
backup sensing
neighbour context
local storage/replay
```

Different redundancy types protect against different failures.

------------------------------------------------------------------------

# 41. Independent Backup Value

A backup is most useful diagnostically when it is sufficiently
independent of the primary failure path.

If both primary and backup share every dependency, one failure may
remove both.

GeoNex's Backup Pipe is intended to provide additional independent
verification/recovery evidence.

------------------------------------------------------------------------

# 42. Recovery Provenance

Recovered data must state where it came from.

Examples:

``` text
DIRECT
LATE_ORIGINAL
BACKUP
FUSED
DERIVED
```

A recovered value must never silently masquerade as an original direct
observation.

------------------------------------------------------------------------

# 43. Data Imputation

Imputation estimates a missing value.

Methods can include:

``` text
forward fill
mean/median
interpolation
neighbour-based estimate
model-based estimate
```

But imputation introduces uncertainty.

C2 therefore couples recovery with provenance/confidence.

------------------------------------------------------------------------

# 44. Late Original vs Estimated Value

If an original stored reading later arrives from SD replay:

``` text
LATE_ORIGINAL
```

is fundamentally different from:

``` text
estimated neighbour-fused value
```

C3 should be allowed to know this difference.

------------------------------------------------------------------------

# 45. Diagnostic Classification

C2 can learn:

``` text
P(failure_type | evidence)
```

where evidence includes:

``` text
silence pattern
device health
network state
backup response
neighbour state
```

This is why RF/XGBoost are appropriate candidates.

------------------------------------------------------------------------

# 46. Deterministic Recovery Policy

Some recovery actions are safety/availability rules.

Example:

``` text
primary sensor confirmed failed
+
backup available
→ activate/use backup
```

There may be no reason to learn this mapping with ML.

------------------------------------------------------------------------

# 47. C3 Theory --- Forecasting

Forecasting estimates a future variable/event from past and current
evidence.

C3 differs from classification of current state.

At forecast origin `t`:

``` text
input = evidence ≤ t
target = event in (t, t+H]
```

------------------------------------------------------------------------

# 48. Time Series

A time series is an ordered set of observations indexed by time.

A multivariate time series contains multiple variables:

``` text
rainfall
soil moisture
tilt
vibration
...
```

------------------------------------------------------------------------

# 49. Regular Time Series

Regular sampling:

``` text
10:00
10:05
10:10
10:15
```

has constant interval:

``` text
Δt = 5 min
```

------------------------------------------------------------------------

# 50. Irregular Time Series

Irregular sampling:

``` text
10:00
10:10
10:20
10:21
10:22
```

has variable `Δt`.

GeoNex intentionally produces this behaviour because sampling/reporting
increases with risk.

------------------------------------------------------------------------

# 51. Why Sequence Position Is Not Time

A standard sequence model sees:

``` text
step 1
step 2
step 3
```

But without explicit timing it may not know whether:

``` text
step1 → step2 = 10 seconds
```

or:

``` text
step1 → step2 = 1 hour
```

Hence C3 preserves elapsed time.

------------------------------------------------------------------------

# 52. Delta Time

``` text
Δt_i = t_i - t_(i-1)
```

This tells C3 how much physical time elapsed between observations.

------------------------------------------------------------------------

# 53. Rate of Change

For value `x`:

``` text
rate ≈ (x_i - x_(i-1)) / Δt
```

The same numeric change can imply very different dynamics depending on
`Δt`.

------------------------------------------------------------------------

# 54. Historical Window

For forecast time `t`:

``` text
history = [t-W, t]
```

where `W` is a configured duration.

The model predicts beyond `t`.

------------------------------------------------------------------------

# 55. Forecast Horizon

``` text
H
```

defines how far into the future the target looks.

Example conceptually:

``` text
event within next H minutes?
```

Different horizons correspond to different warning questions.

------------------------------------------------------------------------

# 56. Multi-Horizon Forecasting

A system may predict:

``` text
near horizon
medium horizon
longer horizon
```

Longer horizons may provide earlier warning but are generally more
uncertain.

------------------------------------------------------------------------

# 57. Recurrent Neural Network

An RNN processes sequence steps while maintaining a hidden state:

``` text
h_t = f(x_t, h_(t-1))
```

The hidden state summarizes previous sequence information.

------------------------------------------------------------------------

# 58. Vanishing Gradient

Basic RNNs can struggle to learn long dependencies because gradients may
become very small through many recurrent steps.

This motivated gated recurrent architectures such as LSTM and GRU.

------------------------------------------------------------------------

# 59. LSTM

Long Short-Term Memory uses gates and a memory cell to control:

``` text
what to remember
what to forget
what to output
```

It can model long temporal dependencies.

------------------------------------------------------------------------

# 60. GRU

Gated Recurrent Unit simplifies the LSTM structure.

Conceptually it uses gates such as:

``` text
update gate
reset gate
```

to control hidden-state memory.

GRU often offers a good balance of temporal capacity and computational
simplicity.

------------------------------------------------------------------------

# 61. Standard GRU Limitation for GeoNex

A standard GRU processes ordered steps but does not inherently know the
real elapsed duration between them.

Therefore:

``` text
GRU + explicit Δt
```

or a time-aware architecture is important to investigate.

------------------------------------------------------------------------

# 62. Time-Aware Recurrence

A time-aware recurrent model changes how historical state is interpreted
based on elapsed time.

Conceptually:

``` text
older state influence
↓
as Δt grows
```

according to a learned/designed mechanism.

Exact architecture must follow the implementation selected in C3
experiments.

------------------------------------------------------------------------

# 63. Missingness Mask

For variable `j` at time `t`:

``` text
m_t,j = 1  if observed
m_t,j = 0  if missing
```

The model can then distinguish:

``` text
actual zero
```

from:

``` text
missing value represented numerically
```

------------------------------------------------------------------------

# 64. Time Since Last Observation

For each feature:

``` text
δ_t,j
```

can represent elapsed time since variable `j` was last observed.

This is especially useful when sensors update asynchronously.

------------------------------------------------------------------------

# 65. GRU-D Concept

GRU-D extends recurrent modeling for missing/irregular clinical-style
time series by incorporating:

``` text
missingness masks
time intervals
decay
```

The conceptual relevance to GeoNex is strong because C3 also encounters
missing and irregular observations.

The exact implementation must be verified against the selected
architecture/reference before coding.

------------------------------------------------------------------------

# 66. Decay Concept

A stale observation may become less informative as time passes.

Conceptually:

``` text
influence = decay(age)
```

where older values receive less weight.

The decay may be learned rather than manually fixed.

------------------------------------------------------------------------

# 67. Why Missingness Can Be Predictive

If a sensor disappears during severe conditions, missingness itself may
correlate with system/environment state.

However this can also create dangerous shortcuts.

C3 therefore uses provenance carefully and tests robustness.

------------------------------------------------------------------------

# 68. Padding

Neural batches often require equal tensor sizes.

Shorter sequences may be padded.

The model must use masks so:

``` text
padding ≠ real zero measurement
```

------------------------------------------------------------------------

# 69. Sequence Leakage

Two overlapping windows may share nearly all observations.

Example:

``` text
A: 10:00–11:00
B: 10:01–11:01
```

Randomly assigning A to train and B to test leaks information.

Split event/time blocks first.

------------------------------------------------------------------------

# 70. Future Leakage

At forecast time `t`, no feature may depend on:

``` text
observations after t
labels after t except target construction
future C1/C2 assessments unavailable at t
```

This is one of the most important forecasting rules.

------------------------------------------------------------------------

# 71. As-Of Semantics

Suppose an observation occurred at:

``` text
10:00
```

but arrived at:

``` text
10:20
```

A forecast generated at:

``` text
10:10
```

could not have used it.

Runtime-equivalent training must respect information availability, not
only observation timestamp.

------------------------------------------------------------------------

# 72. Operating Mode

GeoNex modes:

``` text
DEEP_SLEEP
IDLE
RISK
WARNING
EMERGENCY
```

control sensing/reporting intensity.

Mode is operational context, not geological truth.

------------------------------------------------------------------------

# 73. Adaptive Sampling

Adaptive sampling changes measurement/reporting effort according to
current system state.

Conceptually:

``` text
low concern
→ sparse monitoring

increasing concern
→ denser monitoring
```

Goals include:

``` text
resource efficiency
lower radio usage
faster response during risk
```

------------------------------------------------------------------------

# 74. Acquisition vs Reporting Rate

**Acquisition rate**:

``` text
how often sensor is read
```

**Aggregation rate/window**:

``` text
how local samples are summarized
```

**Reporting interval**:

``` text
how often information is transmitted
```

These are different.

------------------------------------------------------------------------

# 75. Why Adaptive Sampling Creates Statistical Bias

The system samples more frequently when it already believes conditions
are risky.

Therefore high-density data is correlated with risk state.

A model may learn:

``` text
many observations = danger
```

instead of environmental dynamics.

This is why C3 explicitly models mode/Δt and tests a mode-only baseline.

------------------------------------------------------------------------

# 76. Feedback Loop

Conceptually:

``` text
risk evidence
→ higher mode
→ more samples
→ C3 sees denser data
→ forecast changes
→ mode changes again
```

This closed loop must be designed carefully to avoid oscillation and
circular reasoning.

------------------------------------------------------------------------

# 77. Hysteresis

Hysteresis uses different conditions for escalation and de-escalation.

Example concept:

``` text
escalate at higher threshold
de-escalate only after lower threshold/persistence
```

This reduces rapid mode oscillation.

Exact thresholds are Decision Engine configuration.

------------------------------------------------------------------------

# 78. Minimum Dwell Time

A minimum dwell time keeps a mode active for a minimum period unless a
safety override occurs.

This prevents:

``` text
RISK → WARNING → RISK → WARNING
```

from noise around a boundary.

------------------------------------------------------------------------

# 79. C3 Does Not Implement Hysteresis

C3 produces risk evidence.

The Decision Engine applies:

``` text
thresholds
persistence
hysteresis
mode transition policy
```

This preserves separation between prediction and action.

------------------------------------------------------------------------

# 80. Classification Probability

A classifier can output:

``` text
P(y = class | X)
```

or an approximation learned from data.

Raw neural/tree scores are not automatically well-calibrated
probabilities.

------------------------------------------------------------------------

# 81. Calibration

A model is well calibrated when:

``` text
among predictions near 0.8,
approximately 80% of comparable cases experience the event
```

under the evaluated distribution.

Calibration is crucial for C3 risk probabilities.

------------------------------------------------------------------------

# 82. Brier Score

For binary outcome `y ∈ {0,1}` and predicted probability `p`:

``` text
Brier = mean((p - y)^2)
```

Lower is better.

It evaluates probability accuracy, not only classification threshold
performance.

------------------------------------------------------------------------

# 83. Reliability Diagram

Group predictions into probability ranges and compare:

``` text
average predicted probability
vs
observed event frequency
```

This visually reveals overconfidence/underconfidence.

------------------------------------------------------------------------

# 84. ROC Curve

ROC evaluates:

``` text
true positive rate
vs
false positive rate
```

across thresholds.

ROC-AUC summarizes ranking performance.

------------------------------------------------------------------------

# 85. Precision-Recall Curve

Precision:

``` text
TP / (TP + FP)
```

Recall:

``` text
TP / (TP + FN)
```

PR curves are especially informative when the positive event is rare.

------------------------------------------------------------------------

# 86. F1 Score

``` text
F1 = 2 * precision * recall / (precision + recall)
```

It balances precision and recall.

For multiclass tasks, macro-F1 treats classes more equally than raw
accuracy.

------------------------------------------------------------------------

# 87. Specificity

``` text
TN / (TN + FP)
```

Measures ability to correctly reject negatives.

------------------------------------------------------------------------

# 88. Confusion Matrix

For binary classification:

``` text
             Predicted
             +       -
Actual +     TP      FN
Actual -     FP      TN
```

For multiclass tasks, the matrix reveals which classes are confused.

------------------------------------------------------------------------

# 89. False Alarm Rate in Early Warning

A system can have good classification metrics yet produce too many
operational warnings.

Therefore measure:

``` text
false alarms per day/time unit
```

where possible.

------------------------------------------------------------------------

# 90. Warning Lead Time

``` text
lead time =
event onset - first qualifying warning
```

A correct forecast is more useful if it provides enough time for
response.

------------------------------------------------------------------------

# 91. Event-Level Recall

Instead of counting every window independently:

``` text
How many actual events received at least one useful warning before onset?
```

This is an important C3 metric.

------------------------------------------------------------------------

# 92. Class Imbalance

Hazard/failure/security events may be much rarer than normal data.

A model can achieve high accuracy by predicting the majority class.

Therefore use:

``` text
class-specific recall
macro-F1
PR-AUC
event metrics
```

as appropriate.

------------------------------------------------------------------------

# 93. Data Splitting

Purpose:

``` text
TRAIN → learn parameters
VALIDATION → choose model/hyperparameters
TEST → final estimate
```

The test set must remain unseen during development.

------------------------------------------------------------------------

# 94. Group-Aware Splitting

Rows from one event/scenario/device episode are correlated.

Group them together.

Examples:

``` text
storm event
failure episode
attack run
temporal block
```

------------------------------------------------------------------------

# 95. Cross-Validation

Cross-validation repeatedly trains/evaluates across different
partitions.

For GeoNex, ordinary random K-fold may be invalid.

Use:

``` text
group-aware
time-aware
```

variants where appropriate.

------------------------------------------------------------------------

# 96. Overfitting

A model overfits when it learns training-specific patterns that do not
generalize.

Signs:

``` text
very high training score
much lower validation/test score
unstable performance
memorization of IDs/scenarios
```

------------------------------------------------------------------------

# 97. Underfitting

A model underfits when it is too limited or insufficiently trained to
capture relevant structure.

Both training and validation performance may remain poor.

------------------------------------------------------------------------

# 98. Bias--Variance Trade-Off

Simple models may have higher bias but lower variance.

Highly flexible models may reduce bias but increase
variance/overfitting.

Model selection balances this trade-off using held-out evidence.

------------------------------------------------------------------------

# 99. Regularization

Regularization discourages overly complex models.

Examples:

``` text
L1/L2 penalties
tree-depth limits
learning-rate control
dropout
early stopping
```

------------------------------------------------------------------------

# 100. Hyperparameters

Hyperparameters are settings chosen outside normal parameter learning.

Examples:

``` text
tree depth
learning rate
hidden size
dropout
batch size
history duration
```

They are selected using validation evidence.

------------------------------------------------------------------------

# 101. Training Parameters vs Hyperparameters

Model parameters are learned from data:

``` text
tree splits
weights
biases
```

Hyperparameters configure the learning process/model capacity.

------------------------------------------------------------------------

# 102. Loss Function

A loss function quantifies training error.

Examples:

``` text
cross-entropy
weighted cross-entropy
focal loss
```

Training minimizes loss, while research evaluation may use different
metrics.

------------------------------------------------------------------------

# 103. Focal Loss

Focal loss reduces emphasis on easy examples and focuses learning on
harder examples.

It may help imbalanced classification but should be experimentally
justified.

------------------------------------------------------------------------

# 104. Data Standardization

Common transformation:

``` text
z = (x - μ_train) / σ_train
```

Statistics must come from training data only.

------------------------------------------------------------------------

# 105. Robust Scaling

Robust scaling can use median/interquartile statistics and may be less
sensitive to extreme values.

However genuine extremes are important in GeoNex, so preprocessing must
not erase hazard information.

------------------------------------------------------------------------

# 106. C4 Theory --- Security Goals

Core security properties relevant to telemetry include:

``` text
authentication
integrity
freshness
authorization
provenance
availability
```

Confidentiality may also matter depending on the final communication
design.

------------------------------------------------------------------------

# 107. Authentication

Authentication answers:

> Is the sender/entity who it claims to be according to the implemented
> credential mechanism?

Authentication does not prove the sensor measurement itself is
physically correct.

------------------------------------------------------------------------

# 108. Integrity

Integrity answers:

> Has the protected message been altered without authorization?

A valid integrity check means protected content is unchanged under the
security mechanism.

It does not prove environmental truth.

------------------------------------------------------------------------

# 109. Confidentiality

Confidentiality prevents unauthorized parties from reading protected
information.

Encryption is commonly used.

GeoNex's exact confidentiality requirement/protocol remains part of the
security implementation design.

------------------------------------------------------------------------

# 110. Authorization

Authorization answers:

> Is this authenticated entity allowed to perform this action?

Example:

``` text
device is authenticated
```

does not automatically mean:

``` text
device may issue a mode command
```

------------------------------------------------------------------------

# 111. Freshness

Freshness establishes that a message is sufficiently
current/non-replayed under protocol rules.

Potential mechanisms:

``` text
nonce
counter
timestamp
session identifier
```

------------------------------------------------------------------------

# 112. Nonce

A nonce is a value intended for one-time/unique use within a security
protocol.

Reusing an expected-unique nonce can indicate replay or implementation
failure.

------------------------------------------------------------------------

# 113. Sequence Counter

A monotonically increasing counter can help detect:

``` text
duplicates
old messages
reordering
rollback
```

but legitimate reboot/session changes must be handled.

------------------------------------------------------------------------

# 114. Replay Attack

A replay attack resends previously valid information in an unauthorized
context.

Because the old packet may still contain valid historical data,
integrity alone is insufficient.

Freshness is required.

------------------------------------------------------------------------

# 115. C2 Authorized Historical Replay

GeoNex introduces a legitimate case where historical data is
intentionally retransmitted.

Therefore security must bind it to:

``` text
fresh authenticated recovery session/request
+
authorized historical range
```

while preserving the old observation timestamp.

------------------------------------------------------------------------

# 116. Message Authentication

Depending on the final protocol, integrity/authentication may use
mechanisms such as a message authentication code or digital signature.

The exact algorithm is not frozen here.

Never invent a custom cryptographic primitive.

------------------------------------------------------------------------

# 117. Device Attestation

Attestation broadly refers to evidence about the
identity/state/configuration of a device.

In GeoNex, the phrase must be used only for mechanisms actually
implemented.

Do not claim hardware-rooted remote attestation if the prototype only
verifies registration/firmware metadata.

------------------------------------------------------------------------

# 118. Provenance

Provenance records:

``` text
where data came from
how it was processed
what transformations occurred
which models/rules affected it
```

It is essential for auditability.

------------------------------------------------------------------------

# 119. Behavioural Security

Even an authenticated device can behave unusually.

Candidate evidence:

``` text
packet interval
RSSI/SNR profile
retry pattern
path
restart pattern
packet size
```

This motivates C4's behavioural layer.

------------------------------------------------------------------------

# 120. Behavioural Anomaly Detection

Learn:

``` text
expected normal behaviour
```

or:

``` text
patterns associated with trusted/suspicious/untrusted classes
```

Then identify deviations.

Behavioural anomaly does not automatically prove malicious intent.

------------------------------------------------------------------------

# 121. Isolation Forest Concept

Isolation Forest randomly partitions feature space.

Anomalous points tend to require fewer random splits to isolate.

It can work without labeled attack examples, making it useful as a C4
baseline.

------------------------------------------------------------------------

# 122. False Acceptance vs False Rejection

**False acceptance**:

``` text
untrusted telemetry accepted
```

**False rejection**:

``` text
legitimate telemetry rejected
```

Security and availability require balancing both, while hard security
failures remain non-negotiable.

------------------------------------------------------------------------

# 123. Edge Computing

Edge computing processes data near the physical data source rather than
depending entirely on remote cloud infrastructure.

GeoNex's Main Computing System can act as a local edge-site computer.

Benefits:

``` text
lower external-network dependence
local latency
local data retention
operation during internet outage
```

------------------------------------------------------------------------

# 124. Edge AI

Edge AI means AI inference/training-related processing occurs at or near
the edge.

GeoNex can perform:

``` text
C1–C4 inference
Decision Engine processing
database operations
```

locally on the Main Computing System.

This does not require neural models to run on each ESP32.

------------------------------------------------------------------------

# 125. Cloud vs Local Edge

A cloud-dependent warning system can be vulnerable to:

``` text
internet outage
WAN latency
remote service failure
```

A local architecture improves autonomy.

Cloud services may still support:

``` text
backup
dashboard
research synchronization
long-term analytics
```

if later implemented.

------------------------------------------------------------------------

# 126. LoRa Concept

LoRa is a long-range, low-data-rate radio technology suited to small
telemetry messages.

Important design constraints:

``` text
limited throughput
airtime
collisions
packet size
radio configuration
```

It is not appropriate for uncontrolled high-rate raw streaming from
every sensor.

------------------------------------------------------------------------

# 127. Why Local Aggregation Matters

High-frequency sensors such as IMUs can generate many samples.

Instead of transmitting every sample:

``` text
sample locally
→ compute summary
→ transmit compact feature packet
```

Examples:

``` text
mean
RMS
variance
maximum
peak
tilt estimate
```

This reduces radio load.

------------------------------------------------------------------------

# 128. Communication Reliability

Wireless delivery can fail because of:

``` text
interference
distance
obstacles
collision
power problems
radio faults
```

A missing packet is not automatically evidence of environmental damage.

This motivates C2 diagnosis.

------------------------------------------------------------------------

# 129. RSSI

Received Signal Strength Indicator reflects received radio power
according to the radio system.

It can change for many benign reasons.

Therefore C4 treats it as contextual behavioural evidence.

------------------------------------------------------------------------

# 130. SNR

Signal-to-noise ratio compares desired signal level to background noise.

Like RSSI, it can support communication diagnostics/security behaviour
but is not identity proof.

------------------------------------------------------------------------

# 131. Packet Loss

Packet loss is the proportion/count of expected packets not successfully
received.

Interpretation depends on:

``` text
expected reporting policy
network conditions
device health
```

------------------------------------------------------------------------

# 132. Main Black Box vs Main Computing System

The gateway electronics:

``` text
ESP32-S3 + LoRa/interface hardware
```

are not the same as:

``` text
Lenovo ThinkCentre Main Computing System
```

The gateway handles device communication.

The computer hosts heavier software/database/AI responsibilities.

------------------------------------------------------------------------

# 133. Database Theory --- Raw vs Derived

Raw data:

``` text
what was received/observed
```

Derived data:

``` text
what later processing calculated
```

Never overwrite raw evidence with a cleaned value.

------------------------------------------------------------------------

# 134. Immutable Raw Data

Immutability means the original record remains preserved.

Corrections are represented through:

``` text
new records
assessments
derived values
provenance
```

This supports reproducibility and audit.

------------------------------------------------------------------------

# 135. Operational Database vs ML Dataset

Operational DB:

``` text
supports live system state/history
```

ML dataset:

``` text
frozen research artifact built from selected DB evidence
```

They are not the same object.

------------------------------------------------------------------------

# 136. Dataset Versioning

A dataset version identifies:

``` text
source cutoff
schema
builder
filtering
labels
split
hash
```

Changing generator logic requires a new version.

------------------------------------------------------------------------

# 137. Golden Timeline

The Golden Timeline is the best provenance-aware environmental history
currently eligible for downstream reasoning.

It can include:

``` text
direct observation
late original
backup observation
approved reconstruction
```

with source metadata.

It does not mean every value is perfect.

------------------------------------------------------------------------

# 138. Runtime vs Retrospective Golden Timeline

Runtime:

``` text
what was known at time t
```

Retrospective:

``` text
what became known later after delayed/recovered data arrived
```

C3 historical evaluation must preserve the runtime distinction.

------------------------------------------------------------------------

# 139. Data Lineage

Lineage answers:

``` text
Which raw packet produced this observation?
Which C4/C1/C2 result affected it?
Which dataset row used it?
Which model forecast consumed it?
```

This is essential for scientific reproducibility.

------------------------------------------------------------------------

# 140. Model Provenance

A prediction should be traceable to:

``` text
model version
feature schema
input records
preprocessing version
generation time
```

------------------------------------------------------------------------

# 141. MLOps

MLOps applies software-engineering/operations practices to ML lifecycle:

``` text
data versioning
experiment tracking
model registry
deployment
monitoring
retraining
rollback
```

GeoNex needs a lightweight but disciplined MLOps process.

------------------------------------------------------------------------

# 142. Model Registry

A model registry tracks:

``` text
candidate
approved
superseded
rejected
```

artifacts and their metadata.

Only approved models should serve normal runtime inference.

------------------------------------------------------------------------

# 143. Concept Drift

Concept drift occurs when relationships between inputs and targets
change over time.

Potential causes:

``` text
season
sensor aging
environment change
deployment changes
```

Drift may require review/retraining.

------------------------------------------------------------------------

# 144. Data Drift

Data drift means the distribution of input variables changes.

It does not automatically mean model performance has degraded, but it is
a warning signal.

------------------------------------------------------------------------

# 145. Controlled Retraining

GeoNex's "self-learning" means:

``` text
collect
→ validate
→ build candidate dataset
→ train candidate
→ evaluate
→ promote or reject
```

not uncontrolled continuous online weight updates.

------------------------------------------------------------------------

# 146. Why Promotion Gates Matter

A new model can improve one metric while becoming worse on:

``` text
critical recall
false alarms
calibration
latency
```

Promotion must consider the full requirement set.

------------------------------------------------------------------------

# 147. Rollback

Rollback allows the system to return to a previously approved model if
the new version behaves poorly.

This is a basic reliability requirement.

------------------------------------------------------------------------

# 148. Decision Engine

The Decision Engine consumes:

``` text
C3 forecast
current environmental severity
C1 quality
C2 recovery/degradation
C4 trust/security
system health
```

and applies operational policy.

It is not simply another ML classifier.

------------------------------------------------------------------------

# 149. Why Keep Decision Policy Explicit?

Explicit policy improves:

``` text
safety
auditability
hysteresis
manual review
testing
```

and prevents hidden operational actions from being buried inside model
weights.

------------------------------------------------------------------------

# 150. Operating Modes as Resource Policy

Modes represent how aggressively GeoNex should monitor/respond.

Conceptually:

``` text
DEEP_SLEEP — minimum activity
IDLE       — normal monitoring
RISK       — increased attention
WARNING    — high attention
EMERGENCY  — maximum safety response
```

Exact sensor/report intervals remain configurable.

------------------------------------------------------------------------

# 151. Mode Is Not Risk Label

Do not equate:

``` text
WARNING mode
```

with:

``` text
ground-truth landslide WARNING class
```

Mode is a system state created by policy.

------------------------------------------------------------------------

# 152. Latency

End-to-end warning latency can be decomposed:

``` text
L_total =
L_detection
+ L_acquisition
+ L_aggregation
+ L_wait_for_report
+ L_radio
+ L_gateway
+ L_ingestion
+ L_C4
+ L_C1
+ L_C2
+ L_C3
+ L_decision
+ L_alert
```

Not every term occurs in every event.

------------------------------------------------------------------------

# 153. Why ML Inference May Not Dominate Latency

A classifier may run in milliseconds while:

``` text
next scheduled sensor report
```

could be minutes away.

Therefore optimize the whole pipeline, not only model inference.

------------------------------------------------------------------------

# 154. Reliability

Reliability means the system performs its required function consistently
over time/conditions.

GeoNex reliability includes:

``` text
sensor reliability
communication reliability
software reliability
model robustness
power availability
recovery behaviour
```

------------------------------------------------------------------------

# 155. Availability

Availability concerns whether the system/service is operational and
usable when needed.

Redundancy and local operation can improve availability.

------------------------------------------------------------------------

# 156. Fault Tolerance

Fault tolerance means continuing useful operation despite certain
failures.

GeoNex mechanisms include:

``` text
backup sensors
local storage/replay
neighbour fusion
degraded operation
```

------------------------------------------------------------------------

# 157. Fail-Safe

A fail-safe system moves toward a safer state when uncertain/failing.

The exact safe action depends on context.

For example, security failure should not silently allow untrusted
telemetry.

------------------------------------------------------------------------

# 158. Graceful Degradation

Instead of complete failure:

``` text
full direct sensing
→ partial sensing
→ recovered/backup sensing
→ degraded forecast with uncertainty
→ escalation
```

This is preferable where safe and possible.

------------------------------------------------------------------------

# 159. Confidence Propagation

A recovered value may have lower confidence than a direct observation.

C3 can consume:

``` text
provenance
quality
confidence
```

rather than pretending all inputs are equal.

This is uncertainty-aware integration.

------------------------------------------------------------------------

# 160. Error Propagation

Errors can propagate:

``` text
C4 false trust
→ C1 processes malicious packet

C1 false acceptance
→ bad measurement enters Golden Timeline

C2 bad recovery
→ reconstructed value biases C3

C3 false negative
→ delayed warning
```

Therefore integrated testing is necessary.

------------------------------------------------------------------------

# 161. Upstream Model Predictions in Downstream Training

If C3 uses C1 predictions, training C3 on perfect C1 ground-truth labels
creates unrealistic performance.

Use:

``` text
out-of-fold/disjoint C1 predictions
```

to mimic runtime errors.

The same principle applies to C2/C4 outputs.

------------------------------------------------------------------------

# 162. Ablation Study

An ablation removes/adds one mechanism to measure its contribution.

Example C3:

``` text
Sensors
+ History
+ Δt
+ Mode
+ C1
+ C2
```

If `+Δt` improves performance under irregular sampling, that supports
the time-awareness contribution.

------------------------------------------------------------------------

# 163. Stress Testing

Stress tests deliberately create difficult conditions:

``` text
missing sensors
long gaps
noise
radio degradation
mode transitions
recovery errors
attack scenarios
```

A robust system should degrade predictably rather than fail
unexpectedly.

------------------------------------------------------------------------

# 164. Baseline

A baseline is a simpler reference method.

Without baselines, there is no evidence that the proposed mechanism is
necessary.

------------------------------------------------------------------------

# 165. Research Gap

A research gap is not:

``` text
"No one used our exact hardware combination."
```

A stronger gap identifies an unresolved capability/problem.

GeoNex gaps are framed around:

``` text
context-aware credibility
diagnosis of silence
variable-rate forecasting
trusted telemetry provenance
```

------------------------------------------------------------------------

# 166. Research Contribution

A contribution is what the research adds and validates.

It should be:

``` text
specific
measurable
bounded
supported by experiments
```

------------------------------------------------------------------------

# 167. Novelty vs Usefulness

A method can be useful without being globally novel.

For undergraduate research, a strong contribution may come from:

``` text
new integration
problem-specific adaptation
controlled comparison
system mechanism
validated architecture
```

provided claims are accurate.

------------------------------------------------------------------------

# 168. Correlation vs Causation

If rainfall and risk correlate:

``` text
rainfall predicts risk
```

does not alone prove rainfall caused a specific event.

GeoNex primarily performs prediction/diagnosis, not causal inference.

------------------------------------------------------------------------

# 169. Generalization

Generalization is performance on unseen data from the target
distribution/domain.

A model that memorizes synthetic scenarios does not generalize.

------------------------------------------------------------------------

# 170. Domain Shift

Training and deployment conditions can differ:

``` text
soil
climate
sensor placement
hardware
sampling
noise
```

This is domain shift.

It limits broad claims.

------------------------------------------------------------------------

# 171. External Validity

External validity asks:

> Do findings extend beyond the evaluated prototype/dataset?

GeoNex must distinguish:

``` text
prototype validation
```

from:

``` text
real-world deployment validation
```

------------------------------------------------------------------------

# 172. Internal Validity

Internal validity asks whether the experiment correctly supports its
causal/comparative conclusion.

Threats include:

``` text
leakage
unfair tuning
confounding
bad labels
duplicate scenarios
```

------------------------------------------------------------------------

# 173. Reproducibility

A reproducible experiment can be rerun using documented:

``` text
data
code
config
seed
environment
```

to obtain comparable results.

------------------------------------------------------------------------

# 174. Repeatability

Repeatability concerns repeating under the same conditions.

Reproducibility may involve independent reruns or environments.

Terminology can vary by discipline; define usage in the final thesis if
needed.

------------------------------------------------------------------------

# 175. Validity of Synthetic Data

Synthetic data is valuable for:

``` text
controlled experiments
rare scenario generation
pipeline testing
stress testing
```

but reflects generator assumptions.

It should not be presented as equivalent to field evidence.

------------------------------------------------------------------------

# 176. Physical Demo Evidence

The GeoNex prototype can strongly demonstrate:

``` text
sensor acquisition
communication
mode switching
database flow
C1–C4 integration
recovery
security handling
local inference
latency
```

without physically causing a landslide.

------------------------------------------------------------------------

# 177. Power Research Boundary

The demonstration's Type A/B pipes and hubs use the Centralized Power
Hub arrangement.

Therefore measurements can support:

``` text
relative power/current comparisons
```

but should not be converted directly into claims of real field
solar/battery lifetime unless the field power architecture is actually
evaluated.

------------------------------------------------------------------------

# 178. Energy vs Power

Power:

``` text
P = V × I
```

Energy over time:

``` text
E = ∫ P(t) dt
```

Battery-life claims require energy/capacity and realistic duty-cycle
analysis, not only instantaneous current.

------------------------------------------------------------------------

# 179. Adaptive Sampling and Energy

If lower modes reduce:

``` text
sensor activity
MCU active time
radio transmissions
```

energy consumption may decrease.

But this must be measured or estimated with justified assumptions.

------------------------------------------------------------------------

# 180. Communication Cost

Even when mains-powered in the demo, reducing transmissions can improve:

``` text
radio airtime
collision risk
network scalability
data volume
```

Therefore adaptive sampling has value beyond battery saving.

------------------------------------------------------------------------

# 181. GeoNex Core Scientific Story

``` text
A landslide monitoring system cannot safely reason from raw sensor values alone.

First:
verify source trust.

Then:
verify measurement credibility.

If expected information disappears:
diagnose and recover it.

Then:
forecast future risk using actual temporal spacing and provenance.

Finally:
adapt monitoring and warning behaviour according to risk.
```

------------------------------------------------------------------------

# 182. GeoNex Core Research Story

``` text
C4
trusted telemetry provenance

C1
context-aware sensor credibility

C2
mode-aware silence diagnosis and recovery

C3
mode-conditioned variable-rate temporal forecasting

Decision Engine
adaptive sensing and warning
```

Together they create a reliability-aware predictive monitoring
architecture.

------------------------------------------------------------------------

# 183. Easy Viva Mental Model

Remember:

``` text
WHO?  → C4
WHAT? → C1
WHY MISSING? → C2
WHAT NEXT? → C3
WHAT DO WE DO? → Decision Engine
```

------------------------------------------------------------------------

# 184. C1 Viva Mental Model

> A strange sensor value is not automatically a faulty value. C1 checks
> its history, neighbours and environmental context---especially
> rainfall---to decide whether it is a genuine event or an anomaly.

------------------------------------------------------------------------

# 185. C2 Viva Mental Model

> Silence has meaning only when we know when a device was expected to
> report. C2 uses the active mode, device/network evidence and
> independent backup verification to determine why information
> disappeared and how it should be recovered.

------------------------------------------------------------------------

# 186. C3 Viva Mental Model

> GeoNex intentionally changes sampling frequency, so two consecutive
> samples may be seconds or minutes apart. C3 explicitly represents that
> elapsed time and data quality when forecasting future risk.

------------------------------------------------------------------------

# 187. C4 Viva Mental Model

> Cryptography checks mandatory source/integrity properties; ML does not
> replace it. Behavioural ML is an extra layer that looks for suspicious
> device or transmission patterns that basic verification may not
> capture.

------------------------------------------------------------------------

# 188. Decision Engine Viva Mental Model

> The models provide evidence. The Decision Engine decides the
> operational response using explicit safety and mode-transition rules.

------------------------------------------------------------------------

# 189. Theory Checklist --- C1 Member

Must understand:

-   [ ] sensor accuracy/precision/noise/drift
-   [ ] outlier vs fault vs valid event
-   [ ] temporal consistency
-   [ ] spatial consistency
-   [ ] environmental context
-   [ ] supervised classification
-   [ ] RF/XGBoost/LightGBM
-   [ ] class imbalance
-   [ ] confusion matrix/macro-F1
-   [ ] SHAP
-   [ ] leakage/group splitting

------------------------------------------------------------------------

# 190. Theory Checklist --- C2 Member

Must understand:

-   [ ] expected-report scheduling
-   [ ] mode-aware timeout
-   [ ] missingness
-   [ ] fault detection
-   [ ] fault diagnosis/isolation
-   [ ] redundancy
-   [ ] backup verification
-   [ ] imputation/recovery
-   [ ] provenance/confidence
-   [ ] RF/XGBoost
-   [ ] recovery latency

------------------------------------------------------------------------

# 191. Theory Checklist --- C3 Member

Must understand:

-   [ ] time series
-   [ ] irregular sampling
-   [ ] Δt
-   [ ] missingness masks
-   [ ] sequence windows/horizons
-   [ ] RNN
-   [ ] LSTM
-   [ ] GRU
-   [ ] Time-Aware GRU
-   [ ] GRU-D
-   [ ] leakage
-   [ ] calibration
-   [ ] PR-AUC
-   [ ] warning lead time
-   [ ] mode feedback bias

------------------------------------------------------------------------

# 192. Theory Checklist --- C4 Member

Must understand:

-   [ ] identity
-   [ ] authentication
-   [ ] integrity
-   [ ] authorization
-   [ ] freshness
-   [ ] nonce/counter
-   [ ] replay
-   [ ] authorized recovery replay
-   [ ] provenance
-   [ ] behavioural anomaly detection
-   [ ] Isolation Forest
-   [ ] boosted trees
-   [ ] false acceptance/rejection
-   [ ] threat model

------------------------------------------------------------------------

# 193. Theory Checklist --- Entire Team

Everyone should understand:

-   [ ] four-component boundary
-   [ ] Golden Timeline
-   [ ] operating modes
-   [ ] adaptive sampling
-   [ ] raw vs derived data
-   [ ] operational DB vs ML dataset
-   [ ] train/validation/test
-   [ ] leakage
-   [ ] synthetic vs physical evidence
-   [ ] model versioning
-   [ ] controlled retraining
-   [ ] Decision Engine
-   [ ] end-to-end latency
-   [ ] research claim limitations

------------------------------------------------------------------------

# 194. Terms That Must Not Be Confused

``` text
Centralized Power Hub
≠
Centralized Sensor Hub

Main Gateway electronics
≠
Main Computing System

operating mode
≠
ground-truth risk class

anomaly
≠
fault

outlier
≠
invalid data

authentication
≠
measurement credibility

replay attack
≠
authorized C2 historical replay

missing data
≠
zero

risk probability
≠
certainty

C3 forecast
≠
Decision Engine action

synthetic result
≠
field performance
```

------------------------------------------------------------------------

# 195. Theory-to-Implementation Map

``` text
sensor calibration
→ sensor_calibrations / feature correctness

source authentication
→ C4

contextual anomaly theory
→ C1

fault diagnosis/redundancy
→ C2

irregular time-series theory
→ C3

probability calibration
→ C3/other probabilistic outputs

adaptive control
→ Decision Engine / Mode Manager

provenance
→ database + Golden Timeline

MLOps
→ model registry/retraining
```

------------------------------------------------------------------------

# 196. Theory-to-Experiment Map

``` text
context-aware anomaly detection
→ C1 target/history/neighbour/rainfall ablation

fault diagnosis
→ C2 fixed timeout vs mode-aware + backup

irregular time series
→ C3 standard GRU vs Δt/time-aware models

hybrid cybersecurity
→ C4 deterministic vs behavioural vs hybrid

adaptive sampling
→ fixed-rate vs variable-rate system experiment
```

------------------------------------------------------------------------

# 197. Evidence Discipline

Before adding a theory statement to the thesis/paper, ask:

``` text
Is this:
A) mathematical/engineering definition?
B) project design decision?
C) experimental result?
D) claim from literature?
E) inference?
```

Then support it appropriately.

------------------------------------------------------------------------

# 198. Literature Citation Discipline

The final thesis/paper should cite peer-reviewed or authoritative
sources for claims such as:

``` text
landslide physical mechanisms
rainfall-trigger relationships
sensor principles
GRU-D/time-aware methods
anomaly-detection theory
cybersecurity mechanisms
calibration methods
```

Do not cite this internal guide as scientific evidence.

------------------------------------------------------------------------

# 199. Project Decision Discipline

For GeoNex-specific architecture claims, reference the project
specifications and implementation evidence.

Example:

``` text
GeoNex uses five operating modes
```

is a project design decision, not a universal scientific fact.

------------------------------------------------------------------------

# 200. Experimental Result Discipline

Do not write:

``` text
"GRU-D improves forecasting"
```

until GeoNex experiments show it.

Before experiments:

``` text
"GRU-D is evaluated as a candidate because its treatment of missingness and elapsed time aligns with the C3 problem."
```

------------------------------------------------------------------------

# 201. Final Knowledge Structure

A team member should mentally organize GeoNex as:

``` text
PHYSICAL WORLD
rainfall / soil / movement

SENSING
sensors / calibration / noise

COMMUNICATION
LoRa / timing / packet loss

TRUST
C4

DATA QUALITY
C1

AVAILABILITY
C2

TEMPORAL PREDICTION
C3

CONTROL
Decision Engine / modes

DATA ENGINEERING
database / Golden Timeline / provenance

RESEARCH
datasets / baselines / ablations / validation

OPERATIONS
MLOps / monitoring / retraining / rollback
```

------------------------------------------------------------------------

# 202. What Is Frozen by Document 10

1.  GeoNex is framed as management of source, measurement, availability
    and future-state uncertainty.
2.  Landslide prediction is probabilistic/risk-oriented rather than
    certainty.
3.  Environmental sensors require calibration and contextual
    interpretation.
4.  Extreme/outlier values are not automatically faults.
5.  C1 is based on temporal, spatial and environmental credibility
    context.
6.  C2 distinguishes detection, diagnosis, isolation and recovery.
7.  Missingness can be informative.
8.  Recovery provenance must remain explicit.
9.  C3 is a future forecasting problem with strict temporal boundaries.
10. Irregular sampling and Δt are fundamental to C3.
11. Mode is operational context, not geological truth.
12. Adaptive sampling can create feedback/selection bias and must be
    evaluated.
13. C3 and the Decision Engine remain separate.
14. Calibration is necessary for meaningful risk probabilities.
15. C4 mandatory security is deterministic; behavioural ML is
    supplemental.
16. Authentication/integrity do not prove environmental correctness.
17. Authorized historical recovery replay is distinct from malicious
    replay.
18. Provenance and immutable raw evidence are foundational.
19. Operational DB and ML datasets are separate.
20. Synthetic, prototype and field evidence have different evidential
    strength.
21. Controlled retraining, model registry and rollback form GeoNex's
    self-learning/MLOps interpretation.
22. Research claims must be bounded by actual evidence.

------------------------------------------------------------------------

# 203. Topics Requiring Dedicated Literature Support Later

Before thesis/paper finalization, conduct literature-backed work on:

``` text
rainfall-induced landslide mechanisms
local/regional rainfall threshold research
soil-moisture precursors
tilt/deformation monitoring
IoT landslide monitoring
sensor fault/anomaly detection
spatiotemporal sensor credibility
fault diagnosis and redundancy
irregular time-series forecasting
GRU-D / time-aware recurrent methods
probability calibration
adaptive sampling
IoT authentication/integrity/replay protection
behavioural device anomaly detection
edge AI for disaster monitoring
```

This guide intentionally does not invent citations.

------------------------------------------------------------------------

# 204. Next Document

Next:

``` text
11_GEONEX_INTEGRATION_CONTRACT.md
```

It should convert the architectural concepts into explicit
machine-readable/software-facing contracts covering:

``` text
canonical IDs
timestamps
packet envelope
sensor observation schema
C4 output
C1 output
silence event
C2 diagnosis/recovery
Golden Timeline
C3 forecast
mode events
device commands
ACKs
alerts
status/error semantics
schema versions
cross-component ordering
as-of rules
mock contracts
integration tests
```

That document will become the principal shared interface baseline used
by all four developers.

------------------------------------------------------------------------

# Document 10 Status

**`10_GEONEX_RESEARCH_THEORY_AND_CONCEPTS.md` --- SHARED THEORY BASELINE
READY**

The central mental model is:

``` text
WHO?          → C4
WHAT?         → C1
WHY MISSING?  → C2
WHAT NEXT?    → C3
WHAT TO DO?   → Decision Engine
```

All implementation, experiments and research claims should remain
consistent with those boundaries.
