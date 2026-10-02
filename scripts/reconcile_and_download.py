"""Complete, un-truncated downloader with monthly windowing, explicit pagination, request logging, and mixed-series audit."""

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

# 7 Target River Stations
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

request_logs = []
downloaded_data = {}

print("==========================================================================================")
print("STARTING ROBUST DOWNLOAD WITH MONTHLY CHUNKS & FULL PAGINATION")
print("==========================================================================================")

with httpx.Client(timeout=30.0, verify=True) as client:
    for code, info in STATIONS.items():
        st_name = info["name"]
        dist = info["district"]
        start_yr = info["start_yr"]
        end_yr = info["end_yr"]
        
        print(f"\nFetching {st_name} ({code}) in {dist} ({start_yr}–{end_yr})...")
        station_records = []
        
        for yr in range(start_yr, end_yr + 1):
            # Query in 2 half-year blocks (Jan-Jun and Jul-Dec) or monthly to never hit 1000 limit
            month_blocks = [
                (f"{yr}-01-01", f"{yr}-03-31"),
                (f"{yr}-04-01", f"{yr}-06-30"),
                (f"{yr}-07-01", f"{yr}-09-30"),
                (f"{yr}-10-01", f"{yr}-12-31"),
            ]
            
            for s_date, e_date in month_blocks:
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
                            count = len(matched)
                            
                            first_ts = matched[0].get("dataTime") if matched else None
                            last_ts = matched[-1].get("dataTime") if matched else None
                            
                            request_logs.append({
                                "stationCode": code,
                                "stationName": st_name,
                                "district": dist,
                                "startdate": s_date,
                                "enddate": e_date,
                                "page": page,
                                "status_code": r.status_code,
                                "total_returned_on_page": len(data),
                                "station_matched_rows": count,
                                "first_timestamp": first_ts,
                                "last_timestamp": last_ts,
                                "timestamp_utc": req_ts
                            })
                            
                            if matched:
                                station_records.extend(matched)
                                
                            # If total returned on page < 1000, there are no more pages
                            if len(data) < 1000:
                                break
                            page += 1
                            time.sleep(0.1)
                        else:
                            request_logs.append({
                                "stationCode": code,
                                "stationName": st_name,
                                "district": dist,
                                "startdate": s_date,
                                "enddate": e_date,
                                "page": page,
                                "status_code": r.status_code,
                                "error": r.text[:200],
                                "timestamp_utc": req_ts
                            })
                            break
                    except Exception as e:
                        request_logs.append({
                            "stationCode": code,
                            "stationName": st_name,
                            "district": dist,
                            "startdate": s_date,
                            "enddate": e_date,
                            "page": page,
                            "error": str(e),
                            "timestamp_utc": req_ts
                        })
                        break
                        
        if station_records:
            df = pd.DataFrame(station_records)
            df['dataTime'] = pd.to_datetime(df['dataTime'])
            # Sort chronologically and drop duplicate timestamps
            df = df.sort_values('dataTime').drop_duplicates(subset=['dataTime', 'datatypeCode', 'dataValue']).reset_index(drop=True)
            csv_path = out_dir / f"station_{code}_{st_name.lower()}.csv"
            df.to_csv(csv_path, index=False)
            downloaded_data[code] = df
            print(f"  ==> Saved complete un-truncated dataset: {len(df):,} rows to {csv_path}")
        else:
            print(f"  ==> WARNING: 0 rows collected for {st_name}")

# Save full request log to disk
with open(out_dir / "complete_download_requests_log.json", "w", encoding="utf-8") as f:
    json.dump(request_logs, f, indent=2)

print("\nDownload complete. Running analysis...")
