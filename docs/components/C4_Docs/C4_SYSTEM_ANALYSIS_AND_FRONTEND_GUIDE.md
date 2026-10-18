# GeoNex C4 — System Analysis, Data Flow, Storage Inventory and Frontend Guide

**Component C4: Trusted Telemetry Provenance, Device Authentication and Behavioral Trust Assessment**  
**SLIIT IT4010 Research Project**  
**Status of this document:** Findings below are taken from the source in `J26-IT-331` unless a statement is marked **unknown**.

This file is the combined deliverable for:

1. Repository audit  
2. Existing workflow explanation  
3. Storage inventory  
4. Frontend improvement plan (what was implemented)  
5. Implementation notes  
6. Testing report (fill in after commands are run; see Section 8)  
7. Run instructions  
8. Viva preparation  

---

## Deliverable 1 — Repository Audit

### 1.1 Verified entry point

The C4 frontend is launched with:

```powershell
cd C:\Users\User\Desktop\FInal_GeoNex_Repo\J26-IT-331
streamlit run apps/c4_frontend/app.py
```

That file is the only Streamlit entry point for C4. There is no separate production web API serving this dashboard.

### 1.2 Verified module map

| Area | Path | What the code actually does |
| :--- | :--- | :--- |
| Dashboard UI | `apps/c4_frontend/app.py` | Streamlit workspace, scenario buttons, `st.session_state` |
| Styles | `apps/c4_frontend/styles.py` | Shared SOC visual theme |
| Page views | `apps/c4_frontend/views.py` | Command Center, Explorer, Threat, Auth, Registry, Storage, How C4 Works |
| ML explorer UI | `apps/c4_frontend/ml_explorer_ui.py` | Holdout inspection of saved models |
| ML explorer logic | `apps/c4_frontend/ml_explorer.py` | Load artifacts, score CSV holdout, importance |
| Demo backend | `apps/c4_frontend/c4_backend.py` | Builds test CA, registry, signs packets, calls the real C4 gate |
| Trust service | `components/c4_trust/service.py` | `C4TrustService.assess()` — mandatory checks + ML fusion |
| Gate | `components/c4_trust/pipeline.py` | `C4TelemetryGate.process()` — C1 eligibility and quarantine |
| Registry | `components/c4_trust/registry.py` | In-memory `DeviceRegistry` |
| Certificates | `components/c4_trust/certificates.py` | X.509 CA, device certs, validator |
| Runtime features | `components/c4_trust/runtime_features.py` | 18-feature adapter for live packets |
| ML artifacts | `components/c4_trust/models.py` | `TrainedModel`, `C4BehavioralModelRunner` |
| Training features | `components/c4_trust/features.py` | Offline feature extraction from CSV |
| Integration factory | `components/c4_trust/integration.py` | Wires model + adapter into `C4TrustService` |
| Quarantine | `components/c4_trust/quarantine.py` | JSON evidence files |
| Packet contract | `shared/contracts/telemetry.py` | `TelemetryPacket` |
| Assessment contract | `shared/contracts/c4_trust.py` | `C4TrustAssessment` |
| Simulation generator | `shared/simulation/generator.py` | Synthetic sensor values |
| Scheduled demo | `shared/simulation/scheduled_telemetry.py` | Mode-aware demo packets |
| Topology | `shared/simulation/topology.py` | `PIPE_A1` … `PIPE_BK2` in `ZONE_01` / `ZONE_02` |
| DB persistence | `apps/ingestion/persistence.py` | Writes `telemetry_packets` / `sensor_observations` |
| C4-gated loader | `apps/ingestion/simulation_loader.py` | `load_simulated_telemetry_with_c4()` |
| DB load script | `scripts/load_demo_simulation.py` | Separate path: generate → C4 → PostgreSQL |
| Settings | `shared/config/settings.py` | `GEONEX_DB_*` from `.env` |

### 1.3 What is implemented versus documented versus simulated

| Feature | Status in code | Used by the dashboard? |
| :--- | :--- | :--- |
| HMAC-SHA256 sign/verify | Implemented in `C4TrustService` | Yes, sidebar HMAC scenarios |
| ECDSA-SHA256 P-256 | Implemented | Yes, X.509 scenarios |
| X.509 CA, expiry, identity, untrusted issuer | Implemented in `certificates.py` | Yes |
| Device registry lifecycle | Implemented in memory | Yes, rebuilt on every scenario |
| Freshness and replay | Implemented | Yes |
| Behavioral Random Forest runtime scoring | Implemented via `create_c4_service_with_behavioral_ml` | Yes, only after mandatory checks pass |
| Quarantine JSON | Implemented | Dashboard uses a **temporary** directory that is deleted when the backend closes |
| PostgreSQL `telemetry_packets` | Implemented | **Not** read or written by the Streamlit dashboard |
| Physical ESP32 / LoRa ingest | **Not present** as a live source for this UI | No |
| Hardware TPM attestation | Demo evidence dicts only | Simulated |
| Retraining from the UI | Not implemented (correct) | No |

### 1.4 Frontend metrics source (verified)

Command Center counts come only from `st.session_state.c4_results`. They are **not** live database counts, **not** CSV row counts, and **not** hardcoded KPIs.

---

## Deliverable 2 — Existing Workflow (Beginner-Friendly, Code-Verified)

### 2.1 Where dashboard packets come from

They do **not** come from physical sensors.

When you click a sidebar button, `run_scenario()` in `app.py` constructs `C4DemoBackend()` and calls `run_simulation(scenario)`.

That function calls:

`shared/simulation/scheduled_telemetry.py` → `generate_scheduled_demo_telemetry(ScheduledTelemetryConfig(seed=20261010))`

which calls:

`shared/simulation/generator.py` → `generate_baseline_packets()`

which builds a `TelemetryPacket` with:

- `source_origin=SIMULATED`
- synthetic soil moisture, temperature, pressure
- synthetic RSSI, SNR, battery fields
- device IDs such as `PIPE_A1`

Then `C4DemoBackend._prepare_packet()` attaches a demo credential ID, hub ID, test attestation dict and test provenance dict.

### 2.2 Other packet sources in the repository (not the dashboard)

| Source | File / function | What it produces |
| :--- | :--- | :--- |
| Frontend simulation button | `apps/c4_frontend/c4_backend.py` `run_simulation()` | Session assessments |
| Offline C4 CSV | `experiments/c4/data/` | Training/holdout rows for ML, not live packets |
| Database load script | `scripts/load_demo_simulation.py` | Simulated packets that **do** go through C4 then PostgreSQL |
| Unit/security tests | `tests/security/`, `tests/unit/c4/` | Fixtures |
| ESP32 / LoRa gateway | **Not found as a live dashboard input** | Unknown / not wired into this UI |

### 2.3 One packet, start to finish

Verified order in `C4TrustService.assess()` (`components/c4_trust/service.py`):

1. **Packet creation** — `generate_baseline_packets()` then `_prepare_packet()`.
2. **Submission** — `C4TelemetryGate.process(packet, signature, now=packet.observed_at)` from `c4_backend.py`.
3. **Parsing** — packet is already a Pydantic `TelemetryPacket`.
4. **Device identification** — `DeviceRegistry.get(device_id)`, `is_active()`, zone/hub compare.
5. **Certificate validation** — if PEM is present: `X509CertificateValidator.validate()`, plus registry revocation serial check.
6. **Cryptographic verification** — algorithm taken from the **registered credential**, never from the packet: HMAC compare or ECDSA verify over canonical JSON (`_canonical_packet`).
7. **Attestation / provenance** — demo verifiers compare small evidence dicts.
8. **Freshness** — `observed_at` versus `now` and `max_age_seconds=30`.
9. **Replay** — `(device_id, packet_id)` cache and sequence monotonicity. These run only if earlier failures/unknowns are empty.
10. **Behavioral ML** — **skipped** if any mandatory failure or security unknown exists. Otherwise `behavioural_scorer(packet)` → `C4BehavioralModelRunner` → `RuntimeFeatureAdapter.extract_features` → `random_forest_corrected.joblib`. Score = `1 - P(Trusted)`. Threshold `0.70`.
11. **Final decision**
    - failures → `UNTRUSTED` / `REJECT`
    - security unknowns → `UNKNOWN` / `SECURITY_REVIEW`
    - score ≥ 0.70 → `SUSPICIOUS` / `QUARANTINE`
    - else → `TRUSTED` / `ACCEPT`
12. **Gate** — only TRUSTED + mandatory pass + ACCEPT sets `eligible_packet`. Anything else is quarantined.
13. **Frontend** — `_result_row()` copies assessment fields into a dict; `app.py` appends it to `session_state.c4_results`.
14. **Persistence of dashboard results** — **in memory only**. Temporary quarantine files are deleted in `backend.close()`.

Diagram that matches this code:

```
Synthetic generator
  → TelemetryPacket (source_origin=SIMULATED)
  → C4DemoBackend sign (HMAC or ECDSA)
  → C4TelemetryGate.process
  → C4TrustService.assess
       → registry, cert, signature, freshness, replay
       → ML only if mandatory checks passed
  → ACCEPT (eligible for C1) or quarantine record
  → Streamlit session_state display
```

ML is not an arrow that can reverse a failed signature.

---

## Deliverable 3 — Storage Inventory

Passwords, HMAC secrets and private keys are omitted.

| Item | Exact source or path | How data gets there | How it is read | Survives restart? |
| :--- | :--- | :--- | :--- | :--- |
| Dashboard assessments | `st.session_state.c4_results` | Scenario buttons | Command Center / Explorer | **No** |
| Dashboard quarantine JSON | `tempfile.TemporaryDirectory` in `C4DemoBackend` | `C4TelemetryGate` | Deleted by `close()` | **No** |
| Default C4 quarantine JSON | `quarantine/c4/Q_*.json` | `QuarantineManager` when no temp dir is passed (tests, other scripts) | JSON files | Yes, on disk |
| C4 behavioral CSV | `experiments/c4/data/` | Audit/prepare/split scripts | pandas, ML Explorer | Yes |
| Saved models | `experiments/c4/models/*.joblib` | `train_c4_baselines.py`, `retrain_c4_corrected.py` | `TrainedModel.load` | Yes |
| SHAP plots | `experiments/c4/plots/` | `scripts/explain_c4_model.py` | ML Explorer image tab | Yes |
| Demo device registry | In-memory `DeviceRegistry` | `C4DemoBackend.__init__` | Registry page | **No** |
| Demo CA and device keys | Process memory | `create_ca` / `create_device_certificate` | Never shown in UI | **No** |
| PostgreSQL telemetry | Database `geonex`, tables `telemetry_packets`, `sensor_observations` | `persist_telemetry_packet()` via `scripts/load_demo_simulation.py` | SQLAlchemy | Yes, if Docker/Postgres is running |
| C4 assessments in SQL | **No C4 assessment table found** | Not implemented | N/A | N/A |
| Config | `.env` `GEONEX_DB_HOST/PORT/NAME/USER` | Operator | `GeoNexSettings` | Yes |

### Concepts with examples

- **Memory versus disk:** a Command Center count lives in RAM; `C4_test_corrected.csv` lives on disk.
- **CSV versus live packet:** a CSV row is a historical training example. A dashboard packet is a newly generated `TelemetryPacket` with `source_origin=SIMULATED`.
- **Model file versus prediction:** `random_forest_corrected.joblib` is the serialized forest. A behavioral score is one inference result.
- **Telemetry record versus assessment:** `telemetry_packets` stores sensor payload fields. `C4TrustAssessment` is the security decision. The dashboard stores the assessment in session memory, not SQL.
- **Quarantined versus rejected:** both are ineligible for C1. Reject means mandatory security failed (`UNTRUSTED`). Quarantine is also used for suspicious ML or unknown evidence. The gate quarantines any non-ACCEPT packet.
- **Session result versus database row:** seeing a packet in Telemetry Explorer does **not** mean a PostgreSQL row exists.

### Proposed persistence (not implemented)

A compatible next step would be an optional table for `C4TrustAssessment` plus a dashboard flag `persisted_to_database`. That needs a migration and a policy decision. It was **not** added, because it would change storage architecture.

---

## Deliverable 4 — Frontend Improvement Plan (Implemented)

Navigation in `app.py`:

1. How C4 Works  
2. Command Center  
3. Telemetry Explorer  
4. Threat Investigation  
5. Authentication & Device Trust  
6. ML Model Explorer  
7. Device Registry & Policy  
8. Data Storage & Diagnostics  
9. Model & Policy  

Principles applied:

- Keep every existing HMAC and X.509 scenario button.
- Label every metric as **session data**.
- Show unavailable values instead of inventing fields.
- Never render secrets, PEM private material, or HMAC keys.
- Explain HMAC versus ECDSA in plain language on How C4 Works and Authentication pages.
- Packet detail shows origin, checks, ML, decision, assessment ID, and storage explanation.

---

## Deliverable 5 — Implementation Notes

Changed / added files:

- `apps/c4_frontend/app.py` — redesigned workspace shell  
- `apps/c4_frontend/styles.py` — SOC theme  
- `apps/c4_frontend/views.py` — page renderers  
- `apps/c4_frontend/c4_backend.py` — richer `_result_row()`, `list_safe_devices()`, `system_diagnostics()`  
- `apps/c4_frontend/ml_explorer.py` / `ml_explorer_ui.py` — existing ML explorer, preserved  
- `tests/unit/c4/test_c4_frontend_backend.py` — origin, no-secrets, tamper fail-closed  
- `tests/unit/c4/test_c4_ml_explorer.py` — ML explorer unit tests  

Not changed: saved `.joblib` models, C4 trust thresholds, database schema, unrelated C1/C2/C3 components.

---

## Deliverable 6 — Testing Report

Executed from `J26-IT-331` on 18 Oct 2026.

| Command | Result |
| :--- | :--- |
| `python -m ruff check apps/c4_frontend components/c4_trust tests/unit/c4 tests/security` | All checks passed |
| `python -m pytest tests/unit/c4/test_c4_frontend_backend.py tests/unit/c4/test_c4_ml_explorer.py tests/security tests/integration/test_c4_simulation_gate.py -q` | **103 passed**, 18 warnings |
| `python -m pytest tests/unit/c4 tests/unit/test_c4_runtime_features.py -q` | **64 passed**, 18 warnings |
| Streamlit `AppTest` of How C4 Works, Command Center, Authentication, Registry, Diagnostics, ML Model Explorer | No exceptions |
| SHA-256 of `experiments/c4/models/random_forest_corrected.joblib` before and after tests | Unchanged `DE199DD8DC5518CE93AE220F4C07D9EA174D57052A3C5E45F3A91D9DE28AB94E` |

Warnings are pre-existing sklearn unpickle version notes (artifact trained on 1.9.1, runtime 1.9.0) and feature-name warnings on a tiny unit-test forest. They are not new assertion failures.

Verified by tests, not by invention:

- HMAC valid simulation is labeled `FRONTEND_SIMULATION` / `SIMULATED` and `persisted_to_database=False`
- Device list omits secrets
- Tampered HMAC is `UNTRUSTED`, mandatory security fails, `INTEGRITY_INVALID`, not eligible for C1
- Saved runtime model file was not overwritten

Database connectivity was not asserted as a pass/fail gate. The Diagnostics page queries the configured PostgreSQL instance if it is running and shows an error name if it is not. No database was reset.

---

## Deliverable 7 — Run Instructions (Windows PowerShell)

### 7.1 Launch the dashboard

```powershell
cd C:\Users\User\Desktop\FInal_GeoNex_Repo\J26-IT-331
conda activate <your-geonex-env>
streamlit run apps/c4_frontend/app.py
```

Open the Local URL (typically `http://localhost:8501`).

### 7.2 Run tests

```powershell
cd C:\Users\User\Desktop\FInal_GeoNex_Repo\J26-IT-331
python -m pytest tests/security tests/unit/c4 tests/integration/test_c4_simulation_gate.py -q
```

### 7.3 Optional: verify PostgreSQL without resetting it

The dashboard Diagnostics page runs `SELECT 1` and counts `telemetry_packets` if the configured database is up.

Settings come from `.env`: host `127.0.0.1`, port `5433`, database `geonex`, user `geonex_app`. Do not paste the password into slides or this UI.

Optional separate ingest (this **does** write accepted packets to SQL; it is not the Streamlit session path):

```powershell
python scripts/load_demo_simulation.py
```

### 7.4 Locate files

| Need | Path |
| :--- | :--- |
| Frontend | `apps/c4_frontend/app.py` |
| Real C4 engine | `components/c4_trust/service.py` |
| Runtime model | `experiments/c4/models/random_forest_corrected.joblib` |
| Holdout CSV | `experiments/c4/data/C4_test_corrected.csv` |
| Disk quarantine (non-dashboard) | `quarantine/c4/` |

---

## Deliverable 8 — Viva Preparation

### 8.1 Architecture

```
Synthetic demo packets
        │
        ▼
C4DemoBackend (test CA, in-memory registry)
        │
        ▼
C4TelemetryGate ──► C4TrustService.assess
        │                 │
        │                 ├─ DeviceRegistry
        │                 ├─ X.509 validator
        │                 ├─ HMAC or ECDSA
        │                 ├─ freshness / replay
        │                 └─ Random Forest (only if mandatory pass)
        ▼
ACCEPT → eligible for C1
else   → quarantine (temp file in dashboard)
        ▼
Streamlit session display
```

### 8.2 HMAC versus ECDSA (simple, accurate)

HMAC uses one shared secret. Both sides compute SHA-256 HMAC over the same canonical packet bytes. If the bytes change after signing, verification fails (`INTEGRITY_INVALID`).

ECDSA uses a P-256 private key to sign and the matching public key (usually inside an X.509 certificate) to verify. C4 never takes the algorithm from the attacker-controlled packet; it uses `credential.signature_algorithm`. That is why “HMAC signature on an ECDSA device” is rejected (`fallback_rejection`).

### 8.3 X.509 in one minute

A device certificate binds a public key to a device identity and is signed by a CA. C4 checks time validity, issuer trust, identity match (`CN`/SAN versus `device_id`), key usage, and local revocation. An expired, rogue-CA, or identity-mismatched certificate fails **before** ML is allowed to score.

### 8.4 How ML contributes

The saved Random Forest estimates whether behavior looks Trusted. The runtime score is `1 - P(Trusted)`. If that score is ≥ 0.70 **and** mandatory checks passed, the packet is `SUSPICIOUS` and quarantined. If a signature is invalid, the label is `UNTRUSTED` even if the forest would have said “normal”.

Offline training uses `experiments/c4/data/` and must not leak cryptographic flags such as `signature_valid` into features. Runtime uses the 18-name schema in `C4_MODEL_FEATURE_SCHEMA`.

### 8.5 Where the data comes from and where it is stored

Dashboard: generated in Python, assessed in process, shown from `session_state`, gone after refresh.

Training: CSV on disk.

Production-style DB path: only `scripts/load_demo_simulation.py` (or other ingestion callers), not the Streamlit buttons.

### 8.6 Likely viva questions

**Q: Is this live landslide telemetry?**  
A: No. `source_origin` is `SIMULATED`. Values are engineering fixtures from `generate_baseline_packets()`.

**Q: Can ML accept a tampered packet?**  
A: No. `C4TrustAssessment` rejects TRUSTED/SUSPICIOUS when `mandatory_security_pass` is false, and `assess()` short-circuits to UNTRUSTED on failures before using the score.

**Q: Why do Command Center numbers reset?**  
A: They are session memory, not database aggregates.

**Q: Why might PostgreSQL show packets while the dashboard is empty?**  
A: A different script persisted simulation packets. The UI does not query that table for KPIs.

**Q: What is the difference between HMAC and certificates?**  
A: HMAC proves possession of a shared secret. A certificate plus ECDSA proves possession of a private key bound to a named device and a trusted CA.

**Q: Did you change the trained model for the UI?**  
A: No. The UI loads `random_forest_corrected.joblib` read-only.

---

## Limitations of the current implementation (honest)

- Dashboard attestation/provenance verifiers are demo dictionaries, not TPM quotes.
- Dashboard registry and keys are in-memory test PKI.
- Dashboard assessments are not an audit log.
- Freshness is evaluated with `now=packet.observed_at` in the demo so historical simulated timestamps do not immediately fail age checks.
- sklearn pickle version warnings can appear if the training sklearn version differs from the runtime version; the artifact is still the saved forest, not a newly trained one.
