import json, math, pathlib, sys, time
from datetime import date, datetime, timedelta
import httpx
import numpy as np
import pandas as pd
import joblib

SEP  = "=" * 78
THIN = "-" * 78

RAW_DIR       = pathlib.Path("data/raw")
PROCESSED_DIR = pathlib.Path("data/processed")
MODELS_DIR    = pathlib.Path("models")

# ------------------------------------------------------------
# 1. LIVE FORECAST API KEY INSPECTION
# ------------------------------------------------------------
print(SEP); print("1. LIVE FORECAST API DAILY KEYS INSPECTION"); print(SEP)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
params_probe = {
    "latitude": 9.3364,
    "longitude": 76.6974,
    "daily": [
        "precipitation_sum",
        "rain_sum",
        "temperature_2m_max",
        "temperature_2m_min",
        "soil_moisture_0_to_7cm_mean",
        "soil_moisture_7_to_28cm_mean",
    ],
    "timezone": "Asia/Kolkata",
    "forecast_days": 1,
}

print(f"Querying probe request to: {FORECAST_URL}")
with httpx.Client(timeout=30.0) as client:
    r = client.get(FORECAST_URL, params=params_probe)
    print(f"HTTP Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        daily_keys = list(data.get("daily", {}).keys())
        print(f"\nReturned 'daily' keys verbatim:\n{json.dumps(daily_keys, indent=2)}")
        
        has_sm0_7 = "soil_moisture_0_to_7cm_mean" in daily_keys
        has_sm7_28 = "soil_moisture_7_to_28cm_mean" in daily_keys
        print(f"\nKey Verification:")
        print(f"  - soil_moisture_0_to_7cm_mean  exists: {has_sm0_7}")
        print(f"  - soil_moisture_7_to_28cm_mean exists: {has_sm7_28}")
    else:
        print(f"ERROR: {r.text}")

# ------------------------------------------------------------
# 2. LIVE VS ARCHIVE PARITY MEASUREMENT (MAX past_days)
# ------------------------------------------------------------
print(f"\n{SEP}"); print("2. LIVE VS ARCHIVE PARITY MEASUREMENT (Maximum allowed past_days)"); print(SEP)

# Test maximum past_days allowed by Open-Meteo Forecast API
# Open-Meteo standard allows up to past_days=92
max_past = 92
print(f"Querying Live Forecast API with past_days={max_past} ...")

test_zone = "pathanamthitta_kozhencherry"
zone_lat, zone_lon = 9.3364, 76.6974

with httpx.Client(timeout=30.0) as client:
    # 1. Live Forecast endpoint with past_days
    r_live = client.get(FORECAST_URL, params={
        "latitude": zone_lat,
        "longitude": zone_lon,
        "daily": [
            "precipitation_sum",
            "soil_moisture_0_to_7cm_mean",
            "soil_moisture_7_to_28cm_mean",
        ],
        "timezone": "Asia/Kolkata",
        "past_days": max_past,
        "forecast_days": 1,
    })
    
    # 2. Archive endpoint for the same date window
    live_json = r_live.json()["daily"]
    start_date = live_json["time"][0]
    end_date   = live_json["time"][-2]  # up to t-1
    
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
    r_arch = client.get(ARCHIVE_URL, params={
        "latitude": zone_lat,
        "longitude": zone_lon,
        "daily": [
            "precipitation_sum",
            "soil_moisture_0_to_7cm_mean",
            "soil_moisture_7_to_28cm_mean",
        ],
        "timezone": "Asia/Kolkata",
        "start_date": start_date,
        "end_date": end_date,
    })
    arch_json = r_arch.json()["daily"]

df_live = pd.DataFrame(live_json).rename(columns={"time": "date"})
df_arch = pd.DataFrame(arch_json).rename(columns={"time": "date"})

df_live["date"] = pd.to_datetime(df_live["date"])
df_arch["date"] = pd.to_datetime(df_arch["date"])

# Merge on common dates
cmp_df = df_arch.merge(df_live, on="date", suffixes=("_archive", "_live")).sort_values("date").reset_index(drop=True)
print(f"Compared common overlapping dates: {len(cmp_df)} days ({cmp_df['date'].min().date()} to {cmp_df['date'].max().date()})")

# Construct t-1 rolling features on both streams
def build_features_from_stream(df, p_col, s1_col, s2_col):
    res = pd.DataFrame({"date": df["date"]})
    p_shift = df[p_col].shift(1)
    res["rain_1d"]  = p_shift
    res["rain_3d"]  = p_shift.rolling(3, min_periods=3).sum()
    res["rain_7d"]  = p_shift.rolling(7, min_periods=7).sum()
    res["rain_14d"] = p_shift.rolling(14, min_periods=14).sum()
    res["rain_30d"] = p_shift.rolling(30, min_periods=30).sum()
    res["soil_0_7_t1"]  = df[s1_col].shift(1)
    res["soil_7_28_t1"] = df[s2_col].shift(1)
    doy = df["date"].dt.dayofyear
    res["sin_doy"] = np.sin(2 * np.pi * doy / 365.25)
    res["cos_doy"] = np.cos(2 * np.pi * doy / 365.25)
    return res

feat_arch = build_features_from_stream(cmp_df, "precipitation_sum_archive", "soil_moisture_0_to_7cm_mean_archive", "soil_moisture_7_to_28cm_mean_archive")
feat_live = build_features_from_stream(cmp_df, "precipitation_sum_live", "soil_moisture_0_to_7cm_mean_live", "soil_moisture_7_to_28cm_mean_live")

comp_feats = feat_arch.merge(feat_live, on="date", suffixes=("_arch", "_live")).dropna().reset_index(drop=True)

# Heavy rain split (top 10% precipitation)
p90 = comp_feats["rain_1d_arch"].quantile(0.90)
comp_feats["is_heavy_rain"] = comp_feats["rain_1d_arch"] >= p90

feat_names = ["rain_1d", "rain_3d", "rain_7d", "rain_14d", "rain_30d", "soil_0_7_t1", "soil_7_28_t1", "sin_doy", "cos_doy"]

print(f"\n{THIN}")
print(f"Per-Feature Parity Statistics (Live - Archive) across {len(comp_feats)} days:")
print(f"Heavy rain threshold (P90 of rain_1d): {p90:.2f} mm (N_heavy={comp_feats['is_heavy_rain'].sum()}, N_other={(~comp_feats['is_heavy_rain']).sum()})")
print(f"\n{'Feature':<16} | {'Overall MAE':>11} {'Bias':>11} | {'Heavy MAE':>10} {'Heavy Bias':>10} | {'Other MAE':>10} {'Other Bias':>10}")
print(THIN)

for f in feat_names:
    diff_all   = comp_feats[f"{f}_live"] - comp_feats[f"{f}_arch"]
    diff_heavy = comp_feats.loc[comp_feats["is_heavy_rain"], f"{f}_live"] - comp_feats.loc[comp_feats["is_heavy_rain"], f"{f}_arch"]
    diff_other = comp_feats.loc[~comp_feats["is_heavy_rain"], f"{f}_live"] - comp_feats.loc[~comp_feats["is_heavy_rain"], f"{f}_arch"]
    
    mae_all, bias_all = np.abs(diff_all).mean(), diff_all.mean()
    mae_h, bias_h     = np.abs(diff_heavy).mean(), diff_heavy.mean()
    mae_o, bias_o     = np.abs(diff_other).mean(), diff_other.mean()
    
    print(f"{f:<16} | {mae_all:>11.4f} {bias_all:>11.4f} | {mae_h:>10.4f} {bias_h:>10.4f} | {mae_o:>10.4f} {bias_o:>10.4f}")

# Model Alert State Flips
model_path = MODELS_DIR / "logistic_regression_label_danger_full_2000_2018.joblib"
if model_path.exists():
    model = joblib.load(model_path)
    X_arch = comp_feats[[f"{f}_arch" for f in feat_names]].rename(columns=lambda c: c.replace("_arch", ""))
    X_live = comp_feats[[f"{f}_live" for f in feat_names]].rename(columns=lambda c: c.replace("_live", ""))
    
    prob_arch = model.predict_proba(X_arch)[:, 1]
    prob_live = model.predict_proba(X_live)[:, 1]
    
    # Load chosen threshold from metrics.csv
    m_df = pd.read_csv(PROCESSED_DIR / "metrics.csv")
    th_danger = m_df[(m_df["target"]=="label_danger") & (m_df["model"]=="logistic_regression") & (m_df["train_era"]=="full_2000_2018")]["chosen_threshold"].values[0]
    
    alert_arch = (prob_arch >= th_danger).astype(int)
    alert_live = (prob_live >= th_danger).astype(int)
    
    flips = (alert_arch != alert_live)
    flips_heavy = flips[comp_feats["is_heavy_rain"]]
    flips_other = flips[~comp_feats["is_heavy_rain"]]
    
    print(f"\nAlert State Differences (Threshold = {th_danger:.4f}):")
    print(f"  - Overall Flips   : {flips.sum()} / {len(flips)} ({flips.mean():.2%})")
    print(f"  - Heavy Rain Flips: {flips_heavy.sum()} / {len(flips_heavy)} ({flips_heavy.mean():.2%})")
    print(f"  - Other Days Flips: {flips_other.sum()} / {len(flips_other)} ({flips_other.mean():.2%})")

# ------------------------------------------------------------
# 3. GAUGE VS WEATHER COORDINATES & DISTANCE
# ------------------------------------------------------------
print(f"\n{SEP}"); print("3. GAUGE VS WEATHER POINT COORDINATES & DISTANCE"); print(SEP)

# Haversine distance function (km)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# Exact CWC Station Metadata from metadata files / India-WRIS
gauge_coords = {
    "KALLOOPPARA": {"code": "017-SWRDKOCHI", "district": "Pathanamthitta", "river": "Manimala", "lat": 9.3986, "lon": 76.6022},
    "KIDANGOOR":   {"code": "015-SWRDKOCHI", "district": "Kottayam",       "river": "Meenachil", "lat": 9.6800, "lon": 76.6100},
}

weather_coords = {
    "KALLOOPPARA": {"slug": "pathanamthitta_kozhencherry", "town": "Kozhencherry", "lat": 9.3364, "lon": 76.6974},
    "KIDANGOOR":   {"slug": "kottayam_pala",               "town": "Pala",         "lat": 9.7100, "lon": 76.6800},
}

print(f"{'Station':<14} | {'Gauge Coords (CWC)':<22} | {'Weather Point (Town)':<25} | {'Distance':<10}")
print(THIN)
for st in ["KALLOOPPARA", "KIDANGOOR"]:
    g = gauge_coords[st]
    w = weather_coords[st]
    dist_km = haversine(g["lat"], g["lon"], w["lat"], w["lon"])
    print(f"{st:<14} | {g['lat']:.4f} N, {g['lon']:.4f} E     | {w['town']} ({w['lat']:.4f} N, {w['lon']:.4f} E) | {dist_km:6.2f} km")

print("""
Catchment Limitation Note:
- KALLOOPPARA gauge (Manimala basin) is 12.5 km west of the Kozhencherry weather grid point (Pamba basin).
- KIDANGOOR gauge (Meenachil basin) is 8.4 km west of the Pala weather grid point (Meenachil basin).
- The weather point captures regional district precipitation but does not represent spatially aggregated,
  elevation-weighted rainfall across the entire upstream Western Ghats catchment.
""")

# ------------------------------------------------------------
# 4. POSITIVES PER YEAR AND PER SAMPLING REGIME
# ------------------------------------------------------------
print(SEP); print("4. POSITIVES PER YEAR AND PER SAMPLING REGIME"); print(SEP)

df_dataset = pd.read_parquet(PROCESSED_DIR / "dataset.parquet")
df_dataset["year"] = pd.to_datetime(df_dataset["date"]).dt.year

for label_name in ["label_danger", "label_warning"]:
    print(f"\n--- Breakout for {label_name.upper()} ---")
    print(f"{'Year':>5} | {'Total Days':>10} | {'3perday (Days / Pos)':>22} | {'Hourly (Days / Pos)':>22} | {'Total Positives':>15}")
    print(THIN)
    for yr, ygrp in df_dataset.groupby("year"):
        tot_days = len(ygrp)
        grp_3p = ygrp[ygrp["regime"] == "3perday"]
        grp_hr = ygrp[ygrp["regime"] == "hourly"]
        
        pos_3p = int(grp_3p[label_name].sum())
        pos_hr = int(grp_hr[label_name].sum())
        tot_pos = int(ygrp[label_name].sum())
        
        str_3p = f"{len(grp_3p)} / {pos_3p}"
        str_hr = f"{len(grp_hr)} / {pos_hr}"
        print(f"{yr:>5} | {tot_days:>10} | {str_3p:>22} | {str_hr:>22} | {tot_pos:>15}")
    
    # Overall summary by regime
    print(THIN)
    tot_3p_days = len(df_dataset[df_dataset["regime"] == "3perday"])
    tot_3p_pos  = int(df_dataset[df_dataset["regime"] == "3perday"][label_name].sum())
    tot_hr_days = len(df_dataset[df_dataset["regime"] == "hourly"])
    tot_hr_pos  = int(df_dataset[df_dataset["regime"] == "hourly"][label_name].sum())
    
    print(f"REGIME TOTALS for {label_name}:")
    print(f"  - 3perday Regime (mostly pre-2015 + off-season): {tot_3p_days:,} days | {tot_3p_pos} positives ({tot_3p_pos/tot_3p_days:.2%})")
    print(f"  - Hourly Regime  (monsoon seasons 2015-2024)   : {tot_hr_days:,} days | {tot_hr_pos} positives ({tot_hr_pos/tot_hr_days:.2%})")

print(f"\n{SEP}\nSTAGE 1 COMPLETE -- Output presented, stopped for review.\n{SEP}")

