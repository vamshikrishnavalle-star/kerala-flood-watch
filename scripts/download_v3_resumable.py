"""High-Performance Resumable CWC Downloader & Comprehensive Audit Engine (v3):
- 3 worker threads using shared persistent HTTP connection pool.
- 5 retries with exponential backoff on DNS/network errors.
- Never breaks on error.
- Saves chunk files in data/raw/labels/cwc/v2/chunks/.
- Manifest CSV with district, month, pages, rows, status (ok_rows, ok_empty, failed), attempts.
- Merges sorted by (stationCode, datatypeCode, dataTime) into data/raw/labels/cwc/v3/.
"""

import calendar
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import glob
import json
import os
from pathlib import Path
import sys
import time
import httpx
import numpy as np
import pandas as pd

BASE_DIR = Path("data/raw/labels/cwc")
CHUNKS_DIR = BASE_DIR / "v2" / "chunks"
V3_DIR = BASE_DIR / "v3"
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
V3_DIR.mkdir(parents=True, exist_ok=True)

TARGET_STATIONS = {
    "016-SWRDKOCHI": {"name": "VANDIPERIYAR", "district": "Idukki", "start_yr": 2000, "end_yr": 2024},
    "017-SWRDKOCHI": {"name": "KALLOOPPARA", "district": "Pathanamthitta", "start_yr": 2000, "end_yr": 2024},
    "013-SWRDKOCHI": {"name": "KALAMPUR", "district": "Ernakulam", "start_yr": 2000, "end_yr": 2024},
    "015-SWRDKOCHI": {"name": "KIDANGOOR", "district": "Kottayam", "start_yr": 2000, "end_yr": 2024},
    "011-SWRDKOCHI": {"name": "ARANGALI", "district": "Thrissur", "start_yr": 2000, "end_yr": 2024},
    "008-SWRDKOCHI": {"name": "KUMBIDI", "district": "Palakkad", "start_yr": 2000, "end_yr": 2024},
    "006-SWRDKOCHI": {"name": "KARATHODU", "district": "Malappuram", "start_yr": 2000, "end_yr": 2024},
}

API_URL = "https://indiawris.gov.in/Dataset/River Water Level"
HEADERS = {"accept": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch_chunk_with_retry(client, params, max_retries=5):
    for attempt in range(1, max_retries + 1):
        try:
            r = client.post(API_URL, params=params, headers=HEADERS, timeout=30.0)
            if r.status_code == 200:
                data = r.json().get("data", [])
                return {"status": "ok", "data": data, "attempts": attempt, "status_code": 200}
            elif r.status_code in [429, 500, 502, 503, 504]:
                time.sleep(min(1.5 ** attempt, 15))
            else:
                return {"status": "failed", "error": f"http_{r.status_code}", "attempts": attempt, "data": []}
        except Exception as e:
            if attempt == max_retries:
                return {"status": "failed", "error": str(e), "attempts": attempt, "data": []}
            time.sleep(min(1.5 ** attempt, 15))
    return {"status": "failed", "error": "max_retries_exceeded", "attempts": max_retries, "data": []}

def run_month_task(task_args, client):
    st_code, st_name, dist, yr, month = task_args
    _, last_day = calendar.monthrange(yr, month)
    month_str = f"{yr}-{month:02d}"
    s_date = f"{month_str}-01"
    e_date = f"{month_str}-{last_day:02d}"
    
    manifest_entry = {
        "station_code": st_code,
        "station_name": st_name,
        "district": dist,
        "month": month_str,
        "start_date": s_date,
        "end_date": e_date,
        "pages": 0,
        "rows": 0,
        "status": "pending",
        "attempts": 0,
        "error": None
    }
    
    page = 0
    total_matched_records = []
    total_attempts = 0
    
    while True:
        chunk_file = CHUNKS_DIR / f"chunk_{st_code}_{month_str}_p{page}.json"
        
        chunk_res = None
        if chunk_file.exists():
            try:
                with open(chunk_file, "r") as cf:
                    chunk_res = json.load(cf)
            except Exception:
                chunk_res = None
                
        if chunk_res is None or chunk_res.get("status") != "ok":
            params = {
                "stateName": "Kerala",
                "districtName": dist.capitalize(),
                "stationCode": st_code,
                "agencyName": "CWC",
                "startdate": s_date,
                "enddate": e_date,
                "download": "false",
                "page": page,
                "size": 1000
            }
            chunk_res = fetch_chunk_with_retry(client, params)
            total_attempts += chunk_res.get("attempts", 1)
            
            if chunk_res.get("status") == "ok":
                with open(chunk_file, "w") as cf:
                    json.dump(chunk_res, cf)
            else:
                manifest_entry["status"] = "failed"
                manifest_entry["error"] = chunk_res.get("error")
                manifest_entry["attempts"] = total_attempts
                return manifest_entry, []
        else:
            total_attempts += chunk_res.get("attempts", 1)
            
        page_data = chunk_res.get("data", [])
        matched = [d for d in page_data if str(d.get("stationCode")).strip() == st_code and d.get("dataValue") is not None]
        total_matched_records.extend(matched)
        
        # Stopping condition
        if len(page_data) < 1000:
            manifest_entry["pages"] = page + 1
            manifest_entry["rows"] = len(total_matched_records)
            manifest_entry["attempts"] = total_attempts
            manifest_entry["status"] = "ok_rows" if len(total_matched_records) > 0 else "ok_empty"
            return manifest_entry, total_matched_records
        
        page += 1

def main():
    print("="*80, flush=True)
    print("STARTING ROBUST RESUMABLE DOWNLOAD (2000-01 to 2024-12)", flush=True)
    print("="*80, flush=True)

    tasks = []
    for code, info in TARGET_STATIONS.items():
        for yr in range(2000, 2025):
            for m in range(1, 13):
                tasks.append((code, info["name"], info["district"], yr, m))

    print(f"Total month tasks across 7 stations (2000–2024): {len(tasks)}", flush=True)

    manifest_map = {}
    station_records = {code: [] for code in TARGET_STATIONS}

    limits = httpx.Limits(max_keepalive_connections=20, max_connections=20)
    with httpx.Client(verify=True, limits=limits, timeout=30.0) as client:
        pass_num = 1
        current_tasks = tasks
        
        while current_tasks and pass_num <= 3:
            print(f"\n--- PASS {pass_num}: Running {len(current_tasks)} tasks with 3 workers ---", flush=True)
            failed_tasks = []
            completed_count = 0
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(run_month_task, t, client): t for t in current_tasks}
                for future in as_completed(futures):
                    t_orig = futures[future]
                    m_entry, recs = future.result()
                    task_key = (m_entry["station_code"], m_entry["month"])
                    manifest_map[task_key] = m_entry
                    
                    if m_entry["status"] == "failed":
                        failed_tasks.append(t_orig)
                    
                    completed_count += 1
                    if completed_count % 100 == 0 or completed_count == len(current_tasks):
                        print(f"  Progress: {completed_count}/{len(current_tasks)} tasks completed...", flush=True)
            
            if failed_tasks:
                print(f"Pass {pass_num} completed with {len(failed_tasks)} failed tasks. Retrying...", flush=True)
                current_tasks = failed_tasks
                pass_num += 1
                time.sleep(2)
            else:
                print(f"Pass {pass_num} completed: ALL TASKS RESOLVED (failed == 0).", flush=True)
                break

    # Reconstruct complete datasets from all saved chunks on disk
    print("\n" + "="*80, flush=True)
    print("LOADING ALL SAVED CHUNKS & COMPILING V3 DATASETS", flush=True)
    print("="*80, flush=True)

    all_chunk_files = sorted(glob.glob(str(CHUNKS_DIR / "chunk_*.json")))
    print(f"Found {len(all_chunk_files):,} chunk files on disk.", flush=True)
    
    station_all_data = {code: [] for code in TARGET_STATIONS}
    for cf_path in all_chunk_files:
        try:
            with open(cf_path, "r") as cf:
                cdata = json.load(cf)
                rows = cdata.get("data", [])
                for r in rows:
                    scode = str(r.get("stationCode", "")).strip()
                    if scode in station_all_data and r.get("dataValue") is not None:
                        station_all_data[scode].append(r)
        except Exception as e:
            print(f"Error reading chunk {cf_path}: {e}", flush=True)

    # Save Manifest CSV
    manifest_rows = list(manifest_map.values())
    manifest_df = pd.DataFrame(manifest_rows).sort_values(["station_code", "month"]).reset_index(drop=True)
    manifest_path = V3_DIR / "manifest.csv"
    manifest_df.to_csv(manifest_path, index=False)
    print(f"\nManifest CSV saved to {manifest_path}", flush=True)
    print(f"Total entries in manifest: {len(manifest_df):,}")
    print(manifest_df["status"].value_counts().to_string(), flush=True)

    # Save v3 Station CSVs
    print("\n--- Saving v3 Datasets ---", flush=True)
    for code, info in TARGET_STATIONS.items():
        st_name = info["name"]
        raw_rows = station_all_data[code]
        v3_csv = V3_DIR / f"station_{code}_{st_name.lower()}.csv"
        if raw_rows:
            df = pd.DataFrame(raw_rows)
            df["dataTime"] = pd.to_datetime(df["dataTime"])
            # Strictly deduplicate on (stationCode, datatypeCode, dataTime)
            df = df.drop_duplicates(subset=["stationCode", "datatypeCode", "dataTime"])
            df = df.sort_values(["stationCode", "datatypeCode", "dataTime"]).reset_index(drop=True)
            df.to_csv(v3_csv, index=False)
            print(f"  {v3_csv.name}: {len(df):,} clean rows (Date range: {df['dataTime'].min()} to {df['dataTime'].max()})", flush=True)
        else:
            print(f"  WARNING: No data collected for {st_name} ({code})", flush=True)

    print("\nExecution complete!", flush=True)

if __name__ == "__main__":
    main()
