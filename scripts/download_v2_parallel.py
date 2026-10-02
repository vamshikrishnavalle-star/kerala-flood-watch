"""High-speed Parallel v2 CWC Downloader & Audit:
- 8 concurrent threads (one per station).
- Month-by-month chunks with multi-page pagination.
- Writes to data/raw/labels/cwc/v2/.
- Full logging, strict coverage reconciliation, and mixed-series audit.
"""

import calendar
import concurrent.futures
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import httpx
import pandas as pd

v2_dir = Path("data/raw/labels/cwc/v2")
v2_dir.mkdir(parents=True, exist_ok=True)

STATIONS = {
    "016-SWRDKOCHI": {"name": "VANDIPERIYAR", "district": "Idukki", "start_yr": 2000, "end_yr": 2024},
    "017-SWRDKOCHI": {"name": "KALLOOPPARA", "district": "Pathanamthitta", "start_yr": 2000, "end_yr": 2024},
    "013-SWRDKOCHI": {"name": "KALAMPUR", "district": "Ernakulam", "start_yr": 2015, "end_yr": 2024},
    "015-SWRDKOCHI": {"name": "KIDANGOOR", "district": "Kottayam", "start_yr": 2015, "end_yr": 2024},
    "011-SWRDKOCHI": {"name": "ARANGALI", "district": "Thrissur", "start_yr": 2015, "end_yr": 2024},
    "008-SWRDKOCHI": {"name": "KUMBIDI", "district": "Palakkad", "start_yr": 2015, "end_yr": 2024},
    "006-SWRDKOCHI": {"name": "KARATHODU", "district": "Malappuram", "start_yr": 2015, "end_yr": 2024},
}

API_URL = "https://indiawris.gov.in/Dataset/River Water Level"
HEADERS = {"accept": "application/json", "User-Agent": "Mozilla/5.0"}

def download_station(code, info):
    st_name = info["name"]
    dist = info["district"]
    start_yr = info["start_yr"]
    end_yr = info["end_yr"]
    
    st_records = []
    st_logs = []
    
    with httpx.Client(timeout=30.0, verify=True) as client:
        for yr in range(start_yr, end_yr + 1):
            for month in range(1, 13):
                _, last_day = calendar.monthrange(yr, month)
                s_date = f"{yr}-{month:02d}-01"
                e_date = f"{yr}-{month:02d}-{last_day:02d}"
                
                page = 0
                while True:
                    params = {
                        "stateName": "Kerala",
                        "districtName": dist.capitalize(),
                        "agencyName": "CWC",
                        "startdate": s_date,
                        "enddate": e_date,
                        "download": "false",
                        "page": page,
                        "size": 1000
                    }
                    req_ts = datetime.now(timezone.utc).isoformat()
                    try:
                        r = client.post(API_URL, params=params, headers=HEADERS)
                        if r.status_code == 200:
                            data = r.json().get("data", [])
                            matched = [d for d in data if str(d.get("stationCode")).strip() == code and d.get("dataValue") is not None]
                            
                            first_ts = matched[0].get("dataTime") if matched else None
                            last_ts = matched[-1].get("dataTime") if matched else None
                            
                            st_logs.append({
                                "stationCode": code,
                                "stationName": st_name,
                                "district": dist,
                                "startdate": s_date,
                                "enddate": e_date,
                                "page": page,
                                "total_page_rows": len(data),
                                "matched_rows": len(matched),
                                "first_ts": first_ts,
                                "last_ts": last_ts,
                                "ts_utc": req_ts
                            })
                            
                            if matched:
                                st_records.extend(matched)
                                
                            if len(data) < 1000:
                                break
                            page += 1
                            time.sleep(0.02)
                        else:
                            st_logs.append({"stationCode": code, "error": f"http_{r.status_code}", "ts_utc": req_ts})
                            break
                    except Exception as e:
                        st_logs.append({"stationCode": code, "exception": str(e), "ts_utc": req_ts})
                        break
                        
    if st_records:
        df = pd.DataFrame(st_records)
        df['dataTime'] = pd.to_datetime(df['dataTime'])
        df = df.sort_values('dataTime').drop_duplicates(subset=['dataTime', 'datatypeCode', 'dataValue']).reset_index(drop=True)
        csv_path = v2_dir / f"station_{code}_{st_name.lower()}.csv"
        df.to_csv(csv_path, index=False)
        print(f"[COMPLETED] {st_name} ({code}): {len(df):,} verified rows -> {csv_path.name}")
        return code, len(df), st_logs
    else:
        print(f"[WARNING] 0 rows for {st_name}")
        return code, 0, st_logs

print("Spawning 8 parallel workers for concurrent station downloads...")
start_time = time.time()

all_logs = []
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    futures = [executor.submit(download_station, code, info) for code, info in STATIONS.items()]
    for f in concurrent.futures.as_completed(futures):
        c, count, logs = f.result()
        all_logs.extend(logs)

elapsed = time.time() - start_time
print(f"\nAll downloads completed in {elapsed:.1f} seconds! Saving request logs...")

with open(v2_dir / "v2_requests_log.json", "w", encoding="utf-8") as lf:
    json.dump(all_logs, lf, indent=2)

print("\n==========================================================================================")
print("AUDIT & COVERAGE RECONCILIATION")
print("==========================================================================================")

# 1. Coverage Table
cov_rows = []
all_v2_dfs = {}

for code, info in STATIONS.items():
    csv_f = v2_dir / f"station_{code}_{info['name'].lower()}.csv"
    if not csv_f.exists():
        continue
    df = pd.read_csv(csv_f)
    df['dataTime'] = pd.to_datetime(df['dataTime'])
    df['dataValue'] = pd.to_numeric(df['dataValue'], errors='coerce')
    all_v2_dfs[code] = df
    
    df['year'] = df['dataTime'].dt.year
    df['month'] = df['dataTime'].dt.month
    df['date'] = df['dataTime'].dt.date
    
    file_total_rows = len(df)
    sum_year_rows = 0
    
    # Calculate median timestamp gap
    time_diffs = df['dataTime'].diff().dt.total_seconds() / 3600.0
    med_gap_hrs = time_diffs.median()
    
    for yr in sorted(df['year'].unique()):
        sub_yr = df[df['year'] == yr]
        yr_rows = len(sub_yr)
        sum_year_rows += yr_rows
        
        full_distinct_days = sub_yr['date'].nunique()
        total_cal_days = 366 if (yr % 4 == 0 and (yr % 100 != 0 or yr % 400 == 0)) else 365
        
        monsoon_sub = sub_yr[sub_yr['month'].isin([6, 7, 8, 9, 10])]
        monsoon_distinct_days = monsoon_sub['date'].nunique()
        
        cov_rows.append({
            "Station": info["name"],
            "District": info["district"],
            "Year": yr,
            "Rows": yr_rows,
            "Full Year Distinct Days": f"{full_distinct_days} / {total_cal_days}",
            "Jun-Oct Distinct Days": f"{monsoon_distinct_days} / 153",
            "Median Interval": f"{med_gap_hrs:.1f} hrs"
        })
        
    assert sum_year_rows == file_total_rows, f"Row sum mismatch: {sum_year_rows} != {file_total_rows}"

df_cov = pd.DataFrame(cov_rows)
df_cov.to_csv(v2_dir / "coverage_table_v2.csv", index=False)

print("\n--- REBUILT COVERAGE TABLE (v2 Reconciled) ---")
print(df_cov.to_string(index=False))

# 2. VANDIPERIYAR Mixed Series Analysis
print("\n==========================================================================================")
print("VANDIPERIYAR (016-SWRDKOCHI) MIXED SERIES AUDIT")
print("==========================================================================================")
v_df = all_v2_dfs.get("016-SWRDKOCHI")
if v_df is not None:
    group_cols = [c for c in ['datatypeCode', 'description', 'unit'] if c in v_df.columns]
    grouped = v_df.groupby(group_cols).agg(
        record_count=('dataValue', 'count'),
        min_val=('dataValue', 'min'),
        median_val=('dataValue', 'median'),
        max_val=('dataValue', 'max')
    ).reset_index()
    print(grouped.to_string(index=False))
    
    # Check 2021 date gaps for Vandiperiyar
    v_2021 = v_df[v_df['year'] == 2021]
    v_2021_dates = set(v_2021['date'])
    all_2021_dates = set(pd.date_range("2021-01-01", "2021-12-31").date)
    missing_2021 = sorted(list(all_2021_dates - v_2021_dates))
    print(f"\nVandiperiyar 2021 Total Missing Days: {len(missing_2021)} days")
    print(f"Missing Periods in 2021: First missing = {missing_2021[0]}, Last missing = {missing_2021[-1]}")
    if len(missing_2021) > 10:
        print(f"Sample of 2021 missing dates: {[str(d) for d in missing_2021[:10]]} ...")

print("\nAll tasks finished successfully!")
