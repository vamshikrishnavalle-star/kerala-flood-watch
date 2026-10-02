import calendar, httpx, json, os, time, pandas as pd
from pathlib import Path

TARGET_STATIONS = {
    "016-SWRDKOCHI": {"name": "VANDIPERIYAR", "district": "Idukki"},
    "017-SWRDKOCHI": {"name": "KALLOOPPARA", "district": "Pathanamthitta"},
    "013-SWRDKOCHI": {"name": "KALAMPUR", "district": "Ernakulam"},
    "015-SWRDKOCHI": {"name": "KIDANGOOR", "district": "Kottayam"},
    "011-SWRDKOCHI": {"name": "ARANGALI", "district": "Thrissur"},
    "008-SWRDKOCHI": {"name": "KUMBIDI", "district": "Palakkad"},
    "006-SWRDKOCHI": {"name": "KARATHODU", "district": "Malappuram"},
}

API_URL = "https://indiawris.gov.in/Dataset/River Water Level"
HEADERS = {"accept": "application/json", "User-Agent": "Mozilla/5.0"}
CHUNKS_DIR = Path("data/raw/labels/cwc/v2/chunks")
V3_DIR = Path("data/raw/labels/cwc/v3")

print("--- 1. Extending 2025-2026 months ---")
with httpx.Client(timeout=30.0) as client:
    for code, info in TARGET_STATIONS.items():
        for yr in [2025, 2026]:
            for m in range(1, 13):
                _, last_day = calendar.monthrange(yr, m)
                m_str = f"{yr}-{m:02d}"
                s_date = f"{m_str}-01"
                e_date = f"{m_str}-{last_day:02d}"
                p = 0
                while True:
                    cf = CHUNKS_DIR / f"chunk_{code}_{m_str}_p{p}.json"
                    if not cf.exists():
                        params = {"stateName": "Kerala", "districtName": info["district"], "stationCode": code,
                                  "agencyName": "CWC", "startdate": s_date, "enddate": e_date, "page": p, "size": 1000}
                        r = client.post(API_URL, params=params, headers=HEADERS)
                        if r.status_code == 200:
                            data = r.json().get("data", [])
                            with open(cf, "w") as f:
                                json.dump({"status": "ok", "data": data}, f)
                            if len(data) < 1000:
                                break
                            p += 1
                        else:
                            break
                    else:
                        break

print("--- 2. Updating v3 CSV Datasets ---")
all_chunks = list(CHUNKS_DIR.glob("chunk_*.json"))
for code, info in TARGET_STATIONS.items():
    st_name = info["name"]
    rows = []
    for cf in all_chunks:
        if f"chunk_{code}_" in cf.name:
            with open(cf, "r") as f:
                d = json.load(f).get("data", [])
                for r in d:
                    if str(r.get("stationCode")).strip() == code and r.get("dataValue") is not None:
                        rows.append(r)
    if rows:
        df = pd.DataFrame(rows)
        df["dataTime"] = pd.to_datetime(df["dataTime"])
        df = df.drop_duplicates(subset=["stationCode", "datatypeCode", "dataTime"])
        df = df.sort_values(["stationCode", "datatypeCode", "dataTime"]).reset_index(drop=True)
        out_f = V3_DIR / f"station_{code}_{st_name.lower()}.csv"
        df.to_csv(out_f, index=False)
        print(f"  {out_f.name}: {len(df):,} total clean rows (Date range: {df['dataTime'].min()} to {df['dataTime'].max()})")

print("\n--- 3. Running Daily vs Monthly Set Diff for Arangali Aug 2018 ---")
daily_records = []
with httpx.Client(timeout=30.0) as client:
    for day in range(1, 32):
        d_str = f"2018-08-{day:02d}"
        p = {"stateName": "Kerala", "districtName": "Thrissur", "stationCode": "011-SWRDKOCHI",
             "agencyName": "CWC", "startdate": d_str, "enddate": d_str, "page": 0, "size": 1000}
        r = client.post(API_URL, params=p, headers=HEADERS)
        if r.status_code == 200:
            data = [d for d in r.json().get("data", []) if str(d.get("stationCode")).strip() == "011-SWRDKOCHI"]
            daily_records.extend(data)
df_daily = pd.DataFrame(daily_records).drop_duplicates(subset=["datatypeCode", "dataTime"])
df_v3 = pd.read_csv("data/raw/labels/cwc/v3/station_011-SWRDKOCHI_arangali.csv", parse_dates=["dataTime"])
df_v3_aug18 = df_v3[(df_v3.dataTime >= "2018-08-01") & (df_v3.dataTime <= "2018-08-31 23:59:59")]
print(f"Arangali Aug 2018 - Daily pull rows: {len(df_daily):,} | Monthly paged pull rows: {len(df_v3_aug18):,}")
print(f"Timestamp set difference: {len(set(df_daily.dataTime.astype(str)) ^ set(df_v3_aug18.dataTime.astype(str)))}")
