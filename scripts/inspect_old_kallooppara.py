import pandas as pd

# Check old Kallooppara file
old_kal = pd.read_csv("data/raw/labels/cwc/station_017-SWRDKOCHI_kallooppara.csv", parse_dates=["dataTime"])
old_kal["year"] = old_kal.dataTime.dt.year
print("Old Kallooppara file yearly counts:")
print(old_kal.groupby("year").size().to_string())

# Check if there are any errors or if API actually returned 0 in v2_requests_log.json
import json
with open("data/raw/labels/cwc/v2/v2_requests_log.json") as f:
    logs = json.load(f)

kal_logs = [l for l in logs if l.get("stationCode") == "017-SWRDKOCHI" and l.get("startdate", "").startswith(("2017", "2018", "2019"))]
print(f"\nKallooppara 2017-2019 logged requests in v2: {len(kal_logs)}")
for l in kal_logs[:10]:
    print(l)
