import math, pathlib
from datetime import date
import pandas as pd
import numpy as np

SEP  = "=" * 72
THIN = "-" * 72
BASE        = pathlib.Path("data/raw/labels/cwc")
V3          = BASE / "v3"
LEVELS_FILE = BASE / "danger_levels_manual.csv"
PROCESSED   = pathlib.Path("data/processed")
DOCS        = pathlib.Path("docs")
PROCESSED.mkdir(parents=True, exist_ok=True)
DOCS.mkdir(parents=True, exist_ok=True)
LABEL_OUT  = PROCESSED / "labels_daily.csv"
REPORT_OUT = DOCS / "label-sourcing-report.md"

STATION_FILE = {
    "KALLOOPPARA": V3 / "station_017-SWRDKOCHI_kallooppara.csv",
    "KIDANGOOR":   V3 / "station_015-SWRDKOCHI_kidangoor.csv",
}

def load_station(fp):
    df = pd.read_csv(fp, low_memory=False)
    col = {c.lower(): c for c in df.columns}
    dt_c  = col.get("datatime",     list(col.values())[0])
    dty_c = col.get("datatypecode", "datatypeCode")
    val_c = col.get("datavalue",    "dataValue")
    df = df.rename(columns={dt_c:"dataTime", dty_c:"datatypeCode", val_c:"dataValue"})
    df["dataTime"]  = pd.to_datetime(df["dataTime"],  errors="coerce")
    df["dataValue"] = pd.to_numeric(df["dataValue"],  errors="coerce")
    df["_date"]     = df["dataTime"].dt.date
    return df

def count_clusters(vals):
    n, in_c = 0, False
    for v in vals:
        if v == 1:
            if not in_c: n += 1; in_c = True
        else: in_c = False
    return n

# ============================================================
# TASK 1: Update KALLOOPPARA datum
# ============================================================
print(SEP); print("TASK 1 -- UPDATE danger_levels_manual.csv"); print(SEP)
ldf = pd.read_csv(LEVELS_FILE)
mask_kp = ldf["station"].str.strip() == "KALLOOPPARA"
ldf.loc[mask_kp, "datum"] = "HHS series (HZS=HHS, offset 0.00; matches HFL 9.64 on 2018-08-16)"
ldf.to_csv(LEVELS_FILE, index=False)
print("  Updated. Current file:")
print(ldf.to_string(index=False))

levels, hfl_dates = {}, {}
for _, r in ldf.iterrows():
    st = str(r["station"]).strip(); lt = str(r["level_type"]).strip()
    v  = float(r["value"]) if pd.notna(r["value"]) else None
    hd = str(r.get("hfl_date","")).strip()
    if hd in ("","nan"): hd = None
    levels.setdefault(st,{})[lt] = v
    if hd: hfl_dates[st] = hd
approved_series = {"KALLOOPPARA":"HHS","KIDANGOOR":"HHS"}

# ============================================================
# TASK 2: Monthly-regime label rebuild
# ============================================================
print(); print(SEP); print("TASK 2 -- MONTHLY-REGIME LABEL REBUILD"); print(SEP)

prev_lbl = pd.read_csv(LABEL_OUT) if LABEL_OUT.exists() else None
if prev_lbl is not None:
    prev_lbl["label_danger"]  = pd.to_numeric(prev_lbl["label_danger"],  errors="coerce")
    prev_lbl["label_warning"] = pd.to_numeric(prev_lbl["label_warning"], errors="coerce")
    prev_lbl["year"]  = pd.to_datetime(prev_lbl["date"]).dt.year
    prev_lbl["month"] = pd.to_datetime(prev_lbl["date"]).dt.month

label_rows = []
regime_maps = {}

for station in ["KALLOOPPARA","KIDANGOOR"]:
    dtype   = approved_series[station]
    d_level = levels[station]["danger"]
    w_level = levels[station]["warning"]
    print(f"\n  {station} ({dtype})  danger={d_level}  warning={w_level}")

    df  = load_station(STATION_FILE[station])
    sub = df[df["datatypeCode"]==dtype].dropna(subset=["dataValue"]).copy()
    sub["_ym"] = sub["dataTime"].dt.to_period("M")

    # per-month median daily reading count -> regime
    dc = sub.groupby(["_ym","_date"]).size().reset_index(name="n")
    monthly_med = dc.groupby("_ym")["n"].median()
    regime_map  = {}
    for ym, med in monthly_med.items():
        N      = 12 if med >= 12 else 3
        regime = "hourly" if med >= 12 else "3perday"
        regime_map[str(ym)] = (N, regime, round(med,1))
    regime_maps[station] = regime_map

    hourly_ct  = sum(1 for v in regime_map.values() if v[1]=="hourly")
    threeday_ct= sum(1 for v in regime_map.values() if v[1]=="3perday")
    print(f"    Hourly months (N=12): {hourly_ct}   3perday months (N=3): {threeday_ct}")

    # build daily labels
    daily = sub.groupby("_date")["dataValue"].agg(daily_max="max",n_readings="count").reset_index()

    for _, row in daily.iterrows():
        dt   = row["_date"]
        dmax = row["daily_max"]
        n    = int(row["n_readings"])
        ym   = str(pd.Period(dt,"M"))
        N, regime, _ = regime_map.get(ym, (3,"3perday",3))

        def lbl(level, dmax=dmax, n=n, N=N):
            if pd.isna(dmax): return float("nan")
            if dmax >= level: return 1
            return float("nan") if n < N else 0

        label_rows.append({
            "station":       station,
            "series":        dtype,
            "date":          str(dt),
            "daily_max":     round(float(dmax),4),
            "n_readings":    n,
            "regime":        regime,
            "label_danger":  lbl(d_level),
            "label_warning": lbl(w_level),
        })

lbl_df = pd.DataFrame(label_rows)
lbl_df.to_csv(LABEL_OUT, index=False)
print(f"\n  Saved {len(lbl_df)} rows -> {LABEL_OUT}")
lbl_df["label_danger"]  = pd.to_numeric(lbl_df["label_danger"],  errors="coerce")
lbl_df["label_warning"] = pd.to_numeric(lbl_df["label_warning"], errors="coerce")
lbl_df["year"]  = pd.to_datetime(lbl_df["date"]).dt.year
lbl_df["month"] = pd.to_datetime(lbl_df["date"]).dt.month

# Per-year before vs after NaN + positives
print(); print(THIN)
print("  NaN per year: BEFORE (year-cutoff) vs AFTER (monthly-regime) + positives:")
for station in ["KALLOOPPARA","KIDANGOOR"]:
    s_new = lbl_df[lbl_df["station"]==station]
    print(f"\n  {station}:")
    print(f"  {'Year':>6}  {'NaN_bef':>9}  {'NaN_aft':>9}  {'delta':>7}  {'>=DL':>6}  {'>=WL':>6}  {'ev_DL':>7}  {'ev_WL':>7}")
    if prev_lbl is not None:
        s_old = prev_lbl[prev_lbl["station"]==station]
    all_years = sorted(s_new["year"].dropna().unique())
    for yr in all_years:
        g_new  = s_new[s_new["year"]==yr].sort_values("date")
        nn_new = int(g_new["label_danger"].isna().sum())
        nd     = int((g_new["label_danger"] ==1).sum())
        nw     = int((g_new["label_warning"]==1).sum())
        cd     = count_clusters(g_new["label_danger"].tolist())
        cw     = count_clusters(g_new["label_warning"].tolist())
        if prev_lbl is not None:
            g_old  = s_old[s_old["year"]==yr] if len(s_old)>0 else pd.DataFrame()
            nn_old = int(g_old["label_danger"].isna().sum()) if not g_old.empty else 0
        else:
            nn_old = "-"
        delta = (nn_new - nn_old) if isinstance(nn_old,int) else "-"
        print(f"  {int(yr):>6}  {str(nn_old):>9}  {nn_new:>9}  {str(delta):>7}  {nd:>6}  {nw:>6}  {cd:>7}  {cw:>7}")

# Jun-Oct NaN
print(); print(THIN); print("  Jun-Oct NaN before vs after:")
print(f"  {'Station':<16}  {'NaN_bef':>9}  {'NaN_aft':>9}  {'delta':>7}")
for station in ["KALLOOPPARA","KIDANGOOR"]:
    s_new  = lbl_df[(lbl_df["station"]==station)&(lbl_df["month"].between(6,10))]
    nn_new = int(s_new["label_danger"].isna().sum())
    if prev_lbl is not None:
        s_old  = prev_lbl[(prev_lbl["station"]==station)&(prev_lbl["month"].between(6,10))]
        nn_old = int(s_old["label_danger"].isna().sum())
        delta  = nn_new - nn_old
    else:
        nn_old, delta = "-", "-"
    print(f"  {station:<16}  {str(nn_old):>9}  {nn_new:>9}  {str(delta):>7}")

# Totals
total_d=int((lbl_df["label_danger"]==1).sum())
total_w=int((lbl_df["label_warning"]==1).sum())
total_n=int(lbl_df["label_danger"].isna().sum())
print(); print(THIN)
print(f"  TOTALS: rows={len(lbl_df)}  >=danger={total_d}  >=warning={total_w}  NaN={total_n}")
for lname,cnt in [("danger",total_d),("warning",total_w)]:
    print(f"  [{'OK' if cnt>=100 else 'MISS'}] Total {lname}={cnt} (threshold 100)")
for station in ["KALLOOPPARA","KIDANGOOR"]:
    s=lbl_df[lbl_df["station"]==station]
    for lname,cnt in [("danger",int((s["label_danger"]==1).sum())),
                      ("warning",int((s["label_warning"]==1).sum()))]:
        print(f"  [{'OK' if cnt>=10 else 'MISS'}] {station} {lname}={cnt}")

# ============================================================
# TASKS 3+4: Rewrite report
# ============================================================
print(); print(SEP); print("TASKS 3+4 -- REWRITING label-sourcing-report.md"); print(SEP)
rc={}
for station in ["KALLOOPPARA","KIDANGOOR"]:
    s=lbl_df[lbl_df["station"]==station]
    rc[station]=dict(dtype=approved_series[station],danger=levels[station]["danger"],
        warning=levels[station]["warning"],hfl=levels[station]["HFL"],
        hfl_date=hfl_dates[station],n_rows=len(s),
        n_danger=int((s["label_danger"]==1).sum()),n_warning=int((s["label_warning"]==1).sum()),
        n_nan=int(s["label_danger"].isna().sum()),n_labeled=int(s["label_danger"].notna().sum()))
kp=rc["KALLOOPPARA"]; ki=rc["KIDANGOOR"]
md  = "# Phase 2 Label Sourcing Report\n"
md += f"Generated: {date.today().isoformat()}\n\n"
md += "## 1. Source PDFs\n\n| PDF | Bulletin Date | Stations Found |\n|:---|:---|:---|\n"
md += "| cfcrcwcdfb17-10-2021-2.pdf | 2021-10-17 | KALLOOPPARA p.3 Severe Flood, KIDANGOOR p.4 Above Normal |\n"
md += "| cfcrcwcdfb15-11-2021-2.pdf | 2021-11-15 | KALLOOPPARA p.4 Above Normal |\n"
md += "| cfcrcwcdfb19-10-2021_2.pdf | 2021-10-19 | KALLOOPPARA p.4 Above Normal |\n\n"
md += "## 2. Official Levels (danger_levels_manual.csv)\n\n"
md += "| Station | Zone | Danger (m) | Warning (m) | HFL (m) | HFL Date | Datum |\n"
md += "|:---|:---|:---|:---|:---|:---|:---|\n"
md += f"| KALLOOPPARA | Pathanamthitta | {kp['danger']} | {kp['warning']} | {kp['hfl']} | {kp['hfl_date']} | HHS series (HZS=HHS, offset 0.00; matches HFL 9.64 on 2018-08-16) |\n"
md += f"| KIDANGOOR   | Kottayam       | {ki['danger']} | {ki['warning']} | {ki['hfl']} | {ki['hfl_date']} | HHS series (matches HFL 8.24 on 2020-08-09) |\n\n"
md += "> Provisional: levels from CWC Daily Flood Bulletin table columns. Not cross-referenced with CWC Level Forecast Sites register.\n\n"
md += "## 3. Datum Check\n\n"
md += "| Station | Series | HFL (bulletin) | HFL Date | HZS max | HHS max |\n|:---|:---|:---|:---|:---|:---|\n"
md += f"| KALLOOPPARA | HHS | {kp['hfl']} | {kp['hfl_date']} | 9.6400 (offset 0.00) | 9.6400 |\n"
md += f"| KIDANGOOR   | HHS | {ki['hfl']} | {ki['hfl_date']} | 9.4400 (diff 1.20, no match) | 8.2400 |\n\n"
md += "## 4. ARANGALI Aug 17-19 2018\n\n"
md += "API re-verification failed (HTTP 400 for Ernakulam and Thrissur); gap confirmed from v3 data (Aug 17/18/19 show no rows in downloaded dataset); no official level, so unlabeled.\n\n"
md += "## 5. Labels -- data/processed/labels_daily.csv\n\n"
md += "**NaN rule (monthly regime):** per station-month, compute median daily reading count.\n"
md += "If median >= 12: N=12 (hourly). Else N=3 (3perday).\n"
md += "label=1 if daily_max>=level; label=0 if below and n_readings>=N; label=NaN otherwise.\n"
md += "No interpolation, no forward-fill. Missing readings -> NaN -> dropped.\n\n"
md += "| Station | Zone | Series | Danger | Warning | Total days | Labeled | NaN | >=Danger | >=Warning |\n"
md += "|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|\n"
md += f"| KALLOOPPARA | Pathanamthitta | {kp['dtype']} | {kp['danger']} | {kp['warning']} | {kp['n_rows']} | {kp['n_labeled']} | {kp['n_nan']} | {kp['n_danger']} | {kp['n_warning']} |\n"
md += f"| KIDANGOOR   | Kottayam       | {ki['dtype']} | {ki['danger']} | {ki['warning']} | {ki['n_rows']} | {ki['n_labeled']} | {ki['n_nan']} | {ki['n_danger']} | {ki['n_warning']} |\n\n"
md += "## 6. Zones Without Official Levels\n\n"
md += "| Station | Code | District | Coverage |\n|:---|:---|:---|:---|\n"
md += "| VANDIPERIYAR | 016-SWRDKOCHI | Idukki     | HHS+HZS 2000- |\n"
md += "| KALAMPUR     | 013-SWRDKOCHI | Ernakulam  | HHS+HZS 2015- |\n"
md += "| ARANGALI     | 011-SWRDKOCHI | Thrissur   | HZS 2015- |\n"
md += "| KUMBIDI      | 008-SWRDKOCHI | Palakkad   | HZS 2009- |\n"
md += "| KARATHODU    | 006-SWRDKOCHI | Malappuram | HZS 2009- |\n\n"
md += "Zones in src/ingest/zones.py with no valid gauge: Idukki, Wayanad (excluded), Ernakulam, Thrissur, Alappuzha.\n\n"
md += "## 7. Known Gaps\n\n| Gap | Detail |\n|:---|:---|\n"
md += "| Download end | v3 ends 2024-12-31 |\n"
md += "| Pre-2015 obs schedule | 3 obs/day; NaN rule uses monthly regime |\n"
md += f"| NaN days | KALLOOPPARA {kp['n_nan']}, KIDANGOOR {ki['n_nan']} |\n"
md += "| Datum provisional | Not cross-referenced with CWC Level Forecast Sites register |\n"
md += f"| Total danger days | {total_d} ({'MET' if total_d>=100 else 'MISS by '+str(100-total_d)}) |\n"
md += "| 5 of 7 stations unlabeled | No confirmed official level |\n"
REPORT_OUT.write_text(md, encoding="utf-8")
print(f"  Written: {REPORT_OUT}")

# ============================================================
# WEATHER DISCOVERY (for tasks 5-6)
# ============================================================
print(); print(SEP); print("WEATHER DISCOVERY (for tasks 5-6)"); print(SEP)
import os, glob as globlib

# Find weather data directories
for wdir in ["data/weather","data/raw/weather","data/processed/weather",
             "data/interim","data/external"]:
    p=pathlib.Path(wdir)
    if p.exists():
        files=sorted(p.rglob("*"))[:40]
        print(f"\n  DIR EXISTS: {wdir}/")
        for f in files:
            if f.is_file():
                print(f"    {str(f.relative_to(p)):50s}  {f.stat().st_size:>12,} bytes")
    else:
        print(f"  not found: {wdir}")

# Find zones.py
for zpath in ["src/ingest/zones.py","src/zones.py","scripts/zones.py","src/ingest/stations.py"]:
    p=pathlib.Path(zpath)
    if p.exists():
        print(f"\n  {zpath}:")
        print(p.read_text(encoding="utf-8")[:4000])

# Find weather ingest scripts
for idir in ["src/ingest","src","scripts"]:
    p=pathlib.Path(idir)
    if p.exists():
        py_files=[f for f in sorted(p.glob("*.py")) if any(k in f.name.lower()
            for k in ["weather","ingest","download","fetch","open_meteo","openmeteo","era5"])]
        if py_files:
            print(f"\n  Weather-related scripts in {idir}/:")
            for f in py_files:
                print(f"    {f.name}")
                print(pathlib.Path(f).read_text(encoding="utf-8")[:1000])
                print("    ...")

# Show first/last dates in any weather CSV found
print("\n  Checking date ranges in weather CSVs:")
for csv_path in sorted(pathlib.Path(".").rglob("*.csv"))[:200]:
    if any(k in str(csv_path).lower() for k in ["weather","meteo","era5","rain","temp","climate"]):
        try:
            df=pd.read_csv(csv_path,nrows=5)
            last_df=pd.read_csv(csv_path).tail(3)
            print(f"  {csv_path}  cols={list(df.columns)[:6]}  first={list(df.iloc[0])[:3]}  last={list(last_df.iloc[-1])[:3]}")
        except Exception as e:
            print(f"  {csv_path}  ERROR: {e}")

print(); print(SEP); print("DONE -- paste full output for review"); print(SEP)

