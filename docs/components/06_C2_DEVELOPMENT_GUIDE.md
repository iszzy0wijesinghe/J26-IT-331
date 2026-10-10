# 06_C2_DEVELOPMENT_GUIDE.md

**Project:** GeoNex --- Smart Landslide Early Warning Prediction System
using IoT, Edge AI and Risk Analytics\
**Component:** C2 --- Silent-Pattern Diagnostic Classification via
Backup Pipe Verification\
**Document:** Component Development Guide\
**Status:** Implementation Baseline\
**Depends on:** Documents 00--05\
**Primary purpose:** Define a complete, research-defensible
implementation path for C2: detecting meaningful telemetry silence,
diagnosing its likely cause, verifying uncertain cases through
independent evidence, and recovering usable information without
destroying provenance.

------------------------------------------------------------------------

# 1. Component Mission

C2 answers a question that ordinary missing-value handling does not:

> **Why did expected information disappear, and what should GeoNex do
> about it?**

A missing reading may result from:

``` text
normal timing under the current operating mode
temporary packet loss
communication failure
sensor/device hardware failure
hub failure
or
a wider physical-zone disturbance
```

C2 must therefore avoid treating every missing value as identical.

Its responsibility is:

``` text
expected-report awareness
        +
silence detection
        +
contextual diagnosis
        +
independent Backup Pipe verification
        +
recovery/escalation
        +
provenance-preserving output
```

------------------------------------------------------------------------

# 2. C2's Place in GeoNex

C2 is **not simply downstream of C1**.

It has an independent trigger because C1 cannot classify an observation
that never arrived.

Correct conceptual architecture:

``` text
                     ┌───────────────┐
Telemetry arrives →  │ C4 → C1       │
                     └───────┬───────┘
                             │
                             ↓
                      Golden Timeline

Expected-report scheduler
          ↓
deadline exceeded
          ↓
         C2
          ↓
diagnosis / verification / recovery
          ↓
recovered or degraded evidence
          ↓
Golden Timeline
```

C2 may use recent C1/C4 results as diagnostic context, but its silence
trigger does not require a new C1 result.

------------------------------------------------------------------------

# 3. C2 Is Not Generic Imputation

A conventional missing-data pipeline may do:

``` text
missing value
    ↓
mean / interpolation / forward fill
```

This is insufficient for a safety-oriented monitoring system because it
hides the reason information disappeared.

C2 instead asks:

``` text
Was the report actually expected?
Did only one sensor disappear?
Did the whole device disappear?
Did multiple devices disappear?
Is the gateway still receiving others?
Can the Backup Pipe independently observe the area?
Can local storage replay the missing observation?
Is the zone itself showing unusual behaviour?
```

Only after diagnosis should recovery be considered.

------------------------------------------------------------------------

# 4. Research Problem

Fixed missing-data handling assumes that missingness is merely a
data-quality problem.

In GeoNex, silence may itself carry diagnostic information.

The research problem is therefore:

> **Can mode-aware expected-report analysis combined with contextual and
> independent Backup Pipe evidence improve the diagnosis and recovery of
> silent telemetry compared with fixed-timeout or generic missing-data
> approaches?**

------------------------------------------------------------------------

# 5. Research Hypothesis

A defensible hypothesis is:

> **A mode-aware diagnostic approach using device/network context and
> independent Backup Pipe verification will classify the cause of
> telemetry silence and select appropriate recovery/escalation actions
> more reliably than fixed-timeout and context-free missing-data
> approaches.**

This must be tested.

------------------------------------------------------------------------

# 6. C2 Research Contribution

The strongest C2 contribution is the combination:

``` text
MODE-AWARE EXPECTATION
        ↓
SILENCE EVENT
        ↓
CONTEXTUAL DIAGNOSIS
        ↓
INDEPENDENT BACKUP VERIFICATION
        ↓
PROVENANCE-AWARE RECOVERY
```

The novelty/value should not be claimed as merely:

``` text
"We use XGBoost."
```

The model is one mechanism inside the diagnostic framework.

------------------------------------------------------------------------

# 7. C2 Must Not Claim

Do not claim that C2:

-   authenticates devices;
-   determines whether a received measurement is credible;
-   predicts future landslide risk;
-   can prove physical zone damage solely from missing packets;
-   can reconstruct missing values perfectly;
-   guarantees Backup Pipe availability;
-   makes recovered/derived data equivalent to direct measurements.

Those claims exceed C2's evidence.

------------------------------------------------------------------------

# 8. Existing C2 Data Assets

Two existing dataset concepts have been identified.

## Dataset A

``` text
landslide_silence_dataset_20000.csv
```

Target:

``` text
Label
```

with classes:

``` text
normal
communication_failure
hardware_failure
possible_zone_damage
```

## Dataset B

``` text
C2_Recovery.csv
```

Targets:

``` text
failure_type
c2_target_action
```

Current action mapping includes:

``` text
sensor_link_gap
    → REQUEST_SD_REPLAY

primary_sensor_failure
    → ACTIVATE_BACKUP_SENSOR

multi_sensor_gap
    → USE_NEIGHBOR_FUSION

hub_failure
    → SWITCH_BACKUP_HUB

zone_network_failure
    → ESCALATE
```

These are existing research artifacts/concepts and must be audited
before being treated as final production datasets.

------------------------------------------------------------------------

# 9. First C2 Task --- Audit Existing Datasets

Before model training:

``` text
inspect columns
inspect units
inspect target generation
inspect class balance
identify scenario IDs
identify hidden generator variables
identify duplicated rows
identify impossible runtime features
identify action leakage
identify temporal leakage
identify whether failure_type directly determines action
```

Generate an audit report.

------------------------------------------------------------------------

# 10. C2 Should Be Episode-Based

C1 usually evaluates an observation.

C2 should primarily evaluate a **silence/failure episode**.

Example:

``` text
device expected at 10:00:30
deadline passes
        ↓
silence event created
        ↓
diagnostic evidence collected
        ↓
classification/recovery
        ↓
episode resolved or escalated
```

One episode can contain multiple diagnostic steps.

------------------------------------------------------------------------

# 11. Silence Episode Identifier

Every diagnostic event should have:

``` text
silence_event_id
```

or equivalent.

All:

``` text
diagnostic observations
backup requests
retries
recovery actions
outcomes
```

should link to that episode.

------------------------------------------------------------------------

# 12. Mode-Aware Expected Reporting

C2 must use the active reporting policy.

Conceptually:

``` text
expected_next_report
=
last_expected/accepted report time
+
active reporting interval
```

Then:

``` text
silence deadline
=
expected_next_report
+
configured grace
```

Exact intervals/grace values remain configurable and experimentally
determined.

------------------------------------------------------------------------

# 13. Why Fixed Timeout Is Wrong

Suppose a device reports slowly in IDLE and rapidly in WARNING.

A universal rule:

``` text
no packet for 60 s = failure
```

can produce:

``` text
false failure in IDLE
```

or:

``` text
dangerously slow failure detection in WARNING
```

Therefore expected-report timing must depend on:

``` text
mode
device type
sampling-policy version
temporary override
```

------------------------------------------------------------------------

# 14. Expected-Report State

The runtime should maintain enough state to determine:

``` text
device_id
active_mode
active_policy_version
last_observation/packet time
expected_next_report
grace/deadline
communication state
```

This state belongs to shared operational logic; C2 consumes it rather
than inventing its own mode definitions.

------------------------------------------------------------------------

# 15. Observation Time vs Arrival Time

C2 must distinguish:

``` text
observed_at
received_at
```

A reading observed on time but delivered late is not the same as a
sensor that never acquired data.

This distinction supports diagnosis.

------------------------------------------------------------------------

# 16. Silence State Machine

Recommended conceptual states:

``` text
ON_TIME
   ↓
LATE
   ↓
SUSPECTED_SILENCE
   ↓
DIAGNOSING
   ↓
RECOVERING
   ↓
RESOLVED
```

or:

``` text
ESCALATED
```

The exact enum can be simplified in the integration contract.

------------------------------------------------------------------------

# 17. Do Not Immediately Classify Failure

When the first deadline is exceeded:

``` text
missing packet
```

does not automatically imply:

``` text
hardware_failure
```

C2 should collect evidence.

------------------------------------------------------------------------

# 18. Diagnostic Evidence Families

Organize features into:

``` text
D0 — timing/expected-report evidence
D1 — target-device communication evidence
D2 — target-device health history
D3 — neighbouring-device/network evidence
D4 — C1 credibility history
D5 — C4 trust/security history
D6 — Backup Pipe verification
D7 — hub/gateway evidence
D8 — environmental context
```

This enables research ablation.

------------------------------------------------------------------------

# 19. D0 --- Timing Evidence

Candidate features:

``` text
seconds_since_last_report
expected_report_interval_s
lateness_s
missed_expected_reports
current_mode
time_in_mode
policy_version
recent_interval_mean
recent_interval_std
```

Use actual policy-aware timing.

------------------------------------------------------------------------

# 20. D1 --- Communication Evidence

Candidate features where available:

``` text
recent_packet_loss
recent_retry_count
recent_RSSI
recent_SNR
RSSI_change
SNR_change
last_successful_receive
recent_delivery_delay
```

Radio metrics are diagnostic context, not environmental variables.

------------------------------------------------------------------------

# 21. D2 --- Device Health Evidence

Candidate features:

``` text
last_voltage
voltage_trend
recent_sensor_read_errors
recent_device_restart
boot/session change
last_health_report_age
recent watchdog reset
```

Only include fields actually available in runtime.

------------------------------------------------------------------------

# 22. D3 --- Neighbour Evidence

Candidate:

``` text
number_of_neighbours_reporting
fraction_neighbours_reporting
same_zone_devices_missing
cross_zone_devices_missing
neighbour_packet_loss
neighbour_environmental_activity
```

Patterns across multiple devices can help distinguish local device
failure from wider communication/zone problems.

------------------------------------------------------------------------

# 23. D4 --- C1 History

C1 may provide recent evidence such as:

``` text
recent_anomaly_fraction
last_credibility_class
recent sensor-drift suspicion
```

Example:

``` text
repeated anomalous readings
then complete silence
```

may support a hardware-failure hypothesis.

But C1 history is supporting evidence, not proof.

------------------------------------------------------------------------

# 24. D5 --- C4 History

Potential evidence:

``` text
recent trust state
recent replay/security events
authentication failures
unexpected transmission behaviour
```

C2 must not reinterpret a mandatory security rejection as an ordinary
network failure without preserving the C4 reason.

------------------------------------------------------------------------

# 25. D6 --- Backup Pipe Evidence

The Backup Pipe is central to C2.

Possible evidence:

``` text
backup_reachable
backup_response_latency
backup_environmental_measurements
backup_health
backup_radio_state
agreement_with_neighbours
```

The Backup Pipe should have independent power/communication/sensing
dependencies where feasible.

------------------------------------------------------------------------

# 26. D7 --- Hub/Gateway Evidence

Candidate:

``` text
hub_online
hub_health
hub_storage_available
gateway_receiving_other_devices
gateway_radio_state
gateway_queue/backlog
```

This can separate:

``` text
one device failed
```

from:

``` text
shared communication path failed
```

------------------------------------------------------------------------

# 27. D8 --- Environmental Context

Environmental evidence may help distinguish:

``` text
isolated technical failure
```

from:

``` text
possible wider physical disturbance
```

Examples:

``` text
rainfall intensity
other sensors showing abrupt movement
multiple spatially related devices disappearing
```

However C2 must not conclude geological damage solely because conditions
are hazardous.

Use the class:

``` text
possible_zone_damage
```

carefully.

------------------------------------------------------------------------

# 28. "Possible Zone Damage" Semantics

This class should mean:

> Available telemetry/diagnostic evidence is inconsistent with an
> isolated ordinary device or communication fault and warrants
> physical-zone concern/escalation.

It does **not** mean:

``` text
confirmed landslide
```

or:

``` text
confirmed physical pipe destruction
```

The final label specification must preserve this uncertainty.

------------------------------------------------------------------------

# 29. C2 Labeling Specification

Create:

``` text
C2_LABELING_SPECIFICATION.md
```

Define:

``` text
normal
communication_failure
hardware_failure
possible_zone_damage
```

with:

-   observable evidence;
-   hidden experiment truth;
-   ambiguity policy;
-   multi-fault policy;
-   synthetic generation rules;
-   physical fault-injection rules.

------------------------------------------------------------------------

# 30. Failure Taxonomy Should Be Hierarchical

A useful conceptual taxonomy:

``` text
NO FAILURE
|
└── FAILURE / SILENCE
    ├── COMMUNICATION
    │   ├── temporary link loss
    │   ├── device link gap
    │   └── wider network/hub path
    │
    ├── HARDWARE
    │   ├── sensor failure
    │   ├── controller failure
    │   └── power failure
    │
    └── POSSIBLE PHYSICAL-ZONE DISTURBANCE
```

The production labels may remain coarser if data cannot reliably support
fine-grained classes.

Do not create more classes than the evidence can distinguish.

------------------------------------------------------------------------

# 31. Two-Stage C2 Architecture

Recommended:

``` text
STAGE A
Silence diagnosis
        ↓
failure class + confidence/evidence

STAGE B
Recovery/action selection
        ↓
deterministic availability/safety rules
+
optional learned recommendation
```

This separation makes the system easier to evaluate and explain.

------------------------------------------------------------------------

# 32. Why Diagnosis and Action Should Be Separated

If:

``` text
failure_type = primary_sensor_failure
```

and:

``` text
backup is unavailable
```

then the normal action:

``` text
ACTIVATE_BACKUP_SENSOR
```

cannot be executed.

Therefore action depends on:

``` text
diagnosis
+
available resources
+
safety policy
```

not diagnosis alone.

------------------------------------------------------------------------

# 33. Action Leakage Warning

If the dataset defines:

``` text
failure_type
```

and then deterministically maps it to:

``` text
c2_target_action
```

training another ML model to predict action from failure_type may add no
scientific value.

First implement the rule baseline.

Only claim learned action selection if additional context makes action
choice genuinely uncertain and experiments show benefit.

------------------------------------------------------------------------

# 34. Candidate Recovery Actions

Current baseline concepts:

``` text
REQUEST_SD_REPLAY
ACTIVATE_BACKUP_SENSOR
USE_NEIGHBOR_FUSION
SWITCH_BACKUP_HUB
ESCALATE
```

Additional runtime states may include:

``` text
RETRY_STATUS_REQUEST
WAIT_WITHIN_GRACE
NO_ACTION
MARK_UNAVAILABLE
```

Exact shared enum is frozen later.

------------------------------------------------------------------------

# 35. REQUEST_SD_REPLAY

Use when:

``` text
the device/hub appears to have acquired/stored data
but transmission/delivery failed
```

Recovery should request historical locally stored observations.

Recovered records preserve original timestamps.

------------------------------------------------------------------------

# 36. ACTIVATE_BACKUP_SENSOR

Use when:

``` text
primary sensing path is unavailable
+
Backup Pipe is available
```

The Backup Pipe provides independent evidence.

Do not silently relabel backup observations as primary observations.

------------------------------------------------------------------------

# 37. USE_NEIGHBOR_FUSION

Use when direct and backup data are unavailable or insufficient but
neighbouring evidence can support a derived estimate.

This output must be explicitly marked:

``` text
DERIVED
```

with:

``` text
source observations
method
confidence
algorithm version
```

------------------------------------------------------------------------

# 38. SWITCH_BACKUP_HUB

This action is only valid if a backup-hub mechanism is actually
implemented in the final hardware/software architecture.

If no physically implemented backup hub exists, this action must remain:

``` text
simulation/research scenario
```

or be removed from production runtime.

Do not document unimplemented redundancy as deployed capability.

------------------------------------------------------------------------

# 39. ESCALATE

Escalation means:

``` text
C2 cannot safely recover/resolve the situation
or
the pattern warrants higher operational attention
```

Escalation can inform the Decision Engine/operator.

It is not automatically a landslide alarm.

------------------------------------------------------------------------

# 40. Backup Pipe Verification Workflow

Conceptually:

``` text
primary silence detected
        ↓
verify current mode/deadline
        ↓
check communication/device context
        ↓
send verification request to Backup Pipe
        ↓
Backup Pipe acknowledges
        ↓
temporarily increase/perform required sensing
        ↓
return measurements + health
        ↓
compare:
  primary history
  backup
  neighbours
  hub/environment
        ↓
diagnosis
        ↓
recovery/escalation
```

------------------------------------------------------------------------

# 41. Backup Pipe Independence

For useful verification, Backup Pipe should preserve as much
independence as feasible:

``` text
separate ESP32
separate sensing elements
separate battery/solar supply
separate device identity
independent LoRa path
```

This is one reason the backup architecture is research-relevant.

------------------------------------------------------------------------

# 42. Backup Pipe Does Not Need to Mirror Primary Continuously

A resource-aware backup strategy can use:

``` text
low-power background state
        ↓
C2 verification request
        ↓
temporary higher activity
        ↓
verification result
        ↓
return to backup policy
```

Exact timings require hardware experiments.

------------------------------------------------------------------------

# 43. Backup Verification Outcomes

Conceptual outcomes:

``` text
BACKUP_CONFIRMS_NORMAL_ENVIRONMENT
BACKUP_CONFIRMS_ENVIRONMENTAL_CHANGE
BACKUP_UNREACHABLE
BACKUP_SENSOR_ERROR
BACKUP_INCONCLUSIVE
```

Exact enums remain to be frozen.

------------------------------------------------------------------------

# 44. SD Replay Workflow

``` text
gap identified
        ↓
device/hub reconnects
        ↓
request missing sequence/time range
        ↓
read local buffer/microSD
        ↓
send replay with authorization metadata
        ↓
C4 recognizes legitimate recovery path
        ↓
store original observed_at
        ↓
mark received_at = replay delivery time
        ↓
mark provenance = SD_REPLAY
```

------------------------------------------------------------------------

# 45. Authorized Replay vs Attack Replay

C4 must be able to distinguish:

``` text
authorized C2 recovery replay
```

from:

``` text
unauthorized malicious replay
```

C2 cannot bypass C4 security merely because it requested historical
data.

The final protocol needs:

``` text
recovery request ID
authorized sequence/time range
device identity
integrity/authentication
```

or equivalent.

------------------------------------------------------------------------

# 46. Neighbour Fusion Is Not Direct Observation

If C2 derives:

``` text
estimated soil moisture = 72%
```

from neighbours, the Golden Timeline must know:

``` text
value = 72
provenance = NEIGHBOR_FUSION
confidence = ...
```

Never represent it as:

``` text
A1 measured 72%
```

if A1 did not.

------------------------------------------------------------------------

# 47. Candidate Neighbour-Fusion Methods

Start simple:

``` text
median of eligible neighbours
weighted average
distance/reliability-weighted average
```

Only investigate more complex models if data supports them.

The recovery method must be evaluated independently.

------------------------------------------------------------------------

# 48. Recovery Confidence

Recovery confidence should depend on evidence such as:

``` text
number of sources
source credibility
source trust
spatial relevance
staleness
agreement
method uncertainty
```

The exact formulation must be experimentally justified.

------------------------------------------------------------------------

# 49. Recovery Does Not Erase Missingness

C3 may need to know:

``` text
a value was missing and recovered
```

because uncertainty differs from a direct measurement.

Therefore retain:

``` text
was_missing
recovery_method
repair_confidence
source_count
```

or equivalent features.

------------------------------------------------------------------------

# 50. C2 Dataset Unit

Recommended training unit for diagnosis:

``` text
one silence episode at a defined diagnostic decision point
```

not every arbitrary timestamp.

This avoids duplicating hundreds of nearly identical rows from one
failure episode.

------------------------------------------------------------------------

# 51. Diagnostic Decision Points

Possible dataset records:

``` text
T0 = initial confirmed silence
T1 = after status/retry evidence
T2 = after Backup Pipe response
```

If multiple decision points from one episode are used, all must remain
in the same train/validation/test group.

------------------------------------------------------------------------

# 52. Dataset Schema --- Diagnosis

Conceptual record:

``` text
silence_event_id
scenario_id
zone_id
device_id
device_type
event_started_at
decision_at

current_mode
active_policy_version
expected_interval_s
lateness_s
missed_reports

recent_packet_loss
recent_retry_count
recent_rssi
recent_snr

last_voltage
recent_read_errors
recent_restart

same_zone_reporting_fraction
cross_zone_reporting_fraction
hub_online
gateway_receiving_others

recent_c1_anomaly_fraction
recent_c4_trust_state

backup_requested
backup_reachable
backup_response_latency_s
backup_environmental_summary

rainfall_context
environmental_change_context

diagnosis_label
source_origin
```

Only runtime-observable features are eligible for model input.

------------------------------------------------------------------------

# 53. Dataset Schema --- Recovery

Conceptual:

``` text
silence_event_id
diagnosis
backup_available
sd_replay_available
neighbour_count
neighbour_quality
hub_redundancy_available
security_state
operational_mode
candidate_action
action_executed
recovery_success
recovery_latency_s
recovered_value_available
recovery_confidence
```

Separate:

``` text
decision-time features
```

from:

``` text
post-action outcome fields
```

------------------------------------------------------------------------

# 54. Outcome Leakage

Fields such as:

``` text
recovery_success
recovery_latency
final_resolved_state
```

occur after action selection.

They cannot be input features for predicting the action at the earlier
decision time.

They are evaluation outcomes.

------------------------------------------------------------------------

# 55. Hidden Fault Truth

During synthetic/fault-injection experiments, you may know:

``` text
power cable intentionally disconnected
```

This hidden truth defines the target.

It must not become an input feature such as:

``` text
fault_injected = hardware_failure
```

------------------------------------------------------------------------

# 56. Scenario Groups

Each generated/injected failure must have:

``` text
scenario_id
```

All records from that scenario stay in one split.

This is mandatory for honest evaluation.

------------------------------------------------------------------------

# 57. Failure Injection Framework

Controlled C2 experiments can simulate/inject:

``` text
drop selected packets
disable LoRa
power off primary device
disconnect sensor
restart ESP32
simulate low power
disable hub
delay packets
block selected device
disable Backup Pipe
create multi-device outage
```

Only safe, reversible physical tests should be performed.

------------------------------------------------------------------------

# 58. Communication Failure Scenarios

Examples:

``` text
single packet loss
burst packet loss
high delay
radio disconnection
gateway-side receive interruption
```

Ground truth is known from the test setup.

------------------------------------------------------------------------

# 59. Hardware Failure Scenarios

Examples:

``` text
primary sensor disconnected
controller powered off
sensor read repeatedly fails
power instability
```

Use only scenarios that can be safely and reproducibly produced.

------------------------------------------------------------------------

# 60. Possible Zone-Damage Scenarios

Actual destructive landslide tests are not required.

Research scenarios may represent wider physical-zone disturbance through
controlled/synthetic patterns such as:

``` text
multiple spatially related primary devices become unavailable
+
backup/environmental evidence indicates abnormal zone activity
```

Claims must remain:

``` text
possible zone damage / escalation
```

not confirmed geological failure.

------------------------------------------------------------------------

# 61. Normal Class

`normal` should include difficult non-failure conditions:

``` text
expected long IDLE interval
ordinary jitter
temporary delay within grace
mode transition
scheduled lower reporting
authorized replay
```

Otherwise the classifier may learn an unrealistically easy normal class.

------------------------------------------------------------------------

# 62. Baseline 0 --- Fixed Timeout

Implement:

``` text
if silence > fixed threshold:
    failure
```

This intentionally simple baseline demonstrates why mode awareness is
needed.

------------------------------------------------------------------------

# 63. Baseline 1 --- Mode-Aware Rules

Implement:

``` text
active mode/policy
        ↓
expected interval + grace
        ↓
silence state
```

plus basic deterministic diagnostic rules.

This is a critical baseline.

------------------------------------------------------------------------

# 64. Baseline 2 --- Random Forest

Random Forest is a suitable diagnostic baseline for structured episode
data.

It provides:

``` text
nonlinear interactions
little preprocessing
feature importance
strong classical comparison
```

------------------------------------------------------------------------

# 65. Candidate --- XGBoost

XGBoost is a strong candidate for failure diagnosis because C2 inputs
are likely structured/tabular and include interacting context.

It must be compared against simpler baselines.

------------------------------------------------------------------------

# 66. Candidate --- LightGBM

LightGBM may also be evaluated if useful.

Do not create unnecessary algorithm proliferation.

A smaller, well-designed comparison is better than dozens of unmotivated
models.

------------------------------------------------------------------------

# 67. Optional Anomaly Detector

An unsupervised/semi-supervised detector may be useful for:

``` text
previously unseen failure patterns
```

but should not replace supervised diagnosis if labeled scenarios exist.

Possible research extension:

``` text
known-failure classifier
+
unknown-pattern detector
```

This is optional, not required for the initial C2 contribution.

------------------------------------------------------------------------

# 68. Why Deep Learning Is Not Automatically Needed

C2 episode-level features are likely tabular and dataset size is
limited.

Tree ensembles may provide:

``` text
strong performance
interpretability
fast inference
simpler deployment
```

A deep network should only be introduced if sequential raw evidence and
sufficient data justify it.

------------------------------------------------------------------------

# 69. Core Diagnosis Ablation

Use the same frozen split:

``` text
A0 — fixed timeout
A1 — mode-aware timing
A2 — + device/network context
A3 — + neighbour/hub context
A4 — + C1/C4 history
A5 — + Backup Pipe verification
```

This directly tests C2's research value.

------------------------------------------------------------------------

# 70. Most Important C2 Ablation

The strongest comparison is:

``` text
without Backup Pipe verification
vs
with Backup Pipe verification
```

If C2 claims independent verification as a contribution, its value must
be measured.

------------------------------------------------------------------------

# 71. Mode-Aware Ablation

Compare:

``` text
fixed timeout
vs
mode-aware expected reporting
```

Measure:

``` text
false silence detections
detection delay
diagnostic performance
```

This links C2 directly to GeoNex variable-rate operation.

------------------------------------------------------------------------

# 72. Recovery Baseline

Start with deterministic mapping:

``` text
diagnosis + availability
        ↓
action
```

This is likely a strong baseline.

------------------------------------------------------------------------

# 73. Learned Recovery Policy

Only investigate a learned action recommender if:

``` text
same diagnosis
+
different context
```

can legitimately require different actions and enough labeled outcome
data exists.

Otherwise deterministic recovery is safer and scientifically cleaner.

------------------------------------------------------------------------

# 74. Hybrid C2 Recommendation

Recommended architecture:

``` text
ML:
likely failure diagnosis

Deterministic policy:
resource availability
security constraints
safety restrictions
action execution
fallback/escalation
```

This prevents an ML model from issuing impossible or unsafe recovery
actions.

------------------------------------------------------------------------

# 75. Diagnosis Metrics

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

Accuracy alone is insufficient.

------------------------------------------------------------------------

# 76. Critical C2 Errors

Pay particular attention to:

``` text
possible_zone_damage → communication_failure
```

because this may under-escalate a serious condition.

Also:

``` text
communication_failure → possible_zone_damage
```

because excessive false escalation reduces trust/usability.

------------------------------------------------------------------------

# 77. Silence Detection Metrics

Measure separately:

``` text
false silence rate
missed silence rate
silence detection latency
```

The diagnosis classifier should not hide poor silence detection.

------------------------------------------------------------------------

# 78. Recovery Metrics

Measure:

``` text
action correctness
recovery success rate
recovery latency
fraction recovered from direct replay
fraction recovered from backup
fraction derived from neighbour fusion
unresolved/escalated fraction
```

------------------------------------------------------------------------

# 79. Data-Recovery Quality

If C2 reconstructs/recovers numerical observations, evaluate:

``` text
MAE
RMSE where appropriate
absolute/relative error
coverage
confidence calibration
```

against known hidden values in controlled experiments.

Do not mix diagnostic accuracy with numerical recovery quality.

------------------------------------------------------------------------

# 80. Backup Response Metrics

Measure:

``` text
activation/request latency
response success
response latency
energy impact where measurable
verification usefulness
```

This provides evidence that Backup Pipe verification is operationally
practical.

------------------------------------------------------------------------

# 81. Probability Calibration

If diagnostic probabilities drive recovery/escalation, evaluate
calibration.

An uncalibrated:

``` text
0.95 hardware failure
```

should not automatically be interpreted as a true 95% probability.

------------------------------------------------------------------------

# 82. Explainability

For tree models, inspect:

``` text
feature importance
permutation importance
SHAP
```

Questions:

``` text
Is the model relying on mode-aware lateness?
Does Backup Pipe evidence change decisions?
Does it over-rely on device identity?
```

------------------------------------------------------------------------

# 83. Device Identity Shortcut

Do not allow:

``` text
device_id = A1
```

to become a shortcut for a failure class because synthetic scenarios
were generated unevenly.

Device IDs should normally be metadata/grouping variables rather than
model features.

------------------------------------------------------------------------

# 84. Stress Test --- Backup Unavailable

Scenario:

``` text
primary silent
+
Backup Pipe unavailable
```

C2 must not invent verification.

Expected behaviour:

``` text
diagnosis with reduced evidence
+
lower confidence where appropriate
+
alternative recovery/escalation
```

------------------------------------------------------------------------

# 85. Stress Test --- C1 Unavailable

C2 should continue using:

``` text
timing
communication
health
neighbour
backup
```

without assuming C1 is always available.

------------------------------------------------------------------------

# 86. Stress Test --- C4 Degradation

If C4 marks a device untrusted, C2 must preserve that security state.

Do not use untrusted recovery data as ordinary trusted evidence.

------------------------------------------------------------------------

# 87. Stress Test --- Multiple Failures

Test:

``` text
primary failure + backup failure
device failure + network degradation
hub failure + delayed packets
```

Document where diagnosis becomes ambiguous.

------------------------------------------------------------------------

# 88. Stress Test --- Delayed Packet Arrives During Diagnosis

If the supposedly missing packet arrives:

``` text
record late arrival
update episode
```

Do not delete the fact that C2 had already entered diagnosis.

This is valuable latency evidence.

------------------------------------------------------------------------

# 89. Stress Test --- Mode Change During Silence

Example:

``` text
device last reported in IDLE
zone changes to RISK
```

C2 must know when the new reporting policy became effective and whether
the device acknowledged it.

Do not retrospectively expect RISK timing before the device could apply
the command.

------------------------------------------------------------------------

# 90. Applied Policy vs Requested Policy

Important distinction:

``` text
Decision Engine requested WARNING
```

does not prove:

``` text
device is reporting under WARNING profile
```

C2 should use:

``` text
last acknowledged/applied policy
```

when available.

If uncertain, represent policy state as uncertain.

------------------------------------------------------------------------

# 91. C2 Runtime Workflow

``` text
ExpectedReportMonitor
        ↓
deadline event
        ↓
create SilenceEpisode
        ↓
collect diagnostic snapshot
        ↓
optional retry/status request
        ↓
optional Backup Pipe verification
        ↓
C2 diagnostic model
        ↓
failure class + confidence
        ↓
RecoveryPolicyEngine
        ↓
execute allowed action
        ↓
measure outcome
        ↓
store provenance
        ↓
Golden Timeline / Decision Engine
```

------------------------------------------------------------------------

# 92. ExpectedReportMonitor

This service should be deterministic.

It should not require ML to determine whether a report is overdue.

Inputs:

``` text
device
active acknowledged policy
last expected/accepted report
grace configuration
current time
```

Output:

``` text
on_time / late / silence event
```

------------------------------------------------------------------------

# 93. C2DiagnosticService

Conceptual API:

``` text
diagnose(silence_event_id)
    → DiagnosticAssessment
```

It constructs the decision-time feature snapshot and invokes the
approved model/rules.

------------------------------------------------------------------------

# 94. RecoveryPolicyEngine

Conceptual:

``` text
select_action(
    diagnosis,
    resource_availability,
    security_state,
    operational_state
)
    → RecoveryDecision
```

Safety/availability restrictions are deterministic.

------------------------------------------------------------------------

# 95. RecoveryExecutor

Responsible for executing:

``` text
SD replay request
Backup Pipe request
neighbour fusion job
backup route/hub command if implemented
escalation
```

It records success/failure.

------------------------------------------------------------------------

# 96. C2 Output Contract

Conceptually:

``` json
{
  "silence_event_id": "...",
  "device_id": "Z01-A01",
  "diagnosis": "hardware_failure",
  "diagnosis_confidence": 0.89,
  "recommended_action": "ACTIVATE_BACKUP_SENSOR",
  "model_version": "...",
  "generated_at": "...",
  "status": "SUCCESS"
}
```

Execution outcome is stored separately.

------------------------------------------------------------------------

# 97. Recovery Record

Conceptually:

``` json
{
  "recovery_event_id": "...",
  "silence_event_id": "...",
  "action": "ACTIVATE_BACKUP_SENSOR",
  "started_at": "...",
  "completed_at": "...",
  "status": "SUCCESS",
  "source_device_id": "Z01-BK01",
  "provenance": "BACKUP",
  "confidence": 0.86
}
```

Exact schema belongs to the integration/data contract.

------------------------------------------------------------------------

# 98. Golden Timeline Interaction

C2 may produce:

``` text
recovered direct historical observation
backup observation
derived neighbour-fusion observation
or
explicit missing/degraded state
```

The Golden Timeline must preserve which one occurred.

------------------------------------------------------------------------

# 99. C3 Interaction

C3 may receive:

``` text
recovered value
repair confidence
recovery method
missingness mask
time since direct observation
```

This supports the planned C3 `+C2` ablation.

------------------------------------------------------------------------

# 100. Leakage-Safe C2 Outputs for C3

During C3 training, C2-derived features must be generated as they would
have been at runtime.

Do not use:

``` text
final post-event diagnosis
```

at an earlier C3 timestep if that diagnosis was only available later.

Use as-of-time C2 state.

------------------------------------------------------------------------

# 101. C1 Interaction

C2 may consume recent C1 history.

C1 may also evaluate newly received Backup Pipe environmental
observations according to shared policy before they enter trusted
downstream environmental use.

Do not assume backup measurements are automatically credible merely
because they came from backup hardware.

------------------------------------------------------------------------

# 102. C4 Interaction

Every Backup Pipe/replay path remains subject to C4 security controls.

C2 does not override:

``` text
authentication failure
integrity failure
unauthorized replay
```

------------------------------------------------------------------------

# 103. Decision Engine Interaction

C2 can provide:

``` text
system degradation
unresolved silence
possible zone damage
recovery success/failure
```

to the Decision Engine.

The Decision Engine decides whether operational mode/alerts should
change.

C2 does not independently redefine system mode.

------------------------------------------------------------------------

# 104. Database Interaction

C2 conceptually reads:

``` text
device reporting policy/state
raw/normalized telemetry metadata
recent C1/C4 results
device health
network/gateway evidence
backup status
```

and writes:

``` text
silence episodes
diagnostic assessments
recovery requests/actions
recovery outcomes
provenance/confidence
```

Raw telemetry remains immutable.

------------------------------------------------------------------------

# 105. Suggested Code Structure

``` text
components/
└── c2_diagnostics/
    ├── README.md
    ├── configs/
    ├── datasets/
    ├── features/
    ├── monitoring/
    ├── models/
    ├── diagnosis/
    ├── recovery/
    ├── training/
    ├── evaluation/
    ├── service/
    └── tests/
```

------------------------------------------------------------------------

# 106. Shared Code Rule

C2 must not create private copies of:

``` text
mode enum
device IDs
sampling policy schema
telemetry schema
C1/C4 output schema
```

Use shared GeoNex contracts.

------------------------------------------------------------------------

# 107. Configuration

Version/configure:

``` text
grace policy
diagnostic feature windows
backup request timeout
recovery retry policy
model artifact
confidence thresholds
neighbour fusion configuration
```

Do not scatter these values through source code.

------------------------------------------------------------------------

# 108. Training Pipeline

``` text
load frozen episode dataset
        ↓
validate schema
        ↓
load grouped split
        ↓
select decision-time features
        ↓
fit preprocessing on TRAIN
        ↓
train baseline/candidate
        ↓
validation selection
        ↓
optional calibration
        ↓
freeze candidate
        ↓
TEST once
        ↓
save artifact + metadata
```

------------------------------------------------------------------------

# 109. Model Metadata

Record:

``` text
model_name
model_version
algorithm
dataset_version
feature_schema
label_schema
split_version
hyperparameters
seed
metrics
git revision where practical
```

------------------------------------------------------------------------

# 110. Experiment Matrix

Recommended core experiments:

``` text
E0 fixed timeout
E1 mode-aware rules
E2 RF diagnostic
E3 boosted-tree diagnostic
E4 + neighbour/hub context
E5 + C1/C4 context
E6 + Backup Pipe verification
```

Use the same evaluation split wherever comparison requires it.

------------------------------------------------------------------------

# 111. Recovery Experiment Matrix

``` text
R0 deterministic action mapping
R1 availability-aware deterministic policy
R2 optional learned recommendation
```

Only run R2 if the dataset genuinely supports a nontrivial
action-learning problem.

------------------------------------------------------------------------

# 112. Unit Tests

Required examples:

``` text
expected deadline calculated from correct policy
grace applied correctly
mode transition timing handled
late packet recognized
episode created once
duplicate deadline event idempotent
future evidence excluded
backup timeout handled
```

------------------------------------------------------------------------

# 113. Recovery Tests

``` text
authorized SD replay preserves observed_at
backup source preserved
neighbour fusion marked derived
failed backup does not create fake observation
untrusted backup blocked
action outcome recorded
```

------------------------------------------------------------------------

# 114. Dataset Tests

``` text
scenario groups do not cross splits
post-outcome fields excluded from features
hidden fault truth excluded
no future packets used
class mapping valid
source origin recorded
```

------------------------------------------------------------------------

# 115. Model Tests

``` text
model loads
feature schema matches
class valid
probabilities finite
missing optional evidence handled
unsupported schema rejected
```

------------------------------------------------------------------------

# 116. Integration Tests

Minimum scenarios:

### Scenario A

``` text
normal IDLE timing
→ no false C2 failure
```

### Scenario B

``` text
primary packet loss
→ silence
→ communication diagnosis
→ SD replay
```

### Scenario C

``` text
primary hardware off
→ silence
→ Backup Pipe verification
→ backup recovery
```

### Scenario D

``` text
multiple zone devices unavailable
→ diagnostic uncertainty/possible zone concern
→ escalation
```

------------------------------------------------------------------------

# 117. Hardware-in-the-Loop Tests

Use actual devices to measure:

``` text
report timing
silence detection
radio disconnect
primary power-off
Backup Pipe request/response
local buffer replay
command/ACK
recovery latency
```

Record test IDs and ground truth.

------------------------------------------------------------------------

# 118. Research Tables Required

At minimum:

### Diagnosis model comparison

``` text
mode-aware rules
Random Forest
XGBoost/LightGBM candidate
selected model
```

### Context ablation

``` text
timing only
+ device/network
+ neighbour/hub
+ C1/C4
+ Backup Pipe
```

### Recovery results

``` text
action
attempts
success
latency
provenance type
```

------------------------------------------------------------------------

# 119. Research Figures Required

Useful figures:

``` text
confusion matrix
silence timeline
mode-aware vs fixed-timeout false alarms
Backup Pipe ablation
recovery latency distribution
failure episode state diagram
feature importance/SHAP
```

------------------------------------------------------------------------

# 120. Strong C2 Demonstration Figure

A high-value figure:

``` text
time →
primary reports:  ● ● ● X X X
expected deadline:        |
C2 silence detected:      ▲
backup request:             →
backup response:              ●
diagnosis: hardware failure
recovery: backup
```

with real measured timestamps from a physical test.

This clearly communicates the contribution.

------------------------------------------------------------------------

# 121. Research Success Criteria

C2 is scientifically successful if experiments demonstrate defensible
improvements such as:

``` text
mode-aware timing reduces false silence alarms
context improves failure diagnosis
Backup Pipe evidence improves diagnostic discrimination
recovery preserves useful data with known provenance
```

Not every proposed mechanism must improve every metric.

------------------------------------------------------------------------

# 122. Operational Success Criteria

C2 should:

``` text
detect expected-report violations
avoid treating normal low-rate modes as failure
create auditable episodes
collect evidence
request backup/replay
diagnose
execute allowed recovery
preserve provenance
inform Golden Timeline/Decision Engine
```

without blocking the rest of GeoNex.

------------------------------------------------------------------------

# 123. Negative Results

If Backup Pipe evidence does not improve classification:

``` text
do not hide it
```

Investigate:

``` text
backup too correlated with primary?
dataset too easy?
backup features poorly designed?
labels already deterministic from another field?
insufficient scenarios?
```

The research process must remain honest.

------------------------------------------------------------------------

# 124. C2 Thesis Narrative

A strong narrative:

> Fixed missing-data rules are unsuitable for an adaptive monitoring
> network because the expected reporting interval changes with operating
> mode and telemetry silence can have different causes. GeoNex C2
> therefore models silence as a diagnostic event, combines timing,
> communication, health and spatial context, and uses an independently
> powered Backup Pipe to obtain additional evidence before selecting a
> provenance-preserving recovery or escalation action.

------------------------------------------------------------------------

# 125. Candidate Contribution Statement

> **A mode-aware silent-telemetry diagnostic and recovery framework for
> IoT landslide monitoring that combines contextual failure
> classification with independent Backup Pipe verification and
> provenance-preserving recovery.**

Final wording must reflect actual experimental evidence.

------------------------------------------------------------------------

# 126. Limitations to Report

Potential limitations:

``` text
small physical prototype
synthetic fault scenarios
limited number of devices/zones
limited radio environments
Backup Pipe can also fail
ambiguous multi-fault cases
possible-zone-damage class cannot prove geology
recovery quality depends on neighbour correlation
```

------------------------------------------------------------------------

# 127. C2 Definition of Done --- Data

-   [ ] Existing C2 datasets audited
-   [ ] Label specification created
-   [ ] Episode schema finalized
-   [ ] Scenario IDs present
-   [ ] Group-aware split frozen
-   [ ] Decision-time vs outcome fields separated
-   [ ] Leakage tests passing
-   [ ] Synthetic/physical provenance recorded

------------------------------------------------------------------------

# 128. C2 Definition of Done --- Diagnosis

-   [ ] Fixed-timeout baseline implemented
-   [ ] Mode-aware deterministic baseline implemented
-   [ ] Random Forest baseline evaluated
-   [ ] Boosted-tree candidate evaluated
-   [ ] Backup Pipe ablation completed
-   [ ] C1/C4 context ablation completed
-   [ ] Calibration evaluated where required
-   [ ] Failure/error analysis completed

------------------------------------------------------------------------

# 129. C2 Definition of Done --- Recovery

-   [ ] SD replay mechanism tested
-   [ ] Backup Pipe verification tested
-   [ ] Backup provenance retained
-   [ ] Neighbour fusion baseline implemented/evaluated if used
-   [ ] Resource availability checked before action
-   [ ] Failed recovery handled
-   [ ] Recovery latency measured
-   [ ] Recovery quality measured where numerical reconstruction occurs

------------------------------------------------------------------------

# 130. C2 Definition of Done --- Integration

-   [ ] ExpectedReportMonitor implemented
-   [ ] Silence episodes persisted
-   [ ] Diagnostic service implemented
-   [ ] Recovery policy implemented
-   [ ] C4 security boundary respected
-   [ ] C1 history integration tested
-   [ ] Golden Timeline integration tested
-   [ ] C3 provenance features available
-   [ ] Decision Engine degradation/escalation event available
-   [ ] Hardware-in-the-loop scenarios completed

------------------------------------------------------------------------

# 131. Rules for the C2 Member's AI Assistant

The C2 member may paste this guide into their own AI development chat.

That assistant must obey:

> **Do not redesign GeoNex shared architecture, database semantics,
> identifiers, operating modes, sampling-policy contract, C1/C3/C4
> responsibilities, or Golden Timeline semantics. Implement C2 within
> Documents 00--06. If a shared contract is insufficient, propose a
> versioned change for team review rather than silently changing it.**

Additionally:

-   never convert all missing values into zero;
-   never assume silence means hardware failure;
-   never use post-recovery outcomes as diagnosis inputs;
-   never use hidden injected-fault truth as a feature;
-   never treat Backup Pipe data as automatically trusted/credible;
-   never erase recovery provenance;
-   never claim `possible_zone_damage` confirms a landslide;
-   keep synthetic and physical evidence separate.

------------------------------------------------------------------------

# 132. Recommended C2 Implementation Order

``` text
1. Audit existing C2 datasets
2. Write C2 labeling specification
3. Implement expected-report monitor
4. Implement silence episode lifecycle
5. Build canonical episode dataset
6. Freeze group-aware split
7. Implement fixed-timeout baseline
8. Implement mode-aware rule baseline
9. Train Random Forest diagnostic baseline
10. Train boosted-tree candidate
11. Add neighbour/hub context
12. Add C1/C4 history
13. Implement Backup Pipe request/response
14. Run Backup Pipe ablation
15. Implement deterministic recovery policy
16. Implement SD replay
17. Implement neighbour fusion if required
18. Run stress/failure-injection tests
19. Measure recovery quality/latency
20. Freeze approved diagnostic model
21. Integrate Golden Timeline/C3/Decision Engine
22. Run physical hardware tests
23. Generate thesis/paper evidence
```

------------------------------------------------------------------------

# 133. First Coding Milestone

The first milestone should produce:

``` text
C2 dataset audit
+
C2_LABELING_SPECIFICATION.md
+
ExpectedReportMonitor
+
SilenceEpisode model
+
canonical episode builder
+
group-aware split
+
fixed-timeout baseline
+
mode-aware deterministic baseline
```

Do not start by optimizing XGBoost.

------------------------------------------------------------------------

# 134. Component Success in One Sentence

> **C2 succeeds when GeoNex can demonstrate that it recognizes telemetry
> silence according to the system's actual operating schedule, uses
> contextual and independent evidence to reason about why information
> disappeared, and recovers or escalates without pretending
> reconstructed data was directly observed.**

------------------------------------------------------------------------

# 135. Decisions Frozen by Document 06

1.  C2 is an episode-based silence-diagnosis and recovery component.
2.  C2 can trigger independently when expected telemetry does not
    arrive.
3.  Expected-report detection is deterministic and mode/policy aware.
4.  A single fixed global silence timeout is not acceptable.
5.  Observation time and arrival time remain distinct.
6.  C2 diagnosis and recovery/action selection are separate stages.
7.  The baseline diagnosis taxonomy includes normal, communication
    failure, hardware failure and possible zone damage.
8.  `possible_zone_damage` is an escalation/diagnostic hypothesis, not
    confirmation of a landslide.
9.  Backup Pipe verification is a central C2 mechanism and requires an
    ablation.
10. Backup data remains subject to C4 and C1.
11. SD replay preserves original observation timestamps and replay
    provenance.
12. Authorized recovery replay must remain distinguishable from
    malicious replay.
13. Recovered Backup Pipe values retain Backup Pipe source identity.
14. Neighbour-fused values are derived observations, never direct
    measurements.
15. Recovery confidence/provenance must be preserved for C3.
16. Post-action outcomes cannot be diagnosis/action-selection features.
17. Scenario-grouped splitting is required.
18. Fixed-timeout and mode-aware rule baselines are mandatory.
19. Random Forest and boosted trees are candidate diagnostic models, not
    predetermined winners.
20. Recovery safety/resource constraints remain deterministic.
21. A learned recovery policy is optional and must beat a meaningful
    deterministic baseline.
22. Hardware fault injection and physical Backup Pipe tests are required
    where feasible.
23. Diagnostic accuracy, silence-detection performance and recovery
    quality are evaluated separately.
24. C2 cannot silently redesign operating modes, timing policy or
    cross-component contracts.

------------------------------------------------------------------------

# 136. Decisions Intentionally Deferred

Still experimental:

``` text
exact grace durations
number of missed reports before each silence state
final diagnostic feature subset
final diagnostic classifier
final hyperparameters
exact Backup Pipe wake/request timing
exact retry counts
final recovery confidence formula
final neighbour-fusion method
whether learned action recommendation is useful
whether backup-hub switching exists in physical deployment
operational escalation thresholds
```

These require evidence or final hardware decisions.

------------------------------------------------------------------------

# 137. Next Component Guide

The next document is:

``` text
07_C3_DEVELOPMENT_GUIDE.md
```

It will define:

``` text
C3 forecasting target semantics
multi-horizon prediction
time-aware sequences
Δt and missingness
operating-mode representation
Golden Timeline feature construction
C1/C2 provenance integration
baseline models
GRU/LSTM/time-aware GRU/GRU-D candidates
leakage-safe sequence splitting
probability calibration
warning lead-time evaluation
ablation:
Sensors
→ +History
→ +Δt
→ +Mode
→ +C1
→ +C2
stress testing
Decision Engine boundary
controlled cumulative retraining
runtime inference
```

------------------------------------------------------------------------

# Document 06 Status

**`06_C2_DEVELOPMENT_GUIDE.md` --- C2 IMPLEMENTATION BASELINE READY**

The component is deliberately designed so its research value comes from
**mode-aware silence interpretation, contextual diagnosis, independent
verification and provenance-preserving recovery**, rather than from
simply training a classifier on missing-data labels.
