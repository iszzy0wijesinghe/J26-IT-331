# C1 XGBoost Model — Evaluation Results

**Model:** XGBoost (multi:softprob)
**Dataset:** C1_CREDIBILITY_V0.2.0 (213,146 rows)
**Train/Val/Test:** 115,831 / 41,652 / 41,489
**Features:** 18 (after removing leakage features)
**Class Weights:** CLEAN=1.0, ANOMALY=10.0, VALID_EVENT=2.0

## Test Set Performance

| Class | Precision | Recall | F1-Score | Support |
|-------|-----------|--------|----------|---------|
| CLEAN | 0.97 | 0.98 | 0.97 | 36,901 |
| ANOMALY | 0.56 | 0.50 | 0.53 | 775 |
| VALID_EVENT | 0.78 | 0.76 | 0.77 | 3,813 |
| **Overall** | | | **0.95** | **41,489** |

## Confusion Matrix (Test)

| Actual \ Predicted | CLEAN | ANOMALY | VALID_EVENT |
|--------------------|-------|---------|-------------|
| **CLEAN** | 35,995 | 254 | 652 |
| **ANOMALY** | 215 | 386 | 174 |
| **VALID_EVENT** | 881 | 53 | 2,879 |

## Key Observations

1. **CLEAN detection is excellent** (F1=0.97) — majority class well learned.
2. **ANOMALY detection improved significantly** — from F1=0.03 (baseline) to 0.53 (with class weights).
3. **VALID_EVENT detection is good** (F1=0.77) — model distinguishes genuine events from anomalies.
4. **Main remaining challenge:** ANOMALY recall (0.50) — model still misses half of the anomalies. Future work: add more ANOMALY data or tune class weights further.

## Model Artifact

- Path: `models/c1/c1_xgboost_v1.json`
- Size: 1.67 MB