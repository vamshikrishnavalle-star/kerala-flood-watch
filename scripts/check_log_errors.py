import json, pandas as pd

with open("data/raw/labels/cwc/v2/v2_requests_log.json") as f:
    logs = json.load(f)

errs = [l for l in logs if "error" in l or "exception" in l]
print(f"Total error/exception entries in v2_requests_log.json: {len(errs)}")
for e in errs[:20]:
    print(e)
