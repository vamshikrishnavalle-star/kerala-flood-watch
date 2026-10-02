import glob, os, pandas as pd

chunks = glob.glob("data/raw/labels/cwc/v2/chunks/chunk_*.json")
print(f"Total chunks on disk: {len(chunks)}")
data = []
for c in chunks:
    base = os.path.basename(c)
    # chunk_016-SWRDKOCHI_2000-01_p0.json
    parts = base.replace(".json", "").split("_")
    if len(parts) >= 4:
        scode = parts[1]
        m = parts[2]
        p = parts[3]
        data.append({"stationCode": scode, "month": m, "page": p})

df = pd.DataFrame(data)
if not df.empty:
    print("\nChunks breakdown by station:")
    print(df.groupby("stationCode").agg(chunks=("month", "count"), min_month=("month", "min"), max_month=("month", "max")).to_string())
