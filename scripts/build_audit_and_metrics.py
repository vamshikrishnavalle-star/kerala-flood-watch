"""Full Audit & Metrics Script for v3 CWC River Stage Datasets:
- Evaluates manifest.csv.
- Reports first month of data & 2000-2014 empty/failed status per station.
- Computes (HHS - HZS) offset distributions, single-series timestamps, Vandiperiyar 0-value checks.
- Generates 2018 flood week daily tables per station & datatypeCode.
"""

import glob
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd

BASE_DIR = Path("data/raw/labels/cwc")
V3_DIR = BASE_DIR / "v3"
MANIFEST_PATH = V3_DIR / "manifest.csv"

def audit():
    print("="*80)
    print("1. MANIFEST CSV AUDIT & 2000-2014 STATUS")
    print("="*80)
    
    if not MANIFEST_PATH.exists():
        print(f"Manifest not yet generated at {MANIFEST_PATH}")
        return
        
    mdf = pd.read_csv(MANIFEST_PATH)
    print(f"Total entries in manifest: {len(mdf):,}")
    print("\nStatus summary:")
    print(mdf["status"].value_counts().to_string())
    print(f"\nFailed tasks count: {(mdf['status'] == 'failed').sum()}")
    
    # Station by station first month & 2000-2014 status
    print("\n--- Per-Station Historical Probe (2000-2014 & Earliest Record) ---")
    for scode, group in mdf.groupby("station_code"):
        sname = group["station_name"].iloc[0]
        dist = group["district"].iloc[0]
        
        # Earliest month with ok_rows
        rows_group = group[group["status"] == "ok_rows"].sort_values("month")
        first_month = rows_group["month"].iloc[0] if not rows_group.empty else "NO_DATA"
        first_rows = rows_group["rows"].iloc[0] if not rows_group.empty else 0
        
        # 2000-2014 status
        p2000_2014 = group[group["month"] < "2015-01"]
        p_status = p2000_2014["status"].value_counts().to_dict()
        
        print(f"\nStation {scode} ({sname}, {dist}):")
        print(f"  First month with data: {first_month} ({first_rows:,} rows)")
        print(f"  2000-2014 months status ({len(p2000_2014)} total months): {p_status}")
    
    print("\n" + "="*80)
    print("2. V3 CLEAN DATASETS COVERAGE TABLE")
    print("="*80)
    
    v3_files = sorted(glob.glob(str(V3_DIR / "station_*.csv")))
    for vf in v3_files:
        df = pd.read_csv(vf, parse_dates=["dataTime"])
        df["year"] = df.dataTime.dt.year
        scode = df["stationCode"].iloc[0]
        sname = df["stationName"].iloc[0]
        dist = df["district"].iloc[0]
        total_rows = len(df)
        
        yearly = df.groupby("year").agg(
            rows=("dataTime", "size"),
            days=("dataTime", lambda s: s.dt.date.nunique()),
            jun_oct_days=("dataTime", lambda s: s[s.dt.month.between(6, 10)].dt.date.nunique()),
            hhs_rows=("datatypeCode", lambda s: (s == "HHS").sum()),
            hzs_rows=("datatypeCode", lambda s: (s == "HZS").sum())
        ).reset_index()
        
        print(f"\nStation: {sname} ({scode}), District: {dist} | Total File Rows: {total_rows:,}")
        print(f"{'Year':<6} | {'Total Rows':<10} | {'Active Days':<11} | {'Jun-Oct Days':<12} | {'Rows/Day':<8} | {'HHS Rows':<8} | {'HZS Rows':<8}")
        print("-" * 75)
        for _, r in yearly.iterrows():
            r_day = round(r['rows'] / r['days'], 1) if r['days'] > 0 else 0
            print(f"{r['year']:<6} | {r['rows']:<10,} | {r['days']:<11} | {r['jun_oct_days']:<12} | {r_day:<8} | {r['hhs_rows']:<8,} | {r['hzs_rows']:<8,}")
            
    print("\n" + "="*80)
    print("3. HHS - HZS OFFSET DISTRIBUTION & SINGLE-SERIES TIMESTAMPS")
    print("="*80)
    
    for vf in v3_files:
        df = pd.read_csv(vf, parse_dates=["dataTime"])
        scode = df["stationCode"].iloc[0]
        sname = df["stationName"].iloc[0]
        
        hhs = df[df.datatypeCode == "HHS"][["dataTime", "dataValue"]].rename(columns={"dataValue": "HHS"})
        hzs = df[df.datatypeCode == "HZS"][["dataTime", "dataValue"]].rename(columns={"dataValue": "HZS"})
        
        merged = pd.merge(hhs, hzs, on="dataTime", how="inner")
        merged["diff"] = merged["HHS"] - merged["HZS"]
        
        hhs_only = len(set(hhs["dataTime"]) - set(hzs["dataTime"]))
        hzs_only = len(set(hzs["dataTime"]) - set(hhs["dataTime"]))
        
        print(f"\nStation {scode} ({sname}):")
        print(f"  Total HHS rows: {len(hhs):,} | Total HZS rows: {len(hzs):,}")
        print(f"  Concurrent timestamps (both HHS & HZS): {len(merged):,}")
        print(f"  HHS-only timestamps: {hhs_only:,}")
        print(f"  HZS-only timestamps: {hzs_only:,}")
        
        if not merged.empty:
            stats = merged["diff"].describe(percentiles=[0.01, 0.25, 0.5, 0.75, 0.99])
            print(f"  (HHS - HZS) Offset Summary:")
            print(f"    Min: {stats['min']:.2f} | 25%: {stats['25%']:.2f} | Median: {stats['50%']:.2f} | 75%: {stats['75%']:.2f} | Max: {stats['max']:.2f}")
            print(f"    Top 5 most frequent offsets:")
            print("    " + merged["diff"].round(2).value_counts().head(5).to_string().replace("\n", "\n    "))
            
        if "vandiperiyar" in sname.lower():
            # Vandiperiyar specific checks: HHS == 0, HZS == -789.00
            hhs_zero = (hhs["HHS"] == 0).sum()
            hzs_zero = (hzs["HZS"] == 0).sum()
            hzs_neg_789 = (hzs["HZS"] == -789.00).sum()
            hhs_neg_789 = (hhs["HHS"] == -789.00).sum()
            print(f"\n  VANDIPERIYAR SPECIFIC ZERO/NEGATIVE CHECKS:")
            print(f"    HHS == 0 rows: {hhs_zero:,}")
            print(f"    HZS == 0 rows: {hzs_zero:,}")
            print(f"    HZS == -789.00 rows: {hzs_neg_789:,}")
            print(f"    HHS == -789.00 rows: {hhs_neg_789:,}")

    print("\n" + "="*80)
    print("4. AUGUST 14-20 2018 DAILY FLOOD COVERAGE PER STATION & DATATYPE")
    print("="*80)
    flood_days = pd.date_range("2018-08-14", "2018-08-20", freq="D").date
    for vf in v3_files:
        df = pd.read_csv(vf, parse_dates=["dataTime"])
        scode = df["stationCode"].iloc[0]
        sname = df["stationName"].iloc[0]
        sub = df[(df.dataTime >= "2018-08-14") & (df.dataTime < "2018-08-21")].copy()
        sub["date"] = sub.dataTime.dt.date
        print(f"\nStation: {sname} ({scode})")
        if sub.empty:
            print("  NO DATA in 2018-08-14 to 2018-08-20.")
            continue
        piv = sub.groupby(["date", "datatypeCode"]).size().unstack(fill_value=0)
        piv["Total"] = piv.sum(axis=1)
        piv = piv.reindex(flood_days, fill_value=0)
        print(piv.to_string())

if __name__ == "__main__":
    audit()
