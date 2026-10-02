import json, pandas as pd

with open("data/raw/labels/cwc/v2/v2_requests_log.json") as f:
    logs = json.load(f)

df = pd.DataFrame(logs)
for code in df["stationCode"].unique():
    sub = df[df["stationCode"] == code]
    sub_years = sorted(pd.to_datetime(sub["startdate"]).dt.year.unique())
    print(f"Station {code} ({sub['stationName'].iloc[0]}): logged startdate years = {sub_years}")
