import json, math, pathlib, sys, time
from datetime import date, timedelta
import pandas as pd
import numpy as np
import requests

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

def min_n_strict(d):  return 3 if d.year < 2015 else 12
def min_n_all3(d):    return 3

# ============================================================
# SECTION A: KALLOOPPARA HHS/HZS OFFSET ANALYSIS
# ============================================================
print(SEP); print("SECTION A -- KALLOOPPARA HHS/HZS OFFSET ANALYSIS"); print(SEP)
df_k = load_station(STATION_FILE["KALLOOPPARA"])
hhs_s = df_k[df_k["datatypeCode"]=="HHS"].set_index("dataTime")["dataValue"]
hzs_s = df_k[df_k["datatypeCode"]=="HZS"].set_index("dataTime")["dataValue"]
both  = pd.concat([hhs_s.rename("HHS"), hzs_s.rename("HZS")], axis=1).dropna()
both["offset"] = both["HHS"] - both["HZS"]
nonzero = (both["offset"] != 0).sum()
total   = len(both)
print(f"  Timestamps with both HHS and HZS: {total:,}")
print(f"  Nonzero HHS-HZS offsets:          {nonzero:,}")
print(f"  Zero offsets (HHS==HZS):           {total - nonzero:,}")
if nonzero > 0:
    print(f"  Offset min={both['offset'].min():.4f}  median={both['offset'].median():.4f}  max={both['offset'].max():.4f}")
print()
print("  KALLOOPPARA -- yearly row counts and HHS min/median/max:")
print(f"  {'Year':>6}  {'n_HHS':>8}  {'n_HZS':>8}  {'HHS_min':>9}  {'HHS_med':>9}  {'HHS_max':>9}")
df_k["_year"] = df_k["dataTime"].dt.year
for yr, grp in df_k.groupby("_year"):
    hhs_yr = grp[grp["datatypeCode"]=="HHS"]["dataValue"].dropna()
    hzs_yr = grp[grp["datatypeCode"]=="HZS"]["dataValue"].dropna()
    if len(hhs_yr) == 0: continue
    print(f"  {yr:>6}  {len(hhs_yr):>8}  {len(hzs_yr):>8}  {hhs_yr.min():>9.3f}  {hhs_yr.median():>9.3f}  {hhs_yr.max():>9.3f}")

# ============================================================
# SECTION B: READINGS/DAY DISTRIBUTION BY MONTH
# ============================================================
print(); print(SEP); print("SECTION B -- READINGS/DAY DISTRIBUTION BY MONTH"); print(SEP)

for station, dtype in [("KALLOOPPARA","HHS"), ("KIDANGOOR","HHS")]:
    print(f"\n  {station} ({dtype}) -- readings/day by year-month:")
    df  = load_station(STATION_FILE[station])
    sub = df[df["datatypeCode"]==dtype].dropna(subset=["dataValue"])
    sub = sub.copy(); sub["_ym"] = sub["dataTime"].dt.to_period("M")
    dc  = sub.groupby(["_ym","_date"]).size().reset_index(name="n")
    print(f"  {'YearMon':>9}  {'days':>5}  {'min':>5}  {'p25':>5}  {'med':>5}  {'p75':>5}  {'max':>5}  {'<3':>5}  {'<12':>5}")
    for ym, grp in dc.groupby("_ym"):
        c = grp["n"]
        if c.empty: continue
        print(f"  {str(ym):>9}  {len(c):>5}  {c.min():>5}  {int(c.quantile(.25)):>5}  {int(c.median()):>5}  {int(c.quantile(.75)):>5}  {c.max():>5}  {int((c<3).sum()):>5}  {int((c<12).sum()):>5}")

# NaN comparison Jun-Oct: N=3 all years vs N=12 from 2015
print()
print("  Jun-Oct NaN comparison (N=3 all years vs N=12 from 2015):")
print(f"  {'Station':<16}  {'dtype':<5}  {'Jun-Oct days':>13}  {'NaN(N=3 all)':>13}  {'NaN(N=12 post14)':>18}  {'extra NaN':>10}")
for station, dtype, level in [("KALLOOPPARA","HHS",5.0), ("KIDANGOOR","HHS",6.16)]:
    df  = load_station(STATION_FILE[station])
    sub = df[df["datatypeCode"]==dtype].dropna(subset=["dataValue"])
    daily = sub.groupby("_date")["dataValue"].agg(daily_max="max", n_readings="count").reset_index()
    daily["month"] = pd.to_datetime(daily["_date"]).dt.month
    daily["year"]  = pd.to_datetime(daily["_date"]).dt.year
    jun_oct = daily[daily["month"].between(6,10)].copy()
    def nan_strict(row):
        if row["daily_max"] >= level: return False
        return row["n_readings"] < (3 if row["year"] < 2015 else 12)
    def nan_all3(row):
        if row["daily_max"] >= level: return False
        return row["n_readings"] < 3
    ns = jun_oct.apply(nan_strict, axis=1).sum()
    na = jun_oct.apply(nan_all3,   axis=1).sum()
    print(f"  {station:<16}  {dtype:<5}  {len(jun_oct):>13}  {na:>13}  {ns:>18}  {ns-na:>10}")

# ============================================================
# SECTION C: ARANGALI Aug 17-19 2018 (Thrissur)
# ============================================================
print(); print(SEP); print("SECTION C -- ARANGALI Aug 17-19 2018 (districtName=Thrissur, 3s delay)"); print(SEP)

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
    print(f"  Querying {d} (Thrissur) ...", end=" ", flush=True)
    res = api_day("Thrissur", "011-SWRDKOCHI", d)
    arangali_results.append(res)
    err = f"  error={res.get('error','')}" if "error" in res else ""
    print(f"HTTP {res['http']}  district_rows={res['district_rows']}  station_rows={res['station_rows']}{err}")
print()
print(f"  {'Date':<12}  {'HTTP':>5}  {'Dist rows':>10}  {'Stn rows':>10}")
for r in arangali_results:
    print(f"  {r['date']:<12}  {str(r['http']):>5}  {r['district_rows']:>10}  {r['station_rows']:>10}")

# ============================================================
# SECTION D: UPDATE danger_levels_manual.csv
# ============================================================
print(); print(SEP); print("SECTION D -- UPDATING danger_levels_manual.csv"); print(SEP)
ldf = pd.read_csv(LEVELS_FILE)
mask = ldf["station"].str.strip() == "KIDANGOOR"
ldf.loc[mask, "datum"] = "HHS series (matches HFL 8.24 on 2020-08-09)"
ldf.to_csv(LEVELS_FILE, index=False)
print("  KIDANGOOR datum updated. Current file:")
print(ldf.to_string(index=False))

levels, hfl_dates = {}, {}
for _, r in ldf.iterrows():
    st = str(r["station"]).strip(); lt = str(r["level_type"]).strip()
    v  = float(r["value"]) if pd.notna(r["value"]) else None
    hd = str(r.get("hfl_date","")).strip()
    if hd in ("","nan"): hd = None
    levels.setdefault(st,{})[lt] = v
    if hd: hfl_dates[st] = hd

approved_series = {"KALLOOPPARA":"HHS", "KIDANGOOR":"HHS"}

# ============================================================
# SECTION E: REBUILD LABELS
# ============================================================
print(); print(SEP); print("SECTION E -- LABEL GENERATION (both stations HHS, N=3 pre-2015, N=12 from 2015)"); print(SEP)
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
        dt=row["_date"]; dmax=row["daily_max"]; n=int(row["n_readings"]); mn=min_n_strict(dt)
        def lbl(level, dmax=dmax, n=n, mn=mn):
            if pd.isna(dmax): return float("nan")
            if dmax >= level: return 1
            return float("nan") if n < mn else 0
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
# SECTION F: COUNTS PER STATION-YEAR + AUG 14-20
# ============================================================
print(); print(SEP); print("SECTION F -- COUNTS PER STATION-YEAR + Aug 14-20 2018"); print(SEP)
lbl_df["label_danger"]  = pd.to_numeric(lbl_df["label_danger"],  errors="coerce")
lbl_df["label_warning"] = pd.to_numeric(lbl_df["label_warning"], errors="coerce")
lbl_df["year"] = pd.to_datetime(lbl_df["date"]).dt.year
for station in ["KALLOOPPARA","KIDANGOOR"]:
    sdf = lbl_df[lbl_df["station"]==station].sort_values("date")
    print(f"\n  {station} ({approved_series[station]}):")
    print(f"  {'Year':>6}  {'>=DL':>6}  {'>=WL':>6}  {'NaN':>6}  {'labeled':>8}  {'clust_DL':>10}  {'clust_WL':>10}")
    for yr, grp in sdf.groupby("year"):
        g=grp.sort_values("date")
        nd=int((g["label_danger"]==1).sum()); nw=int((g["label_warning"]==1).sum())
        nn=int(g["label_danger"].isna().sum()); nl=int(g["label_danger"].notna().sum())
        cd=count_clusters(g["label_danger"].tolist()); cw=count_clusters(g["label_warning"].tolist())
        print(f"  {yr:>6}  {nd:>6}  {nw:>6}  {nn:>6}  {nl:>8}  {cd:>10}  {cw:>10}")
total_d=int((lbl_df["label_danger"]==1).sum())
total_w=int((lbl_df["label_warning"]==1).sum())
total_n=int(lbl_df["label_danger"].isna().sum())
print(f"\n  TOTALS: rows={len(lbl_df)}  >=danger={total_d}  >=warning={total_w}  NaN={total_n}")
for lname, cnt in [("danger",total_d),("warning",total_w)]:
    print(f"  [{'OK' if cnt>=100 else 'MISS'}] Total {lname} = {cnt} (threshold 100)")
for station in ["KALLOOPPARA","KIDANGOOR"]:
    s=lbl_df[lbl_df["station"]==station]
    for lname,cnt in [("danger",int((s["label_danger"]==1).sum())),
                      ("warning",int((s["label_warning"]==1).sum()))]:
        print(f"  [{'OK' if cnt>=10 else 'MISS'}] {station} {lname} = {cnt} (threshold 10)")

# Aug 14-20 all stations
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
# SECTION G: WRITE CORRECTED REPORT
# ============================================================
print(); print(SEP); print("SECTION G -- WRITING CORRECTED docs/label-sourcing-report.md"); print(SEP)
rc={}
for station in ["KALLOOPPARA","KIDANGOOR"]:
    s=lbl_df[lbl_df["station"]==station]
    rc[station]=dict(dtype=approved_series[station],danger=levels[station]["danger"],
        warning=levels[station]["warning"],hfl=levels[station]["HFL"],hfl_date=hfl_dates[station],
        n_rows=len(s),n_danger=int((s["label_danger"]==1).sum()),
        n_warning=int((s["label_warning"]==1).sum()),
        n_nan=int(s["label_danger"].isna().sum()),n_labeled=int(s["label_danger"].notna().sum()))
ar_tbl="\n".join(
    f"| {r['date']} | {r['http']} | {r['district_rows']} | {r['station_rows']} |"
    for r in arangali_results)
kp=rc["KALLOOPPARA"]; ki=rc["KIDANGOOR"]
md = "# Phase 2 Label Sourcing Report\n"
md += f"Generated: {date.today().isoformat()}\n\n"
md += "## 1. Source PDFs\n\n"
md += "| PDF | Bulletin Date | Stations Found |\n|:---|:---|:---|\n"
md += "| cfcrcwcdfb17-10-2021-2.pdf | 2021-10-17 | KALLOOPPARA p.3 Severe Flood, KIDANGOOR p.4 Above Normal |\n"
md += "| cfcrcwcdfb15-11-2021-2.pdf | 2021-11-15 | KALLOOPPARA p.4 Above Normal |\n"
md += "| cfcrcwcdfb19-10-2021_2.pdf | 2021-10-19 | KALLOOPPARA p.4 Above Normal |\n\n"
md += "## 2. Official Levels (danger_levels_manual.csv)\n\n"
md += "| Station | Danger (m) | Warning (m) | HFL (m) | HFL Date | Datum |\n|:---|:---|:---|:---|:---|:---|\n"
md += f"| KALLOOPPARA | {kp['danger']} | {kp['warning']} | {kp['hfl']} | {kp['hfl_date']} | HZS=HHS (offset 0.00); HHS used for labels |\n"
md += f"| KIDANGOOR   | {ki['danger']} | {ki['warning']} | {ki['hfl']} | {ki['hfl_date']} | HHS series (matches HFL 8.24 on 2020-08-09) |\n\n"
md += "> Provisional: levels from CWC Daily Flood Bulletin table columns. Not cross-referenced with CWC Level Forecast Sites register.\n\n"
md += "## 3. Datum Check\n\n"
md += "| Station | Approved Series | HFL (bulletin) | HFL Date | HZS max | HHS max |\n|:---|:---|:---|:---|:---|:---|\n"
md += f"| KALLOOPPARA | HHS | {kp['hfl']} | {kp['hfl_date']} | 9.6400 (offset 0.00) | 9.6400 |\n"
md += f"| KIDANGOOR   | HHS | {ki['hfl']} | {ki['hfl_date']} | 9.4400 (diff 1.20, no match) | 8.2400 |\n\n"
md += "## 4. ARANGALI Aug 17-19 2018\n\n"
md += "Serial requests (3 s delay), stationCode 011-SWRDKOCHI, districtName=Thrissur.\n\n"
md += "| Date | HTTP | District rows | Station rows |\n|:---|:---|:---|:---|\n"
md += ar_tbl + "\n\n"
md += "v3 series: Aug 17/18/19 show no rows in downloaded data. No official level; excluded from label generation.\n\n"
md += "## 5. Labels -- data/processed/labels_daily.csv\n\n"
md += "| Station | Series | Danger | Warning | Total days | Labeled | NaN | >=Danger | >=Warning |\n|:---|:---|:---|:---|:---|:---|:---|:---|:---|\n"
md += f"| KALLOOPPARA | {kp['dtype']} | {kp['danger']} | {kp['warning']} | {kp['n_rows']} | {kp['n_labeled']} | {kp['n_nan']} | {kp['n_danger']} | {kp['n_warning']} |\n"
md += f"| KIDANGOOR   | {ki['dtype']} | {ki['danger']} | {ki['warning']} | {ki['n_rows']} | {ki['n_labeled']} | {ki['n_nan']} | {ki['n_danger']} | {ki['n_warning']} |\n\n"
md += "Label rules: daily_max=max reading in approved series per calendar day (no interpolation, no forward-fill).\n"
md += "label=1 if daily_max>=level; NaN if below and n_readings<N (N=3 pre-2015, N=12 from 2015); 0 otherwise.\n\n"
md += "## 6. Zones Without Official Levels\n\n"
md += "| Station | Code | District | Coverage |\n|:---|:---|:---|:---|\n"
md += "| VANDIPERIYAR | 016-SWRDKOCHI | Idukki      | HHS+HZS 2000- |\n"
md += "| KALAMPUR     | 013-SWRDKOCHI | Ernakulam   | HHS+HZS 2015- |\n"
md += "| ARANGALI     | 011-SWRDKOCHI | Thrissur    | HZS 2015-     |\n"
md += "| KUMBIDI      | 008-SWRDKOCHI | Palakkad    | HZS 2009-     |\n"
md += "| KARATHODU    | 006-SWRDKOCHI | Malappuram  | HZS 2009-     |\n\n"
md += "Zones in src/ingest/zones.py with no valid gauge (no labels, no proxies):\n"
md += "- Idukki (VANDIPERIYAR has data but no confirmed level)\n"
md += "- Wayanad (003-SWRDKOCHI excluded by design)\n"
md += "- Ernakulam (KALAMPUR has data but no confirmed level)\n"
md += "- Thrissur (ARANGALI has data but no confirmed level)\n"
md += "- Alappuzha (no station in scope for labeling)\n\n"
md += "## 7. Known Gaps\n\n"
md += "| Gap | Detail |\n|:---|:---|\n"
md += "| Download end | v3 ends 2024-12-31; 2025+ not downloaded |\n"
md += "| Pre-2015 obs schedule | 3 obs/day; NaN if n<3 and daily_max<threshold |\n"
md += f"| Mid-series NaN | KALLOOPPARA {kp['n_nan']} NaN days, KIDANGOOR {ki['n_nan']} NaN days |\n"
md += "| Datum provisional | Levels from bulletin table; not cross-referenced with CWC Level Forecast Sites register |\n"
md += f"| Total danger days | {total_d} (threshold 100, {'MET' if total_d>=100 else 'MISS by '+str(100-total_d)}) |\n"
md += "| 5 of 7 stations unlabeled | VANDIPERIYAR, KALAMPUR, ARANGALI, KUMBIDI, KARATHODU: no confirmed official level |\n"
md += "| v3 paging risk | orderBy ignored by API; months >1000 district rows may miss station records |\n"
REPORT_OUT.write_text(md, encoding="utf-8")
print(f"  Written: {REPORT_OUT}")
print(); print(SEP); print("ALL CORRECTIONS COMPLETE -- stopped for approval"); print(SEP)

