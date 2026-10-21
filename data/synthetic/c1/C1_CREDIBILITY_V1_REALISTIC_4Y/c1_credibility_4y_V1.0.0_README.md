# C1 credibility dataset, 4 years (V1.0.0)

File: `c1_credibility_4y_V1.0.0.csv` (also `.csv.gz`). 330,102 rows, 45 columns.
Period 2021-01-01 to 2024-12-31, one site (ZONE-A), 5 soil-moisture sensors.

**Provenance.** Synthetic. Parameters were calibrated on the uploaded real 20 cm moisture
and rainfall files. Labels come from the generator truth. `source_origin = SYNTHETIC` in every
row. Do not report results on it as field data. Cite the real dataset you calibrated on and
check its licence.

## What was taken from the real files
| Quantity | Real files | This dataset |
|---|---|---|
| Rain per year | about 633 mm (793 mm in 15 months) | 647 mm |
| Rain episodes per year | about 183 | 175 |
| Episode size (median / p90) | 1.4 mm / 9.7 mm | lognormal fitted to those |
| Moisture 30-min change std (sensor 1) | 0.00063 | 0.00054 |
| Sensor resolution | about 0.01 % VWC | 0.01 % VWC |
| Response to rain | peak about 20 h after the rain | two reservoirs, peak about 14-17 h |
| Rise after storms of 8 mm or more | 1-5 % VWC | gains set per sensor |
| Season | wet winter, dry summer | antecedent-rain wetness plus summer evapotranspiration |
| Outages | real gaps up to 118 days | random outages, rows not delivered |
| Spikes | sensor 3 jumps up to 15 % | spikes 3-15 % |

## Layout (same 45 columns as the previous C1 dataset, train.py works unchanged)
The 18 model features are: dt_s, value, delta_prev_pct_per_min, baseline_mean, baseline_std,
value_minus_baseline, stuck_run_len, rain_15m_mm, rain_1h_mm, rain_3h_mm, steps_since_rain,
n_neighbours_fresh, neighbour_consensus_change, target_minus_consensus,
neighbour_change_spread, neighbour_rise_agree_frac, device_voltage, history_obs.

- Sampling follows operating modes (provisional intervals, Doc 04 does not freeze them):
  DEEP_SLEEP 120 min (after 5 dry days), IDLE 30 min, RISK 10 min, WARNING 5 min.
  So `dt_s` takes the values 7200, 1800, 600 and 300.
- baseline_* use the last 12 reported observations, so their time span depends on the mode.
- `value` is in % VWC (real files use a 0-1 fraction).
- `split` = month blocks, grouped. `split_temporal` = earliest 60 % train, then val, last test.
  `split_device` holds out 2 of the 5 sensors. Use `split_temporal` for the strictest test.
- `rainfall_regime` is empty. The regime thresholds need real NBRO evidence.

## Cleaning rules (the file has logger mess on purpose)
1. Drop duplicate `record_id` (983 retransmitted rows).
2. Drop rows with an empty `credibility_label` (1,311 error-code rows with null, -999 or 65535).
3. Keep `train_eligible == 1`. Do NOT drop null `value` rows that have a label,
   those are real DROPOUT faults (ANOMALY).
4. Use the `split` columns, never a random row split.

## Known limits
- One site and five sensors, so little spatial diversity.
- Faults are injected at about 3.9 % of rows, more than a real deployment.
- Rain is UK-like in structure. Sri Lankan monsoon rainfall is heavier and needs local records.
- The sensor 3 regime shift in the real data was not reproduced as a separate behaviour.
