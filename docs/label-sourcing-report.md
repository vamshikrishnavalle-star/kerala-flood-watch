# Phase 2 Label Sourcing Report
Generated: 2026-10-03

## 1. Source PDFs

| PDF | Bulletin Date | Stations Found |
|:---|:---|:---|
| cfcrcwcdfb17-10-2021-2.pdf | 2021-10-17 | KALLOOPPARA p.3 Severe Flood, KIDANGOOR p.4 Above Normal |
| cfcrcwcdfb15-11-2021-2.pdf | 2021-11-15 | KALLOOPPARA p.4 Above Normal |
| cfcrcwcdfb19-10-2021_2.pdf | 2021-10-19 | KALLOOPPARA p.4 Above Normal |

## 2. Official Levels (danger_levels_manual.csv)

| Station | Zone | Danger (m) | Warning (m) | HFL (m) | HFL Date | Datum |
|:---|:---|:---|:---|:---|:---|:---|
| KALLOOPPARA | Pathanamthitta | 6.0 | 5.0 | 9.64 | 2018-08-16 | HHS series (HZS=HHS, offset 0.00; matches HFL 9.64 on 2018-08-16) |
| KIDANGOOR   | Kottayam       | 7.16 | 6.16 | 8.24 | 2020-08-09 | HHS series (matches HFL 8.24 on 2020-08-09) |

> Provisional: levels from CWC Daily Flood Bulletin table columns. Not cross-referenced with CWC Level Forecast Sites register.

## 3. Datum Check

| Station | Series | HFL (bulletin) | HFL Date | HZS max | HHS max |
|:---|:---|:---|:---|:---|:---|
| KALLOOPPARA | HHS | 9.64 | 2018-08-16 | 9.6400 (offset 0.00) | 9.6400 |
| KIDANGOOR   | HHS | 8.24 | 2020-08-09 | 9.4400 (diff 1.20, no match) | 8.2400 |

## 4. ARANGALI Aug 17-19 2018

API re-verification failed (HTTP 400 for Ernakulam and Thrissur); gap confirmed from v3 data (Aug 17/18/19 show no rows in downloaded dataset); no official level, so unlabeled.

## 5. Labels -- data/processed/labels_daily.csv

**NaN rule (monthly regime):** per station-month, compute median daily reading count.
If median >= 12: N=12 (hourly). Else N=3 (3perday).
label=1 if daily_max>=level; label=0 if below and n_readings>=N; label=NaN otherwise.
No interpolation, no forward-fill. Missing readings -> NaN -> dropped.

| Station | Zone | Series | Danger | Warning | Total days | Labeled | NaN | >=Danger | >=Warning |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| KALLOOPPARA | Pathanamthitta | HHS | 6.0 | 5.0 | 9010 | 8958 | 52 | 116 | 246 |
| KIDANGOOR   | Kottayam       | HHS | 7.16 | 6.16 | 3253 | 3171 | 82 | 14 | 42 |

## 6. Zones Without Official Levels

| Station | Code | District | Coverage |
|:---|:---|:---|:---|
| VANDIPERIYAR | 016-SWRDKOCHI | Idukki     | HHS+HZS 2000- |
| KALAMPUR     | 013-SWRDKOCHI | Ernakulam  | HHS+HZS 2015- |
| ARANGALI     | 011-SWRDKOCHI | Thrissur   | HZS 2015- |
| KUMBIDI      | 008-SWRDKOCHI | Palakkad   | HZS 2009- |
| KARATHODU    | 006-SWRDKOCHI | Malappuram | HZS 2009- |

Zones in src/ingest/zones.py with no valid gauge: Idukki, Wayanad (excluded), Ernakulam, Thrissur, Alappuzha.

## 7. Known Gaps

| Gap | Detail |
|:---|:---|
| Download end | v3 ends 2024-12-31 |
| Pre-2015 obs schedule | 3 obs/day; NaN rule uses monthly regime |
| NaN days | KALLOOPPARA 52, KIDANGOOR 82 |
| Datum provisional | Not cross-referenced with CWC Level Forecast Sites register |
| Total danger days | 130 (MET) |
| 5 of 7 stations unlabeled | No confirmed official level |
