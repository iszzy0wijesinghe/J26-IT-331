# 01_GEONEX_END_TO_END_ARCHITECTURE.md

**Project:** GeoNex --- Smart Landslide Early Warning Prediction System
using IoT, Edge AI and Risk Analytics\
**Document:** End-to-End System Architecture\
**Status:** Architecture Baseline\
**Depends on:** `00_GEONEX_SYSTEM_DEVELOPMENT_PLAN.md`\
**Purpose:** Define how the GeoNex physical devices, sensors,
communication paths, ingestion services, C1--C4 research components,
Golden Timeline, Decision Engine, operating modes, storage, offline
training and control paths fit together as one implementable system.

------------------------------------------------------------------------

# 1. Purpose of This Architecture

Document 00 established the development principles.

This document answers the next question:

> **What exactly exists in GeoNex, where does each responsibility live,
> and how does information travel through the complete system?**

The architecture must support both:

1.  the **research demonstration** currently being built; and
2.  a software design that remains scientifically valid for later
    field-oriented evaluation.

This document therefore maps:

-   physical devices;
-   sensing responsibilities;
-   telemetry acquisition;
-   packet movement;
-   raw storage;
-   C4 trust processing;
-   C1 measurement credibility processing;
-   C2 silence diagnosis and recovery;
-   Golden Timeline construction;
-   C3 temporal forecasting;
-   Decision Engine behaviour;
-   variable-rate sampling control;
-   alerts;
-   offline dataset generation;
-   model training/deployment;
-   failure paths;
-   provenance;
-   integration boundaries.

It intentionally does **not** yet freeze the complete SQL schema or
final sampling intervals. Those belong to later specifications.

------------------------------------------------------------------------

# 2. Architectural Principles

The following principles are mandatory.

## 2.1 One Integrated System

C1, C2, C3 and C4 are research components inside one GeoNex system.

They are not four unrelated applications.

## 2.2 Raw Evidence Is Preserved

The system stores original received telemetry before learned
credibility/recovery decisions modify the usable analytical
representation.

## 2.3 Trust, Credibility, Recovery and Forecasting Are Different Problems

``` text
C4 → Is the source/transmission trustworthy?

C1 → Is the environmental measurement credible?

C2 → Why is expected information missing and what recovery is justified?

C3 → What future risk is indicated by the trustworthy temporal history?
```

## 2.4 AI Prediction Is Not the Same as Operational Control

C3 produces forecasts.

The Decision Engine determines actions such as:

-   operating-mode changes;
-   sampling-policy changes;
-   warnings;
-   siren/visual activation;
-   degraded-state behaviour.

## 2.5 Time Is First-Class Data

Every important event must retain time information.

Variable-rate sensing makes actual timestamps and elapsed time (`Δt`)
essential.

## 2.6 Provenance Is Never Silently Removed

Original, recovered, derived and synthetic information must remain
distinguishable.

------------------------------------------------------------------------

# 3. Top-Level End-to-End Architecture

``` text
┌─────────────────────────────────────────────────────────────────────┐
│                    PHYSICAL MONITORING ENVIRONMENT                  │
│                                                                     │
│       Zone 1                                Zone 2                  │
│   A1   B1   BK1                         A2   B2   BK2               │
│        │                                     │                      │
│   Centralized Sensor Hub 1              Centralized Sensor Hub 2    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                          LoRa / Field
                         Communication
                               │
                               ▼
                    ┌────────────────────┐
                    │   MAIN BLACK BOX   │
                    │ ESP32-S3 Gateway   │
                    │ LoRa + Alert I/O   │
                    └─────────┬──────────┘
                              │
                    Gateway/Host Interface
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     MAIN COMPUTING SYSTEM                           │
│                                                                     │
│  Ingestion → Raw Storage → C4 → C1 → C2 when required              │
│                                  │                                  │
│                                  └────→ Golden Timeline             │
│                                               │                     │
│                                               ▼                     │
│                                              C3                     │
│                                               │                     │
│                                               ▼                     │
│                                        Decision Engine              │
│                                               │                     │
│             ┌─────────────────────────────────┼───────────────┐     │
│             ↓                                 ↓               ↓     │
│          Alerts                         Mode Control       Audit     │
│                                               │                     │
└───────────────────────────────────────────────┼─────────────────────┘
                                                │
                                                ▼
                                       Main Black Box
                                                │
                                                ▼
                                  Hubs / Sensor Nodes
```

This is the main online runtime architecture.

------------------------------------------------------------------------

# 4. Research Demonstration Physical Topology

The confirmed demonstration contains two monitoring zones.

``` text
                         MAIN COMPUTING SYSTEM
                                  │
                           MAIN BLACK BOX
                           LoRa Gateway
                                  │
                  ┌───────────────┴───────────────┐
                  │                               │
                ZONE 1                          ZONE 2
                  │                               │
       Centralized Sensor Hub 1        Centralized Sensor Hub 2
                  │                               │
           ┌──────┼──────┐                 ┌──────┼──────┐
           │      │      │                 │      │      │
          A1      B1    BK1               A2      B2    BK2
```

Each zone therefore has:

-   one Type A primary pipe;
-   one Type B primary pipe;
-   one independent Backup Pipe;
-   one Centralized Sensor Hub.

The demonstration additionally contains one Centralized Power Hub.

The Centralized Power Hub belongs to the demonstration power
architecture and must not be confused with either monitoring zone's
Centralized Sensor Hub.

------------------------------------------------------------------------

# 5. Confirmed Device Inventory

## 5.1 Type A Pipes --- Two Units

Controller:

-   ESP32-S3

Sensing/electronic hardware:

-   MPU9250;
-   2 × soil-moisture sensors;
-   2 × FSR402;
-   DHT22;
-   DS18B20;
-   INA219;
-   ADS1115.

Type A is the higher-capability primary pipe.

## 5.2 Type B Pipes --- Two Units

Controller:

-   ESP32-C3 Super Mini

Sensing/electronic hardware:

-   MPU9250;
-   2 × soil-moisture sensors;
-   1 × FSR402;
-   INA219;
-   ADS1115.

Type B provides another primary observation point with a reduced sensor
set.

## 5.3 Backup Pipes --- Two Units

Confirmed design includes:

-   ESP32-S3;
-   LoRa SX1278;
-   2 × soil-moisture sensors;
-   2 × FSR402;
-   DHT22;
-   DS18B20;
-   INA219;
-   ADS1115;
-   12 V 2000 mAh battery;
-   2 × 1.5 W 12 V mini solar panels.

The Backup Pipe is independently powered and provides an independent
verification/recovery path.

## 5.4 Centralized Sensor Hubs --- Two Units

Confirmed design includes:

-   ESP32-S3;
-   ESP32 DevKit V1;
-   RTC;
-   microSD;
-   INA226;
-   CAN;
-   MPU6050;
-   LoRa SX1278;
-   rainfall measurement mechanism;
-   barometer.

The rainfall mechanism includes the prototype combination of:

-   3D-printed funnel/cup mechanism;
-   5 kg load cell;
-   HX711;
-   float switch;
-   servo.

The exact engineering conversion from raw rainfall mechanism
measurements to validated rainfall quantities must be documented and
calibrated during implementation.

## 5.5 Main Black Box --- One Unit

Confirmed system design includes:

-   Lenovo ThinkCentre M700;
-   Intel Core i5 6th generation;
-   8 GB RAM;
-   256 GB SSD;
-   ESP32-S3 gateway;
-   SX1278 433 MHz LoRa;
-   siren/visual alert support.

The ESP32/LoRa portion is the field gateway/control interface.

The ThinkCentre-class computer is the main computing host.

## 5.6 Centralized Power Hub --- One Demonstration Arrangement

The demonstration uses a shared 12 V power arrangement for Type A/Type B
pipes and sensor hubs.

Confirmed design includes:

-   12 V 10 A SMPS;
-   ATO/ATC fuse holders;
-   blade fuses;
-   master switch;
-   indicator;
-   terminal distribution;
-   suitable wiring.

Backup Pipes remain independently battery/solar powered.

The Main Black Box/main computing equipment uses its own appropriate
mains-powered arrangement.

This shared Centralized Power Hub is a **prototype cost-reduction
mechanism**, not the intended claim for real-world field power
architecture.

------------------------------------------------------------------------

# 6. Sensor-to-Measurement Mapping

Most physical sensors ultimately provide numerical values after
acquisition and calibration.

However, the system must distinguish:

``` text
RAW ELECTRICAL/DEVICE READING
            ↓
CALIBRATION / CONVERSION
            ↓
ENGINEERING MEASUREMENT
            ↓
FEATURE
```

These are not automatically the same thing.

------------------------------------------------------------------------

# 7. Type A Measurement Families

## 7.1 Soil Moisture

Two probes provide independent local moisture observations.

Conceptual engineering fields:

``` text
soil_moisture_1_pct
soil_moisture_2_pct
```

The actual percentage conversion must come from sensor calibration.

Raw ADC values should remain available where practical.

## 7.2 FSR402

FSR402 is a force-sensitive resistor.

Its raw output is an analog electrical response.

The architecture should not automatically label the raw value as an
exact physical pressure unless the sensor/mechanical assembly has been
calibrated for that interpretation.

Recommended conceptual separation:

``` text
fsr_1_raw
fsr_2_raw

optional calibrated/derived quantity:
fsr_1_force_estimate
fsr_2_force_estimate
```

Exact units must be determined from the calibration procedure.

## 7.3 MPU9250

MPU9250 can provide inertial measurements such as:

``` text
accel_x
accel_y
accel_z

gyro_x
gyro_y
gyro_z
```

and, when the magnetometer is actually configured and used:

``` text
mag_x
mag_y
mag_z
```

Derived orientation/ground-motion features may include:

``` text
tilt_deg
tilt_change
vibration_magnitude
```

Derived features must be explicitly marked as derived rather than raw
sensor channels.

## 7.4 DHT22

Can provide:

``` text
air_temperature_c
relative_humidity_pct
```

## 7.5 DS18B20

Provides local temperature:

``` text
temperature_c
```

Its physical placement determines what that temperature represents. It
must not automatically be called "soil temperature" unless
installed/calibrated for that purpose.

## 7.6 INA219

Provides device/power measurements such as:

``` text
bus_voltage_v
current_a
power_w
```

depending on firmware/library configuration.

These are primarily device-health/power features rather than direct
landslide-environment features.

## 7.7 ADS1115

ADS1115 is an ADC, not an environmental sensor.

It digitizes analog channels from connected sensors.

Therefore it should not appear in the ML dataset as a standalone
environmental variable called "ADS1115".

------------------------------------------------------------------------

# 8. Type B Measurement Families

Type B follows the same measurement principles for its available
hardware:

``` text
soil_moisture_1
soil_moisture_2

fsr_1

accelerometer channels
gyroscope channels
optional magnetometer channels
derived tilt/vibration

power-health measurements
```

It does not automatically contain Type A-only measurements.

The shared schema must tolerate device-specific sensor availability
without inventing measurements that a device cannot physically produce.

------------------------------------------------------------------------

# 9. Backup Pipe Measurement Families

The Backup Pipe can provide measurements corresponding to its installed
sensors:

``` text
soil moisture
FSR responses
air temperature
relative humidity
DS18B20 temperature
device voltage/current/power
```

Its key architectural property is not merely the sensor list.

Its key property is **independence**.

It has a separate controller, communication path and independent power
source, allowing it to provide evidence when primary infrastructure is
questionable.

------------------------------------------------------------------------

# 10. Centralized Sensor Hub Measurement Families

The hub can contribute zone-level measurements and metadata.

Potential confirmed hardware-derived families include:

``` text
rainfall-related measurements
barometric pressure
hub acceleration/motion
hub power status
device health
```

Rainfall features such as:

``` text
rain_15m_sum
rain_1h_sum
rain_6h_sum
```

are **derived temporal features**, not direct instantaneous sensor
outputs.

They should be generated from calibrated rainfall observations with
explicit time windows.

------------------------------------------------------------------------

# 11. Environmental Measurements vs Device-Health Measurements

This distinction is important.

## Environmental / Ground Measurements

Examples:

``` text
soil moisture
rainfall
temperature
humidity
barometric pressure
tilt/motion-related environmental observations
FSR-derived ground/mechanical response
```

## Device / Infrastructure Health

Examples:

``` text
supply voltage
current
power
battery condition
restart count
communication retries
packet delay
SD availability
sensor fault flags
```

Both may be useful to AI components, but they represent different
phenomena.

C3 should not automatically receive every device-health variable merely
because it exists.

------------------------------------------------------------------------

# 12. Acquisition Layer

Each embedded node requires an acquisition pipeline.

Conceptually:

``` text
Sensor
   ↓
Driver / ADC
   ↓
Raw Reading
   ↓
Calibration
   ↓
Range / Validity Check
   ↓
Timestamp
   ↓
Observation Object
```

The firmware should preserve enough information to distinguish:

-   measurement unavailable;
-   sensor read failure;
-   valid zero;
-   out-of-range reading;
-   stale reading.

A missing value must not automatically become numerical zero.

------------------------------------------------------------------------

# 13. Local Timestamping

Where possible, the system should record the time the observation was
actually produced.

At minimum the architecture distinguishes:

``` text
observed_at
received_at
processed_at
```

For example:

``` text
observed_at  = sensor/node observation time
received_at  = ingestion/gateway/server receipt time
processed_at = component processing time
```

This allows communication delay and processing delay to be measured
instead of hidden.

------------------------------------------------------------------------

# 14. Sequence Numbers

Each transmitting device should maintain a packet sequence/counter
mechanism suitable for its firmware/security design.

This helps detect:

-   missing packets;
-   duplicates;
-   out-of-order delivery;
-   replay patterns.

Sequence information is therefore useful to C2 and C4.

------------------------------------------------------------------------

# 15. Device Identity

Every field device must have a stable system identity.

Conceptually:

``` text
Z01-A01
Z01-B01
Z01-BK01
Z01-HUB01

Z02-A01
Z02-B01
Z02-BK01
Z02-HUB01
```

The exact naming convention will be frozen in the data-contract
specification.

The important requirement is that identity is stable and
machine-readable.

------------------------------------------------------------------------

# 16. Observation Identity

Individual observations should eventually be uniquely traceable.

A useful hierarchy is:

``` text
packet_id
   └── one transmitted packet

observation_id
   └── one measurement contained in or derived from a packet
```

One packet may contain multiple measurements.

------------------------------------------------------------------------

# 17. Telemetry Packet Concept

A field packet should carry more than values.

Conceptually:

``` json
{
  "schema_version": "...",
  "packet_id": "...",
  "device_id": "...",
  "zone_id": "...",
  "sequence_no": 18421,
  "observed_at": "...",
  "mode": "RISK",
  "measurements": {
    "soil_moisture_1_pct": 67.4,
    "soil_moisture_2_pct": 69.1
  },
  "device_health": {
    "supply_voltage_v": 12.1
  },
  "security": {
    "...": "..."
  }
}
```

This is a conceptual contract.

The exact serialized LoRa packet must account for payload-size
constraints and may use a compact binary representation rather than
verbose JSON over the radio.

------------------------------------------------------------------------

# 18. Radio Payload vs Internal Data Object

A major implementation distinction:

``` text
LoRa packet format
        ≠
server-side JSON object
        ≠
database row
        ≠
ML training row
```

For radio efficiency, the physical LoRa payload may be compact.

After reception, the gateway/ingestion service can decode it into a
richer internal representation.

This prevents us from designing the entire database around radio-byte
constraints.

------------------------------------------------------------------------

# 19. Main Black Box Gateway Boundary

The ESP32-S3 LoRa gateway is responsible for field communication.

Conceptually:

``` text
LoRa Packet
    ↓
ESP32 Gateway
    ↓
Frame Validation / Decode
    ↓
Host Transport
    ↓
Ingestion Service
```

The gateway should not contain the entire C1--C4 research stack.

The higher-level AI/data pipeline belongs on the main computing system
unless a later experiment explicitly investigates edge placement.

------------------------------------------------------------------------

# 20. Gateway-to-Host Interface

The exact physical/software host interface must be finalized during
implementation.

Possible mechanisms include serial/USB or a network interface, depending
on the final gateway firmware/hardware arrangement.

The architectural requirement is:

``` text
Gateway
   ↓
reliable framed host transport
   ↓
Ingestion Service
```

The ingestion service must be able to detect malformed, duplicate and
incomplete messages.

------------------------------------------------------------------------

# 21. Ingestion Service

The ingestion service is the first main-computer software boundary.

Responsibilities:

1.  receive decoded gateway messages;
2.  validate schema/version;
3.  assign/verify server-side receipt metadata;
4.  prevent accidental duplicate ingestion;
5.  persist raw telemetry;
6.  publish/forward the event for downstream processing;
7.  record ingestion errors.

It must not silently alter suspicious measurements.

------------------------------------------------------------------------

# 22. Persist Before Destructive Interpretation

The preferred reliability pattern is:

``` text
Receive
   ↓
Basic structural validation
   ↓
Persist original/raw event
   ↓
Process C4/C1/C2
```

This ensures a later model/software failure does not erase the received
evidence.

"Raw" here means the received decoded telemetry representation plus
enough original packet/frame information for audit where practical.

------------------------------------------------------------------------

# 23. C4 Processing Boundary

After ingestion, C4 evaluates source/transmission trust.

C4 may use deterministic evidence such as:

``` text
registered device?
approved identity?
integrity verification passed?
fresh sequence/counter?
replay detected?
attestation/firmware state acceptable?
```

and behavioural evidence such as:

``` text
unexpected transmission interval
unusual retry behaviour
RSSI/SNR deviation
unexpected packet timing
device/location mismatch
abnormal restart/fault pattern
```

Not every field is guaranteed to be available in the first prototype.
The implementation must only claim features actually collected.

------------------------------------------------------------------------

# 24. C4 Hybrid Decision

Conceptually:

``` text
             TELEMETRY
                 │
        ┌────────┴────────┐
        ↓                 ↓
Deterministic        Behavioural
Verification         ML Analysis
        │                 │
        └────────┬────────┘
                 ↓
          Trust Assessment
```

A mandatory deterministic failure can force rejection/quarantine even if
the behavioural model considers the packet normal.

------------------------------------------------------------------------

# 25. C4 Output

Conceptual output:

``` json
{
  "packet_id": "...",
  "trust_class": "TRUSTED",
  "trust_score": 0.97,
  "mandatory_verification_passed": true,
  "replay_suspected": false,
  "model_version": "...",
  "processed_at": "..."
}
```

Exact enums/fields are not frozen here.

------------------------------------------------------------------------

# 26. Quarantine Path

If a packet fails mandatory security verification:

``` text
Raw packet preserved
       ↓
C4 failure
       ↓
Quarantine / security event
       ↓
Do not treat as trusted environmental evidence
```

Preservation does not mean acceptance.

The event remains available for audit/security research.

------------------------------------------------------------------------

# 27. C1 Processing Boundary

C1 evaluates measurement credibility.

C1 should operate on measurements from packets that satisfy the required
trust policy, while retaining access to relevant context.

Possible evidence includes:

``` text
current sensor value
historical value
rate of change
rainfall regime
neighbouring sensor behaviour
physical plausibility
device-health context
C4 trust metadata
```

------------------------------------------------------------------------

# 28. C1 Must Protect Genuine Hazard Events

Example:

``` text
soil moisture rapidly increases
+
heavy rainfall is occurring
+
neighbouring sensors show compatible movement
```

The reading may be unusual but environmentally plausible.

C1 should therefore be designed to distinguish a genuine extreme event
from sensor malfunction.

This is the purpose of concepts such as:

``` text
CLEAN
ANOMALY
VALID_EVENT
```

rather than a simplistic normal/abnormal interpretation.

------------------------------------------------------------------------

# 29. C1 Output

Conceptual:

``` json
{
  "observation_id": "...",
  "credibility_class": "VALID_EVENT",
  "credibility_score": 0.94,
  "context_version": "...",
  "model_version": "...",
  "processed_at": "..."
}
```

The original value remains unchanged in raw storage.

------------------------------------------------------------------------

# 30. Where C2 Actually Enters the Architecture

C2 is not simply:

``` text
C4 → C1 → C2 for every row
```

C2 is primarily event-driven by **missing/silent/failed expected
information**.

Conceptually:

``` text
Sampling Policy
      ↓
Expected Observation Schedule
      ↓
Did expected observation arrive?
      │
   ┌──┴───┐
   │      │
  YES     NO
   │      │
   ↓      ↓
C4/C1    Silence Monitor
           ↓
           C2
```

C2 may also receive explicit sensor/device fault indications.

------------------------------------------------------------------------

# 31. Expected-Observation Scheduler

C2 requires knowledge of what should have happened.

If a node is in a low-rate mode, a long gap may be completely normal.

If the same gap occurs during EMERGENCY mode, it may indicate failure.

Therefore C2 requires:

``` text
device
+
current commanded sampling policy
+
last observation time
+
expected next observation time
+
tolerance
```

Without mode-aware expectations, silence detection will generate false
alarms.

------------------------------------------------------------------------

# 32. C2 Silence Detection

Conceptually:

``` text
expected_next_at
        +
allowed_tolerance
        ↓
current time exceeds deadline?
        ↓
YES
        ↓
silence event
```

Exact timeout/tolerance values must be specified later and may depend
on:

-   sampling interval;
-   communication design;
-   retry policy;
-   device type;
-   operating mode.

------------------------------------------------------------------------

# 33. C2 Diagnostic Evidence

When silence is detected, C2 may inspect:

``` text
last primary observation
last device-health status
packet-loss pattern
gateway reception history
neighbouring devices
hub status
power status
backup-pipe response
SD/local replay availability
zone-wide communication behaviour
```

This supports diagnosis rather than blind imputation.

------------------------------------------------------------------------

# 34. Backup Verification Path

A key C2 path is:

``` text
Primary stream unexpectedly silent
            ↓
Request/activate independent Backup Pipe
            ↓
Backup response received?
       ┌────┴────┐
       │         │
      YES        NO
       │         │
       ↓         ↓
Compare      Broader failure/
evidence     zone uncertainty
```

A responding backup can provide evidence that the environmental zone is
still observable even if the primary path has failed.

A non-responding backup does **not by itself prove a landslide**. It
increases uncertainty and requires wider contextual diagnosis.

------------------------------------------------------------------------

# 35. C2 Diagnosis vs Recovery

These are separate concepts.

``` text
DIAGNOSIS
What probably failed?
```

versus:

``` text
RECOVERY
What should the system do about it?
```

Possible diagnosis concepts include:

``` text
communication failure
primary sensor/device failure
multi-sensor gap
hub failure
possible zone-level physical abnormality
```

Possible recovery actions include:

``` text
REQUEST_SD_REPLAY
ACTIVATE_BACKUP_SENSOR
USE_NEIGHBOR_FUSION
SWITCH_BACKUP_HUB
ESCALATE
```

The exact taxonomy must be harmonized in the C2 specification.

------------------------------------------------------------------------

# 36. Recovery Must Be Evidence-Preserving

If C2 reconstructs/replaces a missing point, it must record:

``` text
original expected source
missing status
recovery source
recovery method
recovered value
confidence
time of recovery
component/model/rule version
```

A recovered value must never become indistinguishable from a directly
observed value.

------------------------------------------------------------------------

# 37. Golden Timeline Builder

The Golden Timeline Builder combines usable evidence into a
forecasting-oriented temporal representation.

Conceptually:

``` text
Raw Observation
      +
C4 Trust
      +
C1 Credibility
      +
C2 Recovery/Provenance
      ↓
Golden Timeline Builder
      ↓
Forecast-ready temporal observation
```

The Golden Timeline is therefore a curated analytical layer, not the raw
database.

------------------------------------------------------------------------

# 38. Example Golden Observation

Conceptually:

``` json
{
  "zone_id": "Z01",
  "sensor_id": "...",
  "timestamp": "...",
  "value": 66.4,
  "value_origin": "RECOVERED",
  "trust_class": "TRUSTED",
  "credibility_class": "CLEAN",
  "recovered": true,
  "recovery_method": "BACKUP_SENSOR",
  "recovery_confidence": 0.88
}
```

Exact schema comes later.

------------------------------------------------------------------------

# 39. C3 Input Window

C3 does not simply receive one current row.

It consumes a temporal window/history.

Conceptually:

``` text
t-5  ─┐
t-4   │
t-3   ├── temporal sequence
t-2   │
t-1   │
t     ─┘
       ↓
      C3
       ↓
future risk
```

The sequence contains multiple sensor/features and timing context.

------------------------------------------------------------------------

# 40. C3 Variable-Rate Representation

Because sampling changes by mode:

``` text
timestamp
value
Δt
mode
```

must remain aligned.

Example:

``` text
08:00:00   moisture=54   Δt=...
08:10:00   moisture=55   Δt=600 s
08:20:00   moisture=57   Δt=600 s
08:20:30   moisture=60   Δt=30 s
08:21:00   moisture=63   Δt=30 s
```

A temporal model must not interpret these as five equally spaced events
unless data are explicitly resampled under a documented method.

------------------------------------------------------------------------

# 41. C3 Feature Families

Potential C3 feature families include:

### Environmental state

``` text
soil moisture
rainfall
tilt/motion
vibration
temperature/humidity where justified
barometric information where justified
```

### Temporal features

``` text
Δt
rolling rainfall
rates of change
rolling statistics
trend features
```

### Context

``` text
operating mode
zone/device context
```

### Data-quality context

``` text
C1 credibility
C2 recovered flag
recovery confidence
missingness indicators
```

C4 may influence which observations are allowed into the Golden Timeline
rather than necessarily becoming a direct predictive environmental
feature.

Exact feature selection must be justified experimentally.

------------------------------------------------------------------------

# 42. C3 Forecast Outputs

C3 is intended to support future-risk forecasting.

Conceptual outputs may include:

``` text
risk probability within horizon
risk class
time-to-danger estimate
forecast confidence/quality information
```

Multiple horizons may be investigated, for example near-future windows.

Exact horizons and target construction must be formally specified before
final training.

------------------------------------------------------------------------

# 43. C3 Does Not Directly Command Hardware

Correct:

``` text
C3 → prediction → Decision Engine → action
```

Incorrect:

``` text
C3 neural network → directly switch siren
```

The separation improves safety, auditability and research clarity.

------------------------------------------------------------------------

# 44. Decision Engine Inputs

The Decision Engine can consume:

``` text
C3 forecast
C1 credibility state
C2 recovery/system-health state
C4 trust/security state
current operating mode
configured thresholds/policies
system degradation state
```

It then selects an operational action.

------------------------------------------------------------------------

# 45. Decision Engine Outputs

Possible output categories:

``` text
desired operating mode
sampling policy
warning level
alert action
recovery/control command
system-health/degraded-state flag
```

The exact rule table/state machine will be defined in a later
specification.

------------------------------------------------------------------------

# 46. Operating Mode State Machine

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

The implementation should not assume transitions can only move upward.

Risk may decrease.

However, mode downgrades may require hysteresis/persistence to avoid
rapid oscillation.

------------------------------------------------------------------------

# 47. Why Hysteresis Is Needed

Without hysteresis:

``` text
risk = 0.69 → RISK
risk = 0.71 → WARNING
risk = 0.69 → RISK
risk = 0.71 → WARNING
```

could cause repeated mode switching.

A robust state policy can use:

-   different enter/exit thresholds;
-   persistence duration;
-   multiple consecutive predictions;
-   minimum dwell time.

Exact values must be validated rather than invented here.

------------------------------------------------------------------------

# 48. Sampling Policy Manager

The Sampling Policy Manager translates mode into device behaviour.

Conceptually:

``` text
Operating Mode
      ↓
Sampling Policy
      ↓
per-device / per-sensor schedule
      ↓
control command
```

The policy may eventually specify:

``` text
sensor sampling interval
packet transmission interval
backup readiness/wake behaviour
local aggregation behaviour
```

Exact intervals remain a separate design decision.

------------------------------------------------------------------------

# 49. Sampling vs Transmission Rate

These must not automatically be assumed identical.

A device could theoretically:

``` text
sample every 10 seconds
transmit every 30 seconds
```

by batching observations.

Whether GeoNex should do this depends on memory, latency, radio/power
requirements and research goals.

Therefore architecture should distinguish:

``` text
sampling_interval
transmission_interval
```

even if the first prototype sets them equal.

------------------------------------------------------------------------

# 50. Control Command Path

Mode/sampling changes travel in the reverse direction of telemetry.

``` text
Decision Engine
      ↓
Sampling Policy Manager
      ↓
Command Service
      ↓
Main Black Box Gateway
      ↓
LoRa
      ↓
Target Hub/Node
      ↓
Validate Command
      ↓
Apply Policy
      ↓
Acknowledgement
```

This creates a closed-loop sensing system.

------------------------------------------------------------------------

# 51. Command Acknowledgement

A mode change should not be assumed successful merely because the server
transmitted a command.

Conceptually:

``` text
command created
      ↓
command transmitted
      ↓
device receives
      ↓
device applies
      ↓
ACK
      ↓
server records applied state
```

Failure to acknowledge becomes system-health evidence.

------------------------------------------------------------------------

# 52. Current Mode vs Desired Mode

The architecture should distinguish:

``` text
desired_mode
```

from:

``` text
reported/applied_mode
```

because communication failure may cause them to differ.

This is important for C2 silence expectations.

------------------------------------------------------------------------

# 53. Alert Path

Warnings can be generated from the Decision Engine.

Conceptually:

``` text
Decision Engine
      ↓
Alert Event
      ↓
Alert Service
      ├── local siren
      ├── visual indicator
      └── external notification channel(s)
```

External notification technologies should only be documented as
finalized after their implementation is confirmed.

------------------------------------------------------------------------

# 54. Local Alert Independence

A robust architecture should not make every local emergency alert
dependent on a remote internet/cloud service.

The Main Black Box can support local warning behaviour even if external
connectivity is unavailable, provided the local decision stack and field
communication remain operational.

------------------------------------------------------------------------

# 55. Online Runtime Data Path

The main online path is:

``` text
1. Sensor measurement
2. Local acquisition/calibration
3. Packet construction
4. LoRa transmission
5. Main Black Box reception
6. Host forwarding
7. Ingestion
8. Raw persistence
9. C4 trust assessment
10. C1 credibility assessment
11. C2 only when diagnostic/recovery conditions require it
12. Golden Timeline update
13. C3 temporal inference when forecast conditions are met
14. Decision Engine
15. Mode/alert decision
16. Command transmission
17. Device acknowledgement
18. Audit/logging
```

Not every step must block the next packet synchronously.

------------------------------------------------------------------------

# 56. Avoiding Unnecessary Pipeline Delay

The architecture should use event-driven processing rather than
repeatedly exporting/importing CSV files during runtime.

Incorrect runtime design:

``` text
sensor
 ↓
CSV
 ↓
C4 writes CSV
 ↓
C1 reads CSV
 ↓
C1 writes another CSV
 ↓
C2 reads CSV
...
```

Correct direction:

``` text
Telemetry Event
      ↓
Operational Storage / Event Processing
      ↓
C4/C1/C2 services
      ↓
Golden Timeline
      ↓
C3
```

CSV/Parquet belong primarily to offline dataset/research workflows.

------------------------------------------------------------------------

# 57. Processing Does Introduce Latency

No real system has zero delay.

GeoNex latency can include:

``` text
sensor acquisition latency
local processing latency
LoRa transmission latency
gateway latency
ingestion latency
database latency
C4/C1/C2 processing latency
C3 inference latency
decision latency
command latency
```

The engineering goal is not "zero latency".

The goal is:

> **bounded and measured end-to-end latency that remains acceptable
> relative to the landslide early-warning horizon.**

Latency should therefore be instrumented.

------------------------------------------------------------------------

# 58. Asynchronous vs Synchronous Processing

Not every task belongs on the critical path.

### Critical/near-real-time

``` text
ingestion
mandatory C4 verification
required C1 assessment
silence detection
C3 inference
decision/alert
```

### Can often be asynchronous

``` text
long-term dataset export
experiment tracking
retraining
heavy analytics
report generation
archival
```

This separation prevents research-management tasks from delaying
warnings.

------------------------------------------------------------------------

# 59. Offline Dataset Architecture

Operational data becomes research datasets through a controlled builder.

``` text
Operational Database
      +
approved external/synthetic sources
      ↓
Dataset Builder
      ↓
Schema Validation
      ↓
Feature/Label Construction
      ↓
Quality Checks
      ↓
Versioned Dataset
      ↓
CSV / Parquet
```

The dataset builder must record source/provenance and version
information.

------------------------------------------------------------------------

# 60. Component-Specific Dataset Views

The four components do not necessarily train on identical rows.

Conceptually:

``` text
Shared source data
      │
      ├── C1 credibility dataset
      ├── C2 diagnostic/recovery dataset
      ├── C3 temporal forecasting dataset
      └── C4 trust/anomaly dataset
```

Each dataset requires its own:

-   target;
-   feature definition;
-   leakage rules;
-   split strategy;
-   evaluation protocol.

------------------------------------------------------------------------

# 61. C1 Dataset Path

Conceptually:

``` text
Raw/approved measurements
      +
rainfall context
      +
neighbour context
      +
fault/event labels
      ↓
C1 Dataset Builder
      ↓
C1 Versioned Dataset
```

The research must preserve the distinction between anomalous sensor
behaviour and genuine environmental events.

------------------------------------------------------------------------

# 62. C2 Dataset Path

Conceptually:

``` text
expected schedule
+
missing/silence events
+
device/network health
+
backup verification
+
known failure scenario/outcome
      ↓
C2 Dataset Builder
      ↓
C2 Diagnostic Dataset
```

Recovery-action labels must not simply encode a deterministic lookup if
the research claim is ML-based.

------------------------------------------------------------------------

# 63. C3 Dataset Path

Conceptually:

``` text
Golden Timeline
      ↓
Temporal Window Builder
      ↓
Feature Construction
      ↓
Future-Horizon Label Construction
      ↓
Leakage Validation
      ↓
C3 Versioned Dataset
```

C3 is the component where temporal leakage is particularly dangerous.

------------------------------------------------------------------------

# 64. C4 Dataset Path

Conceptually:

``` text
raw packet metadata
+
identity/security results
+
radio/transmission behaviour
+
known attack/fault scenarios
      ↓
C4 Dataset Builder
      ↓
C4 Versioned Dataset
```

Deterministic verification results and behavioural ML targets must
remain conceptually distinguishable.

------------------------------------------------------------------------

# 65. Training Architecture

Each component follows a reproducible offline pipeline.

``` text
Versioned Dataset
      ↓
Preprocessing
      ↓
Train/Validation/Test Strategy
      ↓
Baseline
      ↓
Candidate Models
      ↓
Evaluation
      ↓
Error Analysis
      ↓
Selected Candidate
      ↓
Model Artifact
      ↓
Model Registry/Metadata
```

------------------------------------------------------------------------

# 66. Deployment Architecture

Approved model artifacts are loaded into runtime inference services.

``` text
Model Registry / Approved Artifact
             ↓
        Inference Service
             ↓
       Runtime Prediction
```

Training code and inference code should share preprocessing definitions
where possible to reduce training-serving skew.

------------------------------------------------------------------------

# 67. Model Promotion

A newly trained model does not automatically become production.

Conceptually:

``` text
candidate model
      ↓
offline evaluation
      ↓
stress evaluation
      ↓
compare with current approved model
      ↓
approval
      ↓
deployment
```

Rollback must remain possible.

------------------------------------------------------------------------

# 68. Controlled C3 Retraining

The planned controlled self-learning mechanism is:

``` text
new accumulated data
      ↓
quality/trust/provenance filtering
      ↓
new dataset version
      ↓
candidate C3 training
      ↓
evaluation
      ↓
promotion decision
```

This is not uncontrolled online weight modification.

------------------------------------------------------------------------

# 69. Database Architectural Layers

Before defining actual tables, the database architecture should
conceptually support:

``` text
DEVICE / CONFIGURATION DATA
RAW TELEMETRY
SECURITY/TRUST ASSESSMENTS
CREDIBILITY ASSESSMENTS
SILENCE/RECOVERY EVENTS
GOLDEN TIMELINE
FORECASTS
DECISIONS
MODE TRANSITIONS
COMMANDS/ACKNOWLEDGEMENTS
ALERTS
MODEL/DATASET METADATA
AUDIT/LOG INFORMATION
```

Document 02 will convert these concepts into concrete database
structures.

------------------------------------------------------------------------

# 70. Recommended Database Direction

For the main operational architecture, a relational database with strong
time-series support is appropriate.

A strong candidate is:

``` text
PostgreSQL
+
TimescaleDB extension
```

Reasons include:

-   relational integrity;
-   SQL querying;
-   device/configuration relationships;
-   timestamped telemetry;
-   time-window aggregation;
-   compatibility with Python/ML tooling;
-   ability to retain normalized operational metadata while supporting
    high-volume time-series data.

This remains an architectural recommendation until the database design
is formally frozen.

Versioned ML datasets can additionally use Parquet and CSV exports.

------------------------------------------------------------------------

# 71. Why Not Use CSV as the Runtime Database

CSV does not provide the operational guarantees needed for:

-   concurrent writes;
-   relational integrity;
-   efficient indexed queries;
-   transactional updates;
-   model/version relationships;
-   device configuration;
-   event tracking;
-   reliable multi-service integration.

CSV remains useful for controlled research exchange and model
experiments.

------------------------------------------------------------------------

# 72. Online and Offline Paths Must Coexist

``` text
                        ┌──→ ONLINE INFERENCE → DECISION
LIVE TELEMETRY → DB ────┤
                        └──→ OFFLINE DATASET BUILDER
                                   ↓
                                TRAINING
                                   ↓
                              NEW ARTIFACT
```

This allows the same system to operate while research experiments
continue independently.

------------------------------------------------------------------------

# 73. Failure Path --- Packet Loss

``` text
expected packet
      ↓
not received
      ↓
mode-aware timeout
      ↓
C2 silence event
      ↓
diagnostic evidence
      ↓
backup verification/recovery
      ↓
Golden Timeline provenance
```

A missing packet must not automatically be replaced with zero.

------------------------------------------------------------------------

# 74. Failure Path --- C4 Security Failure

``` text
packet received
      ↓
raw preservation
      ↓
mandatory C4 verification fails
      ↓
quarantine/security event
      ↓
excluded from trusted environmental stream
      ↓
Decision Engine may receive degraded/security state
```

------------------------------------------------------------------------

# 75. Failure Path --- C1 Anomaly

``` text
trusted packet
      ↓
measurement implausible/inconsistent
      ↓
C1 ANOMALY
      ↓
raw value preserved
      ↓
Golden Timeline policy decides whether/how it is usable
      ↓
possible diagnostic follow-up
```

C1 classification does not delete the original value.

------------------------------------------------------------------------

# 76. Failure Path --- Backup Unavailable

``` text
primary silence
      ↓
backup requested
      ↓
backup unavailable
      ↓
uncertainty increases
      ↓
neighbour/hub/network evidence
      ↓
C2 diagnosis / escalation
      ↓
Decision Engine receives degraded state
```

Backup failure must not be hidden.

------------------------------------------------------------------------

# 77. Failure Path --- C3 Unavailable

``` text
C3 inference failure
      ↓
prediction_status = unavailable
      ↓
Decision Engine
      ↓
fallback/degraded safety policy
```

The exact fallback policy will be designed separately.

The system must not fabricate a normal/low-risk prediction.

------------------------------------------------------------------------

# 78. Failure Path --- Database Temporarily Unavailable

A production-quality design should avoid simply discarding incoming
field data.

Possible implementation mechanisms may include:

-   gateway/local buffering;
-   retry queues;
-   hub microSD retention;
-   idempotent replay.

The exact implementation will be selected during infrastructure
development.

The existing hub microSD capability is particularly relevant to
replay/recovery research.

------------------------------------------------------------------------

# 79. Duplicate and Replay Are Different Concepts

A retransmission caused by communication recovery is not automatically a
malicious replay attack.

Therefore the system should distinguish:

``` text
legitimate retry/duplicate
```

from:

``` text
security replay behaviour
```

using sequence, acknowledgement, freshness and protocol context.

This is an important C2/C4 integration issue.

------------------------------------------------------------------------

# 80. Local SD Replay

Where the hub/node architecture supports retained observations:

``` text
live transmission fails
      ↓
local data retained
      ↓
connection recovers / C2 requests replay
      ↓
historical observations retransmitted
      ↓
server deduplicates
      ↓
original observed_at preserved
      ↓
late/replayed-for-recovery provenance recorded
```

`received_at` will therefore be later than `observed_at`.

------------------------------------------------------------------------

# 81. Delayed Data and C3

Late data must not be allowed to rewrite historical real-time decisions
without clear semantics.

Two uses must be distinguished:

### Runtime decision history

What information was actually available at decision time?

### Retrospective/training history

What information was later recovered and can improve the complete
historical dataset?

This distinction is essential for honest evaluation.

------------------------------------------------------------------------

# 82. Real-Time Evaluation vs Retrospective Dataset

If a missing observation is recovered 20 minutes later, it may be useful
for training.

But it was not available to a forecast made 20 minutes earlier.

Therefore evaluation must prevent retrospective recovered information
from leaking into simulated real-time predictions unless the recovery
would genuinely have completed before that prediction time.

------------------------------------------------------------------------

# 83. Zone-Level Context

GeoNex contains multiple devices per zone.

Therefore the system should support:

``` text
device-level state
sensor-level state
zone-level state
system-level state
```

C1 may use neighbour context.

C2 may use zone-wide silence patterns.

C3 may use multi-sensor/multi-device temporal features.

C4 may use expected device-zone relationships.

------------------------------------------------------------------------

# 84. Cross-Zone Information

Cross-zone information may eventually provide useful context, but it
should not be assumed automatically beneficial.

If used in ML:

-   spatial relationship must be defined;
-   temporal alignment must be correct;
-   leakage must be prevented;
-   research justification must be documented.

------------------------------------------------------------------------

# 85. Data Quality States

The architecture should support explicit quality states rather than only
value/null.

Examples may include:

``` text
OBSERVED
MISSING
ANOMALOUS
VALID_EVENT
RECOVERED
STALE
UNTRUSTED_SOURCE
INSUFFICIENT_CONTEXT
```

Exact enums will be frozen later.

------------------------------------------------------------------------

# 86. Confidence Is Context-Specific

Do not use one ambiguous field called:

``` text
confidence
```

for everything.

Different concepts may require:

``` text
trust_score
credibility_score
recovery_confidence
forecast_probability
```

These values have different meanings and may not be mathematically
comparable.

------------------------------------------------------------------------

# 87. Calibration of Probabilities

If a component outputs a probability used for decisions, model
calibration should be evaluated where appropriate.

For C3 in particular:

``` text
predicted 0.8 risk
```

should ideally have interpretable empirical meaning.

Calibration evaluation may include reliability analysis and suitable
calibration metrics/methods.

The exact technique will be selected during model development.

------------------------------------------------------------------------

# 88. Component Runtime Interfaces

Each component should expose a clean inference/service boundary.

Conceptually:

``` text
C4:
TelemetryContext → TrustAssessment

C1:
ObservationContext → CredibilityAssessment

C2:
Silence/FailureContext → DiagnosticRecoveryAssessment

C3:
TemporalWindow → Forecast
```

The exact API/message schemas will be specified later.

------------------------------------------------------------------------

# 89. Shared Core

The repository's shared layer should contain reusable definitions such
as:

``` text
enums
IDs
timestamps
schemas
configuration
logging
database access abstractions
common validation
feature definitions where genuinely shared
```

This prevents four incompatible implementations.

------------------------------------------------------------------------

# 90. Research Component Independence

Shared infrastructure does not mean the four research questions become
one model.

Each component must still retain:

-   its own dataset;
-   baseline;
-   candidate models;
-   evaluation;
-   metrics;
-   model artifact;
-   research results.

Integration occurs through contracts.

------------------------------------------------------------------------

# 91. Recommended Execution Placement

For the research demonstration:

### Embedded nodes

Best suited to:

-   sensing;
-   calibration/basic preprocessing;
-   packet construction;
-   local health monitoring;
-   command application;
-   local buffering where implemented.

### Main Black Box ESP32 gateway

Best suited to:

-   LoRa communication;
-   frame handling;
-   gateway forwarding;
-   alert/control I/O.

### Main computing host

Best suited to:

-   operational database;
-   C1--C4 higher-level inference;
-   Golden Timeline;
-   C3 temporal inference;
-   Decision Engine;
-   APIs;
-   dataset generation;
-   experiment/model management.

This keeps the initial implementation feasible while preserving an
edge-oriented field architecture.

------------------------------------------------------------------------

# 92. Edge AI Terminology

The project title includes Edge AI.

We must use this term carefully.

Running AI on the local Main Computing System at/near the monitored
field site can constitute edge-side processing relative to a remote
cloud architecture.

However, we should not claim that every AI model runs directly on each
ESP32 unless it actually does.

Deployment location must be stated precisely in reports.

------------------------------------------------------------------------

# 93. Internet/Cloud Independence

The core research demonstration should be capable of local sensing,
local field communication and local processing without requiring a cloud
round trip for every prediction.

Cloud services may later support:

-   remote dashboards;
-   external notifications;
-   backups;
-   centralized analytics;

but they should not silently become a mandatory dependency unless
explicitly designed and tested.

------------------------------------------------------------------------

# 94. Security Boundary

At minimum, architecture should distinguish:

``` text
untrusted external/field input
        ↓
gateway/ingestion validation
        ↓
C4 security/trust boundary
        ↓
trusted analytical processing
```

Database/API credentials and administrative interfaces must not be
exposed through field telemetry protocols.

------------------------------------------------------------------------

# 95. Schema Versioning

Telemetry and component contracts should contain schema-version
information.

This allows firmware/software to evolve without silently misinterpreting
old packets.

Conceptually:

``` text
schema_version = "1.0"
```

Breaking changes require explicit migration/version handling.

------------------------------------------------------------------------

# 96. Idempotency

A retransmitted packet should not create multiple logically identical
observations.

Therefore ingestion/database design must support idempotent handling
using suitable stable identifiers such as:

``` text
device_id
+
sequence number
+
packet identity
```

The exact key strategy will be frozen in the database specification.

------------------------------------------------------------------------

# 97. Audit Trail

Important decisions should be reconstructable.

For a warning, we should eventually be able to answer:

``` text
Which forecast triggered it?
Which model version produced the forecast?
Which Golden Timeline window was used?
Were any observations recovered?
What were C1/C4 states?
What mode existed before the decision?
Which rule changed the mode?
Was the command acknowledged?
```

This is essential for research defensibility.

------------------------------------------------------------------------

# 98. Performance Observability

The system should record performance indicators such as:

``` text
packet latency
processing latency
component inference time
database write time
forecast generation time
command round-trip time
packet loss
recovery duration
```

This allows us to answer whether the integrated architecture introduces
unacceptable delays.

------------------------------------------------------------------------

# 99. Hardware-in-the-Loop Architecture

Testing should eventually include:

``` text
physical sensor/node
      ↓
real LoRa
      ↓
real gateway
      ↓
real ingestion/database
      ↓
C4/C1/C2/C3
      ↓
Decision Engine
      ↓
real command
      ↓
physical node acknowledgement
```

This validates more than isolated ML accuracy.

------------------------------------------------------------------------

# 100. Simulation Path

Before every physical device is complete, a simulator may publish
contract-compliant telemetry.

``` text
Telemetry Simulator
      ↓
same ingestion contract
      ↓
same backend
```

The backend should not require a separate architecture for simulated
data.

Records must clearly identify simulation/synthetic origin.

------------------------------------------------------------------------

# 101. Development-Time Mocking

During concurrent development:

``` text
real C4 unavailable → mock C4 contract
real C1 unavailable → mock C1 contract
real C2 unavailable → mock C2 contract
```

C3 can still develop.

But mocks must never be confused with final experimental results.

------------------------------------------------------------------------

# 102. Integration Order

Recommended technical integration order:

``` text
1. shared schemas/IDs/config
2. database foundation
3. telemetry simulator
4. ingestion/raw persistence
5. C4 interface
6. C1 interface
7. silence monitor + C2 interface
8. Golden Timeline builder
9. C3 interface
10. Decision Engine
11. sampling/control commands
12. hardware gateway
13. real sensor nodes
14. full hardware-in-the-loop tests
```

Individual ML research can proceed concurrently after contracts are
defined.

------------------------------------------------------------------------

# 103. Architectural Separation of Concerns

The following responsibilities must not collapse into one script:

``` text
firmware
gateway
ingestion
database
C4
C1
C2
Golden Timeline
C3
Decision Engine
control service
dataset builder
training pipeline
```

They may initially run on one physical computer, but they remain logical
modules.

------------------------------------------------------------------------

# 104. Initial Deployment Does Not Require Microservices

Logical separation does not mean GeoNex must immediately deploy a
complex Kubernetes/microservice environment.

For a research prototype, a modular monorepo with clearly separated
Python services/modules can be more appropriate.

The architecture should support clean boundaries without unnecessary
operational complexity.

------------------------------------------------------------------------

# 105. Recommended Communication Pattern Inside the Main Host

The implementation may initially use:

-   direct service/module calls for simple synchronous operations;
-   database-backed/event-oriented processing where persistence is
    required;
-   background workers/queues where asynchronous work becomes necessary.

A message broker should only be introduced if its
reliability/concurrency benefits justify the added complexity.

This decision remains open until the concrete implementation plan.

------------------------------------------------------------------------

# 106. Latency-Critical C2 Behaviour

C2 should not force every healthy packet through expensive recovery
processing.

Healthy path:

``` text
packet arrives normally
      ↓
C4
      ↓
C1
      ↓
Golden Timeline
```

Exception path:

``` text
expected packet missing / explicit failure
      ↓
C2 diagnostic workflow
```

This is both conceptually cleaner and more efficient.

------------------------------------------------------------------------

# 107. C1 and C2 Interaction

C1 can also provide evidence useful to C2.

For example:

``` text
device still transmitting
but one sensor repeatedly produces anomalies
```

may indicate a sensor-specific problem rather than communication
silence.

Therefore C2 can consume relevant C1 history when diagnosing faults,
even though its primary trigger is silence/failure.

------------------------------------------------------------------------

# 108. C4 and C2 Interaction

C4 and C2 must cooperate around communication anomalies.

Example:

``` text
packets disappear
```

could mean:

-   communication failure;
-   power failure;
-   device failure;
-   wider physical damage.

Whereas:

``` text
unexpected duplicated/replayed packets
```

may be primarily a C4 security concern.

Shared telemetry metadata enables both components without conflating
their research questions.

------------------------------------------------------------------------

# 109. C4 and C1 Interaction

A trusted source can produce a bad measurement.

An untrusted source can produce a physically plausible value.

Therefore both assessments are needed.

The Golden Timeline policy should not automatically accept physically
plausible data from a source that failed mandatory C4 verification.

------------------------------------------------------------------------

# 110. C1 and C3 Interaction

C1 output provides data-quality context to C3.

Possible experimental strategies include:

``` text
exclude anomalous points
mask anomalous points
include credibility indicator
include credibility score
compare these approaches
```

The final strategy should be experimentally justified rather than
assumed.

------------------------------------------------------------------------

# 111. C2 and C3 Interaction

C2 affects C3 by determining:

-   whether a missing point remains missing;
-   whether a backup observation is available;
-   whether an estimate/fusion is justified;
-   the provenance/confidence of recovery.

C3 can then use recovery/missingness information explicitly.

------------------------------------------------------------------------

# 112. C3 and Sampling Feedback

The key closed loop is:

``` text
environment changes
      ↓
measurements
      ↓
C3 future-risk forecast
      ↓
Decision Engine
      ↓
mode changes
      ↓
sampling changes
      ↓
new temporal data pattern
      ↓
C3
```

This is why C3 is **mode-conditioned** and **variable-rate**.

The model must understand that the data-generation process itself
changes with system mode.

------------------------------------------------------------------------

# 113. Avoiding Feedback-Induced Bias

Because C3 affects sampling through the Decision Engine, high-risk
periods may contain many more observations than low-risk periods.

Training datasets must therefore avoid interpreting observation density
itself as an accidental shortcut for the target unless intentionally
modeled and justified.

Mode and `Δt` should explicitly represent the sampling context.

------------------------------------------------------------------------

# 114. Sampling Policy Must Be Recorded Historically

For every period, the system should know what sampling policy was
intended/applied.

Otherwise C2 cannot know whether a gap was abnormal and C3 cannot
correctly interpret variable observation density.

Historical mode/policy transitions must therefore be persisted.

------------------------------------------------------------------------

# 115. Calibration Metadata

Sensor calibration must be versionable.

Conceptually:

``` text
sensor_id
calibration_version
calibrated_at
conversion parameters
valid_from
valid_to
```

If calibration changes, historical raw values must not be silently
reinterpreted without traceability.

Concrete schema comes later.

------------------------------------------------------------------------

# 116. Sensor Replacement

A physical sensor may be replaced while a logical pipe remains the same.

Therefore:

``` text
device identity
```

and:

``` text
sensor-instance identity
```

should eventually be distinguishable.

This allows the system to know that a new soil-moisture probe was
installed in A1.

------------------------------------------------------------------------

# 117. Device Configuration History

Firmware version, configuration and assigned zone may change.

Historical inference should be able to identify which configuration was
active when an observation was produced.

This is relevant to C4, C2 and reproducibility.

------------------------------------------------------------------------

# 118. Research Ground Truth

AI training targets must not be confused with system predictions.

For example:

``` text
C3 prediction = HIGH
```

cannot later become ground truth merely because the model predicted
HIGH.

Ground-truth construction must use independently justified event/label
methodology.

The exact label methodology will be specified in the dataset/model
documents.

------------------------------------------------------------------------

# 119. External Data

If external rainfall/landslide datasets are used for model development,
they must be stored/registered with:

-   source;
-   license/usage conditions where relevant;
-   acquisition date/version;
-   transformations;
-   mapping to GeoNex features;
-   limitations.

External data must not be silently presented as GeoNex physical-demo
observations.

------------------------------------------------------------------------

# 120. Data Retention

The architecture should preserve research-critical raw and derived
evidence.

Retention policies may differ for:

``` text
raw telemetry
debug logs
model artifacts
datasets
audit events
```

Exact retention periods depend on available storage and research
requirements and are not frozen here.

------------------------------------------------------------------------

# 121. Backup and Recovery

The main computing system should have a backup strategy for
research-critical artifacts:

``` text
database backups
dataset versions
model artifacts
configuration
experiment metadata
documentation
```

A field node's microSD is not a substitute for server/database backup.

------------------------------------------------------------------------

# 122. Privacy Scope

GeoNex's core telemetry is environmental/device data.

If future alert systems store phone numbers, user accounts or
location-linked personal information, those data should be separated and
protected according to their sensitivity.

They should not be mixed unnecessarily into ML sensor datasets.

------------------------------------------------------------------------

# 123. Architecture Decision Records

Important decisions should be documented as architecture decision
records or equivalent documentation.

Examples:

``` text
Why PostgreSQL/TimescaleDB?
Why this packet protocol?
Why this C3 temporal representation?
Why these sampling modes?
Why this C2 recovery hierarchy?
```

This supports thesis and viva justification.

------------------------------------------------------------------------

# 124. Architecture Validation Questions

Before implementation begins, the team should be able to answer:

1.  What physical device produced this measurement?
2.  Which sensor instance produced it?
3.  When was it observed?
4.  When was it received?
5.  Which operating mode/policy was active?
6.  Was the packet trusted by C4?
7.  Was the measurement credible according to C1?
8.  Was anything missing?
9.  Did C2 recover or substitute anything?
10. What entered the Golden Timeline?
11. What temporal window did C3 use?
12. Which model version produced the forecast?
13. What did the Decision Engine decide?
14. Why did it decide that?
15. Was a control command sent?
16. Did the device acknowledge it?
17. Can the complete path be reconstructed later?

If the architecture cannot answer these questions, it is incomplete.

------------------------------------------------------------------------

# 125. Final End-to-End Runtime Story

A normal observation should conceptually behave as follows:

``` text
Physical condition changes
        ↓
Sensor produces electrical/digital reading
        ↓
ESP32 acquires and calibrates it
        ↓
Node attaches identity/time/mode/sequence metadata
        ↓
Compact telemetry packet is transmitted
        ↓
Main Black Box receives packet
        ↓
Gateway forwards it to main computing host
        ↓
Ingestion validates structure
        ↓
Raw telemetry is preserved
        ↓
C4 verifies source/transmission trust
        ↓
C1 evaluates measurement credibility
        ↓
If no failure exists, observation contributes to Golden Timeline
        ↓
C3 receives an updated temporal window
        ↓
C3 forecasts future risk
        ↓
Decision Engine combines prediction + system state
        ↓
Operating mode / warning / sampling decision is produced
        ↓
Control command is sent when required
        ↓
Field node applies new policy
        ↓
Acknowledgement and mode history are stored
        ↓
Future observations arrive at the new rate
```

------------------------------------------------------------------------

# 126. Final End-to-End Failure Story

A missing observation should conceptually behave as follows:

``` text
Sampling policy says A1 should report
        ↓
Expected deadline passes
        ↓
Silence Monitor creates missing-stream event
        ↓
C2 gathers primary/network/device context
        ↓
Backup Pipe is queried when appropriate
        ↓
Neighbour/hub evidence is examined
        ↓
C2 diagnoses likely cause
        ↓
Recovery action is selected
        ↓
Recovered/missing result retains provenance
        ↓
Golden Timeline is updated honestly
        ↓
C3 sees missing/recovered context
        ↓
Decision Engine receives risk + degraded-system information
        ↓
Appropriate mode/alert/recovery action follows
```

------------------------------------------------------------------------

# 127. Final Offline Research Story

``` text
Operational evidence accumulates
        ↓
Approved data sources selected
        ↓
Dataset builder extracts reproducible snapshot
        ↓
Source/provenance preserved
        ↓
Component-specific features and targets created
        ↓
Leakage checks performed
        ↓
Dataset version frozen
        ↓
Baseline and candidate models trained
        ↓
Evaluation/error analysis performed
        ↓
Research comparison produced
        ↓
Approved model artifact registered
        ↓
Controlled deployment
```

------------------------------------------------------------------------

# 128. Architecture Decisions Frozen by This Document

The following are now baseline architectural decisions:

1.  GeoNex is one integrated system with four research components.
2.  Two demonstration zones contain A, B and Backup sensing paths plus
    Centralized Sensor Hubs.
3.  The Centralized Power Hub is separate from the Centralized Sensor
    Hub.
4.  The Main Black Box gateway is logically separate from the main
    computing host.
5.  Sensors produce telemetry; they do not directly produce research CSV
    datasets.
6.  Raw telemetry is preserved.
7.  C4 handles source/transmission trust.
8.  C1 handles measurement credibility.
9.  C2 is primarily triggered by missing/silent/fault conditions rather
    than being an expensive mandatory stage for every healthy
    observation.
10. C2 recovery retains provenance.
11. The Golden Timeline is a curated forecasting representation, not a
    replacement for raw storage.
12. C3 consumes temporal history and must account for variable sampling
    and `Δt`.
13. C3 predictions do not directly command hardware.
14. A separate Decision Engine controls modes, alerts and sampling.
15. Sampling policy is mode-conditioned and historically recorded.
16. Telemetry and control form a closed loop.
17. Online runtime processing does not pass CSV files between
    components.
18. CSV/Parquet are primarily offline dataset artifacts.
19. Training and runtime inference are separate.
20. Synthetic, physical, external, recovered and derived data retain
    provenance.
21. Component development uses shared contracts.
22. The initial prototype may remain a modular deployment rather than
    introducing unnecessary microservice complexity.
23. End-to-end latency and system degradation must be measurable.
24. Retrospectively recovered data must not be allowed to create false
    real-time evaluation results.

------------------------------------------------------------------------

# 129. Decisions Intentionally Not Frozen Yet

The following remain for later dedicated specifications:

-   exact SQL tables and indexes;
-   final operational database technology confirmation;
-   exact packet byte format;
-   exact security/cryptographic protocol;
-   exact sampling intervals for each mode;
-   exact mode transition thresholds;
-   exact alert thresholds;
-   exact C1 label/output schema;
-   harmonized C2 failure/recovery taxonomy;
-   exact C3 forecast horizons;
-   final C3 architecture;
-   final C4 behavioural model;
-   exact feature sets;
-   exact APIs/message schemas;
-   exact queue/broker choice if any;
-   final calibration equations;
-   final ground-truth construction methodology.

These should not be silently invented during component implementation.

------------------------------------------------------------------------

# 130. Required Next Design Documents

The architecture now needs to be converted into implementation
contracts.

Recommended sequence:

``` text
00_GEONEX_SYSTEM_DEVELOPMENT_PLAN.md
        ↓
01_GEONEX_END_TO_END_ARCHITECTURE.md
        ↓
02_GEONEX_DATA_DATABASE_ARCHITECTURE.md
        ↓
03_GEONEX_DATASET_ARCHITECTURE.md
        ↓
04_GEONEX_MODE_SAMPLING_SPECIFICATION.md
        ↓
05_GEONEX_AI_ML_ARCHITECTURE.md
        ↓
06_GEONEX_SHARED_CONTRACTS.md
        ↓
07_GEONEX_REPOSITORY_ARCHITECTURE.md
        ↓
C1/C2/C3/C4 MEMBER DEVELOPMENT GUIDES
        ↓
INTEGRATION / TEST / DEPLOYMENT GUIDES
```

The numbering may be adjusted if the team later separates a topic into
multiple documents, but dependencies must remain clear.

------------------------------------------------------------------------

# Document 01 Status

**`01_GEONEX_END_TO_END_ARCHITECTURE.md` --- ARCHITECTURE BASELINE
READY**

This document establishes the end-to-end GeoNex architecture from
physical sensing to telemetry, trust, credibility, recovery, Golden
Timeline construction, temporal forecasting, decision making, adaptive
sampling, offline research and deployment boundaries.

The next document should turn these architectural entities into a
concrete, normalized and time-series-aware data design:

**`02_GEONEX_DATA_DATABASE_ARCHITECTURE.md`**

That document should define the final logical database architecture,
table responsibilities, keys, relationships, raw-vs-derived storage,
telemetry schema, Golden Timeline representation, component outputs,
mode history, commands, model/dataset metadata, retention/provenance
strategy and example records before SQL migrations are written.
