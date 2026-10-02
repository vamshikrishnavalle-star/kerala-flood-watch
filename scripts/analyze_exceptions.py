import json, pandas as pd

with open("data/raw/labels/cwc/v2/v2_requests_log.json") as f:
    logs = json.load(f)

errs = [l for l in logs if "exception" in l or "error" in l]
edf = pd.DataFrame(errs)
print(f"Total failed/errored requests logged: {len(edf)}")
print(edf.groupby("stationCode").size().to_string())

print("\nSample exception types:")
print(edf["exception"].value_counts().to_string())
