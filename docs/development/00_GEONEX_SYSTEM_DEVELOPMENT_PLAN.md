# 00_GEONEX_SYSTEM_DEVELOPMENT_PLAN.md

**Project:** GeoNex --- Smart Landslide Early Warning Prediction System
using IoT, Edge AI and Risk Analytics\
**Document:** System Development Plan\
**Status:** Development Baseline\
**Purpose:** Establish the common implementation strategy that all four
GeoNex research components must follow before independent development
begins.

------------------------------------------------------------------------

## 1. Why This Document Exists

GeoNex contains four separate research components, but they must not be
developed as four independent systems.

The final system must behave as one pipeline:

``` text
Physical Environment
        ↓
Sensor Network
        ↓
Telemetry Acquisition
        ↓
Communication / Gateway
        ↓
Raw Data Ingestion
        ↓
┌───────────────────────────────────────┐
│ C4 — Telemetry Trust & Provenance     │
└───────────────────┬───────────────────┘
                    ↓
┌───────────────────────────────────────┐
│ C1 — Sensor Measurement Credibility   │
└───────────────────┬───────────────────┘
                    ↓
          ┌─────────┴──────────┐
          │                    │
     Valid Stream        Missing/Silent/
          │               Fault Condition
          │                    ↓
          │          ┌─────────────────────┐
          │          │ C2 — Diagnostics &  │
          │          │ Recovery            │
          │          └──────────┬──────────┘
          │                     │
          └──────────┬──────────┘
                     ↓
              Golden Timeline
                     ↓
┌─────────────────────────────────────────┐
│ C3 — Temporal Landslide Risk Forecasting│
└────────────────────┬────────────────────┘
                     ↓
              Decision Engine
                     ↓
        Mode / Alerts / Sampling
                     ↓
               IoT Network
```

Therefore, all members will work from a shared architecture, database,
naming conventions, data contracts and repository.

------------------------------------------------------------------------

## 2. GeoNex System Objective

GeoNex is intended to provide a landslide early-warning system capable
of:

1.  continuously observing environmental and ground conditions;
2.  determining whether received telemetry is trustworthy;
3.  distinguishing sensor faults from genuine environmental changes;
4.  diagnosing missing or silent telemetry;
5.  recovering/estimating information where appropriate;
6.  forecasting future landslide risk from multivariate temporal
    behaviour;
7.  adapting sensor sampling according to the current risk state;
8.  issuing warnings when appropriate;
9.  maintaining provenance and auditability of observations and
    decisions;
10. supporting controlled future model improvement.

The system therefore addresses more than:

> "Are the current sensor values dangerous?"

GeoNex attempts to determine:

> "Can I trust the source?"

> "Can I trust the measurement?"

> "Why has information disappeared?"

> "Can the missing information be recovered?"

> "What is likely to happen next?"

> "How urgently should the system observe the environment?"

------------------------------------------------------------------------

## 3. Physical GeoNex Demonstration Architecture

The current research demonstration consists of two monitoring zones.

``` text
                         GEONEX
                  MAIN COMPUTING SYSTEM
                           │
                    Main Black Box
                     LoRa Gateway
                           │
             ┌─────────────┴─────────────┐
             │                           │
           ZONE 1                      ZONE 2
             │                           │
      Centralized Hub 1          Centralized Hub 2
             │                           │
       ┌─────┼─────┐               ┌─────┼─────┐
       │     │     │               │     │     │
      A1    B1    BK1             A2    B2    BK2
```

Where:

-   A = Type A sensing pipe
-   B = Type B sensing pipe
-   BK = independent Backup Pipe

The research demonstration additionally uses the Centralized Power Hub
to reduce prototype cost.

The Centralized Power Hub is not the Centralized Sensor Hub.

The centralized power arrangement is specific to the research
demonstration. It must not be presented as proof that a real field
deployment would use the same power architecture.

------------------------------------------------------------------------

## 4. Physical Device Responsibilities

### 4.1 Type A Pipe

Primary high-capability sensing pipe.

Planned sensing includes:

-   MPU9250
-   2 × soil-moisture sensors
-   2 × FSR402
-   DHT22
-   DS18B20
-   INA219
-   ADS1115 for analog acquisition

The pipe produces numerical telemetry representing
ground/environmental/device conditions.

------------------------------------------------------------------------

### 4.2 Type B Pipe

Secondary sensing pipe with a reduced sensor configuration.

Planned sensing includes:

-   MPU9250
-   2 × soil-moisture sensors
-   1 × FSR402
-   INA219
-   ADS1115

It provides spatial redundancy and complementary measurements.

------------------------------------------------------------------------

## 5. Backup Pipe

The Backup Pipe is an independently powered verification/recovery node.

It is particularly important to Component 2.

Its role is not simply:

> "another normal sensor pipe."

It exists to provide an independent observation path when primary
sensing/communication becomes questionable.

The finalized prototype includes an ESP32-S3, LoRa communication,
sensing hardware, power monitoring and an independent battery-based
power arrangement.

This enables scenarios such as:

``` text
Primary Pipe stops reporting
            ↓
C2 detects unexpected silence
            ↓
Backup Pipe queried / activated
            ↓
Backup responds normally
            ↓
Possible primary hardware/
communication problem
```

versus:

``` text
Multiple primary sensors disappear
            +
Backup Pipe also shows abnormal behaviour
            ↓
Possible wider zone-level problem
```

The second case must not automatically be interpreted as hardware
failure.

------------------------------------------------------------------------

## 6. Centralized Sensor Hub

Each zone contains a Centralized Sensor Hub.

Its responsibilities include:

-   zone-level sensing;
-   rainfall-related acquisition;
-   local processing;
-   communication;
-   timestamping;
-   local storage;
-   device-health monitoring;
-   supporting the pipe network.

The physical prototype contains processing, storage, LoRa,
power-monitoring and environmental/motion-related sensing hardware.

The hub must therefore be represented in the system as a first-class
device, not merely a communication relay.

------------------------------------------------------------------------

## 7. Centralized Power Hub

The Centralized Power Hub exists primarily to power the research
demonstration.

It should not be treated as an environmental sensor node.

Therefore:

``` text
Centralized Power Hub
        ≠
Centralized Sensor Hub
```

and it should not automatically produce C3 environmental features.

------------------------------------------------------------------------

## 8. Main Black Box

The Main Black Box acts as the central field gateway/control interface.

The demonstrated electronics include:

-   ESP32-S3-class controller;
-   LoRa radio;
-   external antenna;
-   control/interface circuitry;
-   buzzer;
-   power circuitry.

Its responsibilities include receiving field packets, forwarding
telemetry, receiving control instructions and supporting alerts.

It should not be treated as another landslide sensor.

------------------------------------------------------------------------

## 9. Main Computing System

The main computing platform is logically separated from the ESP32
gateway.

It hosts the higher-level software required for:

-   ingestion;
-   databases;
-   AI/ML inference;
-   decision processing;
-   API/services;
-   monitoring;
-   model management.

Therefore:

``` text
ESP32 Gateway
      ≠
AI Server
      ≠
Database
```

even when all are physically located near each other.

------------------------------------------------------------------------

## 10. Four Research Components

### C1 --- Rainfall Regime-Aware Sensor Credibility Classification

#### Main question

Is this measurement credible, suspicious/anomalous, or a genuine
environmental event?

C1 must avoid the dangerous assumption:

``` text
Unusual value = faulty sensor
```

because during an actual landslide precursor event, measurements are
expected to become unusual.

C1 therefore considers environmental context such as rainfall regime,
neighbouring measurements, historical behaviour and plausibility.

#### Main output

A measurement credibility assessment.

Current research labels may include concepts such as:

``` text
CLEAN
ANOMALY
VALID_EVENT
```

The exact production output contract will be frozen in the later data
architecture.

------------------------------------------------------------------------

## 11. C2 --- Silent-Pattern Diagnostic Classification via Backup Pipe Verification

#### Main question

Why did an expected data stream disappear?

Possible causes include:

-   normal operation;
-   communication failure;
-   hardware failure;
-   wider physical/zone abnormality.

C2 must use contextual evidence and the Backup Pipe where appropriate
rather than blindly replacing missing values.

#### C2 responsibilities

``` text
Expected observation missing
        ↓
Determine whether delay is abnormal
        ↓
Inspect device/network context
        ↓
Request independent verification
        ↓
Classify likely cause
        ↓
Select recovery/escalation action
        ↓
Attach recovery provenance
```

Recovery may include:

-   SD replay;
-   backup sensing;
-   neighbouring-sensor fusion;
-   backup hub;
-   escalation.

------------------------------------------------------------------------

## 12. C3 --- Mode-Conditioned Variable-Rate Multi-Sensor Temporal Forecasting

C3 is responsible for predicting future risk, rather than merely
classifying the current measurement.

#### Main question

Given trustworthy recent environmental history, what is the probability
that dangerous conditions will develop within a future horizon?

C3 must account for:

-   multivariate sensors;
-   temporal history;
-   changing trends;
-   irregular observation intervals;
-   elapsed time Δt;
-   operating mode;
-   validated/recovered observations;
-   multiple forecast horizons.

This component is expected to investigate temporal/deep-learning
approaches such as a time-aware GRU / GRU-D family architecture, against
appropriate baselines.

The exact final model must be determined experimentally rather than
selected only because it sounds advanced.

------------------------------------------------------------------------

## 13. C4 --- Trusted Telemetry Provenance and Device Attestation

#### Main question

Did this telemetry actually originate from a legitimate device and does
its behaviour remain trustworthy?

C4 concerns source and transmission trust.

It can use:

-   device identity;
-   registration;
-   attestation information;
-   integrity verification;
-   freshness;
-   counters/nonces;
-   replay indicators;
-   communication behaviour;
-   device behaviour;
-   radio characteristics.

C4 should combine deterministic security verification with ML where
behavioural anomaly detection provides additional value.

A machine-learning trust score must never override a failed mandatory
cryptographic/security verification.

------------------------------------------------------------------------

## 14. Clear Separation Between C4 and C1

This distinction must be understood by every developer.

### C4

Asks:

> Can I trust where this packet came from?

### C1

Asks:

> Can I trust what this measurement says about the environment?

Example:

``` text
Registered legitimate sensor
        ↓
Correctly authenticated packet
        ↓
C4: TRUSTED
but
soil moisture = impossible/spurious value
inconsistent with sensor/neighbours/context
        ↓
C1: ANOMALY
```

The reverse is also possible.

Therefore:

``` text
Source trust ≠ Measurement credibility
```

------------------------------------------------------------------------

## 15. Shared Data Philosophy

One of the most important project rules is:

> Sensors do not generate the research CSV dataset directly.

A sensor produces a measurement.

For example:

``` text
Soil Moisture Sensor
        ↓
ADC measurement
        ↓
ESP32
        ↓
Calibration
        ↓
soil_moisture = 67.4 %
```

The ESP32 combines this with metadata.

Example conceptual packet:

``` json
{
  "device_id": "A1",
  "zone_id": "Z01",
  "timestamp": "2026-10-10T08:15:20.245+05:30",
  "sequence_no": 18421,
  "mode": "RISK",
  "measurements": {
    "soil_moisture_1_pct": 67.4,
    "soil_moisture_2_pct": 69.1
  }
}
```

This is telemetry, not a training CSV.

------------------------------------------------------------------------

## 16. Operational Database vs ML Dataset

These are different things.

### Operational Database

Used by the running GeoNex system.

Contains continuously arriving:

-   telemetry;
-   metadata;
-   validation results;
-   trust assessments;
-   recovery events;
-   predictions;
-   alerts;
-   mode transitions.

### ML Dataset

A controlled snapshot derived from data for model development.

Examples:

``` text
CSV
Parquet
```

These are useful for:

-   model training;
-   experiments;
-   reproducibility;
-   sharing controlled datasets between members;
-   research evaluation.

Therefore:

``` text
LIVE SYSTEM
Sensors
   ↓
Telemetry
   ↓
Database
```

while:

``` text
MODEL DEVELOPMENT
Database / Approved Sources
          ↓
Dataset Builder
          ↓
Versioned Dataset
          ↓
CSV / Parquet
          ↓
Training
```

CSV is not the live database architecture.

------------------------------------------------------------------------

## 17. Raw Data Must Be Preserved

GeoNex should follow an important data-engineering principle:

> Do not destroy the original observation because a later AI model
> thinks it is incorrect.

Suppose:

``` text
A1 soil moisture = 97.8%
```

and C1 says:

``` text
ANOMALY
```

We should not overwrite:

``` text
97.8 → NULL
```

inside the raw data.

Instead:

``` text
RAW OBSERVATION
97.8
   │
   └── C1 result
       class = ANOMALY
       confidence = ...
```

This preserves:

-   reproducibility;
-   auditing;
-   debugging;
-   future retraining;
-   comparison of model versions;
-   research evidence.

------------------------------------------------------------------------

## 18. Immutable Raw Layer

The project should therefore maintain an append-oriented raw telemetry
layer.

Conceptually:

``` text
             PACKET
                │
                ▼
       ┌─────────────────┐
       │ RAW TELEMETRY   │
       │ preserved       │
       └────────┬────────┘
                │
       ┌────────┴─────────┐
       ↓                  ↓
      C4                  Audit
       ↓
      C1
       ↓
      C2
       ↓
Golden Timeline
```

This protects us from accidentally losing the original evidence.

------------------------------------------------------------------------

## 19. Golden Timeline

The Golden Timeline is one of the central GeoNex concepts.

It is not simply:

> another copy of the database.

It represents the best currently available temporal observation stream
for forecasting after trust, credibility and recovery information has
been considered.

For every observation, we should eventually know concepts such as:

``` text
value
timestamp
device
sensor
trust status
credibility status
recovery status
provenance
confidence
```

C3 consumes this curated temporal representation.

However, the raw observation remains preserved separately.

------------------------------------------------------------------------

## 20. Golden Data Must Retain Provenance

Consider:

``` text
10:00  A1 soil moisture = 61%
10:05  A1 soil moisture = 63%
10:10  A1 missing
10:15  A1 soil moisture = 70%
```

Suppose C2 obtains a suitable recovered estimate/backup observation for
10:10.

The Golden Timeline must not pretend that the value was an ordinary A1
observation.

Instead conceptually:

``` text
10:10
value = 66.4
source = BACKUP/RECOVERY
recovered = true
recovery_method = ...
confidence = ...
```

This allows C3 to distinguish:

``` text
observed data
```

from:

``` text
recovered data
```

That is scientifically much safer.

------------------------------------------------------------------------

## 21. Mode-Conditioned Variable-Rate Sampling

GeoNex operates conceptually through:

``` text
DEEP_SLEEP
    ↓
IDLE
    ↓
RISK
    ↓
WARNING
    ↓
EMERGENCY
```

The sampling frequency increases as risk increases.

However, we will not hard-code arbitrary final intervals in this
document.

They must be designed and justified in the dedicated sampling
specification.

The important architecture is:

``` text
Current observations
        ↓
C1/C2/C3 + system conditions
        ↓
Decision Engine
        ↓
New operating mode
        ↓
Sampling policy
        ↓
Gateway
        ↓
Sensor nodes
```

------------------------------------------------------------------------

## 22. Why Δt Matters

Variable-rate sampling means observations are not necessarily equally
spaced.

Example:

``` text
08:00
08:10
08:20
08:30
```

may later become:

``` text
08:30:00
08:30:30
08:31:00
08:31:30
```

Therefore C3 cannot blindly assume:

> every row represents the same amount of elapsed time.

Each temporal observation must preserve actual time information.

Conceptually:

``` text
Δt = current_timestamp - previous_timestamp
```

C3 can therefore learn:

``` text
measurement change
+
amount of elapsed time
+
operating mode
```

rather than interpreting row position as time.

------------------------------------------------------------------------

## 23. Mode Is Context, Not Ground Truth

A critical ML rule:

``` text
current_mode
```

can be a useful C3 contextual feature.

But we must prevent circular reasoning such as:

``` text
risk prediction
→ mode
→ mode used to construct risk label
→ model predicts same label
```

That would cause target leakage.

Mode, labels and predictions must therefore have explicitly documented
provenance.

------------------------------------------------------------------------

## 24. Decision Engine Is Separate From C3

C3 predicts risk.

The Decision Engine determines system actions.

For example:

``` text
C3:
P(danger within 30 min) = 0.82
```

does not itself mean:

``` text
turn siren on
```

Instead:

``` text
C3 prediction
       +
C1 credibility
       +
C2 recovery status
       +
C4 trust
       +
system rules
       ↓
Decision Engine
       ↓
mode / alert / sampling action
```

This separation is especially important in a safety-related system.

------------------------------------------------------------------------

## 25. AI Does Not Replace Deterministic Logic

GeoNex is an AI-enabled hybrid system.

Not every problem should be solved using ML.

Example:

``` text
Invalid cryptographic signature
```

should not be passed to a neural network asking:

> "Do you think this signature is probably valid?"

It should fail deterministic verification.

Similarly:

``` text
mandatory safety rule
```

should remain deterministic where appropriate.

Therefore:

``` text
GeoNex
=
IoT
+
Data Engineering
+
Deterministic Logic
+
Machine Learning
+
Deep Learning
+
Security Mechanisms
+
Decision Logic
```

------------------------------------------------------------------------

## 26. Model Development Philosophy

No component may begin with:

> "We decided XGBoost/GRU because it is powerful."

Research requires comparison.

Every component should follow:

``` text
Research Question
       ↓
Dataset
       ↓
Baseline
       ↓
Candidate Model(s)
       ↓
Proposed Approach
       ↓
Controlled Evaluation
       ↓
Statistical/Metric Comparison
       ↓
Justification
```

------------------------------------------------------------------------

## 27. C1 Model Direction

Current candidate direction:

``` text
Baseline
   ↓
Random Forest / simple classifier
   ↓
XGBoost / LightGBM
   ↓
Context-enhanced credibility approach
```

The research question is not:

> "Can XGBoost classify rows?"

The research question concerns whether contextual information such as
rainfall regime and neighbouring behaviour improves sensor credibility
assessment while protecting genuine environmental events.

------------------------------------------------------------------------

## 28. C2 Model Direction

C2 should be developed as a hybrid diagnostic system.

Conceptually:

``` text
Silence Detection
      ↓
Feature Construction
      ↓
Failure Classifier
      ↓
Backup Verification
      ↓
Recovery Policy
      ↓
Recovery Result
```

Candidate ML:

-   XGBoost
-   Random Forest

with deterministic safety/recovery constraints.

The research contribution should not simply be a lookup table disguised
as ML.

------------------------------------------------------------------------

## 29. C3 Model Direction

C3 should compare increasingly capable temporal representations.

Conceptually:

``` text
Sensor values only
        ↓
+ history
        ↓
+ Δt
        ↓
+ operating mode
        ↓
+ C1 credibility
        ↓
+ C2 recovery/provenance
```

This naturally supports the planned ablation study.

Candidate models include:

-   conventional tabular baseline;
-   standard GRU/LSTM baseline;
-   time-aware recurrent architecture;
-   GRU-D-style approach where appropriate.

Final selection must come from evaluation.

------------------------------------------------------------------------

## 30. C4 Model Direction

C4 is explicitly hybrid.

``` text
Cryptographic / identity verification
              +
Replay/freshness rules
              +
Behavioural features
              ↓
        Trust assessment
```

Possible ML approaches:

-   LightGBM;
-   XGBoost;
-   Isolation Forest;
-   other experimentally justified anomaly models.

Security guarantees must not depend exclusively on learned behaviour.

------------------------------------------------------------------------

## 31. Shared Component Contract

Every model must ultimately expose a predictable interface.

Conceptually:

``` text
input
  ↓
component
  ↓
structured output
```

Not:

``` text
C1 creates random CSV
C2 reads another random CSV
C3 expects completely different columns
C4 stores JSON somewhere else
```

Shared contracts will later define:

-   IDs;
-   timestamps;
-   enums;
-   confidence representation;
-   model version;
-   provenance;
-   error representation.

------------------------------------------------------------------------

## 32. Common Identifiers

Every part of the system will use standardized identifiers.

Examples:

``` text
zone_id
device_id
sensor_id
packet_id
observation_id
model_id
model_version
prediction_id
event_id
```

These identifiers must remain consistent across components.

A member must not rename:

``` text
zone_id
```

to:

``` text
area
```

inside their component without changing the shared contract.

------------------------------------------------------------------------

## 33. Timestamp Policy

Time is fundamental to GeoNex.

We need to distinguish concepts such as:

``` text
observed_at
received_at
processed_at
```

because:

``` text
sensor measured at 10:00:00
```

does not necessarily mean:

``` text
server received at 10:00:00
```

Communication delay is itself useful information for C2/C4.

Exact database types/timezone policy will be frozen in Document 02.

------------------------------------------------------------------------

## 34. Parallel Development Strategy

Once shared contracts are frozen:

``` text
                 SHARED CORE
                     │
      ┌──────────────┼───────────────┐
      ↓              ↓               ↓
     C1             C2              C3
      │              │               │
      └──────────────┼───────────────┘
                     │
                    C4
```

This diagram means shared infrastructure supports all components; it
does not mean C4 literally executes last.

Each member develops within their own component directory.

For example:

``` text
components/
├── c1_credibility/
├── c2_diagnostics/
├── c3_forecasting/
└── c4_trust/
```

Nobody creates a second independent database architecture.

------------------------------------------------------------------------

## 35. Concurrent Development Through Contract-First Design

The key mechanism enabling four people to work simultaneously is:

> Contract-first development.

Before C1 is complete, C3 can still develop against a defined C1 output
schema.

For example, if the contract states:

``` json
{
  "observation_id": "...",
  "credibility_class": "...",
  "credibility_score": 0.94,
  "model_version": "..."
}
```

C3 can use simulated/mock C1 outputs while C1 is being developed.

Later the real implementation replaces the mock.

This avoids:

> C3 waiting months for C1.

------------------------------------------------------------------------

## 36. Mock Data Is Allowed --- Silent Contract Changes Are Not

During parallel development:

``` text
Mock C1 output
Mock C2 output
Mock C4 output
```

may be used for integration testing.

But mock data must follow the exact shared schema.

This allows us to test the complete pipeline before every AI model is
finished.

------------------------------------------------------------------------

## 37. Repository Strategy

GeoNex should use a single integrated repository unless a strong
technical reason later requires otherwise.

Conceptual organization:

``` text
geonex/
│
├── apps/
├── components/
├── firmware/
├── shared/
├── database/
├── data/
├── models/
├── configs/
├── tests/
├── experiments/
├── docs/
├── scripts/
└── infrastructure/
```

The exact finalized repository tree comes later.

------------------------------------------------------------------------

## 38. Git Development Strategy

The main branch must remain stable.

Recommended workflow:

``` text
main
 │
 └── develop
      │
      ├── feature/c1-...
      ├── feature/c2-...
      ├── feature/c3-...
      └── feature/c4-...
```

Members should not directly develop large experimental changes on main.

Integration should occur through reviewed merges.

------------------------------------------------------------------------

## 39. Shared Code Must Not Be Duplicated

Common functionality belongs in shared modules.

Examples:

``` text
timestamp parsing
device IDs
schema definitions
database client
logging
configuration
feature definitions
common enums
```

We should avoid:

``` text
C1 timestamp parser
C2 timestamp parser
C3 timestamp parser
C4 timestamp parser
```

with four slightly different implementations.

------------------------------------------------------------------------

## 40. Configuration Must Not Be Hard-Coded

Avoid:

``` text
DB_PASSWORD = "password123"
```

or:

``` text
SAMPLING_INTERVAL = 30
```

scattered throughout source files.

Configuration should be centralized and environment-aware.

Examples:

``` text
.env
config/
environment variables
version-controlled safe defaults
```

Secrets must never be committed.

------------------------------------------------------------------------

## 41. Dataset Versioning

Every experimental dataset must be identifiable.

Avoid:

``` text
final.csv
final2.csv
final_new.csv
final_REAL.csv
```

Instead maintain explicit dataset metadata/versioning.

Conceptually:

``` text
C3_TEMPORAL_V4
version: 4
created_at: ...
generator_version: ...
source: synthetic
schema_version: ...
```

This is necessary for reproducible research.

------------------------------------------------------------------------

## 42. Synthetic and Physical Data Must Remain Distinguishable

This is a strict research requirement.

Every relevant record/dataset should be traceable to its origin:

``` text
SYNTHETIC
PHYSICAL_DEMO
EXTERNAL
RECOVERED
DERIVED
```

Synthetic results must not accidentally be reported as field
measurements.

------------------------------------------------------------------------

## 43. Model Versioning

A prediction without knowing which model produced it is insufficient.

Inference records should eventually contain:

``` text
model_name
model_version
prediction_time
```

This allows:

``` text
C3 v1
vs
C3 v2
```

to be audited and compared.

------------------------------------------------------------------------

## 44. Experiment Tracking

Each component should record:

-   dataset version;
-   feature set;
-   split strategy;
-   algorithm;
-   hyperparameters;
-   seed;
-   metrics;
-   model artifact;
-   code version where practical.

This makes paper/thesis results reproducible.

------------------------------------------------------------------------

## 45. Prevent Data Leakage

Leakage is one of the biggest risks to this research.

For temporal C3 data especially, we should generally avoid random row
splitting where observations from the same event/time sequence leak
across train/test.

Temporal/event/zone-aware splitting must be considered.

Similarly:

``` text
future value
```

must never be used to construct a feature for a prediction made in the
past.

------------------------------------------------------------------------

## 46. Training and Runtime Are Separate

Training:

``` text
Versioned Dataset
       ↓
Training Pipeline
       ↓
Evaluation
       ↓
Approved Model
       ↓
Model Artifact
```

Runtime:

``` text
Live Observation
       ↓
Feature Pipeline
       ↓
Approved Model Artifact
       ↓
Prediction
```

We do not retrain a model for every incoming packet.

------------------------------------------------------------------------

## 47. Controlled Self-Learning

For C3, "self-learning" must not mean:

``` text
new reading
   ↓
immediately modify production model
```

Instead:

``` text
New observations
      ↓
C4 validation
      ↓
C1 validation
      ↓
C2 recovery/provenance
      ↓
Approved accumulated dataset
      ↓
Candidate retraining
      ↓
Evaluation
      ↓
Compare with production model
      ↓
      ├── better + safe → promote
      └── worse         → reject/rollback
```

This is controlled cumulative retraining.

------------------------------------------------------------------------

## 48. Logging and Auditability

Every important system operation should produce structured logs.

Examples:

``` text
packet received
packet rejected
C4 verification failed
C1 anomaly detected
C2 recovery requested
C3 prediction produced
mode changed
warning issued
model loaded
database error
```

Logs should be machine-readable where possible.

------------------------------------------------------------------------

## 49. Failure Handling

GeoNex must assume failures will happen.

Examples:

-   sensor unavailable;
-   LoRa packet lost;
-   duplicate packet;
-   malformed packet;
-   delayed packet;
-   database temporarily unavailable;
-   C1 model unavailable;
-   C3 inference error;
-   backup pipe unavailable.

The architecture must define degraded behaviour instead of crashing the
entire pipeline.

------------------------------------------------------------------------

## 50. Safety Principle

An ML model failing must not automatically cause the entire warning
system to become blind.

The Decision Engine should understand:

``` text
prediction available
prediction unavailable
prediction low-confidence
input insufficient
system degraded
```

These states are different.

------------------------------------------------------------------------

## 51. Testing Layers

GeoNex development requires several testing levels.

``` text
Unit Tests
     ↓
Component Tests
     ↓
Contract Tests
     ↓
Integration Tests
     ↓
End-to-End Tests
     ↓
Hardware-in-the-Loop Tests
     ↓
Research Evaluation
```

AI metric evaluation alone is not enough.

------------------------------------------------------------------------

## 52. Component Definition of Done

A component is not done when:

> "the notebook reaches 95% accuracy."

A research component is done only when it has:

-   reproducible dataset;
-   preprocessing pipeline;
-   baseline;
-   proposed approach;
-   evaluation;
-   error analysis;
-   saved model;
-   inference interface;
-   tests;
-   documentation;
-   integration contract;
-   integration test;
-   research evidence/results.

------------------------------------------------------------------------

## 53. Development Phases

We will use the following project phases.

### Phase 0 --- Specification

Current stage.

Produce:

``` text
system plan
architecture
data architecture
dataset plan
sampling plan
component specifications
integration contracts
```

### Phase 1 --- Shared Infrastructure

Implement:

``` text
repository
configuration
schemas
database
common models/types
logging
dataset utilities
```

### Phase 2 --- Baseline Components

Each member develops an initial working baseline.

``` text
C1 baseline
C2 baseline
C3 baseline
C4 baseline
```

### Phase 3 --- Proposed Research Models

Each component implements and evaluates its research contribution.

### Phase 4 --- Integration

Connect:

``` text
C4
 ↓
C1
 ↓
C2/recovery
 ↓
Golden Timeline
 ↓
C3
 ↓
Decision Engine
```

### Phase 5 --- Hardware Integration

Connect real prototype telemetry.

### Phase 6 --- Stress Testing

Test:

-   packet loss;
-   sensor failure;
-   communication failure;
-   missing data;
-   stale readings;
-   irregular sampling;
-   abrupt mode changes;
-   suspicious telemetry;
-   backup failure;
-   extreme environmental scenarios.

### Phase 7 --- Final Evaluation

Produce research metrics, ablations, comparisons and final results.

------------------------------------------------------------------------

## 54. Member Development Rule

Once the four component guides are issued, each member may use their own
AI assistant.

But their AI assistant must be instructed:

> **Do not redesign the GeoNex shared architecture, database schema or
> cross-component contracts. Implement this component within the
> provided specification.**

This is essential.

Otherwise four AI chats will gradually invent four different versions of
GeoNex.

------------------------------------------------------------------------

## 55. Architecture Change Procedure

If a member discovers that a shared contract is insufficient:

``` text
Member identifies problem
        ↓
Document proposed change
        ↓
Team reviews impact
        ↓
Shared contract updated
        ↓
Schema version incremented
        ↓
Affected components updated
```

Not:

> Member silently adds five columns.

------------------------------------------------------------------------

## 56. Documentation Is Part of the Implementation

Every major architectural decision must answer:

``` text
WHAT are we doing?
WHY are we doing it?
HOW is it implemented?
WHAT alternative exists?
WHY did we choose this approach?
HOW will we validate it?
```

This directly supports:

-   thesis writing;
-   research paper;
-   supervisor discussions;
-   viva;
-   future maintainability.

------------------------------------------------------------------------

## 57. Final Target

The final project should allow the following sequence to operate
automatically:

``` text
REAL SENSOR READING
        ↓
ACQUISITION
        ↓
PACKET
        ↓
COMMUNICATION
        ↓
RAW STORAGE
        ↓
TRUST ASSESSMENT
        ↓
CREDIBILITY ASSESSMENT
        ↓
FAILURE/RECOVERY HANDLING
        ↓
GOLDEN TEMPORAL DATA
        ↓
FUTURE RISK FORECAST
        ↓
DECISION ENGINE
        ↓
OPERATING MODE
        ↓
SAMPLING POLICY
        ↓
FIELD DEVICES
```

while simultaneously supporting:

``` text
DATABASE
   ↓
VERSIONED DATASET
   ↓
REPRODUCIBLE TRAINING
   ↓
MODEL EVALUATION
   ↓
MODEL REGISTRY
   ↓
CONTROLLED DEPLOYMENT
```

------------------------------------------------------------------------

## 58. Core Development Principles

These are the rules every GeoNex developer should remember:

1.  One GeoNex system, four research components.
2.  Raw observations are preserved.
3.  Database ≠ CSV dataset.
4.  Training ≠ live inference.
5.  C4 source trust ≠ C1 measurement credibility.
6.  C2 diagnoses missing information instead of blindly imputing it.
7.  C3 predicts future risk from temporal data.
8.  Decision Engine controls operational actions.
9.  Variable sampling requires real timestamps and Δt.
10. Recovered data must retain provenance.
11. Synthetic and physical data must never be silently mixed.
12. ML does not replace deterministic security/safety mechanisms.
13. Models are selected through experiments, not assumptions.
14. All components use shared contracts.
15. All four members can develop concurrently after those contracts are
    frozen.
16. Every result must be reproducible and auditable.

------------------------------------------------------------------------

# Document 00 Status

**`00_GEONEX_SYSTEM_DEVELOPMENT_PLAN.md` --- BASELINE READY**

This document deliberately does not yet freeze database tables, exact
sampling intervals, exact C1--C4 schemas, final algorithms, or
repository implementation details. Those require their own design
documents so we do not mix system-level planning with low-level
implementation decisions.

**Next document:** `01_GEONEX_END_TO_END_ARCHITECTURE.md`.

That is where we should now go substantially deeper: every physical
device, sensor measurement, packet route, processing boundary, C1--C4
interaction, online/offline path, control path, failure path, and
deployment boundary will be mapped before we design the database.
