# GeoNex Component 4 (C4) — Complete Implementation and Frontend Guide

**Project:** J26-IT-331 — GeoNex  
**Component:** C4 — Trusted Telemetry Provenance and Device Attestation  
**Snapshot reviewed:** `FInal_GeoNex_Repo (3).zip`, uploaded 19 October 2026  
**Repository path inside archive:** `FInal_GeoNex_Repo/J26-IT-331/`

> **Reading rule:** This guide describes the current source code in the uploaded repository. Older C4 documents are useful context, but the code is the authority when behavior differs. It distinguishes the Python/Streamlit implementation from the separate React/TypeScript UI. A UI label or mock screen is not proof that a backend feature is connected.

---

## 1. What C4 does in GeoNex

C4 is the **trusted-telemetry gate**. Before downstream components interpret sensor values, C4 checks whether a packet came from an allowed device, has valid integrity/authentication evidence, is fresh, is not a replay, and has sufficient evidence for a behavioral assessment.

C4 does **not** decide whether the soil is actually unstable, whether a sensor reading is environmentally credible, or whether a landslide warning should be issued. Those are separate responsibilities in the wider GeoNex pipeline.

### Responsibility boundary

```text
Sensor / pipe device
    ↓ telemetry packet
Hub / gateway transport metadata
    ↓
C4 identity + credential + certificate checks
    ↓
C4 signature/integrity + evidence + freshness + replay checks
    ↓
C4 behavioral feature extraction + ML score (when configured)
    ↓
C4 trust decision and routing outcome
    ├── TRUSTED      → ACCEPT → eligible for C1
    ├── SUSPICIOUS   → QUARANTINE → review, not eligible for C1
    ├── UNTRUSTED    → REJECT → not eligible for C1
    └── UNKNOWN      → SECURITY_REVIEW → not eligible for C1
```

**Important:** `TRUSTED` means C4 has sufficient evidence to accept the telemetry source/packet. It does not mean the measurement is physically correct. C1 handles sensor credibility; C3 handles forecasting; the integrated decision layer is responsible for final warning decisions.

## 2. Repository map

### C4 security and runtime logic

| File | Responsibility |
|---|---|
| `components/c4_trust/service.py` | Central `C4TrustService`: authentication, identity/credential checks, certificate checks, freshness, replay/sequence checks, evidence callbacks, behavioral score integration, final trust assessment |
| `components/c4_trust/certificates.py` | X.509 certificate loading, CA trust, validity, identity, key usage, signature/chain checks, revocation support, demo CA/device certificate/CRL creation |
| `components/c4_trust/registry.py` | Device registry, credentials, zones/hubs, lifecycle state, approved firmware/config metadata, certificate serial revocation |
| `components/c4_trust/runtime_features.py` | Converts a live `TelemetryPacket` into the fixed behavioral-model feature schema; keeps rolling per-device history |
| `components/c4_trust/features.py` | Offline/training feature extraction and historical/mode-aware feature engineering |
| `components/c4_trust/models.py` | Model loading, schema checks, inference, baseline model wrapper, prediction/evaluation helpers |
| `components/c4_trust/integration.py` | Wires runtime feature extraction and a trained model into `C4TrustService`; also offers deterministic-only construction |
| `components/c4_trust/pipeline.py` | `C4TelemetryGate`: turns assessment into downstream eligibility and quarantine handling |
| `components/c4_trust/quarantine.py` | Quarantine records, reason codes, listing/release/reporting and JSON persistence |
| `components/c4_trust/data_split.py` | Scenario-aware, device-aware and combined dataset splitting/validation |
| `components/c4_trust/__init__.py` | Public package exports |

### Python/Streamlit dashboard

| File | Responsibility |
|---|---|
| `apps/c4_frontend/app.py` | Streamlit application shell, page navigation, session-state result list, scenario execution and result-frame conversion |
| `apps/c4_frontend/c4_backend.py` | `C4DemoBackend`: constructs a temporary demo PKI, registry, real C4 gate, ML-enabled trust service and synthetic telemetry scenarios |
| `apps/c4_frontend/views.py` | Streamlit page rendering and packet detail, trust/security views, registry/policy/storage diagnostics |
| `apps/c4_frontend/ml_explorer.py` | Model catalog, model profile/schema, holdout evaluation, scoring, sample inspector, importance/SHAP paths |
| `apps/c4_frontend/ml_explorer_ui.py` | Streamlit UI for model profile, features, holdout evaluation, inspector, what-if scoring and SHAP plots |
| `apps/c4_frontend/styles.py` | CSS/style definitions for Streamlit |

### React/TypeScript frontend

The separate frontend lives under `apps/web/src/features/c4/`.

- `pages/C4Page.tsx`: top-level page, tabs, local scenario result state and scenario handling.
- `pages/C4Page.css` and `styles/c4*.css`: page and section styling.
- `components/CommandCenter.tsx`: summary metrics, activity/chart-like summaries and results.
- `components/ScenarioButtons.tsx`: scenario control buttons.
- `components/TelemetryExplorer.tsx`: filterable telemetry table and packet details.
- `components/ThreatInvestigation.tsx`: suspicious/untrusted result investigation.
- `components/Authentication.tsx`: authentication/trust-focused view.
- `components/MLExplorer.tsx`: model profile and CSV validation UI; calls a local HTTP API.
- `components/Registry.tsx`: device registry/topology display.
- `components/Storage.tsx`: storage and diagnostic display.
- `components/Policy.tsx`: policy explanation UI.
- `components/HowC4Works.tsx`: explanatory architecture view.
- `types/index.ts`: TypeScript interfaces and unions for packets, assessments, routing and UI metrics.

**Integration warning:** the React page currently creates mock assessments in browser state. Its own result object marks `data_origin: "FRONTEND_SIMULATION"`, `persisted_to_database: false`, and `storage: "react_component_state"`. React Registry and Storage also construct mock data in their components. React ML Explorer uses `http://127.0.0.1:8000`; that dependency must be running and its endpoints must match the frontend's expectations. Do not describe the React scenario controls as invoking the real Python C4 gate.

## 3. Core trust data and concepts

C4 works with shared packet and assessment contracts rather than treating arbitrary dashboard rows as security decisions.

- **TelemetryPacket:** packet identity, device identity, zone, boot/sequence information, observed/received times, measurements, device-health fields, transport/radio metadata and security metadata.
- **SecurityMetadata:** credential ID, integrity/signature-related information, freshness counter/session information, optional firmware/config hashes, optional certificate PEM and optional attestation/provenance evidence.
- **DeviceRecord:** registered device ID, device kind, zone/hub assignment, lifecycle state, credential, and optional approved firmware/config data.
- **DeviceCredential:** credential ID, secret material for HMAC, algorithm selection, optional public key/certificate and optional issued/expiry timestamps.
- **C4TrustAssessment:** trust label/score, mandatory-security-pass flag, reason codes, behavioral score, routing outcome, model/policy version, timestamp and correlation/test identifiers.
- **C4GateResult:** assessment, optional packet eligible for C1, and optional quarantine record.

A key design point is that **mandatory security failures are not overridden by a good ML score**. Behavioral scoring is downstream of the mandatory gate.

## 4. Trust labels and routing outcomes

| Trust label | Typical meaning | Routing outcome | C1 eligibility |
|---|---|---|---|
| `TRUSTED` | Mandatory security checks passed and behavioral score is acceptable, or explicitly allowed deterministic-only mode is active | `ACCEPT` | Yes, if the gate returns the packet as eligible |
| `SUSPICIOUS` | Mandatory checks passed but behavioral anomaly score meets/exceeds the configured threshold | `QUARANTINE` | No |
| `UNTRUSTED` | A hard security failure exists, such as unknown/inactive device, bad signature, invalid certificate, stale packet or replay | `REJECT` | No |
| `UNKNOWN` | Required evidence or behavioral assessment is unavailable/indeterminate | `SECURITY_REVIEW` | No |

The current service defaults visible in `service.py` are:
- maximum packet age: **30 seconds**;
- future timestamp tolerance: **5 seconds**;
- suspicious behavioral score threshold: **0.7**;
- deterministic-only mode is not implicitly assumed; it must be explicitly configured.

A timestamp that is too far in the future is a failure. A timestamp outside the age window is a freshness failure unless the service recognizes an authorized recovery replay context.

## 5. `C4TrustService.assess()` — actual decision sequence

The service collects three categories of evidence:

1. `failures`: checks that positively failed.
2. `security_unknowns`: mandatory evidence is missing or could not be verified.
3. `verified`: checks that passed and can be included in reason codes.

The final decision priority in the current implementation is:

```text
Run identity / registry / zone / hub / credential checks
    ↓
Check credential issue/expiry dates
    ↓
Validate X.509 certificate if supplied or required
    ↓
Verify HMAC-SHA256 or ECDSA signature
    ↓
Verify attestation and provenance through configured callbacks
    ↓
Check timestamp freshness and future tolerance
    ↓
Check packet replay key and sequence monotonicity
    ↓
Any hard failures?
    ├── YES → UNTRUSTED / REJECT / score 0
    └── NO
         ↓
Any mandatory security unknowns?
    ├── YES → UNKNOWN / SECURITY_REVIEW
    └── NO
         ↓
Obtain behavioral score if scorer is configured
    ↓
Score unavailable or invalid and deterministic-only is disabled?
    ├── YES → UNKNOWN / SECURITY_REVIEW
    └── NO
         ↓
Score ≥ 0.7?
    ├── YES → SUSPICIOUS / QUARANTINE
    └── NO  → TRUSTED / ACCEPT
```

The score is validated as a finite numeric value from 0 to 1. The current trust score is derived as `1 - behavioral_score` for scored packets. If the explicit deterministic-only path is used without a score, the service can accept a packet after mandatory checks and records `DETERMINISTIC_ONLY_POLICY`.

### Identity and registry checks

When a `DeviceRegistry` is configured, the service checks:
- device exists;
- device lifecycle state is active;
- reported zone equals the registered zone;
- gateway/hub ID is present and matches the registered hub;
- packet credential ID matches the registered credential ID;
- credential issue/expiry timestamps are sensible and current;
- firmware/config checks when the relevant approval policy/data is configured.

A missing piece of required evidence is not the same as a confirmed mismatch. The implementation can return `UNKNOWN` for missing evidence, while a confirmed mismatch is a hard failure and yields `UNTRUSTED`.

### Lifecycle

The registry supports the lifecycle states represented by `DeviceLifecycleState`, including provisioned, active, suspended, revoked and retired states. Only an active device passes the active-device gate. Registry helpers support activation, suspension, revocation, retirement, credential updates, firmware approval and config approval. Certificate serials can also be tracked as revoked.

## 6. Cryptographic integrity: HMAC and ECDSA

### HMAC-SHA256

HMAC is a symmetric message-authentication mechanism: the sender and verifier share a secret. The service canonicalizes the packet before calculating/verifying the MAC, and uses constant-time comparison for signature/MAC comparison.

```text
Packet + shared device secret
    ↓ canonical packet representation
HMAC-SHA256
    ↓ transmitted signature
C4 recomputes HMAC using registered secret
    ↓ constant-time comparison
Match → INTEGRITY_VALID
Mismatch → INTEGRITY_INVALID → UNTRUSTED / REJECT
```

HMAC is useful for the demo and shared-secret devices, but it requires safe secret distribution and storage. It does not provide public-key identity or non-repudiation.

### ECDSA P-256 / SHA-256

ECDSA uses an asymmetric private/public key pair. The simulation sender signs with a private key; C4 verifies with the registered/certificate-derived public key. The source supports ECDSA-SHA256 with elliptic-curve keys and refuses a signature that cannot be verified.

```text
Device private key signs canonical packet
    ↓ signature
C4 obtains trusted public key from registered credential/certificate
    ↓ verify ECDSA-SHA256
Valid → INTEGRITY_VALID
Invalid/unverifiable → failure or UNKNOWN according to what evidence exists
```

A signature being mathematically valid is not enough by itself: the identity, credential, certificate and lifecycle must also be acceptable.

## 7. X.509 certificate validation

`components/c4_trust/certificates.py` contains `X509CertificateValidator` and helpers to create demo certificate material. The validator supports PEM/DER certificate loading, configured trusted CA certificates, explicit revoked serial numbers and CRLs, certificate validity dates, identity binding to the expected device ID, public-key extraction, and key-usage/CA constraints where required by its configured policy.

The trust service:
1. selects certificate data from the packet or registered credential;
2. detects a mismatch if both packet and registry certificate are present but differ;
3. validates the certificate for the packet's `device_id`;
4. checks registry certificate revocation;
5. compares the certificate public key against the registered credential public key when present;
6. uses the validated EC public key for ECDSA verification.

Common negative scenarios/reason categories include expired certificate, untrusted issuer/CA, identity mismatch, revoked certificate, missing certificate when required, certificate/credential mismatch and public-key mismatch.

**Important distinction:** the dashboard can generate an in-memory test CA and certificates for a controlled demo. That demonstrates validation flow; it is not equivalent to a production PKI deployment with secure key provisioning, protected private keys, operational CA governance and a production revocation service.

## 8. Freshness, replay and sequence protection

Freshness and replay are different:
- **Freshness:** is `observed_at` within the allowed time window, and is it not too far in the future?
- **Replay:** has this packet identity already been seen?
- **Sequence check:** has this device/boot sequence number failed to advance?

The service tracks packet keys using `(device_id, packet_id)` and sequence state using `(device_id, boot_id)`. When sequence checking is required, missing boot/sequence evidence is treated as unknown mandatory evidence. Duplicate packet IDs or a sequence number less than/equal to the last accepted sequence cause replay failures unless an authorized recovery replay context applies.

**Current limitation:** `_seen_packets` and `_last_sequence` are in-memory service state. Unless an external durable store is added, this replay state resets when the service instance is recreated/restarted. The dashboard's demo backend is constructed for scenario execution and uses a temporary directory; do not claim production-grade durable replay protection from this in-memory implementation alone.

### Authorized recovery replay

The service exposes recovery-context helpers to authorize a constrained replay window for a specific device and request. This is a controlled exception for recovery workflows; it should not be confused with accepting arbitrary replayed packets.

## 9. Attestation and provenance evidence

The service accepts optional verifier callbacks for attestation and provenance. Each callback may return:
- `True`: evidence verified;
- `False`: evidence explicitly invalid, producing a hard failure;
- `None`: evidence unavailable/unverified, producing an unknown state.

This is an extension point, not proof that every kind of hardware-rooted attestation is implemented. A real verifier must be wired into the service and validate the actual evidence format. The dashboard may use controlled demo evidence/callbacks to exercise the path.

Firmware/config hashes are also policy-dependent: the registry stores approval metadata and the service compares packet hashes when approval records/policies require it. A packet merely containing a field does not mean firmware integrity has been cryptographically attested.

## 10. Behavioral ML pipeline

C4's behavioral ML supplements, but does not replace, mandatory security checks.

### Runtime path

```text
TelemetryPacket
    ↓ RuntimeFeatureAdapter.extract_features()
fixed feature schema + rolling device history
    ↓ C4BehavioralModelRunner
loaded model inference
    ↓ behavioral anomaly score in [0, 1]
C4TrustService applies threshold (default 0.7)
    ├── lower score → TRUSTED if all mandatory checks pass
    └── high score  → SUSPICIOUS / QUARANTINE
```

The integration factory `create_c4_service_with_behavioral_ml()` loads a model artifact, validates the expected feature schema, creates the runtime adapter, and attaches the behavioral scorer. It can also configure certificate requirements, sequence requirements, firmware/config approval, freshness and future tolerance. `create_c4_service_deterministic_only()` exists for a deliberately configured deterministic-only service.

### Runtime feature schema

`runtime_features.py` defines the model feature contract. The current schema includes:

1. `tx_interval_s`
2. `rx_delay_s`
3. `freshness_status_encoded`
4. `rssi_dbm`
5. `rssi_deviation_db`
6. `snr_db`
7. `retry_count`
8. `packet_size_bytes`
9. `battery_pct`
10. `battery_voltage_v`
11. `current_ma`
12. `reboot_count_24h`
13. `sensor_fault_flag`
14. `rolling_interval_mean`
15. `rolling_interval_std`
16. `rolling_rssi_mean`
17. `rolling_rssi_std`
18. `rolling_retry_mean`

The adapter validates numeric inputs, derives freshness encoding and packet size as needed, calculates RSSI deviation where possible, and maintains rolling history per device (default integration history window: 10 observations). Required missing/invalid feature values raise a feature error rather than silently inventing trustworthy values.

`features.py` serves the offline/training side: extracting from dataframes, adding mode-aware/historical features, and creating behavioral datasets. The training-time and runtime feature definitions must remain aligned; the model wrapper checks feature schema before inference.

### Model artifacts and explorer

The repository contains model artifacts under `experiments/c4/models/`, including:
- `random_forest.joblib`
- `random_forest_corrected.joblib`
- `logistic_regression.joblib`
- `isolation_forest.joblib`

The Python model catalog/explorer can show model profile and feature schema, inspect feature importance, load holdout data, score samples, evaluate holdout metrics, and show available SHAP plot artifacts. The default runtime artifact in the dashboard backend is `experiments/c4/models/random_forest_corrected.joblib`.

Do not treat a filename containing `corrected` as proof it is the only valid or final model. Confirm the artifact's training metadata, feature schema, dataset split and evaluation output before presenting it as authoritative. Do not retrain or overwrite artifacts just to inspect them.

## 11. Dataset files and split cautions

Dataset files live under `experiments/c4/data/`. This repository contains multiple generations of data and split artifacts; they must not be treated as interchangeable.

### Current base behavioral dataset and current split review notes

The file `C4_Behavioral_Dataset.csv` has **10,000 rows and 62 columns** in this snapshot. Its trust labels are:
- Trusted: 7,757
- Untrusted: 1,588
- Suspicious: 655

The repository's `C4_SPLIT_REVIEW_NOTES.md` reports the following current non-corrected split set:

| File | Rows | Columns |
|---|---:|---:|
| `C4_train.csv` | 5,584 | 62 |
| `C4_val.csv` | 3,252 | 62 |
| `C4_test.csv` | 1,164 | 62 |

The notes report 10,000 total rows and no shared `device_id` values between these three files. The scenario field has shared values across splits. This is a device-held-out evaluation design, useful for assessing generalization to unseen devices, but it does **not** evaluate unseen-scenario generalization when scenarios overlap.

The same notes identify the older backup split under `backup_before_device_split_20261013_054519/` as 6,987 / 1,520 / 1,493 rows with device overlap. They recommend preferring the current device-separated split for unseen-device evaluation, while preserving the backup until validation is complete.

### Corrected files are a separate artifact set

The snapshot also includes `C4_train_corrected.csv`, `C4_val_corrected.csv`, and `C4_test_corrected.csv`. They have 66 columns and their row counts differ from the 62-column current split set (for example, the corrected test file has 3,196 rows in this archive). Therefore, do not combine counts or evaluation results from these sets without first checking how each set was generated and which model artifact was trained against it.

The existing audit documents identify risks such as label/feature leakage, scenario-to-label shortcuts and ambiguous binary label semantics. The split review explicitly says further validation is needed for the meaning of `label_untrusted_binary` and to ensure validation/test data are not used for model fitting or model selection. Those warnings should remain visible in any report/viva claim.

## 12. Quarantine and review

`C4TelemetryGate.process()` calls the trust service and uses the assessment to determine downstream eligibility. It can return:
- the trust assessment;
- the packet when eligible for C1;
- a quarantine record when the decision should be isolated for review.

`QuarantineManager` supports reasons including behavioral anomaly, weak signal, degraded device health, clock delay, interval anomaly, RSSI-profile anomaly, path mismatch, security failure, evidence unavailable and custom reasons. A record can preserve packet data, assessment, review assessment, reviewer, release state/time and release reason. It supports lookup/listing by device, unreleased records, counts, counts by reason and report generation.

The implementation can serialize quarantine records as JSON files. Persistence scope depends on the configured directory:
- Python dashboard demo: its `C4DemoBackend` creates a `TemporaryDirectory` and a quarantine subdirectory, so this is temporary demonstration storage.
- A service configured with a stable directory can preserve records across process runs, subject to file-system durability and deployment controls.
- React scenario results are only in browser React state and are cleared on refresh; they are not the Python quarantine store.

A quarantine record or dashboard count should not be described as a database row unless the implementation actually writes it to the database.

## 13. Python/Streamlit dashboard — real C4 pipeline demo

### Execution flow

```text
User selects Streamlit page / scenario
    ↓ apps/c4_frontend/app.py
C4DemoBackend.run_simulation(scenario)
    ↓
Create synthetic telemetry and scenario-specific security conditions
    ↓
Build demo CA/device certificates + device registry/credentials
    ↓
C4TelemetryGate.process(packet, signature)
    ↓
C4TrustService.assess()
    ↓
Behavioral ML runtime features + configured model
    ↓
Assessment + eligible packet / quarantine record
    ↓
Return rows to Streamlit session state
    ↓
views.py renders tables, detail panels, audit and metrics
```

The backend's supported scenario names in the current code include:
- `valid`, `valid_hmac`, `tampered`, `tampered_hmac`, `replay`, `replay_hmac`;
- `valid_ecdsa`, `tampered_ecdsa`;
- `expired_x509`, `untrusted_ca_x509`, `mismatched_identity_x509`, `revoked_x509`;
- `unverifiable_ecdsa`, `fallback_rejection`.

The dashboard uses synthetic scheduled telemetry, a local test CA and test device certificates. It constructs a real `C4TelemetryGate` and C4 service, so it is a code-path demonstration of the trust logic—not a production device enrollment flow.

### Streamlit pages

1. **How C4 Works** — explains the C4 flow and boundaries.
2. **Command Center** — runs scenarios and summarizes session assessments.
3. **Telemetry Explorer** — filters packet/assessment results and opens packet details.
4. **Threat Investigation** — focuses on suspicious/untrusted results and security reason details.
5. **Authentication & Device Trust** — shows identity/authentication evidence and relevant checks.
6. **ML Model Explorer** — model profile, feature schema, holdout evaluation, sample inspector, what-if scoring and SHAP plots when available.
7. **Device Registry & Policy** — registry/lifecycle and policy-oriented information.
8. **Data Storage & Diagnostics** — model/dataset/database diagnostics.
9. **Model & Policy** — model and policy configuration/explanation.

`app.py` stores the scenario results in `st.session_state.c4_results` and increments a run count. This is **Streamlit session state**, not a guarantee of durable database persistence. The `C4DemoBackend` is created per scenario run and closed afterwards; its temporary files are cleaned up when the temporary directory is removed.

## 14. React/TypeScript C4 frontend — current behavior and caveats

### Main page and tabs

`C4Page.tsx` owns:
- `results` state;
- selected tab;
- notice/error messages;
- scenario generation;
- clear-results behavior.

The tabs are:
1. How C4 Works
2. Command Center
3. Telemetry Explorer
4. Threat Investigation
5. Authentication & Device Trust
6. ML Model Explorer
7. Device Registry & Policy
8. Data Storage & Diagnostics
9. Model & Policy

### Scenario buttons are currently a frontend simulation

`handleRunScenario()` builds a `C4AssessmentResult` in the browser. It checks the scenario name for words such as tampered, replay, expired, untrusted CA, identity mismatch, revoked, fallback, ECDSA and HMAC, then assigns mock labels/reason codes. It generates packet fields locally, adds the object to React state, and does not call the Python C4 trust service.

The source itself records:
- `persisted_to_database: false`;
- `storage: "react_component_state"`;
- `data_origin: "FRONTEND_SIMULATION"`;
- an explanation that the result was generated by the React mock and not assessed by the real C4 backend.

This transparency is important. The React screen can be useful for UI development, layout review and illustrating the intended workflow, but the scenario outcomes must not be presented as a cryptographic validation test.

### React section behavior observed in source

- **Command Center:** derives visible summary/activity from the results passed down from `C4Page`.
- **Telemetry Explorer:** filters the passed result list and displays rows/details; it is not evidence of a persistent telemetry query unless a real data source is connected.
- **Threat Investigation:** inspects locally generated assessment results.
- **Authentication:** visualizes authentication/trust fields from the result objects.
- **Registry:** `Registry.tsx` builds a small hard-coded mock device/topology list in a `useEffect`.
- **Storage:** `Storage.tsx` creates a hard-coded diagnostic object, including a sample database “Connection refused” state. This is not a live database health check in the current source.
- **Policy / How C4 Works:** explanatory frontend content.
- **ML Explorer:** `MLExplorer.tsx` calls `http://127.0.0.1:8000` and expects model-profile/CSV-validation responses. It enforces a 10 MiB CSV upload limit in the client. This UI depends on a compatible local API; a failed request is not the same as a model failing inference.

### React types

`types/index.ts` declares types such as `TrustLabel`, `RoutingOutcome`, `SourceOrigin`, `ProcessingStatus`, `FreshnessStatus`, `C4TrustAssessment`, `TelemetryPacket`, `DeviceHealth`, `TransportMetadata`, `SecurityMetadata`, `Measurement`, `C4AssessmentResult`, `SecurityAudit`, `CommandCenterMetrics` and `ScenarioType`.

**Integration checklist for a future live React connection:**
- expose explicit backend endpoints for scenario execution, telemetry results, registry, diagnostics and model profiles;
- make the React scenario handler submit the scenario/packet to the backend rather than fabricate an assessment;
- display backend-returned assessment IDs, reason codes and storage status;
- replace mock Registry/Storage data with API responses and show loading/error states honestly;
- configure the API base URL through environment/config rather than hard-coding loopback;
- add contract tests between TypeScript request/response types and Python shared contracts;
- do not report a result as persisted unless the backend confirms persistence.

## 15. Storage boundaries

Different forms of state exist and should be explained separately:

| Data/state | Current scope |
|---|---|
| Streamlit scenario results | `st.session_state`; generally tied to the Streamlit session |
| Python demo quarantine | Temporary directory created by `C4DemoBackend` for that run |
| C4 replay/sequence tracking | In-memory dictionaries/sets inside a service instance |
| React scenario results | React component state; lost on refresh |
| React Registry / Storage display | Hard-coded mock objects in current React component code |
| ML datasets and artifacts | Files under `experiments/c4/data/` and `experiments/c4/models/` |
| GeoNex TimescaleDB telemetry | Separate project persistence layer; do not assume C4 dashboard rows are automatically written there |

For database-specific claims, inspect the actual API/repository integration and current database schema. The current React Storage view is not a live connection test.

## 16. Tests and verification map

The ZIP contains the following C4 test groups:

### Security tests
- `tests/security/c4/test_c4_device_registry.py`
- `tests/security/c4/test_c4_ecdsa_signatures.py`
- `tests/security/c4/test_c4_trust_service.py`
- `tests/security/c4/test_c4_x509_certificates.py`

### Unit tests
- `tests/unit/c4/test_c4_frontend_backend.py`
- `tests/unit/c4/test_c4_ml_data.py`
- `tests/unit/c4/test_c4_ml_explorer.py`
- `tests/unit/c4/test_c4_runtime_features.py`

### Integration and contracts
- `tests/integration/c4/test_c4_simulation_gate.py`
- `tests/contract/test_c1_c4_contracts.py`

What these test names indicate:
- device registration/lifecycle and credential handling;
- ECDSA signing/verification behavior;
- trust-service decision rules;
- X.509 certificate validation cases;
- dashboard backend simulation integration;
- feature/data and ML explorer behavior;
- runtime feature extraction;
- C1/C4 packet/assessment contract compatibility.

**Verification status for this report:** this was a source/archive review. The tests were located and inspected as repository assets, but this document does not claim that the test suite was executed during this review. Run the tests in the intended environment before quoting a current pass count.

Example PowerShell commands from the repository root (activate the project's intended Python environment first):

```powershell
python -m pytest tests/security/c4 -q
python -m pytest tests/unit/c4 -q
python -m pytest tests/integration/c4 tests/contract/test_c1_c4_contracts.py -q
```

For a full run, use the repository's documented test/lint commands and record the actual output/date. Do not infer success from cached `.pyc` or `.pytest_cache` files.

## 17. Known limitations and claims to avoid

1. **Do not call the React scenario runner a real cryptographic test.** It currently fabricates result objects locally.
2. **Do not claim React Registry/Storage are live.** Their current source creates mock data.
3. **Do not claim all accepted packets are persisted to TimescaleDB.** The Streamlit session, temporary quarantine and DB are different storage scopes.
4. **Do not claim replay state survives restart.** Current packet/sequence tracking is in memory.
5. **Do not claim production hardware attestation is complete just because callback hooks exist.** A concrete verifier must be configured.
6. **Do not claim firmware integrity is always enforced.** Firmware/config checks are policy/configuration dependent.
7. **Do not quote a model accuracy without naming the artifact, split, feature schema, class metrics and evaluation procedure.** Existing files include multiple dataset generations and model artifacts.
8. **Do not claim unseen-scenario generalization from the current device-separated split.** Scenarios are shared across train/validation/test according to the split notes.
9. **Do not call the `_corrected` files authoritative solely because of their names.** Their dimensions differ from the base split set; verify the model/data provenance.
10. **Do not expose `.env`, credentials, private keys or secret material in reports, screenshots, commits or memory files.** The uploaded archive contains a `.env`; this guide intentionally does not reproduce its contents.
11. **Do not conflate C4 trust with C1 sensor credibility or the final landslide decision.**

## 18. Viva-ready explanation

> “C4 is GeoNex's trusted telemetry provenance and device-attestation layer. It validates device registration and lifecycle, credential identity, HMAC or ECDSA integrity, X.509 certificates when configured, freshness, replay/sequence behavior, and configured attestation/provenance evidence. Only after mandatory checks pass does the behavioral model assess packet behavior using runtime features such as transmission interval, delay, RSSI/SNR, retries, battery/device health and rolling history. The service routes packets as Trusted/Accept, Suspicious/Quarantine, Untrusted/Reject or Unknown/Security Review. The C4 gate only forwards eligible telemetry to C1; it does not decide whether a landslide warning should be issued. Our Python Streamlit demo invokes the real C4 service and gate with synthetic telemetry and demo credentials. The separate React frontend currently contains a local scenario mock, so its displayed results must not be confused with a live backend assessment.”

### Short arrow-wise viva flow

```text
Packet received
 → registry/device active?
 → zone + hub + credential match?
 → certificate/key checks (when supplied/required)
 → HMAC/ECDSA signature valid?
 → attestation/provenance evidence verified?
 → timestamp fresh and not future-dated?
 → packet ID / sequence not replayed?
 → behavioral features extracted and model score available?
 → TRUSTED / SUSPICIOUS / UNTRUSTED / UNKNOWN
 → ACCEPT / QUARANTINE / REJECT / SECURITY_REVIEW
 → only ACCEPT/eligible packet is passed to C1
```

## 19. Existing C4 documents to read alongside this guide

Under `docs/components/C4_Docs/`:
- `C4_COMPLETE_IMPLEMENTATION_GUIDE.md`
- `C4_COMPLETION_REPORT.md`
- `C4_DATASET_AUDIT.md`
- `C4_FRONTEND_AND_BACKEND_GUIDE.md`
- `C4_IMPLEMENTATION_SUMMARY.md`
- `C4_INTEGRATION_GUIDE.md`
- `C4_ML_MODEL_EXPLORER.md`
- `C4_RUNTIME_INTEGRATION_SUMMARY.md`
- `C4_SCHEMA_FIX_NOTES.md`
- `C4_SECURITY_VALIDATION.md`
- `C4_SYSTEM_ANALYSIS_AND_FRONTEND_GUIDE.md`
- `C4_THREAT_MODEL.md`
- `C4_TRUST_LABEL_SPECIFICATION.md`

These documents may contain older snapshots or recommendations. Cross-check any version-specific claim against the current source, dataset and tests before using it in a final report or viva.
