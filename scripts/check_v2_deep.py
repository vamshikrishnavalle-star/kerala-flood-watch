import glob, json, os, pandas as pd

station_files = sorted(glob.glob("data/raw/labels/cwc/v2/station_*.csv"))
print(f"Found {len(station_files)} station CSV files to check:\n")

for f in station_files:
    d = pd.read_csv(f, parse_dates=["dataTime"])
    d["year"] = d.dataTime.dt.year
    print(f"\n=======================================================")
    print(f"{os.path.basename(f)} | Total Rows: {len(d):,}")
    print(f"=======================================================")
    print("  Full-row duplicates:", d.duplicated().sum())
    key = [c for c in ["dataTime", "datatypeCode"] if c in d.columns]
    print("  Duplicates on", key, ":", d.duplicated(subset=key).sum())
    if "datatypeCode" in d.columns:
        print("\n  Datatype breakdown:")
        print("  " + d.groupby(["datatypeCode", "description", "unit"], dropna=False).size().to_string().replace("\n", "\n  "))
    
    y = d.groupby("year").agg(
        rows=("dataTime", "size"),
        days=("dataTime", lambda s: s.dt.date.nunique()),
        jun_oct_days=("dataTime", lambda s: s[s.dt.month.between(6, 10)].dt.date.nunique())
    )
    y["rows_per_day"] = (y.rows / y.days).round(1)
    print("\n  Yearly Coverage (rows, active days, Jun-Oct days, rows/day):")
    print(y.to_string())
    
    # Check peak flood window 2018
    a = d[(d.dataTime >= "2018-08-14") & (d.dataTime < "2018-08-21")]
    print(f"\n  Aug 14-20 2018 days present: {a.dataTime.dt.date.nunique()} of 7 (Total readings: {len(a)})")

try:
    log = json.load(open("data/raw/labels/cwc/v2/v2_requests_log.json"))
    print(f"\n=======================================================")
    print(f"API Requests Logged in v2_requests_log.json: {len(log):,} requests")
    print("Sample logged request:")
    print(json.dumps(log[0], indent=2))
    print(f"=======================================================")
except Exception as e:
    print("Log read failed:", e)
