import json, math, pathlib, sys, time
from datetime import date, timedelta
import pandas as pd
import numpy as np
import requests

SEP  = "=" * 72
THIN = "-" * 72
BASE        = pathlib.Path("data/raw/labels/cwc")
V3          = BASE / "v3"
CHUNKS_DIR  = BASE / "v2/chunks"
LEVELS_FILE = BASE / "danger_levels_manual.csv"
PROCESSED   = pathlib.Path("data/processed")
DOCS        = pathlib.Path("docs")
PROCESSED.mkdir(parents=True, exist_ok=True)
DOCS.mkdir(parents=True, exist_ok=True)
LABEL_OUT  = PROCESSED / "labels_daily.csv"
REPORT_OUT = DOCS / "label-sourcing-report.md"
API_URL = "https://indiawris.gov.in/Dataset/River Water Level"
STATION_FILE = {
    "KALLOOPPARA":  V3 / "station_017-SWRDKOCHI_kallooppara.csv",
    "KIDANGOOR":    V3 / "station_015-SWRDKOCHI_kidangoor.csv",
    "VANDIPERIYAR": V3 / "station_016-SWRDKOCHI_vandiperiyar.csv",
    "KALAMPUR":     V3 / "station_013-SWRDKOCHI_kalampur.csv",
    "ARANGALI":     V3 / "station_011-SWRDKOCHI_arangali.csv",
    "KUMBIDI":      V3 / "station_008-SWRDKOCHI_kumbidi.csv",
    "KARATHODU":    V3 / "station_006-SWRDKOCHI_karathodu.csv",
}

def load_station(fp):
    df = pd.read_csv(fp, low_memory=False)
    col = {c.lower(): c for c in df.columns}
    dt_c  = col.get("datatime",     col.get("data_time",  list(col.values())[0]))
    dty_c = col.get("datatypecode", col.get("datatype",   "datatypeCode"))
    val_c = col.get("datavalue",    col.get("value",      "dataValue"))
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

def min_n(d):
    return 3 if d.year < 2015 else 12

# --- load levels ---
print(SEP); print("LOADING danger_levels_manual.csv"); print(SEP)
ldf = pd.read_csv(LEVELS_FILE)
print(ldf.to_string(index=False)); print()
levels, hfl_dates = {}, {}
for _, r in ldf.iterrows():
    st = str(r["station"]).strip(); lt = str(r["level_type"]).strip()
    v  = float(r["value"]) if pd.notna(r["value"]) else None
    hd = str(r.get("hfl_date","")).strip()
    if hd in ("","nan"): hd = None
    levels.setdefault(st, {})[lt] = v
    if hd: hfl_dates[st] = hd

# ============================================================
# TASK 1: DATUM CHECK
# ============================================================
print(SEP); print("TASK 1 — DATUM CHECK"); print(SEP)
approved_series = {}
for station in ["KALLOOPPARA", "KIDANGOOR"]:
    hfl_val  = levels[station]["HFL"]
    hfl_date = hfl_dates[station]
    target   = pd.to_datetime(hfl_date).date()
    print(f"\n{THIN}\nStation: {station}   HFL={hfl_val} m   date={hfl_date}\n{THIN}")
    df = load_station(STATION_FILE[station])
    day_df = df[df["_date"] == target]
    print(f"  Rows on {hfl_date}: {len(day_df)}")
    if len(day_df) == 0:
        avail = sorted(df["_date"].dropna().unique())
        near = [str(d) for d in avail if str(d)[:7] == hfl_date[:7]]
        print(f"  Dates in that month: {near[:20]}")
    matched = False
    for dtype in ["HZS","HHS"]:
        sub = day_df[day_df["datatypeCode"]==dtype]
        if sub.empty: print(f"  {dtype}: 0 readings on {hfl_date}"); continue
        dmax = sub["dataValue"].max()
        diff = abs(dmax - hfl_val)
        hit  = diff <= 0.5
        print(f"  {dtype}: n={len(sub):4d}  daily_max={dmax:.4f}  |{hfl_val}-max|={diff:.4f}  {'MATCH' if hit else 'no match'}")
        if hit and not matched: approved_series[station] = dtype; matched = True
    if not matched:
        print(f"\n  STOP: Neither series within 0.5 m of HFL={hfl_val} for {station}. Exiting.")
        sys.exit(1)
    print(f"  -> Approved: {approved_series[station]}")
print(f"\nApproved series: {approved_series}")
print("Datum check PASSED.\n")

# ============================================================
# TASK 2: ARANGALI Aug 17-19 2018
# ============================================================
print(SEP); print("TASK 2 — ARANGALI Aug 17-19 2018 (serial, 3s delay)"); print(SEP)
ARANGALI_CODE = "011-SWRDKOCHI"
district = None
for cp in sorted(list(CHUNKS_DIR.glob(f"chunk_{ARANGALI_CODE}_2018-08_p*.json")) +
                 list(CHUNKS_DIR.glob(f"chunk_{ARANGALI_CODE}_2015-*.json"))[:5]):
    try:
        raw = json.loads(cp.read_text(encoding="utf-8"))
        body = raw if isinstance(raw,list) else raw.get("data", raw.get("result", raw.get("content",[])))
        if body and isinstance(body,list) and body[0].get("districtName"):
            district = str(body[0]["districtName"]).strip(); break
    except Exception: pass
if not district: district = "Ernakulam"
print(f"  District: {district!r}")

def api_day(dist, code, day_str):
    time.sleep(3)
    payload = {"stateName":"Kerala","districtName":dist,"agencyName":"CWC","stationCode":code,
                "startdate":f"{day_str}T00:00:00","enddate":f"{day_str}T23:59:59","page":0,"size":1000}
    try:
        r = requests.post(API_URL, json=payload, timeout=30)
        raw = r.json()
        body = raw if isinstance(raw,list) else raw.get("data",raw.get("result",raw.get("content",[])))
        if not isinstance(body,list): body = []
        st_rows = [x for x in body if str(x.get("stationCode","")).strip()==code]
        return {"date":day_str,"http":r.status_code,"district_rows":len(body),"station_rows":len(st_rows)}
    except Exception as e:
        return {"date":day_str,"http":"ERR","district_rows":0,"station_rows":0,"error":str(e)}

arangali_results = []
for d in ["2018-08-17","2018-08-18","2018-08-19"]:
    print(f"  Querying {d} ...", end=" ", flush=True)
    res = api_day(district, ARANGALI_CODE, d); arangali_results.append(res)
    err = f"  error={res.get('error','')}" if "error" in res else ""
    print(f"HTTP {res['http']}  district_rows={res['district_rows']}  station_rows={res['station_rows']}{err}")
print()
print(f"  {'Date':<12}  {'HTTP':>5}  {'Dist rows':>10}  {'Stn rows':>10}")
for r in arangali_results:
    print(f"  {r['date']:<12}  {str(r['http']):>5}  {r['district_rows']:>10}  {r['station_rows']:>10}")

# ============================================================
# TASK 3: LABELS
# ============================================================
print(f"\n{SEP}"); print("TASK 3 — LABEL GENERATION"); print(SEP)
label_rows = []
for station in ["KALLOOPPARA","KIDANGOOR"]:
    dtype   = approved_series[station]
    d_level = levels[station]["danger"]
    w_level = levels[station]["warning"]
    print(f"\n  {station}: series={dtype}  danger={d_level}  warning={w_level}")
    df  = load_station(STATION_FILE[station])
    sub = df[df["datatypeCode"]==dtype].dropna(subset=["dataValue"]).copy()
    daily = sub.groupby("_date")["dataValue"].agg(daily_max="max",n_readings="count").reset_index()
    for _, row in daily.iterrows():
        dt=row["_date"]; dmax=row["daily_max"]; n=int(row["n_readings"]); mn=min_n(dt)
        def lbl(level,dmax=dmax,n=n,mn=mn):
            if pd.isna(dmax): return float("nan")
            if dmax>=level: return 1
            return float("nan") if n<mn else 0
        label_rows.append({"station":station,"series":dtype,"date":str(dt),
                           "daily_max":round(float(dmax),4),"n_readings":n,
                           "label_danger":lbl(d_level),"label_warning":lbl(w_level)})
    st_r = [r for r in label_rows if r["station"]==station]
    nd=sum(1 for r in st_r if r["label_danger"]==1)
    nw=sum(1 for r in st_r if r["label_warning"]==1)
    nn=sum(1 for r in st_r if math.isnan(r["label_danger"]))
    print(f"    Total days={len(st_r)}  labeled={len(st_r)-nn}  NaN={nn}  >=danger={nd}  >=warning={nw}")
lbl_df = pd.DataFrame(label_rows)
lbl_df.to_csv(LABEL_OUT, index=False)
print(f"\n  Saved {len(lbl_df)} rows -> {LABEL_OUT}")

# ============================================================
# TASK 4: COUNTS PER STATION-YEAR + AUG 14-20 2018
# ============================================================
print(f"\n{SEP}"); print("TASK 4 — COUNTS PER STATION-YEAR + Aug 14-20 2018"); print(SEP)
lbl_df["label_danger"]  = pd.to_numeric(lbl_df["label_danger"],  errors="coerce")
lbl_df["label_warning"] = pd.to_numeric(lbl_df["label_warning"], errors="coerce")
lbl_df["year"] = pd.to_datetime(lbl_df["date"]).dt.year
for station in ["KALLOOPPARA","KIDANGOOR"]:
    sdf = lbl_df[lbl_df["station"]==station].sort_values("date")
    print(f"\n  {station} ({approved_series[station]}):")
    print(f"  {'Year':>6}  {'>=DL':>6}  {'>=WL':>6}  {'NaN':>6}  {'clust_DL':>10}  {'clust_WL':>10}")
    for yr,grp in sdf.groupby("year"):
        g=grp.sort_values("date")
        nd=int((g["label_danger"]==1).sum()); nw=int((g["label_warning"]==1).sum())
        nn=int(g["label_danger"].isna().sum())
        cd=count_clusters(g["label_danger"].tolist()); cw=count_clusters(g["label_warning"].tolist())
        print(f"  {yr:>6}  {nd:>6}  {nw:>6}  {nn:>6}  {cd:>10}  {cw:>10}")
aug_days=[(date(2018,8,14)+timedelta(i)) for i in range(7)]; aug_strs=[str(d) for d in aug_days]
print(f"\n{THIN}\n  Aug 14-20 2018 daily max (all 7 stations):")
print("  " + f"{'Station':<16} {'Ser':<5}  " + "  ".join(d.strftime("%b%d") for d in aug_days))
for sname,fp in STATION_FILE.items():
    if not fp.exists(): print(f"  {sname:<16} FILE MISSING"); continue
    df=load_station(fp)
    for dtype in ["HZS","HHS"]:
        sub=df[df["datatypeCode"]==dtype]
        if sub.empty: continue
        vals=[]
        for ds in aug_strs:
            dm=sub[sub["_date"].astype(str)==ds]["dataValue"]
            vals.append(f"{dm.max():7.2f}" if not dm.empty else "    ---")
        print(f"  {sname:<16} {dtype:<5}  "+"  ".join(vals))

# ============================================================
# TASK 5: TOTALS vs THRESHOLDS
# ============================================================
print(f"\n{SEP}"); print("TASK 5 — TOTALS vs THRESHOLDS"); print(SEP)
total_d=int((lbl_df["label_danger"]==1).sum())
total_w=int((lbl_df["label_warning"]==1).sum())
total_n=int(lbl_df["label_danger"].isna().sum())
print(f"  Rows in labels_daily.csv : {len(lbl_df)}")
print(f"  Days >= danger  (all)    : {total_d}")
print(f"  Days >= warning (all)    : {total_w}")
print(f"  NaN days                 : {total_n}\n")
for station in ["KALLOOPPARA","KIDANGOOR"]:
    s=lbl_df[lbl_df["station"]==station]
    nd=int((s["label_danger"]==1).sum()); nw=int((s["label_warning"]==1).sum())
    print(f"  {station:<16}  danger={nd:4d}  warning={nw:4d}")
print()
for lname,cnt in [("danger",total_d),("warning",total_w)]:
    sym="OK" if cnt>=100 else "MISS"
    print(f"  [{sym}] Total {lname} days = {cnt} (threshold 100)")
for station in ["KALLOOPPARA","KIDANGOOR"]:
    s=lbl_df[lbl_df["station"]==station]
    nd=int((s["label_danger"]==1).sum()); nw=int((s["label_warning"]==1).sum())
    for lname,cnt in [("danger",nd),("warning",nw)]:
        sym="OK" if cnt>=10 else "MISS"
        print(f"  [{sym}] {station} {lname} = {cnt} (threshold 10)")

# ============================================================
# TASK 6: ZONES WITHOUT OFFICIAL LEVELS
# ============================================================
print(f"\n{SEP}"); print("TASK 6 — ZONES WITHOUT OFFICIAL LEVELS"); print(SEP)
NO_LEVEL=[("VANDIPERIYAR","016","Idukki","HHS+HZS 2000-"),
          ("KALAMPUR","013","Pathanamthitta","HHS+HZS 2015-"),
          ("ARANGALI","011","Ernakulam","HZS 2015-"),
          ("KUMBIDI","008","Alappuzha","HZS 2009-"),
          ("KARATHODU","006","Alappuzha","HZS 2009-")]
print(f"  {'Station':<16}{'Code':<6}{'District':<18}{'Coverage'}")
for st,cd,ds,cv in NO_LEVEL: print(f"  {st:<16}{cd:<6}{ds:<18}{cv}")
print("\n  No official level -> no labels, no proxies, no percentile thresholds.")
print("  Gauge-less zones also excluded: Wayanad, Thrissur, Ernakulam (non-Arangali),")
print("  Alappuzha/Kuttanad. Awaiting your decision.\n")

# ============================================================
# TASK 7: WRITE REPORT
# ============================================================
print(SEP); print("TASK 7 — WRITING docs/label-sourcing-report.md"); print(SEP)
rc={}
for station in ["KALLOOPPARA","KIDANGOOR"]:
    s=lbl_df[lbl_df["station"]==station]
    rc[station]=dict(dtype=approved_series[station],danger=levels[station]["danger"],
        warning=levels[station]["warning"],hfl=levels[station]["HFL"],hfl_date=hfl_dates[station],
        n_rows=len(s),n_danger=int((s["label_danger"]==1).sum()),
        n_warning=int((s["label_warning"]==1).sum()),
        n_nan=int(s["label_danger"].isna().sum()),n_labeled=int(s["label_danger"].notna().sum()))
ar_tbl="\n".join(f"| {r['date']} | {r['http']} | {r['district_rows']} | {r['station_rows']} |" for r in arangali_results)
md=f"""# Phase 2 Label Sourcing Report\nGenerated: {date.today().isoformat()}\n
## 1. Source PDFs\n| PDF | Date | Stations |\n|:---|:---|:---|\n| cfcrcwcdfb17-10-2021-2.pdf | 2021-10-17 | KALLOOPPARA p.3 Severe Flood, KIDANGOOR p.4 Above Normal |\n| cfcrcwcdfb15-11-2021-2.pdf | 2021-11-15 | KALLOOPPARA p.4 Above Normal |\n| cfcrcwcdfb19-10-2021_2.pdf | 2021-10-19 | KALLOOPPARA p.4 Above Normal |\n
## 2. Official Levels\n| Station | Danger | Warning | HFL | HFL Date | Datum |\n|:---|:---|:---|:---|:---|:---|\n| KALLOOPPARA | {rc['KALLOOPPARA']['danger']} | {rc['KALLOOPPARA']['warning']} | {rc['KALLOOPPARA']['hfl']} | {rc['KALLOOPPARA']['hfl_date']} | HZS_gauge (provisional) |\n| KIDANGOOR | {rc['KIDANGOOR']['danger']} | {rc['KIDANGOOR']['warning']} | {rc['KIDANGOOR']['hfl']} | {rc['KIDANGOOR']['hfl_date']} | HZS_gauge (provisional) |\n\n> Provisional: levels from CWC bulletin table columns. Datum assumed HZS from value range. Not yet cross-referenced with CWC Level Forecast Sites register.\n
## 3. Datum Check\n| Station | Approved Series | HFL | HFL Date |\n|:---|:---|:---|:---|\n| KALLOOPPARA | {rc['KALLOOPPARA']['dtype']} | {rc['KALLOOPPARA']['hfl']} | {rc['KALLOOPPARA']['hfl_date']} |\n| KIDANGOOR | {rc['KIDANGOOR']['dtype']} | {rc['KIDANGOOR']['hfl']} | {rc['KIDANGOOR']['hfl_date']} |\n
## 4. ARANGALI Aug 17-19 2018\n| Date | HTTP | District rows | Station rows |\n|:---|:---|:---|:---|\n{ar_tbl}\n\nARANGALI: no official level, excluded from label generation.\n
## 5. Labels — data/processed/labels_daily.csv\n| Station | Series | Danger | Warning | Days | Labeled | NaN | >=Danger | >=Warning |\n|:---|:---|:---|:---|:---|:---|:---|:---|:---|\n| KALLOOPPARA | {rc['KALLOOPPARA']['dtype']} | {rc['KALLOOPPARA']['danger']} | {rc['KALLOOPPARA']['warning']} | {rc['KALLOOPPARA']['n_rows']} | {rc['KALLOOPPARA']['n_labeled']} | {rc['KALLOOPPARA']['n_nan']} | {rc['KALLOOPPARA']['n_danger']} | {rc['KALLOOPPARA']['n_warning']} |\n| KIDANGOOR | {rc['KIDANGOOR']['dtype']} | {rc['KIDANGOOR']['danger']} | {rc['KIDANGOOR']['warning']} | {rc['KIDANGOOR']['n_rows']} | {rc['KIDANGOOR']['n_labeled']} | {rc['KIDANGOOR']['n_nan']} | {rc['KIDANGOOR']['n_danger']} | {rc['KIDANGOOR']['n_warning']} |\n\nRules: label=1 if daily_max>=level; label=NaN if below and n<N (N=3 pre-2015, N=12 from 2015); label=0 otherwise. No interpolation.\n
## 6. Zones Without Official Levels\nVANDIPERIYAR (Idukki), KALAMPUR (Pathanamthitta), ARANGALI (Ernakulam), KUMBIDI (Alappuzha), KARATHODU (Alappuzha). No proxies created. Also excluded: Wayanad, Thrissur, Alappuzha/Kuttanad.\n
## 7. Known Gaps\n- Download ends 2024-12-31\n- Pre-2015: 3 obs/day; NaN if n<3 and below threshold\n- ~175 mid-series ok_empty months not re-verified\n- Datum provisional (HZS assumed, not confirmed)\n- HFL from bulletin table only, not verified against v3 max\n- 5 of 7 stations unlabeled (no official level)\n- v3 paging risk: orderBy ignored, months >1000 district rows may miss records\n"""
REPORT_OUT.write_text(md, encoding="utf-8")
print(f"  Written: {REPORT_OUT}")
print(f"\n{SEP}\nALL TASKS COMPLETE\n{SEP}")

