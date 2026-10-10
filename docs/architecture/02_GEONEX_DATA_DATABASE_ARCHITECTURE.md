# 02_GEONEX_DATA_DATABASE_ARCHITECTURE.md

**Project:** GeoNex --- Smart Landslide Early Warning Prediction System
using IoT, Edge AI and Risk Analytics\
**Document:** Data & Database Architecture\
**Status:** Data Architecture Baseline\
**Depends on:** `00_GEONEX_SYSTEM_DEVELOPMENT_PLAN.md`,
`01_GEONEX_END_TO_END_ARCHITECTURE.md`\
**Purpose:** Define the shared operational data architecture, database
entities, identifiers, timestamps, provenance, C1--C4 result storage,
Golden Timeline representation, control/audit data, and the boundary
between the live database and offline ML datasets.

------------------------------------------------------------------------

# 1. Why This Document Exists

GeoNex cannot be developed safely if each component creates its own
interpretation of the data.

Without a shared data architecture, the project could become:

``` text
C1 → one CSV format
C2 → another CSV format
C3 → unrelated temporal file
C4 → separate JSON structure
Firmware → different names
Database → different names again
```

That would make integration difficult and research results difficult to
reproduce.

This document therefore defines a single logical data architecture for
all four components.

The core principle is:

> **One preserved operational evidence base, multiple component-specific
> analytical views and datasets.**

------------------------------------------------------------------------

# 2. Database and Dataset Are Different

This distinction is mandatory.

## Operational Database

The operational database supports the running GeoNex system.

It stores information such as:

-   registered devices and sensors;
-   incoming packets;
-   observations;
-   C4 trust assessments;
-   C1 credibility assessments;
-   C2 silence/diagnostic/recovery events;
-   Golden Timeline records;
-   C3 forecasts;
-   decisions;
-   operating modes;
-   sampling policies;
-   commands and acknowledgements;
-   alerts;
-   model metadata;
-   dataset metadata;
-   calibration/configuration history.

## ML Dataset

An ML dataset is a controlled, versioned research artifact derived from
approved sources.

It may be exported as:

``` text
Parquet
CSV
```

and used for:

-   training;
-   validation;
-   testing;
-   ablation studies;
-   reproducibility;
-   sharing controlled data between team members.

Therefore:

``` text
LIVE SYSTEM
Sensors
   ↓
Telemetry
   ↓
Operational Database
```

is different from:

``` text
RESEARCH / TRAINING
Operational DB + approved sources
            ↓
Dataset Builder
            ↓
Versioned Dataset
            ↓
Parquet / CSV
            ↓
Training / Evaluation
```

------------------------------------------------------------------------

# 3. Recommended Operational Database Technology

The recommended baseline is:

``` text
PostgreSQL
+
TimescaleDB
```

PostgreSQL provides:

-   relational integrity;
-   transactions;
-   mature indexing;
-   constraints;
-   JSON support where justified;
-   strong Python ecosystem support.

TimescaleDB extends PostgreSQL for time-series workloads such as:

-   timestamped telemetry;
-   time-window queries;
-   time-based partitioning/chunking;
-   continuous/time-window analytics where useful.

This architecture does not require every table to be a Timescale
hypertable.

Configuration/reference tables remain conventional relational tables.

High-volume temporal tables are the main candidates for time-series
optimization.

------------------------------------------------------------------------

# 4. Why a Relational + Time-Series Design Fits GeoNex

GeoNex contains both relational and temporal information.

Relational examples:

``` text
zone → devices
device → sensor instances
sensor instance → calibration
model → model versions
command → acknowledgement
```

Temporal examples:

``` text
sensor observations
packet arrivals
mode changes
C3 forecasts
alerts
device-health observations
```

A relational/time-series architecture therefore avoids maintaining
unrelated database technologies without a demonstrated need.

------------------------------------------------------------------------

# 5. Main Logical Data Layers

The operational database is divided conceptually into:

``` text
L0 — Reference / Configuration
L1 — Raw Ingestion Evidence
L2 — Normalized Observations
L3 — Component Assessments
L4 — Golden Timeline
L5 — Forecast / Decision / Control
L6 — ML / Dataset / Model Metadata
L7 — Audit / Operational Metadata
```

These are logical layers.

They do not necessarily require seven separate physical databases.

------------------------------------------------------------------------

# 6. High-Level Entity Flow

``` text
zones
  ↓
devices
  ↓
sensor_instances
  ↓
telemetry_packets
  ↓
sensor_observations
  │
  ├────────────→ c4_trust_assessments
  │
  ├────────────→ c1_credibility_assessments
  │
  └────────────→ C2 monitoring context
                         ↓
                    silence_events
                         ↓
                   c2_diagnoses
                         ↓
                   recovery_events
                         ↓
              golden_observations
                         ↓
                   c3_forecasts
                         ↓
                    decisions
                         ↓
              mode / command / alert
```

The exact runtime execution remains as defined in Document 01: C4 source
trust precedes acceptance into trusted analytical processing; C2 is
primarily exception/event-driven.

------------------------------------------------------------------------

# 7. Naming Conventions

Database naming should be predictable.

Recommended rules:

-   lowercase;
-   `snake_case`;
-   plural table names;
-   singular descriptive column names;
-   `_id` suffix for identifiers;
-   `_at` suffix for timestamps;
-   `_pct` for percentages where the stored unit is percent;
-   `_v`, `_a`, `_w`, `_c`, etc. only when the engineering unit is
    explicit and stable.

Examples:

``` text
device_id
sensor_instance_id
observed_at
received_at
soil_moisture_pct
bus_voltage_v
```

Avoid ambiguous names such as:

``` text
value1
data
status2
time
reading_x
```

------------------------------------------------------------------------

# 8. Identifier Strategy

GeoNex needs both machine identifiers and human-readable codes.

Recommended pattern:

``` text
internal primary key
+
stable public/logical code
```

Example:

``` text
zone_id       = UUID/internal ID
zone_code     = Z01

device_id     = UUID/internal ID
device_code   = Z01-A01
```

This prevents database relationships from depending entirely on editable
display names.

UUIDs are a suitable candidate for distributed logical identifiers.

The concrete SQL type is frozen in the implementation migration
specification.

------------------------------------------------------------------------

# 9. Core Identifiers

The architecture must support at least:

``` text
zone_id
device_id
sensor_instance_id
packet_id
observation_id
silence_event_id
recovery_event_id
forecast_id
decision_id
command_id
alert_id
model_id
model_version_id
dataset_id
dataset_version_id
```

Each identifier represents a different entity and must not be reused
ambiguously.

------------------------------------------------------------------------

# 10. Timestamp Policy

Time is fundamental to GeoNex.

The database must distinguish at least:

``` text
observed_at
received_at
processed_at
```

## `observed_at`

When the sensor/device says the observation occurred.

## `received_at`

When the main computing system received/accepted the telemetry event
into ingestion.

## `processed_at`

When a particular analytical component produced its result.

For database storage, timezone-aware timestamps should be used.

Recommended implementation:

``` text
PostgreSQL TIMESTAMPTZ
```

The backend should normalize stored timestamps consistently, preferably
UTC internally, while presentation layers can render Sri Lanka/local
time as required.

------------------------------------------------------------------------

# 11. Why Multiple Timestamps Matter

Example:

``` text
observed_at = 04:30:00 UTC
received_at = 04:30:02 UTC
```

means approximately two seconds elapsed between observation and server
receipt.

But after an SD replay:

``` text
observed_at = 04:30:00 UTC
received_at = 04:50:00 UTC
```

The observation happened at 04:30 even though the server only received
it at 04:50.

If the system stored only one timestamp, this distinction would
disappear.

------------------------------------------------------------------------

# 12. Time Synchronization Quality

Embedded clocks may drift or temporarily lack a reliable RTC reference.

Therefore observation timing should support quality/context metadata
where needed.

Conceptually:

``` text
timestamp_source
clock_sync_status
clock_offset_estimate_ms
```

These fields are optional until the firmware time-synchronization
mechanism is finalized, but the architecture must not assume every
device timestamp is perfect.

------------------------------------------------------------------------

# 13. Data-Origin / Provenance Taxonomy

Every research-relevant value must be traceable to origin.

Baseline provenance concepts:

``` text
PHYSICAL_DEMO
SYNTHETIC
EXTERNAL
RECOVERED
DERIVED
SIMULATED
```

These concepts may be represented through source fields and lineage
records rather than one field alone.

A synthetic record must never silently appear as a physical observation.

------------------------------------------------------------------------

# 14. Core Reference Table --- `zones`

Purpose:

Represent monitored geographical/logical zones.

Recommended fields:

  Field           Meaning
  --------------- ------------------------------------------
  `zone_id`       Internal primary identifier
  `zone_code`     Stable human-readable code such as `Z01`
  `name`          Optional descriptive name
  `description`   Zone description
  `is_active`     Whether zone is operational
  `created_at`    Record creation time
  `updated_at`    Last metadata update

For the demonstration:

``` text
Z01
Z02
```

No precise real-world coordinates are required merely to represent the
prototype zones.

------------------------------------------------------------------------

# 15. Core Reference Table --- `devices`

Purpose:

Represent physical processing/communication devices.

Examples:

``` text
A1 pipe controller
B1 pipe controller
BK1 backup controller
Hub 1
Main Black Box gateway
```

Recommended fields:

  Field                Meaning
  -------------------- --------------------------------------------------
  `device_id`          Primary identifier
  `device_code`        Stable code
  `zone_id`            Assigned zone, nullable for system-level devices
  `device_type`        TYPE_A, TYPE_B, BACKUP, SENSOR_HUB, GATEWAY
  `hardware_model`     ESP32-S3, ESP32-C3, etc.
  `firmware_version`   Current firmware version
  `is_active`          Operational registration state
  `installed_at`       Installation/commission time
  `retired_at`         Retirement time if applicable
  `created_at`         Metadata creation
  `updated_at`         Metadata update

The Main Computing System itself may be represented separately as
infrastructure rather than pretending it is a sensor node.

------------------------------------------------------------------------

# 16. Device-Type Enumeration

Baseline conceptual values:

``` text
TYPE_A
TYPE_B
BACKUP
SENSOR_HUB
GATEWAY
```

The Centralized Power Hub should not automatically be inserted as a
sensing device unless telemetry is actually digitized and ingested from
it.

A local panel display alone is not operational telemetry.

------------------------------------------------------------------------

# 17. Core Reference Table --- `sensor_definitions`

Purpose:

Define sensor/channel types independently of individual physical
installations.

Examples:

``` text
SOIL_MOISTURE
FSR
ACCELEROMETER
GYROSCOPE
MAGNETOMETER
AIR_TEMPERATURE
RELATIVE_HUMIDITY
DS18B20_TEMPERATURE
RAINFALL
BAROMETRIC_PRESSURE
BUS_VOLTAGE
CURRENT
```

Recommended fields:

  Field                    Meaning
  ------------------------ --------------------------------------------
  `sensor_definition_id`   Primary identifier
  `sensor_type_code`       Stable type code
  `measurement_family`     Environmental, motion, device-health, etc.
  `default_unit`           Expected engineering unit where applicable
  `description`            Meaning
  `is_environmental`       Environmental/ground measurement flag
  `is_device_health`       Device-health flag

------------------------------------------------------------------------

# 18. Core Reference Table --- `sensor_instances`

Purpose:

Represent the actual physical sensor/channel installed on a particular
device.

Example:

``` text
A1 soil moisture probe 1
A1 soil moisture probe 2
A1 FSR 1
```

Recommended fields:

  Field                    Meaning
  ------------------------ --------------------------------------------------
  `sensor_instance_id`     Primary identifier
  `device_id`              Parent device
  `sensor_definition_id`   Sensor/channel type
  `sensor_code`            Stable local code
  `channel_index`          Channel number where useful
  `hardware_model`         MPU9250, FSR402, etc.
  `installed_at`           Installation time
  `removed_at`             Removal/replacement time
  `is_active`              Current state
  `metadata`               Limited structured hardware metadata if required

This permits a sensor to be replaced without changing the logical
identity of the entire pipe.

------------------------------------------------------------------------

# 19. Sensor Definition vs Sensor Instance

Example:

``` text
sensor_definition:
SOIL_MOISTURE
```

versus:

``` text
sensor_instance:
Z01-A01-SM01
```

The first means "what kind of measurement is this?"

The second means "which actual probe produced it?"

Both are needed for calibration and provenance.

------------------------------------------------------------------------

# 20. Calibration Table --- `sensor_calibrations`

Purpose:

Version calibration/conversion rules.

Recommended fields:

  Field                   Meaning
  ----------------------- ----------------------------------
  `calibration_id`        Primary identifier
  `sensor_instance_id`    Physical sensor
  `calibration_version`   Version
  `valid_from`            Start of applicability
  `valid_to`              End of applicability
  `method`                Calibration method/reference
  `parameters`            Structured conversion parameters
  `unit_out`              Engineering output unit
  `created_at`            Record creation

The original raw measurement should remain available even after
calibrated values are produced.

------------------------------------------------------------------------

# 21. Raw Packet Table --- `telemetry_packets`

Purpose:

Preserve one record per received field packet/frame after minimal
structural decoding.

Recommended fields:

  -----------------------------------------------------------------------
  Field                               Meaning
  ----------------------------------- -----------------------------------
  `packet_id`                         Primary packet identifier

  `device_id`                         Claimed/resolved sender

  `zone_id`                           Associated zone

  `schema_version`                    Telemetry contract version

  `sequence_no`                       Device sequence number

  `observed_at`                       Packet/device observation time

  `received_at`                       Main-host receipt time

  `gateway_device_id`                 Gateway that received it

  `operating_mode`                    Mode reported by sender

  `payload_raw`                       Preserved raw/decoded payload
                                      representation

  `payload_hash`                      Integrity/audit hash where
                                      implemented

  `rssi_dbm`                          Radio metadata if available

  `snr_db`                            Radio metadata if available

  `ingestion_status`                  Accepted structurally, malformed,
                                      duplicate, etc.

  `source_origin`                     PHYSICAL_DEMO, SIMULATED, etc.

  `created_at`                        DB insertion time
  -----------------------------------------------------------------------

Exact cryptographic fields will be finalized with C4.

------------------------------------------------------------------------

# 22. Why Store Packets Separately From Observations

One packet may contain:

``` text
soil moisture 1
soil moisture 2
FSR
temperature
humidity
voltage
```

Therefore:

``` text
1 packet
   ↓
many observations
```

Packet-level metadata such as RSSI and sequence number should not need
to be duplicated conceptually as independent sensor readings.

------------------------------------------------------------------------

# 23. Raw Payload Preservation

`payload_raw` exists for audit/reprocessing.

Implementation choices may include:

``` text
JSONB decoded representation
+
optional original binary/frame bytes where practical
```

The database must not rely only on the raw payload for normal analytical
queries.

Important measurements are normalized into observation records.

------------------------------------------------------------------------

# 24. Observation Table --- `sensor_observations`

Purpose:

Store normalized sensor/channel observations.

Recommended fields:

  Field                  Meaning
  ---------------------- ----------------------------------------------
  `observation_id`       Primary identifier
  `packet_id`            Parent packet
  `zone_id`              Zone
  `device_id`            Device
  `sensor_instance_id`   Actual sensor/channel
  `observed_at`          Measurement time
  `received_at`          Server receipt time
  `raw_value`            Raw sensor/ADC value when meaningful
  `calibrated_value`     Engineering value
  `unit`                 Engineering unit
  `calibration_id`       Calibration version used
  `quality_flag`         Acquisition-level quality state
  `source_origin`        Physical/simulated/external where applicable
  `created_at`           Persistence time

This is a high-volume time-series table and is a strong candidate for
TimescaleDB hypertable treatment.

------------------------------------------------------------------------

# 25. Raw vs Calibrated Value

Example:

``` text
raw_value        = 2431
calibrated_value = 67.4
unit             = %
```

This allows future calibration improvements without pretending the raw
ADC reading never existed.

Not every digital sensor requires a meaningful ADC-style raw value.

For direct digital measurements, `raw_value` may represent the
device-reported numeric reading or be nullable according to the channel
contract.

------------------------------------------------------------------------

# 26. Measurement Units

Units must be explicit and standardized.

Examples:

``` text
%
°C
hPa
V
A
W
m/s²
deg/s
```

Do not mix:

``` text
0.67
```

and:

``` text
67
```

for soil moisture without documenting whether the unit is fraction or
percent.

Unit semantics belong in the sensor/channel definition and dataset
specification.

------------------------------------------------------------------------

# 27. Vector Sensors

An IMU produces multiple axes.

Two acceptable logical strategies are:

1.  individual channel definitions, such as `ACCEL_X`, `ACCEL_Y`,
    `ACCEL_Z`; or
2.  a structured vector observation.

For GeoNex's SQL/ML integration, explicit scalar channels are generally
easier to query and feature-engineer.

Therefore the recommended baseline is separate scalar channel
definitions, with derived magnitude/orientation stored separately.

------------------------------------------------------------------------

# 28. Derived Measurements Table --- `derived_observations`

Purpose:

Store values computed from one or more original observations where
persistence is useful.

Examples:

``` text
tilt_deg
vibration_rms
rain_15m_sum
rain_1h_sum
soil_moisture_mean
soil_moisture_trend_30m
```

Recommended fields:

  Field                      Meaning
  -------------------------- --------------------------------------------
  `derived_observation_id`   Primary identifier
  `zone_id`                  Zone
  `device_id`                Device where applicable
  `feature_code`             Derived measurement code
  `window_start`             Input window start if applicable
  `window_end`               Input window end
  `observed_at`              Effective feature timestamp
  `value`                    Derived numeric value
  `unit`                     Unit
  `derivation_version`       Feature/algorithm version
  `source_lineage`           Reference/metadata for source observations
  `created_at`               Creation time

Not every runtime feature needs permanent persistence. Persist derived
values when needed for audit, reuse or reproducibility.

------------------------------------------------------------------------

# 29. Device-Health Observations

Device-health telemetry can use the same normalized observation
architecture when it represents numeric channels.

Examples:

``` text
bus_voltage_v
current_a
power_w
battery_voltage_v
```

Other state/event information may belong in a device-event table.

Environmental and health channels remain distinguishable through
`measurement_family`.

------------------------------------------------------------------------

# 30. Device Event Table --- `device_events`

Purpose:

Store discrete device/system events.

Examples:

``` text
BOOT
RESTART
SENSOR_READ_FAILURE
SD_WRITE_FAILURE
LOW_POWER
FIRMWARE_ERROR
MODE_APPLIED
```

Recommended fields:

  Field               Meaning
  ------------------- --------------------------------------------
  `device_event_id`   Primary identifier
  `device_id`         Device
  `event_type`        Event code
  `severity`          Informational/warning/error classification
  `occurred_at`       Device/event time
  `received_at`       Server receipt
  `details`           Structured event metadata
  `created_at`        DB creation

------------------------------------------------------------------------

# 31. C4 Table --- `c4_trust_assessments`

Purpose:

Store C4's assessment of packet/source trust.

Recommended fields:

  Field                             Meaning
  --------------------------------- ---------------------------------------------------
  `c4_assessment_id`                Primary identifier
  `packet_id`                       Packet assessed
  `device_id`                       Sender
  `mandatory_verification_passed`   Deterministic gate
  `identity_valid`                  Identity result where implemented
  `integrity_valid`                 Integrity result where implemented
  `freshness_valid`                 Freshness result
  `replay_suspected`                Replay indication
  `behavioural_score`               ML anomaly/trust score if used
  `trust_class`                     TRUSTED/SUSPICIOUS/UNTRUSTED or frozen equivalent
  `trust_score`                     Defined C4 score if supported
  `model_version_id`                ML model version if ML used
  `ruleset_version`                 Deterministic security rules version
  `processed_at`                    Assessment time
  `details`                         Explainability/reason codes

A failed mandatory cryptographic/security gate cannot be overridden by a
favourable ML score.

------------------------------------------------------------------------

# 32. C4 Reason Codes

C4 should provide machine-readable reasons.

Conceptual examples:

``` text
IDENTITY_UNKNOWN
SIGNATURE_INVALID
COUNTER_REUSED
PACKET_STALE
BEHAVIOURAL_ANOMALY
RADIO_PATTERN_ANOMALY
VERIFIED
```

Exact codes will be frozen in the C4 contract.

Reason codes are preferable to only storing:

``` text
trust_score = 0.2
```

because they improve auditability.

------------------------------------------------------------------------

# 33. Quarantine Representation

A packet that fails C4 remains in `telemetry_packets`.

It may additionally receive:

``` text
trust_class = UNTRUSTED
mandatory_verification_passed = false
```

Downstream trusted views exclude it according to policy.

The raw evidence is not deleted.

------------------------------------------------------------------------

# 34. C1 Table --- `c1_credibility_assessments`

Purpose:

Store measurement-level credibility assessment.

Recommended fields:

  Field                      Meaning
  -------------------------- ------------------------------------------------
  `c1_assessment_id`         Primary identifier
  `observation_id`           Observation assessed
  `credibility_class`        CLEAN/ANOMALY/VALID_EVENT or frozen equivalent
  `credibility_score`        Confidence/score with documented semantics
  `rainfall_context_code`    Regime/context where used
  `neighbour_context_used`   Whether neighbour evidence was available
  `model_version_id`         C1 model
  `feature_schema_version`   Feature contract
  `processed_at`             Assessment time
  `reason_codes`             Explainability/context codes

C1 does not overwrite `sensor_observations.calibrated_value`.

------------------------------------------------------------------------

# 35. C1 Granularity

C1 primarily assesses measurements/observations.

Therefore its natural foreign key is:

``` text
observation_id
```

not only `packet_id`.

One packet can contain one credible sensor value and another problematic
sensor value.

------------------------------------------------------------------------

# 36. Silence Monitoring Table --- `expected_observations`

Purpose:

Represent expected reporting deadlines derived from the currently
applied sampling/transmission policy.

Recommended conceptual fields:

  Field                      Meaning
  -------------------------- ---------------------------------------
  `expectation_id`           Primary identifier
  `device_id`                Expected device
  `policy_id`                Policy generating expectation
  `expected_at`              Expected arrival/observation time
  `deadline_at`              Expected time plus tolerance
  `status`                   PENDING, SATISFIED, MISSED, CANCELLED
  `satisfied_by_packet_id`   Packet satisfying expectation
  `created_at`               Creation

Implementation may optimize this rather than materializing every future
expectation row.

The logical requirement is that C2 can determine what was expected under
the active mode.

------------------------------------------------------------------------

# 37. C2 Table --- `silence_events`

Purpose:

Record abnormal expected-stream gaps.

Recommended fields:

  Field                  Meaning
  ---------------------- ------------------------------------
  `silence_event_id`     Primary identifier
  `zone_id`              Zone
  `device_id`            Silent device
  `sensor_instance_id`   Optional sensor-specific silence
  `expected_at`          Expected time
  `deadline_at`          Miss threshold
  `detected_at`          Silence detection time
  `mode_at_detection`    Applied operating mode
  `policy_id`            Active policy
  `last_packet_id`       Last known packet
  `status`               OPEN/DIAGNOSED/RECOVERED/ESCALATED
  `created_at`           Persistence time

------------------------------------------------------------------------

# 38. C2 Table --- `c2_diagnoses`

Purpose:

Store diagnostic classification for a silence/failure event.

Recommended fields:

  Field                   Meaning
  ----------------------- -----------------------------------------
  `c2_diagnosis_id`       Primary identifier
  `silence_event_id`      Trigger
  `failure_class`         Diagnosed class
  `failure_probability`   Model probability/confidence if defined
  `backup_checked`        Whether backup verification occurred
  `backup_status`         Result
  `model_version_id`      C2 model
  `ruleset_version`       Hybrid rule version
  `processed_at`          Diagnosis time
  `reason_codes`          Diagnostic evidence

The exact failure taxonomy will be frozen in the C2 component
specification.

------------------------------------------------------------------------

# 39. C2 Table --- `recovery_events`

Purpose:

Store recovery attempts/actions and their outcomes.

Recommended fields:

  Field                   Meaning
  ----------------------- --------------------------------------------------
  `recovery_event_id`     Primary identifier
  `silence_event_id`      Original failure
  `c2_diagnosis_id`       Diagnosis
  `recovery_action`       SD replay, backup sensor, neighbour fusion, etc.
  `requested_at`          Recovery request time
  `completed_at`          Completion time
  `recovery_status`       SUCCESS/FAILED/PARTIAL/etc.
  `recovery_confidence`   Confidence where applicable
  `source_device_id`      Backup/source device if applicable
  `ruleset_version`       Recovery policy
  `details`               Additional provenance

Recovery action and failure diagnosis are deliberately stored
separately.

------------------------------------------------------------------------

# 40. Recovered Values

If recovery produces a value usable by C3, that value must be stored
without pretending it was a direct original measurement.

Two linked concepts are required:

``` text
recovery event
+
recovered observation/value
```

A dedicated table is recommended.

------------------------------------------------------------------------

# 41. Table --- `recovered_observations`

Recommended fields:

  Field                         Meaning
  ----------------------------- -------------------------------------------------
  `recovered_observation_id`    Primary identifier
  `recovery_event_id`           Recovery process
  `target_sensor_instance_id`   Missing logical target
  `effective_observed_at`       Time represented
  `value`                       Recovered value
  `unit`                        Unit
  `recovery_method`             BACKUP_SENSOR, SD_REPLAY, NEIGHBOR_FUSION, etc.
  `source_observation_id`       Direct source if one exists
  `source_device_id`            Source device
  `recovery_confidence`         Confidence
  `created_at`                  Creation

For SD replay, the replayed value may also be a late-arriving original
observation. The implementation must distinguish "late original" from
"estimated/fused substitute".

------------------------------------------------------------------------

# 42. Late Original vs Estimated Recovery

These are scientifically different.

## Late Original

Example:

``` text
A1 measured 67.2 at 10:10
network failed
A1 stored it locally
SD replay sends the actual 10:10 reading later
```

This is still an original A1 observation received late.

## Estimated / Substitute

Example:

``` text
A1 10:10 value missing
BK1/neighbour fusion estimates 66.4
```

This is recovered/derived information.

The database must not collapse both into the same provenance category.

------------------------------------------------------------------------

# 43. Golden Timeline Design

The Golden Timeline is the curated temporal layer used to construct C3
input windows.

It should not duplicate all raw data blindly.

A recommended implementation is a persisted table or materialized
analytical layer called:

``` text
golden_observations
```

Its exact implementation can combine stored rows with views, but its
contract must be stable.

------------------------------------------------------------------------

# 44. Table --- `golden_observations`

Recommended fields:

  Field                         Meaning
  ----------------------------- -----------------------------------------------------
  `golden_observation_id`       Primary identifier
  `zone_id`                     Zone
  `logical_feature_code`        Forecasting channel/feature
  `target_sensor_instance_id`   Logical source where applicable
  `effective_at`                Temporal position
  `value`                       Selected usable value
  `unit`                        Unit
  `value_origin`                DIRECT, LATE_ORIGINAL, BACKUP, FUSED, DERIVED, etc.
  `source_observation_id`       Original source if direct
  `recovered_observation_id`    Recovery source if applicable
  `c4_assessment_id`            Relevant trust assessment
  `c1_assessment_id`            Relevant credibility assessment
  `trust_state`                 Snapshot used by builder
  `credibility_state`           Snapshot used by builder
  `recovered`                   Boolean
  `recovery_confidence`         If recovered
  `golden_policy_version`       Builder policy version
  `created_at`                  Creation

The Golden Timeline must remain traceable to underlying evidence.

------------------------------------------------------------------------

# 45. Golden Timeline Is Policy-Driven

Not every raw observation automatically becomes Golden data.

Conceptually:

``` text
raw observation
      ↓
C4 acceptable?
      ↓
C1 usable?
      ↓
direct/recovery evidence available?
      ↓
Golden Builder Policy
      ↓
golden_observation
```

The policy itself must be versioned.

This allows future experiments to compare different handling strategies.

------------------------------------------------------------------------

# 46. Do Not Overwrite Golden History Silently

If a late observation arrives after a recovered estimate was used, the
system may need both:

``` text
what was available in real time
```

and:

``` text
best retrospective reconstruction
```

Therefore a future implementation may expose two analytical views:

``` text
as_of_runtime
retrospective_best
```

At minimum, replacement/supersession must be traceable rather than
silently updating history.

------------------------------------------------------------------------

# 47. Operating Mode Table --- `operating_mode_events`

Purpose:

Record mode history.

Recommended fields:

  Field             Meaning
  ----------------- -------------------------------------
  `mode_event_id`   Primary identifier
  `scope_type`      SYSTEM, ZONE, DEVICE as implemented
  `scope_id`        Target scope
  `previous_mode`   Prior mode
  `new_mode`        New mode
  `reason_code`     Why transition occurred
  `decision_id`     Decision causing transition
  `requested_at`    Requested time
  `applied_at`      Confirmed application time
  `created_at`      DB time

This historical record is necessary for C2 and C3.

------------------------------------------------------------------------

# 48. Sampling Policy Table --- `sampling_policies`

Purpose:

Define reusable sampling/transmission profiles.

Recommended fields:

  ----------------------------------------------------------------------------
  Field                               Meaning
  ----------------------------------- ----------------------------------------
  `policy_id`                         Primary identifier

  `policy_code`                       Stable name/version

  `mode`                              DEEP_SLEEP/IDLE/RISK/WARNING/EMERGENCY

  `device_type`                       Applicable type

  `sampling_interval_ms`              Sensor acquisition interval where
                                      applicable

  `transmission_interval_ms`          Packet/report interval

  `aggregation_policy`                Optional local aggregation

  `tolerance_ms`                      Reporting grace/tolerance

  `version`                           Policy version

  `is_active`                         Current approved policy
  ----------------------------------------------------------------------------

Exact interval values are deliberately not defined here.

------------------------------------------------------------------------

# 49. Why Sampling Policy Is Stored

C2 must know:

``` text
Was the device actually expected to report now?
```

C3 must know:

``` text
Why did observation density change?
```

Therefore sampling policy cannot exist only as constants hidden in
firmware.

------------------------------------------------------------------------

# 50. Applied Policy Table --- `device_policy_assignments`

Purpose:

Track which policy was commanded/applied to a device.

Recommended fields:

  Field             Meaning
  ----------------- -------------------------------------
  `assignment_id`   Primary identifier
  `device_id`       Device
  `policy_id`       Sampling policy
  `desired_from`    Requested start
  `applied_from`    Device-confirmed start
  `ended_at`        End
  `command_id`      Command that caused assignment
  `status`          REQUESTED/APPLIED/FAILED/SUPERSEDED
  `created_at`      Creation

This distinguishes desired mode from confirmed device behaviour.

------------------------------------------------------------------------

# 51. C3 Forecast Table --- `c3_forecasts`

Purpose:

Store runtime forecasting outputs.

Recommended fields:

  Field                      Meaning
  -------------------------- ----------------------------------------------
  `forecast_id`              Primary identifier
  `zone_id`                  Forecasted zone
  `forecast_generated_at`    Inference time
  `window_start`             Input history start
  `window_end`               Input history end
  `horizon_minutes`          Future horizon
  `risk_probability`         Forecast probability
  `risk_class`               LOW/WATCH/HIGH/CRITICAL or frozen equivalent
  `time_to_danger_minutes`   Optional model output
  `input_quality_status`     Input sufficiency/degraded status
  `model_version_id`         C3 model
  `feature_schema_version`   C3 feature contract
  `golden_policy_version`    Golden builder policy
  `created_at`               Persistence

Exact output fields depend on the final experimentally justified C3
model.

------------------------------------------------------------------------

# 52. C3 Input Snapshot / Lineage

A forecast should be reproducible.

At minimum, the system must be able to determine which Golden Timeline
range/version generated it.

Possible mechanisms:

-   `window_start` + `window_end` + zone + policy/model versions;
-   an immutable feature-window identifier;
-   a dedicated forecast-input manifest.

For rigorous experiments, a dedicated input manifest is recommended.

------------------------------------------------------------------------

# 53. Table --- `forecast_input_manifests`

Purpose:

Record the exact feature-window identity used by C3.

Recommended fields:

  Field                      Meaning
  -------------------------- ---------------------
  `input_manifest_id`        Primary identifier
  `zone_id`                  Zone
  `window_start`             Start
  `window_end`               End
  `feature_schema_version`   Feature set
  `golden_policy_version`    Golden construction
  `data_fingerprint`         Hash/fingerprint
  `created_at`               Creation

`c3_forecasts` can reference this manifest.

The final implementation may optimize how individual row lineage is
stored.

------------------------------------------------------------------------

# 54. Decision Table --- `decisions`

Purpose:

Store Decision Engine outputs.

Recommended fields:

  Field               Meaning
  ------------------- ------------------------------------------
  `decision_id`       Primary identifier
  `zone_id`           Zone/system scope
  `forecast_id`       C3 forecast where applicable
  `decision_type`     MODE_CHANGE, ALERT, HOLD, DEGRADED, etc.
  `previous_mode`     Existing mode
  `desired_mode`      Selected mode
  `warning_level`     Selected warning state
  `decision_status`   Applied/pending/etc.
  `ruleset_version`   Decision policy version
  `reason_codes`      Explainable reasons
  `decided_at`        Decision time
  `created_at`        Persistence

A Decision Engine rule may act even when a C3 forecast is unavailable,
so `forecast_id` can be nullable where justified.

------------------------------------------------------------------------

# 55. Decision Reason Codes

Example conceptual reasons:

``` text
FORECAST_THRESHOLD_EXCEEDED
PERSISTENT_HIGH_RISK
SECURITY_DEGRADED
INSUFFICIENT_DATA
RECOVERY_FAILURE
MANUAL_OVERRIDE
RISK_DECREASE_CONFIRMED
```

The exact set belongs to the Decision Engine specification.

------------------------------------------------------------------------

# 56. Command Table --- `device_commands`

Purpose:

Track commands sent to field devices/gateway.

Recommended fields:

  -----------------------------------------------------------------------
  Field                               Meaning
  ----------------------------------- -----------------------------------
  `command_id`                        Primary identifier

  `device_id`                         Target

  `decision_id`                       Originating decision

  `command_type`                      SET_MODE, SET_POLICY,
                                      REQUEST_BACKUP, REQUEST_REPLAY,
                                      etc.

  `payload`                           Structured command parameters

  `command_sequence`                  Ordering/idempotency token

  `created_at`                        Creation

  `sent_at`                           Transmission

  `expires_at`                        Validity deadline

  `status`                            PENDING/SENT/ACKED/FAILED/EXPIRED
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 57. Command Acknowledgement Table --- `command_acknowledgements`

Recommended fields:

  Field             Meaning
  ----------------- ----------------------------
  `ack_id`          Primary identifier
  `command_id`      Command
  `device_id`       Responding device
  `ack_status`      APPLIED/REJECTED/FAILED
  `reported_mode`   Device mode after command
  `received_at`     ACK receipt
  `details`         Failure/reason information

This prevents the server from assuming a command was applied merely
because it was sent.

------------------------------------------------------------------------

# 58. Alert Table --- `alerts`

Purpose:

Record warnings/notifications.

Recommended fields:

  Field            Meaning
  ---------------- --------------------------------------------------
  `alert_id`       Primary identifier
  `zone_id`        Affected zone
  `decision_id`    Triggering decision
  `alert_type`     LOCAL_SIREN, VISUAL, EXTERNAL_NOTIFICATION, etc.
  `severity`       Warning severity
  `message_code`   Stable alert template/code
  `created_at`     Creation
  `activated_at`   Activation
  `cleared_at`     Clear time
  `status`         ACTIVE/CLEARED/FAILED

External notification channel details should only be added once
implementation is finalized.

------------------------------------------------------------------------

# 59. Model Registry --- `models`

Purpose:

Represent a logical model/component model family.

Recommended fields:

  Field           Meaning
  --------------- ------------------------------------------------------
  `model_id`      Primary identifier
  `component`     C1/C2/C3/C4
  `model_name`    Logical name
  `task_type`     Classification, forecasting, anomaly detection, etc.
  `description`   Model purpose
  `created_at`    Creation

------------------------------------------------------------------------

# 60. Model Registry --- `model_versions`

Purpose:

Version trained artifacts.

Recommended fields:

  Field                      Meaning
  -------------------------- ----------------------------------------
  `model_version_id`         Primary identifier
  `model_id`                 Parent model
  `version`                  Version string
  `dataset_version_id`       Training dataset
  `algorithm`                Algorithm/architecture
  `feature_schema_version`   Feature contract
  `artifact_uri`             Artifact location
  `artifact_hash`            Integrity/reproducibility hash
  `metrics`                  Structured evaluation summary
  `code_version`             Git commit/tag where practical
  `status`                   CANDIDATE/APPROVED/RETIRED/ROLLED_BACK
  `trained_at`               Training time
  `approved_at`              Promotion time
  `created_at`               Metadata creation

Large model binaries should normally live in artifact storage/filesystem
rather than as database blobs.

------------------------------------------------------------------------

# 61. Dataset Registry --- `datasets`

Purpose:

Represent logical research datasets.

Examples:

``` text
C1_CREDIBILITY
C2_DIAGNOSTICS
C3_TEMPORAL
C4_TRUST
```

Recommended fields:

  Field            Meaning
  ---------------- ---------------------
  `dataset_id`     Primary identifier
  `dataset_code`   Stable logical name
  `component`      Owner
  `description`    Purpose
  `created_at`     Creation

------------------------------------------------------------------------

# 62. Dataset Registry --- `dataset_versions`

Recommended fields:

  Field                  Meaning
  ---------------------- ----------------------------------
  `dataset_version_id`   Primary identifier
  `dataset_id`           Parent dataset
  `version`              Version
  `schema_version`       Dataset schema
  `source_cutoff_at`     Operational-data cutoff
  `source_types`         Physical/synthetic/external etc.
  `row_count`            Number of records/windows
  `file_uri`             Export location
  `file_hash`            Integrity hash
  `builder_version`      Dataset builder version
  `split_strategy`       Time/zone/event-aware method
  `created_at`           Creation

This eliminates filenames such as `final_REAL_v7_new.csv`.

------------------------------------------------------------------------

# 63. Experiment Table --- `experiments`

Purpose:

Track reproducible model experiments.

Recommended fields:

  Field                  Meaning
  ---------------------- ----------------------------
  `experiment_id`        Primary identifier
  `component`            C1/C2/C3/C4
  `dataset_version_id`   Dataset
  `experiment_name`      Human-readable name
  `algorithm`            Model
  `hyperparameters`      Structured parameters
  `feature_set`          Feature definition/version
  `random_seed`          Seed where applicable
  `split_strategy`       Evaluation split
  `metrics`              Results
  `code_version`         Git commit/tag
  `artifact_uri`         Output artifacts
  `started_at`           Start
  `completed_at`         Completion

A specialized experiment tracker may later complement this table, but
the research metadata must remain reproducible.

------------------------------------------------------------------------

# 64. Schema Registry / Contract Versioning

A small registry should track important data contracts.

Conceptually:

``` text
telemetry schema v1
C1 output schema v1
C2 output schema v1
Golden Timeline schema v1
C3 input schema v1
C3 output schema v1
```

Recommended table:

``` text
schema_versions
```

with fields such as:

``` text
schema_name
version
definition_uri
hash
status
created_at
```

------------------------------------------------------------------------

# 65. Audit Events --- `audit_events`

Purpose:

Record significant software/security/administrative actions that are not
ordinary telemetry.

Examples:

``` text
MODEL_PROMOTED
MODEL_ROLLED_BACK
SCHEMA_CHANGED
DEVICE_REGISTERED
CALIBRATION_UPDATED
MANUAL_MODE_OVERRIDE
DATASET_FROZEN
```

Recommended fields:

  Field              Meaning
  ------------------ ---------------------
  `audit_event_id`   Primary identifier
  `event_type`       Event
  `entity_type`      Affected entity
  `entity_id`        Affected ID
  `actor_type`       SYSTEM/USER/SERVICE
  `details`          Structured metadata
  `occurred_at`      Time

------------------------------------------------------------------------

# 66. Application Logs vs Database Audit

Do not store every debug log as a relational business row.

Use structured application logs for high-volume operational diagnostics.

Use database audit records for research/security/business-significant
state changes.

This avoids turning the main database into a generic text-log dump.

------------------------------------------------------------------------

# 67. Conceptual Entity Relationship Diagram

``` text
zones
  │
  └──< devices
         │
         └──< sensor_instances
                 │
                 └──< sensor_calibrations

devices
  │
  └──< telemetry_packets
          │
          ├──< sensor_observations
          │       │
          │       └──< c1_credibility_assessments
          │
          └──< c4_trust_assessments

devices
  └──< silence_events
          │
          └──< c2_diagnoses
                  │
                  └──< recovery_events
                           │
                           └──< recovered_observations

sensor_observations ─┐
c4 assessments ──────┼──→ golden_observations
c1 assessments ──────┤
recovered obs ───────┘
                           │
                           └──→ forecast input
                                   │
                                   └──< c3_forecasts
                                            │
                                            └──< decisions
                                                     │
                                                     ├──< device_commands
                                                     │       └──< command_acknowledgements
                                                     │
                                                     ├──< operating_mode_events
                                                     └──< alerts
```

------------------------------------------------------------------------

# 68. Example: One Normal Type A Packet

Conceptual packet:

``` json
{
  "schema_version": "1.0",
  "packet_id": "example-packet-id",
  "device_code": "Z01-A01",
  "zone_code": "Z01",
  "sequence_no": 18421,
  "observed_at": "2026-10-10T02:45:20.245Z",
  "mode": "RISK",
  "measurements": {
    "soil_moisture_1_pct": 67.4,
    "soil_moisture_2_pct": 69.1,
    "fsr_1_raw": 1830,
    "fsr_2_raw": 1764,
    "air_temperature_c": 27.8,
    "relative_humidity_pct": 84.2,
    "bus_voltage_v": 11.96
  }
}
```

This example illustrates structure only.

It does not define final radio encoding.

------------------------------------------------------------------------

# 69. Example: Database Normalization

The packet above becomes approximately:

``` text
telemetry_packets
-----------------
packet_id      = ...
device         = Z01-A01
sequence_no    = 18421
observed_at    = ...
received_at    = ...
mode           = RISK
```

plus several:

``` text
sensor_observations
-------------------
observation 1 → soil moisture probe 1 → 67.4 %
observation 2 → soil moisture probe 2 → 69.1 %
observation 3 → FSR 1 raw → 1830
observation 4 → FSR 2 raw → 1764
observation 5 → air temperature → 27.8 °C
observation 6 → humidity → 84.2 %
observation 7 → bus voltage → 11.96 V
```

This is why packet and observation are separate entities.

------------------------------------------------------------------------

# 70. Example: C4 + C1

For the same packet:

``` text
C4:
packet_id = ...
trust_class = TRUSTED
mandatory_verification_passed = true
```

For soil moisture observation 1:

``` text
C1:
observation_id = ...
credibility_class = VALID_EVENT
credibility_score = ...
```

For another observation in the same packet, C1 could theoretically
return ANOMALY.

Packet trust and measurement credibility remain separate.

------------------------------------------------------------------------

# 71. Example: C2 Recovery

Suppose:

``` text
A1 expected at 10:10
A1 packet missing
```

The system creates:

``` text
silence_event
```

C2 diagnoses:

``` text
failure_class = communication_failure
```

and requests:

``` text
REQUEST_SD_REPLAY
```

If A1 later sends its stored original 10:10 reading:

``` text
observed_at = 10:10
received_at = 10:14
origin = LATE_ORIGINAL / replay recovery
```

The database retains the actual observation time and late receipt.

------------------------------------------------------------------------

# 72. Example: Backup-Derived Recovery

If A1's actual value cannot be recovered but BK1 provides evidence:

``` text
target = A1 soil moisture at 10:10
backup source = BK1
recovery method = BACKUP_SENSOR
value = ...
confidence = ...
```

This becomes a recovered observation with explicit provenance.

It must not be inserted as though A1 directly measured it.

------------------------------------------------------------------------

# 73. Example: Golden Timeline

Conceptually:

  Time            Feature   Value Origin   Credibility         Recovered
  ------- --------------- ------- -------- ------------------- -----------
  10:00     soil moisture    61.0 DIRECT   CLEAN               false
  10:05     soil moisture    63.0 DIRECT   CLEAN               false
  10:10     soil moisture    66.4 BACKUP   usable per policy   true
  10:15     soil moisture    70.0 DIRECT   VALID_EVENT         false

C3 can now distinguish direct and recovered evidence.

------------------------------------------------------------------------

# 74. C3 Temporal Feature View

The C3 dataset builder may transform Golden Timeline records into a wide
temporal feature representation.

Example conceptual training row/window:

``` text
zone_id
window_end
horizon_min

rain_15m_sum
rain_1h_sum
rain_6h_sum

soil_moisture_mean
soil_moisture_trend_30m

tilt_mean_deg
tilt_rate_deg_h
vibration_mean_g

delta_t
current_system_mode

recovered_fraction
mean_recovery_confidence
credibility_summary

target_landslide_within_horizon
```

The exact C3 schema belongs to Document 03.

------------------------------------------------------------------------

# 75. Long-Format Operational Data vs Wide ML Data

Operational sensor storage should generally remain normalized/long-form:

``` text
time | sensor | value
```

ML datasets may be wide:

``` text
time | moisture | rain | tilt | vibration | ...
```

Trying to make the live operational database look exactly like one ML
CSV would create unnecessary coupling.

------------------------------------------------------------------------

# 76. Missing Values

A missing measurement must remain distinguishable from:

``` text
0
```

Examples:

``` text
rainfall = 0
```

can be a valid observation.

``` text
rainfall = NULL / missing state
```

means no usable measurement exists.

The dataset builder may later encode missingness appropriately for a
selected model.

------------------------------------------------------------------------

# 77. NaN/NULL Policy

Operational SQL storage should use database `NULL` only when the
semantics genuinely mean unknown/not available.

Special states such as:

``` text
UNTRUSTED
ANOMALOUS
RECOVERED
STALE
```

should be represented through quality/provenance metadata rather than
overloading `NULL`.

ML exports can map SQL nulls to the representation required by each
library.

------------------------------------------------------------------------

# 78. Duplicate Packet Handling

The ingestion layer must be idempotent.

A packet retransmitted because an ACK was lost should not produce
duplicate logical observations.

Candidate uniqueness context:

``` text
device_id
+
sequence_no
+
protocol/session context
```

or a stable `packet_id`.

The final key must account for sequence counter resets/reboots.

Therefore a simplistic global unique constraint on sequence number alone
is unsafe.

------------------------------------------------------------------------

# 79. Sequence Reset / Device Restart

If a device restarts and sequence numbering resets, the system needs
contextual evidence such as:

``` text
boot/session identifier
restart event
device identity
timestamp
```

to distinguish:

``` text
new legitimate sequence
```

from:

``` text
replay
```

This will be coordinated with C4.

------------------------------------------------------------------------

# 80. Indexing Strategy

Exact indexes will be generated with SQL migrations, but expected
high-value query paths include:

``` text
sensor observations by sensor + time
packets by device + time
packets by device + sequence/session
Golden observations by zone + time
forecasts by zone + generated time
silence events by device + status
commands by device + status
mode events by scope + time
```

Indexes should support actual query patterns rather than indexing every
column.

------------------------------------------------------------------------

# 81. TimescaleDB Hypertable Candidates

Likely candidates include:

``` text
sensor_observations
golden_observations
possibly telemetry_packets
possibly derived_observations
possibly c3_forecasts
```

The final choice should be based on expected volume/query patterns.

Small reference tables should remain ordinary PostgreSQL tables.

------------------------------------------------------------------------

# 82. Retention and Compression

Research evidence should not be deleted merely to optimize storage
without a documented retention policy.

Timescale compression/retention features may later be used where
appropriate.

Before deleting raw telemetry, the team must consider:

-   thesis reproducibility;
-   audit requirements;
-   retraining;
-   model comparison;
-   storage capacity.

No automatic destructive retention is frozen here.

------------------------------------------------------------------------

# 83. Database Transactions

Operations that must remain logically consistent should use
transactions.

Example:

``` text
insert packet
+
insert observations
```

should not leave a partially created packet state unnoticed if
processing fails midway.

Downstream component outputs may be asynchronous and independently
transactional.

------------------------------------------------------------------------

# 84. Foreign-Key Integrity

Reference relationships should use database constraints where practical.

Examples:

``` text
observation.device_id → devices.device_id
observation.packet_id → telemetry_packets.packet_id
C1.observation_id → sensor_observations.observation_id
C4.packet_id → telemetry_packets.packet_id
forecast.model_version_id → model_versions.model_version_id
```

This reduces silent data corruption.

------------------------------------------------------------------------

# 85. Enum Strategy

Enums such as operating mode need a shared definition.

Baseline modes:

``` text
DEEP_SLEEP
IDLE
RISK
WARNING
EMERGENCY
```

Implementation may use:

-   PostgreSQL enum;
-   constrained text;
-   reference table.

Whichever mechanism is chosen, application code must consume the same
shared definition.

------------------------------------------------------------------------

# 86. JSONB Usage

JSONB is useful for:

-   extensible metadata;
-   model metrics;
-   reason details;
-   raw decoded payloads;
-   hyperparameters.

It should not be used as an excuse to place the entire database into one
unstructured JSON column.

Frequently queried/core relational fields should remain explicit
columns.

------------------------------------------------------------------------

# 87. Binary/Artifact Storage

Do not store large files directly in normal relational rows unless a
strong reason exists.

Examples:

``` text
trained .pt/.pkl/.joblib artifacts
Parquet datasets
plots
reports
```

should generally live in versioned filesystem/object/artifact storage.

The database stores:

``` text
URI/path
hash
version
metadata
```

------------------------------------------------------------------------

# 88. Data Lineage

Dataset/model results must be traceable backward.

Ideal chain:

``` text
forecast
  ↓
model version
  ↓
feature schema
  ↓
Golden input window
  ↓
Golden observations
  ↓
C1/C2/C4 assessments
  ↓
raw observations
  ↓
packets
  ↓
device/sensor/calibration
```

This is one of GeoNex's strongest architecture requirements.

------------------------------------------------------------------------

# 89. C1 Dataset Extraction Boundary

C1 training data should be produced through a dedicated dataset builder.

It may combine:

``` text
sensor observations
rainfall context
neighbour observations
historical features
known labels
```

The builder freezes a versioned dataset.

C1 training code should not directly mutate operational tables.

------------------------------------------------------------------------

# 90. C2 Dataset Extraction Boundary

C2 dataset construction may combine:

``` text
silence events
packet timing
device health
backup response
neighbour/hub state
known failure scenario
recovery outcome
```

Targets must be independently defined and documented.

------------------------------------------------------------------------

# 91. C3 Dataset Extraction Boundary

C3 should normally derive training sequences from a frozen Golden
Timeline/data snapshot rather than querying a constantly changing live
view during training.

This ensures that:

``` text
training run A
```

and:

``` text
training run B
```

can use the exact same input data.

------------------------------------------------------------------------

# 92. C4 Dataset Extraction Boundary

C4 behavioural training data may combine:

``` text
packet timing
RSSI/SNR where available
retry patterns
identity/security outcomes
device-health behaviour
known attack/anomaly labels
```

Mandatory deterministic verification does not need to be "learned" by
the ML model.

------------------------------------------------------------------------

# 93. Dataset Manifest

Every exported dataset should have a manifest.

Recommended metadata:

``` yaml
dataset_code: C3_TEMPORAL
version: 1
schema_version: 1
created_at: ...
source_cutoff_at: ...
source_types:
  - SYNTHETIC
builder_version: ...
split_strategy: ...
row_count: ...
file_hash: ...
```

Later physical datasets may contain:

``` yaml
source_types:
  - PHYSICAL_DEMO
```

or a controlled combination with explicit provenance.

------------------------------------------------------------------------

# 94. Synthetic Data Policy

Synthetic data must include generator metadata.

Recommended:

``` text
generator_name
generator_version
random_seed
scenario/config version
generation time
```

Synthetic and physical records should not be merged without an explicit
experiment design.

------------------------------------------------------------------------

# 95. External Data Policy

External datasets require metadata including:

``` text
source name
source version/date
original schema
transformation/mapping
license/usage notes where applicable
```

The transformed GeoNex dataset should retain the source identifier.

------------------------------------------------------------------------

# 96. Physical Demo Data Policy

Physical-demo data should record:

``` text
device/sensor identity
calibration
firmware version
sampling policy
observation timestamps
experiment/scenario identifier where applicable
```

This is needed to interpret prototype experiments correctly.

------------------------------------------------------------------------

# 97. Scenario / Test Run Table --- `test_runs`

A dedicated test-run entity is recommended for physical and simulated
experiments.

Fields:

  Field                     Meaning
  ------------------------- --------------------------------------
  `test_run_id`             Primary identifier
  `test_run_code`           Human-readable code
  `test_type`               PHYSICAL_DEMO, SIMULATION, HIL, etc.
  `started_at`              Start
  `ended_at`                End
  `scenario`                Scenario metadata
  `configuration_version`   System configuration
  `notes`                   Research notes

Packets/observations may optionally reference a test run.

------------------------------------------------------------------------

# 98. Why Test Runs Matter

Suppose the team intentionally disconnects A1 to test C2.

Those packets/silence events should be traceable to:

``` text
C2_COMMS_FAILURE_TEST_001
```

rather than later being mistaken for a naturally occurring field
failure.

------------------------------------------------------------------------

# 99. Ground-Truth Labels

Ground truth must be stored separately from predictions.

Recommended generic concept:

``` text
ground_truth_annotations
```

Possible fields:

``` text
annotation_id
entity_type
entity_id / time window
label_type
label_value
annotation_source
annotator/method
confidence
created_at
```

Exact component-specific label tables may later be preferable.

The central rule is:

> **A model prediction must never silently become its own ground
> truth.**

------------------------------------------------------------------------

# 100. Label Provenance

A label should answer:

``` text
Who/what created this label?
From which evidence?
Was it simulated?
Was it experimentally induced?
Was it manually reviewed?
Was it derived from an external dataset?
```

This is critical for research validity.

------------------------------------------------------------------------

# 101. Data Leakage Guardrails

Dataset builders must explicitly prevent:

-   future observations entering past features;
-   post-event recovery entering an earlier simulated runtime window;
-   target-derived fields becoming features;
-   model predictions becoming labels;
-   random row splitting of strongly dependent temporal windows;
-   duplicate event windows appearing in both train and test.

Each component's detailed leakage rules belong in Document 03 and its
member guide.

------------------------------------------------------------------------

# 102. C3 Special Leakage Risk

Suppose:

``` text
risk_probability
```

was generated from the same future-event target used to define:

``` text
risk_level
```

Then using `risk_probability` as a feature to predict `risk_level` would
be leakage.

Similarly, if:

``` text
recommended_mode
```

was generated from the target risk label, using it as an input can
create circular prediction.

All C3 fields must therefore have explicit provenance.

------------------------------------------------------------------------

# 103. Historical "As-Of" Semantics

For rigorous runtime simulation, dataset queries should support the
question:

> What information was available as of time T?

This matters because:

``` text
observed_at < T
```

does not guarantee:

``` text
received_at < T
```

A late-replayed observation cannot be used by a real-time forecast that
occurred before it arrived.

------------------------------------------------------------------------

# 104. C3 Runtime Dataset Condition

For real-time-equivalent evaluation, an observation should only be
available if it satisfies the experiment's "as-of" policy.

Conceptually:

``` text
observed_at <= forecast_time
AND
received_at <= forecast_time
AND
processing/validation completed before forecast_time
```

The exact condition depends on the simulated pipeline.

This prevents retrospective knowledge from inflating model performance.

------------------------------------------------------------------------

# 105. Data Access Layer

Application components should not each embed arbitrary SQL throughout
their code.

A shared data-access layer/repository module should expose controlled
operations such as:

``` text
save_packet()
save_observations()
get_recent_zone_window()
save_c1_assessment()
open_silence_event()
save_recovery()
get_golden_window()
save_forecast()
save_decision()
```

This improves consistency and testability.

------------------------------------------------------------------------

# 106. Component Write Ownership

Recommended ownership:

``` text
Ingestion
  → telemetry_packets
  → sensor_observations

C4
  → c4_trust_assessments

C1
  → c1_credibility_assessments

C2
  → silence_events
  → c2_diagnoses
  → recovery_events
  → recovered_observations

Golden Builder
  → golden_observations

C3
  → c3_forecasts

Decision Engine
  → decisions

Control Service
  → device_commands
  → command acknowledgements / applied policy state

Alert Service
  → alerts
```

Components may read required shared data but should not randomly modify
another component's output.

------------------------------------------------------------------------

# 107. Append-Oriented Analytical Results

Component assessment tables should generally be
append-oriented/version-aware.

If C1 model v2 reprocesses an old observation, do not silently destroy
the v1 result.

The system should be able to compare:

``` text
C1 v1 result
C1 v2 result
```

A separate "current approved result" view can select the active model
result.

------------------------------------------------------------------------

# 108. Reprocessing

Reprocessing is expected in research.

Examples:

``` text
rerun C1 with new model
rebuild Golden Timeline under new policy
rerun C3 retrospectively
```

Therefore derived results need:

``` text
model version
ruleset/policy version
processing time
```

Without these fields, reproducibility becomes impossible.

------------------------------------------------------------------------

# 109. Soft Deactivation vs Deletion

Reference/configuration records such as devices and sensors should
usually be retired/deactivated rather than deleted if historical
telemetry references them.

Example:

``` text
sensor removed
→ removed_at populated
```

not:

``` text
DELETE sensor
```

which would break historical lineage.

------------------------------------------------------------------------

# 110. Database Migration Strategy

Schema changes must be version-controlled.

Recommended approach:

``` text
database/
  migrations/
```

Every structural change becomes a migration.

Members must not manually alter their local database and forget to
commit the schema change.

------------------------------------------------------------------------

# 111. Seed Data

Shared static/reference data should be reproducibly seeded.

Examples:

``` text
operating modes
device types
sensor definitions
initial sampling-policy placeholders
reason-code definitions where implemented
```

Seed scripts must not insert fake research results into production
tables.

------------------------------------------------------------------------

# 112. Development Database

Each developer can run a local database instance with the same schema.

Recommended development mechanism:

``` text
Docker Compose
+
PostgreSQL/TimescaleDB
+
migrations
+
seed data
```

The exact infrastructure file will be provided in the repository
architecture/development-start guide.

------------------------------------------------------------------------

# 113. Environment Separation

At minimum distinguish:

``` text
development
test
research/demo
```

Do not point unit tests at the only copy of research data.

Configuration should select the correct database through environment
variables.

------------------------------------------------------------------------

# 114. Credentials

Database passwords and secrets must be loaded through environment
configuration.

Do not commit:

``` text
real passwords
private keys
API credentials
```

to Git.

A safe `.env.example` may document required variable names without real
secrets.

------------------------------------------------------------------------

# 115. Database Backup

Research-critical database state should be backed up.

At minimum:

-   scheduled logical backups during important experimental periods;
-   backup before destructive migrations;
-   exported dataset/model artifacts stored separately.

Exact operational schedule will depend on project resources.

------------------------------------------------------------------------

# 116. Data Validation at Ingestion

Before a packet enters normalized observation tables, ingestion should
validate:

``` text
schema version recognized
required identifiers present
timestamp parseable
measurement keys recognized
numeric type valid
unit/channel contract valid
payload structurally valid
```

This is structural validation.

It is **not** the same as C1 environmental credibility.

------------------------------------------------------------------------

# 117. Structural Validation vs C1

Example:

``` text
soil_moisture = 9999
```

may be structurally valid JSON and numeric.

Ingestion can accept/preserve it.

C1 or acquisition-range logic may then identify it as
implausible/anomalous.

Do not merge software schema validation and research credibility
classification into one concept.

------------------------------------------------------------------------

# 118. Firmware Range Checks

Embedded firmware may detect obvious acquisition faults such as:

``` text
ADC read failed
sensor disconnected
CRC failure from digital sensor
```

These should be transmitted as acquisition-quality/device-health
metadata where possible.

C1 then receives better context.

Firmware should not hide every unusual environmental reading merely
because it appears extreme.

------------------------------------------------------------------------

# 119. Raw Data Immutability

Once accepted into the raw evidence layer, core packet/observation
evidence should not be casually edited.

Corrections should preferably be represented as:

``` text
new derived/corrected record
+
lineage
+
reason
```

Administrative corrections require auditability.

------------------------------------------------------------------------

# 120. Golden Timeline Rebuildability

The Golden Timeline should be reproducible from:

``` text
raw observations
+
C4 results
+
C1 results
+
C2 results
+
Golden policy version
```

Therefore Golden data is not the only surviving copy of the evidence.

------------------------------------------------------------------------

# 121. Data Flow --- Normal Packet

``` text
telemetry packet
      ↓
telemetry_packets
      ↓
sensor_observations
      ↓
c4_trust_assessments
      ↓
c1_credibility_assessments
      ↓
Golden Builder
      ↓
golden_observations
      ↓
C3 temporal window
```

------------------------------------------------------------------------

# 122. Data Flow --- Silent Device

``` text
sampling policy
      ↓
expected reporting deadline
      ↓
deadline missed
      ↓
silence_events
      ↓
c2_diagnoses
      ↓
recovery_events
      ↓
recovered_observations / late originals
      ↓
Golden Builder
```

------------------------------------------------------------------------

# 123. Data Flow --- Forecast to Control

``` text
golden_observations
      ↓
forecast input manifest
      ↓
c3_forecasts
      ↓
decisions
      ↓
operating_mode_events
      +
device_commands
      ↓
command_acknowledgements
      ↓
device_policy_assignments
```

------------------------------------------------------------------------

# 124. Data Flow --- Research Dataset

``` text
frozen operational snapshot
      +
approved synthetic/external data
      ↓
component dataset builder
      ↓
dataset manifest
      ↓
dataset_versions
      ↓
Parquet / CSV artifact
      ↓
experiment
      ↓
model_versions
```

------------------------------------------------------------------------

# 125. Minimum Database Tables

The initial integrated repository should plan for at least the following
logical tables:

``` text
zones
devices
sensor_definitions
sensor_instances
sensor_calibrations

telemetry_packets
sensor_observations
derived_observations
device_events

c4_trust_assessments
c1_credibility_assessments

silence_events
c2_diagnoses
recovery_events
recovered_observations

golden_observations

sampling_policies
device_policy_assignments
operating_mode_events

forecast_input_manifests
c3_forecasts
decisions

device_commands
command_acknowledgements
alerts

models
model_versions
datasets
dataset_versions
experiments
schema_versions

test_runs
ground_truth_annotations
audit_events
```

Some tables may be refined/split during SQL implementation, but no
component may independently replace this shared architecture without
team review.

------------------------------------------------------------------------

# 126. Tables That Must Not Be Confused

``` text
telemetry_packets
≠
sensor_observations

sensor_observations
≠
golden_observations

golden_observations
≠
C3 training CSV

c3_forecasts
≠
ground truth

sampling_policies
≠
operating_mode_events

device_commands
≠
command_acknowledgements

c2_diagnoses
≠
recovery_events
```

These distinctions are intentional.

------------------------------------------------------------------------

# 127. Example Full Lineage

Suppose C3 predicts high risk at 10:20.

The database should eventually allow:

``` text
forecast F001
   ↓
model C3 v3
   ↓
input manifest M001
   ↓
Golden window 09:50–10:20
   ↓
soil moisture at 10:10
   ↓
recovered via BK1
   ↓
recovery event R007
   ↓
A1 silence event S004
   ↓
C2 diagnosis: communication failure
```

and for a direct value:

``` text
Golden value
   ↓
C1 VALID_EVENT
   ↓
C4 TRUSTED
   ↓
raw observation
   ↓
packet
   ↓
A1 sensor instance
   ↓
calibration version
```

This is the level of traceability GeoNex should target.

------------------------------------------------------------------------

# 128. Data Architecture Best Practices Adopted

GeoNex adopts the following best-practice principles:

1.  immutable/preserved raw evidence;
2.  normalized operational telemetry;
3.  explicit units;
4.  stable identifiers;
5.  timezone-aware timestamps;
6.  separate observation and receipt time;
7.  calibration versioning;
8.  provenance tracking;
9.  append/version-aware AI results;
10. explicit model versions;
11. explicit dataset versions;
12. contract/schema versioning;
13. idempotent ingestion;
14. foreign-key integrity;
15. migrations;
16. environment-separated configuration;
17. secrets outside Git;
18. dataset manifests;
19. reproducible experiments;
20. as-of-time semantics for temporal evaluation.

------------------------------------------------------------------------

# 129. Research Justification of the Architecture

This architecture is not merely software organization.

It directly protects research validity.

## Raw preservation

Allows re-analysis when models change.

## Provenance

Prevents recovered/synthetic data from being misrepresented as direct
physical observations.

## Model versioning

Allows experimental comparisons and auditability.

## Time-aware storage

Supports variable-rate C3 forecasting and C2 silence detection.

## Separate C4/C1 results

Preserves the theoretical distinction between source trust and
measurement credibility.

## Separate C2 diagnosis/recovery

Prevents recovery policy from being confused with failure
classification.

## Golden Timeline

Provides C3 with a controlled, provenance-aware temporal representation
without destroying original evidence.

## Dataset registry

Supports reproducible papers/thesis experiments.

------------------------------------------------------------------------

# 130. Decisions Frozen by Document 02

The following are now baseline data-architecture decisions:

1.  The live system uses an operational database rather than CSV files
    as inter-component storage.
2.  PostgreSQL + TimescaleDB is the recommended operational database
    baseline.
3.  Raw packets and normalized observations are separate.
4.  One packet may contain many observations.
5.  Sensor definitions and physical sensor instances are separate.
6.  Calibration is versioned.
7.  `observed_at`, `received_at` and component processing times are
    distinct.
8.  Raw evidence is preserved.
9.  C4 assessments are packet/source-oriented.
10. C1 assessments are observation-oriented.
11. C2 silence events, diagnoses and recoveries are separate entities.
12. Late-original recovery and estimated/substitute recovery are
    distinguished.
13. Golden Timeline data retains lineage and provenance.
14. C3 forecasts retain model/input-window lineage.
15. Decision Engine outputs are stored separately from C3 predictions.
16. Mode history, sampling policies and device policy application are
    persisted.
17. Commands and acknowledgements are separate.
18. Dataset and model versions are first-class entities.
19. Synthetic, simulated, external and physical data must remain
    identifiable.
20. Ground truth is separate from predictions.
21. Runtime and retrospective/as-of-time semantics must remain
    distinguishable.
22. Database schema changes are migration-controlled.
23. Components write to their owned output entities through shared
    contracts.
24. ML datasets are exported/versioned artifacts, not the operational
    database itself.

------------------------------------------------------------------------

# 131. Decisions Not Frozen Yet

The following remain for subsequent documents/implementation:

-   exact SQL DDL;
-   exact UUID implementation;
-   exact Timescale hypertables/chunk sizes;
-   exact indexes;
-   exact enum implementation;
-   exact C4 cryptographic fields;
-   exact C1 feature/output contract;
-   exact C2 class/action taxonomy;
-   exact Golden Builder acceptance policy;
-   exact C3 feature/window schema;
-   exact C3 target/horizons;
-   exact sampling intervals/tolerances;
-   exact mode transition policy;
-   exact artifact storage mechanism;
-   exact retention/compression schedule;
-   exact message broker/event infrastructure if any.

No member should silently decide these cross-component items
independently.

------------------------------------------------------------------------

# 132. What Comes Next

Now that the operational data architecture is defined, the next document
must specify the **research datasets themselves**.

It should answer:

``` text
What exact dataset does C1 train on?
What exact dataset does C2 train on?
What exact temporal dataset does C3 train on?
What exact dataset does C4 train on?

Which columns are raw?
Which are derived?
Which are metadata?
Which are features?
Which are labels?
Which must never be used as features?
How are windows constructed?
How are synthetic/physical/external sources represented?
How are train/validation/test splits created?
What sample rows look like?
How does each dataset map back to the operational DB?
```

------------------------------------------------------------------------

# Document 02 Status

**`02_GEONEX_DATA_DATABASE_ARCHITECTURE.md` --- DATA ARCHITECTURE
BASELINE READY**

This document establishes the shared operational data model that all
four component developers must follow.

**Next document:**

`03_GEONEX_DATASET_ARCHITECTURE.md`

Document 03 will define C1, C2, C3 and C4 dataset structures in detail,
including fields, feature/label roles, sample rows, temporal windows,
source/provenance fields, leakage controls, split strategies, dataset
builders and mappings from the operational database.
