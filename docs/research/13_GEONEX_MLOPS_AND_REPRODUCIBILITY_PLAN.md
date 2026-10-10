# 13_GEONEX_MLOPS_AND_REPRODUCIBILITY_PLAN.md

**Project:** GeoNex --- Smart Landslide Early Warning Prediction System
using IoT, Edge AI and Risk Analytics\
**Document:** MLOps, Model Lifecycle and Reproducibility Plan\
**Status:** MLOps Baseline v1\
**Depends on:** Documents 00--12\
**Audience:** All GeoNex component developers, integration developer,
research team\
**Purpose:** Define how GeoNex datasets, experiments, models,
configurations, deployments, retraining, promotion, rollback and
research evidence are versioned and reproduced.

------------------------------------------------------------------------

# 1. Why This Document Exists

GeoNex contains four research components whose models will evolve during
development.

Without lifecycle control, the team can easily reach situations such as:

``` text
"Which dataset trained this model?"
"Which split produced this accuracy?"
"Was preprocessing fitted using the test set?"
"Which C1 model generated the C3 training feature?"
"Which model was running during the demo?"
"Why is today's result different from yesterday's?"
"Can we reproduce the thesis table?"
```

This document prevents those failures.

------------------------------------------------------------------------

# 2. GeoNex MLOps Objective

GeoNex MLOps is not about building a large commercial cloud platform.

Its purpose is:

``` text
REPRODUCIBILITY
+
TRACEABILITY
+
CONTROLLED MODEL CHANGE
+
SAFE DEPLOYMENT
+
RESEARCH AUDITABILITY
```

for a university research prototype.

------------------------------------------------------------------------

# 3. Core Lifecycle

``` text
Raw / Operational Evidence
        ↓
Frozen Source Snapshot
        ↓
Versioned Dataset Builder
        ↓
Versioned Dataset
        ↓
Frozen Split
        ↓
Experiment
        ↓
Candidate Model
        ↓
Validation
        ↓
Promotion Decision
        ↓
Model Registry
        ↓
Deployment
        ↓
Runtime Monitoring
        ↓
New Validated Evidence
        ↓
Candidate Retraining
        ↓
Evaluation
        ↓
Promote OR Reject
```

------------------------------------------------------------------------

# 4. "Self-Learning" Definition

For GeoNex:

> **Self-learning means controlled cumulative retraining from newly
> collected, quality-controlled evidence, followed by evaluation and
> explicit promotion or rollback.**

It does **not** mean:

``` text
model modifies itself after every packet
model trains directly on its own predictions
model automatically deploys every retrained version
unreviewed online learning
```

------------------------------------------------------------------------

# 5. Controlled Cumulative Retraining

Canonical lifecycle:

``` text
COLLECT
→ C4 TRUST VALIDATION
→ C1 CREDIBILITY / QUALITY PROCESSING
→ C2 RECOVERY / PROVENANCE
→ GROUND-TRUTH / LABEL VALIDATION
→ FREEZE DATASET CANDIDATE
→ RETRAIN CANDIDATE
→ EVALUATE
→ COMPARE WITH CHAMPION
→ PROMOTE OR REJECT
→ ROLLBACK IF NECESSARY
```

------------------------------------------------------------------------

# 6. Human/Policy Gate

Model promotion is an explicit action.

A training script must not silently replace the deployed model.

Promotion requires:

``` text
evaluation complete
acceptance criteria checked
artifacts stored
version assigned
compatibility checked
approval recorded
```

------------------------------------------------------------------------

# 7. MLOps Scope

This plan covers:

``` text
C1 credibility models
C2 diagnostic models
C3 forecasting models
C4 behavioural models
shared feature builders
preprocessing artifacts
calibration models
datasets
splits
experiments
deployment manifests
runtime monitoring
```

Deterministic rules/security controls are versioned too, even when they
are not ML models.

------------------------------------------------------------------------

# 8. Artifact Classes

GeoNex should distinguish:

``` text
SOURCE DATA
DATASET
SPLIT
FEATURE SCHEMA
PREPROCESSOR
MODEL
CALIBRATOR
CONFIGURATION
EXPERIMENT
DEPLOYMENT
EVALUATION
```

Each has its own identity/version.

------------------------------------------------------------------------

# 9. Reproducibility Principle

A final result should be reconstructable from:

``` text
code version
+
dataset version
+
split version
+
configuration
+
random seed
+
environment
+
model/preprocessing version
```

------------------------------------------------------------------------

# 10. Source Data Is Not a Dataset

Operational database records are evidence.

A training dataset is a reproducible transformation of a frozen evidence
snapshot.

Therefore:

``` text
database query today
```

must not silently redefine an old experiment.

------------------------------------------------------------------------

# 11. Frozen Source Snapshot

Each formal dataset build should identify a stable source boundary.

Possible mechanisms:

``` text
database snapshot
source cutoff timestamp
immutable export
specific test_run_ids
external file hashes
```

------------------------------------------------------------------------

# 12. Source Snapshot Manifest

Record:

``` text
snapshot_id
created_at
source systems
query/filter definition
source cutoff
test runs included
file/table hashes where practical
record counts
builder compatibility
```

------------------------------------------------------------------------

# 13. Dataset Version

Recommended conceptual naming:

``` text
C1_DS_001
C2_DS_001
C3_DS_001
C4_DS_001
```

or semantic versions if preferred.

The exact naming convention can be implemented later, but every formal
dataset must be uniquely identifiable.

------------------------------------------------------------------------

# 14. Dataset Manifest

Every dataset version records:

``` text
dataset_version
component
created_at
source_snapshot_id
builder_version
schema_version
feature/field roles
target definition
row/sample count
class/event distribution
origin distribution
split strategy
known limitations
hashes
```

------------------------------------------------------------------------

# 15. Dataset Origin

Preserve:

``` text
PHYSICAL_DEMO
SYNTHETIC
EXTERNAL
SIMULATED
```

through dataset construction.

Do not erase evidence origin after feature engineering.

------------------------------------------------------------------------

# 16. Dataset Builder Version

The code that converts source evidence into ML samples must be
versioned.

Example concept:

``` text
C3_BUILDER_004
```

Changing window logic can change the dataset even if raw data is
identical.

------------------------------------------------------------------------

# 17. Deterministic Dataset Build

Given:

``` text
same source snapshot
same builder
same configuration
same seed where relevant
```

the dataset should be reproducible.

------------------------------------------------------------------------

# 18. Dataset Hash

Store a cryptographic/content hash for important frozen artifacts where
practical.

Purpose:

``` text
detect accidental modification
prove experiment input identity
```

------------------------------------------------------------------------

# 19. Field Roles

Dataset manifests should explicitly classify columns as:

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

Models should consume only approved feature fields.

------------------------------------------------------------------------

# 20. No "All Columns Except Label"

Never use:

``` python
X = df.drop("label")
```

as the final research feature definition without an explicit feature
allowlist.

Identifiers/debug fields can leak scenario/target information.

------------------------------------------------------------------------

# 21. Split Version

A split is a research artifact.

Example:

``` text
C3_SPLIT_001
```

Record:

``` text
train groups
validation groups
test groups
strategy
seed
time boundaries
zone/event grouping
```

------------------------------------------------------------------------

# 22. Freeze Test Set

Once selected for final evaluation:

``` text
test set is not used for iterative model selection
```

If it becomes development data, define a new final test protocol
transparently.

------------------------------------------------------------------------

# 23. Group-Aware Split

Component-specific grouping remains mandatory where appropriate:

``` text
C1 → event/scenario/device/time
C2 → fault/scenario/test run
C3 → event/time block/zone before windows
C4 → attack/scenario/session/device
```

------------------------------------------------------------------------

# 24. Preprocessing Fit Boundary

Any learned preprocessing must fit only on training data.

Examples:

``` text
scaler
imputer
encoder
feature selector
calibrator training stage
```

------------------------------------------------------------------------

# 25. Preprocessor Artifact

Store fitted preprocessing with the model.

Example:

``` text
C3_PREP_003
```

Runtime must not refit preprocessing from live data.

------------------------------------------------------------------------

# 26. Feature Schema Version

Every model references:

``` text
feature_schema_version
```

This defines:

``` text
feature names
order
units
transformations
mask semantics
window semantics
```

------------------------------------------------------------------------

# 27. Model Version

Every trained model gets an immutable model version.

Conceptual:

``` text
C1_MODEL_007
C2_MODEL_005
C3_MODEL_012
C4_MODEL_006
```

Never overwrite an existing model artifact and keep the same version.

------------------------------------------------------------------------

# 28. Model Registry

The registry stores metadata for every candidate and deployed model.

At minimum:

``` text
model_version
component
algorithm
created_at
dataset_version
split_version
feature_schema_version
preprocessor_version
code_version
configuration
metrics
artifact path/hash
status
```

------------------------------------------------------------------------

# 29. Model Status

Recommended lifecycle:

``` text
EXPERIMENTAL
CANDIDATE
VALIDATED
CHAMPION
REJECTED
RETIRED
```

A separate deployment state may indicate what is currently active.

------------------------------------------------------------------------

# 30. Champion and Challenger

For each component:

``` text
CHAMPION
= currently approved model

CHALLENGER
= new candidate being evaluated
```

The challenger must demonstrate sufficient evidence before replacing the
champion.

------------------------------------------------------------------------

# 31. Experiment ID

Every training/evaluation run gets an ID.

Example:

``` text
C3_EXP_20261010_001
```

The exact naming format is configurable.

------------------------------------------------------------------------

# 32. Experiment Record

Store:

``` text
experiment_id
component
research question
dataset_version
split_version
feature set
model type
hyperparameters
seed
environment
training metrics
validation metrics
test metrics if final
artifacts
notes
```

------------------------------------------------------------------------

# 33. Experiment Configuration

Prefer configuration files over hardcoded experiment settings.

Conceptual:

``` yaml
component: C3
dataset_version: C3_DS_004
split_version: C3_SPLIT_002
history_minutes: ...
horizon_minutes: ...
model:
  type: ...
training:
  seed: ...
```

Values shown in actual configs must reflect approved experiments.

------------------------------------------------------------------------

# 34. Configuration Immutability

Once an experiment is recorded, preserve the exact configuration used.

Do not edit it later to represent another run.

------------------------------------------------------------------------

# 35. Code Version

Every formal experiment records:

``` text
Git commit SHA
```

or equivalent repository version.

This connects results to exact implementation.

------------------------------------------------------------------------

# 36. Dirty Working Tree

For final experiments, avoid running from uncommitted code.

If unavoidable, record:

``` text
dirty = true
```

and preserve the patch/diff.

------------------------------------------------------------------------

# 37. Random Seeds

Record seeds for:

``` text
data splitting
model initialization
sampling
synthetic generation
```

where applicable.

Seeds improve reproducibility but do not guarantee identical results
across all hardware/libraries.

------------------------------------------------------------------------

# 38. Repeated Seeds

For stochastic final models, evaluate several documented seeds where
feasible.

Do not select only the best lucky seed.

------------------------------------------------------------------------

# 39. Environment Specification

Record software dependencies.

Possible artifacts:

``` text
requirements.txt
pyproject.toml
lock file
environment.yml
Dockerfile
```

Use one reproducible method appropriate to the final repository.

------------------------------------------------------------------------

# 40. Python Version

Record exact Python version for formal experiments.

Library behavior can differ across versions.

------------------------------------------------------------------------

# 41. Hardware Metadata

For compute-sensitive experiments record:

``` text
CPU
GPU if used
RAM
OS
```

This is especially relevant for training/inference-time comparisons.

------------------------------------------------------------------------

# 42. Artifact Directory

Conceptual:

``` text
artifacts/
├── datasets/
├── splits/
├── preprocessors/
├── models/
├── calibrators/
├── evaluations/
├── plots/
└── deployments/
```

Large artifacts need not all be committed to Git.

------------------------------------------------------------------------

# 43. Git Rule

Commit:

``` text
code
schemas
small configs
manifests
tests
documentation
```

Do not blindly commit:

``` text
large raw datasets
database dumps
large model checkpoints
secrets
temporary experiment files
```

------------------------------------------------------------------------

# 44. Artifact Storage

For the research prototype, artifact storage can initially be:

``` text
controlled local/project storage
+
metadata registry
+
backup
```

A cloud MLOps platform is not required.

------------------------------------------------------------------------

# 45. Artifact Naming

Names should expose identity, not arbitrary labels such as:

``` text
final_model.pkl
final_final_model2.pkl
```

Prefer:

``` text
C1_MODEL_007.*
```

------------------------------------------------------------------------

# 46. Artifact Hash

Important model/preprocessing artifacts should have hashes where
practical.

At deployment, verify the loaded artifact matches the registered
version.

------------------------------------------------------------------------

# 47. Training Pipeline

Canonical component training pipeline:

``` text
load manifest
→ verify dataset
→ load frozen split
→ fit preprocessing on train
→ transform train/validation
→ train candidate
→ evaluate validation
→ tune using train/validation only
→ fit/calibrate according to approved protocol
→ final held-out evaluation
→ save artifacts
→ register model
```

------------------------------------------------------------------------

# 48. Training Pipeline Must Fail Loudly

Stop training if:

``` text
dataset hash mismatch
target missing
feature schema mismatch
split overlap detected
future leakage test fails
required metadata missing
```

Do not silently continue.

------------------------------------------------------------------------

# 49. Leakage Gate

Before formal training run automated checks for:

``` text
target-derived feature
future timestamp
group overlap
same synthetic base scenario across split
runtime-unavailable feature
post-action C2 feature
future/recommended mode
```

as relevant.

------------------------------------------------------------------------

# 50. C1 Training Pipeline

C1 training records:

``` text
target taxonomy
sensor type scope
context windows
rainfall-regime definition
neighbour selection
feature schema
class handling
model/calibration
```

------------------------------------------------------------------------

# 51. C2 Training Pipeline

C2 training records separately:

``` text
silence detection policy
diagnostic dataset
failure taxonomy
backup verification availability
diagnostic model
action policy
recovery evaluation
```

Do not hide deterministic action rules inside the diagnosis model
artifact.

------------------------------------------------------------------------

# 52. C3 Training Pipeline

C3 records:

``` text
history window
forecast horizon
sequence representation
Δt semantics
mask semantics
mode representation
C1/C2 feature versions
target event definition
censoring rules
model
calibration
threshold evaluation
```

------------------------------------------------------------------------

# 53. C4 Training Pipeline

C4 records:

``` text
threat/scenario taxonomy
deterministic security policy version
behavioural feature schema
attack grouping
model
thresholds
```

Mandatory deterministic checks remain separately versioned.

------------------------------------------------------------------------

# 54. Upstream Model Dependency

If C3 uses learned C1/C2 outputs, its manifest must identify which
upstream model versions generated them.

Example:

``` text
c1_feature_source_model = C1_MODEL_007
c2_feature_source_model = C2_MODEL_005
```

------------------------------------------------------------------------

# 55. Out-of-Fold Upstream Features

For downstream training, learned upstream predictions should be
generated using leakage-safe out-of-fold/disjoint models.

Do not train C1 on a row and then give C1's in-sample prediction on that
row to C3 as if it were runtime-equivalent.

------------------------------------------------------------------------

# 56. OOF Provenance

Record:

``` text
upstream_oof_strategy
fold/group assignment
upstream model version/fold
prediction timestamp/build version
```

------------------------------------------------------------------------

# 57. Ground Truth Is Separate

New model predictions do not become labels automatically.

Labels require:

``` text
controlled test truth
external reference
human/research annotation
verified event record
```

depending on the task.

------------------------------------------------------------------------

# 58. Pseudo-Labels

If pseudo-labeling is ever investigated, it must be:

``` text
explicit
separately tagged
experimentally justified
```

It is not part of the baseline controlled retraining workflow.

------------------------------------------------------------------------

# 59. Retraining Trigger

Retraining may be considered when:

``` text
sufficient new validated data collected
new physical test campaign completed
distribution changes meaningfully
known weakness receives new evidence
scheduled research milestone reached
```

It should not occur simply because one new packet arrived.

------------------------------------------------------------------------

# 60. Minimum New Data

No universal minimum sample count is frozen.

The retraining decision depends on:

``` text
class/event coverage
data quality
independence
component
research objective
```

------------------------------------------------------------------------

# 61. Candidate Dataset Build

New evidence is not appended blindly.

It passes:

``` text
schema checks
trust/quality checks
provenance checks
label validation
duplicate checks
```

before inclusion.

------------------------------------------------------------------------

# 62. Historical Data Retention

New cumulative dataset versions may include prior validated data plus
new evidence.

Keep previous dataset versions reproducible.

Do not overwrite them.

------------------------------------------------------------------------

# 63. Dataset Lineage

Example:

``` text
C3_DS_003
   ↓ + validated October test campaign
C3_DS_004
```

Manifest records parent dataset(s) and newly added evidence.

------------------------------------------------------------------------

# 64. Candidate Retraining

A retraining run produces:

``` text
new candidate model
```

not a replacement champion.

------------------------------------------------------------------------

# 65. Candidate Evaluation Gate

Compare candidate against champion on:

``` text
same approved validation/test framework
critical class/event metrics
calibration
robustness
latency/resource requirements
```

------------------------------------------------------------------------

# 66. No Single-Metric Promotion

Do not promote solely because:

``` text
accuracy increased
```

while:

``` text
critical recall decreased
calibration worsened
latency became unacceptable
```

------------------------------------------------------------------------

# 67. Component-Specific Promotion Criteria --- C1

Consider:

``` text
macro-F1
VALID_EVENT recall
ANOMALY recall
dangerous VALID_EVENT → ANOMALY rate
calibration
stress robustness
```

------------------------------------------------------------------------

# 68. Component-Specific Promotion Criteria --- C2

Consider:

``` text
diagnosis macro-F1
critical failure recall
backup verification performance
recovery success
recovery latency
false escalation
```

------------------------------------------------------------------------

# 69. Component-Specific Promotion Criteria --- C3

Consider:

``` text
event recall
PR-AUC
false alarm rate
calibration/Brier
warning lead time
missing-data robustness
inference latency
```

------------------------------------------------------------------------

# 70. Component-Specific Promotion Criteria --- C4

Consider:

``` text
mandatory security correctness
attack/untrusted recall
false acceptance
false rejection
behavioural added value
runtime latency
```

------------------------------------------------------------------------

# 71. Regression Gate

A candidate must also pass existing regression tests.

Model improvement must not break:

``` text
schema
runtime API
integration
resource limits
critical known scenarios
```

------------------------------------------------------------------------

# 72. Promotion Record

Record:

``` text
promotion_id
candidate version
previous champion
evaluation report
decision
approver/team decision
date
reason
```

------------------------------------------------------------------------

# 73. Deployment Manifest

Every deployment should state:

``` text
deployment_id
environment
deployed_at
C1 model/version
C2 model/version
C3 model/version
C4 model/version
feature schemas
preprocessors
decision policy
sampling policy
security policy
code version
```

------------------------------------------------------------------------

# 74. Complete System Version

For demonstrations/research runs, create a system release identity.

Example:

``` text
GEONEX_DEMO_R1
```

This maps to the exact collection of component/config versions.

------------------------------------------------------------------------

# 75. Deployment Compatibility

Before activation verify:

``` text
model ↔ feature schema
model ↔ preprocessor
service ↔ contract schema
Decision Engine ↔ forecast contract
firmware ↔ sampling policy
```

------------------------------------------------------------------------

# 76. Atomic Model Activation

Avoid partially replacing model files while inference is active.

Preferred conceptual process:

``` text
download/copy candidate
→ verify hash
→ load
→ health check
→ switch active reference
```

------------------------------------------------------------------------

# 77. Runtime Model Loading

At startup log:

``` text
component
model version
artifact hash
feature schema
preprocessor version
load status
```

------------------------------------------------------------------------

# 78. Runtime Prediction Trace

Every model output already carries:

``` text
model_version
generated_at
```

and should be traceable to its input.

This allows later comparison between deployed versions.

------------------------------------------------------------------------

# 79. Rollback

Keep the previous approved champion available.

If a new model causes:

``` text
runtime errors
schema incompatibility
unexpected degradation
unsafe behavior
```

switch back to the previous known-good version.

------------------------------------------------------------------------

# 80. Rollback Record

Record:

``` text
rollback_id
from_version
to_version
reason
time
affected deployment
```

------------------------------------------------------------------------

# 81. Model Failure Is Not Prediction

If a model cannot load or infer:

``` text
MODEL_UNAVAILABLE
PROCESSING_ERROR
```

must propagate.

Never silently substitute a normal/safe class.

------------------------------------------------------------------------

# 82. Shadow Evaluation

Where feasible, a challenger may run in:

``` text
shadow mode
```

where it receives runtime inputs but does not control decisions.

Its outputs can be compared safely against the champion.

------------------------------------------------------------------------

# 83. Shadow Output

Shadow predictions must be clearly tagged so they cannot enter
operational Decision Engine logic accidentally.

------------------------------------------------------------------------

# 84. Monitoring Categories

Runtime monitoring includes:

``` text
SYSTEM HEALTH
DATA QUALITY
INPUT DISTRIBUTION
MODEL OUTPUT
OPERATIONAL OUTCOME
```

These are distinct.

------------------------------------------------------------------------

# 85. System Health Monitoring

Track:

``` text
service availability
model load failures
inference errors
latency
memory/CPU
queue backlog
database errors
```

------------------------------------------------------------------------

# 86. Data Quality Monitoring

Track:

``` text
missingness
staleness
sensor read failures
range/plausibility flags
C1 credibility distribution
C2 recovery frequency
C4 trust distribution
```

------------------------------------------------------------------------

# 87. Input Distribution Monitoring

Compare recent feature distributions with the training reference where
meaningful.

Potential methods:

``` text
summary statistics
histograms
PSI
KS-type comparisons
distance measures
```

No single drift statistic is mandatory.

------------------------------------------------------------------------

# 88. Drift Is Not Automatically Failure

A distribution change may represent:

``` text
real environmental change
seasonality
new hardware
sensor drift
attack
data pipeline bug
```

Therefore drift triggers investigation, not automatic
retraining/deployment.

------------------------------------------------------------------------

# 89. Concept Drift

Concept drift means the relationship between input and target changes.

It can only be evaluated when new ground truth becomes available.

Do not infer concept drift solely from changed input distribution.

------------------------------------------------------------------------

# 90. C1 Monitoring

Potential:

``` text
class distribution
sensor-specific anomaly rate
VALID_EVENT frequency
confidence/calibration when labels later available
```

------------------------------------------------------------------------

# 91. C2 Monitoring

Potential:

``` text
silence-event rate
failure diagnoses
backup activation
recovery success
recovery latency
escalation frequency
```

------------------------------------------------------------------------

# 92. C3 Monitoring

Potential:

``` text
risk probability distribution
forecast frequency
input missingness
input age
mode distribution
calibration/performance once event labels arrive
```

------------------------------------------------------------------------

# 93. C4 Monitoring

Potential:

``` text
trust distribution
mandatory security failures
replay detections
behavioural anomalies
false rejection after investigation
```

------------------------------------------------------------------------

# 94. Monitoring Reference Window

Any drift/reference comparison must define:

``` text
reference dataset/window
current window
feature
method
threshold
```

Exact windows/thresholds are deferred.

------------------------------------------------------------------------

# 95. Alert on Pipeline Failure

Operational alerts should exist for important failures such as:

``` text
model not loaded
feature schema mismatch
database unavailable
extreme queue delay
persistent inference failure
```

These are engineering alerts, not landslide warnings.

------------------------------------------------------------------------

# 96. Retraining Is Not a Drift Reflex

Correct:

``` text
drift detected
→ investigate
→ validate data
→ obtain labels/evidence
→ build candidate dataset
→ retrain
→ evaluate
→ promote if justified
```

Incorrect:

``` text
drift detected
→ retrain and deploy automatically
```

------------------------------------------------------------------------

# 97. Cumulative Learning Audit

Every cumulative retraining cycle should answer:

``` text
What new data was added?
Why was it trusted?
How was it labeled?
What previous data remained?
What changed in performance?
Why was the candidate promoted/rejected?
```

------------------------------------------------------------------------

# 98. Retraining Cycle ID

Example:

``` text
C3_RETRAIN_003
```

Record:

``` text
parent champion
parent dataset
new dataset
new evidence
candidate model
evaluation
decision
```

------------------------------------------------------------------------

# 99. Roll-Forward vs Rollback

If a deployed model is poor:

``` text
rollback
```

returns to known-good artifact.

A later corrected model is:

``` text
new version
```

not an overwrite of the failed version.

------------------------------------------------------------------------

# 100. Reproducible Evaluation Script

Metrics should be generated from scripts, not manually calculated for
the thesis.

Conceptual:

``` text
evaluate_c1.py
evaluate_c2.py
evaluate_c3.py
evaluate_c4.py
```

Final naming may differ.

------------------------------------------------------------------------

# 101. Generated Research Tables

Where practical generate:

``` text
baseline comparison tables
ablation tables
confusion matrices
calibration metrics
stress-test tables
```

directly from stored experiment results.

------------------------------------------------------------------------

# 102. Generated Figures

Figures should record:

``` text
source experiment IDs
dataset versions
script version
```

so they can be recreated.

------------------------------------------------------------------------

# 103. Notebook Policy

Notebooks are useful for exploration.

Final reproducible pipelines should move critical logic into versioned
modules/scripts.

Avoid final results that exist only as manually executed notebook cells.

------------------------------------------------------------------------

# 104. Experiment Notebook Header

Each notebook should state:

``` text
purpose
dataset_version
experiment_id
date
author
status: exploratory/final
```

------------------------------------------------------------------------

# 105. Synthetic Generator Version

Synthetic datasets must identify:

``` text
generator version
seed
scenario parameters
```

Changing generator logic creates a new dataset lineage.

------------------------------------------------------------------------

# 106. Historical C3 Synthetic Artifacts

Existing files such as:

``` text
basic_c3_sensor_data.csv
c3_temporal_synthetic_v2.csv
c3_temporal_synthetic_v3.csv
v4 generator work
```

remain historical development artifacts until audited and migrated into
the formal versioned dataset system.

They should not be silently renamed as final evidence.

------------------------------------------------------------------------

# 107. Synthetic Scenario Leakage

The same underlying generated storm/event/scenario must not appear
across training and test through overlapping or slightly modified rows.

Group by scenario identity.

------------------------------------------------------------------------

# 108. Physical Test Data Versioning

Physical prototype data should record:

``` text
test_run_id
hardware version
firmware version
calibration version
sampling policy
environment/test setup
```

------------------------------------------------------------------------

# 109. External Dataset Versioning

For external data record:

``` text
source
retrieval date/version
license/usage terms
original files/hashes
transformations
```

Do not silently modify source files.

------------------------------------------------------------------------

# 110. Data Corrections

If a dataset error is found:

``` text
create corrected dataset version
```

Do not overwrite the original formal version.

------------------------------------------------------------------------

# 111. Label Corrections

Record:

``` text
old label
new label
reason
annotation version
```

where feasible.

This is especially important for research ground truth.

------------------------------------------------------------------------

# 112. Model Serialization

Use stable supported serialization appropriate to the framework.

Examples may include:

``` text
joblib/pickle with controlled environment
native XGBoost/LightGBM format
PyTorch state_dict/checkpoint
ONNX if justified
```

Final choice is component-specific.

------------------------------------------------------------------------

# 113. Serialization Security

Do not load untrusted arbitrary serialized model files.

Model artifacts are internal controlled project artifacts.

------------------------------------------------------------------------

# 114. Neural Checkpoint

For neural models store:

``` text
architecture/config
weights
preprocessing reference
feature schema
training metadata
```

Weights alone are insufficient.

------------------------------------------------------------------------

# 115. Tree Model Artifact

Store:

``` text
model
feature list/order
preprocessing
class mapping
threshold/calibration if applicable
```

------------------------------------------------------------------------

# 116. Probability Calibration Artifact

If post-hoc calibration is used, it has its own identity/version and
training provenance.

Do not silently replace raw model probability semantics.

------------------------------------------------------------------------

# 117. Threshold Artifact/Policy

Operational thresholds should be versioned separately where appropriate.

Examples:

``` text
C3 warning operating point
C1 action threshold
C4 behavioural threshold
```

------------------------------------------------------------------------

# 118. Decision Policy Is Not C3 Model

A new Decision Engine threshold does not necessarily require retraining
C3.

Version:

``` text
forecast model
```

and:

``` text
decision policy
```

separately.

------------------------------------------------------------------------

# 119. Sampling Policy Is Not Model Version

Changing sensor rates creates a new:

``` text
sampling_policy_version
```

not a new C3 model version unless the model itself changes.

------------------------------------------------------------------------

# 120. Calibration Version Is Not Model Version

Changing physical sensor calibration creates:

``` text
calibration_version
```

and may require dataset/model reevaluation, but should not be hidden
inside a model name.

------------------------------------------------------------------------

# 121. Schema Compatibility Matrix

Maintain a compatibility record such as:

  Artifact          Requires
  ----------------- -------------------------------------------------
  C1 model          C1 feature schema + preprocessor
  C2 model          C2 feature schema + taxonomy
  C3 model          C3 feature schema + upstream semantics
  C4 model          C4 feature schema + security policy assumptions
  Decision policy   C3 forecast contract + system health contract

------------------------------------------------------------------------

# 122. Runtime Compatibility Failure

If deployed model expects:

``` text
C3FS_004
```

but runtime produces:

``` text
C3FS_005
```

the system should fail readiness/compatibility checks rather than guess.

------------------------------------------------------------------------

# 123. Migration Test

When a feature schema changes:

``` text
build old sample
build new sample
document difference
test migration/compatibility
```

------------------------------------------------------------------------

# 124. Backup Strategy

Back up important:

``` text
source evidence
dataset manifests
formal datasets
model registry
champion artifacts
experiment metadata
thesis-result artifacts
```

------------------------------------------------------------------------

# 125. Backup Verification

A backup that has never been restored is not fully validated.

Perform test restoration of important artifacts before final submission.

------------------------------------------------------------------------

# 126. Retention

Do not delete prior:

``` text
champions
formal datasets
final experiment artifacts
```

during the research period unless storage policy requires it and
evidence is safely archived elsewhere.

------------------------------------------------------------------------

# 127. Secrets Management

Never place:

``` text
DB passwords
API tokens
private keys
device secrets
```

inside experiment configs committed to the repository.

Use environment/secrets mechanisms.

------------------------------------------------------------------------

# 128. `.gitignore`

At minimum consider excluding:

``` text
.env
secrets
temporary datasets
large generated artifacts
local DB files
IDE/cache files
```

according to final repository structure.

------------------------------------------------------------------------

# 129. Logging

Training logs should capture:

``` text
experiment ID
dataset
model
epoch/iteration
metrics
warnings/errors
duration
```

Runtime logs capture deployed model identity.

------------------------------------------------------------------------

# 130. Audit Log

Important lifecycle actions:

``` text
dataset frozen
model registered
model promoted
model rejected
deployment changed
rollback
manual label correction
```

should be auditable.

------------------------------------------------------------------------

# 131. Access Control

Only authorized team/integration workflows should modify:

``` text
champion status
deployment manifest
ground-truth labels
formal dataset versions
```

The exact access-control mechanism depends on deployment.

------------------------------------------------------------------------

# 132. CI Checks

When repository automation is available, run:

``` text
unit tests
schema tests
contract tests
lint/static checks
critical leakage tests
```

before merging relevant changes.

------------------------------------------------------------------------

# 133. Model Training Is Not Necessarily CI

Full training may be too expensive/slow for every commit.

CI can run:

``` text
small smoke training
feature tests
pipeline tests
```

while formal training is an explicit workflow.

------------------------------------------------------------------------

# 134. Training Smoke Test

Use a tiny controlled dataset to verify:

``` text
pipeline executes
artifact saves
model reloads
prediction contract works
```

This tests software, not scientific performance.

------------------------------------------------------------------------

# 135. Model Reload Test

Every saved model should be reloaded in a clean process and produce
compatible output before registration/promotion.

------------------------------------------------------------------------

# 136. Reproduction Test

Before final reporting, another team member/environment should reproduce
at least key final experiments from:

``` text
instructions
config
dataset
code
```

without relying on hidden notebook state.

------------------------------------------------------------------------

# 137. Thesis Result Freeze

Before thesis submission freeze:

``` text
final dataset versions
final split versions
final model versions
final experiment IDs
final figures/tables
```

and record them in a result manifest.

------------------------------------------------------------------------

# 138. Paper Result Freeze

If an ICAC/other paper uses a subset or earlier prototype:

``` text
create separate paper result manifest
```

so later project changes do not alter what the paper reported.

------------------------------------------------------------------------

# 139. Result Manifest

Conceptual:

``` yaml
result_set: GEONEX_THESIS_FINAL
c1:
  model: ...
  dataset: ...
  experiments: [...]
c2:
  model: ...
c3:
  model: ...
c4:
  model: ...
system_tests:
  - ...
```

------------------------------------------------------------------------

# 140. Demo Release Manifest

Before the final demonstration record exact:

``` text
firmware versions
database schema
services
models
policies
hardware configuration
```

------------------------------------------------------------------------

# 141. Demo Model Freeze

Do not retrain a model immediately before a critical demo without
completing validation.

Use a known tested release.

------------------------------------------------------------------------

# 142. Development vs Research Models

A quick development model may exist for pipeline testing.

Tag it:

``` text
EXPERIMENTAL
```

Do not accidentally report its metrics as final research results.

------------------------------------------------------------------------

# 143. Baseline Registry

Store important baseline models too.

This ensures proposed models remain comparable throughout the project.

------------------------------------------------------------------------

# 144. C1 Baseline Registry

Examples:

``` text
range/plausibility rule
value-only model
history model
neighbour model
full context model
```

------------------------------------------------------------------------

# 145. C2 Baseline Registry

Examples:

``` text
fixed timeout
mode-aware deterministic diagnosis
diagnostic ML without backup
diagnostic ML with backup
```

------------------------------------------------------------------------

# 146. C3 Baseline Registry

Examples:

``` text
threshold/persistence
tabular boosted tree
standard GRU/LSTM
time-aware candidate
```

------------------------------------------------------------------------

# 147. C4 Baseline Registry

Examples:

``` text
deterministic security only
behavioural only
hybrid
```

------------------------------------------------------------------------

# 148. Ablation Registry

Treat each important ablation as a formal experiment configuration.

This makes thesis contribution tables reproducible.

------------------------------------------------------------------------

# 149. Stress-Test Registry

Store standard stress configurations:

``` text
missing sensor
long gap
short gap
stale neighbour
mode transition
recovered input
radio degradation
attack scenario
```

so multiple model versions can be compared consistently.

------------------------------------------------------------------------

# 150. Evaluation Dataset Stability

When comparing champion and challenger, use the same frozen evaluation
sets.

Do not make the challenger look better by changing the test data.

------------------------------------------------------------------------

# 151. New Distribution Evaluation

If new evidence represents a genuinely new distribution, evaluate:

``` text
old reference test
+
new distribution test
```

where possible.

This exposes regression vs adaptation trade-offs.

------------------------------------------------------------------------

# 152. Catastrophic Forgetting Check

For cumulative retraining, ensure performance on important historical
scenarios does not collapse.

Evaluate previous benchmark suites.

------------------------------------------------------------------------

# 153. Rare Critical Cases

Preserve dedicated evaluation sets for rare high-consequence cases where
available.

Examples:

``` text
C1 genuine extreme
C2 possible zone damage
C3 actual/critical event windows
C4 replay/tamper
```

------------------------------------------------------------------------

# 154. Class Distribution Tracking

Every dataset version records class/event distribution.

This helps identify whether apparent improvement is due merely to easier
data composition.

------------------------------------------------------------------------

# 155. Data Duplication Check

Check exact and near-duplicate records/scenarios.

Duplicate leakage can dramatically inflate research results.

------------------------------------------------------------------------

# 156. Data Contamination Check

Ensure:

``` text
test events
```

are not indirectly encoded in:

``` text
scenario IDs
filenames
timestamps
generator flags
debug fields
```

used as features.

------------------------------------------------------------------------

# 157. C3 Censoring Version

C3 dataset manifest must document how windows without complete future
horizon are handled.

This logic is part of the dataset builder version.

------------------------------------------------------------------------

# 158. C3 Multi-Horizon Versioning

If multiple horizons are supported, record whether the model uses:

``` text
separate models
multi-head outputs
horizon as input
```

and version the output semantics.

------------------------------------------------------------------------

# 159. C3 Threshold Selection

Select operational threshold using validation data/policy objectives.

Store:

``` text
threshold
selection method
validation experiment
policy version
```

Do not optimize threshold on final test set.

------------------------------------------------------------------------

# 160. C1 Rainfall-Regime Version

If rainfall regimes are discretized:

``` text
definition/thresholds
```

must be versioned.

Changing them changes feature semantics.

------------------------------------------------------------------------

# 161. C2 Expected-Report Policy Version

C2 silence labels/features depend on active sampling policy.

Record the policy version used in dataset generation and runtime
diagnosis.

------------------------------------------------------------------------

# 162. C4 Security Policy Version

C4 behavioral data must record deterministic security policy
assumptions.

A packet considered fresh under one policy may not be under another.

------------------------------------------------------------------------

# 163. Calibration Drift

If physical sensors are recalibrated:

``` text
record new calibration
compare behavior
consider model compatibility
```

Do not silently mix incompatible calibration scales.

------------------------------------------------------------------------

# 164. Hardware Revision

If a sensor/device is replaced with materially different hardware:

``` text
hardware_revision
```

should be recorded.

This may create distribution shift.

------------------------------------------------------------------------

# 165. Firmware Revision

Telemetry behavior can change with firmware.

Formal physical data records should include:

``` text
firmware_version
```

------------------------------------------------------------------------

# 166. Sampling Policy in Dataset

Because GeoNex is variable-rate, C3 data must retain the policy/mode
context that produced observations.

This supports both modeling and bias analysis.

------------------------------------------------------------------------

# 167. Selection Bias Risk

Adaptive sampling means high-risk periods may be observed more densely.

Dataset analysis must account for this.

Do not assume rows are uniformly sampled independent observations.

------------------------------------------------------------------------

# 168. Feedback Loop Risk

Conceptually:

``` text
C3 risk
→ Decision Engine increases mode
→ more observations
→ future C3 training data
```

This creates policy-dependent data.

Record mode/policy provenance to analyze it.

------------------------------------------------------------------------

# 169. Retraining Feedback Safety

Do not let the model learn blindly from a dataset whose labels/coverage
are heavily determined by its own previous decisions without analyzing
this feedback loop.

------------------------------------------------------------------------

# 170. Monitoring Without Labels

When ground truth is delayed/unavailable, monitor:

``` text
input quality
distribution
prediction distribution
system behavior
```

but do not claim true predictive accuracy.

------------------------------------------------------------------------

# 171. Delayed Labels

When later event truth becomes available, link it to previous forecasts
without rewriting those forecasts.

Then compute retrospective performance.

------------------------------------------------------------------------

# 172. Model Evaluation Time

Store:

``` text
evaluated_at
```

and evaluation dataset/version.

Metrics are properties of:

``` text
model + dataset + evaluation protocol
```

not of model alone.

------------------------------------------------------------------------

# 173. Recalculated Metrics

If evaluation code changes, create a new evaluation record.

Do not silently replace old published metrics.

------------------------------------------------------------------------

# 174. Research Claim Traceability

Each major thesis claim should map to:

``` text
experiment IDs
tables/figures
dataset versions
model versions
```

------------------------------------------------------------------------

# 175. Example C3 Claim Trace

``` text
Claim:
Explicit Δt improves robustness under irregular sampling.

Evidence:
C3_EXP_041 vs C3_EXP_042

Same:
dataset
split
model family
features

Difference:
Δt representation

Metrics:
PR-AUC
event recall
Brier
gap stress test
```

------------------------------------------------------------------------

# 176. Example C2 Claim Trace

``` text
Claim:
Backup verification improves failure diagnosis.

Evidence:
same held-out fault scenarios
without backup features
vs
with backup verification
```

------------------------------------------------------------------------

# 177. Example C1 Claim Trace

``` text
Claim:
Rainfall/neighbour context reduces rejection of genuine extreme readings.

Evidence:
context ablation
+
VALID_EVENT recall/error analysis
```

------------------------------------------------------------------------

# 178. Example C4 Claim Trace

``` text
Claim:
Behavioural analysis adds detection value beyond deterministic checks.

Evidence:
deterministic-only
vs
hybrid
on held-out behavioral attack scenarios
```

------------------------------------------------------------------------

# 179. Reproducibility Checklist

Before marking an experiment final:

-   [ ] dataset version known
-   [ ] source snapshot known
-   [ ] split version known
-   [ ] feature schema known
-   [ ] preprocessing stored
-   [ ] config stored
-   [ ] code commit stored
-   [ ] environment stored
-   [ ] seed stored
-   [ ] model artifact stored
-   [ ] evaluation script stored
-   [ ] metrics stored
-   [ ] plots reproducible
-   [ ] leakage checks passed
-   [ ] limitations recorded

------------------------------------------------------------------------

# 180. Promotion Checklist

Before champion promotion:

-   [ ] candidate registered
-   [ ] validation complete
-   [ ] critical metrics checked
-   [ ] baseline/champion comparison complete
-   [ ] calibration checked if needed
-   [ ] stress tests passed
-   [ ] latency/resources acceptable
-   [ ] contract compatibility passed
-   [ ] model reload passed
-   [ ] regression suite passed
-   [ ] deployment manifest prepared
-   [ ] rollback artifact available
-   [ ] promotion decision recorded

------------------------------------------------------------------------

# 181. Retraining Checklist

Before cumulative retraining:

-   [ ] new evidence identified
-   [ ] origin known
-   [ ] trust/quality checked
-   [ ] labels independently validated
-   [ ] duplicates checked
-   [ ] previous dataset retained
-   [ ] new dataset version created
-   [ ] split strategy reviewed
-   [ ] feedback-loop risk reviewed
-   [ ] candidate only, no automatic deployment

------------------------------------------------------------------------

# 182. Rollback Checklist

When rollback is needed:

-   [ ] identify issue
-   [ ] disable affected candidate
-   [ ] restore previous champion
-   [ ] verify artifact hash
-   [ ] run health/readiness check
-   [ ] record rollback
-   [ ] preserve failed version/evidence
-   [ ] create regression test if applicable

------------------------------------------------------------------------

# 183. Recommended Lightweight Tooling

GeoNex can implement the baseline with:

``` text
Git
Python
configuration files
structured manifests
PostgreSQL/TimescaleDB
filesystem/object-style artifact storage
pytest
optional MLflow or similar experiment tracker
```

A specific MLOps platform is not mandatory.

------------------------------------------------------------------------

# 184. MLflow Position

MLflow is a reasonable candidate for:

``` text
experiment tracking
metric logging
artifact logging
model registry
```

but GeoNex architecture must not depend on it conceptually.

If not used, equivalent metadata must still be preserved.

------------------------------------------------------------------------

# 185. DVC Position

DVC or similar tooling can help version large datasets/artifacts.

It is optional.

Dataset lineage/versioning requirements remain mandatory regardless of
tool.

------------------------------------------------------------------------

# 186. Containerization

Docker can improve reproducibility for:

``` text
database
services
training environment
```

but hardware/serial/LoRa development may still require native host
access.

Use it where it reduces complexity rather than adding unnecessary
overhead.

------------------------------------------------------------------------

# 187. Recommended Repository Areas

Conceptually:

``` text
configs/
experiments/
models/
data/
shared/schemas/
tests/
scripts/
docs/
```

The final repository guide will freeze exact organization.

------------------------------------------------------------------------

# 188. One-Command Reproduction Goal

For important experiments, aim for a command conceptually like:

``` text
python run_experiment.py --config configs/c3/exp_041.yaml
```

that regenerates the experiment from registered inputs.

Exact CLI is implementation-specific.

------------------------------------------------------------------------

# 189. One-Command Evaluation Goal

Likewise:

``` text
python evaluate.py --model C3_MODEL_012 --dataset C3_DS_TEST_003
```

should conceptually regenerate metrics.

------------------------------------------------------------------------

# 190. Do Not Hide Manual Steps

If an experiment requires manual annotation/calibration:

``` text
document it
```

rather than pretending the pipeline is fully automatic.

------------------------------------------------------------------------

# 191. AI-Assisted Development

AI may assist with:

``` text
code drafting
debugging
documentation
experiment planning
```

but final research artifacts must be:

``` text
reviewed
executed
verified
versioned
```

by the project team.

------------------------------------------------------------------------

# 192. AI Must Not Invent Results

No model metric, test outcome, calibration curve or hardware measurement
may be generated as a claimed result without executing the corresponding
experiment.

------------------------------------------------------------------------

# 193. Data Governance Rule

Never modify evidence merely to improve model performance.

Cleaning must be:

``` text
rule-based
documented
versioned
```

with original data retained.

------------------------------------------------------------------------

# 194. Failure Reproducibility

When a model/pipeline fails unexpectedly, preserve enough information to
recreate:

``` text
input
version
configuration
error
environment
```

------------------------------------------------------------------------

# 195. Definition of MLOps Readiness

GeoNex is MLOps-ready when the team can answer:

``` text
Which model is deployed?
Which data trained it?
Which code created it?
Which features does it expect?
How was it evaluated?
Why was it promoted?
Can we reproduce it?
Can we roll it back?
```

for every component.

------------------------------------------------------------------------

# 196. Definition of Controlled Self-Learning Success

The "self-learning" mechanism is successfully demonstrated when GeoNex
can show:

``` text
Version N deployed
        ↓
new validated evidence collected
        ↓
Dataset N+1 created
        ↓
Candidate Model N+1 trained
        ↓
candidate evaluated against Version N
        ↓
promotion/rejection decision recorded
        ↓
if promoted, deployment updated
        ↓
previous champion retained for rollback
```

This is a stronger and safer research implementation than uncontrolled
online adaptation.

------------------------------------------------------------------------

# 197. Example Controlled Retraining Demonstration

For C3, a research demo could show:

``` text
1. C3_MODEL_003 is champion.
2. New physical/synthetic validated scenarios are collected.
3. C3_DS_004 is created with documented lineage.
4. C3_MODEL_004 candidate is trained.
5. Same benchmark suite evaluates both.
6. Candidate improves selected critical metrics without unacceptable regression.
7. Candidate is promoted.
8. Deployment manifest changes.
9. C3_MODEL_003 remains available.
```

Numbers above are illustrative version labels, not existing results.

------------------------------------------------------------------------

# 198. What Is Frozen by Document 13

1.  GeoNex self-learning is controlled cumulative retraining, not
    uncontrolled online learning.
2.  Runtime inference and model training remain separate.
3.  New data does not automatically become training data.
4.  Predictions do not automatically become ground truth.
5.  Formal datasets are immutable/versioned.
6.  Dataset builders are versioned.
7.  Source snapshots are traceable.
8.  Splits are versioned research artifacts.
9.  Final test sets are protected from iterative tuning.
10. Preprocessing fits on training data only.
11. Feature schemas are versioned.
12. Models are immutable/versioned.
13. Model artifacts link to dataset, split, code and config.
14. Candidate models do not automatically replace champions.
15. Promotion uses multiple operational/research criteria.
16. Previous champions remain available for rollback.
17. Deployment manifests identify the complete active
    model/configuration set.
18. Runtime outputs identify model versions.
19. Upstream learned features used downstream require leakage-safe
    OOF/disjoint generation.
20. Drift triggers investigation, not automatic deployment.
21. Concept drift requires outcome/label evidence.
22. Synthetic generators and scenarios are versioned.
23. Physical data records hardware/firmware/calibration/test-run
    context.
24. Model, decision-policy, sampling-policy and calibration versions
    remain distinct.
25. Important artifacts are backed up and restoration is tested.
26. Final research results map to reproducible experiment IDs.
27. Failed and rejected models remain part of the research audit trail.
28. AI-assisted work cannot invent experimental results.
29. A model lifecycle action must be traceable.
30. GeoNex must be able to reproduce and roll back deployed research
    models.

------------------------------------------------------------------------

# 199. Decisions Still Deferred

This document intentionally does not freeze:

``` text
MLflow adoption
DVC adoption
exact artifact server/storage
exact version-number syntax
exact CI/CD platform
exact retraining schedule
exact drift metric
exact drift thresholds
exact promotion numeric thresholds
exact number of random seeds
exact container strategy
exact model serialization per component
exact backup destination
exact access-control implementation
```

These are implementation choices, not reasons to weaken the lifecycle
requirements.

------------------------------------------------------------------------

# 200. Recommended Implementation Order

``` text
1. Create shared version/manifest schemas.
2. Freeze dataset directory conventions.
3. Implement dataset manifests.
4. Implement split manifests.
5. Add experiment configuration format.
6. Add experiment IDs/logging.
7. Add model registry metadata.
8. Save preprocessing with models.
9. Add artifact hashes.
10. Add model reload/compatibility tests.
11. Add champion/candidate status.
12. Add deployment manifest.
13. Add rollback mechanism.
14. Add runtime model-version logging.
15. Add monitoring metrics.
16. Implement controlled retraining workflow.
17. Run one complete retraining/promotion rehearsal.
18. Freeze thesis/paper result manifests.
```

------------------------------------------------------------------------

# 201. Next Documentation Stage

The core technical baseline documents 00--13 now cover:

``` text
system development
architecture
database/data
datasets
mode/sampling/timing
C1
C2
C3
C4
model selection
research theory
integration contracts
testing/validation
MLOps/reproducibility
```

The next documentation should move toward the actual repository and
implementation environment.

Recommended next document:

``` text
14_GEONEX_REPOSITORY_AND_IMPLEMENTATION_GUIDE.md
```

It should freeze:

``` text
final repository structure
service/module ownership
Python package structure
shared schemas
configuration layout
database migrations
firmware directories
component boundaries
tests
scripts
artifacts
Git workflow
branching
environment setup
local run commands
coding conventions
member workflow
```

After that, create the root:

``` text
README.md
CONTRIBUTING.md
```

and begin implementation against the frozen baseline.

------------------------------------------------------------------------

# Document 13 Status

**`13_GEONEX_MLOPS_AND_REPRODUCIBILITY_PLAN.md` --- MLOPS BASELINE v1
READY**

The governing lifecycle is:

``` text
NEW DATA
   ↓
VALIDATE EVIDENCE
   ↓
VERSION DATASET
   ↓
TRAIN CANDIDATE
   ↓
EVALUATE AGAINST CHAMPION
   ↓
        ┌──────────────┐
        │              │
     PROMOTE         REJECT
        │              │
        ↓              ↓
    DEPLOY         ARCHIVE RESULT
        │
        ↓
    MONITOR
        │
        ↓
ROLLBACK IF REQUIRED
```

GeoNex does not become stronger because a model retrains itself
frequently.

It becomes stronger because every learning cycle is **controlled,
measurable, reproducible and reversible**.
