import glob, json, os, pandas as pd

# 1. Compare station-years between old station files and v2 files
old_station_files = sorted(glob.glob("data/raw/labels/cwc/station_*.csv"))
v2_station_files = sorted(glob.glob("data/raw/labels/cwc/v2/station_*.csv"))

print("=== OLD FILES VS V2 FILES YEAR COMPARISON ===")
for vf in v2_station_files:
    base = os.path.basename(vf)
    of = os.path.join("data/raw/labels/cwc", base)
    
    vdf = pd.read_csv(vf, parse_dates=["dataTime"])
    v_years = set(vdf.dataTime.dt.year.unique())
    
    if os.path.exists(of):
        odf = pd.read_csv(of, parse_dates=["dataTime"])
        o_years = set(odf.dataTime.dt.year.unique())
        
        in_old_not_v2 = sorted(list(o_years - v_years))
        in_v2_not_old = sorted(list(v_years - o_years))
        print(f"\n{base}:")
        print(f"  Old file rows: {len(odf):,} | Years in old: {sorted(list(o_years))}")
        print(f"  V2 file rows:  {len(vdf):,} | Years in v2:  {sorted(list(v_years))}")
        print(f"  Years present in Old but MISSING in V2: {in_old_not_v2}")
        print(f"  Years present in V2 but MISSING in Old: {in_v2_not_old}")
    else:
        print(f"\n{base}: No direct old station file match.")

# 2. Check district level old files (cwc_{district}_water_levels.csv)
print("\n=== OLD DISTRICT FILES (cwc_{district}_water_levels.csv) ===")
dist_files = sorted(glob.glob("data/raw/labels/cwc/cwc_*_water_levels.csv"))
for df_path in dist_files:
    ddf = pd.read_csv(df_path, parse_dates=["dataTime"])
    print(f"\n{os.path.basename(df_path)} ({len(ddf):,} rows):")
    stations = ddf["stationCode"].unique()
    for st in stations:
        st_sub = ddf[ddf["stationCode"] == st]
        print(f"  Station {st}: {len(st_sub):,} rows | Years: {sorted(st_sub.dataTime.dt.year.unique().tolist())}")

# 3. Check v2_requests_log.json details for missing years
print("\n=== ZERO-ROW REQUESTS LOG DETAILS ===")
with open("data/raw/labels/cwc/v2/v2_requests_log.json") as lf:
    logs = json.load(lf)

log_df = pd.DataFrame(logs)
print("Log columns:", list(log_df.columns))

# Group by stationCode and check months returned
for st_code, g in log_df.groupby("stationCode"):
    st_name = g["stationName"].iloc[0]
    zero_g = g[g["matched_rows"] == 0]
    nonzero_g = g[g["matched_rows"] > 0]
    print(f"\nStation {st_code} ({st_name}):")
    print(f"  Total API calls logged: {len(g)}")
    print(f"  Calls returning >0 rows: {len(nonzero_g)} (Total rows downloaded: {nonzero_g['matched_rows'].sum():,})")
    print(f"  Calls returning 0 rows:  {len(zero_g)}")
    
    # List years with zero rows
    zero_dates = zero_g["startdate"].str[:7].tolist()
    # Check if whole years returned 0
    zero_years = g.groupby(g["startdate"].str[:4]).agg(
        total_months=("startdate", "count"),
        zero_months=("matched_rows", lambda s: (s == 0).sum()),
        total_rows=("matched_rows", "sum")
    )
    print("  Year-by-year API response summary:")
    print(zero_years.to_string())
