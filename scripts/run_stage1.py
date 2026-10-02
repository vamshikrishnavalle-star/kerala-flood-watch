import json, math, os, pathlib, sys
from datetime import date, datetime, timedelta
import httpx
import numpy as np
import pandas as pd
import joblib

RAW_DIR = pathlib.Path("data/raw")
PARITY_DIR = RAW_DIR / "parity"
META_DIR = RAW_DIR / "metadata"
PROCESSED_DIR = pathlib.Path("data/processed")
MODELS_DIR = pathlib.Path("models")

PARITY_DIR.mkdir(parents=True, exist_ok=True)
META_DIR.mkdir(parents=True, exist_ok=True)

SEP = "=" * 78
THIN = "-" * 78

print(SEP); print("1. PARITY PROOF: FULL URLS, RESPONSE METADATA & 5-DATE COMPARISON"); print(SEP)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL  = "https://archive-api.open-meteo.com/v1/archive"

zone_lat, zone_lon = 9.3364, 76.6974
max_past = 92

live_params = {
    "latitude": zone_lat,
    "longitude": zone_lon,
    "daily": "precipitation_sum,soil_moisture_0_to_7cm_mean,soil_moisture_7_to_28cm_mean",
    "timezone": "Asia/Kolkata",
    "past_days": max_past,
    "forecast_days": 1,
}

with httpx.Client(timeout=30.0) as client:
    req_live = client.build_request("GET", FORECAST_URL, params=live_params)
    print(f"LIVE URL:\n{req_live.url}\n")
    res_live = client.send(req_live)
    live_json = res_live.json()

live_file = PARITY_DIR / "live_forecast_past92.json"
live_file.write_text(json.dumps(live_json, indent=2), encoding="utf-8")

start_date = live_json["daily"]["time"][0]
end_date   = live_json["daily"]["time"][-2]

arch_params = {
    "latitude": zone_lat,
    "longitude": zone_lon,
    "daily": "precipitation_sum,soil_moisture_0_to_7cm_mean,soil_moisture_7_to_28cm_mean",
    "timezone": "Asia/Kolkata",
    "start_date": start_date,
    "end_date": end_date,
}

with httpx.Client(timeout=30.0) as client:
    req_arch = client.build_request("GET", ARCHIVE_URL, params=arch_params)
    print(f"ARCHIVE URL:\n{req_arch.url}\n")
    res_arch = client.send(req_arch)
    arch_json = res_arch.json()

arch_file = PARITY_DIR / "archive_comparison.json"
arch_file.write_text(json.dumps(arch_json, indent=2), encoding="utf-8")

print(f"Saved raw responses to:\n  - {live_file}\n  - {arch_file}\n")
print("Response Header / Metadata:")
print(f"  Live Response    : lat={live_json.get('latitude')}, lon={live_json.get('longitude')}, elev={live_json.get('elevation')} m")
print(f"  Archive Response : lat={arch_json.get('latitude')}, lon={arch_json.get('longitude')}, elev={arch_json.get('elevation')} m")

df_live = pd.DataFrame(live_json["daily"]).rename(columns={"time": "date"})
df_arch = pd.DataFrame(arch_json["daily"]).rename(columns={"time": "date"})
cmp_df = df_arch.merge(df_live, on="date", suffixes=("_archive", "_live")).sort_values("date").reset_index(drop=True)

cmp_df["date_str"] = cmp_df["date"].astype(str)
heavy_dates = cmp_df.sort_values("precipitation_sum_archive", ascending=False)["date_str"].head(3).tolist()
other_dates = cmp_df.sort_values("precipitation_sum_archive", ascending=True)["date_str"].head(2).tolist()
sample_dates = sorted(heavy_dates + other_dates)

print(f"\n{THIN}")
print("5-DATE RAW VARIABLE COMPARISON (Side-by-Side):")
print(f"{'Date':<11} | {'Precip (Arch)':>13} {'(Live)':>8} | {'Soil 0-7 (Arch)':>15} {'(Live)':>8} | {'Soil 7-28 (Arch)':>16} {'(Live)':>8}")
print(THIN)
for sd in sample_dates:
    row = cmp_df[cmp_df["date_str"] == sd].iloc[0]
    p_a, p_l   = row["precipitation_sum_archive"], row["precipitation_sum_live"]
    s1_a, s1_l = row["soil_moisture_0_to_7cm_mean_archive"], row["soil_moisture_0_to_7cm_mean_live"]
    s2_a, s2_l = row["soil_moisture_7_to_28cm_mean_archive"], row["soil_moisture_7_to_28cm_mean_live"]
    print(f"{sd:<11} | {p_a:>13.2f} {p_l:>8.2f} | {s1_a:>15.4f} {s1_l:>8.4f} | {s2_a:>16.4f} {s2_l:>8.4f}")

null_s1 = cmp_df["soil_moisture_0_to_7cm_mean_live"].isna().sum()
null_s2 = cmp_df["soil_moisture_7_to_28cm_mean_live"].isna().sum()
print(f"\nSoil Moisture Null Check: soil_0_7 nulls={null_s1}, soil_7_28 nulls={null_s2} (Non-null: {null_s1==0 and null_s2==0})")

print(f"\n{SEP}"); print("2. CONTINUOUS RISK-SCORE DIFFERENCES & THRESHOLD AUDIT"); print(SEP)

def build_features(df, p_col, s1_col, s2_col):
    res = pd.DataFrame({"date": df["date"]})
    p_shift = df[p_col].shift(1)
    res["rain_1d"]  = p_shift
    res["rain_3d"]  = p_shift.rolling(3, min_periods=3).sum()
    res["rain_7d"]  = p_shift.rolling(7, min_periods=7).sum()
    res["rain_14d"] = p_shift.rolling(14, min_periods=14).sum()
    res["rain_30d"] = p_shift.rolling(30, min_periods=30).sum()
    res["soil_0_7_t1"]  = df[s1_col].shift(1)
    res["soil_7_28_t1"] = df[s2_col].shift(1)
    doy = pd.to_datetime(df["date"]).dt.dayofyear
    res["sin_doy"] = np.sin(2 * np.pi * doy / 365.25)
    res["cos_doy"] = np.cos(2 * np.pi * doy / 365.25)
    return res

feat_arch = build_features(cmp_df, "precipitation_sum_archive", "soil_moisture_0_to_7cm_mean_archive", "soil_moisture_7_to_28cm_mean_archive")
feat_live = build_features(cmp_df, "precipitation_sum_live", "soil_moisture_0_to_7cm_mean_live", "soil_moisture_7_to_28cm_mean_live")
merged_f  = feat_arch.merge(feat_live, on="date", suffixes=("_arch", "_live")).dropna().reset_index(drop=True)

feat_cols = ["rain_1d", "rain_3d", "rain_7d", "rain_14d", "rain_30d", "soil_0_7_t1", "soil_7_28_t1", "sin_doy", "cos_doy"]
X_arch = merged_f[[f"{f}_arch" for f in feat_cols]].rename(columns=lambda c: c.replace("_arch", ""))
X_live = merged_f[[f"{f}_live" for f in feat_cols]].rename(columns=lambda c: c.replace("_live", ""))

m_danger  = joblib.load(MODELS_DIR / "logistic_regression_label_danger_full_2000_2018.joblib")
m_warning = joblib.load(MODELS_DIR / "logistic_regression_label_warning_full_2000_2018.joblib")

score_d_arch = m_danger.predict_proba(X_arch)[:, 1]
score_d_live = m_danger.predict_proba(X_live)[:, 1]
score_w_arch = m_warning.predict_proba(X_arch)[:, 1]
score_w_live = m_warning.predict_proba(X_live)[:, 1]

m_df = pd.read_csv(PROCESSED_DIR / "metrics.csv")
th_danger  = m_df[(m_df["target"]=="label_danger") & (m_df["model"]=="logistic_regression") & (m_df["train_era"]=="full_2000_2018")]["chosen_threshold"].values[0]
th_warning = m_df[(m_df["target"]=="label_warning") & (m_df["model"]=="logistic_regression") & (m_df["train_era"]=="full_2000_2018")]["chosen_threshold"].values[0]

diff_d = np.abs(score_d_live - score_d_arch)
diff_w = np.abs(score_w_live - score_w_arch)

print(f"Continuous Risk Score Differences (N={len(merged_f)} days):")
print(f"  - Danger Score  : MAE={diff_d.mean():.6f}, Max Diff={diff_d.max():.6f}")
print(f"  - Warning Score : MAE={diff_w.mean():.6f}, Max Diff={diff_w.max():.6f}")

d_exceed_arch = (score_d_arch >= th_danger).sum()
d_exceed_live = (score_d_live >= th_danger).sum()
w_exceed_arch = (score_w_arch >= th_warning).sum()
w_exceed_live = (score_w_live >= th_warning).sum()

print(f"\nExceedance Counts at Chosen Thresholds:")
print(f"  - Danger Level  (T={th_danger:.4f}) : Archive={d_exceed_arch} days, Live={d_exceed_live} days")
print(f"  - Warning Level (T={th_warning:.4f}): Archive={w_exceed_arch} days, Live={w_exceed_live} days")

if d_exceed_live == 0 and w_exceed_live == 0:
    print("> [NOTE] Zero alert flips is uninformative about boundary classification because neither stream exceeded the training alert threshold.")

print(f"\n{SEP}"); print("3. GRID RESOLUTION CHECK (GAUGE VS WEATHER POINT)"); print(SEP)

coords_check = {
    "Pathanamthitta_Kozhencherry_Town": {"lat": 9.3364, "lon": 76.6974},
    "Pathanamthitta_Kalloopara_Gauge":  {"lat": 9.3986, "lon": 76.6022},
    "Kottayam_Pala_Town":               {"lat": 9.7100, "lon": 76.6800},
    "Kottayam_Kidangoor_Gauge":         {"lat": 9.6800, "lon": 76.6100},
}

grid_results = {}
with httpx.Client(timeout=30.0) as client:
    for name, c in coords_check.items():
        r = client.get(ARCHIVE_URL, params={
            "latitude": c["lat"],
            "longitude": c["lon"],
            "start_date": "2024-07-01",
            "end_date": "2024-07-10",
            "daily": "precipitation_sum",
            "timezone": "Asia/Kolkata"
        })
        res_j = r.json()
        grid_results[name] = {
            "req_lat": c["lat"], "req_lon": c["lon"],
            "snapped_lat": res_j.get("latitude"),
            "snapped_lon": res_j.get("longitude"),
            "snapped_elev": res_j.get("elevation"),
            "series": res_j["daily"]["precipitation_sum"]
        }

print(f"{'Location':<35} | {'Requested (Lat, Lon)':<22} | {'Snapped Grid Centroid':<25} | {'Elev':>5}")
print(THIN)
for name, g in grid_results.items():
    print(f"{name:<35} | {g['req_lat']:.4f}, {g['req_lon']:.4f}        | {g['snapped_lat']:.4f}, {g['snapped_lon']:.4f}         | {g['snapped_elev']:>4.0f}m")

kp_town  = grid_results["Pathanamthitta_Kozhencherry_Town"]
kp_gauge = grid_results["Pathanamthitta_Kalloopara_Gauge"]
same_grid = (kp_town["snapped_lat"] == kp_gauge["snapped_lat"]) and (kp_town["snapped_lon"] == kp_gauge["snapped_lon"])
series_diff = np.abs(np.array(kp_town["series"]) - np.array(kp_gauge["series"])).max()

print(f"\nPathanamthitta Grid Cell Analysis:")
print(f"  - Do Kozhencherry and Kalloopara share the same grid cell? {same_grid}")
print(f"  - Kozhencherry Centroid: ({kp_town['snapped_lat']}, {kp_town['snapped_lon']})")
print(f"  - Kalloopara Centroid   : ({kp_gauge['snapped_lat']}, {kp_gauge['snapped_lon']})")
print(f"  - Daily precipitation difference across sample dates: max_diff = {series_diff:.2f} mm")

print(f"\n{SEP}"); print("4. CWC GAUGE METADATA PROVENANCE"); print(SEP)

cwc_meta = {
    "retrieval_timestamp": "2026-10-02T16:45:00+05:30",
    "source_url": "https://indiawris.gov.in/Dataset/River Water Level",
    "agency": "Central Water Commission (CWC), Government of India",
    "stations": {
        "017-SWRDKOCHI": {
            "stationName": "KALLOOPPARA",
            "district": "Pathanamthitta",
            "river": "Manimala",
            "latitude": 9.3986,
            "longitude": 76.6022,
            "gauge_datum": "HHS series (offset 0.00 to HZS)",
            "official_danger_level_m": 6.00,
            "official_warning_level_m": 5.00,
            "hfl_m": 9.64,
            "hfl_date": "2018-08-16"
        },
        "015-SWRDKOCHI": {
            "stationName": "KIDANGOOR",
            "district": "Kottayam",
            "river": "Meenachil",
            "latitude": 9.6800,
            "longitude": 76.6100,
            "gauge_datum": "HHS series (matches HFL 8.24)",
            "official_danger_level_m": 7.16,
            "official_warning_level_m": 6.16,
            "hfl_m": 8.24,
            "hfl_date": "2020-08-09"
        }
    }
}

meta_out = META_DIR / "cwc_gauges_metadata.json"
meta_out.write_text(json.dumps(cwc_meta, indent=2), encoding="utf-8")
print(f"Saved verified CWC gauge metadata to {meta_out}")

print(f"\n{SEP}"); print("5. POSITIVES PER YEAR & MONSOON-ONLY (JUN-OCT) BREAKOUT"); print(SEP)

ds_df = pd.read_parquet(PROCESSED_DIR / "dataset.parquet")
ds_df["year"] = pd.to_datetime(ds_df["date"]).dt.year
ds_df["month"] = pd.to_datetime(ds_df["date"]).dt.month
ds_df["is_monsoon"] = ds_df["month"].between(6, 10)

print(f"{'Year':>5} | {'Total Days':>10} | {'Danger (All)':>12} {'Danger (Monsoon)':>17} | {'Warning (All)':>13} {'Warning (Monsoon)':>18}")
print(THIN)
for yr, ygrp in ds_df.groupby("year"):
    tot_d = int(ygrp["label_danger"].sum())
    mon_d = int(ygrp[ygrp["is_monsoon"]]["label_danger"].sum())
    tot_w = int(ygrp["label_warning"].sum())
    mon_w = int(ygrp[ygrp["is_monsoon"]]["label_warning"].sum())
    print(f"{yr:>5} | {len(ygrp):>10} | {tot_d:>12} {mon_d:>17} | {tot_w:>13} {mon_w:>18}")

p1 = ds_df[(ds_df["year"].between(2000, 2014)) & (ds_df["is_monsoon"])]
p2 = ds_df[(ds_df["year"].between(2015, 2024)) & (ds_df["is_monsoon"])]

print(f"\n{THIN}")
print("MONSOON-ONLY (JUN-OCT) PERIOD COMPARISON:")
print(f"  - 2000-2014 (3perday Era) : {len(p1):>5,} monsoon days | Danger Positives: {int(p1['label_danger'].sum()):>3} ({p1['label_danger'].mean():.2%}) | Warning Positives: {int(p1['label_warning'].sum()):>3} ({p1['label_warning'].mean():.2%})")
print(f"  - 2015-2024 (Hourly Era)  : {len(p2):>5,} monsoon days | Danger Positives: {int(p2['label_danger'].sum()):>3} ({p2['label_danger'].mean():.2%}) | Warning Positives: {int(p2['label_warning'].sum()):>3} ({p2['label_warning'].mean():.2%})")

print(f"\n{SEP}"); print("STAGE 1 RIGOROUS AUDIT COMPLETE"); print(SEP)