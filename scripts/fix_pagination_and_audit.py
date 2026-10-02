"""Script to:
1. Fix API pagination and re-download complete records for all 8 river stations.
2. Generate the COMPLETE year-by-year coverage table across all stations (2000-2024).
3. Extract and list all outliers (<= 0 and > 99.9th percentile) with full detail.
4. Document the time resolution and daily maximum computation logic.
"""

import glob
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx
import numpy as np
import pandas as pd

out_dir = Path("data/raw/labels/cwc")
out_dir.mkdir(parents=True, exist_ok=True)

TARGET_STATIONS = {
    "016-SWRDKOCHI": {"name": "VANDIPERIYAR", "district": "Idukki", "earliest_yr": 2000},
    "017-SWRDKOCHI": {"name": "KALLOOPPARA", "district": "Pathanamthitta", "earliest_yr": 2000},
    "013-SWRDKOCHI": {"name": "KALAMPUR", "district": "Ernakulam", "earliest_yr": 2015},
    "015-SWRDKOCHI": {"name": "KIDANGOOR", "district": "Kottayam", "earliest_yr": 2015},
    "011-SWRDKOCHI": {"name": "ARANGALI", "district": "Thrissur", "earliest_yr": 2015},
    "003-SWRDKOCHI": {"name": "MUTHANKERA", "district": "Wayanad", "earliest_yr": 2015},
    "008-SWRDKOCHI": {"name": "KUMBIDI", "district": "Palakkad", "earliest_yr": 2015},
    "006-SWRDKOCHI": {"name": "KARATHODU", "district": "Malappuram", "earliest_yr": 2015},
}

API_URL = "https://indiawris.gov.in/Dataset/River Water Level"
HEADERS = {"accept": "application/json", "User-Agent": "Mozilla/5.0"}

# Record previous counts
prev_counts = {}
for code, info in TARGET_STATIONS.items():
    fpath = out_dir / f"station_{code}_{info['name'].lower()}.csv"
    if fpath.exists():
        prev_counts[code] = len(pd.read_csv(fpath))
    else:
        prev_counts[code] = 0

print("==========================================================================================")
print("1. TRUNCATION & MULTI-PAGE PAGINATION CHECK")
print("==========================================================================================")

all_station_dfs = {}
new_counts = {}

with httpx.Client(timeout=30.0, verify=True) as client:
    for code, info in TARGET_STATIONS.items():
        st_name = info["name"]
        dist = info["district"]
        start_yr = info["earliest_yr"]
        print(f"\nRe-downloading {st_name} ({code}) with full pagination across {start_yr}–2024...")
        
        all_records = []
        
        for yr in range(start_yr, 2025):
            page = 0
            while True:
                params = {
                    "stateName": "Kerala",
                    "districtName": dist.capitalize(),
                    "agencyName": "CWC",
                    "startdate": f"{yr}-01-01",
                    "enddate": f"{yr}-12-31",
                    "download": "false",
                    "page": page,
                    "size": 1000
                }
                try:
                    r = client.post(API_URL, params=params, headers=HEADERS)
                    if r.status_code == 200:
                        data = r.json().get("data", [])
                        matched = [d for d in data if str(d.get("stationCode")).strip() == code and d.get("dataValue") is not None]
                        all_records.extend(matched)
                        
                        # If page returned less than 1000 total items, no more pages exist for this year
                        if len(data) < 1000:
                            break
                        page += 1
                        time.sleep(0.15)
                    else:
                        break
                except Exception as e:
                    print(f"  Error on {yr} page {page}: {e}")
                    break
                    
        if all_records:
            df = pd.DataFrame(all_records)
            df['dataTime'] = pd.to_datetime(df['dataTime'])
            df = df.sort_values('dataTime').drop_duplicates(subset=['dataTime']).reset_index(drop=True)
            st_csv_path = out_dir / f"station_{code}_{st_name.lower()}.csv"
            df.to_csv(st_csv_path, index=False)
            all_station_dfs[code] = df
            new_counts[code] = len(df)
            print(f"  ==> Previous: {prev_counts[code]:,} | New Total: {len(df):,} readings (Delta: +{len(df) - prev_counts[code]:,})")
        else:
            new_counts[code] = 0

print("\n--- TRUNCATION CHECK SUMMARY ---")
trunc_summary = []
for code, info in TARGET_STATIONS.items():
    p_c = prev_counts.get(code, 0)
    n_c = new_counts.get(code, 0)
    trunc_summary.append({
        "Station Code": code,
        "Station Name": info["name"],
        "District": info["district"],
        "Previous Count": f"{p_c:,}",
        "Paginated Total Count": f"{n_c:,}",
        "Count Changed?": "YES (Pagination Recovered Data)" if n_c != p_c else "NO (API naturally had exact count)"
    })
print(pd.DataFrame(trunc_summary).to_string(index=False))

print("\n==========================================================================================")
print("2. FULL YEAR-BY-YEAR COVERAGE TABLE (ALL STATIONS & ALL YEARS)")
print("==========================================================================================")

coverage_records = []

for code, info in TARGET_STATIONS.items():
    st_name = info["name"]
    dist = info["district"]
    df = all_station_dfs.get(code)
    
    if df is None or df.empty:
        continue
        
    df['year'] = df['dataTime'].dt.year
    df['month'] = df['dataTime'].dt.month
    df['date_only'] = df['dataTime'].dt.date
    
    for yr in sorted(df['year'].unique()):
        df_yr = df[df['year'] == yr]
        total_days_in_yr = 366 if (yr % 4 == 0 and (yr % 100 != 0 or yr % 400 == 0)) else 365
        days_with_data_yr = df_yr['date_only'].nunique()
        total_readings_yr = len(df_yr)
        
        # Readings per active day
        rpd_typical = round(total_readings_yr / days_with_data_yr, 1) if days_with_data_yr > 0 else 0.0
        
        # Monsoon window (Jun 1 - Oct 31, 153 days)
        df_monsoon = df_yr[df_yr['month'].isin([6, 7, 8, 9, 10])]
        monsoon_days_with_data = df_monsoon['date_only'].nunique()
        monsoon_missing_days = 153 - monsoon_days_with_data
        full_yr_missing_days = total_days_in_yr - days_with_data_yr
        
        coverage_records.append({
            "Station Code": code,
            "Station Name": st_name,
            "District": dist,
            "Year": yr,
            "Total Readings": total_readings_yr,
            "Readings/Day (Active Days)": rpd_typical,
            "Monsoon Days (Jun-Oct)": f"{monsoon_days_with_data} / 153",
            "Monsoon Missing": monsoon_missing_days,
            "Full Year Days": f"{days_with_data_yr} / {total_days_in_yr}",
            "Full Year Missing": full_yr_missing_days
        })

df_full_cov = pd.DataFrame(coverage_records)
print(df_full_cov.to_string(index=False))

print("\n==========================================================================================")
print("3. OUTLIER AUDIT: READINGS <= 0 OR > 99.9th PERCENTILE")
print("==========================================================================================")

outlier_list = []
outlier_counts_per_station = []

for code, info in TARGET_STATIONS.items():
    st_name = info["name"]
    df = all_station_dfs.get(code)
    if df is None or df.empty:
        continue
        
    vals = pd.to_numeric(df['dataValue'], errors='coerce').dropna()
    p999 = vals.quantile(0.999)
    
    # Condition: <= 0 OR > 99.9th percentile
    neg_zero = df[df['dataValue'] <= 0.0]
    extreme_high = df[df['dataValue'] > p999]
    
    total_outliers = len(neg_zero) + len(extreme_high)
    outlier_counts_per_station.append({
        "Station Code": code,
        "Station Name": st_name,
        "Total Readings": len(df),
        "99.9th Percentile (m)": f"{p999:.2f}",
        "Readings <= 0": len(neg_zero),
        "Readings > 99.9th %ile": len(extreme_high),
        "Total Flagged Outliers": total_outliers
    })
    
    for _, row in neg_zero.iterrows():
        outlier_list.append({
            "Station Code": code,
            "Station Name": st_name,
            "Timestamp": str(row['dataTime']),
            "Value (m)": row['dataValue'],
            "Flag Type": "Negative or Zero (<= 0)"
        })
        
    for _, row in extreme_high.iterrows():
        outlier_list.append({
            "Station Code": code,
            "Station Name": st_name,
            "Timestamp": str(row['dataTime']),
            "Value (m)": row['dataValue'],
            "Flag Type": f"Extreme High (> 99.9th %ile of {p999:.2f}m)"
        })

df_outlier_counts = pd.DataFrame(outlier_counts_per_station)
df_all_outliers = pd.DataFrame(outlier_list)

print("--- OUTLIER SUMMARY COUNTS PER STATION ---")
print(df_outlier_counts.to_string(index=False))

print(f"\n--- FULL LIST OF FLAGGED OUTLIER READINGS ({len(df_all_outliers)} records) ---")
if not df_all_outliers.empty:
    print(df_all_outliers.to_string(index=False))
else:
    print("No outliers found.")

print("\n==========================================================================================")
print("4. TIME RESOLUTION & DAILY MAXIMUM COMPUTATION METHODOLOGY")
print("==========================================================================================")

resolution_analysis = []
for code, info in TARGET_STATIONS.items():
    df = all_station_dfs.get(code)
    if df is None or df.empty:
        continue
    # Compute time differences between consecutive readings
    diffs = df['dataTime'].diff().dt.total_seconds() / 3600.0
    median_diff = diffs.median()
    min_diff = diffs.min()
    
    res_str = ""
    if median_diff == 1.0:
        res_str = "Hourly Telemetry (1-hour step)"
    elif median_diff == 24.0 or median_diff >= 12.0:
        res_str = f"Daily Manual / Multi-hour (~{median_diff:.0f}-hour interval)"
    else:
        res_str = f"Sub-daily Telemetry (~{median_diff:.1f} hours)"
        
    resolution_analysis.append({
        "Station Code": code,
        "Station Name": info["name"],
        "Median Interval": f"{median_diff:.1f} hrs",
        "Primary Time Resolution": res_str,
        "Total Readings": f"{len(df):,}"
    })

print(pd.DataFrame(resolution_analysis).to_string(index=False))

# Save summary tables to disk
df_full_cov.to_csv(out_dir / "full_coverage_table_all_stations_2000_2024.csv", index=False)
df_all_outliers.to_csv(out_dir / "outliers_raw_audit.csv", index=False)
