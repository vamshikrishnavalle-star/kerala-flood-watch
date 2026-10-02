import math, pathlib
import pandas as pd
import numpy as np

SEP  = "=" * 72
THIN = "-" * 72

LABEL_FILE = pathlib.Path("data/processed/labels_daily.csv")
HIST_DIR   = pathlib.Path("data/raw/historical")

ZONE_MAP = {
    "KALLOOPPARA": "pathanamthitta_kozhencherry",
    "KIDANGOOR":   "kottayam_pala",
}
ZONE_DISTRICT = {
    "pathanamthitta_kozhencherry": "Pathanamthitta",
    "kottayam_pala":               "Kottayam",
}
WEATHER_VARS = [
    "precipitation_sum","rain_sum","temperature_2m_max",
    "temperature_2m_min","soil_moisture_0_7cm","soil_moisture_7_28cm",
]

def count_clusters(vals):
    n, in_c = 0, False
    for v in vals:
        if v == 1:
            if not in_c: n += 1; in_c = True
        else: in_c = False
    return n

# ============================================================
# TASK 5 (post-fetch): variable coverage by year
# ============================================================
print(SEP); print("TASK 5 -- VARIABLE COVERAGE BY YEAR"); print(SEP)
for zone_slug, district in ZONE_DISTRICT.items():
    fp = HIST_DIR / f"{zone_slug}.csv"
    if not fp.exists():
        print(f"  MISSING: {fp}"); continue
    wdf = pd.read_csv(fp, parse_dates=["date"])
    wdf["year"] = wdf["date"].dt.year
    print(f"\n  {zone_slug} ({district})")
    print(f"  rows={len(wdf):,}  {wdf['date'].min().date()} to {wdf['date'].max().date()}")
    header = f"  {'Year':>6}  {'rows':>5}  " + "  ".join(f"{v[:14]:>14}" for v in WEATHER_VARS)
    print(header)
    for yr, grp in wdf.groupby("year"):
        row = f"  {int(yr):>6}  {len(grp):>5}  "
        for v in WEATHER_VARS:
            if v not in grp.columns:
                row += f"  {'MISSING':>14}"
            else:
                nc = grp[v].isna().sum()
                row += f"  {str(nc)+' null' if nc else 'OK':>14}"
        print(row)

# ============================================================
# TASK 6 step 1: join and inspect
# ============================================================
print(); print(SEP); print("TASK 6 STEP 1 -- JOIN INSPECTION"); print(SEP)
import sys

# --- load labels ---
lbl = pd.read_csv(LABEL_FILE, parse_dates=["date"])
lbl["label_danger"]  = pd.to_numeric(lbl["label_danger"],  errors="coerce")
lbl["label_warning"] = pd.to_numeric(lbl["label_warning"], errors="coerce")
lbl["zone_slug"]     = lbl["station"].map(ZONE_MAP)
lbl["year"]          = lbl["date"].dt.year
print(f"\n  Labels: {len(lbl):,} rows  columns={list(lbl.columns)}")
for st in ["KALLOOPPARA","KIDANGOOR"]:
    s = lbl[lbl["station"]==st]
    nd  = int((s["label_danger"] ==1).sum())
    nw  = int((s["label_warning"]==1).sum())
    nan = int(s["label_danger"].isna().sum())
    print(f"    {st}: {len(s):,} rows  {s['date'].min().date()} to {s['date'].max().date()}  >=DL={nd}  >=WL={nw}  NaN={nan}")

# --- load weather ---
wframes = []
for zs in ZONE_MAP.values():
    fp = HIST_DIR / f"{zs}.csv"
    if not fp.exists():
        print(f"\n  WEATHER MISSING: {fp}  -- run fetch_data.py first"); sys.exit(1)
    wdf = pd.read_csv(fp, parse_dates=["date"])
    wframes.append(wdf)
    print(f"  Weather {zs}: {len(wdf):,} rows  {wdf['date'].min().date()} to {wdf['date'].max().date()}")

weather = pd.concat(wframes, ignore_index=True)
print(f"\n  Weather combined: {len(weather):,} rows")

# --- inner join on date + zone_slug ---
joined = lbl.merge(weather, on=["date","zone_slug"], how="inner")
print(f"\n  After inner join on (date, zone_slug): {len(joined):,} rows")
print(f"  Date range: {joined['date'].min().date()} to {joined['date'].max().date()}")
print(f"  Label rows without weather match : {len(lbl)     - len(joined)}")
print(f"  Weather rows without label match : {len(weather) - len(joined)}")

# duplicates
dup = joined.duplicated(subset=["station","date"]).sum()
print(f"  Duplicate (station, date) pairs  : {dup}")

# --- missing values per column ---
print(f"\n  Missing values per column (all {len(joined):,} joined rows):")
all_cols = ["daily_max","n_readings","label_danger","label_warning"] + WEATHER_VARS
for col in all_cols:
    if col not in joined.columns: print(f"    {col:<30}  COLUMN ABSENT"); continue
    nc  = joined[col].isna().sum()
    pct = 100*nc/len(joined) if joined.shape[0]>0 else 0
    print(f"    {col:<30}  {nc:>6} null  ({pct:.1f}%)")

# --- drop NaN labels and NaN weather ---
drop_cols = ["label_danger","label_warning"] + WEATHER_VARS
clean = joined.dropna(subset=drop_cols)
clean = clean.copy()
clean["year"] = clean["date"].dt.year
dropped = len(joined) - len(clean)
print(f"\n  After dropping rows with NaN label or NaN weather: {len(clean):,} rows  (dropped {dropped:,})")

# --- positives per zone per year ---
print(); print(THIN)
print("  Positives per zone per year (label=1 days, post-drop):")
print(f"  {'Station':<20}  {'Year':>5}  {'days':>6}  {'>=DL':>6}  {'>=WL':>6}  {'ev_DL':>7}  {'ev_WL':>7}")
for st in ["KALLOOPPARA","KIDANGOOR"]:
    s = clean[clean["station"]==st].sort_values("date")
    for yr, grp in s.groupby("year"):
        g  = grp.sort_values("date")
        nd = int((g["label_danger"] ==1).sum())
        nw = int((g["label_warning"]==1).sum())
        cd = count_clusters(g["label_danger"].tolist())
        cw = count_clusters(g["label_warning"].tolist())
        if nd>0 or nw>0:
            print(f"  {st:<20}  {int(yr):>5}  {len(g):>6}  {nd:>6}  {nw:>6}  {cd:>7}  {cw:>7}")

# --- per-zone totals ---
print(); print(THIN)
print("  Per-zone totals (post-drop):")
print(f"  {'Station':<20}  {'rows':>7}  {'>=DL':>6}  {'>=WL':>6}  {'ev_DL':>7}  {'ev_WL':>7}")
for st in ["KALLOOPPARA","KIDANGOOR"]:
    s  = clean[clean["station"]==st].sort_values("date")
    nd = int((s["label_danger"] ==1).sum())
    nw = int((s["label_warning"]==1).sum())
    cd = count_clusters(s["label_danger"].tolist())
    cw = count_clusters(s["label_warning"].tolist())
    print(f"  {st:<20}  {len(s):>7}  {nd:>6}  {nw:>6}  {cd:>7}  {cw:>7}")
td = int((clean["label_danger"] ==1).sum())
tw = int((clean["label_warning"]==1).sum())
print(f"  {'TOTAL':<20}  {len(clean):>7}  {td:>6}  {tw:>6}")
for lname,cnt in [("danger",td),("warning",tw)]:
    print(f"  [{'OK' if cnt>=100 else 'MISS'}] Total {lname}={cnt} (threshold 100)")

# --- year x zone coverage summary ---
print(); print(THIN)
print("  Row counts per zone per year (post-drop, all years):")
print(f"  {'Year':>5}  {'KALLOOPPARA':>14}  {'KIDANGOOR':>12}  {'total':>7}")
all_years = sorted(clean["year"].unique())
for yr in all_years:
    row_kp = len(clean[(clean["station"]=="KALLOOPPARA")&(clean["year"]==yr)])
    row_ki = len(clean[(clean["station"]=="KIDANGOOR")&(clean["year"]==yr)])
    print(f"  {int(yr):>5}  {row_kp:>14}  {row_ki:>12}  {row_kp+row_ki:>7}")

print(); print(SEP); print("STEP 1 COMPLETE -- stopped, awaiting approval"); print(SEP)

