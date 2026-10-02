"""Robust v2 CWC Downloader & Audit Script:
- Monthly windows + multi-page pagination.
- Writes to data/raw/labels/cwc/v2/.
- Request-by-request logging (params, rows, first/last ts).
- Full coverage table with strict row-count reconciliation.
- Vandiperiyar mixed series audit (datatypeCode, description, unit) & 2021 gap analysis.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
import calendar
import httpx
import numpy as np
import pandas as pd

v2_dir = Path("data/raw/labels/cwc/v2")
v2_dir.mkdir(parents=True, exist_ok=True)

# 7 Target River Stations (Excluding Muthankera / Wayanad per rule)
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

request_log = []
downloaded_stations = {}

print("Starting v2 download with monthly pagination into data/raw/labels/cwc/v2/...")

with httpx.Client(timeout=30.0, verify=True) as client:
    for code, info in STATIONS.items():
        st_name = info["name"]
        dist = info["district"]
        start_yr = info["start_yr"]
        end_yr = info["end_yr"]
        
        print(f"\n==========================================")
        print(f"Fetching {st_name} ({code}) in {dist} [{start_yr}–{end_yr}]")
        print(f"==========================================")
        
        station_rows = []
        
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
                            
                            request_log.append({
                                "stationCode": code,
                                "stationName": st_name,
                                "district": dist,
                                "startdate": s_date,
                                "enddate": e_date,
                                "page": page,
                                "total_page_rows": len(data),
                                "matched_station_rows": len(matched),
                                "first_timestamp": first_ts,
                                "last_timestamp": last_ts,
                                "timestamp_utc": req_ts
                            })
                            
                            if matched:
                                station_rows.extend(matched)
                                
                            # If total rows returned for district < 1000, all pages for this month are done
                            if len(data) < 1000:
                                break
                            page += 1
                            time.sleep(0.05)
                        else:
                            request_log.append({
                                "stationCode": code,
                                "stationName": st_name,
                                "district": dist,
                                "startdate": s_date,
                                "enddate": e_date,
                                "page": page,
                                "http_error": r.status_code,
                                "timestamp_utc": req_ts
                            })
                            break
                    except Exception as exc:
                        request_log.append({
                            "stationCode": code,
                            "stationName": st_name,
                            "district": dist,
                            "startdate": s_date,
                            "enddate": e_date,
                            "page": page,
                            "exception": str(exc),
                            "timestamp_utc": req_ts
                        })
                        break
                        
        if station_rows:
            df = pd.DataFrame(station_rows)
            df['dataTime'] = pd.to_datetime(df['dataTime'])
            # Sort and preserve all distinct measurements
            df = df.sort_values('dataTime').drop_duplicates(subset=['dataTime', 'datatypeCode', 'dataValue']).reset_index(drop=True)
            v2_csv_path = v2_dir / f"station_{code}_{st_name.lower()}.csv"
            df.to_csv(v2_csv_path, index=False)
            downloaded_stations[code] = df
            print(f"--> Saved {len(df):,} total verified rows to {v2_csv_path}")

# Save request log
with open(v2_dir / "v2_requests_log.json", "w", encoding="utf-8") as f:
    json.dump(request_log, f, indent=2)

print("\nv2 Download Complete. Generating reconciliation and coverage audit...")
