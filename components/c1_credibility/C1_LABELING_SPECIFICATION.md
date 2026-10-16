# C1 Labeling Specification

**Component:** C1 — Rainfall Regime-Aware Sensor Credibility Classification
**Version:** 1.1
**Status:** Draft — pending owner review
**Owner:** R. M. Kanishka Harshana
**Jira:** GEONEX-5 — Generate Datasets for C1
**Depends on:** Document 03 (Dataset Architecture), Document 04 (Mode Sampling and Timing Specification), Document 05 (C1 Development Guide), Document 14 (Repository and Implementation Guide). Context from Document 00 (System Development Plan) and Document 02 (Data & Database Architecture).

---

## 0. Compliance map for Document 05 §12

Document 05 §12 requires this file to define eight things. This table shows where each is defined.

| Doc 05 §12 requirement | Section |
|---|---|
| Exact evidence required for CLEAN | §4 |
| Exact anomaly-generation / annotation criteria | §5, §6 |
| Exact VALID_EVENT criteria | §7 |
| Ambiguous cases | §9 |
| Multi-sensor event handling | §8 |
| Synthetic-label construction | §10 |
| Physical-demo labeling | §11 |
| External-data labeling | §12 |

Related requirements: Doc 03 §16–18 (unit, target, metadata) are in §2 and §13. Doc 05 §37–41 (leakage and generator separation) are in §14. Doc 05 §49–52 (splits) are in §15.

**Parameter status.** Every numeric value in this document is **PROVISIONAL**. Document 05 §28 and §101 forbid arbitrary values and hard-coded thresholds, so each value lives in `components/c1_credibility/configs/c1_labeling_v1.yaml` (see §16) and must be justified by the `C1_Validation.csv` audit, the calibration records, the simulator physics, or literature before a dataset is frozen. This document names the parameters; the config file holds the values.

---

## 1. Purpose and principles

This document defines the ground-truth labeling criteria for the C1 credibility classifier. Document 05 states that no model result is scientifically stronger than its ground truth, so these rules are written before any model is trained.

1. Labels are derived from controlled generation truth, controlled experiment records, or documented annotation. They are **never** derived from C1's own predictions.
2. C1 judges **measurement credibility**: "Can I trust what this measurement says about the environment?" It does not judge where a packet came from (C4) or why data is missing (C2). Source trust is not measurement credibility (Doc 00 §14).
3. An unusual value is **not** automatically a faulty sensor. During a real landslide precursor, unusual values are expected. This is why `VALID_EVENT` exists.
4. Raw observations are never modified. Labels are stored beside them.
5. Synthetic, physical-demo and external data stay distinguishable at every row (Doc 05 §14).

## 2. Scope and prediction unit

### 2.1 Sensor-family scope

- **First family: soil moisture.** Rainfall and spatial consistency have interpretable relationships with soil moisture, and credible ground truth can be generated (Doc 05 §17).
- Other families (FSR, motion, tilt, vibration, temperature, humidity) are **out of scope for v1.x**. Expanding scope requires a new spec version and a working soil-moisture baseline.
- Rainfall and temperature appear only as **context**, not as target families.
- The choice between a shared classifier and per-family classifiers (Doc 05 §16) is an experiment, not a labeling decision.

### 2.2 Prediction unit (Doc 03 §16)

One row is one **target sensor observation** plus **only the context available at that observation's decision time** (the as-of rule). A label belongs to an `observation_id`, not to a packet, because one packet can hold a credible value and a problematic one (Doc 02 §35).

### 2.3 Calibration

Labels apply to **calibrated engineering values**, not raw ADC responses (Doc 05 §43). Every record carries `calibration_version`. Calibration errors must not be left for C1 to learn.

### 2.4 C4 gate

Observations from packets that fail mandatory C4 security policy are not C1 inputs and are never labeled `ANOMALY` for C1 (Doc 05 §19). Only C4-accepted observations enter C1 datasets.

## 3. Target classes

`credibility_label` takes exactly one of three values (Doc 03 §17, Doc 05 §10).

| Class | Meaning |
|---|---|
| **CLEAN** | Measurement is consistent with expected sensor and environmental behaviour |
| **ANOMALY** | Evidence indicates the measurement is likely unreliable, erroneous, or a sensor-related abnormality |
| **VALID_EVENT** | Measurement is unusual or extreme, but contextual evidence supports it as a genuine environmental change |

### 3.1 Why three classes

A binary NORMAL/ANOMALY classifier would treat genuine hazard-related extremes as anomalies. `VALID_EVENT` represents the central research challenge.

**Critical error:** `VALID_EVENT` → `ANOMALY`, because it suppresses genuine warning evidence (Doc 05 §11). Evaluation reports this error separately.

### 3.2 Not a class

`INSUFFICIENT_CONTEXT` is **not** a training class. See §9.1.

## 4. CLEAN criteria

A soil-moisture observation is `CLEAN` when **all** of the following hold. Each uses a parameter from the labeling config.

| # | Evidence | Parameter | Provisional value |
|---|---|---|---|
| C1 | Value within the sensor's valid physical range | `valid_range_min`, `valid_range_max` | 0 %, 100 % (replace with the calibration record) |
| C2 | Rate of change from the previous observation, computed with the **actual Δt**, is within the physical limit | `max_normal_rate_pct_per_min` | 1.0 %/min |
| C3 | Deviation from neighbour consensus is within tolerance (see §7.3) | `neighbour_tolerance_k` | 3.0 robust SDs |
| C4 | No unexplained rise: any rise larger than `unexplained_rise_pct` within `unexplained_rise_window_min` is accompanied by rainfall support (§7.2) | `unexplained_rise_pct`, `unexplained_rise_window_min` | 2.0 %, 30 min |
| C5 | No real device-health fault evidence (§9.2) | see §9.2 | — |
| C6 | Not inside a generated fault window or genuine-event response (synthetic data), or not marked as either in the experiment log (physical-demo data) | — | — |

C1–C5 are the **observable evidence**. For synthetic data, the label comes from generator truth (§10), and C1–C5 are checked afterwards by the validation step to confirm that CLEAN rows really look clean. For annotated data, C1–C5 define the annotation rule.

## 5. ANOMALY criteria

### 5.1 Fault families

Only faults relevant to soil moisture are used (Doc 05 §39). All are **sensor-level** faults.

| Fault family | Description | Synthetic generation (in `datasets/`) | Key parameters |
|---|---|---|---|
| **Spike** | Sudden isolated extreme value | Add a large offset to one or a few samples | `spike_min_sigma` = 5 × σ_noise |
| **Stuck-at** | Value frozen at a constant | Repeat one value for N samples | `stuck_min_samples` = 5 |
| **Drift** | Gradual bias growing over time | Add a linearly increasing offset | `drift_floor_sigma` = 3 × σ_noise |
| **Bias** | Constant offset from the true value | Add a constant offset | `bias_min_sigma` = 3 × σ_noise |
| **Dropout** | Invalid sensor reading (see 5.2) | Set to null, an error code, or an out-of-range value | — |
| **Excessive noise** | High-variance signal | Add noise with several times the calibrated σ | `noise_factor_min` = 4 |
| **Out-of-range** | Physically impossible value | Set a value outside the valid range | — |
| **Quantization / ADC issue** | Coarse steps or stuck low-order bits from ADC problems | Quantize to few levels, or clamp or alias ADC codes | `quant_levels_max` = 8 |

### 5.2 Dropout means a sensor-level invalid reading

`Dropout` here is a **reading** that the sensor produced but that is invalid: null, a sentinel, or an error code from the sensor or its ADC. It is **not** a lost packet, a missing transmission or a silent pipe. Missing transmissions are C2's problem (§5.4).

### 5.3 Where new fault families are generated

The simulator's `shared/simulation/faults.py` offers `SENSOR_SPIKE` and `SENSOR_DRIFT` as C1-relevant faults. The other families above are **generated by C1's own code in `components/c1_credibility/datasets/`**. Do **not** edit `shared/simulation/faults.py` or the shared `FaultType` enum for this purpose: shared enums and simulation code need owner coordination (Doc 14 §19, §27).

### 5.4 Excluded: simulator faults that are not C1 anomalies

Document 05 §19 says C1 must not treat C4 or transport failures as ordinary measurement anomalies, and Document 00 §14 says source trust is not measurement credibility. These simulator faults are therefore **excluded** from C1 `ANOMALY` labels.

| Simulator fault | Why excluded | Owner |
|---|---|---|
| `PACKET_DROP` | A lost transmission is a missing-data / silence problem, not a wrong measurement | C2 |
| `DELIVERY_DELAY` | A timing problem. It may make context stale (see staleness, §14.3) but does not make a value wrong | C2 / shared timing |
| `SEQUENCE_ANOMALY` | A packet-provenance and integrity problem | C4 |

Rows affected only by these faults keep the label their measurement deserves (usually `CLEAN`). If a delay makes required context too old, the row becomes `INSUFFICIENT_CONTEXT` (§9.1), not `ANOMALY`.

### 5.5 Detectability requirement

A synthetic fault must be detectable from features available at runtime, not only from hidden truth. The validation step (`datasets/validate.py`) must report the fraction of fault rows that are not detectable and apply the rules below.

- A fault observation whose injected effect is below its floor (`spike_min_sigma`, `drift_floor_sigma`, `bias_min_sigma`) is **not** labeled `ANOMALY`. It is flagged `ambiguous` with reason `FAULT_BELOW_DETECTABILITY` (§9).
- Stuck-at faults are injected only while the true signal would have varied by at least `stuck_min_variation_sigma` = 2 × σ_noise over the window; otherwise a stuck sensor is indistinguishable from a stable one.

### 5.6 Evidence rule for annotated and physical data

For **physical-demo and annotated data without a controlled-disturbance record**, an observation is labeled `ANOMALY` only when **at least two** of these independent pieces of evidence hold:

1. Value outside the physical range.
2. Rate of change exceeds the physical limit (using actual Δt).
3. Disagreement with neighbours while the environment is stable.
4. Disagreement with environmental context (for example, high moisture with no rainfall support).
5. Real device-health fault evidence (§9.2).

This evidence rule does **not** apply to synthetic data. Synthetic labels come from generator truth (§10), because a single injected fault may trigger only one indicator and would otherwise fail a multi-evidence rule. It also avoids computing labels from the same features the model sees, which would let the classifier learn the labeling thresholds instead of credibility.

## 6. Label precedence

When more than one rule could apply to an observation, apply them in this order. First match wins.

1. **Context eligibility.** If required context is unavailable, the row is `INSUFFICIENT_CONTEXT` and excluded from training (§9.1).
2. **Fault truth.** If the observation lies inside a fault window and its injected effect meets the detectability floor → `ANOMALY`. (Below the floor → ambiguous, §5.5.)
3. **Event truth.** If the observation lies inside an event response and its event component meets the event-strength floor (§7.4) → `VALID_EVENT`.
4. **Otherwise** → `CLEAN`.

A fault always overrides an event for the **faulty sensor only**. See §8.

## 7. VALID_EVENT criteria

### 7.1 Definition

An observation is `VALID_EVENT` when it is unusual but environmentally plausible: the environment itself changed, and the observation reflects that change.

Required evidence for physical or annotated data (all of these):

- The value is extreme or changing fast, but physically possible.
- Rainfall support precedes it (§7.2).
- A minimum number of neighbours show a compatible response (§7.3).
- The temporal trend is plausible: the response begins after rainfall onset and follows the expected shape.
- No real device-health fault evidence (§9.2).

**Example.** Soil moisture 86.2 % (rapid rise from 78.1 %), `rain_1h_sum` = 24.5 mm, `neighbour_mean` = 84.9 % with a compatible rise → `VALID_EVENT`.

### 7.2 Rainfall support and lag

| Parameter | Meaning | Provisional value |
|---|---|---|
| `rain_lag_min_min` | Earliest plausible soil response after rainfall onset | 0 min |
| `rain_lag_max_min` | Latest plausible soil response after rainfall onset | 120 min |
| `rain_support_min_mm` | Minimum accumulated rainfall inside the lag window to count as support | 1.0 mm |
| `event_min_duration_obs` | Minimum number of consecutive observations in an event response | 3 |
| `event_min_duration_min` | Minimum event duration in minutes (the larger of the two durations applies) | 10 min |

Rainfall support is evidence for **annotation and validation**. It is **not** the rule that assigns synthetic labels (see §7.5).

### 7.3 Neighbours and agreement

A **neighbour** is a configured sensor with the same `sensor_type` in the same `zone_id`, other than the target (Doc 05 §32). Neighbour relationships come from configuration, never from guessing.

| Parameter | Meaning | Provisional value |
|---|---|---|
| `neighbour_min_count` | Minimum available neighbours for a context-supported label | 2 |
| `neighbour_agreement_fraction_min` | Fraction of available neighbours that must show a compatible response for `VALID_EVENT` | 0.5 |
| `neighbour_tolerance_k` | Compatible = within k robust SDs of the neighbour consensus change | 3.0 |
| `neighbour_max_age_s` | Maximum age of a neighbour reading to be used (as-of join, Doc 05 §33–34) | 2 × the operating-mode sampling interval (set per mode; see Doc 04) |

If fewer than `neighbour_min_count` neighbours are available inside `neighbour_max_age_s`, neighbour evidence is **missing**, not negative (§9.1).

### 7.4 Event strength

An observation inside an event response is `VALID_EVENT` only when the **event component of the true signal** is at least `event_min_effect_sigma` = 3 × σ_noise above the pre-event baseline. Observations inside the event window but below that floor are `CLEAN`.

**Event strength follows rainfall dynamics, not regime thresholds.** The expected response size grows with accumulated rainfall and falls with antecedent wetness. The generator must produce events across the full range of rainfall intensities, including:

- weak-rain events with small responses, which mostly stay `CLEAN`;
- heavy-rain events with large responses, which produce `VALID_EVENT` rows.

Regime names such as DRY, LIGHT, MODERATE, HEAVY and EXTREME are used only to **describe and analyse** events and as a feature for the model. They never decide a label (§7.5).

### 7.5 Generate events from dynamics, not thresholds (anti-circularity)

If rainfall thresholds decided `VALID_EVENT`, and the same thresholds defined the rainfall-regime feature, then the core ablation (does rainfall context help?) would prove nothing, because the model would only recover the labeling rule.

Therefore, for synthetic data:

1. Generate a rainfall time series (temporal profile) from a stochastic rainfall process.
2. Pass it through a soil-response model (infiltration with lag, saturation limit and antecedent wetness) to obtain the **true** soil-moisture signal.
3. Add spatial heterogeneity and correlation for each neighbour (different gain, lag and local noise).
4. Add calibrated sensor noise to get the observed signal.
5. Assign `VALID_EVENT` from **generator truth**: the observation is in an event response (`event_id`) and its event component meets §7.4.
6. The generator must **not read** the rainfall-regime thresholds. Regime thresholds live only in the feature config (Doc 05 §28) and are applied later by the feature builder.
7. After generation, `validate.py` checks coherence as a **sanity test**, never as a labeling step: responses lag rainfall within `rain_lag_*`, neighbours co-move, and no `VALID_EVENT` row exists without a preceding rainfall event.

Do **not** create `VALID_EVENT` by assigning the label to random extreme values (Doc 05 §40).

### 7.6 Negative cases

These must be generated and must **not** be `VALID_EVENT`. They are the hard cases that teach C1 the difference.

| Case | Setup | Label |
|---|---|---|
| N1 — extreme value, no rain, no neighbour support | Large rise in a dry period; neighbours flat | `ANOMALY` |
| N2 — rain and neighbour response, target does not respond | Target stuck or flat while neighbours rise | `ANOMALY` |
| N3 — isolated target response, neighbours quiet, rain present | Only the target rises | `ambiguous` (`ISOLATED_RESPONSE`); label by generator truth, flagged |
| N4 — extreme value while rainfall sensor has failed | Rain context missing | `INSUFFICIENT_CONTEXT` (§9.1) |
| N5 — all neighbours unavailable | No neighbour context | `INSUFFICIENT_CONTEXT` |

## 8. Multi-sensor event handling

1. **`event_id`.** Every genuine event gets one `event_id` shared by **all** observations from **all** sensors it affects. The `event_id` is used for splitting (§15) and sampled as metadata, never as a feature.
2. **Per-observation labels.** Labels are assigned per `observation_id`, not per event. One event can contain `VALID_EVENT`, `CLEAN` and `ANOMALY` rows.
3. **Fault during a real event.**
   - The **faulty sensor's** affected observations are `ANOMALY` (fault truth takes precedence, §6), even though an event is occurring.
   - **Neighbours** that respond genuinely keep `VALID_EVENT`.
   - The record carries both `event_id` and `fault_id`, and the fault's `fault_window` is stored in the ground-truth sidecar.
4. **Neighbour support is evidence for the target only.** A neighbour's fault must not change a healthy target's label; if a neighbour is faulty, it is excluded from the target's neighbour consensus when the fault is observable (device-health evidence or flagged by the generator's truth for validation).
5. **Partial response.** If fewer than `neighbour_agreement_fraction_min` of the available neighbours respond, the target observation is flagged `ambiguous` (`PARTIAL_NEIGHBOUR_RESPONSE`).
6. **Multiple events overlapping** in the same zone keep separate `event_id` values. Observations inside the overlap carry both and are flagged `ambiguous` (`OVERLAPPING_EVENTS`).

## 9. Ambiguous cases

### 9.1 Insufficient context

Required context is: a minimum history length (`min_history_obs`, provisional 5), rainfall available, and at least `neighbour_min_count` neighbours inside `neighbour_max_age_s`.

- If any required context is unavailable, the row is **not given a training label**. Its `credibility_label` is empty and its `context_status` is `INSUFFICIENT_CONTEXT`.
- These rows are **excluded from training and from headline evaluation**. They are kept in a separate exclusions file for audit and for the missing-context stress tests (Doc 05 §78, §82, §83).
- **Runtime** returns `INSUFFICIENT_CONTEXT` through the `context_status` field of the C1 output contract. Use the exact values defined in `shared/contracts/c1_credibility.py`. Do not redefine them in C1.
- Context is never fabricated (Doc 05 §22).

### 9.2 Device-health priority

When a device-health indicator and the environment disagree, the device-health indicator takes priority **only if it is real fault evidence**, meaning an independent signal from the device, not something inferred from the value itself.

Real evidence is one of:

- `recent_read_failures` at or above `health_read_failures_min` consecutive failures (provisional 3);
- `device_voltage` below `health_voltage_min_v` (provisional: from the hardware spec);
- a firmware self-test or error flag;
- for synthetic data, a **generator-injected** device-health fault recorded in the truth sidecar.

An unusual value alone is **never** device-health evidence. This protects genuine events from being relabeled as faults.

When real fault evidence exists inside an event, the **affected sensor** is `ANOMALY` (§8.3); its neighbours are unaffected.

### 9.3 Borderline extremes

A borderline extreme is a value that is extreme but whose context only partly supports it.

- Label by generator truth (synthetic) or by the annotation protocol (physical).
- Set `borderline_extreme = true`.
- **Rationale for preferring `VALID_EVENT` when context supports it:** missing a genuine event costs more than a wrong flag, and `VALID_EVENT` → `ANOMALY` is the critical error (Doc 05 §11). The cost is a possible upward bias in the `VALID_EVENT` class.
- **Reporting:** metrics are reported on the full set **and** on the set without borderline rows. A sensitivity run flips borderline labels to check that conclusions hold.

### 9.4 Ambiguity flags and training policy

Every row has `ambiguous` (true/false) and, when true, `ambiguity_reason`.

| `ambiguity_reason` | Training policy | Reporting |
|---|---|---|
| `FAULT_BELOW_DETECTABILITY` | Excluded from training | Counted and reported |
| `ISOLATED_RESPONSE` | Excluded from training | Counted and reported |
| `PARTIAL_NEIGHBOUR_RESPONSE` | Excluded from training | Counted and reported |
| `OVERLAPPING_EVENTS` | Excluded from training | Counted and reported |
| `BORDERLINE_EXTREME` | Kept in training | Reported separately (§9.3) |

The dataset manifest records the **per-reason counts** and the total `ambiguous_count` (§16.2).

## 10. Synthetic-label construction

1. **Baseline (CLEAN) signal.** Generate rainfall, true soil moisture (via §7.5), temperature and device health with temporal and spatial consistency. Add Gaussian sensor noise with σ from calibration.
2. **Events.** Add genuine events per §7.5 and §8. Record `event_id` and the event window in the truth sidecar.
3. **Faults.** Start from the signal above and apply **one** fault family per fault window. Record `fault_id`, `fault_type` and `fault_window` in the truth sidecar. Faults are spread across devices and across event and non-event periods, so that no device or period correlates with a label.
4. **Missingness.** Inject context missingness (rainfall outages, neighbour outages, short history) at configured rates. These produce `INSUFFICIENT_CONTEXT` rows (§9.1) and stress-test sets.
5. **Labels from generator truth.** Apply §6 precedence using the truth sidecar. Set `label_source = SYNTHETIC_GENERATOR_TRUTH`.
6. **Validation.** Run `validate.py`: coherence checks (§7.5), detectability report (§5.5), label-distribution check, leakage tests (§14), schema checks.
7. **Hidden fields.** `fault_type`, `fault_window`, `fault_id`, `event_id` and the true signal live in a separate truth sidecar and are never joined into the feature table.
8. **Determinism.** The build is deterministic for a given `random_seed` and `builder_version`.

All synthetic rows carry `source_origin = SYNTHETIC`. Synthetic results are never reported as field measurements (Doc 00 §42).

## 11. Physical-demo labeling

Physical-demo data is collected on the prototype and kept separate from synthetic data (`source_origin = PHYSICAL_DEMO`). It is never invented or simulated to fill gaps (Doc 05 §127).

### 11.1 Protocol

Each experiment records:

- **Known normal conditions** — baseline periods with no intended disturbance.
- **Controlled sensor disturbances** — for example, disconnecting a probe, covering it, or injecting a known offset. Each disturbance is logged with start and end times.
- **Controlled environmental changes where safe** — for example, applying measured water to the soil.
- **Rainfall-mechanism response** — what the rainfall sensor or mechanism reported.
- **Neighbour sensor responses** — all neighbours' readings in the same period.
- **Timestamps** — timezone-aware, with `observed_at` and `received_at` kept separate (Handbook §14).
- **`test_run_id`** — one per experiment run.

### 11.2 Labeling rules

| Situation | Label | `label_source` |
|---|---|---|
| Inside a logged controlled disturbance | `ANOMALY` | `PHYSICAL_PROTOCOL` |
| Inside a logged controlled environmental change with compatible neighbour response | `VALID_EVENT` | `PHYSICAL_PROTOCOL` |
| Logged known-normal period | `CLEAN` | `PHYSICAL_PROTOCOL` |
| Unlogged period labeled afterwards | Apply §5.6 (two-evidence rule) for `ANOMALY` and §7.1 for `VALID_EVENT` | `PHYSICAL_ANNOTATION` |

Annotations record the annotator, date and the evidence used. Rows that do not meet either rule are not labeled.

### 11.3 Reporting

Physical-demo results are reported **separately** from synthetic results. Claims stay conservative because the prototype has few devices and few events.

## 12. External-data labeling

**v1.1 does not use external data.**

If external data is added later:

- it must carry `source_origin = EXTERNAL` and `label_source = EXTERNAL_LABEL`, with the data's provenance and licence recorded;
- its labels must be mapped to the three classes by a documented, reviewed rule, in a new version of this specification (v1.2 or later), **before** it is used;
- it is never combined with synthetic or physical data in one reported metric without explicit written justification (Doc 05 §14).

### 12.1 Legacy asset: `C1_Validation.csv`

`C1_Validation.csv` is an existing research artifact with the same three classes. It is **not** assumed to be a valid training set (Doc 05 §13). Its rows are not used until the audit is complete: schema, class balance, source, how labels were generated, leakage fields, scenario grouping, units, then a manifest and a registered dataset version. After the audit, each row's `label_source` and `source_origin` are set from the audit result.

## 13. Record fields

### 13.1 Target

| Field | Notes |
|---|---|
| `credibility_label` | `CLEAN`, `ANOMALY` or `VALID_EVENT`. Empty for `INSUFFICIENT_CONTEXT` rows. The numeric encoding is a training detail (Doc 03 §17). |

### 13.2 Metadata (non-feature fields, Doc 03 §18)

`record_id`, `observation_id`, `zone_id`, `device_id`, `sensor_instance_id`, `observed_at`, `source_origin`, `test_run_id`, `dataset_version`.

These support traceability and split construction. **They are never fed to the model.**

### 13.3 Label-support fields (non-feature)

| Field | Notes |
|---|---|
| `label_source` | `SYNTHETIC_GENERATOR_TRUTH`, `PHYSICAL_PROTOCOL`, `PHYSICAL_ANNOTATION`, `EXTERNAL_LABEL` |
| `event_id` | Event group (§8); empty if none |
| `calibration_version` | Calibration record used |
| `context_status` | Matches the shared C1 contract, including `INSUFFICIENT_CONTEXT` |
| `ambiguous`, `ambiguity_reason` | §9.4 |
| `borderline_extreme` | §9.3 |

### 13.4 Ground-truth sidecar (never joined to features)

`fault_id`, `fault_type`, `fault_window`, `event_id`, true signal, injected device-health fault.

### 13.5 Feature fields

The baseline analytical record follows Doc 05 §47 (temporal, rainfall, neighbour and device-health features, plus `rainfall_regime`). The feature set is defined by the feature schema, not by this document.

## 14. Leakage rules

### 14.1 Fields that must never be features

- `packet_id`, `observation_id`, `record_id` and every other ID
- device serial number
- dataset row number
- scenario ID and `event_id`
- ground-truth label and `credibility_label`
- ground-truth event flag
- injected-fault flag
- hidden generator variables: `fault_type`, `fault_window`, `fault_id` and the true signal
- `label_source`
- future observations or future context
- C3 risk probability (and any C3 output)
- future operating mode
- C1's own predictions

### 14.2 Absolute ID rule

**IDs are metadata and split keys, not features.** This includes `device_id`, `zone_id` and `sensor_instance_id`. If all faults came from one device, an ID feature would let the model memorize "that device = anomaly" instead of learning credibility (Doc 05 §38). Faults must also be spread across devices at generation time (§10).

### 14.3 As-of joins and staleness

- All temporal, rainfall and neighbour features use **only past and current** data relative to the target's decision time.
- Neighbour readings older than `neighbour_max_age_s` are treated as **missing**, never carried forward (Doc 05 §34).
- Rainfall windows have exact boundaries, and rate of change uses the actual Δt (Doc 05 §105).
- No neighbour join may use a future observation.

### 14.4 Preprocessing statistics

Scalers, imputers, calibrators and any fitted statistics are fitted on **training data only**. Test-set statistics must not be used (Doc 05 §106).

### 14.5 Required automated checks

`validate.py` and the tests assert that:

- scenario and event groups do not cross splits;
- no future context is used;
- hidden generator fields and target are excluded from features;
- no ID field appears in the feature set;
- test preprocessing statistics are not used.

## 15. Split strategy

1. **Group by scenario and event.** All rows of a scenario stay in one split. All observations from all sensors in one `event_id` stay in one split (§8). Random row splits are **not** allowed (Doc 05 §49–50).
2. **Frozen split.** The split is generated once, saved, and recorded in the manifest with `split_strategy: scenario_grouped` and `random_seed`. It does not change between experiments.
3. **All three classes in every split.** Train, validation and test must each contain `CLEAN`, `ANOMALY` and `VALID_EVENT`. If the grouped split cannot achieve this, generate more scenarios or stratify at the **group** level. Never break a group.
4. **Temporal holdout.** Earlier scenarios train; later scenarios test (Doc 05 §52).
5. **Device holdout.** Train on some devices and test on another compatible device, **only where enough devices and data exist** (Doc 05 §51). Otherwise, state that it was not run.
6. **Conservative claims.** With a small prototype, results from physical-demo data are reported as preliminary.

## 16. Config and manifest

### 16.1 Labeling config

All parameters in this document live in `components/c1_credibility/configs/c1_labeling_v1.yaml`. The config has a `parameter_status` of `PROVISIONAL` or `APPROVED` and a `justification` entry for each value. `validate.py` **refuses to freeze** a dataset while any parameter is `PROVISIONAL`.

### 16.2 Dataset manifest

The manifest is generated by the build, never written by hand (Doc 05 §48). It contains:

- `dataset_code: C1_CREDIBILITY`, `version`, `schema_version`, `label_schema_version`
- `source_types`, `builder_version`, `random_seed`, `split_strategy: scenario_grouped`
- `row_count`, `file_hash`
- `labeling_spec_version` (this document) and `labeling_config_version`
- `label_counts` per class and per split
- `label_source_counts`
- `ambiguous_count` and per-reason counts
- `insufficient_context_count`
- `detectability_report` summary
- the sensor family and the calibration versions used

The manifest is stored in `data/manifests/`. Large generated data is not committed to Git (Doc 14 §39–40).

## 17. Out of scope

- Final model choice, training and evaluation (separate tickets).
- Rule and value-only baselines (mandatory, but after the dataset milestone, Doc 05 §128–129).
- Changes to shared contracts, enums, IDs, modes or the Golden Timeline. If a shared contract is insufficient, propose a versioned change for team review instead of editing it (Doc 05 §127, Doc 14 §19).

## 18. Version history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-10-15 | Initial specification |
| 1.1 | 2026-10-16 | Added Doc 05 §12 coverage map; excluded non-C1 fault types with rationale; added quantization/ADC fault family and sensor-level dropout definition; synthetic labels from generator truth; evidence rule limited to physical and annotated data; label precedence; VALID_EVENT parameters, negative cases and dynamics-based generation; multi-sensor event handling; ambiguous-case policy and flags; physical-demo and external-data labeling; Doc 03 §16–18 fields; complete leakage rules; detailed split rules; labeling config and manifest requirements; soil moisture as first sensor family |

## 19. Owner sign-off

- **Prepared by:** R. M. Kanishka Harshana
- **Reviewed by:** _(pending)_
- **Approved by:** _(pending)_