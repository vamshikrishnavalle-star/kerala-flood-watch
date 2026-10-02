import glob, json, os, sys
import pandas as pd
import numpy as np

print("="*80)
print("1. COVERAGE TABLE COMPUTED DIRECTLY FROM V2 FILES")
print("="*80)

station_files = sorted(glob.glob("data/raw/labels/cwc/v2/station_*.csv"))

coverage_rows = []
for f in station_files:
    df = pd.read_csv(f, parse_dates=["dataTime"])
    df["year"] = df.dataTime.dt.year
    station_code = df["stationCode"].iloc[0] if "stationCode" in df.columns else "UNKNOWN"
    station_name = df["stationName"].iloc[0] if "stationName" in df.columns else os.path.basename(f)
    district = df["district"].iloc[0] if "district" in df.columns else "UNKNOWN"
    total_file_rows = len(df)
    
    yearly = df.groupby("year").agg(
        rows=("dataTime", "size"),
        days=("dataTime", lambda s: s.dt.date.nunique()),
        jun_oct_days=("dataTime", lambda s: s[s.dt.month.between(6, 10)].dt.date.nunique()),
        hhs_rows=("datatypeCode", lambda s: (s == "HHS").sum()),
        hzs_rows=("datatypeCode", lambda s: (s == "HZS").sum())
    ).reset_index()
    
    assert yearly["rows"].sum() == total_file_rows, f"Mismatch in {f}: sum {yearly['rows'].sum()} != {total_file_rows}"
    
    print(f"\nStation: {station_name} ({station_code}), District: {district} | Total Rows in File: {total_file_rows:,}")
    print(f"{'Year':<6} | {'Total Rows':<10} | {'Active Days':<11} | {'Jun-Oct Days':<12} | {'Rows/Day':<8} | {'HHS Rows':<8} | {'HZS Rows':<8} | {'HHS/Day':<7} | {'HZS/Day':<7}")
    print("-" * 88)
    for _, r in yearly.iterrows():
        r_day = round(r['rows'] / r['days'], 1) if r['days'] > 0 else 0
        hhs_day = round(r['hhs_rows'] / r['days'], 1) if r['days'] > 0 else 0
        hzs_day = round(r['hzs_rows'] / r['days'], 1) if r['days'] > 0 else 0
        print(f"{r['year']:<6} | {r['rows']:<10,} | {r['days']:<11} | {r['jun_oct_days']:<12} | {r_day:<8} | {r['hhs_rows']:<8,} | {r['hzs_rows']:<8,} | {hhs_day:<7} | {hzs_day:<7}")
        coverage_rows.append({
            "station_code": station_code,
            "station_name": station_name,
            "district": district,
            "year": r["year"],
            "rows": r["rows"],
            "days": r["days"],
            "jun_oct_days": r["jun_oct_days"],
            "rows_per_day": r_day,
            "hhs_rows": r["hhs_rows"],
            "hzs_rows": r["hzs_rows"]
        })
    print(f"VERIFICATION: Sum of yearly rows ({yearly['rows'].sum():,}) == File total ({total_file_rows:,}) -> MATCH: TRUE")

print("\n" + "="*80)
print("2. OLD FILES VS V2 COMPARISON & REQUEST LOG AUDIT")
print("="*80)

# Check old files
old_files = sorted(glob.glob("data/raw/labels/cwc/*.csv"))
print("Old CSV files found in data/raw/labels/cwc/:")
for of in old_files:
    if "danger_levels" in of or "coverage" in of:
        continue
    try:
        odf = pd.read_csv(of)
        # find time column
        tcol = None
        for col in ["dataTime", "timestamp", "datetime", "Date"]:
            if col in odf.columns:
                tcol = col
                break
        if tcol:
            odf[tcol] = pd.to_datetime(odf[tcol], errors="coerce")
            years = sorted(odf[tcol].dt.year.dropna().unique().astype(int).tolist())
            print(f"  {os.path.basename(of)}: {len(odf):,} rows, years: {years}")
        else:
            print(f"  {os.path.basename(of)}: {len(odf):,} rows, cols: {list(odf.columns)}")
    except Exception as e:
        print(f"  {os.path.basename(of)}: error reading ({e})")

# Check v2_requests_log.json
print("\n--- v2_requests_log.json Deep Audit ---")
try:
    with open("data/raw/labels/cwc/v2/v2_requests_log.json") as lf:
        req_logs = json.load(lf)
    print(f"Total logged requests in v2_requests_log.json: {len(req_logs):,}")
    
    # Analyze zero row requests and status
    zero_rows = [r for r in req_logs if r.get("matched_rows", 0) == 0]
    non_zero = [r for r in req_logs if r.get("matched_rows", 0) > 0]
    errors = [r for r in req_logs if "error" in r or r.get("status_code", 200) != 200]
    
    print(f"Requests with > 0 rows: {len(non_zero):,}")
    print(f"Requests with 0 rows: {len(zero_rows):,}")
    print(f"Logged explicit errors / non-200: {len(errors):,}")
    
    # Check zero-row distribution by station and year
    zero_df = pd.DataFrame(zero_rows)
    if not zero_df.empty:
        zero_df["year"] = pd.to_datetime(zero_df["startdate"]).dt.year
        print("\nDistribution of 0-row monthly requests by station & year (API returned empty dataset):")
        piv = zero_df.groupby(["stationName", "year"]).size().unstack(fill_value=0)
        print(piv.to_string())
except Exception as e:
    print(f"Error reading requests log: {e}")

print("\n" + "="*80)
print("3. DATATYPES, DUPLICATE ANALYSIS & WHY >24 ROWS/DAY")
print("="*80)

for f in station_files:
    df = pd.read_csv(f, parse_dates=["dataTime"])
    station_name = df["stationName"].iloc[0] if "stationName" in df.columns else os.path.basename(f)
    print(f"\n--- Station: {station_name} ---")
    gb = df.groupby(["datatypeCode", "description", "unit"], dropna=False).agg(
        total_rows=("dataTime", "size"),
        distinct_timestamps=("dataTime", "nunique"),
        min_date=("dataTime", "min"),
        max_date=("dataTime", "max")
    ).reset_index()
    print(gb.to_string())
    
    full_dups = df.duplicated().sum()
    pair_dups = df.duplicated(subset=["dataTime", "datatypeCode"]).sum()
    print(f"  Full row duplicates: {full_dups}")
    print(f"  Duplicates on (dataTime, datatypeCode): {pair_dups}")
    
    # Look at time intervals / hours per day for a sample year (e.g. 2022 or 2023)
    df_recent = df[df.dataTime.dt.year >= 2021].copy()
    if not df_recent.empty:
        # Check readings per day per datatype
        df_recent["date"] = df_recent.dataTime.dt.date
        hhs_per_day = df_recent[df_recent.datatypeCode == "HHS"].groupby("date").size()
        hzs_per_day = df_recent[df_recent.datatypeCode == "HZS"].groupby("date").size()
        print(f"  2021+ daily stats:")
        print(f"    HHS readings/day: median = {hhs_per_day.median()}, min = {hhs_per_day.min()}, max = {hhs_per_day.max()}")
        print(f"    HZS readings/day: median = {hzs_per_day.median()}, min = {hzs_per_day.min()}, max = {hzs_per_day.max()}")
        # Check hours
        df_recent["hour"] = df_recent.dataTime.dt.hour
        hhs_hours = df_recent[df_recent.datatypeCode == "HHS"]["hour"].unique()
        print(f"    Hours present in HHS: {sorted(hhs_hours.tolist())}")

print("\n" + "="*80)
print("4. VANDIPERIYAR: HHS MINUS HZS OFFSET DISTRIBUTION")
print("="*80)
vandi_f = [f for f in station_files if "vandiperiyar" in f.lower()][0]
vdf = pd.read_csv(vandi_f, parse_dates=["dataTime"])

# Pivot or merge HHS and HZS on dataTime
hhs = vdf[vdf.datatypeCode == "HHS"][["dataTime", "dataValue"]].rename(columns={"dataValue": "HHS_MSL"})
hzs = vdf[vdf.datatypeCode == "HZS"][["dataTime", "dataValue"]].rename(columns={"dataValue": "HZS_Gauge"})

merged_vandi = pd.merge(hhs, hzs, on="dataTime", how="inner")
print(f"Total timestamps where BOTH HHS and HZS exist in Vandiperiyar: {len(merged_vandi):,}")

merged_vandi["diff_HHS_minus_HZS"] = merged_vandi["HHS_MSL"] - merged_vandi["HZS_Gauge"]

print("\nSummary statistics of (HHS - HZS):")
stats = merged_vandi["diff_HHS_minus_HZS"].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
print(stats.to_string())

print("\nDistinct values / histogram of (HHS - HZS):")
val_counts = merged_vandi["diff_HHS_minus_HZS"].round(2).value_counts().head(10)
print(val_counts.to_string())

print("\n" + "="*80)
print("5. AUGUST 14-20, 2018 DAILY COVERAGE PER STATION & DATATYPE")
print("="*80)

flood_days = pd.date_range("2018-08-14", "2018-08-20", freq="D").date

for f in station_files:
    df = pd.read_csv(f, parse_dates=["dataTime"])
    station_name = df["stationName"].iloc[0] if "stationName" in df.columns else os.path.basename(f)
    station_code = df["stationCode"].iloc[0] if "stationCode" in df.columns else "UNKNOWN"
    
    sub = df[(df.dataTime >= "2018-08-14") & (df.dataTime < "2018-08-21")].copy()
    sub["date"] = sub.dataTime.dt.date
    
    print(f"\nStation: {station_name} ({station_code})")
    if sub.empty:
        print("  NO DATA in 2018-08-14 to 2018-08-20.")
        continue
    
    piv = sub.groupby(["date", "datatypeCode"]).size().unstack(fill_value=0)
    piv["Total"] = piv.sum(axis=1)
    
    # Reindex over all 7 flood days to show any missing days explicitly
    piv = piv.reindex(flood_days, fill_value=0)
    print(piv.to_string())
