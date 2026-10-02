import json, math, os, pathlib, sys, time
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
PARITY_DIR    = RAW_DIR / "parity"
PARITY_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# 1. CWC API REQUEST DEBUGGING & DATE PROBE
# ------------------------------------------------------------
print(SEP); print("1. CWC API REQUEST DEBUGGING & DATE PROBE"); print(SEP)

CWC_URL = "https://indiawris.gov.in/Dataset/River Water Level"

probe_periods = [
    ("2024 Monsoon", "2024-06-01", "2024-10-02"),
    ("2025 Full",    "2025-01-01", "2025-12-31"),
    ("2026 Q1",      "2026-01-01", "2026-03-31"),
    ("2026 Monsoon", "2026-06-01", "2026-10-02"),
]

with httpx.Client(timeout=30.0, verify=False) as client:
    for pname, s_dt, e_dt in probe_periods:
        params = {
            "stateName": "Kerala",
            "districtName": "Pathanamthitta",
            "agencyName": "CWC",
            "stationCode": "017-SWRDKOCHI",
            "startdate": f"{s_dt}T00:00:00",
            "enddate": f"{e_dt}T23:59:59",
            "page": 0,
            "size": 1000
        }
        
        r = client.post(CWC_URL, params=params)
        print(f"Probe: {pname} ({s_dt} to {e_dt})")
        print(f"  Request URL: {r.url}")
        print(f"  HTTP Status: {r.status_code}")
        
        if r.status_code == 200:
            res_j = r.json()
            body = res_j if isinstance(res_j, list) else res_j.get("data", res_j.get("result", []))
            print(f"  Records returned: {len(body)}")
            if len(body) > 0:
                first_ts = body[0].get("dataTime", body[0].get("data_time"))
                last_ts  = body[-1].get("dataTime", body[-1].get("data_time"))
                print(f"  First TS: {first_ts}, Last TS: {last_ts}")
        else:
            print(f"  Response Body: {r.text[:200]}")
        print()

# ------------------------------------------------------------
# 2. FEATURE DECOMPOSITION SUMMARY
# ------------------------------------------------------------
print(SEP); print("2. FEATURE CONTRIBUTIONS & DECOMPOSITION SUMMARY"); print(SEP)

feat_cols = ["rain_1d", "rain_3d", "rain_7d", "rain_14d", "rain_30d", "soil_0_7_t1", "soil_7_28_t1", "sin_doy", "cos_doy"]
m_pipe = joblib.load(MODELS_DIR / "logistic_regression_label_danger_full_2000_2018.joblib")
scaler = m_pipe.named_steps["scaler"]
clf    = m_pipe.named_steps["clf"]
coefs  = clf.coef_[0]

print("Model Feature Coefficients (Beta):")
for f_name, c in zip(feat_cols, coefs):
    print(f"  {f_name:<16}: {c:>9.4f}")

print("""
Key Observation on 2026-09-09..20 Alerts:
- On 2026-09-16 (daily rain = 0.40 mm), the Danger Risk Score reached 0.9999.
- ROOT DRIVER:
  1. soil_0_7_t1 Beta = -3.1677. In September, dry topsoil (raw = 0.1130) produced a large negative z-score (Z = -4.3980).
     Multiplying two negative numbers produced a massive POSITIVE logit push: Beta * Z = +13.9316!
  2. sin_doy Beta = -3.2512. Day 260 produced a negative sine (Z = -1.3524), contributing another Beta * Z = +4.3971.
  3. Result: Pathological linear extrapolation where dry topsoil coupled with late-monsoon seasonality
     forced the unconstrained linear logit to +9.75, generating false danger alerts during a dry spell.
""")

# ------------------------------------------------------------
# 3. ALERT LOAD BY MONTH & PERIOD
# ------------------------------------------------------------
print(SEP); print("3. ALERT LOAD BY MONTH & PERIOD"); print(SEP)

hist_weather = []
for zslug, zname in [("pathanamthitta_kozhencherry", "Pathanamthitta"), ("kottayam_pala", "Kottayam")]:
    wfp = RAW_DIR / "historical" / f"{zslug}.csv"
    wdf = pd.read_csv(wfp, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    p_shift = wdf["precipitation_sum"].shift(1)
    wdf["rain_1d"]  = p_shift
    wdf["rain_3d"]  = p_shift.rolling(3, min_periods=3).sum()
    wdf["rain_7d"]  = p_shift.rolling(7, min_periods=7).sum()
    wdf["rain_14d"] = p_shift.rolling(14, min_periods=14).sum()
    wdf["rain_30d"] = p_shift.rolling(30, min_periods=30).sum()
    
    col_map = {c.lower(): c for c in wdf.columns}
    s1_key = col_map.get("soil_moisture_0_7cm", col_map.get("soil_moisture_0_to_7cm_mean"))
    s2_key = col_map.get("soil_moisture_7_28cm", col_map.get("soil_moisture_7_to_28cm_mean"))
    
    wdf["soil_0_7_t1"]  = wdf[s1_key].shift(1)
    wdf["soil_7_28_t1"] = wdf[s2_key].shift(1)
    doy = wdf["date"].dt.dayofyear
    wdf["sin_doy"] = np.sin(2 * np.pi * doy / 365.25)
    wdf["cos_doy"] = np.cos(2 * np.pi * doy / 365.25)
    wdf["zone"] = zname
    hist_weather.append(wdf[["date", "zone"] + feat_cols])

full_hist = pd.concat(hist_weather, ignore_index=True).dropna().reset_index(drop=True)
full_hist["danger_score"] = m_pipe.predict_proba(full_hist[feat_cols])[:, 1]
full_hist["is_alert"] = full_hist["danger_score"] >= 0.9965
full_hist["year"]  = full_hist["date"].dt.year
full_hist["month"] = full_hist["date"].dt.month

full_hist["era"] = np.where(full_hist["year"] <= 2018, "Train (2000-2018)", "Test (2019-2024)")

print("Danger Alert Rate (% of days with Danger Alert >= 0.9965) by Month:")
print(f"{'Month':>6} | {'Pathanamthitta (2000-18)':>24} {'(2019-24)':>10} | {'Kottayam (2000-18)':>20} {'(2019-24)':>10}")
print(THIN)
for m in range(1, 13):
    m_name = date(2000, m, 1).strftime("%b")
    rates = {}
    for z in ["Pathanamthitta", "Kottayam"]:
        for era in ["Train (2000-2018)", "Test (2019-2024)"]:
            sub = full_hist[(full_hist["zone"] == z) & (full_hist["era"] == era) & (full_hist["month"] == m)]
            rates[f"{z}_{era}"] = sub["is_alert"].mean() if len(sub) > 0 else 0.0
            
    print(f"{m_name:>6} | {rates['Pathanamthitta_Train (2000-2018)']:>23.2%} {rates['Pathanamthitta_Test (2019-2024)']:>10.2%} | {rates['Kottayam_Train (2000-2018)']:>19.2%} {rates['Kottayam_Test (2019-2024)']:>10.2%}")

# ------------------------------------------------------------
# 4. PER-ZONE TABLE WITH MISSING DAYS & POSITIVES
# ------------------------------------------------------------
print(f"\n{SEP}"); print("4. PER-ZONE ANNUAL TABLE WITH MISSING DAYS & JUN-OCT COVERAGE"); print(SEP)

ds_df = pd.read_parquet(PROCESSED_DIR / "dataset.parquet")
ds_df["year"] = pd.to_datetime(ds_df["date"]).dt.year
ds_df["month"] = pd.to_datetime(ds_df["date"]).dt.month

for stn, zname in [("KALLOOPPARA", "Pathanamthitta"), ("KIDANGOOR", "Kottayam")]:
    print(f"\nStation: {stn} ({zname})")
    print(f"{'Year':>5} | {'Total Days':>10} | {'Danger Pos':>10} {'Warning Pos':>11} {'Missing/NaN':>12} | {'Jun-Oct Days':>12} {'Jun-Oct Pos(D)':>15} {'Jun-Oct Pos(W)':>15}")
    print(THIN)
    sub = ds_df[ds_df["station"] == stn]
    for yr, ygrp in sub.groupby("year"):
        tot_d = int(ygrp["label_danger"].sum())
        tot_w = int(ygrp["label_warning"].sum())
        
        is_leap = (yr % 4 == 0 and yr % 100 != 0) or (yr % 400 == 0)
        exp_days = 366 if is_leap else 365
        miss_days = exp_days - len(ygrp)
        
        mon_grp = ygrp[ygrp["month"].between(6, 10)]
        mon_d = int(mon_grp["label_danger"].sum())
        mon_w = int(mon_grp["label_warning"].sum())
        
        print(f"{yr:>5} | {len(ygrp):>10} | {tot_d:>10} {tot_w:>11} {miss_days:>12} | {len(mon_grp):>12} {mon_d:>15} {mon_w:>15}")

# ------------------------------------------------------------
# 5. LABEL BIAS CHECK (HOURLY VS 3-OBS THINNING FOR KALLOOPPARA)
# ------------------------------------------------------------
print(f"\n{SEP}"); print("5. LABEL BIAS CHECK: HOURLY VS 3-OBS THINNING (2015-2024)"); print(SEP)

raw_kp_path = RAW_DIR / "labels/cwc/v3/station_017-SWRDKOCHI_kallooppara.csv"
raw_kp = pd.read_csv(raw_kp_path, low_memory=False)

col = {c.lower(): c for c in raw_kp.columns}
dt_c  = col.get("datatime", list(col.values())[0])
dty_c = col.get("datatypecode", "datatypeCode")
val_c = col.get("datavalue", "dataValue")

raw_kp = raw_kp.rename(columns={dt_c:"dataTime", dty_c:"datatypeCode", val_c:"dataValue"})
raw_kp["dataTime"]  = pd.to_datetime(raw_kp["dataTime"], errors="coerce")
raw_kp["dataValue"] = pd.to_numeric(raw_kp["dataValue"], errors="coerce")
raw_kp["_date"]     = raw_kp["dataTime"].dt.date
raw_kp["_hour"]     = raw_kp["dataTime"].dt.hour
raw_kp["_year"]     = raw_kp["dataTime"].dt.year

hhs_post14 = raw_kp[(raw_kp["datatypeCode"] == "HHS") & (raw_kp["_year"] >= 2015)].dropna(subset=["dataValue"]).copy()
daily_full = hhs_post14.groupby("_date")["dataValue"].agg(max_full="max", count_full="count").reset_index()

thinned = hhs_post14[hhs_post14["_hour"].isin([8, 13, 18])]
daily_thinned = thinned.groupby("_date")["dataValue"].agg(max_thinned="max", count_thinned="count").reset_index()

cmp_thin = daily_full.merge(daily_thinned, on="_date", how="left")

DANGER_TH  = 6.00
WARNING_TH = 5.00

cmp_thin["danger_full"]    = (cmp_thin["max_full"] >= DANGER_TH).astype(int)
cmp_thin["danger_thinned"] = (cmp_thin["max_thinned"] >= DANGER_TH).astype(int)

cmp_thin["warning_full"]    = (cmp_thin["max_full"] >= WARNING_TH).astype(int)
cmp_thin["warning_thinned"] = (cmp_thin["max_thinned"] >= WARNING_TH).astype(int)

d_full_cnt = int(cmp_thin["danger_full"].sum())
d_thin_cnt = int(cmp_thin["danger_thinned"].sum())
d_missed   = int(((cmp_thin["danger_full"] == 1) & (cmp_thin["danger_thinned"] == 0)).sum())

w_full_cnt = int(cmp_thin["warning_full"].sum())
w_thin_cnt = int(cmp_thin["warning_thinned"].sum())
w_missed   = int(((cmp_thin["warning_full"] == 1) & (cmp_thin["warning_thinned"] == 0)).sum())

print(f"Kallooppara 2015-2024 Schedule Thinning Comparison (N={len(cmp_thin):,} days):")
print(f"  - Danger Level Exceedance Days (>= {DANGER_TH} m):")
print(f"    * Full Hourly Telemetry  : {d_full_cnt} days")
print(f"    * Thinned 3-Obs Schedule : {d_thin_cnt} days")
print(f"    * Missed Danger Days     : {d_missed} days ({d_missed/max(d_full_cnt,1):.2%} missed)")
print(f"\n  - Warning Level Exceedance Days (>= {WARNING_TH} m):")
print(f"    * Full Hourly Telemetry  : {w_full_cnt} days")
print(f"    * Thinned 3-Obs Schedule : {w_thin_cnt} days")
print(f"    * Missed Warning Days    : {w_missed} days ({w_missed/max(w_full_cnt,1):.2%} missed)")

missed_df = cmp_thin[(cmp_thin["danger_full"] == 1) & (cmp_thin["danger_thinned"] == 0)]
if not missed_df.empty:
    print(f"\nDetails of Missed Danger Exceedances (Peak caught by hourly, missed by 3-obs):")
    for _, r in missed_df.iterrows():
        print(f"  Date: {r['_date']} | Hourly Peak: {r['max_full']:.2f} m | 3-Obs Peak: {r['max_thinned']} m")

print(f"\n{SEP}\nSTAGE 1 COMPREHENSIVE DIAGNOSTICS COMPLETE\n{SEP}")