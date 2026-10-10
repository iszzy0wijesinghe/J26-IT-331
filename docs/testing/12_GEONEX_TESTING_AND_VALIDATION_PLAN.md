# 12_GEONEX_TESTING_AND_VALIDATION_PLAN.md

**Project:** GeoNex --- Smart Landslide Early Warning Prediction System
using IoT, Edge AI and Risk Analytics\
**Document:** Complete Testing and Validation Plan\
**Status:** Validation Baseline v1\
**Depends on:** Documents 00--11\
**Audience:** Entire GeoNex research team\
**Purpose:** Define how GeoNex will be tested scientifically and
technically so that component, integration, prototype and research
claims are supported by reproducible evidence rather than by a
successful demonstration alone.

------------------------------------------------------------------------

# 1. Why This Document Exists

GeoNex contains:

``` text
physical sensors
embedded firmware
wireless communication
local storage
database systems
security controls
four research components
machine-learning models
recovery mechanisms
adaptive sensing
Decision Engine logic
alerts
```

A system this complex cannot be validated by reporting one final
accuracy value.

Validation must answer:

``` text
Does each sensor behave as expected?
Does firmware collect the correct values?
Does communication preserve the data?
Can faults be detected and recovered?
Do models generalize?
Are probabilities meaningful?
Does variable-rate sensing actually help?
Does security reject intended threats?
Does the complete system behave safely when something fails?
```

------------------------------------------------------------------------

# 2. Validation Philosophy

GeoNex validation follows:

``` text
UNIT
→ COMPONENT
→ CONTRACT
→ INTEGRATION
→ HARDWARE-IN-LOOP
→ END-TO-END
→ RESEARCH EXPERIMENT
→ DEMONSTRATION
```

Passing a later layer does not replace earlier testing.

------------------------------------------------------------------------

# 3. Evidence Hierarchy

Different evidence supports different claims.

``` text
Synthetic experiment
→ algorithm/pipeline behaviour under controlled assumptions

Bench test
→ hardware/software behaviour under controlled physical conditions

Fault injection
→ recovery/security behaviour under deliberately created failures

Prototype demonstration
→ integrated system feasibility

Field data
→ behaviour under real deployment conditions
```

Do not present one category as another.

------------------------------------------------------------------------

# 4. Core Validation Rule

For every important claim record:

``` text
claim
test
input
ground truth/reference
metric
acceptance criterion
result
evidence artifact
limitations
```

------------------------------------------------------------------------

# 5. Test Identification

Recommended ID pattern:

``` text
HW-xxx
FW-xxx
NET-xxx
DB-xxx
C1-xxx
C2-xxx
C3-xxx
C4-xxx
INT-xxx
E2E-xxx
SEC-xxx
PERF-xxx
PWR-xxx
```

Exact numbering can be maintained in a test registry.

------------------------------------------------------------------------

# 6. Test Record Template

Every formal test should record:

``` text
test_id
title
objective
date/time
operator
hardware/software versions
configuration
dataset/test_run_id
preconditions
procedure
expected result
actual result
pass/fail
measurements
evidence files
notes/limitations
```

------------------------------------------------------------------------

# 7. Test Run ID

Physical and simulated experiments should carry:

``` text
test_run_id
```

through telemetry where possible.

This allows database records to be associated with a specific controlled
experiment.

------------------------------------------------------------------------

# 8. Evidence Folder

Recommended conceptual structure:

``` text
evidence/
├── calibration/
├── hardware/
├── firmware/
├── network/
├── c1/
├── c2/
├── c3/
├── c4/
├── integration/
├── end_to_end/
├── latency/
├── power/
└── demo/
```

Each test should have machine-readable results plus human-readable notes
where practical.

------------------------------------------------------------------------

# 9. Reproducibility Metadata

Research experiments should preserve:

``` text
dataset_version
split_version
code commit
model version
configuration
random seed
library/environment versions
hardware where relevant
```

------------------------------------------------------------------------

# 10. Acceptance Criteria

Acceptance criteria should be defined before inspecting final test
results where possible.

Avoid:

``` text
"We got 83%, therefore 83% is acceptable."
```

Instead define the criterion from:

``` text
research objective
baseline
safety relevance
operational requirement
available evidence
```

------------------------------------------------------------------------

# 11. No Universal Accuracy Threshold

This document does not invent a universal target such as:

``` text
accuracy > 95%
```

because appropriate performance depends on:

``` text
task
class imbalance
baseline
data quality
cost of errors
deployment conditions
```

Research success is based on defensible improvement and operational
relevance.

------------------------------------------------------------------------

# 12. Hardware Validation Scope

Hardware testing covers:

``` text
Type A Pipe
Type B Pipe
Backup Pipe
Centralized Sensor Hub
Centralized Power Hub
Main Gateway electronics
Main Computing System interfaces
```

Type A/B tests begin after physical construction.

------------------------------------------------------------------------

# 13. Hardware Inventory Verification

Before functional testing verify:

``` text
device ID
board type
sensor instances
wiring
power input
communication interface
firmware version
physical label
```

Do not assume the planned BOM exactly matches the assembled prototype.

------------------------------------------------------------------------

# 14. Visual Evidence

Photographs should document:

``` text
assembled device
sensor placement
wiring
test setup
measurement/reference instrument
```

where relevant.

Photos are supporting evidence, not quantitative validation by
themselves.

------------------------------------------------------------------------

# 15. Power Wiring Test

Before connecting sensitive electronics:

``` text
verify supply polarity
verify output voltage
verify fuse placement
verify common ground where required
inspect shorts
```

Use safe electrical procedures.

------------------------------------------------------------------------

# 16. Centralized Power Hub Test

Validate:

``` text
SMPS output
distribution outputs
master switch
fuse paths
voltage stability under representative load
connector polarity
```

The Power Hub is demo infrastructure, not an environmental sensing node.

------------------------------------------------------------------------

# 17. Backup Power Test

For Backup Pipes validate separately:

``` text
battery operation
charging path
solar input behaviour where testable
voltage/current monitoring
transition behaviour
```

Do not infer long-term field battery life from a short bench test.

------------------------------------------------------------------------

# 18. Sensor Bring-Up Test

For every sensor instance:

``` text
device detects sensor
read operation succeeds
values change plausibly under stimulus
errors are logged
sensor ID/channel mapping is correct
```

------------------------------------------------------------------------

# 19. Soil-Moisture Sensor Test

Controlled tests should evaluate:

``` text
dry condition response
increasing moisture response
wet/saturated-like response
repeatability
sensor-to-sensor differences
```

If physical moisture units are claimed, calibration against a justified
reference method is required.

------------------------------------------------------------------------

# 20. Soil-Moisture Calibration

A calibration experiment should record:

``` text
raw ADC/value
reference moisture condition
temperature/context
sensor instance
replicates
fitted relationship
error
valid range
```

Each calibration gets a version.

------------------------------------------------------------------------

# 21. FSR402 Test

Validate:

``` text
no-load response
increasing applied load/contact response
repeatability
hysteresis if present
ADC range
saturation
```

Without force calibration, report relative/raw response.

------------------------------------------------------------------------

# 22. DHT22 Test

Where used:

``` text
compare temperature/humidity with a reasonable reference
test stable environment
test changing environment
record missing/read-error rate
```

------------------------------------------------------------------------

# 23. DS18B20 Test

Validate:

``` text
device addressing
temperature response
repeatability
error handling
```

If multiple sensors share a bus, verify identity remains stable.

------------------------------------------------------------------------

# 24. MPU9250/MPU6050 Test

Validate:

``` text
stationary baseline
known orientation changes
repeatability
noise
sampling stability
```

For movement/vibration features also verify local feature calculations.

------------------------------------------------------------------------

# 25. IMU Orientation Test

Use controlled orientations such as:

``` text
level
known tilt increments
return to level
```

Compare estimated orientation with the physical reference method used.

------------------------------------------------------------------------

# 26. IMU Vibration Test

Create controlled repeatable disturbances.

Measure whether:

``` text
RMS
variance
peak
other selected summaries
```

respond consistently.

Do not label arbitrary vibration as landslide movement.

------------------------------------------------------------------------

# 27. INA219/INA226 Test

Compare voltage/current measurements with an appropriate reference
instrument under several loads.

Record:

``` text
bias
error
repeatability
range
```

These sensors primarily support power/system-health analysis.

------------------------------------------------------------------------

# 28. ADS1115 Test

Validate:

``` text
channel mapping
known input voltages
gain/range configuration
repeatability
noise
```

------------------------------------------------------------------------

# 29. Rainfall Mechanism Test

The Centralized Sensor Hub rainfall mechanism requires controlled
calibration.

Use known water quantities/rates where feasible.

Measure:

``` text
raw load/level response
collection relationship
reset/drain behaviour
repeatability
overflow/saturation
```

------------------------------------------------------------------------

# 30. Rainfall Calibration Output

Produce:

``` text
calibration curve
error summary
valid operating range
calibration_version
```

Do not report rainfall in physical units until the mapping is justified.

------------------------------------------------------------------------

# 31. Barometer Test

If used, compare pressure response against a reasonable reference and
verify stability.

Its inclusion in C3 remains evidence-driven.

------------------------------------------------------------------------

# 32. Ultrasonic Module Test

If the visible HC-SR04-type module is actually used:

``` text
define what physical quantity it measures
test distance/reference response
document environmental limitations
```

Do not include it in research features merely because it exists
physically.

------------------------------------------------------------------------

# 33. Sensor Cross-Talk Test

Where multiple sensors share:

``` text
power
ADC
bus
physical enclosure
```

verify one sensor's operation does not corrupt another.

------------------------------------------------------------------------

# 34. Long-Run Hardware Stability

Run representative devices continuously.

Track:

``` text
read failures
reboots
memory issues
temperature
communication loss
timestamp drift
```

Duration should be documented rather than described vaguely as
"long-term."

------------------------------------------------------------------------

# 35. Firmware Unit Tests

Where logic can run off-device, test:

``` text
packet serialization
CRC/integrity preparation
sampling scheduler
mode transitions
buffer management
SD replay selection
command parsing
duplicate command handling
```

------------------------------------------------------------------------

# 36. Firmware Sensor Mapping Test

Verify every packet field maps to the correct physical sensor/channel.

A perfectly trained model is useless if channels are swapped.

------------------------------------------------------------------------

# 37. Firmware Timestamp Test

Verify:

``` text
timestamp creation
RTC behavior
boot/session handling
clock synchronization
```

Record known clock uncertainty/drift.

------------------------------------------------------------------------

# 38. Firmware Sequence Test

Verify sequence numbers:

``` text
increment normally
handle reboot/session change
do not unexpectedly reset within session
```

------------------------------------------------------------------------

# 39. Local Buffer Test

If devices buffer data:

``` text
disconnect communication
continue acquisition
restore communication
verify stored data
```

Check:

``` text
observed_at preserved
sequence preserved
no silent loss
```

------------------------------------------------------------------------

# 40. SD Replay Test

Request a defined historical interval.

Verify:

``` text
only authorized/requested records returned
historical timestamps preserved
new arrival time recorded
duplicates controlled
C4 can distinguish authorized replay
```

------------------------------------------------------------------------

# 41. Mode Application Test

For each mode:

``` text
DEEP_SLEEP
IDLE
RISK
WARNING
EMERGENCY
```

verify the device applies the correct versioned sampling profile.

Exact rates come from the active policy.

------------------------------------------------------------------------

# 42. Acquisition vs Reporting Test

Verify independently:

``` text
sensor read frequency
local aggregation behavior
radio report frequency
```

Do not infer acquisition frequency from packet frequency.

------------------------------------------------------------------------

# 43. Local Event Trigger Test

If deterministic local triggers are implemented:

``` text
create trigger condition
verify temporary sampling/report change
verify event packet
verify return policy
```

The trigger must not be described as AI prediction.

------------------------------------------------------------------------

# 44. Firmware Watchdog/Recovery Test

Where implemented:

``` text
induce recoverable firmware fault
verify restart/recovery
record boot/session change
ensure C4/C2 interpret it correctly
```

------------------------------------------------------------------------

# 45. LoRa Link Test

Measure under controlled conditions:

``` text
packet delivery
RSSI
SNR
latency
retries
```

across representative distances/obstructions available to the prototype.

Do not claim the nominal module range as experimentally achieved range.

------------------------------------------------------------------------

# 46. Packet Size Test

Test actual GeoNex packet sizes.

Verify:

``` text
serialization size
airtime implications
fragmentation if any
delivery reliability
```

------------------------------------------------------------------------

# 47. Multi-Device Radio Test

Operate multiple devices concurrently.

Measure:

``` text
collision/loss
latency
throughput
fairness
```

especially under higher-risk reporting modes.

------------------------------------------------------------------------

# 48. Radio Stress Test

Increase packet/report activity within safe/configured limits.

Observe:

``` text
loss
queue buildup
retry growth
latency
```

This helps validate adaptive sampling scalability.

------------------------------------------------------------------------

# 49. Network Disconnection Test

Temporarily block/disconnect a device.

Expected:

``` text
expected-report scheduler notices absence
C2 creates silence event
recovery/escalation path executes
```

------------------------------------------------------------------------

# 50. Gateway Restart Test

Restart gateway electronics/software.

Verify:

``` text
devices recover communication
duplicates controlled
sessions handled
database continuity preserved
```

------------------------------------------------------------------------

# 51. Main Computer Restart Test

Restart the Main Computing System/software stack.

Verify:

``` text
raw data safety
service recovery
model loading
database consistency
device communication restoration
```

------------------------------------------------------------------------

# 52. Database Migration Test

For every migration:

``` text
apply to clean DB
apply to previous supported schema
verify constraints/indexes
test rollback strategy where applicable
```

------------------------------------------------------------------------

# 53. Database Constraint Test

Verify invalid data cannot silently violate key invariants such as:

``` text
unknown device reference
duplicate canonical ID
invalid enum
missing required timestamp
```

------------------------------------------------------------------------

# 54. Raw Immutability Test

After downstream processing:

``` text
raw packet
raw observation
```

must remain unchanged.

Derived corrections appear separately.

------------------------------------------------------------------------

# 55. Provenance Trace Test

Choose a forecast and trace backwards:

``` text
forecast
→ input manifest
→ Golden observations
→ C1/C2/C4 records
→ sensor observations
→ raw packets
```

Every link should resolve.

------------------------------------------------------------------------

# 56. Runtime/Retrospective Test

Create a late recovered observation.

Verify:

``` text
retrospective history sees it
past runtime forecast input does not
```

------------------------------------------------------------------------

# 57. Duplicate Ingestion Test

Submit the same packet twice.

Expected:

``` text
duplicate recognized
no duplicate physical observation created unintentionally
audit evidence retained
```

------------------------------------------------------------------------

# 58. Out-of-Order Ingestion Test

Submit packets in reverse arrival order.

Verify:

``` text
observed order preserved correctly
arrival order preserved separately
```

------------------------------------------------------------------------

# 59. Database Performance Test

Measure representative:

``` text
insert rate
time-window query latency
Golden Timeline query
C3 feature retrieval
```

using realistic prototype data volume.

------------------------------------------------------------------------

# 60. C1 Validation Objective

C1 must demonstrate that context improves sensor credibility
classification, especially:

``` text
detecting anomalies
without rejecting genuine hazardous extremes
```

------------------------------------------------------------------------

# 61. C1 Ground Truth

Labels must come from:

``` text
controlled fault injection
known synthetic generation
independent annotation/reference
```

not from C1's own predictions.

------------------------------------------------------------------------

# 62. C1 Baseline Experiments

Mandatory comparison:

``` text
B0 — simple plausibility/range rule
B1 — target value only
B2 — target + temporal history
B3 — target + temporal + neighbours
P  — target + temporal + neighbours + rainfall/context
```

Exact naming can differ.

------------------------------------------------------------------------

# 63. C1 Candidate Models

Evaluate justified candidates such as:

``` text
Random Forest
XGBoost
LightGBM
```

The winner is selected experimentally.

------------------------------------------------------------------------

# 64. C1 Split Strategy

Prefer grouping by:

``` text
event/scenario
time block
device/zone
```

as appropriate.

Synthetic variants derived from the same base event must not cross
train/test.

------------------------------------------------------------------------

# 65. C1 Metrics

Report:

``` text
macro-F1
per-class precision
per-class recall
confusion matrix
balanced accuracy if useful
```

Critical:

``` text
VALID_EVENT recall
ANOMALY recall
VALID_EVENT → ANOMALY error
```

------------------------------------------------------------------------

# 66. C1 Genuine-Extreme Test

Create/evaluate cases where:

``` text
target value is extreme
rainfall supports it
neighbours support it
```

C1 should avoid treating all such cases as faults.

------------------------------------------------------------------------

# 67. C1 Fault Injection

Candidate controlled anomalies:

``` text
stuck value
spike
dropout
impossible jump
bias/drift
sensor-specific corruption
```

Only inject patterns appropriate to the tested sensor.

------------------------------------------------------------------------

# 68. C1 Context Removal Ablation

Remove:

``` text
rainfall
neighbours
history
```

one at a time.

Measure contribution.

------------------------------------------------------------------------

# 69. C1 Missing-Context Stress Test

Test:

``` text
missing neighbour
stale rainfall
partial history
```

C1 should return meaningful degraded/context status.

------------------------------------------------------------------------

# 70. C1 Calibration Test

If C1 probabilities drive downstream policy:

``` text
reliability diagram
Brier score
ECE if selected
```

should be evaluated.

------------------------------------------------------------------------

# 71. C1 Explainability Test

For representative:

``` text
CLEAN
ANOMALY
VALID_EVENT
```

cases inspect feature contributions.

Check whether the model is relying on scientifically sensible features
rather than IDs/leakage.

------------------------------------------------------------------------

# 72. C1 Acceptance Logic

C1 succeeds scientifically if the proposed context-aware configuration:

``` text
improves meaningful metrics over simpler baselines
and/or
reduces dangerous genuine-event rejection
```

under held-out conditions.

No fabricated percentage threshold is frozen here.

------------------------------------------------------------------------

# 73. C2 Validation Objective

C2 must demonstrate that:

``` text
mode-aware expected-report reasoning
+
diagnostic context
+
backup verification
+
provenance-aware recovery
```

provide value beyond simple timeout and blind imputation.

------------------------------------------------------------------------

# 74. C2 Silence Detection Baseline

Compare:

``` text
fixed global timeout
```

against:

``` text
mode/policy-aware expected-report deadline
```

Measure false/missed silence detections and detection latency.

------------------------------------------------------------------------

# 75. C2 Fault Injection Matrix

Controlled scenarios should include where physically/software feasible:

``` text
single sensor failure
primary pipe/device failure
communication block
hub/network failure
multiple sensor gap
power interruption
SD replay requirement
backup unavailable
possible wider zone disruption pattern
```

------------------------------------------------------------------------

# 76. C2 Diagnosis Ground Truth

Because faults are deliberately injected, the test controller records
the true fault type independently.

C2 predictions are compared against that record.

------------------------------------------------------------------------

# 77. C2 Diagnosis Metrics

Report:

``` text
macro-F1
per-class precision/recall
confusion matrix
critical class recall
```

especially:

``` text
POSSIBLE_ZONE_DAMAGE / escalation-relevant recall
```

according to final taxonomy.

------------------------------------------------------------------------

# 78. C2 Backup Ablation

Compare:

``` text
diagnosis without backup verification
vs
diagnosis with backup verification
```

This directly tests the research value of the Backup Pipe.

------------------------------------------------------------------------

# 79. C2 Recovery Tests

For each implemented recovery:

``` text
REQUEST_SD_REPLAY
ACTIVATE_BACKUP_SENSOR
USE_NEIGHBOR_FUSION
SWITCH_BACKUP_HUB if physically supported
ESCALATE
```

measure success/failure and latency.

------------------------------------------------------------------------

# 80. C2 SD Replay Accuracy

Where original local records exist, recovered replay should match them
exactly apart from transport metadata.

Verify:

``` text
value
sensor identity
observed_at
sequence
```

------------------------------------------------------------------------

# 81. C2 Fusion Accuracy

For neighbour/model-based reconstructed values:

``` text
hide known original value
perform recovery
compare estimate with held-out original
```

Report appropriate error metric.

------------------------------------------------------------------------

# 82. C2 Provenance Test

Every recovered value must correctly identify:

``` text
LATE_ORIGINAL
BACKUP
FUSED
DERIVED
```

as applicable.

------------------------------------------------------------------------

# 83. C2 Recovery Latency

Measure:

``` text
silence detected
→ diagnosis
→ action
→ usable recovered data / escalation
```

Report distribution, not only best case.

------------------------------------------------------------------------

# 84. C2 Unknown Case

Present an unsupported/ambiguous failure pattern.

C2 should not be forced to confidently misclassify it if the final
design supports an unknown/degraded state.

------------------------------------------------------------------------

# 85. C2 Acceptance Logic

C2 succeeds if it demonstrates measurable advantage over:

``` text
fixed timeout
+
blind missing-value handling
```

in diagnosis/recovery quality and operational interpretability.

------------------------------------------------------------------------

# 86. C3 Validation Objective

C3 must demonstrate whether:

``` text
history
+
real elapsed time
+
operating mode
+
credibility/recovery provenance
```

improve future-risk forecasting under variable-rate/missing sensing.

------------------------------------------------------------------------

# 87. C3 Ground Truth

Primary event target can be:

``` text
target_landslide_within_horizon
```

only when event occurrence/timing is independently grounded.

Synthetic event labels must remain identified as synthetic.

------------------------------------------------------------------------

# 88. C3 Forecast Origin

For every sample define:

``` text
forecast origin T
history [T-W, T]
target interval (T, T+H]
```

No future evidence enters the history.

------------------------------------------------------------------------

# 89. C3 Split Before Windows

Split:

``` text
events/time blocks/zones
```

before creating overlapping sequences.

This prevents near-duplicate windows crossing train/test.

------------------------------------------------------------------------

# 90. C3 Baselines

Mandatory:

``` text
B0 — persistence/simple threshold
B1 — static tabular LightGBM/XGBoost
B2 — standard GRU/LSTM
P  — time-aware candidate such as Time-Aware GRU / GRU-D
```

Final candidate set follows actual implementation resources.

------------------------------------------------------------------------

# 91. C3 Core Ablation

Evaluate:

``` text
A0 Sensors
A1 + History
A2 + Δt
A3 + Mode
A4 + C1 credibility
A5 + C2 recovery/provenance
```

This is central evidence for C3.

------------------------------------------------------------------------

# 92. C3 Fixed-Rate vs Variable-Rate Test

Where feasible compare:

``` text
naively resampled/fixed-rate representation
```

against:

``` text
variable-rate-aware representation preserving Δt/masks/age
```

under identical held-out events.

------------------------------------------------------------------------

# 93. C3 Mode-Only Shortcut Test

Train/evaluate a simple predictor using:

``` text
mode only
```

or inspect mode dependence.

If mode alone predicts the target strongly, investigate
feedback/confounding.

------------------------------------------------------------------------

# 94. C3 Future-Leakage Tests

Automated tests should verify:

``` text
no observation after T
no late-arriving data unavailable at T
no future mode
no recommended_mode
no target-derived risk_probability/risk_level
```

enters the feature set.

------------------------------------------------------------------------

# 95. C3 Metrics

Report:

``` text
event recall
precision
PR-AUC
ROC-AUC where useful
Brier score
calibration
false alarms per time unit
warning lead time
```

and window-level metrics where appropriate.

------------------------------------------------------------------------

# 96. C3 Event-Level Evaluation

Repeated positive windows before one event should not be treated as many
independent successful landslides.

Compute event-level detection/warning metrics.

------------------------------------------------------------------------

# 97. C3 Lead-Time Evaluation

For each event:

``` text
lead time =
event onset - first qualifying warning
```

Threshold must be chosen on validation data, not test data.

------------------------------------------------------------------------

# 98. C3 Calibration

Use:

``` text
reliability diagram
Brier score
```

and selected calibration method if necessary.

Fit calibration on training/validation data only.

------------------------------------------------------------------------

# 99. C3 Missing-Sensor Stress Test

Remove one or more feature streams.

Examples:

``` text
soil moisture unavailable
rainfall unavailable
tilt unavailable
neighbour unavailable
```

Measure degradation.

------------------------------------------------------------------------

# 100. C3 Gap Stress Test

Inject/evaluate:

``` text
short gaps
long gaps
irregular Δt
late packets
```

Measure robustness of standard vs time-aware models.

------------------------------------------------------------------------

# 101. C3 Mode-Transition Stress Test

Create sequences crossing:

``` text
IDLE → RISK
RISK → WARNING
WARNING → EMERGENCY
```

Verify feature timing/mode representation is correct.

------------------------------------------------------------------------

# 102. C3 C1-Error Stress Test

Introduce realistic C1 misclassification/quality errors.

Measure how C3 degrades.

This tests integrated robustness rather than assuming perfect upstream
AI.

------------------------------------------------------------------------

# 103. C3 C2-Recovery Stress Test

Evaluate:

``` text
DIRECT only
+
BACKUP
+
LATE_ORIGINAL
+
FUSED/DERIVED
```

according to available data.

Measure whether provenance-aware features improve robustness.

------------------------------------------------------------------------

# 104. C3 OOF Upstream Test

When training with learned C1/C2 outputs:

``` text
use out-of-fold/disjoint predictions
```

rather than perfect ground truth or predictions from a model trained on
the same rows.

------------------------------------------------------------------------

# 105. C3 Latency Test

Measure:

``` text
feature retrieval
feature construction
model inference
postprocessing
total C3 service latency
```

across representative sequence sizes.

------------------------------------------------------------------------

# 106. C3 Resource Test

Measure:

``` text
RAM
CPU
model size
inference time
```

on the actual Main Computing System where possible.

------------------------------------------------------------------------

# 107. C3 Acceptance Logic

C3 succeeds scientifically if temporal/irregularity/provenance
mechanisms demonstrate meaningful held-out advantage or robustness over
simpler baselines.

If a simpler model wins, report it and analyze why.

------------------------------------------------------------------------

# 108. C4 Validation Objective

C4 must demonstrate that:

``` text
mandatory deterministic security
+
behavioural analysis
```

provides trustworthy telemetry handling under the defined threat model.

------------------------------------------------------------------------

# 109. C4 Threat Model

Before testing define:

``` text
protected assets
trusted entities
attacker capabilities
in-scope attacks
out-of-scope attacks
```

Do not claim protection against attacks not evaluated/designed for.

------------------------------------------------------------------------

# 110. C4 Deterministic Security Tests

According to implemented protocol test:

``` text
known registered device
unknown device
valid integrity
modified payload
valid freshness
duplicate/replay
counter rollback
expired/stale message
unauthorized command
```

------------------------------------------------------------------------

# 111. C4 Mandatory Failure Test

For every mandatory security failure verify:

``` text
behavioural ML cannot override it to trusted
```

------------------------------------------------------------------------

# 112. C4 Behavioural Baselines

Compare where feasible:

``` text
deterministic only
behavioural ML only
hybrid
```

The hybrid should preserve mandatory security semantics.

------------------------------------------------------------------------

# 113. C4 Supervised Candidate Evaluation

For RF/XGBoost/LightGBM candidates report:

``` text
macro-F1
per-class recall
false acceptance
false rejection
confusion matrix
```

------------------------------------------------------------------------

# 114. C4 Isolation Forest Evaluation

If used:

``` text
train on designated normal/trusted training data
evaluate on held-out normal + attack/anomaly cases
```

Do not train it on test attacks and call that unsupervised
generalization.

------------------------------------------------------------------------

# 115. C4 Replay Test

Capture a previously valid packet and resend it outside authorized
recovery context.

Expected:

``` text
rejected/quarantined according to security policy
```

------------------------------------------------------------------------

# 116. C4 Authorized Recovery Replay Test

Perform C2-authorized SD replay.

Expected:

``` text
accepted only through valid fresh recovery context
historical observation provenance preserved
```

This is a critical C2/C4 integration test.

------------------------------------------------------------------------

# 117. C4 Tamper Test

Modify protected packet content.

Expected:

``` text
integrity failure
```

if the final protocol protects that field.

------------------------------------------------------------------------

# 118. C4 Identity Test

Attempt telemetry under:

``` text
unknown/unregistered identity
```

and any feasible credential-mismatch scenario.

Record exact implemented protection rather than claiming hardware
attestation unless implemented.

------------------------------------------------------------------------

# 119. C4 Behavioural Anomaly Tests

Candidate controlled deviations:

``` text
unusual packet interval
radio-profile shift
retry anomaly
location/hub mismatch
restart anomaly
packet-size anomaly
```

Only use features actually implemented.

------------------------------------------------------------------------

# 120. C4 Attack Episode Splitting

Packets from the same generated attack episode/template must not be
randomly divided across train/test.

Group by attack/scenario.

------------------------------------------------------------------------

# 121. C4 Acceptance Logic

C4 succeeds if the hybrid architecture:

``` text
preserves mandatory deterministic security
and
behavioural analysis provides measurable additional detection value
```

within the stated threat model.

------------------------------------------------------------------------

# 122. Contract Validation

Validate every Document 11 contract using machine-readable schemas where
implemented.

Tests include:

``` text
required fields
types
enum values
version compatibility
unknown fields policy
invalid timestamps
missing IDs
```

------------------------------------------------------------------------

# 123. Cross-Component ID Test

Track one packet through:

``` text
packet_id
observation_id
C4 assessment
C1 assessment
Golden observation
forecast
decision
command
```

No link should be lost.

------------------------------------------------------------------------

# 124. Cross-Component Timestamp Test

Verify:

``` text
observed_at
received_at
available_at
forecast_origin
decision time
command/ACK time
```

retain their intended semantics.

------------------------------------------------------------------------

# 125. Cross-Component Error Test

Force each component to fail individually.

Verify the next layer receives:

``` text
explicit unavailable/degraded status
```

rather than a fabricated scientific class.

------------------------------------------------------------------------

# 126. C4 → C1 Integration

Cases:

``` text
TRUSTED packet → C1 eligible
UNTRUSTED packet → normal environmental path blocked
SUSPICIOUS packet → configured policy applied
```

------------------------------------------------------------------------

# 127. C1 → Golden Timeline Integration

Cases:

``` text
CLEAN
VALID_EVENT
ANOMALY
C1 unavailable
```

Verify selection/preservation policy.

------------------------------------------------------------------------

# 128. C2 → Golden Timeline Integration

Cases:

``` text
LATE_ORIGINAL
BACKUP
FUSED
DERIVED
```

Verify provenance and availability time.

------------------------------------------------------------------------

# 129. Golden Timeline → C3 Integration

Verify:

``` text
only runtime-eligible observations
correct units
correct masks
correct age
correct Δt
correct mode
correct provenance
```

enter C3.

------------------------------------------------------------------------

# 130. C3 → Decision Engine Integration

Test:

``` text
low risk
rising risk
high risk
poor data quality
C3 unavailable
```

Decision policy should react according to explicit rules.

------------------------------------------------------------------------

# 131. Decision Engine → Device Integration

Test:

``` text
mode command
ACK
lost ACK
duplicate command
expired command
out-of-order command
```

------------------------------------------------------------------------

# 132. End-to-End Scenario E1 --- Normal Stable

``` text
trusted telemetry
credible normal measurements
no silence
low forecast risk
IDLE/appropriate low mode
no unnecessary alert
```

------------------------------------------------------------------------

# 133. End-to-End Scenario E2 --- Genuine Environmental Change

``` text
rainfall increases
soil moisture rises
neighbours agree
C1 = VALID_EVENT
C3 risk increases
Decision Engine escalates mode
```

This demonstrates why C1 must not reject genuine extremes.

------------------------------------------------------------------------

# 134. End-to-End Scenario E3 --- Sensor Spike

``` text
one sensor spikes
neighbours/context disagree
C1 identifies anomaly
bad measurement does not dominate C3
```

------------------------------------------------------------------------

# 135. End-to-End Scenario E4 --- Communication Failure

``` text
device stops reporting
mode-aware deadline passes
C2 diagnoses communication issue
recovery/replay attempted
provenance preserved
```

------------------------------------------------------------------------

# 136. End-to-End Scenario E5 --- Primary Failure + Backup

``` text
primary fails
backup remains available
C2 verifies backup
backup data enters Golden Timeline with provenance
C3 continues in degraded/recovered mode
```

------------------------------------------------------------------------

# 137. End-to-End Scenario E6 --- Wider Zone Disruption

``` text
multiple expected streams disappear
backup/network evidence supports serious disruption
C2 escalates possible zone damage
Decision Engine reacts conservatively
```

Do not call this confirmed landslide unless independent ground truth
exists.

------------------------------------------------------------------------

# 138. End-to-End Scenario E7 --- Malicious Replay

``` text
old valid packet resent
C4 detects freshness/replay failure
packet quarantined
does not enter Golden Timeline
```

------------------------------------------------------------------------

# 139. End-to-End Scenario E8 --- Authorized Replay

``` text
C2 requests historical data
fresh authorized recovery context
C4 accepts recovery path
old observed_at retained
new available_at retained
past C3 forecast unaffected
```

------------------------------------------------------------------------

# 140. End-to-End Scenario E9 --- C3 Failure

``` text
C3 unavailable
Decision Engine uses approved degraded/current-state policy
system does not interpret failure as zero risk
```

------------------------------------------------------------------------

# 141. End-to-End Scenario E10 --- Gateway/Main Computer Recovery

Test loss and restoration of central communication/processing.

Verify:

``` text
device buffering
reconnection
deduplication
service recovery
audit trail
```

------------------------------------------------------------------------

# 142. Adaptive Sampling Validation Objective

Demonstrate whether mode-conditioned sensing provides a useful trade-off
between:

``` text
monitoring/resource cost
and
responsiveness/information quality
```

------------------------------------------------------------------------

# 143. Adaptive Sampling Baseline

Compare against a reasonable fixed-rate policy.

Use the same scenario/event conditions where possible.

------------------------------------------------------------------------

# 144. Adaptive Sampling Metrics

Measure:

``` text
number of sensor acquisitions
number of radio packets
radio airtime estimate/measurement
data volume
average/current draw where measurable
event detection latency
forecast performance
warning lead time
missed events
```

------------------------------------------------------------------------

# 145. Power Measurement Boundary

Because Type A/B and hubs use centralized demo power:

``` text
measure relative current/power behaviour
```

but do not claim final field battery lifetime.

Backup Pipe battery/solar can be evaluated separately.

------------------------------------------------------------------------

# 146. Current Measurement Test

For each mode/device where possible record:

``` text
idle/current profile
sensor-active current
radio-transmit current
average current over representative interval
```

using a justified measurement setup.

------------------------------------------------------------------------

# 147. Energy Estimate

If estimating energy:

``` text
E = ∫ V(t)I(t)dt
```

or an appropriate sampled approximation.

Document assumptions and measurement duration.

------------------------------------------------------------------------

# 148. Radio Airtime Evaluation

Estimate/measure transmission cost using actual:

``` text
packet size
radio settings
report frequency
```

Do not infer airtime from packet count alone if settings vary.

------------------------------------------------------------------------

# 149. Fixed vs Adaptive Experiment

Run equivalent controlled scenarios under:

``` text
fixed policy
adaptive policy
```

Compare resource and warning metrics.

This can provide system-level research evidence.

------------------------------------------------------------------------

# 150. End-to-End Latency Measurement

Instrument timestamps for:

``` text
physical/event detection
acquisition
aggregation
report wait
radio
gateway
ingestion
C4
C1
C2 if invoked
C3
decision
alert/command
```

------------------------------------------------------------------------

# 151. Latency Statistics

Report:

``` text
median
mean if useful
high percentile
min/max with caution
```

and mode/scenario-specific results.

------------------------------------------------------------------------

# 152. Warning Latency vs Forecast Lead Time

These are different.

``` text
processing latency
```

measures system delay.

``` text
warning lead time
```

measures how early the warning occurs before an event.

------------------------------------------------------------------------

# 153. Load Test

Generate representative concurrent telemetry.

Measure:

``` text
ingestion throughput
queue delay
DB load
model inference throughput
decision latency
```

Do not need internet-scale load; test the intended prototype/device
count plus reasonable margin.

------------------------------------------------------------------------

# 154. Soak Test

Run the integrated system continuously for a documented period.

Monitor:

``` text
memory growth
service crashes
database growth
packet loss
clock drift
model availability
```

------------------------------------------------------------------------

# 155. Failure Injection Principles

Failures should be:

``` text
controlled
documented
reversible
safe
```

Do not damage hardware merely to create a test.

Prefer switches/software blocks/disconnections where appropriate.

------------------------------------------------------------------------

# 156. Safety During Physical Testing

Do not create dangerous real slope failures for validation.

Use:

``` text
bench rigs
controlled water
controlled tilt
simulated/fault-injected signals
recorded/synthetic sequences
```

and clearly state their limitations.

------------------------------------------------------------------------

# 157. Research Experiment Registry

For each component maintain:

``` text
experiment_id
hypothesis
dataset_version
split
features
model
hyperparameters
metrics
artifact path
result
interpretation
```

------------------------------------------------------------------------

# 158. Baseline Fairness

All compared models should use:

``` text
same eligible training information
same split
same target
same evaluation set
```

unless the experiment explicitly studies information differences.

------------------------------------------------------------------------

# 159. Hyperparameter Fairness

Do not heavily tune the proposed model while leaving baselines at
arbitrary defaults.

Give reasonable tuning effort to important baselines.

------------------------------------------------------------------------

# 160. Test Set Discipline

The final test set must not be repeatedly used for model selection.

Use:

``` text
training
validation/cross-validation
```

for development.

------------------------------------------------------------------------

# 161. Multiple Runs

For stochastic models, repeat training with several documented seeds
where feasible.

Report:

``` text
mean
variation
```

rather than one lucky run.

------------------------------------------------------------------------

# 162. Statistical Comparison

Where sample size/design allows, use appropriate confidence intervals or
statistical tests for key comparisons.

Do not apply significance tests mechanically without checking
assumptions.

------------------------------------------------------------------------

# 163. Confidence Intervals

For event-level metrics with limited events, uncertainty may be large.

Report this honestly.

A high point estimate from very few events is weak evidence.

------------------------------------------------------------------------

# 164. Error Analysis

For every final model inspect:

``` text
false positives
false negatives
class confusions
high-confidence mistakes
```

Research value comes from understanding failure, not only reporting
score.

------------------------------------------------------------------------

# 165. Ablation Reporting

For each ablation show:

``` text
configuration
added/removed mechanism
metric change
interpretation
```

Do not claim a feature is valuable merely because it exists.

------------------------------------------------------------------------

# 166. Calibration Reporting

For any probability used operationally, report calibration.

A model with strong ranking but poor calibration may require post-hoc
calibration.

------------------------------------------------------------------------

# 167. Robustness Reporting

Final component results should include both:

``` text
normal held-out performance
stress-condition performance
```

------------------------------------------------------------------------

# 168. Synthetic vs Physical Reporting

Never merge them into one headline score without clear justification.

Recommended:

``` text
Synthetic controlled evaluation
Physical prototype/fault-injection evaluation
External/field evaluation if available
```

------------------------------------------------------------------------

# 169. Demo Validation vs Research Validation

Demo success:

``` text
system visibly works end-to-end
```

Research success:

``` text
proposed mechanisms outperform/extend meaningful baselines under controlled evaluation
```

Both are required, but they are different.

------------------------------------------------------------------------

# 170. Research Success --- C1

Evidence should show whether:

``` text
rainfall/environment + neighbour + temporal context
```

improves credibility classification and protects genuine extremes.

------------------------------------------------------------------------

# 171. Research Success --- C2

Evidence should show whether:

``` text
mode-aware silence + backup verification + provenance-aware recovery
```

improves diagnosis/recovery over simple approaches.

------------------------------------------------------------------------

# 172. Research Success --- C3

Evidence should show whether:

``` text
history + Δt + mode + upstream quality/provenance
```

improves variable-rate forecasting or robustness.

------------------------------------------------------------------------

# 173. Research Success --- C4

Evidence should show whether:

``` text
deterministic security + behavioural analysis
```

adds useful trust protection within the evaluated threat model.

------------------------------------------------------------------------

# 174. System-Level Success

GeoNex should demonstrate:

``` text
trusted acquisition
credible data handling
failure awareness/recovery
future-risk forecasting
adaptive operation
traceable decisions
safe degraded behaviour
```

in one integrated prototype.

------------------------------------------------------------------------

# 175. Minimum Evidence for Each Figure/Table

Every thesis/paper result should be reproducible from:

``` text
dataset/test_run
script/notebook
configuration
saved output
```

Avoid manually typed result tables when they can be generated.

------------------------------------------------------------------------

# 176. Confusion Matrix Artifact

Save both:

``` text
raw counts
normalized visualization
```

where useful.

The underlying numeric data should be retained.

------------------------------------------------------------------------

# 177. Training Curve Artifact

For neural models save:

``` text
training loss
validation loss
selected metric
epoch
early stopping point
```

------------------------------------------------------------------------

# 178. Feature Importance Artifact

For tree models save:

``` text
global importance
SHAP summary where used
representative local explanations
```

with correct limitations.

------------------------------------------------------------------------

# 179. Calibration Artifact

Save:

``` text
reliability data
Brier score
calibration method/version
```

------------------------------------------------------------------------

# 180. Latency Artifact

Save raw stage timestamps so latency plots can be regenerated.

------------------------------------------------------------------------

# 181. Power Artifact

Save:

``` text
measurement interval
voltage/current samples
mode
device
firmware/policy version
```

------------------------------------------------------------------------

# 182. Test Evidence Naming

Recommended pattern:

``` text
<test_id>_<date>_<short-description>
```

Example:

``` text
C2-014_2026-10-20_backup-verification
```

------------------------------------------------------------------------

# 183. Evidence Integrity

Do not overwrite failed test evidence.

A failed test followed by a successful fix is valuable engineering
history.

Record both.

------------------------------------------------------------------------

# 184. Bug-to-Test Rule

When a significant bug is fixed:

``` text
add regression test
```

where feasible.

This prevents recurrence.

------------------------------------------------------------------------

# 185. Pre-Demo Regression Suite

Before official demonstration run:

``` text
hardware smoke tests
sensor reads
LoRa
database
C1
C2
C3
C4
Decision Engine
commands/ACK
alerts
critical end-to-end scenarios
```

------------------------------------------------------------------------

# 186. Demo Script

Prepare a repeatable demonstration sequence.

Suggested structure:

``` text
1. normal monitoring
2. genuine environmental change
3. C1 credibility decision
4. variable-rate/mode escalation
5. communication failure
6. C2 backup/recovery
7. C4 replay/security example
8. C3 forecast
9. Decision Engine warning
10. audit/dashboard evidence
```

Exact sequence depends on implementation readiness.

------------------------------------------------------------------------

# 187. Demo Reset Procedure

Document how to return the prototype to known initial state:

``` text
mode
database/test run
device sessions
buffers
alerts
models
```

This improves repeatability.

------------------------------------------------------------------------

# 188. Demo Failure Contingency

Prepare fallback evidence if a physical component temporarily fails
during presentation:

``` text
recorded test evidence
logs
saved run
plots
```

Do not misrepresent recorded evidence as live execution.

------------------------------------------------------------------------

# 189. Acceptance Gate --- Hardware Ready

Hardware is ready when:

``` text
required sensors respond
IDs/channels correct
power stable
communication works
calibration status documented
known limitations recorded
```

------------------------------------------------------------------------

# 190. Acceptance Gate --- Data Ready

Data layer is ready when:

``` text
raw immutable storage works
timestamps correct
provenance trace works
Golden Timeline works
dataset export/versioning works
```

------------------------------------------------------------------------

# 191. Acceptance Gate --- Component Ready

A component is ready when:

``` text
contract implemented
unit tests pass
baseline implemented
proposed method evaluated
stress tests run
model artifact versioned
failure behaviour defined
```

------------------------------------------------------------------------

# 192. Acceptance Gate --- Integration Ready

Integration is ready when:

``` text
Document 11 contracts pass
normal flow works
failure flow works
IDs/timestamps trace
as-of leakage test passes
commands/ACK work
```

------------------------------------------------------------------------

# 193. Acceptance Gate --- Research Ready

Research is ready for reporting when:

``` text
datasets frozen/versioned
splits frozen
baselines fair
final experiments complete
test set untouched until final evaluation
results reproducible
limitations documented
```

------------------------------------------------------------------------

# 194. Acceptance Gate --- Demo Ready

Demo is ready when:

``` text
critical end-to-end scenarios pass
regression suite passes
reset procedure works
evidence backup exists
team can explain component boundaries
```

------------------------------------------------------------------------

# 195. Test Priority

Prioritize by consequence:

``` text
P0 — safety/security/data-integrity critical
P1 — core research/runtime function
P2 — degraded/edge case
P3 — convenience/UI/noncritical
```

------------------------------------------------------------------------

# 196. P0 Examples

Examples:

``` text
untrusted packet enters Golden Timeline
future leakage into C3
C3 failure interpreted as low risk
stale command overrides emergency state
raw evidence overwritten
malicious replay accepted as fresh
```

These must be addressed before final validation.

------------------------------------------------------------------------

# 197. Validation Matrix

  -----------------------------------------------------------------------
  Area                    Primary evidence        Key metric/output
  ----------------------- ----------------------- -----------------------
  Sensors                 calibration/bench tests error, repeatability,
                                                  response

  Firmware                unit/HIL                correct acquisition,
                                                  mode, buffering

  LoRa                    network tests           delivery, latency,
                                                  RSSI/SNR

  Database                integration tests       integrity,
                                                  traceability, query
                                                  behavior

  C1                      held-out experiments    macro-F1, class recall,
                                                  dangerous error

  C2                      fault injection         diagnosis, recovery
                                                  success/latency

  C3                      temporal evaluation     PR-AUC, event recall,
                                                  calibration, lead time

  C4                      threat tests            detection, false
                                                  accept/reject

  Adaptive sensing        controlled comparison   packets/power vs
                                                  responsiveness

  Integration             contract/E2E            correct provenance and
                                                  state

  System                  scenario/demo           reliable end-to-end
                                                  behavior
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 198. Evidence That Must Not Be Claimed Without Testing

Do not claim:

``` text
10 km operational LoRa range
field battery lifetime
real-world landslide prediction accuracy
universal rainfall threshold
hardware-rooted attestation
zero false alarms
real-time guarantee
fault tolerance for untested failures
```

unless supported by actual evidence.

------------------------------------------------------------------------

# 199. Negative Results

If:

``` text
Time-Aware GRU does not beat XGBoost
backup verification helps only some faults
behavioural C4 increases false rejection
adaptive sampling saves little power
```

report it.

Negative results can still answer the research question.

------------------------------------------------------------------------

# 200. Limitation Register

Maintain a live list:

``` text
limitation
affected claim
impact
mitigation
future work
```

Examples:

``` text
synthetic event labels
small physical test set
bench rather than field deployment
limited attack diversity
prototype sensor calibration
```

------------------------------------------------------------------------

# 201. Final Validation Package

Before thesis/paper completion, archive:

``` text
test registry
calibration records
dataset manifests
experiment configs
model artifacts
metrics
plots
logs
hardware evidence
integration reports
end-to-end results
limitation register
```

------------------------------------------------------------------------

# 202. What Is Frozen by Document 12

1.  GeoNex validation is multi-layered; one accuracy score is
    insufficient.
2.  Synthetic, bench, prototype and field evidence are reported
    separately.
3.  Every formal test should have a traceable test ID/run/evidence.
4.  Hardware calibration is required before claiming calibrated physical
    quantities.
5.  Type A/B physical validation occurs after construction.
6.  Nominal LoRa range is not treated as experimentally proven range.
7.  Raw-data integrity/provenance are explicitly tested.
8.  C1 must be compared against simpler contextual/value baselines.
9.  C1's dangerous `VALID_EVENT → ANOMALY` error is explicitly
    evaluated.
10. C2 fixed-timeout vs mode-aware detection is a mandatory comparison.
11. C2 backup verification requires an ablation.
12. C2 recovery quality and latency are evaluated separately from
    diagnosis.
13. C3 split occurs before overlapping sequence generation.
14. C3 A0--A5 ablation is central.
15. C3 variable-rate-aware representation is compared against simpler
    representations where feasible.
16. C3 event-level recall, calibration, false alarms and lead time
    matter beyond accuracy.
17. C3 runtime as-of leakage tests are mandatory.
18. C4 mandatory security cannot be overridden by ML.
19. C4 deterministic-only, behavioural-only and hybrid comparisons are
    evaluated where feasible.
20. Authorized recovery replay and malicious replay are tested
    separately.
21. Adaptive sampling is evaluated against a fixed-rate baseline.
22. Demo centralized power does not justify field battery-life claims.
23. End-to-end latency is measured by stages.
24. Upstream model errors are included in downstream robustness testing.
25. Baselines receive fair evaluation.
26. Final test data is protected from iterative tuning.
27. Failed/negative experiments are retained and reported honestly.
28. Component execution failures must be tested explicitly.
29. A pre-demo regression suite is required.
30. Research success requires reproducible evidence and bounded claims.

------------------------------------------------------------------------

# 203. Decisions Still Deferred

This plan intentionally does not freeze:

``` text
exact calibration apparatus
exact number of physical repetitions
exact acceptance percentages
exact LoRa test distances
exact soak-test duration
exact C1/C2/C3/C4 final models
exact statistical significance test
exact C3 forecast horizons/history lengths
exact C4 cryptographic implementation
exact adaptive-sampling rates
exact power-measurement instrument
exact final demo sequence
```

These should be finalized based on hardware availability, literature,
supervisor guidance and implementation evidence.

------------------------------------------------------------------------

# 204. Recommended Immediate Testing Order

``` text
1. Complete hardware inventory and IDs.
2. Validate power distribution.
3. Bring up each sensor.
4. Calibrate/characterize sensors.
5. Validate firmware packet/timestamp/sequence behavior.
6. Validate LoRa delivery.
7. Validate ingestion/database.
8. Implement contract tests.
9. Validate C4 mandatory path.
10. Validate C1.
11. Validate expected-report scheduler/C2.
12. Validate Golden Timeline.
13. Validate C3 feature builder/model.
14. Validate Decision Engine.
15. Validate commands/ACK.
16. Run end-to-end scenarios.
17. Run adaptive-sampling/power/latency tests.
18. Freeze final research datasets/splits.
19. Run final held-out experiments.
20. Prepare reproducible demo/evidence package.
```

------------------------------------------------------------------------

# 205. Next Document

Next:

``` text
13_GEONEX_MLOPS_AND_REPRODUCIBILITY_PLAN.md
```

It should define:

``` text
experiment tracking
dataset/model registry
configuration management
training pipeline
artifact naming
model promotion
rollback
controlled cumulative retraining
data/model drift monitoring
reproducible environments
seeds
code/version linkage
deployment packages
runtime model loading
audit
backup/retention
```

This will formalize the project's "self-learning" mechanism as
controlled, testable and reproducible model lifecycle management rather
than uncontrolled online retraining.

------------------------------------------------------------------------

# Document 12 Status

**`12_GEONEX_TESTING_AND_VALIDATION_PLAN.md` --- VALIDATION BASELINE v1
READY**

The governing principle is:

``` text
CLAIM
  ↓
CONTROLLED TEST
  ↓
REFERENCE / GROUND TRUTH
  ↓
MEASUREMENT
  ↓
BASELINE COMPARISON
  ↓
REPRODUCIBLE EVIDENCE
  ↓
BOUNDED CONCLUSION
```

A working demonstration shows feasibility.

A controlled, reproducible comparison shows research value.
