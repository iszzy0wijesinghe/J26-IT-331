# 09_GEONEX_MODEL_SELECTION_AND_JUSTIFICATION.md

**Project:** GeoNex --- Smart Landslide Early Warning Prediction System
using IoT, Edge AI and Risk Analytics\
**Document:** Cross-Component Model Selection and Justification\
**Status:** Research and Development Baseline\
**Depends on:** Documents 00--08\
**Scope:** C1, C2, C3, C4 and their deterministic/ML boundaries

------------------------------------------------------------------------

# 1. Purpose

This document defines **how GeoNex selects, compares, justifies and
finally approves algorithms for all four research components**.

The objective is not to decide that the most complex model is
automatically best.

The objective is to answer:

> **Which algorithm provides the strongest evidence-based solution for
> each component's actual research problem, subject to predictive
> performance, safety, explainability, robustness, latency, data
> availability and deployment constraints?**

Final model choices must therefore be earned experimentally.

------------------------------------------------------------------------

# 2. Core Principle

GeoNex does not follow:

``` text
research problem
→ choose fashionable AI model
→ report accuracy
```

It follows:

``` text
research problem
→ define target and evidence
→ establish deterministic/simple baseline
→ establish strong ML baseline
→ test proposed mechanism
→ ablate contribution
→ stress test
→ evaluate operational cost
→ select simplest model that adequately satisfies requirements
```

------------------------------------------------------------------------

# 3. AI, ML and Deterministic Logic

GeoNex is an AI-driven system containing:

``` text
machine learning
deep learning
deterministic safety/security logic
statistical processing
decision rules
```

Not every problem should be solved by ML.

Correct framing:

> **GeoNex consists of four AI-driven research components employing
> machine learning, deep learning and deterministic mechanisms according
> to the nature of each problem.**

------------------------------------------------------------------------

# 4. Why Hybrid Design Is Necessary

Certain decisions have explicit logical truth conditions.

Examples:

``` text
cryptographic authentication failed
device revoked
packet replay unauthorized
```

These belong to deterministic security logic.

Other relationships are uncertain and data-dependent.

Examples:

``` text
is an unusual sensor value faulty or a genuine hazard event?
what caused a silent stream?
what future risk follows this multivariate temporal pattern?
is authenticated telemetry behaviourally abnormal?
```

These are suitable for statistical/ML reasoning.

------------------------------------------------------------------------

# 5. Research Value Is Not Model Complexity

A component becomes valuable through:

``` text
specific research problem
+
clear gap
+
appropriate mechanism
+
strong baseline
+
controlled comparison
+
robust evaluation
+
operational relevance
```

not through:

``` text
number of neural-network layers
```

------------------------------------------------------------------------

# 6. Shared Selection Criteria

Every candidate model is evaluated across:

  -----------------------------------------------------------------------
  Criterion                           Question
  ----------------------------------- -----------------------------------
  Predictive quality                  Does it solve the component task
                                      well?

  Critical-class recall               Does it detect important
                                      hazardous/failure/security cases?

  False-positive burden               Does it create excessive
                                      unnecessary actions?

  Calibration                         Are probability/confidence outputs
                                      meaningful?

  Robustness                          Does it tolerate
                                      missing/noisy/shifted conditions?

  Leakage resistance                  Is performance based on legitimate
                                      information?

  Explainability                      Can the team explain important
                                      decisions?

  Latency                             Can it run within operational
                                      timing needs?

  Resource use                        Is CPU/RAM/storage cost acceptable?

  Data requirement                    Is available training evidence
                                      sufficient?

  Maintainability                     Can the team reproduce/update it?

  Integration                         Does it fit the shared contracts?

  Research contribution               Does it test the actual proposed
                                      mechanism?
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 7. Model Selection Must Be Multi-Criteria

The final model is not necessarily:

``` text
argmax(F1)
```

A slightly better F1 may not justify:

``` text
10× inference cost
poor calibration
unstable results
weak explainability
difficult deployment
```

Selection should use a documented evidence table.

------------------------------------------------------------------------

# 8. Final Test Set Rule

The final test set is not a tuning resource.

Correct:

``` text
TRAIN → fit
VALIDATION → tune/select
TEST → final unbiased evaluation
```

Repeatedly changing the model after observing test performance
contaminates the test set.

------------------------------------------------------------------------

# 9. Multiple Random Seeds

Where stochastic training is involved, especially neural models:

``` text
one lucky run ≠ evidence
```

Use multiple seeds where feasible and report:

``` text
mean
standard deviation
individual runs
```

for important final comparisons.

------------------------------------------------------------------------

# 10. Statistical Comparison

Where sample/event count permits, use:

``` text
confidence intervals
bootstrap estimates
paired event-level comparison
```

rather than relying only on a tiny numerical difference.

------------------------------------------------------------------------

# 11. Baseline Philosophy

Each component should contain three conceptual levels:

``` text
B0 — simple/deterministic baseline
B1 — strong conventional ML baseline
P  — proposed research approach
```

The proposed approach must justify its extra complexity.

------------------------------------------------------------------------

# 12. Component Model Overview

Recommended candidate families:

  -----------------------------------------------------------------------
  Component               Problem                 Core candidate
                                                  direction
  ----------------------- ----------------------- -----------------------
  C1                      Measurement credibility LightGBM / XGBoost

  C2                      Silence/failure         XGBoost / Random
                          diagnosis               Forest + deterministic
                                                  recovery policy

  C3                      Variable-rate temporal  Time-Aware GRU / GRU-D
                          forecasting             

  C4                      Telemetry trust         deterministic
                                                  security +
                                                  LightGBM/XGBoost or
                                                  anomaly detector
  -----------------------------------------------------------------------

These are **candidate directions**, not predeclared winners.

------------------------------------------------------------------------

# 13. Why Deep Learning Is Mainly C3

C3 directly models:

``` text
multivariate temporal sequences
+
irregular intervals
+
missingness
+
longitudinal context
```

This provides a strong reason for recurrent/time-aware deep learning.

C1, C2 and C4 are initially more naturally represented as:

``` text
structured/tabular contextual features
```

where boosted trees may provide stronger data efficiency and easier
explanation.

------------------------------------------------------------------------

# 14. Why Not Use Deep Learning Everywhere?

Potential disadvantages:

``` text
larger datasets required
greater tuning burden
higher compute
harder debugging
more difficult explanation
higher overfitting risk
```

If a boosted tree solves C1 better than a neural network, the tree is
the better research choice.

------------------------------------------------------------------------

# 15. Why Boosted Trees Are Strong Candidates

XGBoost/LightGBM are attractive for C1/C2/C4 because they handle:

``` text
nonlinear interactions
mixed-scale tabular features
missing values
moderate datasets
feature interactions
```

and support useful explanation techniques such as SHAP.

------------------------------------------------------------------------

# 16. XGBoost vs LightGBM

Neither is automatically superior.

General tendencies:

``` text
XGBoost
→ mature, robust, strong regularization ecosystem

LightGBM
→ efficient histogram/tree growth, often fast on larger tabular data
```

Actual selection must use GeoNex data.

------------------------------------------------------------------------

# 17. Random Forest

Random Forest is an important baseline because it is:

``` text
easy to train
nonlinear
relatively robust
less tuning-intensive
interpretable through feature importance
```

If it performs similarly to a more complex boosted model, that is
meaningful.

------------------------------------------------------------------------

# 18. Logistic Regression

Logistic Regression remains useful as:

``` text
simple supervised baseline
```

for appropriate binary/multiclass formulations.

It reveals whether complex nonlinear modeling is actually necessary.

------------------------------------------------------------------------

# 19. Isolation Forest

Isolation Forest is useful where:

``` text
normal examples are plentiful
abnormal labels are limited
```

especially for C4 behavioural anomaly experiments.

It should not replace supervised models automatically.

------------------------------------------------------------------------

# 20. C1 Problem

C1 classifies a sensor observation using environmental and contextual
evidence into a taxonomy such as:

``` text
CLEAN
ANOMALY
VALID_EVENT
```

The crucial distinction is:

``` text
ANOMALY
vs
VALID_EVENT
```

because a real hazardous environmental change must not be rejected
merely for being unusual.

------------------------------------------------------------------------

# 21. Why C1 Is Not Generic Anomaly Detection

Generic anomaly detection often assumes:

``` text
rare = suspicious
```

But in early warning:

``` text
rare extreme environmental event
```

may be exactly the signal GeoNex must preserve.

Therefore C1 requires contextual supervised reasoning where possible.

------------------------------------------------------------------------

# 22. C1 Research Mechanism

C1 proposes that credibility should depend on:

``` text
target measurement
+
temporal history
+
neighbour agreement
+
rainfall/environmental regime
+
device-health context
```

rather than target value alone.

------------------------------------------------------------------------

# 23. C1 Baseline 0 --- Plausibility Rules

Examples:

``` text
physical range
maximum plausible rate-of-change
stuck-value detection
```

These provide a deterministic reference.

Exact thresholds require sensor calibration/domain justification.

------------------------------------------------------------------------

# 24. C1 Baseline 1 --- Robust Statistical Detector

Potential:

``` text
median/MAD
IQR
z-score where justified
```

This represents conventional anomaly detection.

Expected weakness:

``` text
genuine extreme events may be rejected
```

------------------------------------------------------------------------

# 25. C1 Baseline 2 --- Logistic Regression

A supervised linear baseline tests whether contextual classes can be
separated without nonlinear trees.

------------------------------------------------------------------------

# 26. C1 Baseline 3 --- Random Forest

Provides a strong nonlinear reference.

------------------------------------------------------------------------

# 27. C1 Candidate --- XGBoost/LightGBM

Strong candidate because interactions such as:

``` text
high soil moisture
+
heavy recent rainfall
+
neighbour increase
```

may indicate a valid environmental event, while:

``` text
high soil moisture
+
dry conditions
+
stable neighbours
```

may indicate a sensor anomaly.

Trees naturally represent such conditional interactions.

------------------------------------------------------------------------

# 28. C1 Deep Learning?

Not recommended as the first proposed model.

It becomes justified only if:

``` text
large temporal raw streams
substantial training data
clear improvement over tree models
```

exist.

Otherwise it adds complexity without strengthening the research
question.

------------------------------------------------------------------------

# 29. C1 Mandatory Model Comparison

``` text
physical/statistical rules
robust anomaly baseline
Logistic Regression
Random Forest
XGBoost
LightGBM
```

Then select the strongest justified model.

------------------------------------------------------------------------

# 30. C1 Mandatory Feature Ablation

``` text
target only
+ temporal history
+ neighbours
+ rainfall context
+ combined context
```

Optional:

``` text
+ device/C4 context
```

This proves why C1 is **rainfall regime-aware** rather than merely a
classifier.

------------------------------------------------------------------------

# 31. C1 Primary Selection Metrics

``` text
macro-F1
ANOMALY recall
VALID_EVENT recall
VALID_EVENT false-rejection rate
per-class precision
confusion matrix
```

Headline accuracy is insufficient.

------------------------------------------------------------------------

# 32. C1 Key Research Criterion

The winning C1 model should reduce:

``` text
VALID_EVENT → ANOMALY
```

errors without causing unacceptable loss in true anomaly detection.

This is central to the component's value.

------------------------------------------------------------------------

# 33. C1 Explainability

For tree candidates:

``` text
SHAP
feature importance
case-level explanations
```

should test whether decisions depend on plausible context.

SHAP is explanatory evidence, not causal proof.

------------------------------------------------------------------------

# 34. C1 Final Selection Statement Template

> C1 selected **\[MODEL\]** because it achieved the strongest balance of
> macro-F1, anomaly recall and genuine-event preservation on held-out
> data. The contextual ablation showed that
> **\[rainfall/neighbour/history\]** contributed **\[measured
> effect\]**, while inference latency and model complexity remained
> suitable for the GeoNex edge-host environment.

Fill only after experiments.

------------------------------------------------------------------------

# 35. C2 Problem

C2 answers:

> **Why did expected telemetry become silent or unavailable, and what
> recovery action is appropriate?**

Potential classes:

``` text
normal
communication_failure
hardware_failure
possible_zone_damage
```

------------------------------------------------------------------------

# 36. C2 Is Not Imputation

C2 should not be reduced to:

``` text
value missing
→ fill mean
```

Its research problem is:

``` text
silence detection
+
cause diagnosis
+
independent backup verification
+
recovery selection
+
provenance
```

------------------------------------------------------------------------

# 37. C2 Two-Stage Architecture

Recommended:

``` text
Stage A
silence/failure diagnosis
        ↓
Stage B
recovery/action selection
```

This separation is scientifically cleaner.

------------------------------------------------------------------------

# 38. C2 Stage A Baseline 0 --- Fixed Timeout

Conventional:

``` text
if no packet for N seconds:
    failure
```

Weakness:

GeoNex uses variable-rate sampling.

A legitimate DEEP_SLEEP interval can appear as failure under a fixed
timeout.

------------------------------------------------------------------------

# 39. C2 Improved Detection --- Mode-Aware Timeout

Expected silence must use:

``` text
current applied mode
+
expected report interval
+
grace policy
```

This is an important deterministic contribution even before ML
diagnosis.

------------------------------------------------------------------------

# 40. C2 Stage A Baseline 1 --- Rule Diagnosis

Example logic:

``` text
missing primary
+ hub reachable
+ backup reachable
→ possible primary sensor/link problem
```

Useful as interpretable baseline.

------------------------------------------------------------------------

# 41. C2 Stage A Baseline 2 --- Logistic/Decision Tree

Provides a simple supervised diagnostic reference.

------------------------------------------------------------------------

# 42. C2 Stage A Candidate --- Random Forest

Strong candidate because diagnosis uses structured evidence such as:

``` text
last-seen time
packet loss
battery
hub status
backup response
neighbour state
```

------------------------------------------------------------------------

# 43. C2 Stage A Candidate --- XGBoost

Also strong for nonlinear tabular diagnosis.

Final RF vs XGBoost selection is experimental.

------------------------------------------------------------------------

# 44. C2 Stage B --- Recovery

Existing conceptual actions:

``` text
REQUEST_SD_REPLAY
ACTIVATE_BACKUP_SENSOR
USE_NEIGHBOR_FUSION
SWITCH_BACKUP_HUB
ESCALATE
```

If these actions are almost deterministically mapped from diagnosed
failure type and availability, a rule-based policy is preferable.

------------------------------------------------------------------------

# 45. Why Not Force ML into C2 Stage B?

If:

``` text
failure_type = primary_sensor_failure
```

and the only safe available action is:

``` text
ACTIVATE_BACKUP_SENSOR
```

training a classifier to rediscover this lookup table adds no research
value.

Use deterministic safety policy unless action selection genuinely
depends on uncertain multivariate context.

------------------------------------------------------------------------

# 46. C2 Backup Verification Contribution

Mandatory comparison:

``` text
diagnosis without backup evidence
vs
diagnosis with independent Backup Pipe evidence
```

This proves whether backup hardware adds diagnostic value rather than
being simple redundancy.

------------------------------------------------------------------------

# 47. C2 Recovery Comparison

Compare:

``` text
blind imputation
vs
backup recovery
vs
neighbour fusion
vs
SD replay
```

where applicable.

Measure not only recovered-value error but provenance and latency.

------------------------------------------------------------------------

# 48. C2 Primary Selection Metrics

``` text
macro-F1
per-failure recall
possible-zone-damage recall
diagnosis latency
recovery success rate
recovered-value error/confidence
false failure triggers
```

------------------------------------------------------------------------

# 49. C2 Safety Criterion

A model must not casually classify:

``` text
possible_zone_damage
```

as confirmed landslide.

It means:

``` text
evidence is consistent with a broader zone-level problem
→ escalate
```

------------------------------------------------------------------------

# 50. C2 Final Selection Statement Template

> C2 selected **\[MODEL\]** for failure-cause diagnosis because it
> provided the strongest held-out multiclass performance and robustness
> under mode-aware silence scenarios. Recovery remained governed by
> **\[deterministic/hybrid\]** policy because **\[reason\]**, while
> backup verification improved **\[metric\]** relative to diagnosis
> without independent backup evidence.

------------------------------------------------------------------------

# 51. C3 Problem

C3 forecasts future risk from:

``` text
multivariate temporal history
+
irregular Δt
+
mode
+
missingness
+
C1 credibility
+
C2 provenance
```

This is the component with the strongest justification for deep temporal
learning.

------------------------------------------------------------------------

# 52. C3 Baseline 0 --- Current-State Rule

Uses current/rolling hazard indicators.

This tests whether advanced forecasting beats reactive thresholding.

------------------------------------------------------------------------

# 53. C3 Baseline 1 --- Logistic Regression

Uses engineered temporal summaries.

Provides interpretable linear baseline.

------------------------------------------------------------------------

# 54. C3 Baseline 2 --- XGBoost/LightGBM

A critical strong baseline.

Use engineered:

``` text
rainfall sums
soil trends
tilt rates
vibration summaries
Δt statistics
quality summaries
```

A neural model must justify itself against this.

------------------------------------------------------------------------

# 55. C3 Baseline 3 --- Standard GRU

GRU models ordered sequence history.

But a standard GRU typically treats recurrent steps as abstract sequence
steps unless elapsed time is explicitly represented.

This makes it the ideal neural baseline.

------------------------------------------------------------------------

# 56. Optional C3 LSTM

LSTM may be included if resources allow.

It is a classical recurrent comparison, not the core contribution.

------------------------------------------------------------------------

# 57. C3 Candidate --- Time-Aware GRU

A time-aware recurrent architecture explicitly incorporates elapsed time
into state evolution.

It directly addresses:

``` text
variable-rate sampling
```

and is therefore a strong candidate for the proposed method.

------------------------------------------------------------------------

# 58. C3 Candidate --- GRU-D

GRU-D is particularly relevant when:

``` text
variables are missing irregularly
time since last observation matters
missingness itself is informative
```

It uses:

``` text
mask
time gap
decay mechanisms
```

which align closely with GeoNex.

------------------------------------------------------------------------

# 59. Time-Aware GRU vs GRU-D

Selection depends on actual data.

If the primary challenge is:

``` text
variable global sampling interval
```

a Time-Aware GRU may be sufficient.

If the data exhibits substantial:

``` text
per-variable missingness
asynchronous sensor observations
```

GRU-D may offer stronger inductive bias.

Test both.

------------------------------------------------------------------------

# 60. Why Not Standard GRU Alone?

Because two transitions:

``` text
70 → 80 over 1 minute
```

and:

``` text
70 → 80 over 1 hour
```

are physically different.

Explicit timing allows the model to distinguish them.

------------------------------------------------------------------------

# 61. Why Not Transformer by Default?

GeoNex does not currently require a Transformer to establish its
research contribution.

Potential disadvantages:

``` text
greater data requirement
greater tuning burden
more compute
weaker justification on small datasets
```

It may be tested later only if evidence warrants it.

------------------------------------------------------------------------

# 62. C3 Mandatory Feature Ablation

``` text
A0 Sensors/current state
A1 + History
A2 + Δt
A3 + Mode
A4 + C1
A5 + C2
```

This is the central C3 evidence chain.

------------------------------------------------------------------------

# 63. C3 Mandatory Architecture Comparison

At minimum:

``` text
boosted-tree baseline
standard GRU
Time-Aware GRU
GRU-D
```

Optional:

``` text
LSTM
```

------------------------------------------------------------------------

# 64. C3 Mode-Only Baseline

Mandatory:

``` text
current mode → target
```

This checks whether the model could exploit:

``` text
WARNING/EMERGENCY
```

as a shortcut rather than learning environmental dynamics.

------------------------------------------------------------------------

# 65. C3 Primary Metrics

``` text
PR-AUC
ROC-AUC
event recall
precision
F1
false alarms per unit time
warning lead time
Brier score
calibration
```

For early warning, event-level operational metrics are crucial.

------------------------------------------------------------------------

# 66. C3 Calibration Criterion

If C3 says:

``` text
risk probability = 0.80
```

that probability should be empirically meaningful.

Model ranking performance alone is insufficient for Decision Engine use.

------------------------------------------------------------------------

# 67. C3 Robustness Criteria

Test:

``` text
long gaps
short gaps
missing sensors
stale values
abrupt mode changes
C1 errors
C2 recovery
distribution shift
```

Time-aware architecture should demonstrate its value especially under
irregularity.

------------------------------------------------------------------------

# 68. C3 Complexity Criterion

If Time-Aware GRU achieves only negligible benefit over XGBoost while
requiring substantially greater complexity, the research must report
that.

Do not force the neural model to win.

------------------------------------------------------------------------

# 69. C3 Final Selection Statement Template

> C3 selected **\[MODEL\]** because it achieved the strongest balance of
> held-out event detection, probability calibration, warning lead time
> and robustness under irregular sampling. Compared with standard GRU,
> explicit **\[Δt/missingness decay\]** improved **\[metric\]**, while
> the Sensors→History→Δt→Mode→C1→C2 ablation demonstrated the
> contribution of each information source.

------------------------------------------------------------------------

# 70. C4 Problem

C4 determines:

``` text
source/transmission trust
```

through:

``` text
mandatory deterministic security
+
behavioural anomaly analysis
```

------------------------------------------------------------------------

# 71. C4 Baseline 0 --- Registration Only

Tests:

``` text
known device?
```

This is intentionally weak.

It shows that registration alone does not address all trust problems.

------------------------------------------------------------------------

# 72. C4 Baseline 1 --- Deterministic Security

Uses implemented:

``` text
identity
authentication
integrity
freshness
replay rules
```

This is the mandatory security baseline.

------------------------------------------------------------------------

# 73. C4 Behavioural Baseline --- Logistic/RF

Uses timing/radio/device/path behaviour.

This establishes whether nonlinear behavioural modeling is necessary.

------------------------------------------------------------------------

# 74. C4 Candidate --- XGBoost/LightGBM

Strong supervised behavioural candidate for labeled attack/suspicious
scenarios.

------------------------------------------------------------------------

# 75. C4 Candidate --- Isolation Forest

Useful for detecting deviations from normal behaviour where attack
labels are incomplete.

This provides a different research assumption:

``` text
learn normal
→ flag unusual
```

------------------------------------------------------------------------

# 76. C4 Hybrid Proposed System

``` text
mandatory deterministic gate
        +
selected behavioural model
        +
trust fusion
```

Hard security failures dominate.

------------------------------------------------------------------------

# 77. Why Not Neural Security Model by Default?

Current C4 evidence is primarily structured behavioural telemetry.

Boosted trees/anomaly methods are likely more data-efficient and
explainable.

Deep learning is only justified if future high-dimensional sequential
security data demands it.

------------------------------------------------------------------------

# 78. C4 Mandatory Ablation

``` text
registration/basic identity
+ deterministic security
behavioural only
hybrid
hybrid + mode-aware context
```

This proves whether behavioural ML adds value.

------------------------------------------------------------------------

# 79. C4 Primary Metrics

``` text
untrusted recall
false acceptance rate
false rejection rate
macro-F1
per-class recall
PR-AUC
latency
```

For deterministic controls, also report direct scenario pass/fail
detection.

------------------------------------------------------------------------

# 80. C4 Security Dominance Rule

No model-selection metric can justify accepting:

``` text
failed mandatory authentication
```

because an ML model thinks the behaviour looks normal.

This is an architectural invariant.

------------------------------------------------------------------------

# 81. C4 Final Selection Statement Template

> C4 selected **\[MODEL\]** for behavioural assessment because it
> improved detection of **\[scenario types\]** beyond deterministic
> verification while maintaining an acceptable false-rejection rate.
> Mandatory identity/integrity/freshness failures remain deterministic
> and override the behavioural model.

------------------------------------------------------------------------

# 82. Cross-Component Model Philosophy

The resulting system should look approximately like:

``` text
C4:
deterministic security + tabular/anomaly ML

C1:
context-aware tabular supervised ML

C2:
mode-aware deterministic silence detection
+ tabular diagnostic ML
+ deterministic/hybrid recovery

C3:
time-aware temporal deep learning
```

This diversity is intentional.

------------------------------------------------------------------------

# 83. Why One Model Family Should Not Be Used Everywhere

Using XGBoost everywhere or neural networks everywhere would ignore
problem structure.

Model architecture should match:

``` text
data geometry
target
uncertainty
temporal structure
safety requirements
```

------------------------------------------------------------------------

# 84. Explainability Strategy

Recommended:

``` text
C1 → SHAP + case analysis
C2 → SHAP/rule trace + recovery reason
C3 → ablation + temporal occlusion + feature perturbation
C4 → deterministic reason codes + SHAP/deviation explanation
```

No single explanation method is sufficient for all components.

------------------------------------------------------------------------

# 85. Confidence Is Not Ground Truth

A model confidence of:

``` text
0.95
```

means:

``` text
the model is highly confident under its learned representation
```

not:

``` text
95% guaranteed physical truth
```

Calibration determines whether numerical probabilities can be
interpreted probabilistically.

------------------------------------------------------------------------

# 86. Probability Calibration by Component

Strongly relevant:

``` text
C3 risk probability
```

Potentially relevant:

``` text
C1 class probability
C2 diagnosis probability
C4 behavioural probability
```

if downstream policies use those values.

------------------------------------------------------------------------

# 87. Class Imbalance

Potential methods:

``` text
class weighting
balanced training batches
focal loss for neural models
careful threshold selection
```

Apply only to training.

Do not artificially balance final test data when claiming operational
performance.

------------------------------------------------------------------------

# 88. SMOTE Caution

SMOTE may be reasonable for some static tabular experiments.

However:

``` text
temporal sequences
event-grouped data
security scenarios
```

can be corrupted by naive synthetic interpolation.

Do not use SMOTE automatically.

------------------------------------------------------------------------

# 89. Hyperparameter Tuning

Use:

``` text
validation set
cross-validation compatible with grouping/time
Bayesian/random/grid search where justified
```

with a comparable tuning budget across competing models.

------------------------------------------------------------------------

# 90. Group-Aware Cross-Validation

Potential grouping:

``` text
C1 → event/device/time block
C2 → silence/failure episode
C3 → event/scenario/time block
C4 → attack scenario/device/time block
```

Random row CV is often inappropriate.

------------------------------------------------------------------------

# 91. Data Leakage Audit Before Model Comparison

Every component must audit:

``` text
target-derived features
future features
post-outcome features
IDs correlated with labels
synthetic scenario IDs
overlapping windows
upstream ground-truth labels unavailable at runtime
```

A sophisticated model trained on leaked data is invalid.

------------------------------------------------------------------------

# 92. Upstream Prediction Leakage

For integrated training:

``` text
C3 using C1/C2 outputs
```

must use:

``` text
out-of-fold/disjoint upstream predictions
```

not perfect labels or predictions generated by a model trained on the
same records.

------------------------------------------------------------------------

# 93. Synthetic Data Rule

Synthetic data can establish:

``` text
pipeline correctness
controlled mechanism behavior
stress-test coverage
```

but cannot alone establish broad real-world landslide performance.

Model selection reports must state evidence origin.

------------------------------------------------------------------------

# 94. Physical Prototype Rule

The physical prototype can establish:

``` text
hardware/software integration
timing
communication
mode switching
failure recovery
security behaviour
inference latency
```

It cannot by itself establish broad landslide generalization.

------------------------------------------------------------------------

# 95. External Dataset Rule

External real-world datasets may strengthen predictive validation.

But document:

``` text
domain
sensor differences
sampling differences
label differences
mapping
```

and discuss domain shift.

------------------------------------------------------------------------

# 96. Runtime Latency Budget

For each component measure:

``` text
feature/query latency
model inference latency
post-processing latency
total component latency
```

Then measure end-to-end system latency separately.

------------------------------------------------------------------------

# 97. Model Size

Record:

``` text
artifact size
RAM use
CPU load
```

for final candidates.

This supports deployment justification.

------------------------------------------------------------------------

# 98. Main Computing Platform

Initial server-side/edge-site ML execution is intended for the GeoNex
Main Computing System:

``` text
Lenovo ThinkCentre M700
i5 6th generation
8 GB RAM
256 GB SSD
```

Therefore final models should be benchmarked on or against this
practical resource class.

------------------------------------------------------------------------

# 99. Microcontroller Models

Do not assume C1--C4 must run directly on ESP32.

ESP32 nodes primarily perform:

``` text
sensor acquisition
local aggregation
communication
local safety/fallback functions
```

Main ML inference can run on the local Main Computing System.

------------------------------------------------------------------------

# 100. Deployment Suitability Scorecard

For each final candidate produce:

  Factor              Weight/priority     Model A   Model B   Model C
  ------------------- ----------------- --------- --------- ---------
  predictive metric   high                                  
  critical recall     high                                  
  calibration         task-dependent                        
  robustness          high                                  
  latency             high                                  
  RAM/CPU             medium/high                           
  explainability      medium/high                           
  maintainability     medium                                

Weights must be justified rather than chosen to force a preferred
winner.

------------------------------------------------------------------------

# 101. Pareto Analysis

A useful model-selection concept is the Pareto frontier.

Model A may have:

``` text
higher accuracy
higher latency
```

while Model B has:

``` text
slightly lower accuracy
much lower latency
```

Neither dominates automatically.

Document the trade-off.

------------------------------------------------------------------------

# 102. Minimum Acceptability Gates

Before ranking models, define gates such as:

``` text
critical-class recall ≥ approved minimum
latency ≤ approved maximum
no leakage
integration tests pass
calibration acceptable where required
```

Exact numeric thresholds are deferred until experiments/domain review.

------------------------------------------------------------------------

# 103. Safety Beats Aggregate Score

If Model A has higher macro-F1 but repeatedly misses the most important
critical class, Model B may be preferable.

Selection must reflect system consequences.

------------------------------------------------------------------------

# 104. Robustness Beats Benchmark-Only Performance

A model that performs well only on clean synthetic data but collapses
under:

``` text
missing sensors
timing gaps
noise
mode changes
```

is not the strongest GeoNex model.

------------------------------------------------------------------------

# 105. Explainability Does Not Mean Simplicity Only

Complex models can still be studied through:

``` text
SHAP
ablation
occlusion
counterfactual perturbation
case studies
```

But explanations must not be presented as causal proof.

------------------------------------------------------------------------

# 106. Model Versioning

Every approved model needs:

``` text
component
model_version
algorithm
dataset_version
feature_schema_version
training code revision
metrics
approval status
```

------------------------------------------------------------------------

# 107. Model Lifecycle

Conceptually:

``` text
EXPERIMENTAL
CANDIDATE
APPROVED
SUPERSEDED
REJECTED
```

Only approved artifacts are used in normal runtime.

------------------------------------------------------------------------

# 108. Reproducibility Package

Each selected model should include:

``` text
training configuration
dataset manifest/hash
split definition
preprocessing
model artifact
calibration artifact
evaluation report
requirements/environment
seed
code revision
```

------------------------------------------------------------------------

# 109. Experiment Naming

Recommended:

``` text
C1_E05_LGBM_CONTEXT_V001
C2_E04_XGB_BACKUP_V001
C3_A05_GRUD_V001
C4_E06_HYBRID_LGBM_V001
```

Names should expose:

``` text
component
experiment
model
feature/ablation level
version
```

------------------------------------------------------------------------

# 110. Common Experiment Report

Every major experiment should produce:

``` text
objective
hypothesis
dataset
split
features
model
hyperparameters
metrics
confusion/error analysis
latency
resource use
limitations
conclusion
```

------------------------------------------------------------------------

# 111. Negative Result Policy

Negative results are valid research evidence.

Examples:

``` text
mode adds no benefit after Δt
GRU-D does not outperform XGBoost
C4 behavioural ML adds excessive false positives
C2 ML action selection offers no advantage over rules
```

Report them rather than hiding them.

------------------------------------------------------------------------

# 112. Avoiding Confirmation Bias

Do not define the proposed method as:

``` text
the model that must win
```

Define the research mechanism first.

Then let experiments determine:

``` text
whether
how much
under what conditions
```

it helps.

------------------------------------------------------------------------

# 113. Component Research Questions Together

``` text
C4:
Can source/transmission trust be strengthened through
deterministic verification + behavioural context?

C1:
Can rainfall/temporal/spatial context distinguish
genuine extreme events from faulty measurements?

C2:
Can mode-aware silence interpretation + independent backup evidence
improve failure diagnosis and recovery?

C3:
Can explicit timing/mode/quality provenance improve
future-risk forecasting under variable-rate sensing?
```

------------------------------------------------------------------------

# 114. Component Baselines Together

``` text
C1:
rules/statistics → RF → boosted trees

C2:
fixed timeout/rules → RF/XGBoost diagnosis → hybrid recovery

C3:
current-state/tree → standard GRU → time-aware recurrent

C4:
registration/deterministic → behavioural ML → hybrid
```

This provides a coherent escalation of evidence.

------------------------------------------------------------------------

# 115. Component Ablations Together

``` text
C1:
target → history → neighbours → rainfall

C2:
fixed timeout → mode-aware → backup verification → provenance recovery

C3:
sensors → history → Δt → mode → C1 → C2

C4:
identity → deterministic security → behavioural → hybrid → mode-aware hybrid
```

This is the core experimental architecture of GeoNex.

------------------------------------------------------------------------

# 116. Why This Strengthens the Overall Research

The project does not simply contain four disconnected models.

Each component addresses a different uncertainty:

``` text
C4 → source uncertainty
C1 → measurement uncertainty
C2 → availability/failure uncertainty
C3 → future-state uncertainty
```

The final system therefore forms a progressive uncertainty-management
pipeline.

------------------------------------------------------------------------

# 117. System-Level Ablation

Beyond component experiments, compare:

``` text
S0 — raw/basic telemetry → simple forecasting
S1 — + C4
S2 — + C1
S3 — + C2
S4 — + full C3 time-aware model
S5 — + adaptive mode policy
```

Exact experiment feasibility depends on available data.

------------------------------------------------------------------------

# 118. Integrated Metrics

Potential:

``` text
event recall
warning lead time
false alarms/day
percentage of rejected spoofed telemetry
genuine-event preservation
recovery success
end-to-end latency
transmission count
resource consumption
```

This demonstrates system value beyond isolated classifier scores.

------------------------------------------------------------------------

# 119. Adaptive Sampling Comparison

Compare:

``` text
fixed high-rate
fixed low-rate
GeoNex variable-rate
```

where feasible.

Measure:

``` text
forecast quality
warning latency
packet count
radio activity
energy proxy/measured power
```

Do not claim field battery-life extension from the centralized demo
power arrangement.

------------------------------------------------------------------------

# 120. Model Selection Review Meeting

Before freezing any final model, each member should present:

``` text
problem
dataset
leakage audit
baselines
candidate models
ablation
stress tests
metrics
latency
explainability
limitations
recommended winner
```

The team approves the model based on evidence.

------------------------------------------------------------------------

# 121. Required C1 Evidence Package

``` text
C1_DATASET_AUDIT
label specification
baseline report
context ablation
model comparison
confusion matrix
VALID_EVENT rejection analysis
SHAP/error cases
latency
final selection rationale
```

------------------------------------------------------------------------

# 122. Required C2 Evidence Package

``` text
C2 dataset/episode audit
mode-aware silence experiment
diagnostic model comparison
backup verification ablation
recovery comparison
possible-zone-damage analysis
latency
final selection rationale
```

------------------------------------------------------------------------

# 123. Required C3 Evidence Package

``` text
C3 dataset audit
target specification
event-aware split
tree baseline
mode-only baseline
GRU baseline
Time-Aware GRU
GRU-D
A0–A5 ablation
stress tests
calibration
lead time
false alarms/time
latency
final selection rationale
```

------------------------------------------------------------------------

# 124. Required C4 Evidence Package

``` text
threat model
dataset audit
trust-label specification
deterministic security test report
behavioural model comparison
hybrid ablation
authorized replay test
false accept/reject analysis
latency
final selection rationale
```

------------------------------------------------------------------------

# 125. Thesis/Paper Model Table

Eventually create a consolidated table:

  ------------------------------------------------------------------------------
  Component      Baseline       Proposed mechanism Selected model Why selected
  -------------- -------------- ------------------ -------------- --------------
  C1                            rainfall/spatial                  
                                credibility                       

  C2                            mode-aware                        
                                diagnosis + backup                

  C3                            time-aware                        
                                variable-rate                     
                                forecasting                       

  C4                            deterministic +                   
                                behavioural trust                 
  ------------------------------------------------------------------------------

Populate only after experiments.

------------------------------------------------------------------------

# 126. Viva Question --- Why Different Algorithms?

Recommended answer:

> The four components solve different classes of problems. C1, C2 and C4
> primarily operate on structured contextual evidence, so tree-based
> methods are strong, data-efficient candidates. C3 models irregular
> multivariate temporal sequences, which gives recurrent time-aware deep
> learning a stronger justification. We still compare each proposed
> approach against simpler baselines and select the final model
> experimentally.

------------------------------------------------------------------------

# 127. Viva Question --- Why Not Use Deep Learning for Everything?

Recommended answer:

> Deep learning is not automatically better. It normally requires more
> data and computation and can be harder to explain. We use it where the
> temporal structure justifies it, particularly C3, while testing more
> appropriate tabular models for the other components.

------------------------------------------------------------------------

# 128. Viva Question --- Why XGBoost/LightGBM?

Recommended answer:

> They are strong candidates for nonlinear tabular data, can capture
> interactions between environmental or device-health variables, work
> effectively with moderate datasets, and support explanation methods.
> But they are candidates, not predetermined winners; Random Forest and
> simpler baselines are also evaluated.

------------------------------------------------------------------------

# 129. Viva Question --- Why GRU-D/Time-Aware GRU?

Recommended answer:

> GeoNex deliberately changes sampling frequency according to risk, so
> consecutive observations may represent different elapsed times.
> Time-aware recurrent models can explicitly represent those intervals,
> and GRU-D additionally handles missingness and time since each
> variable was last observed. We compare them against standard GRU and
> boosted-tree baselines.

------------------------------------------------------------------------

# 130. Viva Question --- Why Does C4 Need ML if Cryptography Exists?

Recommended answer:

> Cryptography handles mandatory identity, integrity and freshness
> properties, and ML never replaces those controls. Behavioural ML is an
> additional layer for suspicious timing, radio, route or device
> patterns that can occur even when basic verification passes. The
> research evaluates whether this hybrid approach adds value.

------------------------------------------------------------------------

# 131. Viva Question --- Why Does C2 Need ML?

Recommended answer:

> Detecting that a stream is late can be rule-based and mode-aware, but
> diagnosing why it became silent can depend on several uncertain
> signals such as communication state, device health, neighbouring nodes
> and independent backup evidence. We compare ML diagnosis against
> deterministic baselines, while keeping safety-critical recovery rules
> deterministic where appropriate.

------------------------------------------------------------------------

# 132. Viva Question --- How Do You Know the Models Are Not Cheating?

Recommended answer:

> We explicitly audit target-derived and future features, split by event
> or scenario before generating overlapping temporal samples, fit
> preprocessing only on training data, keep synthetic scenario groups
> separated, and use out-of-fold upstream predictions when one component
> consumes another model's outputs.

------------------------------------------------------------------------

# 133. Viva Question --- What if the Simpler Model Wins?

Recommended answer:

> Then we select the simpler model if it satisfies the research and
> operational requirements. The contribution is the tested mechanism and
> evidence, not forcing a complex algorithm to win.

------------------------------------------------------------------------

# 134. Anti-Pattern --- Accuracy Competition

Do not present:

``` text
RF = 96%
XGBoost = 97%
GRU = 98%
therefore GRU is best
```

without:

``` text
split validity
class metrics
calibration
latency
stress testing
statistical uncertainty
```

------------------------------------------------------------------------

# 135. Anti-Pattern --- Predetermined Winner

Do not write thesis text claiming:

``` text
GRU-D is the final C3 model
```

before experiments.

Use:

``` text
candidate proposed architecture
```

until selection is complete.

------------------------------------------------------------------------

# 136. Anti-Pattern --- Algorithm Shopping

Do not train dozens of unrelated algorithms merely to produce a large
table.

Every candidate needs a reason.

A focused comparison is stronger.

------------------------------------------------------------------------

# 137. Anti-Pattern --- Hidden Rules Inside Labels

Do not create labels from a deterministic formula, feed the same formula
inputs to ML, obtain near-perfect accuracy, and claim discovery.

This is especially relevant to synthetic C1/C3/C4 datasets.

------------------------------------------------------------------------

# 138. Anti-Pattern --- Test-Set Tuning

Do not repeatedly alter:

``` text
features
thresholds
architecture
```

based on test results.

Use validation.

------------------------------------------------------------------------

# 139. Anti-Pattern --- One Metric

No component should be selected using only:

``` text
accuracy
```

Each has task-specific critical metrics.

------------------------------------------------------------------------

# 140. Anti-Pattern --- Ignoring Runtime

A model that cannot run reliably within the local system's
resource/timing requirements is not the best production model.

Benchmark actual deployment conditions.

------------------------------------------------------------------------

# 141. Anti-Pattern --- Ignoring Failure Modes

All final candidates require stress testing.

A clean-dataset benchmark alone is insufficient for an early-warning
system.

------------------------------------------------------------------------

# 142. Model Selection Workflow

``` text
STEP 1
freeze task/target

STEP 2
audit data/leakage

STEP 3
freeze split

STEP 4
implement simple baseline

STEP 5
implement strong conventional baseline

STEP 6
implement proposed mechanism

STEP 7
tune using validation

STEP 8
run ablation

STEP 9
run stress tests

STEP 10
measure calibration/latency/resources

STEP 11
select candidate

STEP 12
evaluate final test

STEP 13
document rationale

STEP 14
register approved artifact
```

------------------------------------------------------------------------

# 143. Model Selection Record

For each component create:

``` text
MODEL_SELECTION_RECORD.md
```

containing:

``` text
candidate models
selection criteria
results
trade-offs
winner
rejected alternatives
limitations
approval
```

------------------------------------------------------------------------

# 144. Selection Decision Example

Not final:

``` text
Model A:
F1 0.91
latency 4 ms
interpretable
stable

Model B:
F1 0.915
latency 60 ms
unstable across seeds

Decision:
Model A may be preferable
```

The highest score does not automatically win.

------------------------------------------------------------------------

# 145. Rejected Model Documentation

Record why an alternative was rejected:

``` text
no meaningful gain
overfit
poor critical recall
poor calibration
too slow
unstable
unnecessary complexity
```

This strengthens thesis justification.

------------------------------------------------------------------------

# 146. Final Research Claim Discipline

Use:

``` text
"Our experiments indicate..."
"Under the evaluated scenarios..."
"On the held-out dataset..."
```

Avoid:

``` text
"This model guarantees..."
"This is the best model for all landslides..."
```

------------------------------------------------------------------------

# 147. What Is Frozen by This Document

1.  Model choice is evidence-driven, not predetermined.
2.  Every component requires simple and strong baselines.
3.  Deep learning is principally justified for C3's temporal problem.
4.  Boosted trees are strong candidates for C1/C2/C4 but not guaranteed
    winners.
5.  C2 recovery and C4 mandatory security retain deterministic logic
    where appropriate.
6.  Final test data cannot be used for tuning.
7.  Event/scenario/group-aware splitting is required.
8.  Task-specific metrics supersede headline accuracy.
9.  Calibration is required where probability semantics affect
    decisions.
10. Latency/resource use are model-selection criteria.
11. Explainability/error analysis are required.
12. Ablations must test the proposed research mechanisms.
13. Stress testing is mandatory.
14. Synthetic, physical and external evidence must remain
    distinguishable.
15. Negative results are acceptable.
16. Simpler models may legitimately win.
17. Model artifacts and experiments must be versioned/reproducible.
18. Final selection rationale must document rejected alternatives.
19. C3 requires a mode-only shortcut baseline.
20. C4 ML cannot override mandatory security failure.
21. Integrated upstream predictions must be leakage-safe.
22. Final research claims must be bounded by evaluated evidence.

------------------------------------------------------------------------

# 148. Decisions Intentionally Deferred

Until experiments:

``` text
final C1 algorithm
final C2 diagnosis algorithm
final C2 action-selection mechanism beyond mandatory safety rules
final C3 architecture
final C4 behavioural algorithm
hyperparameters
feature subsets
classification thresholds
calibration methods
minimum acceptance thresholds
component-specific latency limits
final multi-criteria weights
```

------------------------------------------------------------------------

# 149. Next Document

Next:

``` text
10_GEONEX_RESEARCH_THEORY_AND_CONCEPTS.md
```

It should consolidate the scientific and technical theory required to
understand and defend GeoNex, including:

``` text
landslide precursor concepts
IoT sensing principles
sensor credibility
context-aware anomaly detection
missing-data mechanisms
fault diagnosis
redundancy and recovery
temporal forecasting
irregular time series
GRU/LSTM/GRU-D/time-aware recurrence
adaptive sampling
probability/calibration
cybersecurity fundamentals
authentication/integrity/replay
behavioural anomaly detection
provenance
edge AI
decision systems
research validation
```

It should explain the theory in a form useful for implementation, thesis
writing and viva preparation.

------------------------------------------------------------------------

# Document 09 Status

**`09_GEONEX_MODEL_SELECTION_AND_JUSTIFICATION.md` --- CROSS-COMPONENT
MODEL-SELECTION BASELINE READY**

GeoNex will not defend its models by saying they are modern or complex.
Each final model must be justified by **problem fit, valid held-out
evidence, baseline improvement, ablation, robustness, calibration where
relevant, explainability, operational latency and deployment
practicality.**
