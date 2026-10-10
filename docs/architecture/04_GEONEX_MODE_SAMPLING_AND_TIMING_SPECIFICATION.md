# 04_GEONEX_MODE_SAMPLING_AND_TIMING_SPECIFICATION.md

**Project:** GeoNex --- Smart Landslide Early Warning Prediction System
using IoT, Edge AI and Risk Analytics\
**Document:** Mode-Conditioned Sampling, Timing and Control
Specification\
**Status:** Development Baseline\
**Depends on:** `00_GEONEX_SYSTEM_DEVELOPMENT_PLAN.md`,
`01_GEONEX_END_TO_END_ARCHITECTURE.md`,
`02_GEONEX_DATA_DATABASE_ARCHITECTURE.md`,
`03_GEONEX_DATASET_ARCHITECTURE.md`\
**Purpose:** Define the common timing model that connects sensing,
communication, C1--C4, forecasting and operational control, while
ensuring that each research component has a defensible, measurable
contribution rather than functioning as an isolated classifier.

------------------------------------------------------------------------

# 1. Why This Document Is Critical

GeoNex is not a fixed-rate sensor logger.

Its intended behaviour is:

``` text
low apparent risk
      ↓
lower observation/reporting intensity
      ↓
conditions begin changing
      ↓
increase monitoring intensity
      ↓
risk continues increasing
      ↓
faster observation/reporting
      ↓
warning / emergency response
```

This creates an important research problem:

> The meaning of time between observations changes as the operating mode
> changes.

Therefore C2 cannot diagnose silence using one fixed timeout, and C3
cannot assume that consecutive rows are equally spaced.

This document defines the timing/control architecture required to make
the four components work together correctly.

------------------------------------------------------------------------

# 2. Research Value of the Four-Component System

The four components should not be presented as four unrelated AI models.

Their stronger combined research story is:

``` text
C4
Can the source and transmission be trusted?
        ↓
C1
Can the environmental measurement be trusted?
        ↓
C2
If expected information disappears, why,
and how should the system recover?
        ↓
C3
Given the best trustworthy temporal history,
what is likely to happen next?
        ↓
Decision Engine
How should the sensing/warning system respond?
```

This gives GeoNex a coherent progression:

``` text
SOURCE TRUST
→ DATA CREDIBILITY
→ AVAILABILITY/RECOVERY
→ FUTURE RISK
→ ADAPTIVE RESPONSE
```

Each component therefore protects a different failure point in an
early-warning pipeline.

------------------------------------------------------------------------

# 3. How Each Component Becomes Research-Strong

A component is not made strong merely by selecting a complicated model.

Each component must demonstrate:

``` text
specific problem
+
clear research gap
+
appropriate mechanism
+
meaningful baseline
+
proposed contribution
+
controlled experiment
+
ablation
+
stress testing
+
operational relevance
+
limitations
```

The final thesis/paper should answer:

> What capability does this component add that a simpler GeoNex system
> would not have?

------------------------------------------------------------------------

# 4. C1 Research Value

C1's strongest research position is not simply:

> "We detect sensor anomalies."

Generic anomaly detection is already well studied.

The stronger question is:

> Can environmental context prevent a landslide monitoring system from
> incorrectly rejecting genuine hazardous changes as sensor faults?

The key distinction is:

``` text
abnormal measurement
        ≠
faulty measurement
```

A rapidly increasing soil-moisture reading during intense rainfall may
be unusual statistically while being physically legitimate.

Therefore C1 should investigate whether adding:

``` text
rainfall regime
+
temporal behaviour
+
neighbour agreement
+
device context
```

improves credibility classification.

------------------------------------------------------------------------

# 5. C1 Evidence Required

A strong C1 experiment should compare at least conceptually:

``` text
Baseline A
target sensor value only

Baseline B
target + temporal history

Experiment C
target + temporal + neighbour context

Proposed C1
target + temporal + neighbour + rainfall regime/context
```

Then demonstrate whether the proposed context improves:

``` text
macro F1
ANOMALY recall
VALID_EVENT recall
false rejection of genuine events
```

The most research-relevant error is:

``` text
genuine environmental event
        ↓
classified as sensor fault
```

because that can remove useful warning evidence.

------------------------------------------------------------------------

# 6. C2 Research Value

C2's strongest research position is not:

> "We fill missing sensor values."

Blind imputation can hide the cause of missing information.

C2 instead asks:

> What does silence mean?

A missing stream may represent:

``` text
packet loss
sensor failure
device failure
hub/network failure
or
a wider physical disturbance
```

The independent Backup Pipe gives C2 a physically meaningful
verification mechanism.

Therefore the research contribution is:

``` text
mode-aware silence detection
+
contextual failure diagnosis
+
independent backup verification
+
provenance-aware recovery/escalation
```

------------------------------------------------------------------------

# 7. C2 Evidence Required

C2 should compare:

``` text
fixed timeout
vs
mode-aware expected-report timeout
```

and:

``` text
diagnosis without backup evidence
vs
diagnosis with backup verification
```

and:

``` text
blind imputation/replacement
vs
provenance-aware recovery policy
```

Important metrics include:

``` text
failure-class macro F1
hardware/communication distinction
zone-damage recall
recovery success
recovery latency
false escalation
missed escalation
```

This directly justifies why the Backup Pipe exists as more than
redundant hardware.

------------------------------------------------------------------------

# 8. C3 Research Value

C3's strongest question is not:

> "Can a GRU predict landslides?"

The stronger question is:

> Can future risk be forecast reliably when observations arrive at
> variable intervals because the monitoring system intentionally changes
> its sensing behaviour according to risk?

This makes:

``` text
Δt
+
operating mode
+
missingness
+
credibility
+
recovery provenance
```

scientifically relevant.

------------------------------------------------------------------------

# 9. C3 Evidence Required

The planned ablation should be treated as a central research experiment:

``` text
A0  Sensor state only
A1  + temporal history
A2  + Δt
A3  + operating mode
A4  + C1 credibility
A5  + C2 recovery/provenance
```

Model comparisons should include meaningful simpler baselines before the
proposed temporal architecture.

Candidate progression:

``` text
simple persistence/threshold baseline
        ↓
tabular boosted-tree baseline
        ↓
standard GRU/LSTM
        ↓
time-aware GRU / GRU-D-style candidate
```

The final architecture must be selected by results.

Important C3 evaluation includes:

``` text
event recall
precision
PR-AUC
calibration
false alarms per unit time
warning lead time
robustness under missing/irregular data
```

A high classification accuracy alone is not sufficient evidence for an
early-warning forecasting contribution.

------------------------------------------------------------------------

# 10. C4 Research Value

C4 should not claim:

> "AI provides device authentication."

Cryptographic identity and integrity verification should remain
deterministic.

C4 becomes stronger when positioned as:

> A hybrid trust layer in which deterministic security establishes
> mandatory validity while behavioural ML detects suspicious telemetry
> patterns that valid credentials alone may not reveal.

Conceptually:

``` text
identity/signature/integrity/freshness
              ↓
      deterministic gate
              ↓
behavioural/radio/transmission evidence
              ↓
        ML anomaly/trust model
              ↓
       combined trust evidence
```

------------------------------------------------------------------------

# 11. C4 Evidence Required

C4 should compare:

``` text
deterministic checks only
vs
behavioural ML only
vs
hybrid deterministic + behavioural approach
```

It should also test scenario generalization where feasible:

``` text
normal traffic
replay
timing anomalies
spoofing-like behaviour
device/route inconsistencies
unseen behavioural anomalies
```

Security claims must remain limited to mechanisms actually implemented
and tested.

------------------------------------------------------------------------

# 12. Why Timing Connects All Four Components

Timing is not only a C3 feature.

It affects:

``` text
C4 → freshness, replay, packet interval behaviour

C1 → historical changes and neighbour alignment

C2 → whether a stream is actually late or missing

C3 → Δt and irregular temporal forecasting
```

Therefore timing must be standardized across GeoNex.

------------------------------------------------------------------------

# 13. Three Different Rates Must Not Be Confused

GeoNex must distinguish:

## 13.1 Acquisition Rate

How frequently the MCU reads a physical sensor.

Example concept:

``` text
IMU sampled many times per second
```

## 13.2 Aggregation Rate

How raw samples are summarized.

Example:

``` text
1-second vibration RMS
```

## 13.3 Reporting/Transmission Rate

How frequently a telemetry packet is sent upstream.

Example:

``` text
one summarized packet every N seconds
```

These are not necessarily equal.

------------------------------------------------------------------------

# 14. Why This Distinction Matters

For vibration:

``` text
acquiring one IMU value every five minutes
```

would lose short-duration motion.

Instead:

``` text
high-rate local acquisition
        ↓
local feature extraction
        ↓
compact summary
        ↓
slower LoRa reporting
```

can preserve useful motion information without transmitting every raw
sample.

For soil moisture, much slower acquisition may be sufficient.

Therefore a mode does not need one universal frequency for every sensor.

------------------------------------------------------------------------

# 15. Sensor-Class Sampling Profiles

Each operating mode should reference a profile containing sensor-class
policies.

Conceptually:

``` yaml
mode: RISK

soil_moisture:
  acquisition_interval: configurable
  report_interval: configurable

imu:
  acquisition_frequency: configurable
  aggregation_window: configurable
  report_interval: configurable

temperature:
  acquisition_interval: configurable

rainfall:
  acquisition_policy: configurable
```

Final numeric values are not frozen here.

They must be validated experimentally.

------------------------------------------------------------------------

# 16. Operating Modes

The GeoNex operating-mode sequence is:

``` text
DEEP_SLEEP
IDLE
RISK
WARNING
EMERGENCY
```

These modes represent operational monitoring intensity.

They should not be treated as direct landslide ground-truth classes.

------------------------------------------------------------------------

# 17. DEEP_SLEEP

Purpose:

``` text
minimum-energy monitoring during prolonged low-risk conditions
```

Expected behaviour may include:

-   reduced acquisition for slow-changing sensors;
-   reduced reporting;
-   periodic wake/check;
-   local trigger capability where hardware supports it;
-   ability to receive/apply relevant mode changes subject to
    radio/power design.

Deep Sleep must not make the system incapable of detecting meaningful
rapid changes.

Therefore wake/trigger strategy must be tested.

------------------------------------------------------------------------

# 18. IDLE

Purpose:

``` text
normal low-risk monitoring
```

The system remains regularly observable while conserving bandwidth/power
relative to higher-risk modes.

IDLE is the normal monitoring state, not "system off."

------------------------------------------------------------------------

# 19. RISK

Purpose:

``` text
increase temporal resolution because environmental evidence is becoming concerning
```

Expected behaviour:

-   more frequent relevant sensing;
-   more frequent reporting;
-   tighter C2 silence deadlines;
-   greater attention to trend evolution.

------------------------------------------------------------------------

# 20. WARNING

Purpose:

``` text
high-intensity monitoring when forecast/current evidence indicates substantial concern
```

Expected behaviour:

-   short reporting intervals;
-   increased acquisition where meaningful;
-   stronger monitoring of communication/device health;
-   rapid decision updates;
-   preparation/activation of warning mechanisms according to Decision
    Engine policy.

------------------------------------------------------------------------

# 21. EMERGENCY

Purpose:

``` text
highest operational urgency
```

The priority shifts toward:

``` text
latency
reliability
warning continuity
```

rather than maximum energy conservation.

However even EMERGENCY should not blindly transmit unlimited raw data
and congest the communication channel.

------------------------------------------------------------------------

# 22. Mode Does Not Equal Sampling Interval

Incorrect design:

``` text
RISK = every 30 seconds
```

as one global rule.

Correct design:

``` text
RISK
  ├── soil moisture policy
  ├── IMU acquisition policy
  ├── vibration aggregation policy
  ├── rainfall policy
  ├── health telemetry policy
  └── transmission policy
```

The mode selects a **sampling profile**.

------------------------------------------------------------------------

# 23. Sampling Policy Object

A versioned sampling policy should conceptually contain:

``` text
sampling_policy_id
policy_version
mode
sensor_class
acquisition_interval/frequency
aggregation_window
report_interval
event_trigger_enabled
priority
effective_from
```

This policy should be centrally configurable rather than scattered
through firmware constants.

------------------------------------------------------------------------

# 24. Why Numeric Intervals Are Not Frozen Yet

Choosing:

``` text
Deep Sleep = 30 minutes
Warning = 10 seconds
```

without evidence would be arbitrary.

Final values depend on:

``` text
sensor dynamics
power use
LoRa airtime
packet size
number of devices
event-detection latency
hardware stability
desired warning lead time
```

Therefore Document 04 freezes the mechanism, while experiments later
freeze calibrated numeric values.

------------------------------------------------------------------------

# 25. Sampling-Rate Selection Experiment

For each important sensor class, evaluate candidate rates against:

``` text
information loss
event detection delay
energy consumption
network load
storage load
forecasting performance
```

The selected profile should represent an experimentally justified
trade-off.

------------------------------------------------------------------------

# 26. Mode Manager

A dedicated logical **Mode Manager** should determine the current
system/zone mode.

The Mode Manager is part of the Decision Engine layer.

It receives evidence such as:

``` text
C3 forecast
current environmental severity
C1 credibility
C2 degradation/recovery state
C4 trust state
system-health conditions
safety rules
```

and determines whether a mode transition is appropriate.

------------------------------------------------------------------------

# 27. C3 Does Not Directly Control Firmware

Incorrect:

``` text
C3 neural network
      ↓
set ESP32 interval = 5 seconds
```

Preferred:

``` text
C3 forecast
      ↓
Decision Engine / Mode Manager
      ↓
mode decision
      ↓
sampling policy
      ↓
versioned command
      ↓
gateway
      ↓
device
```

This maintains safety, explainability and control.

------------------------------------------------------------------------

# 28. Mode Transition Concept

Conceptually:

``` text
DEEP_SLEEP
   ↕
IDLE
   ↕
RISK
   ↕
WARNING
   ↕
EMERGENCY
```

Normal transitions may be adjacent.

However safety rules may permit escalation across multiple levels when
severe evidence occurs.

Example:

``` text
IDLE
  ↓ severe local trigger
EMERGENCY
```

if the final Decision Engine policy allows it.

------------------------------------------------------------------------

# 29. Escalation and De-Escalation Are Not Symmetric

Escalation should generally respond quickly to credible worsening
evidence.

De-escalation should require stronger evidence of sustained improvement.

Otherwise the system may oscillate:

``` text
RISK
WARNING
RISK
WARNING
RISK
...
```

This is undesirable for:

``` text
power
network load
interpretability
alerts
C3 temporal context
```

------------------------------------------------------------------------

# 30. Hysteresis

Mode thresholds should use hysteresis where appropriate.

Conceptual example only:

``` text
enter WARNING when risk > upper threshold

leave WARNING only when
risk < lower threshold
for sufficient time
```

with:

``` text
lower threshold < upper threshold
```

Exact thresholds are intentionally not specified here.

------------------------------------------------------------------------

# 31. Minimum Dwell Time

A mode may require a minimum dwell duration before ordinary
de-escalation.

This prevents transient model fluctuations from continuously changing
the sampling profile.

Emergency/safety escalation may override dwell constraints where
required.

------------------------------------------------------------------------

# 32. Evidence Persistence

A transition may require:

``` text
condition persists for N evaluations
```

or:

``` text
condition persists for T duration
```

depending on the rule.

This should be configurable.

------------------------------------------------------------------------

# 33. Mode Decision Inputs Must Be Time-Stamped

Every evidence item used by the Mode Manager should include its
effective time.

The Decision Engine must avoid using stale:

``` text
C3 forecast
C1 result
C2 diagnosis
C4 assessment
```

as if it were current.

------------------------------------------------------------------------

# 34. Mode Transition Record

Every transition should produce an auditable event:

``` text
mode_event_id
zone_id
previous_mode
new_mode
decided_at
effective_at
reason_code
trigger_source
decision_policy_version
c3_prediction_id
```

Optional references may point to relevant C1/C2/C4 evidence.

------------------------------------------------------------------------

# 35. Reason Codes

Examples:

``` text
FORECAST_ESCALATION
ENVIRONMENTAL_THRESHOLD
SYSTEM_DEGRADED
SECURITY_DEGRADATION
MANUAL_OVERRIDE
EMERGENCY_TRIGGER
RISK_CLEARED
```

The final enum belongs to the shared contract.

------------------------------------------------------------------------

# 36. Zone Mode vs Device Mode

The architecture should support a **zone operating mode**.

Individual devices may have local implementation states, but the shared
operational policy should be expressed primarily at zone/system level.

Example:

``` text
Zone 1 = WARNING
Zone 2 = IDLE
```

This avoids forcing every zone to consume maximum power because one zone
is at risk.

------------------------------------------------------------------------

# 37. Device Capability Profiles

Not every device has identical hardware.

Therefore sampling policy application should consider:

``` text
device_type
sensor capabilities
power source
communication capability
firmware version
```

Example:

``` text
Type A
Type B
Backup
Sensor Hub
```

can implement different profile details under the same zone mode.

------------------------------------------------------------------------

# 38. Backup Pipe Operating Policy

The Backup Pipe should not necessarily behave identically to a primary
pipe continuously.

Its design objective includes independent verification and recovery.

Potential policy:

``` text
normal low-power monitoring
        ↓
C2 verification request
        ↓
temporary higher activity
        ↓
collect/return independent evidence
        ↓
return to appropriate backup state
```

The exact battery/sampling strategy requires hardware testing.

------------------------------------------------------------------------

# 39. Independent Backup Principle

For C2 to have research value, the Backup Pipe should preserve useful
independence from the suspected primary failure path where possible.

Independence can include:

``` text
separate power
separate sensing
direct/independent LoRa path
separate device identity
```

If primary and backup share every failure dependency, backup
verification becomes weaker.

------------------------------------------------------------------------

# 40. Event-Triggered Acquisition

Periodic sampling alone can create latency.

Example:

``` text
next scheduled report in several minutes
```

but sudden strong motion occurs now.

Where supported, local firmware may implement lightweight deterministic
event triggers.

Examples:

``` text
large IMU motion
rapid FSR change
extreme sensor threshold
rainfall mechanism event
```

A local trigger can temporarily increase acquisition/reporting or send a
priority event.

------------------------------------------------------------------------

# 41. Event Trigger Is Not a Landslide Prediction

A local trigger means:

``` text
something requires immediate attention
```

not:

``` text
a landslide has definitely been predicted
```

The event enters the broader trust/credibility/decision pipeline.

------------------------------------------------------------------------

# 42. Local Trigger Requirements

Every trigger must define:

``` text
sensor
condition
threshold/algorithm
debounce
cooldown
priority
resulting action
```

Thresholds must be calibrated/validated.

------------------------------------------------------------------------

# 43. Sampling Pipeline

A device-side pipeline should conceptually be:

``` text
physical sensor
      ↓
raw acquisition
      ↓
basic validation
      ↓
calibration
      ↓
local aggregation/features
      ↓
packet builder
      ↓
sequence/counter/timestamp
      ↓
security/provenance fields
      ↓
transmission
```

Raw high-frequency data may optionally be retained locally where storage
allows.

------------------------------------------------------------------------

# 44. High-Frequency IMU Handling

Transmitting every IMU sample over LoRa is generally undesirable.

A better pattern:

``` text
high-rate local IMU acquisition
      ↓
short window
      ↓
derive:
   mean
   max
   RMS
   variance
   peak
   orientation/tilt indicators
      ↓
transmit compact features
```

Raw windows may be retained selectively for experiments/debugging.

The exact features must be scientifically justified and tested.

------------------------------------------------------------------------

# 45. Soil-Moisture Handling

Soil moisture changes more slowly than vibration.

Its policy may therefore use:

``` text
lower acquisition rate
+
trend computation
+
mode-dependent reporting
```

but final rates require physical testing.

------------------------------------------------------------------------

# 46. FSR Handling

FSR measurements should preserve:

``` text
raw ADC
```

and calibrated/derived values only where calibration supports them.

Possible local summaries:

``` text
latest response
mean
max
rate of change
```

Do not call an uncalibrated FSR reading geological pressure.

------------------------------------------------------------------------

# 47. Rainfall Handling

The rainfall mechanism may require:

``` text
local accumulation
rate estimation
event detection
```

depending on the final calibrated implementation.

Rainfall features used by C1/C3 must be based on documented calibration
and window definitions.

------------------------------------------------------------------------

# 48. Environmental Temperature/Humidity

DHT22/DS18B20 measurements may be acquired less frequently than motion
signals unless experiments justify otherwise.

They should not dominate communication bandwidth simply because they are
available.

------------------------------------------------------------------------

# 49. Power Monitoring

INA219/INA226 values can support:

``` text
device-health monitoring
C2 diagnosis
C4 behavioural context
```

Power telemetry may have a different reporting policy from environmental
telemetry.

Critical low-power events may be transmitted immediately.

------------------------------------------------------------------------

# 50. Packet Reporting

A report should identify:

``` text
device
zone
sequence
observation time/range
mode
sampling policy version
measurements
quality flags
device-health summary
```

Security fields are added according to the C4 protocol specification.

------------------------------------------------------------------------

# 51. Multiple Observation Times

A packet may contain measurements summarized over different intervals.

Therefore the system should not assume:

``` text
packet received_at = every sensor observed_at
```

Where necessary, observations should carry their own effective
observation/window time.

------------------------------------------------------------------------

# 52. Timestamp Model

GeoNex needs at least:

``` text
observed_at
received_at
ingested_at
processed_at
```

where applicable.

For windowed sensor features, also consider:

``` text
window_start
window_end
```

------------------------------------------------------------------------

# 53. Why Multiple Times Matter

Example:

``` text
observed_at = 10:00:00
received_at = 10:00:03
processed_at = 10:00:04
```

This allows GeoNex to distinguish:

``` text
environmental timing
network delay
processing delay
```

C2/C4 can use the distinction.

------------------------------------------------------------------------

# 54. Clock Source

Sensor-node clocks can drift.

The architecture should therefore define:

``` text
RTC/local device time where available
gateway/server receive time
clock synchronization/status metadata
```

The final synchronization method depends on implemented
connectivity/hardware.

------------------------------------------------------------------------

# 55. Clock Uncertainty

If a node timestamp is unreliable:

``` text
timestamp_quality
```

or equivalent metadata should allow downstream processing to know this.

Do not silently treat a badly drifting sensor clock as perfect.

------------------------------------------------------------------------

# 56. Sequence Numbers

Every transmitting device should maintain a monotonically progressing
packet sequence/counter within a defined lifecycle.

This helps:

``` text
duplicate detection
loss estimation
replay detection
ordering
C2 diagnosis
C4 security
```

Counter reset behaviour after reboot must be defined and auditable.

------------------------------------------------------------------------

# 57. Packet ID vs Sequence Number

Conceptually:

``` text
sequence_no
```

is device-local ordering.

``` text
packet_id
```

is a globally unique system identifier.

Both are useful.

------------------------------------------------------------------------

# 58. Expected Reporting Schedule

C2 needs to know when the next report should have arrived.

For device `d`:

``` text
expected_next_report
=
last accepted report
+
active report interval
```

with appropriate policy/grace logic.

This expected interval depends on:

``` text
mode
device type
sampling policy
temporary override
event state
```

------------------------------------------------------------------------

# 59. Silence Detection Must Be Mode-Aware

Incorrect:

``` text
if no packet for 60 seconds:
    failure
```

because 60 seconds may be:

``` text
normal in IDLE
```

but:

``` text
dangerously late in WARNING
```

Correct:

``` text
active policy
      ↓
expected interval
      ↓
grace/tolerance
      ↓
late/silent decision
```

------------------------------------------------------------------------

# 60. Grace Interval

Real networks contain jitter.

Therefore:

``` text
deadline
=
expected_next_report
+
grace
```

Grace may depend on:

``` text
mode
network behaviour
retry policy
device type
```

Exact values require empirical measurement.

------------------------------------------------------------------------

# 61. Silence States

Instead of instantly declaring hardware failure, C2 can use staged
states:

``` text
ON_TIME
LATE
SUSPECTED_SILENCE
CONFIRMED_SILENCE
DIAGNOSING
RECOVERING
RESOLVED / ESCALATED
```

The exact enum can be simplified later, but staged diagnosis is
preferable to immediate fault assumptions.

------------------------------------------------------------------------

# 62. C2 Silence Workflow

``` text
expected deadline exceeded
        ↓
check active mode/policy
        ↓
check gateway/network context
        ↓
check other devices
        ↓
check device-health history
        ↓
request retry/status if possible
        ↓
query/activate Backup Pipe
        ↓
classify likely cause
        ↓
recovery or escalation
```

------------------------------------------------------------------------

# 63. Delayed Packets

A packet may arrive after C2 has declared silence.

Do not simply insert it into history as if it had arrived on time.

Store:

``` text
observed_at
received_at
late_flag
```

and preserve the fact that the runtime decision did not have that packet
at the time.

This is crucial for honest C3 backtesting.

------------------------------------------------------------------------

# 64. Duplicate Packets

Duplicate packet handling should use:

``` text
device_id
sequence_no
packet identity/security metadata
```

Raw evidence may be retained, but normalized observation processing must
avoid double-counting the same measurement.

Duplicates can also be useful C4 evidence.

------------------------------------------------------------------------

# 65. Out-of-Order Packets

Out-of-order telemetry should be stored with its true timestamps.

The live Golden Timeline may have an as-of state, while offline
reprocessing can reconstruct the best historical timeline.

These are different views.

------------------------------------------------------------------------

# 66. Runtime Golden Timeline

At time `T`, the runtime Golden Timeline contains only information
available by `T`.

This is the view C3 should use for live inference.

------------------------------------------------------------------------

# 67. Retrospective Golden Timeline

Later, delayed/recovered evidence may produce a more complete historical
timeline.

This can be used for:

``` text
analysis
retraining
ground-truth reconstruction
```

but must not be used to pretend the live system knew information earlier
than it did.

------------------------------------------------------------------------

# 68. C3 Δt

For consecutive effective sequence steps:

``` text
Δt_t = t_t - t_(t-1)
```

The model receives this information explicitly when required by the
architecture.

This prevents:

``` text
one row apart
```

from being interpreted as:

``` text
one fixed amount of time apart
```

------------------------------------------------------------------------

# 69. Per-Feature Δt

If individual sensor channels update asynchronously, C3 may need:

``` text
Δt_soil
Δt_rain
Δt_tilt
...
```

representing time since the last valid observation for each feature.

This is especially relevant to GRU-D-style missing-data handling.

Whether to use global or per-feature Δt will be determined
experimentally.

------------------------------------------------------------------------

# 70. Mode Transition Inside a C3 Window

A sequence may contain:

``` text
IDLE → RISK → WARNING
```

within one history window.

Do not replace the entire window with only the final mode unless that is
the explicitly tested representation.

Possible representations include:

``` text
mode at every timestep
```

or:

``` text
mode-transition features
```

The proposed time-aware experiment should preserve mode history where
feasible.

------------------------------------------------------------------------

# 71. Mode Duration Feature

Potential C3 contextual features include:

``` text
time_in_current_mode
number_of_mode_changes_in_window
```

These may be investigated, but must pass leakage analysis.

------------------------------------------------------------------------

# 72. Mode Leakage Warning

If mode is directly generated from the same future-risk target used to
label C3 training examples, mode can leak the answer.

Therefore mode provenance must be documented.

For synthetic datasets:

``` text
environmental process
→ observations
→ operational mode policy
```

must remain causally separate from:

``` text
future event label
```

as much as possible.

------------------------------------------------------------------------

# 73. Mode Policy for Synthetic Generation

Synthetic data should simulate mode changes based on information
available at the simulated current time.

Do not generate:

``` text
future landslide event
      ↓
assign WARNING to all earlier rows
```

without modelling the actual decision rule.

That would make mode an encoded target.

------------------------------------------------------------------------

# 74. Decision Engine Evidence

The Decision Engine may consume:

``` text
C3 probability
C3 uncertainty/confidence
C1 data-quality state
C2 system-availability state
C4 security/trust state
current measurements
current mode
manual override
```

Exact rule logic will be documented later.

------------------------------------------------------------------------

# 75. Safety Overrides

Certain deterministic conditions may require escalation independently of
C3.

Examples could include validated extreme sensor conditions or system
safety rules.

These conditions must be explicitly defined and tested.

Do not hide safety overrides inside ML code.

------------------------------------------------------------------------

# 76. Degraded Mode

The system should represent degradation.

Examples:

``` text
C3 unavailable
C1 unavailable
database temporarily unavailable
multiple sensors unavailable
C4 verification unavailable
```

The Decision Engine must distinguish:

``` text
LOW RISK
```

from:

``` text
INSUFFICIENT INFORMATION
```

These are not equivalent.

------------------------------------------------------------------------

# 77. Confidence and Availability

Every component output should eventually expose:

``` text
status
result
confidence where meaningful
model/rule version
generated_at
```

A component can return:

``` text
UNAVAILABLE
INSUFFICIENT_DATA
DEGRADED
```

instead of inventing a confident result.

------------------------------------------------------------------------

# 78. Mode Under Degradation

A failure in monitoring capability should not automatically cause
de-escalation.

Example:

``` text
WARNING
   ↓
C3 becomes unavailable
```

must not become:

``` text
IDLE
```

simply because there is no new risk score.

Fallback behaviour should be conservative and policy-defined.

------------------------------------------------------------------------

# 79. Command Path

Mode/sampling commands flow:

``` text
Decision Engine
      ↓
command record
      ↓
Main Computer
      ↓
Gateway
      ↓
LoRa/device link
      ↓
target device
      ↓
validate command
      ↓
apply policy
      ↓
ACK
```

------------------------------------------------------------------------

# 80. Command Contents

Conceptually:

``` json
{
  "command_id": "...",
  "target_device_id": "Z01-A01",
  "command_type": "SET_MODE",
  "mode": "WARNING",
  "policy_version": "...",
  "issued_at": "...",
  "expires_at": "..."
}
```

Actual security fields/protocol encoding will be defined with
C4/firmware contracts.

------------------------------------------------------------------------

# 81. Command Acknowledgement

The device should respond conceptually with:

``` text
command_id
device_id
received_at
applied_at
status
active_mode
active_policy_version
```

This allows the system to know whether the requested mode actually
became active.

------------------------------------------------------------------------

# 82. Command Idempotency

Receiving the same valid command twice should not cause unsafe duplicate
effects.

Commands should therefore use:

``` text
command_id
version/sequence
```

and idempotent handling where possible.

------------------------------------------------------------------------

# 83. Lost Command

If a command is sent but no ACK arrives:

``` text
retry according to policy
        ↓
check device communication
        ↓
C2 diagnostic path if appropriate
        ↓
mark device mode uncertain
```

The database must not simply assume success.

------------------------------------------------------------------------

# 84. Stale Command

A delayed old command must not overwrite a newer state.

Use:

``` text
command sequence/version
issued_at
expires_at
```

plus deterministic validation.

------------------------------------------------------------------------

# 85. Local Fallback Policy

If a device loses contact with the gateway, firmware should have a safe
local fallback.

Potential behaviours depend on device role and power constraints.

Examples:

``` text
retain last safe profile temporarily
activate local event triggers
enter predefined communication-recovery behaviour
```

The exact fallback must be hardware-tested.

------------------------------------------------------------------------

# 86. Gateway Failure

If the Main Black Box gateway fails:

``` text
field devices
```

may continue local sensing/storage where supported.

Sensor Hubs/microSD and device-local buffers can support later recovery.

The failure should not cause historical observations to be silently
fabricated.

------------------------------------------------------------------------

# 87. Local Buffering

Where firmware/storage permits, maintain a bounded local buffer of
unsent observations.

On communication recovery:

``` text
buffered records
      ↓
replay/upload
```

with original observation times preserved.

------------------------------------------------------------------------

# 88. SD Replay

For devices/hubs with suitable local storage, C2 recovery may request
historical data replay.

Replayed data must be marked:

``` text
replayed = true
observed_at = original time
received_at = replay time
```

This protects temporal provenance.

------------------------------------------------------------------------

# 89. Replay Recovery vs Security Replay

Important distinction:

``` text
authorized SD replay
```

is legitimate recovery.

``` text
malicious packet replay
```

is a C4 security concern.

The protocol must allow C4 to distinguish authorized recovery from
suspicious duplicate/replayed traffic.

------------------------------------------------------------------------

# 90. Backup Observation

If Backup Pipe supplies a value:

``` text
source_device = BK1
```

must remain known.

Do not rewrite it as:

``` text
source_device = A1
```

even if it fills an A1 gap.

------------------------------------------------------------------------

# 91. Neighbour Fusion

If C2 estimates a missing value from neighbouring sensors:

``` text
value
method = NEIGHBOR_FUSION
source_observation_ids
confidence
algorithm_version
```

must be retained.

The result is derived data, not direct sensing.

------------------------------------------------------------------------

# 92. C3 Treatment of Recovered Data

C3 should be able to distinguish:

``` text
DIRECT
BACKUP
SD_REPLAY
NEIGHBOR_FUSION
OTHER_RECOVERY
```

through provenance features/masks where experiments include them.

This enables the C3 `+C2` ablation.

------------------------------------------------------------------------

# 93. Latency Budget

End-to-end warning latency can be decomposed:

``` text
L_total
=
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
+ L_command_or_alert
```

Not every term occurs for every event.

------------------------------------------------------------------------

# 94. Dominant Latency

For local server inference, ML/database processing may be relatively
fast.

The dominant delay can instead be:

``` text
waiting for the next sample/report
```

especially in low-risk modes.

Therefore adaptive sampling can improve responsiveness even if the AI
model itself is already fast.

This must be measured rather than assumed.

------------------------------------------------------------------------

# 95. Latency Measurement

Every major pipeline stage should emit timestamps so actual latency can
be measured.

Examples:

``` text
sensor observation
packet transmit
gateway receive
ingestion
C4 complete
C1 complete
C2 complete
C3 complete
decision complete
alert issued
```

This produces a defensible end-to-end latency evaluation.

------------------------------------------------------------------------

# 96. Latency Research Result

The final evaluation should report:

``` text
median latency
high-percentile latency
mode-specific latency
failure/recovery latency
```

rather than only one average.

Exact percentile choices will be fixed in the validation plan.

------------------------------------------------------------------------

# 97. LoRa Constraints

LoRa offers long-range, low-power communication but has limited
throughput.

Therefore GeoNex should avoid:

``` text
unbounded high-frequency raw streaming
```

especially from multiple nodes.

Mode policies must consider:

``` text
packet size
airtime
spreading factor/configuration
collision risk
retry behaviour
regulatory constraints
number of devices
```

Actual radio configuration must be tested on the prototype.

------------------------------------------------------------------------

# 98. Priority Messaging

Messages can conceptually have priorities:

``` text
EMERGENCY_EVENT
MODE_COMMAND
SECURITY/FAILURE EVENT
NORMAL TELEMETRY
BULK REPLAY
```

Priority scheduling can prevent historical replay from delaying an
emergency message.

The exact MAC/queue mechanism depends on firmware design.

------------------------------------------------------------------------

# 99. Replay Throttling

When communication returns after a long outage, a device may have many
stored observations.

Do not flood the radio with all history before current critical
telemetry.

Preferred:

``` text
current critical state first
      ↓
controlled historical replay
```

------------------------------------------------------------------------

# 100. Packet Batching

Low-risk modes may batch multiple slow-changing observations where this
reduces overhead.

However batching increases delivery latency.

Therefore batching policy should be mode-dependent and experimentally
evaluated.

------------------------------------------------------------------------

# 101. Reliability vs Energy Trade-Off

Mode-conditioned sampling exists because GeoNex has competing
objectives:

``` text
higher sampling
→ better temporal resolution
→ potentially faster detection
but
→ more energy
→ more radio airtime
→ more storage
```

and:

``` text
lower sampling
→ lower energy/network load
but
→ potentially slower detection
```

The research/engineering goal is not simply maximum sampling.

It is sufficient information at appropriate operational cost.

------------------------------------------------------------------------

# 102. Research Evaluation of Variable-Rate Sampling

The final system should compare:

``` text
fixed-rate policy
vs
mode-conditioned variable-rate policy
```

where feasible.

Metrics may include:

``` text
estimated/measured energy consumption
packet count
radio airtime
data volume
event detection latency
forecast performance
warning lead time
missed events
```

This provides evidence for the adaptive-sampling design.

------------------------------------------------------------------------

# 103. Power Evaluation

For the research demo, A/B/hubs use centralized prototype power, so
direct battery-life claims for those nodes would be inappropriate.

However:

``` text
current/power measurements
+
packet/activity counts
+
controlled experiments
```

can still evaluate relative consumption of sampling policies.

Backup Pipe battery/solar behaviour can be evaluated separately.

Real-field lifetime claims require an appropriate field-power model or
deployment evidence.

------------------------------------------------------------------------

# 104. C3 and System-Lifetime Story

C3 contributes to more than prediction.

Its risk forecast supports the Decision Engine in selecting monitoring
intensity.

Therefore the system-level story is:

``` text
forecasted risk
      ↓
adaptive mode
      ↓
sampling/reporting intensity
      ↓
resource use + warning responsiveness
```

C3 does not directly "save battery."

Rather, its forecast is one evidence source enabling a resource-aware
adaptive policy.

This wording is scientifically safer.

------------------------------------------------------------------------

# 105. C1 and System Reliability Story

C1 protects the decision pipeline from:

``` text
bad sensor measurement
```

while attempting not to suppress:

``` text
genuine unusual environmental change
```

Therefore C1 contributes to reliability by improving measurement
credibility assessment.

Its value must be demonstrated through reduced harmful
misclassification, not merely claimed.

------------------------------------------------------------------------

# 106. C2 and System Reliability Story

C2 protects against:

``` text
information disappearance
```

by identifying whether silence represents a device/network problem or
potentially meaningful wider condition, then selecting a
recovery/escalation path.

This contributes to availability and fault tolerance.

------------------------------------------------------------------------

# 107. C4 and System Reliability Story

C4 protects against:

``` text
untrusted source/transmission behaviour
```

so downstream models are less likely to act on malicious, replayed or
otherwise invalid telemetry.

Its value is trust/provenance and security resilience, not environmental
anomaly detection.

------------------------------------------------------------------------

# 108. Combined Research Story

A strong final GeoNex explanation is:

> GeoNex investigates whether landslide early-warning reliability can be
> improved by treating telemetry trust, measurement credibility, data
> availability and future-risk forecasting as connected but distinct
> problems, while adapting sensing intensity to operational risk.

This is stronger than presenting four disconnected classifiers.

------------------------------------------------------------------------

# 109. Component Dependency Without Component Collapse

Although integrated:

``` text
C4 → C1 → C2/C3
```

each component must remain independently evaluable.

Otherwise one component's failure can make it impossible to determine
another component's contribution.

Therefore experiments require:

``` text
standalone baseline
+
component-specific proposed approach
+
integrated experiment
```

------------------------------------------------------------------------

# 110. Avoiding Research Overclaim

Do not claim:

``` text
GeoNex prevents landslides
```

It does not.

Do not claim:

``` text
GeoNex guarantees accurate early warning
```

without field-scale evidence.

Appropriate claims concern:

``` text
prediction/diagnostic performance
prototype behaviour
robustness
latency
data trust
adaptive monitoring
```

under the evaluated conditions.

------------------------------------------------------------------------

# 111. Avoiding Synthetic-Data Overclaim

If strong results are obtained on synthetic datasets:

``` text
high synthetic test performance
```

means performance on the modeled synthetic distribution.

It does not prove equivalent real-world landslide performance.

Physical prototype and external/real data should be reported separately.

------------------------------------------------------------------------

# 112. Common Mode Contract

Shared enum:

``` text
DEEP_SLEEP
IDLE
RISK
WARNING
EMERGENCY
```

All components must use these exact semantic mode names once the
contract is frozen.

No component should independently invent:

``` text
NORMAL
HIGH
DANGER
```

as equivalent operating modes.

Risk labels may have different names because risk class and operating
mode are different concepts.

------------------------------------------------------------------------

# 113. Sampling Policy Version

Every telemetry packet should eventually allow the server to determine:

``` text
which sampling/reporting policy was active
```

through:

``` text
policy_version
```

or equivalent.

This is important for C2 expected-report logic and C3 interpretation.

------------------------------------------------------------------------

# 114. Mode Version

The system should record:

``` text
mode
mode_since
mode_policy_version
```

where relevant.

This enables reproducible reconstruction of operating behaviour.

------------------------------------------------------------------------

# 115. Firmware Configuration

Firmware should receive configurable profiles rather than requiring
source-code edits for every experiment.

Conceptually:

``` text
default safe configuration
+
server-distributed approved policy
```

with validation and bounds.

------------------------------------------------------------------------

# 116. Safe Bounds

Even configurable intervals should have firmware safety bounds.

Example concept:

``` text
server requests impossible/unsafe interval
        ↓
device rejects command
        ↓
ACK = INVALID_POLICY
```

This protects against malformed configuration.

Exact limits depend on hardware tests.

------------------------------------------------------------------------

# 117. Firmware Watchdog

ESP32 firmware should use appropriate watchdog/recovery mechanisms so a
blocked sensor/radio operation does not permanently stop monitoring.

Watchdog resets should be logged and become device-health evidence.

------------------------------------------------------------------------

# 118. Sensor Read Failure

A failed sensor read should produce an explicit state:

``` text
missing/invalid measurement
+
reason
```

rather than:

``` text
0
```

unless zero is physically the actual reading.

Using numeric zero for missing data can corrupt C1/C3.

------------------------------------------------------------------------

# 119. Quality Flags

Possible local quality flags:

``` text
READ_OK
READ_TIMEOUT
OUT_OF_ADC_RANGE
CALIBRATION_ERROR
SENSOR_NOT_AVAILABLE
```

C1 remains responsible for higher-level credibility assessment.

------------------------------------------------------------------------

# 120. Communication Retry

Retries should be bounded.

Store:

``` text
retry_count
```

where feasible because it can support C2/C4 analysis.

Unlimited retry loops can increase energy use and block new critical
data.

------------------------------------------------------------------------

# 121. Device Reboot

On reboot:

``` text
boot_id
```

or equivalent session metadata can distinguish legitimate sequence reset
from replay/counter anomalies.

This is especially valuable to C4.

------------------------------------------------------------------------

# 122. Backup Activation Audit

Every C2 backup action should record:

``` text
request time
target backup device
response time
measurements returned
verification outcome
recovery action
```

This provides measurable evidence for C2's research contribution.

------------------------------------------------------------------------

# 123. Mode Transition Audit

Every transition must allow later reconstruction:

``` text
what was known?
which rule/model version?
why did mode change?
when did devices actually apply it?
```

This supports thesis analysis and debugging.

------------------------------------------------------------------------

# 124. Manual Override

For prototype testing, an authorized manual mode override is useful.

It must be logged as:

``` text
MANUAL_OVERRIDE
```

so it is not confused with an AI-generated transition.

------------------------------------------------------------------------

# 125. Simulation Mode

Development should support simulated time/device input so mode logic can
be tested without waiting hours in real time.

Simulation-generated records must remain marked as simulated.

------------------------------------------------------------------------

# 126. Hardware-in-the-Loop Timing Tests

Before final evaluation, test:

``` text
mode command propagation
ACK latency
actual acquisition interval
actual report interval
packet loss
local buffering
replay
backup activation
gateway interruption
```

using physical hardware.

------------------------------------------------------------------------

# 127. Clock/Timing Acceptance Tests

For each device type verify:

``` text
timestamps increase correctly
sequence increases correctly
mode changes applied
policy version reported
expected interval approximately maintained
reboot behaviour known
delayed packet identifiable
```

------------------------------------------------------------------------

# 128. C2 Timing Acceptance Tests

Create controlled scenarios:

``` text
normal IDLE delay
normal WARNING delay
single lost packet
multiple lost packets
primary device powered off
radio disconnected
hub unavailable
backup unavailable
whole-zone interruption
```

C2 must respond according to active policy.

------------------------------------------------------------------------

# 129. C3 Timing Acceptance Tests

Create equivalent environmental sequences with different observation
schedules:

``` text
regular sampling
mild irregularity
large gaps
mode transitions
missing channels
recovered values
```

Measure how candidate models degrade.

This directly tests the value of Δt/missingness/mode-aware modeling.

------------------------------------------------------------------------

# 130. C4 Timing Acceptance Tests

Test:

``` text
valid packet cadence
duplicate packet
old packet
counter reuse
unexpected interval
reboot/counter reset
authorized SD replay
```

C4 must distinguish legitimate operational behaviour from
security-relevant anomalies where the protocol provides sufficient
evidence.

------------------------------------------------------------------------

# 131. C1 Timing Acceptance Tests

Test:

``` text
rapid genuine environmental change
isolated sensor spike
slow drift
neighbour-consistent extreme
neighbour-inconsistent extreme
rainfall-associated rise
```

This evaluates whether temporal/context features improve credibility
classification.

------------------------------------------------------------------------

# 132. Integration Success Criteria

The integrated system should demonstrate at minimum:

``` text
1. Physical telemetry enters the system.
2. C4 security/trust evidence is generated.
3. C1 credibility evidence is generated.
4. Missing streams can trigger C2.
5. Recovery retains provenance.
6. Golden Timeline is produced.
7. C3 receives real Δt/mode information.
8. C3 forecast is produced.
9. Decision Engine evaluates evidence.
10. Mode command is issued.
11. Device applies/ACKs the mode.
12. Reporting behaviour changes according to policy.
13. Alerts can be activated through defined rules.
14. Entire chain is logged/auditable.
```

------------------------------------------------------------------------

# 133. Research Success Criteria --- C1

C1 succeeds scientifically if it demonstrates, under a defensible
dataset/evaluation:

``` text
context improves credibility decisions
```

especially by protecting genuine environmental events while detecting
actual anomalies.

It does not need 100% accuracy.

------------------------------------------------------------------------

# 134. Research Success Criteria --- C2

C2 succeeds scientifically if it demonstrates that:

``` text
mode-aware silence/context/backup verification
```

improves diagnosis and/or recovery over simpler timeout/imputation
approaches.

------------------------------------------------------------------------

# 135. Research Success Criteria --- C3

C3 succeeds scientifically if it demonstrates that:

``` text
temporal history
+
real elapsed time
+
mode/provenance information
```

provides measurable forecasting/robustness value over simpler baselines
under variable-rate/missing-data conditions.

------------------------------------------------------------------------

# 136. Research Success Criteria --- C4

C4 succeeds scientifically if it demonstrates that:

``` text
deterministic security
+
behavioural analysis
```

provides useful detection/trust capability beyond either an
inappropriate ML-only approach or basic checks alone, within the tested
threat model.

------------------------------------------------------------------------

# 137. System-Level Success Criteria

GeoNex succeeds as an integrated research prototype if the four
contributions combine without losing:

``` text
provenance
timing correctness
component boundaries
auditability
failure awareness
```

and adaptive sensing produces a measurable trade-off between monitoring
cost and responsiveness.

------------------------------------------------------------------------

# 138. Decisions Frozen by Document 04

The following become baseline architectural decisions:

1.  Acquisition, aggregation and reporting rates are separate concepts.
2.  Modes select versioned sampling profiles rather than one universal
    interval.
3.  Modes are `DEEP_SLEEP`, `IDLE`, `RISK`, `WARNING`, `EMERGENCY`.
4.  Mode is operational context, not landslide ground truth.
5.  The Decision Engine/Mode Manager controls mode changes; C3 does not
    directly control firmware.
6.  Escalation/de-escalation should support hysteresis/persistence.
7.  Minimum dwell behaviour is supported.
8.  Safety escalation may override ordinary transition restrictions.
9.  Sensor classes may have different acquisition policies under one
    mode.
10. C2 expected-report logic is mode/policy aware.
11. C2 must not use one fixed global silence timeout.
12. Runtime and retrospective timelines remain distinguishable.
13. Delayed/replayed records retain original observation and actual
    receipt times.
14. C3 receives actual timing information/Δt where required.
15. Missingness/recovery provenance must not be silently erased.
16. Commands require identity, version/order, validity and
    acknowledgement semantics.
17. Lost/stale/duplicate commands must be handled deterministically.
18. Devices require a defined communication-loss fallback.
19. Local buffering/replay preserves provenance.
20. Authorized recovery replay must be distinguishable from malicious
    replay.
21. High-frequency sensor signals may be locally aggregated before LoRa
    transmission.
22. Priority traffic must not be blocked by bulk historical replay.
23. End-to-end latency must be measured by stage.
24. Variable-rate policy must be evaluated against fixed-rate
    alternatives where feasible.
25. C1--C4 research value must be established through baselines,
    ablations, stress tests and operational metrics---not model
    complexity alone.

------------------------------------------------------------------------

# 139. Decisions Intentionally Deferred

Still not frozen:

``` text
exact per-mode acquisition intervals
exact per-mode report intervals
exact IMU acquisition frequency
exact aggregation windows
exact C2 grace times
exact C2 number-of-missed-report thresholds
exact hysteresis thresholds
exact minimum dwell durations
exact C3 risk thresholds
exact Decision Engine mode-transition equations
exact LoRa radio parameters
exact retry counts
exact local trigger thresholds
exact command encoding/security format
```

These values require prototype measurement, literature/engineering
justification, or controlled experimentation.

------------------------------------------------------------------------

# 140. Required Experiments Before Freezing Numeric Timing

Before final timing values are accepted, collect:

``` text
sensor dynamics
radio packet success
radio latency
packet airtime
power/current measurements
gateway latency
component inference latency
database latency
command/ACK latency
event detection delay
```

Then select timing profiles based on evidence.

------------------------------------------------------------------------

# 141. Recommended Research Narrative

The four-component research can be presented as a reliability chain:

``` text
TRUST THE SOURCE
       C4
        ↓
TRUST THE MEASUREMENT
       C1
        ↓
MAINTAIN INFORMATION AVAILABILITY
       C2
        ↓
FORECAST WHAT HAPPENS NEXT
       C3
        ↓
ADAPT MONITORING AND RESPONSE
   DECISION ENGINE
```

This provides a clear justification for why all four components belong
in one GeoNex system.

------------------------------------------------------------------------

# 142. What Makes GeoNex More Than Four Models

The integration itself should preserve:

``` text
security provenance
measurement credibility
failure provenance
temporal uncertainty
adaptive operation
```

A prediction is therefore not simply:

``` text
risk = HIGH
```

It can be interpreted together with:

``` text
which devices contributed?
were they trusted?
were measurements credible?
were values recovered?
how old were they?
what mode was active?
which model generated the prediction?
what action followed?
```

This auditability is particularly valuable for a safety-oriented
research prototype.

------------------------------------------------------------------------

# 143. Development Gate After Document 04

Before independent component implementation begins, the remaining
documentation must convert these system rules into component-specific
instructions and integration contracts.

The component guides must not simply explain how to train a model.

Each must define:

``` text
research contribution
research question/hypothesis
input contract
dataset
feature engineering
baselines
candidate algorithms
proposed method
justification
training
evaluation
ablation
stress testing
runtime inference
database interaction
cross-component interaction
tests
deliverables
paper/thesis evidence
definition of done
```

------------------------------------------------------------------------

# 144. Next Documents

The next stage should now create the component guides one at a time:

``` text
05_C1_DEVELOPMENT_GUIDE.md
06_C2_DEVELOPMENT_GUIDE.md
07_C3_DEVELOPMENT_GUIDE.md
08_C4_DEVELOPMENT_GUIDE.md
```

Each guide must be copy-paste-ready for the relevant team member's AI
development chat while explicitly prohibiting redesign of shared GeoNex
contracts.

After the four guides:

``` text
09_GEONEX_MODEL_SELECTION_AND_JUSTIFICATION.md
10_GEONEX_RESEARCH_THEORY_AND_CONCEPTS.md
11_GEONEX_INTEGRATION_CONTRACT.md
12_GEONEX_TESTING_AND_VALIDATION_PLAN.md
13_GEONEX_MLOPS_AND_REPRODUCIBILITY_PLAN.md
```

Naming may be reconciled with the final documentation index before
repository initialization.

------------------------------------------------------------------------

# Document 04 Status

**`04_GEONEX_MODE_SAMPLING_AND_TIMING_SPECIFICATION.md` --- DEVELOPMENT
BASELINE READY**

The document intentionally freezes **how** variable-rate monitoring
works while leaving exact numeric intervals and thresholds to
evidence-based experiments.

The central implementation principle is:

> **GeoNex should increase information collection when risk or
> uncertainty demands it, reduce unnecessary monitoring cost when
> conditions permit, preserve the real timing and provenance of every
> observation, and evaluate whether each C1--C4 contribution measurably
> improves the reliability of the complete early-warning pipeline.**
