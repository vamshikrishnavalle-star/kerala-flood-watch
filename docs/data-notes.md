# Dataset Notes and Data Provenance

Generated: 2026-10-03

## 1. Label Definitions and Thresholds

Ground-truth water levels are derived from official CWC river gauge bulletins.

| Station | Station Code | District / Zone | Danger Level | Warning Level | HFL (Date) | Datum Series | Official Bulletin Source |
|:---|:---|:---|:---:|:---:|:---:|:---|:---|
| **KALLOOPPARA** | `017-SWRDKOCHI` | Pathanamthitta | 6.00 m | 5.00 m | 9.64 m (2018-08-16) | HHS (HZS=HHS, offset 0.00) | [CWC Flood Bulletin 17-10-2021](https://cwc.gov.in/sites/default/files/cfcrcwcdfb17-10-2021-2.pdf) |
| **KIDANGOOR** | `015-SWRDKOCHI` | Kottayam | 7.16 m | 6.16 m | 8.24 m (2020-08-09) | HHS series (matches HFL 8.24) | [CWC Flood Bulletin 17-10-2021](https://cwc.gov.in/sites/default/files/cfcrcwcdfb17-10-2021-2.pdf) |

### Leakage-Prevention Rule for Phase 3
> [!IMPORTANT]
> **Label Date Semantics**: The `date` column corresponds to the actual day on which the maximum river water level was observed.
> When building feature pipelines in Phase 3, **only data available strictly prior to the prediction time** (e.g. past weather up to $t-1$, or forecasts issued at or before prediction time) must be used as model inputs.

## 2. Data Sources and Download Information

| Dataset | Source Agency | Frequency / Resolution | Coverage Downloaded |
|:---|:---|:---|:---|
| River Gauge Water Levels | Central Water Commission (CWC) / India-WRIS | Hourly / Sub-daily readings | 2000-01-01 to 2024-12-31 (KALLOOPPARA), 2015-06-01 to 2024-12-31 (KIDANGOOR) |
| Historical Weather & Soil | Open-Meteo ERA5 Reanalysis Archive | Daily aggregates per district town | 2000-01-01 to 2024-12-31 |
| Zone Coordinates | `src/ingest/zones.py` | Point coordinates | Kozhencherry (9.3364 N, 76.6974 E), Pala (9.7100 N, 76.6800 E) |

## 3. Cleaning & Transformation Rules

1. **Approved Series Selection**: Only the verified matching datum series (`HHS`) is used for each station.
2. **Daily Aggregation**: `daily_max = max(readings)` across calendar day in IST.
3. **Monthly Regime Threshold**:
   - For each station-month, median daily reading count is computed.
   - If `median >= 12` readings/day: `regime = hourly`, minimum required readings $N = 12$.
   - If `median < 12` readings/day: `regime = 3perday`, minimum required readings $N = 3$.
4. **Strict Label Logic**:
   - `label = 1` if `daily_max >= threshold` (regardless of reading count).
   - `label = 0` if `daily_max < threshold` AND `n_readings >= N`.
   - `label = NaN` if `daily_max < threshold` AND `n_readings < N`.
5. **Zero Imputation**: Missing or NaN label days are strictly dropped (134 days dropped). No interpolation, forward-filling, oversampling, or synthetic augmentation.

## 4. Scope and Excluded Zones

Only zones with confirmed, official CWC bulletin danger levels are included in the labeled dataset.
The following monitored zones in `src/ingest/zones.py` lack official CWC danger levels or are excluded by design and remain unlabeled / excluded from ML training:
- **Idukki** (`idukki_cheruthoni` / VANDIPERIYAR): Gauge data exists, but no official threshold was located.
- **Wayanad** (`wayanad_vythiri` / MUTHANKERA): Excluded from training scope by project design.
- **Ernakulam** (`ernakulam_aluva` / KALAMPUR): Gauge data exists, but no official threshold was located.
- **Thrissur** (`thrissur_chalakudy` / ARANGALI): Gauge data exists, but no official threshold was located.
- **Alappuzha** (`alappuzha_kuttanad`): Excluded from training scope; no river gauge in scope.

## 5. Known Weaknesses and Limitations

1. **Pre-2015 Sampling Schedule**: Before 2015 the CWC series has 3 readings per day, so short peaks between readings can be missed. Pre-2015 days labeled 0 may therefore include unobserved exceedances (about 20 of the 47 Kalloopara danger events fall in this era). The monthly regime rule only controls which days are labeled NaN; it cannot recover unrecorded peaks. Results should be reported separately for the 3-per-day and hourly regimes.
2. **Single-Point District Weather**: Weather features represent ERA5 grid points at central district towns (Kozhencherry and Pala) rather than spatially distributed catchment-averaged rainfall.
3. **Download Horizon**: Dataset ends at 2024-12-31; 2025–2026 data has not been retrieved.
4. **ARANGALI 2018 Gap**: Station `011-SWRDKOCHI` has unrecorded gauge readings during the Aug 17–19, 2018 peak (confirmed from raw v3 data).
5. **No Satellite Inundation / DFO Cross-Verification**: Flood labels are hydro-gauge stage exceedances and have not been cross-matched against Dartmouth Flood Observatory (DFO) remote sensing footprints.
