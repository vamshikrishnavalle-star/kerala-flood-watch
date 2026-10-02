"""Script to precisely compute and format all 4 audit checks for direct chat output:
1. Truncation proof & year-by-year row counts for Kalampur, Kidangoor, Karathodu.
2. Full year-by-year coverage table across all 8 stations.
3. Outlier counts & 10 most extreme values with neighbouring readings for Muthankera, Vandiperiyar, Kallooppara.
4. Time resolution & daily-max computation rule.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

out_dir = Path("data/raw/labels/cwc")

TARGET_STATIONS = {
    "016-SWRDKOCHI": {"name": "VANDIPERIYAR", "district": "Idukki"},
    "017-SWRDKOCHI": {"name": "KALLOOPPARA", "district": "Pathanamthitta"},
    "013-SWRDKOCHI": {"name": "KALAMPUR", "district": "Ernakulam"},
    "015-SWRDKOCHI": {"name": "KIDANGOOR", "district": "Kottayam"},
    "011-SWRDKOCHI": {"name": "ARANGALI", "district": "Thrissur"},
    "003-SWRDKOCHI": {"name": "MUTHANKERA", "district": "Wayanad"},
    "008-SWRDKOCHI": {"name": "KUMBIDI", "district": "Palakkad"},
    "006-SWRDKOCHI": {"name": "KARATHODU", "district": "Malappuram"},
}

all_dfs = {}
for code, info in TARGET_STATIONS.items():
    csv_file = out_dir / f"station_{code}_{info['name'].lower()}.csv"
    if csv_file.exists():
        df = pd.read_csv(csv_file)
        df['dataTime'] = pd.to_datetime(df['dataTime'])
        df['dataValue'] = pd.to_numeric(df['dataValue'], errors='coerce')
        df = df.sort_values('dataTime').reset_index(drop=True)
        all_dfs[code] = df

# 1. TRUNCATION BREAKDOWN
print("### 1. TRUNCATION & API CAP INVESTIGATION\n")
for code in ["013-SWRDKOCHI", "015-SWRDKOCHI", "006-SWRDKOCHI"]:
    info = TARGET_STATIONS[code]
    df = all_dfs.get(code)
    print(f"Station: {info['name']} ({code}) in {info['district']}")
    if df is not None:
        yr_breakdown = df.groupby(df['dataTime'].dt.year).size().reset_index(name='reading_count')
        print(yr_breakdown.to_string(index=False))
        print(f"Total: {len(df)} rows\n")

# 2. FULL COVERAGE TABLE
print("\n### 2. FULL YEAR-BY-YEAR COVERAGE TABLE\n")
cov_rows = []
for code, info in TARGET_STATIONS.items():
    df = all_dfs.get(code)
    if df is None:
        continue
    df['year'] = df['dataTime'].dt.year
    df['month'] = df['dataTime'].dt.month
    df['date'] = df['dataTime'].dt.date
    
    for yr in sorted(df['year'].unique()):
        sub_yr = df[df['year'] == yr]
        total_days = 366 if (yr % 4 == 0 and (yr % 100 != 0 or yr % 400 == 0)) else 365
        active_days = sub_yr['date'].nunique()
        readings_cnt = len(sub_yr)
        rpd = round(readings_cnt / active_days, 1) if active_days > 0 else 0.0
        
        # Monsoon Jun-Oct (153 days)
        monsoon_sub = sub_yr[sub_yr['month'].isin([6, 7, 8, 9, 10])]
        monsoon_days = monsoon_sub['date'].nunique()
        monsoon_missing = 153 - monsoon_days
        full_missing = total_days - active_days
        
        cov_rows.append({
            "Station": info["name"],
            "District": info["district"],
            "Year": yr,
            "Typical Readings/Day": rpd,
            "Jun-Oct Active (of 153)": f"{monsoon_days} / 153",
            "Jun-Oct Missing": monsoon_missing,
            "Full Year Active": f"{active_days} / {total_days}",
            "Full Year Missing": full_missing
        })

df_cov = pd.DataFrame(cov_rows)
print(df_cov.to_string(index=False))

# 3. OUTLIERS & NEIGHBOURING READINGS
print("\n### 3. OUTLIER COUNTS & TOP 10 EXTREME VALUES WITH NEIGHBOURS\n")
outlier_summary = []
for code, info in TARGET_STATIONS.items():
    df = all_dfs.get(code)
    if df is None:
        continue
    vals = df['dataValue'].dropna()
    p999 = vals.quantile(0.999)
    neg_zero = df[df['dataValue'] <= 0.0]
    high_p999 = df[df['dataValue'] > p999]
    outlier_summary.append({
        "Station Code": code,
        "Station Name": info["name"],
        "District": info["district"],
        "Total Readings": len(df),
        "99.9th %ile": f"{p999:.2f} m",
        "Readings <= 0.0m": len(neg_zero),
        "Readings > 99.9th %ile": len(high_p999),
        "Total Flagged": len(neg_zero) + len(high_p999)
    })

print(pd.DataFrame(outlier_summary).to_string(index=False))

# Deep dive into MUTHANKERA, VANDIPERIYAR, KALLOOPPARA extreme values with neighbours
for code in ["003-SWRDKOCHI", "016-SWRDKOCHI", "017-SWRDKOCHI"]:
    info = TARGET_STATIONS[code]
    df = all_dfs[code].copy()
    print(f"\n==========================================================================================")
    print(f"Top 10 Extreme Readings & Neighbouring Context for {info['name']} ({code})")
    print(f"==========================================================================================")
    
    # Sort by absolute deviation from median
    med = df['dataValue'].median()
    df['abs_dev'] = (df['dataValue'] - med).abs()
    top10_indices = df.sort_values('abs_dev', ascending=False).head(10).index
    
    for idx in top10_indices:
        target_row = df.loc[idx]
        t_time = target_row['dataTime']
        t_val = target_row['dataValue']
        
        # Get 2 preceding and 2 succeeding readings
        start_idx = max(0, idx - 2)
        end_idx = min(len(df), idx + 3)
        context_df = df.iloc[start_idx:end_idx][['dataTime', 'dataValue']]
        print(f"\nFlagged Reading: {t_time} -> {t_val} m")
        print("Surrounding 5 readings:")
        print(context_df.to_string(index=False))

