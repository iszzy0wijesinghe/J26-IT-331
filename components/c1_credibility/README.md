\# C1 — Rainfall Regime-Aware Sensor Credibility Classification



\## Research Problem

Determine whether an environmental sensor observation is credible (CLEAN),

anomalous/faulty (ANOMALY), or a genuine unusual environmental event (VALID\_EVENT).



\## Component Boundary

\- C1 assesses measurement credibility — NOT source authentication (that is C4).

\- C1 does NOT erase raw observations.

\- C1 output is an assessment attached to an observation.



\## Inputs

\- Normalized sensor observations (from ingestion)

\- Temporal context (past values, rate of change)

\- Neighbour context (same sensor family, same zone)

\- Rainfall context (calibrated rainfall features)

\- Device health context

\- C4 trust metadata (for gating)



\## Outputs

\- credibility\_label: CLEAN | ANOMALY | VALID\_EVENT

\- credibility\_score: probability/confidence

\- context\_status: COMPLETE | PARTIAL | INSUFFICIENT\_CONTEXT

\- reason\_codes: structured explanation

\- model\_version: version identifier



\## Target Classes

\- CLEAN — consistent with expected behaviour

\- ANOMALY — likely unreliable/erroneous/sensor fault

\- VALID\_EVENT — unusual but contextually supported environmental change



\## Dataset Versions

\- TBD (to be defined after audit)



\## Baseline Models

\- Rule/plausibility baseline

\- Value-only classifier

\- Temporal classifier

\- Random Forest

\- XGBoost/LightGBM (candidate)



\## Candidate Model

\- Context-aware classifier (TBD after experiments)



\## Training Command

TBD



\## Evaluation Command

TBD



\## Runtime Interface

TBD



\## Known Limitations

\- Limited physical deployment scale

\- Synthetic-data dependence (initially)

\- Only two prototype zones

\- Sensor calibration uncertainty



\## Owner

\- R. M. Kanishka Harshana Kumarasinghe (C1)

