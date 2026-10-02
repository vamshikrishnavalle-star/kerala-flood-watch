import json, re, pandas as pd
from pathlib import Path

path = Path("data/raw/labels/Telemetry Sites.geojson")
print("Reading file in streaming mode...")

kerala_stations = []
total_found = 0

with open(path, "r", encoding="utf-8", errors="ignore") as f:
    buffer = ""
    for line in f:
        buffer += line
        if '"type": "Feature"' in buffer and ('}},' in line or '}}' in line):
            # Try to extract the JSON object for this feature
            start = buffer.find('{"type": "Feature"')
            if start == -1:
                start = buffer.find('{"type":"Feature"')
            
            end = buffer.rfind('}}')
            if start != -1 and end != -1 and end > start:
                feat_str = buffer[start:end+2]
                try:
                    feat = json.loads(feat_str)
                    total_found += 1
                    props = feat.get("properties", {})
                    if any("kerala" in str(v).lower() for v in props.values()):
                        coords = feat.get("geometry", {}).get("coordinates", [])
                        if coords and len(coords) >= 2:
                            props["lon"] = coords[0]
                            props["lat"] = coords[1]
                        kerala_stations.append(props)
                except Exception:
                    pass
                buffer = buffer[end+2:]

print(f"Total stations scanned: {total_found}")
print(f"Total Kerala telemetry stations matched: {len(kerala_stations)}")

df = pd.DataFrame(kerala_stations).drop_duplicates()
df.to_csv("data/raw/labels/kerala_telemetry_stations.csv", index=False)
print(f"Saved {len(df)} stations to data/raw/labels/kerala_telemetry_stations.csv")

if not df.empty:
    cols = [c for c in ['station_name', 'site_name', 'river_name', 'district__name', 'basin__name', 'lat', 'long', 'lon'] if c in df.columns]
    print("\nKerala Stations List:")
    print(df[cols].head(25).to_string() if cols else df.head(15).to_string())
