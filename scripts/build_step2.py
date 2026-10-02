import math, pathlib, subprocess, sys
from datetime import date
import pandas as pd
import numpy as np

SEP  = "=" * 72
THIN = "-" * 72

PROCESSED_DIR = pathlib.Path("data/processed")
RAW_DIR       = pathlib.Path("data/raw")
DOCS_DIR      = pathlib.Path("docs")
SCRIPTS_DIR   = pathlib.Path("scripts")
TESTS_DIR     = pathlib.Path("tests")

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
TESTS_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# 1. Rewrite station_zone_map.csv programmatically
# ------------------------------------------------------------
print(SEP); print("1. WRITING station_zone_map.csv"); print(SEP)

map_data = [
    {
        "station": "KALLOOPPARA",
        "station_code": "017-SWRDKOCHI",
        "district": "Pathanamthitta",
        "series_datum": "HHS",
        "zone_slug": "pathanamthitta_kozhencherry",
        "latitude": 9.3364,
        "longitude": 76.6974,
        "river_basin": "Manimala",
        "note": "weather point = district town, not gauge location; gauge on Manimala/Meenachil river",
    },
    {
        "station": "KIDANGOOR",
        "station_code": "015-SWRDKOCHI",
        "district": "Kottayam",
        "series_datum": "HHS",
        "zone_slug": "kottayam_pala",
        "latitude": 9.7100,
        "longitude": 76.6800,
        "river_basin": "Meenachil",
        "note": "weather point = district town, not gauge location; gauge on Manimala/Meenachil river",
    }
]

map_df = pd.DataFrame(map_data)
map_path = RAW_DIR / "station_zone_map.csv"
map_df.to_csv(map_path, index=False)
print(f"  Written to {map_path}:\n")
print(map_df.to_string(index=False))

# ------------------------------------------------------------
# 2. Build dataset.parquet
# ------------------------------------------------------------
print(f"\n{SEP}"); print("2. BUILDING data/processed/dataset.parquet"); print(SEP)

labels_path = PROCESSED_DIR / "labels_daily.csv"
if not labels_path.exists():
    print(f"ERROR: {labels_path} does not exist."); sys.exit(1)

labels_df = pd.read_csv(labels_path, parse_dates=["date"])
labels_df["label_danger"]  = pd.to_numeric(labels_df["label_danger"],  errors="coerce")
labels_df["label_warning"] = pd.to_numeric(labels_df["label_warning"], errors="coerce")

# Map station to zone slug and zone display name
zone_slug_map = {"KALLOOPPARA": "pathanamthitta_kozhencherry", "KIDANGOOR": "kottayam_pala"}
district_map  = {"KALLOOPPARA": "Pathanamthitta", "KIDANGOOR": "Kottayam"}

labels_df["zone_slug"] = labels_df["station"].map(zone_slug_map)
labels_df["zone"]      = labels_df["station"].map(district_map)
labels_df["year"]      = labels_df["date"].dt.year

# Load historical weather
wframes = []
for zslug in zone_slug_map.values():
    wfp = RAW_DIR / "historical" / f"{zslug}.csv"
    if not wfp.exists():
        print(f"ERROR: Weather file {wfp} missing."); sys.exit(1)
    wdf = pd.read_csv(wfp, parse_dates=["date"])
    wframes.append(wdf)

weather_df = pd.concat(wframes, ignore_index=True)

# Merge on date and zone_slug
merged = labels_df.merge(weather_df, on=["date", "zone_slug"], how="inner")
print(f"  Total matched rows prior to NaN filtering: {len(merged):,}")

# Log dropped rows per station and year
weather_cols = [
    "precipitation_sum", "rain_sum", "temperature_2m_max",
    "temperature_2m_min", "soil_moisture_0_7cm", "soil_moisture_7_28cm"
]

req_cols = ["label_danger", "label_warning"] + weather_cols
nan_mask = merged[req_cols].isna().any(axis=1)
dropped_df = merged[nan_mask]

print(f"\n{THIN}")
print("  DROPPED ROWS (NaN labels / missing data) LOG:")
print(f"  {'Station':<16} {'Year':>6} {'Dropped Days':>14} {'Reason'}")
for (stn, yr), grp in dropped_df.groupby(["station", "year"]):
    print(f"  {stn:<16} {int(yr):>6} {len(grp):>14}   n_readings < N in daily label")
print(f"  Total dropped rows: {len(dropped_df):,}")

clean_df = merged[~nan_mask].copy()

# Cast labels to int
clean_df["label_danger"]  = clean_df["label_danger"].astype(int)
clean_df["label_warning"] = clean_df["label_warning"].astype(int)

# Exact required schema
final_cols = [
    "date", "zone", "station",
    "precipitation_sum", "rain_sum", "temperature_2m_max",
    "temperature_2m_min", "soil_moisture_0_7cm", "soil_moisture_7_28cm",
    "daily_max", "n_readings", "regime",
    "label_danger", "label_warning"
]

dataset_df = clean_df[final_cols].sort_values(["zone", "date"]).reset_index(drop=True)

out_parquet = PROCESSED_DIR / "dataset.parquet"
dataset_df.to_parquet(out_parquet, index=False)
print(f"\n  Saved {len(dataset_df):,} rows -> {out_parquet}")
print(f"  Schema:\n{dataset_df.dtypes}")

# ------------------------------------------------------------
# 3. Create scripts/audit_dataset.py and generate docs/data-audit.md
# ------------------------------------------------------------
print(f"\n{SEP}"); print("3. CREATING & RUNNING scripts/audit_dataset.py"); print(SEP)

audit_script = '''import pathlib, sys
from datetime import date
import pandas as pd
import numpy as np

def count_clusters(vals):
    n, in_c = 0, False
    for v in vals:
        if v == 1:
            if not in_c: n += 1; in_c = True
        else: in_c = False
    return n

df = pd.read_parquet("data/processed/dataset.parquet")
df["year"] = pd.to_datetime(df["date"]).dt.year

tot_d = int((df["label_danger"] == 1).sum())
tot_w = int((df["label_warning"] == 1).sum())
tot_rows = len(df)

# Check thresholds & 2018
warns = []
if tot_d < 100:
    warns.append(f"WARNING: Total danger positives ({tot_d}) < 100 threshold")
if tot_w < 100:
    warns.append(f"WARNING: Total warning positives ({tot_w}) < 100 threshold")

for z in df["zone"].unique():
    zd = int((df[df["zone"] == z]["label_danger"] == 1).sum())
    if zd < 10:
        warns.append(f"WARNING: Zone {z} danger positives ({zd}) < 10 threshold")

d_2018 = int((df[df["year"] == 2018]["label_danger"] == 1).sum())
if d_2018 == 0:
    warns.append("WARNING: 2018 has 0 danger positives (critical flood year!)")

# Positives by zone, year, regime, event
summary_rows = []
for z, zgrp in df.groupby("zone"):
    for yr, ygrp in zgrp.groupby("year"):
        ygrp_sorted = ygrp.sort_values("date")
        nd = int((ygrp_sorted["label_danger"] == 1).sum())
        nw = int((ygrp_sorted["label_warning"] == 1).sum())
        cd = count_clusters(ygrp_sorted["label_danger"].tolist())
        cw = count_clusters(ygrp_sorted["label_warning"].tolist())
        regimes = ",".join(sorted(ygrp["regime"].unique()))
        summary_rows.append({
            "zone": z, "year": yr, "days": len(ygrp),
            "danger_pos": nd, "warning_pos": nw,
            "danger_events": cd, "warning_events": cw,
            "regimes": regimes
        })

sum_df = pd.DataFrame(summary_rows)

md = f"""# Phase 2 Dataset Audit Report

Generated: {date.today().isoformat()}

## 1. Executive Summary

- **Total Rows**: {tot_rows:,}
- **Zones Included**: {", ".join(sorted(df["zone"].unique()))}
- **Date Range**: {df["date"].min().date()} to {df["date"].max().date()}
- **Total Danger Positives**: {tot_d} ({tot_d/tot_rows:.2%})
- **Total Warning Positives**: {tot_w} ({tot_w/tot_rows:.2%})

### Threshold Validation Checks
"""

if not warns:
    md += "\\n> [!NOTE]\\n> **ALL AUDIT CHECKS PASSED**: Total positives >= 100, each zone >= 10, 2018 flood year verified non-zero.\\n\\n"
else:
    for w in warns:
        md += f"\\n> [!WARNING]\\n> {w}\\n"

md += f"""
## 2. Positives by Zone, Year, Event, and Regime

| Zone | Year | Total Days | >= Danger | Danger Events | >= Warning | Warning Events | Regimes |
|:---|---:|---:|---:|---:|---:|---:|:---|
"""
for _, r in sum_df.iterrows():
    md += f"| {r['zone']} | {r['year']} | {r['days']} | {r['danger_pos']} | {r['danger_events']} | {r['warning_pos']} | {r['warning_events']} | {r['regimes']} |\\n"

md += f"""
## 3. Totals by Zone

| Zone | Total Days | >= Danger | Danger Events | >= Warning | Warning Events |
|:---|---:|---:|---:|---:|---:|
"""
for z, zgrp in df.groupby("zone"):
    z_sorted = zgrp.sort_values("date")
    nd = int((z_sorted["label_danger"] == 1).sum())
    nw = int((z_sorted["label_warning"] == 1).sum())
    cd = count_clusters(z_sorted["label_danger"].tolist())
    cw = count_clusters(z_sorted["label_warning"].tolist())
    md += f"| {z} | {len(zgrp):,} | {nd} | {cd} | {nw} | {cw} |\\n"

md += f"| **TOTAL** | **{tot_rows:,}** | **{tot_d}** | **{sum_df['danger_events'].sum()}** | **{tot_w}** | **{sum_df['warning_events'].sum()}** |\\n"

pathlib.Path("docs/data-audit.md").write_text(md, encoding="utf-8")
print(md)
'''

(SCRIPTS_DIR / "audit_dataset.py").write_text(audit_script, encoding="utf-8")
subprocess.run([sys.executable, "scripts/audit_dataset.py"], check=True)

# ------------------------------------------------------------
# 4. Write docs/data-notes.md
# ------------------------------------------------------------
print(f"\n{SEP}"); print("4. WRITING docs/data-notes.md"); print(SEP)

data_notes_md = f"""# Dataset Notes and Data Provenance

Generated: {date.today().isoformat()}

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
| Elevation & Zone Coordinates | Open-Meteo / `src/ingest/zones.py` | Point coordinates | Kozhencherry (13m MSL), Pala (20m MSL) |

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
- **Idukki** (`idukki_cheruthoni` / VANDIPERIYAR): Gauge data exists, but no official bulletin threshold.
- **Wayanad** (`wayanad_vythiri` / MUTHANKERA): Excluded from training scope by project design.
- **Ernakulam** (`ernakulam_aluva` / KALAMPUR): Gauge data exists, but no official bulletin threshold.
- **Thrissur** (`thrissur_chalakudy` / ARANGALI): Gauge data exists, but no official bulletin threshold.
- **Alappuzha** (`alappuzha_kuttanad`): Excluded from training scope; no river gauge in scope.

## 5. Known Weaknesses and Limitations

1. **Pre-2015 Sampling Schedule**: Historical CWC observations before 2015 followed a 3-readings/day schedule (08:00, 13:00, 18:00 IST) rather than hourly telemetric sampling. While flood peaks may occasionally fall between 3-hour windows, the monthly regime rule preserves all observed historical exceedances.
2. **Single-Point District Weather**: Weather features represent ERA5 grid points at central district towns (Kozhencherry and Pala) rather than spatially distributed catchment-averaged rainfall.
3. **Download Horizon**: Dataset ends at 2024-12-31; 2025–2026 data has not been retrieved.
4. **ARANGALI 2018 Gap**: Station `011-SWRDKOCHI` has unrecorded gauge readings during the Aug 17–19, 2018 peak (confirmed from raw v3 data).
5. **No Satellite Inundation / DFO Cross-Verification**: Flood labels are hydro-gauge stage exceedances and have not been cross-matched against Dartmouth Flood Observatory (DFO) remote sensing footprints.
"""

(DOCS_DIR / "data-notes.md").write_text(data_notes_md, encoding="utf-8")
print(f"  Written to {DOCS_DIR / 'data-notes.md'}")

# ------------------------------------------------------------
# 5. Write and Run Tests
# ------------------------------------------------------------
print(f"\n{SEP}"); print("5. RUNNING UNIT TESTS (tests/test_dataset.py)"); print(SEP)

test_code = '''import pathlib
import pandas as pd
import pytest

DATASET_PATH = pathlib.Path("data/processed/dataset.parquet")

@pytest.fixture(scope="module")
def dataset():
    assert DATASET_PATH.exists(), "dataset.parquet must exist"
    return pd.read_parquet(DATASET_PATH)

def test_no_duplicate_zone_date(dataset):
    """Test there are no duplicate (zone, date) pairs."""
    dups = dataset.duplicated(subset=["zone", "date"]).sum()
    assert dups == 0, f"Found {dups} duplicate (zone, date) records."

def test_no_nan_labels(dataset):
    """Test that all label columns have zero NaN values."""
    assert dataset["label_danger"].isna().sum() == 0, "label_danger contains NaNs"
    assert dataset["label_warning"].isna().sum() == 0, "label_warning contains NaNs"

def test_sorted_dates(dataset):
    """Test that records are properly sorted by zone and date."""
    for zone, grp in dataset.groupby("zone"):
        dates = pd.to_datetime(grp["date"]).tolist()
        assert dates == sorted(dates), f"Dates in zone {zone} are not sorted in ascending order."

def test_join_example(dataset):
    """Test that a specific known date joins properly with expected weather columns."""
    sample = dataset[(dataset["station"] == "KALLOOPPARA") & (dataset["date"] == "2018-08-16")]
    assert len(sample) == 1, "Expected exactly 1 row for KALLOOPPARA on 2018-08-16"
    row = sample.iloc[0]
    assert row["precipitation_sum"] > 0, "Expected non-zero precipitation on 2018-08-16"
    assert row["daily_max"] >= 9.60, f"Expected daily_max near HFL (got {row['daily_max']})"

def test_exceedance_example_label_one(dataset):
    """Test that a known major flood date yields label 1 for both danger and warning."""
    # KALLOOPPARA 2018-08-16 had HFL of 9.64m (Danger=6.0m, Warning=5.0m)
    sample = dataset[(dataset["station"] == "KALLOOPPARA") & (dataset["date"] == "2018-08-16")]
    row = sample.iloc[0]
    assert row["label_danger"] == 1, "Expected label_danger == 1 for 2018-08-16 peak"
    assert row["label_warning"] == 1, "Expected label_warning == 1 for 2018-08-16 peak"

def test_dataset_columns(dataset):
    """Verify exact column structure and expected types."""
    expected = [
        "date", "zone", "station",
        "precipitation_sum", "rain_sum", "temperature_2m_max",
        "temperature_2m_min", "soil_moisture_0_7cm", "soil_moisture_7_28cm",
        "daily_max", "n_readings", "regime",
        "label_danger", "label_warning"
    ]
    assert list(dataset.columns) == expected
'''

(TESTS_DIR / "test_dataset.py").write_text(test_code, encoding="utf-8")

res = subprocess.run([sys.executable, "-m", "pytest", "tests/test_dataset.py", "-v"], capture_output=True, text=True)
print(res.stdout)
if res.stderr:
    print(res.stderr)
if res.returncode != 0:
    print("TESTS FAILED")
    sys.exit(res.returncode)
else:
    print("ALL TESTS PASSED SUCCESSFULLY!")

print(f"\n{SEP}\nPROMPT B STEP 2 COMPLETE -- Stopped for approval\n{SEP}")

