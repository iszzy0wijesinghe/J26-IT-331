# 08_C4_DEVELOPMENT_GUIDE.md

**Project:** GeoNex --- Smart Landslide Early Warning Prediction System
using IoT, Edge AI and Risk Analytics\
**Component:** C4 --- Trusted Telemetry Provenance and Device
Attestation\
**Document:** Component Development Guide\
**Status:** Implementation Baseline\
**Depends on:** Documents 00--07\
**Primary purpose:** Define a complete, research-defensible
implementation path for C4 so GeoNex can distinguish legitimate
telemetry from untrusted, replayed, spoofed, cloned, tampered, or
behaviorally abnormal telemetry without incorrectly treating machine
learning as a replacement for cryptographic security.

------------------------------------------------------------------------

# 1. Component Mission

C4 answers:

> **Can GeoNex trust the source and transmission context of this
> telemetry enough to allow it into downstream environmental
> reasoning?**

C4 protects the boundary between:

``` text
physical IoT devices
        ↓
wireless/wired telemetry
        ↓
GeoNex analytical pipeline
```

Its responsibility combines:

``` text
device identity
+
registration
+
authentication/integrity
+
freshness/replay protection
+
provenance
+
behavioural anomaly detection
+
trust fusion
+
quarantine/audit
```

------------------------------------------------------------------------

# 2. C4's Position in GeoNex

Primary received-packet flow:

``` text
Sensor/Hub
    ↓
Gateway
    ↓
Raw immutable ingestion
    ↓
C4 deterministic security verification
    ↓
C4 behavioural assessment
    ↓
trust decision
    ├── eligible → C1
    └── quarantine/restrict → audit / security handling
```

Raw evidence is retained even when a packet is rejected from
environmental use.

------------------------------------------------------------------------

# 3. C4 Is Not C1

C4 asks:

``` text
Did this information come from a legitimate source
through an acceptable transmission/security context?
```

C1 asks:

``` text
Is the environmental measurement itself credible
given rainfall, history, neighbours and plausibility?
```

Example:

``` text
legitimate A1 device
+
faulty soil sensor
```

may produce:

``` text
C4 = trusted source
C1 = anomalous measurement
```

Conversely:

``` text
spoofed device
+
plausible soil value
```

may produce:

``` text
C4 = untrusted source
```

before C1 accepts it.

------------------------------------------------------------------------

# 4. C4 Is Hybrid by Design

C4 must not make all security decisions with ML.

Correct conceptual architecture:

``` text
DETERMINISTIC SECURITY GATE
identity / registration / authentication / integrity / freshness
        ↓
BEHAVIOURAL ML
transmission/device anomaly assessment
        ↓
TRUST FUSION
        ↓
Trusted / Suspicious / Untrusted
```

------------------------------------------------------------------------

# 5. Non-Negotiable Security Principle

> **A machine-learning trust score must never override a failed
> mandatory cryptographic or integrity requirement.**

For example:

``` text
signature/authentication invalid
```

cannot become:

``` text
trusted
```

because a classifier outputs `0.98 trusted`.

------------------------------------------------------------------------

# 6. Research Problem

Cryptographic verification can determine whether mandatory security
properties hold, but valid credentials alone may not reveal every
abnormal device/transmission behaviour.

Examples include:

``` text
compromised legitimate device
cloned behavioural identity
unexpected location/path
abnormal packet timing
unusual retry/radio behaviour
suspicious transmission pattern
```

C4 investigates whether deterministic security controls combined with
behavioural telemetry analysis improve detection and provenance
assurance beyond either approach alone.

------------------------------------------------------------------------

# 7. Research Question

Recommended:

> **Can a hybrid telemetry-trust framework combining deterministic
> device/security verification with behavioural anomaly classification
> improve detection of suspicious IoT telemetry while preserving
> explainable provenance for a landslide early-warning network?**

------------------------------------------------------------------------

# 8. Research Hypothesis

> **Mandatory deterministic verification combined with learned
> behavioural context will identify a broader set of untrusted or
> suspicious telemetry conditions than deterministic registration checks
> or behavioural ML alone, while retaining explicit reasons for every
> trust decision.**

This must be tested experimentally.

------------------------------------------------------------------------

# 9. C4 Research Contribution

The strongest contribution is:

``` text
PROVABLE SECURITY CONDITIONS
        +
BEHAVIOURAL TELEMETRY EVIDENCE
        +
EXPLICIT TRUST FUSION
        +
PROVENANCE/AUDIT
```

not:

``` text
"We trained XGBoost for cybersecurity."
```

------------------------------------------------------------------------

# 10. C4 Must Not Claim

Do not claim that C4:

-   proves a sensor measurement is environmentally correct;
-   predicts landslide risk;
-   repairs missing values;
-   replaces cryptographic authentication with AI;
-   provides perfect intrusion detection;
-   can identify every zero-day attack;
-   proves physical device identity solely from RSSI;
-   makes LoRa inherently secure merely by using it.

------------------------------------------------------------------------

# 11. Threat Model Must Be Written First

Before final model training, create:

``` text
C4_THREAT_MODEL.md
```

For every threat define:

``` text
asset
adversary capability
attack path
observable evidence
deterministic protection
ML-relevant evidence
expected response
limitations
```

------------------------------------------------------------------------

# 12. Assets to Protect

At minimum:

``` text
device identity
telemetry integrity
telemetry freshness
sequence continuity
sensor provenance
mode/control messages
recovery requests
historical replay authorization
model/decision input eligibility
audit records
```

------------------------------------------------------------------------

# 13. Candidate Threats

Research/test scenarios may include:

``` text
unknown device
spoofed device identifier
invalid authentication
payload tampering
unauthorized replay
duplicate sequence
stale packet
counter rollback
cloned identity behaviour
unexpected gateway/location path
abnormal packet interval
abnormal packet size
abnormal retry behaviour
abnormal RSSI/SNR pattern
firmware/state inconsistency
```

Only claim threats actually implemented/tested.

------------------------------------------------------------------------

# 14. Device Registration

Every operational device should have a registry record describing:

``` text
device_id
device_type
zone
expected role
registration status
approved configuration/firmware metadata where implemented
security identity/reference
lifecycle state
```

Exact credential fields are deferred to the security implementation
specification.

------------------------------------------------------------------------

# 15. Stable Identity

Do not rely solely on:

``` text
human-readable device name
```

such as `A1`.

The runtime needs a stable device identity linked to registration.

Human-readable aliases remain metadata.

------------------------------------------------------------------------

# 16. Identity Lifecycle

Support conceptual states such as:

``` text
PROVISIONED
ACTIVE
SUSPENDED
REVOKED
RETIRED
```

Exact enum can be finalized in the integration/security contract.

------------------------------------------------------------------------

# 17. Key/Credential Handling

Secrets must not be:

``` text
committed to Git
printed in logs
stored in public dataset exports
hard-coded in shared source
```

Use environment/provisioning mechanisms appropriate to the prototype.

------------------------------------------------------------------------

# 18. Cryptographic Algorithm Selection

This guide deliberately does **not** freeze:

``` text
exact cipher
exact MAC/signature algorithm
exact key-exchange mechanism
```

Those choices require compatibility, performance and threat-model
review.

The invariant is that mandatory authentication/integrity cannot be
replaced by behavioural ML.

------------------------------------------------------------------------

# 19. Packet Security Evidence

Conceptually C4 may evaluate:

``` text
device registered?
identity valid?
authentication valid?
integrity valid?
sequence acceptable?
freshness acceptable?
replay detected?
firmware/config approved?
```

Only implemented checks should appear as production fields.

------------------------------------------------------------------------

# 20. Freshness

A packet can be authentic yet stale.

Freshness mechanisms may use:

``` text
sequence/counter
nonce/challenge
timestamp within policy
session state
```

depending on the final protocol.

------------------------------------------------------------------------

# 21. Replay Attack

Unauthorized replay means previously legitimate data is resent outside
an authorized recovery context.

Potential evidence:

``` text
reused nonce
duplicate sequence
counter rollback
unexpected old observed_at
duplicate authenticated payload
```

------------------------------------------------------------------------

# 22. Authorized C2 Replay

C2 may legitimately request historical observations from local storage.

Therefore C4 must distinguish:

``` text
MALICIOUS REPLAY
```

from:

``` text
AUTHORIZED RECOVERY REPLAY
```

Conceptually, authorized recovery should bind the replay to:

``` text
recovery_request_id
authorized device
authorized time/sequence range
fresh authenticated response context
```

------------------------------------------------------------------------

# 23. C2 Cannot Disable Replay Protection

Incorrect:

``` text
if C2 requested data:
    skip C4
```

Correct:

``` text
C2 creates authorized recovery context
        ↓
device sends historical data under valid current security context
        ↓
C4 verifies identity/integrity
        ↓
C4 verifies replay authorization
        ↓
historical observed_at retained
```

------------------------------------------------------------------------

# 24. Sequence Number Semantics

C4 must account for:

``` text
normal increment
duplicate
gap
rollback
device reboot/session reset
```

A sequence reset after a legitimate reboot is not automatically an
attack.

Session/boot identity can help distinguish them.

------------------------------------------------------------------------

# 25. Clock Uncertainty

Timestamp-based freshness requires clock quality.

Record:

``` text
clock source
sync status
clock uncertainty where feasible
```

Do not reject legitimate packets solely because low-cost IoT clocks
drift unless the protocol accounts for drift.

------------------------------------------------------------------------

# 26. Deterministic Gate

Recommended conceptual result:

``` text
PASS
FAIL
INDETERMINATE
```

with reason codes.

Example failures:

``` text
UNKNOWN_DEVICE
AUTHENTICATION_FAILED
INTEGRITY_FAILED
UNAUTHORIZED_REPLAY
REVOKED_DEVICE
```

------------------------------------------------------------------------

# 27. Deterministic Fail-Closed Conditions

Mandatory security failures should normally make telemetry:

``` text
ineligible for environmental downstream use
```

while still retaining the packet/evidence for audit.

Exact availability-vs-security policy must be documented.

------------------------------------------------------------------------

# 28. Behavioural Layer

Only after deterministic evidence is represented should C4 analyze
behavioural context.

Candidate question:

> Does this packet/device behave consistently with legitimate operation,
> or does its transmission/device behaviour resemble
> suspicious/untrusted patterns?

------------------------------------------------------------------------

# 29. Existing C4 Dataset Concept

Existing work refers to:

``` text
C4_Trust.csv
```

with candidate evidence such as:

``` text
registered device
certificate/identity approval
firmware approval
signature/integrity validation
nonce reuse
counter/freshness
RSSI deviation
SNR
retries
packet delay
packet size
packet interval
hub/location consistency
restart/fault indicators
```

and targets such as:

``` text
Trusted
Suspicious
Untrusted
```

plus:

``` text
label_untrusted_binary
```

This dataset must be audited before final training.

------------------------------------------------------------------------

# 30. First C4 Data Task

Create:

``` text
C4_DATASET_AUDIT.md
```

Check:

``` text
target-generation logic
security-field leakage
scenario duplication
device-ID shortcut
attack-template duplication
time leakage
class balance
synthetic/physical origin
feature availability
```

------------------------------------------------------------------------

# 31. Critical Leakage Risk

Suppose:

``` text
label_untrusted_binary = 1
```

whenever:

``` text
signature_valid = 0
```

and then the model receives:

``` text
signature_valid
```

as an input.

The classifier can trivially recover the labeling rule.

That does not demonstrate behavioural anomaly intelligence.

------------------------------------------------------------------------

# 32. Separate Security Evidence from Behavioural ML

Recommended datasets:

``` text
C4-A Deterministic Verification Evidence
C4-B Behavioural ML Dataset
```

C4-A is primarily rule/security evidence.

C4-B is used to evaluate learned behavioural detection.

Trust fusion combines them at runtime.

------------------------------------------------------------------------

# 33. C4-A Deterministic Evidence

Conceptual fields:

``` text
packet_id
device_id
registered
lifecycle_status
authentication_valid
integrity_valid
freshness_valid
sequence_valid
authorized_replay
firmware/config approval where implemented
deterministic_result
reason_codes
```

This is not necessarily a machine-learning dataset.

------------------------------------------------------------------------

# 34. C4-B Behavioural Features

Candidate families:

``` text
B0 — timing
B1 — radio/link
B2 — packet/sequence behaviour
B3 — device-health behaviour
B4 — path/location consistency
B5 — historical behavioural profile
```

------------------------------------------------------------------------

# 35. B0 --- Timing Features

Candidate:

``` text
packet_interval_s
interval_deviation
delivery_delay
jitter
unexpected transmission time
mode-adjusted interval deviation
```

Expected interval must account for operating mode.

------------------------------------------------------------------------

# 36. B1 --- Radio Features

Where exposed:

``` text
RSSI
RSSI deviation from device baseline
SNR
SNR deviation
retry count
packet-loss context
```

RSSI is noisy and environment-dependent.

It is behavioural evidence, not proof of physical identity.

------------------------------------------------------------------------

# 37. B2 --- Packet Behaviour

Potential:

``` text
packet size
message type
sequence gap
duplicate frequency
counter behaviour
burst rate
unexpected message frequency
```

Do not duplicate deterministic replay verdict directly into the ML
feature set unless explicitly testing a fusion model.

------------------------------------------------------------------------

# 38. B3 --- Device Health Behaviour

Potential:

``` text
restart frequency
boot/session changes
fault flags
power behaviour
unexpected firmware/config state
```

Some may also support C2.

Shared evidence should have one canonical source.

------------------------------------------------------------------------

# 39. B4 --- Path / Location Consistency

Potential:

``` text
expected zone
expected hub/gateway path
observed receiving gateway
location/path mismatch
```

Only use location features that the actual deployment can observe.

Do not imply precise geolocation from LoRa RSSI alone.

------------------------------------------------------------------------

# 40. B5 --- Historical Profile

Potential:

``` text
rolling interval mean/std
rolling RSSI/SNR profile
normal retry distribution
normal packet-size distribution
normal active-mode behaviour
```

All rolling features must be causal.

------------------------------------------------------------------------

# 41. Mode-Aware Behaviour

A device transmitting rapidly in WARNING may be normal.

The same rate in DEEP_SLEEP may be unusual.

Therefore behavioural features should consider:

``` text
active acknowledged sampling policy
```

where appropriate.

------------------------------------------------------------------------

# 42. Trust Labels

Conceptual:

``` text
TRUSTED
SUSPICIOUS
UNTRUSTED
```

These need a formal labeling specification.

Create:

``` text
C4_TRUST_LABEL_SPECIFICATION.md
```

------------------------------------------------------------------------

# 43. Trusted

Meaning:

> Mandatory security checks pass and available behavioural evidence is
> consistent with expected legitimate operation.

This does not mean the environmental measurement is correct.

------------------------------------------------------------------------

# 44. Suspicious

Meaning:

> Mandatory checks have not established a hard rejection, but
> behavioural or contextual evidence is sufficiently abnormal to require
> caution, further verification, reduced eligibility, or investigation.

Exact runtime treatment is policy-controlled.

------------------------------------------------------------------------

# 45. Untrusted

Meaning:

> A mandatory security condition failed or sufficiently strong
> evidence/policy determines the telemetry is not eligible for normal
> downstream environmental use.

Reason codes are mandatory.

------------------------------------------------------------------------

# 46. Binary Label

`label_untrusted_binary` can support binary experiments:

``` text
0 = trusted/allowed class according to experiment
1 = untrusted
```

But mapping of `SUSPICIOUS` must be explicitly documented.

Do not silently merge it differently across experiments.

------------------------------------------------------------------------

# 47. Label Provenance

Each labeled record/scenario should identify:

``` text
label source
attack/test scenario
manual/rule/synthetic annotation
confidence where relevant
```

------------------------------------------------------------------------

# 48. Scenario IDs

Every attack/fault simulation should have:

``` text
scenario_id
```

All records from the same scenario must stay in one
train/validation/test partition.

------------------------------------------------------------------------

# 49. Attack Template Leakage

If the same replay script with nearly identical parameters appears in
train and test, high accuracy may only show memorization.

Hold out:

``` text
entire attack runs
parameter ranges
devices
or attack templates
```

where possible.

------------------------------------------------------------------------

# 50. Device Shortcut Leakage

Do not let the model learn:

``` text
device BK1 = suspicious
```

because attacks were generated only on BK1.

Distribute scenarios across devices or hold out devices.

Device identity should generally be metadata, not a direct ML feature.

------------------------------------------------------------------------

# 51. Time-Aware Split

For physical telemetry, later time periods can provide deployment-like
evaluation.

Do not randomly split adjacent packets from the same behavioural
episode.

------------------------------------------------------------------------

# 52. Supervised Baseline --- Logistic Regression

Useful for:

``` text
interpretable linear behavioural baseline
```

after appropriate preprocessing.

------------------------------------------------------------------------

# 53. Supervised Baseline --- Random Forest

Strong classical baseline for mixed nonlinear behavioural features.

------------------------------------------------------------------------

# 54. Candidate --- XGBoost / LightGBM

A boosted-tree model is a strong candidate for supervised C4 behavioural
classification.

Final selection must be experimental.

------------------------------------------------------------------------

# 55. Unsupervised Candidate --- Isolation Forest

Useful if:

``` text
trusted/normal telemetry is abundant
attack labels are limited
```

Train primarily on normal behaviour and evaluate against held-out
anomalies.

------------------------------------------------------------------------

# 56. Other Anomaly Methods

Potential alternatives:

``` text
One-Class SVM
autoencoder
```

but only add them if they answer a useful research question.

Do not create an unnecessarily large model comparison.

------------------------------------------------------------------------

# 57. Recommended C4 Model Study

Core:

``` text
deterministic-only
behavioural Logistic/RF baseline
behavioural boosted tree
Isolation Forest anomaly baseline
hybrid deterministic + selected behavioural model
```

This directly tests the hybrid contribution.

------------------------------------------------------------------------

# 58. Mandatory C4 Ablation

Recommended:

``` text
A0 — registration/basic deterministic identity
A1 — + integrity/authentication/freshness
A2 — behavioural ML only
A3 — deterministic + behavioural
A4 — + mode-aware behavioural context
```

Compare detection and false positives.

------------------------------------------------------------------------

# 59. Deterministic vs ML Metrics

Do not collapse all results into one classifier score.

Measure deterministic controls separately:

``` text
mandatory violation detection rate
unauthorized replay rejection
unknown-device rejection
```

and behavioural model separately:

``` text
precision
recall
F1
PR-AUC
ROC-AUC
```

------------------------------------------------------------------------

# 60. Security-Relevant Errors

Critical:

``` text
UNTRUSTED → TRUSTED
```

is a false acceptance.

Also important:

``` text
TRUSTED → UNTRUSTED
```

is a false rejection that can reduce system availability.

Report both.

------------------------------------------------------------------------

# 61. Suspicious-Class Evaluation

For three-class classification:

``` text
macro-F1
per-class precision/recall/F1
confusion matrix
```

are important.

Accuracy alone is insufficient.

------------------------------------------------------------------------

# 62. Calibration

If behavioural probability contributes to trust fusion, evaluate
probability calibration.

Do not interpret raw classifier scores as exact trust probabilities
without evidence.

------------------------------------------------------------------------

# 63. Trust Fusion

Recommended conceptual logic:

``` text
if mandatory deterministic failure:
    UNTRUSTED
else:
    behavioural assessment
        ↓
    TRUSTED / SUSPICIOUS / UNTRUSTED according to policy
```

The exact thresholds are deferred.

------------------------------------------------------------------------

# 64. Hard vs Soft Evidence

Hard evidence examples:

``` text
invalid authentication
failed integrity
revoked identity
unauthorized replay
```

Soft evidence examples:

``` text
unusual RSSI
unexpected packet timing
high retries
unusual path
```

Hard failures should dominate.

------------------------------------------------------------------------

# 65. Reason Codes

Every C4 result should include machine-readable reasons.

Examples:

``` text
REGISTERED_DEVICE
AUTH_OK
INTEGRITY_OK
FRESHNESS_OK
BEHAVIOUR_INTERVAL_ANOMALY
RSSI_PROFILE_ANOMALY
UNEXPECTED_PATH
UNAUTHORIZED_REPLAY
```

Exact enum is finalized later.

------------------------------------------------------------------------

# 66. Trust Score vs Trust Class

If a numerical score is used, distinguish:

``` text
behavioural anomaly score
```

from:

``` text
final trust class
```

A final security decision should not be represented as an unexplained
single floating-point number.

------------------------------------------------------------------------

# 67. Quarantine

Rejected/suspicious telemetry should not simply disappear.

Conceptually:

``` text
raw packet retained
C4 result retained
reason retained
downstream eligibility restricted
```

This enables:

``` text
audit
incident analysis
model improvement
```

------------------------------------------------------------------------

# 68. Raw Immutability

C4 must never modify the raw packet to make it appear valid.

Store:

``` text
raw evidence
+
C4 assessment
```

separately.

------------------------------------------------------------------------

# 69. Provenance Chain

For an accepted environmental observation, GeoNex should be able to
trace:

``` text
observation
→ packet
→ device
→ registration/security result
→ C4 assessment
→ C1 assessment
→ Golden Timeline
→ C3 forecast
```

This is central to trusted telemetry provenance.

------------------------------------------------------------------------

# 70. C4 Output Contract

Conceptually:

``` json
{
  "packet_id": "...",
  "device_id": "Z01-A01",
  "deterministic_result": "PASS",
  "behavioural_class": "TRUSTED",
  "behavioural_score": 0.04,
  "final_trust_class": "TRUSTED",
  "reason_codes": ["AUTH_OK", "FRESHNESS_OK"],
  "model_version": "...",
  "generated_at": "..."
}
```

Exact schema belongs to the integration contract.

------------------------------------------------------------------------

# 71. C4 Failure Contract

Example:

``` json
{
  "packet_id": "...",
  "device_id": "Z01-A01",
  "deterministic_result": "FAIL",
  "final_trust_class": "UNTRUSTED",
  "reason_codes": ["UNAUTHORIZED_REPLAY"],
  "eligible_for_environmental_use": false
}
```

Behavioural ML cannot reverse this.

------------------------------------------------------------------------

# 72. C1 Interaction

C1 should receive only telemetry eligible according to the agreed C4
policy, plus trust metadata if useful.

C1 does not redo authentication.

------------------------------------------------------------------------

# 73. C2 Interaction

C2 uses C4 context when diagnosing silence/recovery.

Examples:

``` text
packet missing because security rejected repeated unauthorized replay
```

differs from:

``` text
device completely silent
```

C2 must preserve the distinction.

------------------------------------------------------------------------

# 74. C2 Recovery Replay Interaction

C4 needs an explicit authorized-replay path.

This is a major cross-component integration test.

------------------------------------------------------------------------

# 75. C3 Interaction

C3 normally consumes Golden Timeline rather than raw C4 packet features.

Potential summarized quality information may flow downstream through
Golden provenance.

Do not flood C3 with raw cybersecurity features unless research
justifies it.

------------------------------------------------------------------------

# 76. Decision Engine Interaction

C4 may generate system degradation/security events such as:

``` text
device quarantined
multiple devices untrusted
gateway security concern
```

The Decision Engine decides operational consequences.

C4 does not independently redefine landslide risk.

------------------------------------------------------------------------

# 77. Control-Command Security

GeoNex also sends:

``` text
mode/sampling commands
backup activation
recovery requests
```

toward devices.

These commands should eventually receive appropriate:

``` text
authentication
integrity
freshness
authorization
```

C4 research may focus on telemetry, but the architecture must
acknowledge the reverse control path.

------------------------------------------------------------------------

# 78. Main Gateway Boundary

The ESP32-S3 Main Black Box gateway receives LoRa traffic.

The Lenovo ThinkCentre hosts the main software stack.

C4 verification may be split between:

``` text
gateway-level basic packet checks
+
host-level full verification/behavioural analysis
```

but responsibilities must be explicit.

------------------------------------------------------------------------

# 79. Recommended Initial Placement

Keep:

``` text
cryptographic verification
behavioural feature construction
ML inference
trust fusion
```

primarily on the Main Computing System initially unless latency/security
requirements justify moving specific checks to the gateway.

This simplifies development and auditability.

------------------------------------------------------------------------

# 80. Fail-Safe Degradation

If the C4 ML model is unavailable:

``` text
mandatory deterministic security checks must still operate
```

The system may mark behavioural assessment:

``` text
UNAVAILABLE
```

rather than bypass security.

------------------------------------------------------------------------

# 81. If Registration Store Is Unavailable

Define a safe degraded policy.

Do not automatically trust unknown devices merely to maintain data flow.

Exact fail-open/fail-closed behavior is a security/availability design
decision to be documented.

------------------------------------------------------------------------

# 82. Attack/Test Framework

Build a controlled test harness capable of generating:

``` text
legitimate telemetry
unknown-device packets
tampered payloads
duplicate packets
stale replay
counter rollback
timing anomalies
radio-behaviour anomalies
path mismatch scenarios
```

No real-world malicious deployment is required.

------------------------------------------------------------------------

# 83. Physical Security Tests

Using the GeoNex prototype, safely test:

``` text
legitimate device registration
duplicate transmission
delayed resend
device restart
changed reporting interval
unexpected gateway/path where possible
authorized C2 replay
```

Cryptographic tamper tests depend on the final protocol implementation.

------------------------------------------------------------------------

# 84. Synthetic Security Data

Synthetic attack data can help development.

Every record must identify:

``` text
source_origin = SYNTHETIC
scenario_id
generator_version
attack_type
```

Synthetic detection scores are not equivalent to real adversarial
security validation.

------------------------------------------------------------------------

# 85. Normal Behaviour Diversity

The normal class should include:

``` text
all operating modes
legitimate packet jitter
normal RSSI fluctuation
device restart where authorized
authorized recovery replay
temporary network degradation
```

Otherwise C4 will flag ordinary operation as attack.

------------------------------------------------------------------------

# 86. Mode Transition Test

A rapid reporting increase after:

``` text
IDLE → WARNING
```

must not be classified as suspicious merely because packet intervals
suddenly shrink.

Mode-aware expected behaviour is essential.

------------------------------------------------------------------------

# 87. Authorized Replay Test

Scenario:

``` text
C2 requests missing sequence range
device sends historical observations
```

Expected:

``` text
C4 authenticates current transfer
recognizes authorized recovery context
preserves historical observed_at
does not classify as malicious replay
```

------------------------------------------------------------------------

# 88. Unauthorized Replay Test

Scenario:

``` text
previous valid packet resent without recovery authorization
```

Expected:

``` text
replay detected
packet retained for audit
environmental eligibility denied
```

------------------------------------------------------------------------

# 89. Unknown Device Test

Scenario:

``` text
packet claims unknown/unregistered identity
```

Expected:

``` text
deterministic rejection/quarantine
```

No ML is required.

------------------------------------------------------------------------

# 90. Tamper Test

If integrity/authentication is implemented:

``` text
modify protected payload
```

Expected:

``` text
integrity/authentication failure
```

This must not depend on ML.

------------------------------------------------------------------------

# 91. Behavioural Clone Test

A more research-relevant behavioural scenario:

``` text
credential/identity appears valid in experiment
but timing/radio/path behaviour deviates strongly
```

This tests whether behavioural analysis adds value beyond basic identity
acceptance.

Do not overclaim physical clone detection if the test is only simulated.

------------------------------------------------------------------------

# 92. Unseen Attack Evaluation

Where dataset size permits, hold out an attack/scenario family from
supervised training and evaluate:

``` text
supervised classifier
vs
anomaly detector
```

This tests generalization.

------------------------------------------------------------------------

# 93. Robustness to Radio Environment

RSSI/SNR change due to:

``` text
distance
obstacles
weather
antenna orientation
interference
```

not only attacks.

Therefore train/test across normal radio variation and avoid using RSSI
as a simplistic identity fingerprint.

------------------------------------------------------------------------

# 94. Explainability

For tree models:

``` text
SHAP
permutation importance
```

For anomaly models:

``` text
feature deviation report
```

C4 should explain:

``` text
why a packet/device became suspicious
```

------------------------------------------------------------------------

# 95. Security Explanation vs Causal Proof

A SHAP result such as:

``` text
RSSI deviation contributed strongly
```

means:

``` text
the model used RSSI deviation
```

not:

``` text
RSSI proves an attacker was present
```

Keep interpretations precise.

------------------------------------------------------------------------

# 96. Latency

Measure:

``` text
deterministic verification latency
feature construction latency
behavioural inference latency
trust-fusion latency
total C4 latency
```

C4 sits early in the pipeline, so excessive latency affects warnings.

------------------------------------------------------------------------

# 97. Throughput

Test:

``` text
normal low-rate load
RISK/WARNING high-rate load
multi-device bursts
replay/duplicate bursts
```

C4 must not become a bottleneck.

------------------------------------------------------------------------

# 98. Resource Usage

Measure where practical:

``` text
CPU
memory
storage/audit growth
```

on the Main Computing System.

------------------------------------------------------------------------

# 99. Audit Logging

Record security-relevant events:

``` text
packet/device
timestamp
result
reason
model/rule version
action/quarantine
authorized recovery context where applicable
```

Never log secret key material.

------------------------------------------------------------------------

# 100. Security Event Retention

Security evidence may require a different retention policy from
environmental features.

Exact retention is deferred, but the architecture must preserve
sufficient evidence for research/audit.

------------------------------------------------------------------------

# 101. Dataset Privacy/Security

When exporting ML datasets:

``` text
remove secrets
remove raw credentials
remove private keys
replace sensitive identifiers where needed
```

Model training never needs secret key material.

------------------------------------------------------------------------

# 102. Suggested Code Structure

``` text
components/
└── c4_trust/
    ├── README.md
    ├── configs/
    ├── security/
    │   ├── identity/
    │   ├── integrity/
    │   ├── freshness/
    │   └── replay/
    ├── datasets/
    ├── features/
    ├── models/
    │   ├── supervised/
    │   └── anomaly/
    ├── fusion/
    ├── quarantine/
    ├── training/
    ├── evaluation/
    ├── service/
    └── tests/
```

------------------------------------------------------------------------

# 103. Shared Code Rule

C4 must not privately redefine:

``` text
device IDs
mode enums
packet schema
recovery request schema
gateway identifiers
```

Use shared GeoNex contracts.

------------------------------------------------------------------------

# 104. Security Configuration

Version/configure:

``` text
credential references
freshness windows
sequence policies
replay policy
behavioural feature windows
model artifact
trust thresholds
quarantine policy
```

Secrets remain outside ordinary configuration files.

------------------------------------------------------------------------

# 105. Training Pipeline

``` text
load frozen behavioural dataset
        ↓
validate
        ↓
group-aware split
        ↓
exclude deterministic-label leakage
        ↓
fit preprocessing on TRAIN
        ↓
train baselines/candidates
        ↓
validation/tuning
        ↓
calibration where needed
        ↓
freeze model
        ↓
TEST once
        ↓
save artifact + metadata
```

------------------------------------------------------------------------

# 106. Anomaly-Detection Pipeline

For Isolation Forest-style experiments:

``` text
trusted TRAIN behaviour
        ↓
fit normal-profile detector
        ↓
threshold on validation
        ↓
evaluate trusted + attack/anomaly TEST
```

Do not train unsupervised anomaly models on a mixture without
documenting the assumption.

------------------------------------------------------------------------

# 107. Model Metadata

Record:

``` text
model version
algorithm
dataset version
feature schema
label specification
scenario split
hyperparameters
seed
metrics
threshold
calibration
code revision
```

------------------------------------------------------------------------

# 108. Experiment Matrix

Recommended:

``` text
E0 deterministic basic identity
E1 deterministic full implemented checks
E2 behavioural Random Forest
E3 behavioural boosted tree
E4 Isolation Forest
E5 hybrid deterministic + selected behavioural
E6 hybrid + mode-aware behavioural features
```

------------------------------------------------------------------------

# 109. Unit Tests --- Security

Required examples:

``` text
unknown device rejected
revoked device rejected
invalid integrity rejected
duplicate sequence handled
authorized replay recognized
unauthorized replay rejected
legitimate reboot/session handled
```

Only include checks supported by the final protocol.

------------------------------------------------------------------------

# 110. Unit Tests --- Behaviour

``` text
rolling features causal
mode-adjusted interval correct
device ID excluded from ML feature vector
future packets excluded
missing radio metadata handled
```

------------------------------------------------------------------------

# 111. Dataset Tests

``` text
scenario does not cross split
attack template grouping correct
no secret material
deterministic target shortcut excluded
source origin present
labels valid
```

------------------------------------------------------------------------

# 112. Model Tests

``` text
artifact loads
feature schema matches
scores finite
class valid
unknown category handled
missing optional evidence handled
```

------------------------------------------------------------------------

# 113. Integration Tests

### Scenario A --- legitimate telemetry

``` text
device
→ C4 PASS/TRUSTED
→ C1
```

### Scenario B --- bad integrity/authentication

``` text
device packet
→ C4 deterministic FAIL
→ quarantine
→ not normal C1 path
```

### Scenario C --- behavioural anomaly

``` text
mandatory checks pass
→ behavioural anomaly
→ SUSPICIOUS
→ policy response
```

### Scenario D --- C2 authorized replay

``` text
C2 request
→ historical data
→ C4 authorization verification
→ accepted with replay provenance
```

------------------------------------------------------------------------

# 114. Cross-Component Test

One critical integrated test:

``` text
primary telemetry disappears
        ↓
C2 requests SD replay
        ↓
device returns old observations
        ↓
C4 validates current authenticated transfer
        ↓
authorized recovery recognized
        ↓
C1 evaluates measurement credibility
        ↓
Golden Timeline stores LATE_ORIGINAL
        ↓
C3 uses provenance-aware sequence
```

This demonstrates that all four components cooperate rather than
conflict.

------------------------------------------------------------------------

# 115. Research Tables

At minimum:

### Security-control table

``` text
scenario
deterministic check
expected outcome
actual outcome
latency
```

### Behavioural model comparison

``` text
Logistic/RF
boosted tree
Isolation Forest
selected model
```

### Hybrid ablation

``` text
deterministic only
behavioural only
hybrid
hybrid + mode context
```

------------------------------------------------------------------------

# 116. Research Figures

Useful:

``` text
hybrid C4 architecture
confusion matrix
ROC/PR curves
feature importance/SHAP
anomaly-score distributions
false accept/reject comparison
trust-decision timeline
authorized vs unauthorized replay sequence
```

------------------------------------------------------------------------

# 117. Strong C4 Demonstration

A compelling demonstration:

``` text
1. legitimate A1 telemetry accepted
2. old packet resent without authorization → rejected
3. same historical range requested through C2
4. device sends it under authorized recovery context
5. C4 accepts transfer with recovery provenance
```

This demonstrates security and availability working together.

------------------------------------------------------------------------

# 118. Research Success Criteria

C4 is scientifically successful if evidence supports claims such as:

``` text
mandatory deterministic controls reliably reject hard violations
behavioural features detect suspicious cases not represented by basic registration alone
hybrid fusion reduces important false acceptance relative to weaker baselines
mode-aware behaviour reduces false alarms caused by adaptive reporting
authorized C2 replay remains usable without disabling replay protection
```

------------------------------------------------------------------------

# 119. Operational Success Criteria

C4 should:

``` text
verify registered sources
enforce implemented integrity/freshness rules
detect unauthorized replay
score behavioural anomalies
produce explainable trust decisions
quarantine ineligible telemetry
preserve raw evidence
support authorized recovery
pass eligible data to C1 with provenance
```

without becoming a major pipeline bottleneck.

------------------------------------------------------------------------

# 120. Negative Results

If behavioural ML adds little beyond deterministic controls, report it.

Possible reasons:

``` text
dataset too simple
attack labels defined directly by deterministic fields
insufficient behavioural diversity
features too noisy
security checks already solve tested attacks
```

Do not manufacture an ML contribution where deterministic security is
objectively better.

------------------------------------------------------------------------

# 121. C4 Thesis Narrative

> IoT telemetry used for early-warning decisions must be evaluated not
> only for environmental plausibility but also for source and
> transmission trust. C4 therefore combines deterministic identity,
> integrity and freshness controls with behavioural telemetry analysis.
> Mandatory security failures cannot be overridden by machine learning,
> while behavioural models provide an additional layer for suspicious
> patterns that pass basic verification. All trust decisions preserve
> reasoned provenance and integrate with GeoNex recovery and downstream
> credibility processing.

------------------------------------------------------------------------

# 122. Candidate Contribution Statement

> **A hybrid trusted-telemetry provenance framework for IoT landslide
> monitoring that combines deterministic device/security verification
> with mode-aware behavioural anomaly assessment and recovery-compatible
> replay control.**

Final wording must reflect implemented controls and experimental
evidence.

------------------------------------------------------------------------

# 123. Limitations

Potential:

``` text
prototype-scale device population
synthetic attack scenarios
limited RF environments
credential compromise may be difficult to distinguish behaviourally
RSSI/SNR instability
limited physical clone experiments
security protocol not formally verified
behavioural model may drift
```

Report them explicitly.

------------------------------------------------------------------------

# 124. C4 Definition of Done --- Security

-   [ ] Threat model written
-   [ ] Device registry implemented
-   [ ] Credential handling avoids source-control secrets
-   [ ] Mandatory identity/authentication/integrity checks implemented
    as selected
-   [ ] Freshness/replay policy implemented
-   [ ] Authorized C2 replay path implemented
-   [ ] Revocation/lifecycle policy implemented
-   [ ] Reason codes recorded
-   [ ] Raw evidence retained
-   [ ] Quarantine path implemented

------------------------------------------------------------------------

# 125. C4 Definition of Done --- Dataset

-   [ ] Existing `C4_Trust.csv` audited
-   [ ] Trust-label specification written
-   [ ] Deterministic and behavioural evidence separated
-   [ ] Scenario IDs present
-   [ ] Device/attack groups split safely
-   [ ] Target-derived deterministic leakage removed
-   [ ] Synthetic/physical origins identified
-   [ ] No secrets in dataset
-   [ ] Dataset version frozen

------------------------------------------------------------------------

# 126. C4 Definition of Done --- ML

-   [ ] Logistic/RF baseline evaluated
-   [ ] Boosted-tree candidate evaluated
-   [ ] Isolation Forest baseline evaluated where appropriate
-   [ ] Mode-aware features tested
-   [ ] Hybrid ablation completed
-   [ ] Calibration evaluated if scores are used probabilistically
-   [ ] Explainability/error analysis completed
-   [ ] Final behavioural model selected by evidence

------------------------------------------------------------------------

# 127. C4 Definition of Done --- Integration

-   [ ] C4 executes before ordinary C1 eligibility
-   [ ] C1 receives trust metadata
-   [ ] C2 receives security context
-   [ ] Authorized C2 replay integration passes
-   [ ] C3/Golden provenance remains traceable
-   [ ] Decision Engine receives security degradation events where
    required
-   [ ] Main Gateway/Main Computer boundary documented
-   [ ] latency/throughput measured
-   [ ] end-to-end tests pass

------------------------------------------------------------------------

# 128. Rules for the C4 Member's AI Assistant

The C4 member may paste this guide into their own AI development chat.

That assistant must obey:

> **Do not redesign GeoNex shared architecture, database semantics,
> packet contracts, operating modes, C1/C2/C3 responsibilities, Golden
> Timeline, or Decision Engine boundary. Implement C4 within Documents
> 00--08. If a shared contract is insufficient, propose a versioned
> change for team review rather than silently changing it.**

Additionally:

-   never replace mandatory security checks with ML;
-   never allow ML to override invalid authentication/integrity;
-   never use secret keys as ML features;
-   never equate RSSI with identity proof;
-   never classify authorized C2 replay as malicious merely because data
    is historical;
-   never disable replay protection to support recovery;
-   never let deterministic target-generation fields create trivial ML
    leakage;
-   never claim C4 validates environmental truth;
-   always preserve reason codes and raw audit evidence.

------------------------------------------------------------------------

# 129. Recommended C4 Implementation Order

``` text
1. Write C4 threat model
2. Audit C4_Trust.csv
3. Write trust-label specification
4. Finalize device registry/lifecycle
5. Implement deterministic verification interfaces
6. Implement freshness/sequence/replay handling
7. Implement C2 authorized-replay context
8. Build behavioural feature pipeline
9. Freeze scenario-aware split
10. Implement Logistic/RF baseline
11. Train boosted-tree candidate
12. Train Isolation Forest baseline
13. Add mode-aware behavioural context
14. Run deterministic vs behavioural vs hybrid ablation
15. Implement trust fusion
16. Implement quarantine/audit
17. Integrate C1
18. Integrate C2 recovery
19. Run attack/test scenarios
20. Measure false accept/reject and latency
21. Freeze approved model/policy
22. Run end-to-end four-component tests
23. Generate thesis/paper evidence
```

------------------------------------------------------------------------

# 130. First Coding Milestone

Before sophisticated ML, produce:

``` text
C4_THREAT_MODEL.md
+
C4_DATASET_AUDIT.md
+
C4_TRUST_LABEL_SPECIFICATION.md
+
device registry
+
deterministic verification result contract
+
freshness/replay test harness
+
scenario-aware behavioural dataset split
```

Only then optimize behavioural models.

------------------------------------------------------------------------

# 131. Four-Component Research Coherence

With C4 defined, the four GeoNex research questions align:

``` text
C4:
Can I trust WHO/WHERE this telemetry came from?

C1:
Can I trust WHAT this sensor measurement says?

C2:
WHY did expected information disappear,
and how can it be recovered?

C3:
WHAT is likely to happen next?
```

This separation is one of GeoNex's strongest architectural properties.

------------------------------------------------------------------------

# 132. Four-Component Evidence Chain

A normal observation can produce:

``` text
packet
→ C4 trusted
→ C1 clean/valid event
→ Golden Timeline direct observation
→ C3 forecast
→ Decision Engine
```

A degraded case can produce:

``` text
expected packet absent
→ C2 diagnosis
→ authorized backup/replay
→ C4 verification
→ C1 credibility
→ Golden Timeline recovered provenance
→ C3 quality-aware forecast
→ Decision Engine
```

This is the integrated research story.

------------------------------------------------------------------------

# 133. Why All Four Components Are Necessary

Without C4:

``` text
plausible spoofed data may enter environmental reasoning
```

Without C1:

``` text
legitimate devices can still produce faulty measurements
```

Without C2:

``` text
missing telemetry remains unexplained/unrecovered
```

Without C3:

``` text
the system remains reactive instead of forecasting future risk
```

The four components therefore solve distinct but complementary
uncertainty problems.

------------------------------------------------------------------------

# 134. Component Success in One Sentence

> **C4 succeeds when GeoNex can demonstrate that mandatory security
> properties are enforced deterministically, behaviourally suspicious
> telemetry can be identified without confusing normal adaptive
> operation for attack, authorized recovery remains possible without
> weakening replay protection, and every downstream observation retains
> explainable source provenance.**

------------------------------------------------------------------------

# 135. Decisions Frozen by Document 08

1.  C4 is a hybrid deterministic-security and behavioural-ML component.
2.  Mandatory cryptographic/integrity failures cannot be overridden by
    ML.
3.  C4 source/transmission trust is distinct from C1 measurement
    credibility.
4.  Raw rejected telemetry remains available for audit.
5.  Device registration/lifecycle is explicit.
6.  Freshness/replay protection is mandatory at the protocol level
    selected later.
7.  Authorized C2 recovery replay must be distinguishable from
    unauthorized replay.
8.  C2 cannot bypass C4.
9.  Deterministic verification evidence and behavioural ML data are
    separated conceptually.
10. Behavioural ML must not learn trivial target rules from
    deterministic failure fields.
11. Mode-aware transmission behaviour is required because GeoNex
    reporting rate changes by mode.
12. RSSI/SNR are behavioural evidence, not identity proof.
13. Scenario/group-aware splitting is required.
14. Device identity should not become an ML shortcut.
15. Deterministic-only, behavioural-only and hybrid comparisons are
    mandatory.
16. Supervised boosted trees and an anomaly-detection baseline are
    candidate approaches, not predetermined winners.
17. Trust decisions require reason codes.
18. Quarantine restricts downstream eligibility without deleting
    evidence.
19. Security degradation can be reported to the Decision Engine without
    redefining landslide risk.
20. Reverse control/recovery messages also require security
    consideration.
21. Secrets never enter ML datasets or ordinary source control.
22. Security latency/throughput must be measured.
23. Synthetic and physical security evidence are reported separately.
24. C4 claims are limited to implemented/tested threat scenarios.

------------------------------------------------------------------------

# 136. Decisions Intentionally Deferred

Still to be finalized:

``` text
exact cryptographic algorithms
exact credential provisioning
exact key rotation
exact freshness window
exact nonce/counter/session format
exact trust-fusion thresholds
exact suspicious handling policy
final behavioural feature subset
final supervised model
final anomaly model
final quarantine duration
final security-event retention
exact gateway-vs-host verification split
```

These require the dedicated integration/security implementation and
experiments.

------------------------------------------------------------------------

# 137. Next Shared Research Document

With C1--C4 guides complete, the next document should be:

``` text
09_GEONEX_MODEL_SELECTION_AND_JUSTIFICATION.md
```

It will compare and justify the candidate algorithms across all four
components so the team can defend:

``` text
why ML is needed
why a specific model family is appropriate
why simpler baselines are necessary
why deep learning is appropriate mainly for C3
why deterministic logic remains necessary
how final model selection will be evidence-driven
how complexity, latency, explainability and deployment constraints affect selection
```

------------------------------------------------------------------------

# Document 08 Status

**`08_C4_DEVELOPMENT_GUIDE.md` --- C4 IMPLEMENTATION BASELINE READY**

C4 is deliberately designed so its research value comes from a **hybrid
trust architecture**: deterministic security establishes non-negotiable
validity constraints, behavioural ML investigates additional anomalous
patterns, and provenance/reason codes make every trust decision
auditable and compatible with C2 recovery.
