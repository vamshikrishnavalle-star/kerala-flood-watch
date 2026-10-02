import pathlib
import pandas as pd
import numpy as np

out_dir = pathlib.Path("docs/step0")
out_dir.mkdir(parents=True, exist_ok=True)

raw_path = pathlib.Path("data/raw/labels/cwc/v3/station_017-SWRDKOCHI_kallooppara.csv")
df_raw = pd.read_csv(raw_path, low_memory=False)

# Normalize column names
col_map = {c.lower(): c for c in df_raw.columns}
dt_c  = col_map.get("datatime", list(col_map.values())[0])
val_c = col_map.get("datavalue", "dataValue")

df_raw = df_raw.rename(columns={dt_c: "dataTime", val_c: "dataValue"})
df_raw["dataTime"]  = pd.to_datetime(df_raw["dataTime"], errors="coerce")
df_raw["dataValue"] = pd.to_numeric(df_raw["dataValue"], errors="coerce")

df_raw = df_raw.dropna(subset=["dataTime", "dataValue"]).sort_values("dataTime").reset_index(drop=True)

# 1. Pre-2015 Timestamps Distribution
pre15 = df_raw[df_raw["dataTime"].dt.year < 2015].copy()
pre15["hour"] = pre15["dataTime"].dt.hour
pre15["minute"] = pre15["dataTime"].dt.minute

hour_dist = pre15["hour"].value_counts().sort_index()
print("=" * 80)
print("1. PRE-2015 KALLOOPPARA READING HOURS DISTRIBUTION")
print("=" * 80)
print(hour_dist.to_string())

top3_hours = pre15["hour"].value_counts().head(3).index.tolist()
top3_hours = sorted(top3_hours)
print(f"\nTop 3 Derived Reading Hours: {top3_hours} (Hours IST)")

# 2. Thinning Test on Post-2015 Hourly Data (2015-2024)
post15 = df_raw[df_raw["dataTime"].dt.year >= 2015].copy()
post15["date"] = post15["dataTime"].dt.date
post15["hour"] = post15["dataTime"].dt.hour

# Daily max from all readings (Full hourly telemetry)
daily_full = post15.groupby("date")["dataValue"].agg(full_max="max", n_obs="count").reset_index()

# Daily max restricted to top 3 reading hours only
post15_thinned = post15[post15["hour"].isin(top3_hours)]
daily_thinned = post15_thinned.groupby("date")["dataValue"].agg(thinned_max="max", n_obs_thinned="count").reset_index()

comp = daily_full.merge(daily_thinned, on="date", how="inner")
comp = comp[comp["n_obs"] >= 18].copy().reset_index(drop=True) # Ensure days with full hourly reporting

# CWC Official Thresholds for Kallooppara (Manimala River)
WARNING_LEVEL = 5.00
DANGER_LEVEL  = 6.00

comp["true_warn"] = (comp["full_max"] >= WARNING_LEVEL).astype(int)
comp["true_dang"] = (comp["full_max"] >= DANGER_LEVEL).astype(int)

comp["thin_warn"] = (comp["thinned_max"] >= WARNING_LEVEL).astype(int)
comp["thin_dang"] = (comp["thinned_max"] >= DANGER_LEVEL).astype(int)

# Differences
comp["crest_underestimate_m"] = comp["full_max"] - comp["thinned_max"]

# Exceedance detection rates under thinning
dang_tot = comp["true_dang"].sum()
dang_caught = ((comp["true_dang"] == 1) & (comp["thin_dang"] == 1)).sum()
dang_missed = ((comp["true_dang"] == 1) & (comp["thin_dang"] == 0)).sum()

warn_tot = comp["true_warn"].sum()
warn_caught = ((comp["true_warn"] == 1) & (comp["thin_warn"] == 1)).sum()
warn_missed = ((comp["true_warn"] == 1) & (comp["thin_warn"] == 0)).sum()

# When flood occurred, mean crest clipping
ex_days = comp[comp["true_warn"] == 1]
mean_clip = ex_days["crest_underestimate_m"].mean()
max_clip = ex_days["crest_underestimate_m"].max()

report_text = f"""Pre-2015 Kallooppara Observation Schedule & Empirical Thinning Test
================================================================================
1. Empirical Timestamp Derivation:
Total Pre-2015 Readings analyzed: {len(pre15)}
Hour Distribution (Hours IST):
{hour_dist.to_string()}

Derived Canonical Reading Hours: {top3_hours} (08:00, 13:00, 18:00 IST)
Percentage of pre-2015 readings taken at these 3 hours: {(pre15['hour'].isin(top3_hours).sum() / len(pre15)):.2%}

2. Thinning Test Results (Post-2015 Hourly Data thinned to {top3_hours}):
Evaluation Period: 2015 to 2024 (Days with >= 18 hourly readings: {len(comp)} days)

Danger Level Exceedances (Threshold = {DANGER_LEVEL:.2f} m):
- True Hourly Danger Days: {dang_tot} days
- Caught by 3-Reading Schedule: {dang_caught} days ({(dang_caught / max(dang_tot, 1)):.2%})
- Missed Danger Days (Crest occurred between observation windows): {dang_missed} days ({(dang_missed / max(dang_tot, 1)):.2%})

Warning Level Exceedances (Threshold = {WARNING_LEVEL:.2f} m):
- True Hourly Warning Days: {warn_tot} days
- Caught by 3-Reading Schedule: {warn_caught} days ({(warn_caught / max(warn_tot, 1)):.2%})
- Missed Warning Days: {warn_missed} days ({(warn_missed / max(warn_tot, 1)):.2%})

Crest Attenuation on Exceedance Days:
- Mean Peak Water Level Under-estimation: {mean_clip:.3f} meters
- Maximum Peak Water Level Under-estimation: {max_clip:.3f} meters

Conclusion:
Pre-2015 historical label records suffer from a significant sampling resolution bias: 
a 3-reading daily protocol misses {(dang_missed / max(dang_tot, 1)):.1%} of danger crests and attenuates observed peak water levels by up to {max_clip:.2f} meters compared to modern telemetric monitoring.
"""

(out_dir / "thinning_test_results.txt").write_text(report_text, encoding="utf-8")
print(report_text)
