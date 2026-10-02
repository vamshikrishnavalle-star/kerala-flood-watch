"""Script to immediately analyze downloaded station CSVs, generate the full coverage table, audit all outliers, and explain time resolution and daily max logic."""

import glob
from pathlib import Path
import numpy as np
import pandas as pd

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
        all_dfs[code] = df

# 1. TRUNCATION & COUNT ANALYSIS
print("==========================================================================================")
print("1. TRUNCATION ANALYSIS & TOTAL RECORD COUNTS")
print("==========================================================================================")
count_rows = []
for code, info in TARGET_STATIONS.items():
    df = all_dfs.get(code)
    cnt = len(df) if df is not None else 0
    # Group by year to see distribution
    if df is not None:
        yr_counts = df.groupby(df['dataTime'].dt.year).size().to_dict()
    else:
        yr_counts = {}
    count_rows.append({
        "Station Code": code,
        "Station Name": info["name"],
        "District": info["district"],
        "Total Readings": f"{cnt:,}",
        "Yearly Distribution": ", ".join([f"{y}: {c}" for y, c in sorted(yr_counts.items())])
    })
print(pd.DataFrame(count_rows)[['Station Code', 'Station Name', 'District', 'Total Readings']].to_string(index=False))

# 2. FULL COVERAGE TABLE (ALL STATIONS, ALL YEARS)
print("\n==========================================================================================")
print("2. FULL YEAR-BY-YEAR COVERAGE MATRIX (2000–2024)")
print("==========================================================================================")
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
        rpd = round(readings_cnt / active_days, 1) if active_days > 0 else 0
        
        # Monsoon Jun-Oct (153 days)
        monsoon_sub = sub_yr[sub_yr['month'].isin([6, 7, 8, 9, 10])]
        monsoon_days = monsoon_sub['date'].nunique()
        monsoon_missing = 153 - monsoon_days
        full_missing = total_days - active_days
        
        cov_rows.append({
            "Station Name": info["name"],
            "District": info["district"],
            "Year": yr,
            "Typical Readings/Day": rpd,
            "Monsoon Active Days (Jun-Oct)": f"{monsoon_days} / 153",
            "Monsoon Missing Days": monsoon_missing,
            "Full Year Active Days": f"{active_days} / {total_days}",
            "Full Year Missing Days": full_missing
        })

df_cov = pd.DataFrame(cov_rows)
print(df_cov.to_string(index=False))

# 3. OUTLIER AUDIT (<= 0 OR > 99.9th PERCENTILE)
print("\n==========================================================================================")
print("3. OUTLIER AUDIT: READINGS <= 0 OR > 99.9th PERCENTILE")
print("==========================================================================================")

outlier_summary = []
flagged_records = []

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
        "Total Readings": len(df),
        "99.9th %ile (m)": round(p999, 2),
        "Readings <= 0": len(neg_zero),
        "Readings > 99.9th %ile": len(high_p999),
        "Total Outliers Flagged": len(neg_zero) + len(high_p999)
    })
    
    for _, r in neg_zero.iterrows():
        flagged_records.append({
            "Station Name": info["name"],
            "District": info["district"],
            "Timestamp": str(r['dataTime']),
            "Value (m)": r['dataValue'],
            "Flag": "Negative or Zero (<= 0.0m)"
        })
    for _, r in high_p999.iterrows():
        flagged_records.append({
            "Station Name": info["name"],
            "District": info["district"],
            "Timestamp": str(r['dataTime']),
            "Value (m)": r['dataValue'],
            "Flag": f"Extreme Spike (> 99.9th %ile: {p999:.2f}m)"
        })

df_outlier_summary = pd.DataFrame(outlier_summary)
df_flags = pd.DataFrame(flagged_records)

print(df_outlier_summary.to_string(index=False))

print(f"\n--- DETAILED FLAGGED OUTLIER ROWS (Sample of {len(df_flags)} records) ---")
print(df_flags.head(30).to_string(index=False))

# 4. TIME RESOLUTION & DAILY MAXIMUM METHODOLOGY
print("\n==========================================================================================")
print("4. TIME RESOLUTION & DAILY MAXIMUM COMPUTATION METHODOLOGY")
print("==========================================================================================")
res_rows = []
for code, info in TARGET_STATIONS.items():
    df = all_dfs.get(code)
    if df is None:
        continue
    diffs = df['dataTime'].diff().dt.total_seconds() / 3600.0
    med_diff = diffs.median()
    
    if med_diff == 1.0:
        res_type = "Hourly Continuous Telemetry (1-hour delta)"
    elif med_diff >= 12.0:
        res_type = "Daily / 12-hour Manual Staff Gauge Observation"
    else:
        res_type = f"Sub-daily Telemetry ({med_diff:.1f}-hour median delta)"
        
    res_rows.append({
        "Station Code": code,
        "Station Name": info["name"],
        "District": info["district"],
        "Median Delta (Hours)": f"{med_diff:.1f} hrs",
        "Reporting Mode": res_type
    })
print(pd.DataFrame(res_rows).to_string(index=False))
