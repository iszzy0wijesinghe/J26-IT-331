# 11_GEONEX_INTEGRATION_CONTRACT.md

**Project:** GeoNex --- Smart Landslide Early Warning Prediction System
using IoT, Edge AI and Risk Analytics\
**Document:** Shared Integration Contract\
**Status:** Integration Baseline v1\
**Depends on:** Documents 00--10\
**Audience:** All four component developers, firmware developers,
database/integration developer, testing team\
**Primary purpose:** Freeze the shared meanings and interface boundaries
required for independent development without allowing one component to
silently redefine another component's data.

------------------------------------------------------------------------

# 1. Why This Document Exists

GeoNex contains independently developed components that must behave as
one system.

Without a shared contract, teams can accidentally create incompatible
assumptions such as:

``` text
C1 calls a device "node_id"
C4 calls it "device_id"

C2 interprets timestamp as receipt time
C3 interprets it as observation time

C1 overwrites bad raw values
C3 assumes all stored values are original

C3 directly changes device mode
Decision Engine also changes device mode

one service treats WARNING as risk label
another treats WARNING as operating mode
```

This document prevents those failures.

------------------------------------------------------------------------

# 2. Contract Principle

Every boundary must answer:

``` text
WHAT is this object?
WHO creates it?
WHO may modify it?
WHEN was it valid?
WHAT version defines it?
WHERE did it come from?
HOW should failure be represented?
```

------------------------------------------------------------------------

# 3. Integration Rule

No member may silently change:

``` text
canonical IDs
timestamp semantics
mode names
shared status meanings
Golden Timeline provenance
cross-component ordering
component output meanings
command semantics
```

A required change must be proposed as a shared architecture change.

------------------------------------------------------------------------

# 4. Contract Layers

GeoNex integration is divided into:

``` text
Layer 1 — Physical/device identity
Layer 2 — Telemetry transport
Layer 3 — Operational observations
Layer 4 — C4 trust
Layer 5 — C1 credibility
Layer 6 — C2 silence/recovery
Layer 7 — Golden Timeline
Layer 8 — C3 forecast
Layer 9 — Decision Engine
Layer 10 — Device commands/ACK
Layer 11 — Alerts/audit
```

------------------------------------------------------------------------

# 5. Canonical Naming Style

Recommended shared software field style:

``` text
snake_case
```

Examples:

``` text
device_id
observed_at
model_version
```

Enums use stable uppercase values:

``` text
DEEP_SLEEP
VALID_EVENT
TRUSTED
```

------------------------------------------------------------------------

# 6. Canonical Identifier Principle

Identifiers describe entities, not display names.

They should be:

``` text
stable
unique within intended scope
machine-readable
not reused for a different entity
```

Database internal numeric keys may coexist with canonical external IDs.

------------------------------------------------------------------------

# 7. Canonical IDs

Shared identifiers include:

``` text
zone_id
device_id
sensor_instance_id
packet_id
observation_id
assessment_id
silence_event_id
diagnosis_id
recovery_event_id
golden_observation_id
forecast_id
decision_id
command_id
alert_id
model_version
dataset_version
schema_version
test_run_id
```

------------------------------------------------------------------------

# 8. `zone_id`

Identifies a monitored physical zone.

Example only:

``` text
ZONE_01
ZONE_02
```

Do not encode mutable risk state into `zone_id`.

------------------------------------------------------------------------

# 9. `device_id`

Identifies a physical/logical device participating in telemetry.

Examples conceptually:

``` text
PIPE_A1
PIPE_B1
PIPE_BK1
HUB_01
GATEWAY_MAIN
```

Final deployed naming can be configured, but semantics must remain
stable.

------------------------------------------------------------------------

# 10. `pipe_id` and `hub_id`

Where domain clarity helps, records may contain:

``` text
pipe_id
hub_id
```

but shared integrations should retain `device_id` as the general device
identity.

Do not create competing identities for the same hardware.

------------------------------------------------------------------------

# 11. `sensor_instance_id`

Identifies one installed sensor instance/channel.

It is not merely the sensor type.

Example concept:

``` text
SM_A1_01
SM_A1_02
```

Two soil-moisture sensors on one pipe require different instance IDs.

------------------------------------------------------------------------

# 12. `packet_id`

Identifies a telemetry packet/message instance.

It supports:

``` text
deduplication
audit
C4 analysis
traceability
```

Its exact generation scheme must be implementation-safe and unique
enough for the intended scope.

------------------------------------------------------------------------

# 13. `observation_id`

Identifies a normalized sensor observation extracted from telemetry.

One packet can contain multiple observations.

Therefore:

``` text
packet_id ≠ observation_id
```

------------------------------------------------------------------------

# 14. `model_version`

Every model-generated output must identify the model artifact/version
that created it.

Example pattern only:

``` text
C1_LGBM_001
C3_GRUD_003
```

Do not infer algorithm solely from a version string; model registry
stores authoritative metadata.

------------------------------------------------------------------------

# 15. `schema_version`

Every shared serialized contract should carry a schema version.

Initial conceptual version:

``` text
1.0
```

Version format can be finalized in implementation.

------------------------------------------------------------------------

# 16. Timestamp Standard

Shared timestamps should use an unambiguous timezone-aware
representation.

Recommended API/event representation:

``` text
ISO 8601 UTC
```

Example:

``` text
2026-10-10T03:45:12.450Z
```

Database storage may use timezone-aware timestamp types.

------------------------------------------------------------------------

# 17. Core Timestamp Semantics

Do not collapse:

``` text
observed_at
received_at
ingested_at
processed_at
generated_at
```

into one generic `timestamp`.

------------------------------------------------------------------------

# 18. `observed_at`

Time the measurement/event occurred at the originating device according
to its clock.

For recovered historical data:

``` text
observed_at
```

remains the original measurement time.

------------------------------------------------------------------------

# 19. `received_at`

Time the receiving gateway/system received the packet.

This can be much later than `observed_at`.

------------------------------------------------------------------------

# 20. `ingested_at`

Time the software ingestion/database pipeline accepted the record.

------------------------------------------------------------------------

# 21. `processed_at`

Time a component completed processing the relevant input.

------------------------------------------------------------------------

# 22. `generated_at`

Time a derived artifact was created.

Examples:

``` text
forecast
assessment
decision
command
```

------------------------------------------------------------------------

# 23. Clock Quality

Where available, include metadata such as:

``` text
clock_source
clock_sync_status
clock_uncertainty_ms
boot_id/session_id
```

Do not pretend device timestamps are perfectly synchronized if they are
not.

------------------------------------------------------------------------

# 24. Sequence Number

Telemetry should contain a sequence/counter where feasible.

Purpose:

``` text
detect duplicates
detect gaps
support ordering
support C4 freshness/replay analysis
support C2 missing-report reasoning
```

Reboot/session handling must prevent false replay conclusions.

------------------------------------------------------------------------

# 25. Common Envelope

All software-facing event objects should conceptually support:

``` json
{
  "schema_version": "1.0",
  "event_type": "EVENT_TYPE",
  "event_id": "UNIQUE_ID",
  "generated_at": "ISO_8601_UTC",
  "source": {
    "service": "SERVICE_NAME",
    "component": "COMPONENT_NAME"
  },
  "correlation_id": "TRACE_OR_REQUEST_ID",
  "payload": {}
}
```

Not every database row must physically store this exact wrapper.

It defines shared message semantics.

------------------------------------------------------------------------

# 26. Correlation ID

A `correlation_id` allows one end-to-end processing chain to be traced.

Example:

``` text
packet
→ C4
→ C1
→ Golden Timeline
→ C3
→ decision
→ command
```

------------------------------------------------------------------------

# 27. Transport Envelope vs Domain Payload

Keep:

``` text
transport metadata
```

separate from:

``` text
environmental measurements
```

This prevents RSSI/security metadata from being confused with physical
sensor values.

------------------------------------------------------------------------

# 28. Raw Telemetry Packet Contract

Conceptual normalized gateway-to-ingestion contract:

``` json
{
  "schema_version": "1.0",
  "packet_id": "PKT_...",
  "device_id": "PIPE_A1",
  "zone_id": "ZONE_01",
  "boot_id": "BOOT_...",
  "sequence_no": 1254,
  "observed_at": "2026-10-10T03:45:10.000Z",
  "received_at": "2026-10-10T03:45:10.250Z",
  "message_type": "TELEMETRY",
  "measurements": [],
  "device_health": {},
  "transport": {},
  "security": {}
}
```

Exact binary/JSON/CBOR on-radio encoding may differ.

------------------------------------------------------------------------

# 29. Raw Packet Preservation

The original received packet representation should be retained where
practical for:

``` text
audit
debugging
C4
reprocessing
research reproducibility
```

Normalized fields do not justify deleting original evidence.

------------------------------------------------------------------------

# 30. Measurement Entry

Conceptual:

``` json
{
  "sensor_instance_id": "SM_A1_01",
  "sensor_type": "SOIL_MOISTURE",
  "channel": "CH1",
  "raw_value": 2310,
  "value": 67.4,
  "unit": "CALIBRATED_UNIT",
  "calibration_version": "CAL_..."
}
```

`value` and `unit` must only claim a calibrated physical meaning when
justified.

------------------------------------------------------------------------

# 31. Sensor Types

Use a controlled registry rather than arbitrary strings.

Candidate categories include:

``` text
SOIL_MOISTURE
FSR_RESPONSE
AIR_TEMPERATURE
AIR_HUMIDITY
SOIL_TEMPERATURE
TILT
VIBRATION
RAINFALL
BAROMETRIC_PRESSURE
DEVICE_VOLTAGE
DEVICE_CURRENT
```

Final registry must match implemented hardware and calibration.

------------------------------------------------------------------------

# 32. Device Health Is Not Environmental Telemetry

Examples:

``` text
battery voltage
supply current
restart count
sensor read error
SD status
```

belong primarily to system-health/diagnostic context.

They should not automatically become C3 environmental features.

------------------------------------------------------------------------

# 33. Transport Metadata

Potential:

``` json
{
  "rssi_dbm": -92,
  "snr_db": 7.5,
  "retry_count": 0,
  "gateway_id": "GATEWAY_MAIN"
}
```

Primarily relevant to:

``` text
C2
C4
network diagnostics
```

------------------------------------------------------------------------

# 34. Security Metadata

Exact security fields depend on final protocol.

Conceptual:

``` json
{
  "credential_id": "...",
  "integrity_present": true,
  "freshness_counter": 1254,
  "session_id": "..."
}
```

Do not place secret keys in telemetry records/logs.

------------------------------------------------------------------------

# 35. Ingestion Output

Ingestion creates:

``` text
telemetry packet record
+
normalized sensor observations
```

before downstream ML decisions.

Ingestion must not silently discard an observation because it appears
abnormal.

------------------------------------------------------------------------

# 36. Sensor Observation Contract

Conceptual:

``` json
{
  "schema_version": "1.0",
  "observation_id": "OBS_...",
  "packet_id": "PKT_...",
  "zone_id": "ZONE_01",
  "device_id": "PIPE_A1",
  "sensor_instance_id": "SM_A1_01",
  "observed_at": "2026-10-10T03:45:10Z",
  "received_at": "2026-10-10T03:45:10.250Z",
  "raw_value": 2310,
  "value": 67.4,
  "unit": "CALIBRATED_UNIT",
  "calibration_version": "CAL_...",
  "source_origin": "PHYSICAL_DEMO"
}
```

------------------------------------------------------------------------

# 37. Source Origin

Canonical evidence-origin values:

``` text
PHYSICAL_DEMO
SYNTHETIC
EXTERNAL
SIMULATED
```

This describes evidence origin, not recovery provenance.

------------------------------------------------------------------------

# 38. C4 Input Boundary

C4 may consume:

``` text
packet identity
device identity
security verification results
sequence/freshness information
transport behaviour
timing behaviour
device/session metadata
```

C4 does not decide whether soil moisture is environmentally plausible.

------------------------------------------------------------------------

# 39. C4 Output Contract

Conceptual:

``` json
{
  "schema_version": "1.0",
  "assessment_id": "C4A_...",
  "packet_id": "PKT_...",
  "device_id": "PIPE_A1",
  "trust_label": "TRUSTED",
  "trust_score": 0.97,
  "mandatory_security_pass": true,
  "reason_codes": [
    "IDENTITY_VALID",
    "INTEGRITY_VALID",
    "FRESHNESS_VALID"
  ],
  "behavioural_score": 0.08,
  "model_version": "C4_MODEL_...",
  "generated_at": "2026-10-10T03:45:10.310Z"
}
```

Fields unavailable under the final C4 design may be nullable/omitted
according to schema.

------------------------------------------------------------------------

# 40. C4 Canonical Trust Labels

Baseline shared labels:

``` text
TRUSTED
SUSPICIOUS
UNTRUSTED
```

If C4 experiments use another internal taxonomy, integration must map it
to these shared semantics or formally version the contract.

------------------------------------------------------------------------

# 41. Mandatory Security Override

If a mandatory security property fails:

``` text
mandatory_security_pass = false
```

behavioural ML must not convert the packet to trusted.

------------------------------------------------------------------------

# 42. C4 Reason Codes

Prefer structured codes over free text.

Candidate examples:

``` text
IDENTITY_VALID
IDENTITY_UNKNOWN
INTEGRITY_VALID
INTEGRITY_FAILED
FRESHNESS_VALID
REPLAY_SUSPECTED
COUNTER_ROLLBACK
BEHAVIOURAL_ANOMALY
LOCATION_MISMATCH
RADIO_PROFILE_ANOMALY
```

Final list belongs to C4 implementation/schema version.

------------------------------------------------------------------------

# 43. C4 Processing Outcome

Downstream routing should distinguish:

``` text
ACCEPT
QUARANTINE
REJECT
```

from trust class if needed.

Example:

``` text
SUSPICIOUS → QUARANTINE/limited handling
```

Policy belongs to integration/security configuration.

------------------------------------------------------------------------

# 44. Untrusted Raw Data Preservation

Rejecting a packet from the trusted environmental pipeline does not mean
deleting it.

Retain appropriate evidence for:

``` text
audit
security analysis
testing
```

subject to storage/security policy.

------------------------------------------------------------------------

# 45. C1 Input Boundary

C1 consumes an eligible target observation plus context available at the
assessment time.

Potential context:

``` text
target value
history
neighbours
rainfall regime
device health
C4 trust context if explicitly included
```

------------------------------------------------------------------------

# 46. C1 Must Not Receive Future Context

At C1 assessment time `T`, context must satisfy runtime availability.

No future observations may be used.

------------------------------------------------------------------------

# 47. C1 Output Contract

Conceptual:

``` json
{
  "schema_version": "1.0",
  "assessment_id": "C1A_...",
  "observation_id": "OBS_...",
  "credibility_label": "VALID_EVENT",
  "confidence": 0.91,
  "class_probabilities": {
    "CLEAN": 0.06,
    "ANOMALY": 0.03,
    "VALID_EVENT": 0.91
  },
  "context_status": "COMPLETE",
  "reason_codes": [
    "RAINFALL_CONTEXT_SUPPORTS_CHANGE",
    "NEIGHBOURS_AGREE"
  ],
  "model_version": "C1_MODEL_...",
  "generated_at": "2026-10-10T03:45:10.390Z"
}
```

Probability fields are only used if the selected model/calibration
supports meaningful output.

------------------------------------------------------------------------

# 48. C1 Canonical Labels

Baseline:

``` text
CLEAN
ANOMALY
VALID_EVENT
```

These preserve the critical distinction between:

``` text
fault-like anomaly
```

and:

``` text
genuine extreme environmental event
```

------------------------------------------------------------------------

# 49. C1 Context Status

Candidate values:

``` text
COMPLETE
PARTIAL
INSUFFICIENT_CONTEXT
STALE_CONTEXT
```

This is separate from the credibility label.

------------------------------------------------------------------------

# 50. C1 Failure Status

A component execution status should not be encoded as a sensor class.

For example:

``` text
MODEL_UNAVAILABLE
INSUFFICIENT_DATA
SCHEMA_ERROR
```

must not become:

``` text
ANOMALY
```

------------------------------------------------------------------------

# 51. C1 Does Not Overwrite Observation

C1 attaches an assessment.

It must not mutate:

``` text
raw_value
original calibrated value
observed_at
packet provenance
```

------------------------------------------------------------------------

# 52. C2 Trigger Boundary

C2 may be triggered by:

``` text
expected report missing
late stream
device-health alarm
communication degradation
explicit diagnostic request
```

It does not need to wait for a C1 result when there is no observation to
classify.

------------------------------------------------------------------------

# 53. Expected Observation Contract

Logical representation:

``` json
{
  "schema_version": "1.0",
  "device_id": "PIPE_A1",
  "zone_id": "ZONE_01",
  "policy_version": "SP_...",
  "operating_mode": "RISK",
  "last_accepted_report_at": "2026-10-10T03:40:00Z",
  "expected_next_report_at": "2026-10-10T03:45:00Z",
  "deadline_at": "2026-10-10T03:45:30Z"
}
```

Exact interval/grace values come from active policy.

------------------------------------------------------------------------

# 54. Silence Event Contract

Conceptual:

``` json
{
  "schema_version": "1.0",
  "silence_event_id": "SIL_...",
  "zone_id": "ZONE_01",
  "device_id": "PIPE_A1",
  "detected_at": "2026-10-10T03:45:31Z",
  "expected_at": "2026-10-10T03:45:00Z",
  "deadline_at": "2026-10-10T03:45:30Z",
  "operating_mode": "RISK",
  "policy_version": "SP_...",
  "state": "CONFIRMED_SILENCE"
}
```

------------------------------------------------------------------------

# 55. Silence State

Conceptual state machine:

``` text
ON_TIME
LATE
SUSPECTED_SILENCE
CONFIRMED_SILENCE
DIAGNOSING
RECOVERING
RESOLVED
ESCALATED
```

Exact persisted implementation may refine this taxonomy.

------------------------------------------------------------------------

# 56. C2 Diagnosis Contract

Conceptual:

``` json
{
  "schema_version": "1.0",
  "diagnosis_id": "C2D_...",
  "silence_event_id": "SIL_...",
  "device_id": "PIPE_A1",
  "failure_type": "PRIMARY_SENSOR_FAILURE",
  "confidence": 0.88,
  "backup_verification_used": true,
  "evidence_codes": [
    "PRIMARY_MISSING",
    "HUB_REACHABLE",
    "BACKUP_RESPONDED"
  ],
  "recommended_action": "ACTIVATE_BACKUP_SENSOR",
  "model_version": "C2_MODEL_...",
  "generated_at": "2026-10-10T03:45:33Z"
}
```

------------------------------------------------------------------------

# 57. C2 Shared Failure Taxonomy

Existing datasets contain different naming levels.

Shared runtime taxonomy must be mapped explicitly.

Candidate high-level classes:

``` text
NORMAL
COMMUNICATION_FAILURE
HARDWARE_FAILURE
POSSIBLE_ZONE_DAMAGE
UNKNOWN
```

More specific internal diagnoses may include:

``` text
SENSOR_LINK_GAP
PRIMARY_SENSOR_FAILURE
MULTI_SENSOR_GAP
HUB_FAILURE
ZONE_NETWORK_FAILURE
```

The mapping must be documented rather than mixing the two taxonomies.

------------------------------------------------------------------------

# 58. C2 Action Taxonomy

Baseline actions:

``` text
REQUEST_SD_REPLAY
ACTIVATE_BACKUP_SENSOR
USE_NEIGHBOR_FUSION
SWITCH_BACKUP_HUB
ESCALATE
NO_ACTION
```

Action availability depends on actual hardware/topology.

------------------------------------------------------------------------

# 59. Recommended Action vs Executed Action

C2 can produce:

``` text
recommended_action
```

but the system must separately record:

``` text
executed_action
```

because policy/resource state may change the action.

------------------------------------------------------------------------

# 60. Recovery Event Contract

Conceptual:

``` json
{
  "schema_version": "1.0",
  "recovery_event_id": "REC_...",
  "silence_event_id": "SIL_...",
  "diagnosis_id": "C2D_...",
  "action": "REQUEST_SD_REPLAY",
  "started_at": "2026-10-10T03:45:34Z",
  "completed_at": "2026-10-10T03:45:38Z",
  "status": "SUCCESS",
  "recovered_count": 4
}
```

------------------------------------------------------------------------

# 61. Recovered Observation Contract

Conceptual:

``` json
{
  "schema_version": "1.0",
  "observation_id": "OBS_REC_...",
  "zone_id": "ZONE_01",
  "device_id": "PIPE_A1",
  "sensor_instance_id": "SM_A1_01",
  "observed_at": "2026-10-10T03:42:00Z",
  "received_at": "2026-10-10T03:45:37Z",
  "value": 68.1,
  "recovery_provenance": "LATE_ORIGINAL",
  "recovery_confidence": 1.0,
  "recovery_event_id": "REC_..."
}
```

A confidence of `1.0` is not automatically appropriate; shown only
illustratively.

------------------------------------------------------------------------

# 62. Recovery Provenance Enum

Baseline:

``` text
DIRECT
LATE_ORIGINAL
BACKUP
FUSED
DERIVED
```

`DIRECT` normally describes normal accepted observations, while the
others describe alternate/recovery origins.

------------------------------------------------------------------------

# 63. Authorized SD Replay

Historical replay must preserve:

``` text
original observed_at
original sequence/identity where available
new received_at
fresh authenticated recovery context
```

C4 must be able to distinguish authorized replay from malicious replay.

------------------------------------------------------------------------

# 64. Golden Timeline Purpose

The Golden Timeline is the downstream environmental history selected
after trust, credibility and recovery reasoning.

It is:

``` text
provenance-aware
quality-aware
time-aware
```

It is not a destructive replacement of raw data.

------------------------------------------------------------------------

# 65. Golden Observation Contract

Conceptual:

``` json
{
  "schema_version": "1.0",
  "golden_observation_id": "GOBS_...",
  "source_observation_id": "OBS_...",
  "zone_id": "ZONE_01",
  "device_id": "PIPE_A1",
  "sensor_instance_id": "SM_A1_01",
  "observed_at": "2026-10-10T03:45:10Z",
  "available_at": "2026-10-10T03:45:10.400Z",
  "value": 67.4,
  "unit": "CALIBRATED_UNIT",
  "recovery_provenance": "DIRECT",
  "trust_label": "TRUSTED",
  "credibility_label": "VALID_EVENT",
  "quality_score": 0.91,
  "is_estimated": false,
  "c4_assessment_id": "C4A_...",
  "c1_assessment_id": "C1A_...",
  "c2_recovery_event_id": null
}
```

------------------------------------------------------------------------

# 66. `available_at`

This is crucial for temporal research.

`available_at` means:

> earliest time this Golden Timeline value was legitimately available to
> downstream runtime processing.

For a late replay:

``` text
observed_at = old time
available_at = later recovery time
```

------------------------------------------------------------------------

# 67. Runtime As-Of Rule

For a forecast generated at time `T`:

``` text
Golden observation may be used only if
available_at <= T
```

even when:

``` text
observed_at <= T
```

This prevents retrospective leakage.

------------------------------------------------------------------------

# 68. Golden Timeline Selection

Selection logic may prefer:

``` text
trusted direct observation
```

over an estimate, while allowing recovery when direct data is absent.

Exact precedence should be encoded as versioned policy.

------------------------------------------------------------------------

# 69. Golden Timeline Does Not Erase Alternatives

If both:

``` text
backup value
late original
```

exist, retain their source records.

The Golden Timeline identifies the selected downstream representation,
not the only historical evidence.

------------------------------------------------------------------------

# 70. Quality Score

If a unified quality score is implemented, its derivation must be
versioned and documented.

Do not arbitrarily combine:

``` text
C4 trust_score
C1 confidence
C2 recovery_confidence
```

by multiplication or averaging without justification.

------------------------------------------------------------------------

# 71. C3 Input Contract

C3 consumes a versioned temporal feature sequence derived from
runtime-eligible Golden Timeline data.

Conceptual per-step structure:

``` json
{
  "time": "2026-10-10T03:45:00Z",
  "delta_t_seconds": 60,
  "operating_mode": "RISK",
  "features": {},
  "masks": {},
  "ages_seconds": {},
  "quality": {},
  "provenance": {}
}
```

------------------------------------------------------------------------

# 72. C3 Feature Schema Version

Every forecast records:

``` text
feature_schema_version
```

because model compatibility depends on:

``` text
feature names
ordering
units
normalization
windowing
```

------------------------------------------------------------------------

# 73. C3 Forecast Contract

Conceptual:

``` json
{
  "schema_version": "1.0",
  "forecast_id": "FC_...",
  "zone_id": "ZONE_01",
  "forecast_origin": "2026-10-10T03:45:40Z",
  "history_start": "2026-10-10T02:45:40Z",
  "history_end": "2026-10-10T03:45:40Z",
  "horizon_minutes": 15,
  "risk_probability": 0.73,
  "risk_class": "HIGH",
  "input_quality_status": "ADEQUATE",
  "model_version": "C3_MODEL_...",
  "feature_schema_version": "C3FS_...",
  "input_manifest_id": "FIM_...",
  "generated_at": "2026-10-10T03:45:40.120Z"
}
```

`risk_class` thresholds are policy/model-version dependent and not
frozen here.

------------------------------------------------------------------------

# 74. C3 Forecast Does Not Contain Final Mode Command

C3 may expose:

``` text
risk probability
risk class
forecast horizon
quality
```

but normal architecture does not let C3 directly command:

``` text
EMERGENCY mode
```

That belongs to the Decision Engine.

------------------------------------------------------------------------

# 75. Forecast Input Manifest

A forecast should be traceable to its inputs.

Conceptual manifest contains:

``` text
forecast_id
Golden observation IDs / feature-window reference
feature schema
mode history
quality/provenance summary
builder version
```

This supports reproducibility.

------------------------------------------------------------------------

# 76. C3 Insufficient Input

If C3 cannot make a reliable forecast because required history is
unavailable, return a processing status such as:

``` text
INSUFFICIENT_HISTORY
INSUFFICIENT_TRUSTED_DATA
FEATURE_BUILD_FAILED
MODEL_UNAVAILABLE
```

Do not fabricate a normal low-risk prediction.

------------------------------------------------------------------------

# 77. Decision Engine Input

Conceptually:

``` json
{
  "zone_id": "ZONE_01",
  "current_mode": "RISK",
  "forecast_id": "FC_...",
  "environmental_severity": {},
  "data_quality": {},
  "system_health": {},
  "security_state": {}
}
```

Exact policy features remain a dedicated implementation decision.

------------------------------------------------------------------------

# 78. Operating Mode Enum

Frozen names:

``` text
DEEP_SLEEP
IDLE
RISK
WARNING
EMERGENCY
```

Spelling/case should remain stable in shared interfaces.

------------------------------------------------------------------------

# 79. Mode Event Contract

Conceptual:

``` json
{
  "schema_version": "1.0",
  "mode_event_id": "MODE_...",
  "zone_id": "ZONE_01",
  "previous_mode": "RISK",
  "new_mode": "WARNING",
  "effective_at": "2026-10-10T03:45:41Z",
  "decision_id": "DEC_...",
  "policy_version": "DP_...",
  "reason_codes": [
    "FORECAST_RISK_THRESHOLD",
    "PERSISTENCE_MET"
  ]
}
```

------------------------------------------------------------------------

# 80. Decision Contract

Conceptual:

``` json
{
  "schema_version": "1.0",
  "decision_id": "DEC_...",
  "zone_id": "ZONE_01",
  "decision_type": "MODE_CHANGE",
  "previous_mode": "RISK",
  "selected_mode": "WARNING",
  "forecast_id": "FC_...",
  "policy_version": "DP_...",
  "reason_codes": [],
  "generated_at": "2026-10-10T03:45:40.500Z"
}
```

------------------------------------------------------------------------

# 81. Decision Policy Version

Every operational decision should identify the policy version.

This allows:

``` text
same forecast
+
different policy version
→ potentially different action
```

to be audited.

------------------------------------------------------------------------

# 82. Sampling Policy Contract

Conceptual:

``` json
{
  "policy_version": "SP_...",
  "mode": "RISK",
  "device_profile": "TYPE_A",
  "acquisition_profile": {},
  "aggregation_profile": {},
  "report_interval_seconds": null
}
```

Exact rates remain configurable until calibrated/tested.

------------------------------------------------------------------------

# 83. Device Command Contract

Conceptual:

``` json
{
  "schema_version": "1.0",
  "command_id": "CMD_...",
  "target_device_id": "PIPE_A1",
  "zone_id": "ZONE_01",
  "command_type": "APPLY_MODE",
  "requested_mode": "WARNING",
  "policy_version": "SP_...",
  "issued_at": "2026-10-10T03:45:41Z",
  "expires_at": "2026-10-10T03:46:41Z",
  "decision_id": "DEC_..."
}
```

Security/authentication fields are added by the final command protocol.

------------------------------------------------------------------------

# 84. Command Types

Candidate shared types:

``` text
APPLY_MODE
APPLY_SAMPLING_POLICY
REQUEST_STATUS
REQUEST_SD_REPLAY
ACTIVATE_BACKUP
DEACTIVATE_BACKUP
TRIGGER_ALERT_DEVICE
```

Only implemented/authorized commands should be enabled.

------------------------------------------------------------------------

# 85. Command Expiry

A delayed old command must not override a newer safety state.

Commands therefore need:

``` text
issued_at
expires_at
ordering/version information
```

as appropriate.

------------------------------------------------------------------------

# 86. Command Idempotency

Receiving the same command twice should not create unintended repeated
side effects.

`command_id` supports duplicate detection.

------------------------------------------------------------------------

# 87. Command ACK Contract

Conceptual:

``` json
{
  "schema_version": "1.0",
  "command_id": "CMD_...",
  "device_id": "PIPE_A1",
  "received_at": "2026-10-10T03:45:41.200Z",
  "applied_at": "2026-10-10T03:45:41.250Z",
  "status": "APPLIED",
  "active_mode": "WARNING",
  "active_policy_version": "SP_...",
  "reason_code": null
}
```

------------------------------------------------------------------------

# 88. ACK Status

Candidate:

``` text
RECEIVED
APPLIED
REJECTED
EXPIRED
UNSUPPORTED
FAILED
```

Do not treat radio receipt alone as proof that the device applied the
policy.

------------------------------------------------------------------------

# 89. Command Retry

Retries must reuse/relate to command identity so duplicate application
is controlled.

Exact retry strategy belongs to communication design.

------------------------------------------------------------------------

# 90. Local Fallback

If a device loses connection to the gateway, it needs defined local
behaviour.

Potential principles:

``` text
retain last valid policy for bounded period
enter configured safe fallback
continue local storage
report recovery when communication returns
```

Exact fallback differs by device role and must be tested.

------------------------------------------------------------------------

# 91. Alert Contract

Conceptual:

``` json
{
  "schema_version": "1.0",
  "alert_id": "ALT_...",
  "zone_id": "ZONE_01",
  "severity": "WARNING",
  "alert_type": "LANDSLIDE_RISK",
  "decision_id": "DEC_...",
  "message_code": "HIGH_NEAR_TERM_RISK",
  "created_at": "2026-10-10T03:45:42Z",
  "status": "ACTIVE"
}
```

Human-readable text can be generated separately.

------------------------------------------------------------------------

# 92. Alert Severity vs Operating Mode

They may share words such as:

``` text
WARNING
EMERGENCY
```

but they are different domains.

Prefer separate typed fields/enums:

``` text
operating_mode
alert_severity
```

to avoid accidental mixing.

------------------------------------------------------------------------

# 93. Processing Status

Shared service responses should distinguish processing state from
scientific class.

Candidate statuses:

``` text
OK
PARTIAL
INSUFFICIENT_DATA
INVALID_SCHEMA
UNSUPPORTED_VERSION
MODEL_UNAVAILABLE
DEPENDENCY_UNAVAILABLE
PROCESSING_ERROR
```

------------------------------------------------------------------------

# 94. Scientific Output vs Execution Failure

Never convert:

``` text
C1 model crashed
```

into:

``` text
ANOMALY
```

or:

``` text
C3 feature builder failed
```

into:

``` text
LOW risk
```

Execution failure must remain explicit.

------------------------------------------------------------------------

# 95. Error Contract

Conceptual:

``` json
{
  "status": "PROCESSING_ERROR",
  "error_code": "C3_FEATURE_BUILD_FAILED",
  "retryable": true,
  "correlation_id": "CORR_...",
  "generated_at": "..."
}
```

Avoid exposing secrets/internal stack traces to external consumers.

------------------------------------------------------------------------

# 96. Reason Codes

Use structured reason codes for:

``` text
security
credibility
diagnosis
decision
command failure
```

They improve:

``` text
testing
audit
analytics
viva evidence
```

Free-text explanations may accompany them.

------------------------------------------------------------------------

# 97. Schema Validation

Every shared message crossing a component boundary should be validated.

Validation includes:

``` text
required fields
types
enum values
timestamp format
numeric ranges where structurally valid
schema version
```

------------------------------------------------------------------------

# 98. Semantic Validation

Schema-valid data can still be semantically invalid.

Example:

``` text
observed_at > received_at
```

may be possible due to clock drift, but should be flagged/handled
according to clock-quality rules rather than silently accepted as
normal.

------------------------------------------------------------------------

# 99. Units

Every physical/calibrated variable requires an explicit unit definition.

Do not assume:

``` text
temperature = °C
rainfall = mm
FSR = N
```

without schema/calibration metadata.

------------------------------------------------------------------------

# 100. Unit Conversion

Conversion should occur in a shared tested layer.

Models must receive the units they were trained on.

Feature schema version should make this reproducible.

------------------------------------------------------------------------

# 101. Missing Value Representation

At software boundaries prefer explicit:

``` text
null
missing mask
status field
```

rather than magic numbers such as:

``` text
-999
```

unless a file format requires a sentinel and it is documented.

------------------------------------------------------------------------

# 102. Zero Is a Measurement

Never use:

``` text
0
```

to mean missing when zero is physically valid.

------------------------------------------------------------------------

# 103. Staleness

A value can exist but be too old for a current decision.

Therefore distinguish:

``` text
missing
```

from:

``` text
stale
```

C3 may receive age features.

------------------------------------------------------------------------

# 104. Cross-Component Execution Order

Normal accepted packet path:

``` text
Gateway
→ Ingestion
→ C4
→ C1
→ Golden Timeline update
→ C3 feature/window process
→ C3
→ Decision Engine
```

C2 is event-driven and can enter when expected information is missing.

------------------------------------------------------------------------

# 105. C2 Is Not Strictly Between C1 and C3

C2 may run:

``` text
without a new packet
```

because silence itself triggers it.

Its recovery outputs later influence the Golden Timeline and therefore
C3.

------------------------------------------------------------------------

# 106. Parallel/Asynchronous Processing

The implementation may use:

``` text
queues
events
workers
async tasks
```

but logical dependencies remain enforced.

Example:

C1 must not assess an observation as trusted environmental input before
required C4 gating semantics are satisfied.

------------------------------------------------------------------------

# 107. Eventual Consistency

Some derived records may appear after the raw record.

Consumers must not assume every assessment is immediately available.

Use:

``` text
status
timestamps
IDs
```

to resolve state.

------------------------------------------------------------------------

# 108. Idempotent Processing

Reprocessing the same event should not create uncontrolled duplicate
outputs.

Use stable source IDs and uniqueness constraints where appropriate.

------------------------------------------------------------------------

# 109. Exactly-Once Assumption

Do not design as if wireless/event delivery is magically exactly once.

Support:

``` text
duplicates
retries
late messages
out-of-order messages
```

------------------------------------------------------------------------

# 110. Late Packets

A late packet should:

``` text
remain stored
be security checked
be classified according to provenance/freshness context
update retrospective history if valid
```

but must not retroactively alter what a past forecast knew.

------------------------------------------------------------------------

# 111. Out-of-Order Packets

Ordering should use:

``` text
observed_at
sequence/session metadata
received_at
```

appropriately.

Do not simply sort all records by database insertion ID.

------------------------------------------------------------------------

# 112. Duplicate Packets

Duplicate transport receipt should not create multiple independent
physical observations unless evidence indicates they truly are separate
measurements.

------------------------------------------------------------------------

# 113. Data Quarantine

Suspicious/untrusted data can be stored in a quarantine/security path.

It should not silently enter the Golden Timeline.

------------------------------------------------------------------------

# 114. C1 Anomaly Handling

An observation labeled:

``` text
ANOMALY
```

should remain preserved but normally be excluded/down-weighted according
to Golden Timeline policy.

Exact downstream policy is versioned.

------------------------------------------------------------------------

# 115. C1 Valid Event Handling

`VALID_EVENT` means:

``` text
unusual but environmentally credible
```

and must not be filtered merely because it is extreme.

------------------------------------------------------------------------

# 116. C2 Estimated Recovery Handling

`FUSED` or `DERIVED` values must expose:

``` text
is_estimated = true
provenance
confidence/quality
```

so C3 can treat them differently.

------------------------------------------------------------------------

# 117. Model API Boundary

Each ML component should expose a stable internal interface independent
of the training framework.

Conceptual:

``` text
validate_input()
build_features()
predict()
postprocess()
return_contract()
```

This prevents the rest of GeoNex from depending directly on
XGBoost/PyTorch-specific objects.

------------------------------------------------------------------------

# 118. C1 Service Interface

Conceptually:

``` text
assess_observation(observation_id, as_of_time)
→ C1Assessment
```

Batch/offline equivalent:

``` text
assess_batch(records)
```

------------------------------------------------------------------------

# 119. C2 Service Interface

Conceptually:

``` text
diagnose_silence(silence_event_id)
→ C2Diagnosis
```

Recovery orchestration:

``` text
execute_recovery(diagnosis_id)
→ RecoveryEvent
```

These may be separate services/functions.

------------------------------------------------------------------------

# 120. C3 Service Interface

Conceptually:

``` text
forecast(zone_id, forecast_origin, horizon)
→ C3Forecast
```

The service builds/requests runtime-eligible features rather than
accepting arbitrary unvalidated CSV rows.

------------------------------------------------------------------------

# 121. C4 Service Interface

Conceptually:

``` text
assess_packet(packet_id)
→ C4TrustAssessment
```

Mandatory security verification may occur partly before the ML
behavioural layer.

------------------------------------------------------------------------

# 122. Decision Engine Interface

Conceptually:

``` text
evaluate_zone(zone_id, as_of_time)
→ Decision
```

It consumes approved component outputs through shared
repositories/contracts.

------------------------------------------------------------------------

# 123. Training Interfaces Are Separate

Runtime:

``` text
predict
```

must be separated from:

``` text
train
fit
tune
promote
```

No runtime request should silently retrain a model.

------------------------------------------------------------------------

# 124. Dataset Builder Boundary

Offline builders read versioned source snapshots and produce:

``` text
Parquet/CSV
manifest
split metadata
```

They do not change live operational records.

------------------------------------------------------------------------

# 125. Feature Builder Reuse

Where practical, share feature definitions between:

``` text
offline training
runtime inference
```

to reduce training-serving skew.

------------------------------------------------------------------------

# 126. Training-Serving Skew

This occurs when:

``` text
training feature calculation
≠
runtime feature calculation
```

Example:

training uses perfect future-filled values while runtime uses stale
observations.

Contract/versioning must prevent this.

------------------------------------------------------------------------

# 127. Model Compatibility Check

Before loading a model verify:

``` text
model_version
feature_schema_version
preprocessing version
required dependencies
```

Incompatible model/schema combinations must fail explicitly.

------------------------------------------------------------------------

# 128. Model Output Versioning

Changing:

``` text
class taxonomy
probability meaning
feature semantics
```

requires a compatible contract/model version update.

------------------------------------------------------------------------

# 129. Backward-Compatible Change

Examples may include:

``` text
adding optional metadata field
adding new reason code understood as unknown by old consumer
```

provided consumers tolerate it.

------------------------------------------------------------------------

# 130. Breaking Change

Examples:

``` text
rename device_id
change WARNING meaning
change observed_at semantics
remove required field
change risk probability definition
```

requires explicit schema version migration.

------------------------------------------------------------------------

# 131. Shared Contract Repository

Recommended conceptual location:

``` text
shared/
└── contracts/
    ├── telemetry/
    ├── c1/
    ├── c2/
    ├── c3/
    ├── c4/
    ├── decision/
    └── common/
```

Final repository structure is frozen later.

------------------------------------------------------------------------

# 132. Machine-Readable Schemas

Recommended implementation choices:

``` text
JSON Schema
Pydantic models
typed DTOs
```

depending on service language.

The schema should be generated/tested from one authoritative definition
where possible.

------------------------------------------------------------------------

# 133. Contract Tests

Each producer/consumer pair needs tests.

Example:

``` text
C1 emits VALID_EVENT
→ Golden Timeline accepts known enum

C1 emits typo VALID-EVENT
→ schema validation fails
```

------------------------------------------------------------------------

# 134. Mock Contracts

Component developers may use realistic mock objects before other
components are complete.

Mocks must conform to this shared contract.

Do not invent private fields and later expect integration to adapt
silently.

------------------------------------------------------------------------

# 135. Mock C4 Output for C1

Example:

``` json
{
  "packet_id": "PKT_TEST_001",
  "trust_label": "TRUSTED",
  "mandatory_security_pass": true,
  "model_version": "MOCK_C4_001"
}
```

Clearly mark mock provenance in test environments.

------------------------------------------------------------------------

# 136. Mock C1/C2 Output for C3

C3 development may use:

``` text
mock credibility
mock recovery provenance
```

but experiments claiming integrated performance must eventually use
leakage-safe real component outputs.

------------------------------------------------------------------------

# 137. Contract Test Environments

Recommended:

``` text
unit
component
integration
hardware-in-loop
end-to-end
```

Each tests different boundaries.

------------------------------------------------------------------------

# 138. Unit Test Example

C1:

``` text
given valid input schema
when prediction returns VALID_EVENT
then output contract contains observation_id + model_version
```

------------------------------------------------------------------------

# 139. Integration Test Example

``` text
trusted packet
→ normalized observation
→ C1 assessment
→ Golden observation
→ C3 feature
```

Verify IDs/timestamps/provenance survive.

------------------------------------------------------------------------

# 140. C2 Integration Test Example

``` text
RISK mode
→ expected report missed
→ silence event
→ backup responds
→ diagnosis
→ recovery
→ Golden Timeline
→ later C3 forecast
```

------------------------------------------------------------------------

# 141. C4 Replay Integration Test

Test both:

``` text
unauthorized replay
→ rejected/quarantined
```

and:

``` text
authorized C2 SD recovery replay
→ authenticated recovery path
→ accepted with historical provenance
```

------------------------------------------------------------------------

# 142. As-Of Leakage Test

Create:

``` text
observation observed at 10:00
received/recovered at 10:20
forecast origin 10:10
```

Expected:

``` text
observation MUST NOT enter 10:10 runtime feature set
```

This should be automated.

------------------------------------------------------------------------

# 143. Mode Command Test

``` text
Decision Engine issues WARNING
→ command transmitted
→ device ACK APPLIED
→ active policy recorded
→ expected-report scheduler uses WARNING policy
```

This verifies Decision Engine ↔ C2 timing integration.

------------------------------------------------------------------------

# 144. Stale Command Test

``` text
old RISK command arrives after newer WARNING command
```

Expected:

``` text
must not downgrade device incorrectly
```

according to command ordering/expiry policy.

------------------------------------------------------------------------

# 145. Component Timeout

If a component does not respond within operational limits:

``` text
do not fabricate its result
```

Use explicit degraded/error state and Decision Engine fallback policy.

Exact timeouts are configured later.

------------------------------------------------------------------------

# 146. C4 Unavailable

Possible system behaviour must be defined conservatively.

Do not automatically mark all packets:

``` text
TRUSTED
```

because C4 is unavailable.

------------------------------------------------------------------------

# 147. C1 Unavailable

Do not automatically mark observations:

``` text
CLEAN
```

Fallback may use deterministic plausibility/quality policy if approved.

------------------------------------------------------------------------

# 148. C2 Unavailable

Silence/recovery must not disappear from system awareness.

At minimum:

``` text
record failure
escalate/degrade
```

according to policy.

------------------------------------------------------------------------

# 149. C3 Unavailable

Do not return:

``` text
risk_probability = 0
```

Fallback Decision Engine may use current-state deterministic safety
rules.

------------------------------------------------------------------------

# 150. Database Transaction Boundary

Raw ingestion should not be lost because a downstream model fails.

Prefer:

``` text
persist raw
→ downstream processing
```

rather than one giant transaction requiring every ML component to
succeed.

------------------------------------------------------------------------

# 151. Audit Event

Important actions should produce audit evidence:

``` text
model loaded
packet quarantined
recovery started
mode changed
command rejected
model promoted
manual override
```

------------------------------------------------------------------------

# 152. Manual Override

If the system supports human override, record:

``` text
who/role
what
when
reason
previous state
new state
```

with appropriate authentication/authorization.

Exact UI is deferred.

------------------------------------------------------------------------

# 153. Privacy and Secrets

Do not log:

``` text
private keys
raw credentials
tokens
passwords
```

Shared contracts should reference secure credential IDs, not secrets.

------------------------------------------------------------------------

# 154. Logging Correlation

Logs should include where applicable:

``` text
correlation_id
packet_id
zone_id
device_id
component
model_version
```

without exposing secrets.

------------------------------------------------------------------------

# 155. Observability

Operational monitoring should track:

``` text
ingestion rate
packet loss
component errors
inference latency
queue backlog
model availability
command ACK rate
```

This is system health, not research target data.

------------------------------------------------------------------------

# 156. Latency Trace

Record stage timestamps to estimate:

``` text
radio
ingestion
C4
C1
C2
C3
decision
command/alert
```

latencies.

Do not infer end-to-end latency from model inference alone.

------------------------------------------------------------------------

# 157. Component Ownership

Each member owns implementation inside their component.

Shared contracts are team-owned.

A component owner may not independently change another component's
contract.

------------------------------------------------------------------------

# 158. Shared Architecture Change Procedure

If a change is required:

``` text
1. describe problem
2. identify affected contract
3. propose change
4. list affected components/data/tests
5. decide backward compatibility
6. approve as team
7. increment schema/version if required
8. update docs/schemas/tests
9. implement
```

------------------------------------------------------------------------

# 159. Contract Change Record

Recommended:

``` text
docs/architecture/changes/
```

Each record contains:

``` text
change ID
date
reason
old behaviour
new behaviour
affected modules
migration
approval
```

------------------------------------------------------------------------

# 160. Do Not Share Database Tables as APIs

Components should not depend casually on private table internals.

Use:

``` text
repository/service contracts
views
typed domain objects
```

where appropriate.

This reduces coupling.

------------------------------------------------------------------------

# 161. Database Remains Authoritative History

Events/messages may drive processing, but the operational database
preserves authoritative project history according to the data
architecture.

------------------------------------------------------------------------

# 162. Event Bus Is Optional

GeoNex can initially implement integration through:

``` text
service calls
database-backed jobs
local queues
```

without requiring a large distributed event platform.

The contract is independent of transport technology.

------------------------------------------------------------------------

# 163. Local Deployment Principle

Because GeoNex is initially a local edge system, avoid unnecessary
distributed-system complexity.

Use modular boundaries even if multiple services run on the same
computer.

------------------------------------------------------------------------

# 164. Recommended Initial Integration Style

Practical prototype:

``` text
PostgreSQL/TimescaleDB
+
Python services/modules
+
shared typed schemas
+
local job/event orchestration
+
ESP32 gateway interface
```

Exact framework remains an implementation decision.

------------------------------------------------------------------------

# 165. API Response Wrapper

If REST/internal HTTP is used, conceptual:

``` json
{
  "status": "OK",
  "data": {},
  "error": null,
  "correlation_id": "CORR_..."
}
```

Do not force this wrapper onto database/event storage if unnecessary.

------------------------------------------------------------------------

# 166. Health Endpoint

Each service should expose a simple health status if service-oriented
deployment is used:

``` text
service running
model loaded
database reachable
schema compatible
```

Health does not imply prediction quality.

------------------------------------------------------------------------

# 167. Readiness vs Liveness

Conceptually:

``` text
liveness
→ process is alive

readiness
→ process is ready to serve correctly
```

A C3 process can be alive but not ready if its model failed to load.

------------------------------------------------------------------------

# 168. Data Quality Status

Downstream objects may summarize input quality:

``` text
GOOD
DEGRADED
INSUFFICIENT
```

if the policy is explicitly defined.

Do not invent a vague score without derivation.

------------------------------------------------------------------------

# 169. Confidence Naming

Avoid using one generic `confidence` with different meanings across
every component without documentation.

Examples:

``` text
C1 class probability
C2 diagnosis confidence
C2 recovery confidence
C4 behavioural score
C3 risk probability
```

These are not interchangeable.

------------------------------------------------------------------------

# 170. Threshold Ownership

Thresholds belong to specific layers.

Examples:

``` text
C1 classification threshold → C1/model config
C4 trust threshold → C4/security policy
C3 risk-to-class threshold → model/Decision policy
mode transition threshold → Decision Engine
silence grace threshold → sampling/C2 policy
```

Do not duplicate them in multiple components.

------------------------------------------------------------------------

# 171. Configuration Versioning

Version important configuration:

``` text
sampling policy
decision policy
feature schema
calibration
security policy
```

so historical behavior can be reconstructed.

------------------------------------------------------------------------

# 172. Environment Configuration

Separate:

``` text
development
test
demo
production/field
```

configurations.

Do not train/test against hidden production credentials or hardcoded
endpoints.

------------------------------------------------------------------------

# 173. Time Zone Presentation

Store/process canonical timestamps unambiguously, preferably UTC.

Convert to local time only at:

``` text
UI
reports
human-readable exports
```

as required.

------------------------------------------------------------------------

# 174. Numeric Precision

Store sufficient precision to preserve sensor/model information.

Do not round aggressively during ingestion.

Presentation rounding belongs to UI/reporting.

------------------------------------------------------------------------

# 175. Raw ADC Preservation

Where relevant retain:

``` text
raw ADC
```

alongside calibrated/derived values.

This allows recalibration and audit.

------------------------------------------------------------------------

# 176. Calibration Change

New calibration must not rewrite historical raw values.

Derived recalibrated views/records can be generated with:

``` text
calibration_version
```

------------------------------------------------------------------------

# 177. Model Reprocessing

A new C1/C4 model may re-evaluate historical raw data for research.

This retrospective result must not overwrite the historical runtime
decision without version/provenance.

------------------------------------------------------------------------

# 178. Runtime vs Retrospective Assessment

Where needed record:

``` text
assessment_context = RUNTIME
```

or:

``` text
assessment_context = RETROSPECTIVE
```

to prevent research reprocessing from masquerading as historical runtime
state.

------------------------------------------------------------------------

# 179. Test Run Isolation

Physical/synthetic test records should carry:

``` text
test_run_id
source_origin
```

so controlled experiments can be separated from normal operational data.

------------------------------------------------------------------------

# 180. Synthetic Data Isolation

Synthetic packets must not accidentally enter live operational warning
logic.

Use environment/source controls.

------------------------------------------------------------------------

# 181. Dataset Export Boundary

Dataset exports may include:

``` text
identifiers
metadata
features
targets
provenance
split keys
```

but the dataset manifest must define field roles.

------------------------------------------------------------------------

# 182. No Target in Runtime Contract

Ground-truth research labels such as:

``` text
target_landslide_within_horizon
```

do not belong in normal runtime C3 input.

They exist for dataset evaluation.

------------------------------------------------------------------------

# 183. Ground Truth Contract

Research annotations should be stored separately:

``` json
{
  "annotation_id": "GT_...",
  "entity_type": "EVENT_OR_WINDOW",
  "entity_id": "...",
  "label": "...",
  "label_source": "...",
  "annotated_at": "...",
  "confidence": null
}
```

Exact annotation schema depends on component.

------------------------------------------------------------------------

# 184. Prediction Is Not Ground Truth

Never copy:

``` text
C1 prediction
```

into:

``` text
C1 ground truth label
```

without independent annotation.

The same applies to all components.

------------------------------------------------------------------------

# 185. Recommended Shared Enum Registry

Centralize definitions for:

``` text
OperatingMode
SourceOrigin
RecoveryProvenance
ProcessingStatus
C1CredibilityLabel
C4TrustLabel
C2FailureType
C2Action
CommandStatus
AlertSeverity
```

------------------------------------------------------------------------

# 186. Enum Migration

Removing/renaming an enum value is a breaking change unless a
compatibility mapping exists.

------------------------------------------------------------------------

# 187. Example End-to-End Normal Flow

``` text
1. PIPE_A1 reads sensors.
2. Device creates packet PKT_100.
3. Gateway receives packet.
4. Ingestion stores raw packet.
5. Observations OBS_101...OBS_105 created.
6. C4 creates C4A_100 → TRUSTED.
7. C1 evaluates eligible environmental observations.
8. C1 marks soil change VALID_EVENT.
9. Golden Timeline creates GOBS records.
10. C3 window builder updates ZONE_01 history.
11. C3 creates FC_100.
12. Decision Engine creates DEC_100.
13. Mode changes IDLE → RISK.
14. CMD_100 sent.
15. Device ACK confirms RISK policy applied.
16. Expected-observation scheduler now uses RISK timing.
```

------------------------------------------------------------------------

# 188. Example End-to-End Silence Flow

``` text
1. PIPE_A1 is operating under RISK policy.
2. Expected report deadline passes.
3. SIL_200 created.
4. C2 gathers health/network evidence.
5. Backup Pipe is queried.
6. Backup responds.
7. C2 creates diagnosis C2D_200.
8. Recovery action selected.
9. REC_200 executed.
10. Recovered observations retain provenance.
11. Golden Timeline updates.
12. C3 later consumes eligible recovered data.
13. Decision Engine can also react immediately to degradation.
```

------------------------------------------------------------------------

# 189. Example Security-Rejection Flow

``` text
1. Packet arrives claiming PIPE_A1.
2. C4 mandatory integrity/freshness check fails.
3. C4 output = UNTRUSTED.
4. Packet retained for audit/quarantine.
5. Environmental observations do not enter normal Golden Timeline.
6. Security/system-health state may inform Decision Engine.
```

------------------------------------------------------------------------

# 190. Example Authorized Historical Replay

``` text
1. C2 detects communication gap.
2. C2 requests SD replay using fresh authenticated command/session.
3. Device sends historical measurements.
4. C4 validates recovery authorization and packet security.
5. Historical observed_at values are preserved.
6. new received_at records replay arrival.
7. recovery_provenance = LATE_ORIGINAL.
8. retrospective Golden Timeline can include them.
9. past forecasts are NOT recomputed as if the data had arrived earlier.
```

------------------------------------------------------------------------

# 191. Example Genuine Extreme Event

``` text
soil moisture rises sharply
rainfall context is high
neighbours show compatible rise
C4 source is trusted
```

C1 may classify:

``` text
VALID_EVENT
```

The value remains eligible for C3 despite being extreme.

------------------------------------------------------------------------

# 192. Example Component Failure

``` text
C3 model file missing
```

Correct:

``` text
status = MODEL_UNAVAILABLE
Decision Engine invokes approved degraded policy
```

Incorrect:

``` text
risk_probability = 0.0
```

------------------------------------------------------------------------

# 193. Definition of Integration Success

Integration is successful when:

``` text
IDs remain traceable
timestamps retain meaning
raw data remains preserved
C4 gating is respected
C1 does not erase measurements
C2 recovery preserves provenance
Golden Timeline enforces as-of availability
C3 receives runtime-equivalent history
Decision Engine owns mode action
commands are acknowledged
errors remain explicit
schemas are versioned
```

------------------------------------------------------------------------

# 194. Mandatory Integration Tests Before Demo

At minimum:

-   [ ] normal trusted telemetry
-   [ ] duplicate packet
-   [ ] out-of-order packet
-   [ ] C4 rejected packet
-   [ ] C1 CLEAN
-   [ ] C1 ANOMALY
-   [ ] C1 VALID_EVENT
-   [ ] missing expected report
-   [ ] backup verification
-   [ ] SD replay
-   [ ] authorized replay vs malicious replay
-   [ ] recovered provenance
-   [ ] C3 normal forecast
-   [ ] C3 insufficient history
-   [ ] mode escalation
-   [ ] mode de-escalation/hysteresis
-   [ ] lost command
-   [ ] duplicate command
-   [ ] stale command
-   [ ] ACK failure
-   [ ] component unavailable
-   [ ] as-of leakage test
-   [ ] full end-to-end trace

------------------------------------------------------------------------

# 195. Member Rule

Each member's AI/development workspace must be given this instruction:

> **Do not redesign shared GeoNex IDs, timestamps, operating modes,
> component boundaries, Golden Timeline semantics, provenance fields,
> command semantics or cross-component contracts. Implement your
> component against the shared integration contract. If a change is
> necessary, propose it through the GeoNex shared architecture change
> procedure before modifying shared behaviour.**

------------------------------------------------------------------------

# 196. What Is Frozen by Document 11

The following are shared integration invariants:

1.  Stable canonical entity IDs are used across components.
2.  `observed_at`, `received_at`, `ingested_at`, `processed_at` and
    `generated_at` have different meanings.
3.  Shared timestamps are unambiguous/timezone-aware.
4.  Raw packets and normalized observations remain preserved.
5.  Packet identity and observation identity are distinct.
6.  C4 assesses source/transmission trust.
7.  C1 assesses measurement credibility.
8.  C2 may trigger independently when expected telemetry is absent.
9.  C2 diagnosis and recovery are separate concepts.
10. Recovery provenance is explicit.
11. Authorized historical replay is distinguishable from malicious
    replay.
12. Golden Timeline values carry provenance/quality/trust context.
13. `available_at` controls runtime as-of eligibility.
14. Retrospectively recovered data cannot leak into past forecasts.
15. C3 consumes versioned temporal features derived from eligible Golden
    Timeline history.
16. C3 forecast is not a device command.
17. Decision Engine owns mode/action policy.
18. Operating modes are exactly `DEEP_SLEEP`, `IDLE`, `RISK`, `WARNING`,
    `EMERGENCY`.
19. Device commands have identity, timing and acknowledgement semantics.
20. Scientific class and execution status are separate.
21. Missing and zero are different.
22. Stale and missing are different.
23. Prediction and ground truth are separate.
24. Models and feature schemas are versioned.
25. Shared messages/contracts are schema-versioned.
26. Duplicate/late/out-of-order events must be handled.
27. Component failure cannot silently become a safe/normal prediction.
28. Shared contract changes require coordinated review/versioning.
29. Mocks must conform to the same contract.
30. Integration tests must verify provenance, timing and failure
    semantics.

------------------------------------------------------------------------

# 197. Decisions Still Deferred

This document intentionally does **not** freeze:

``` text
exact radio packet binary encoding
exact REST framework
exact message queue/event-bus technology
exact UUID/ID-generation library
final cryptographic protocol
final security reason-code list
final sensor-unit registry
final C2 fine-grained failure taxonomy
exact quality-score formula
exact risk-class thresholds
exact sampling intervals
exact command retry counts/timeouts
exact local fallback durations
final SQL DDL
final API route names
final repository implementation structure
```

These must be finalized through implementation/security/testing work
without violating the shared semantics above.

------------------------------------------------------------------------

# 198. Next Document

Next:

``` text
12_GEONEX_TESTING_AND_VALIDATION_PLAN.md
```

It should define the complete evidence strategy across:

``` text
sensor calibration tests
firmware tests
LoRa/network tests
database tests
C1 experiments
C2 experiments
C3 experiments
C4 experiments
contract tests
integration tests
hardware-in-loop tests
failure injection
security tests
adaptive-sampling tests
latency tests
resource/power tests
end-to-end scenarios
acceptance criteria
research evidence collection
demo validation
```

The objective is to convert the architecture into a defensible,
repeatable validation program rather than a one-time demonstration.

------------------------------------------------------------------------

# Document 11 Status

**`11_GEONEX_INTEGRATION_CONTRACT.md` --- SHARED INTEGRATION BASELINE v1
READY**

The most important implementation rule is:

``` text
RAW EVIDENCE IS PRESERVED
        ↓
EVERY DERIVED DECISION IS TRACEABLE
        ↓
RECOVERY NEVER HIDES ITS PROVENANCE
        ↓
PAST FORECASTS ONLY USE WHAT WAS AVAILABLE AT THAT TIME
        ↓
MODE/ACTION POLICY REMAINS OUTSIDE THE PREDICTIVE MODEL
```
