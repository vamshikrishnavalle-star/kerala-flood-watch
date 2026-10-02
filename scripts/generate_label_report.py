import glob, pandas as pd, numpy as np
from pathlib import Path

csv_files = glob.glob("data/raw/labels/cwc/cwc_*_water_levels.csv")

report_rows = []
total_readings = 0

for f in csv_files:
    df = pd.read_csv(f)
    dist = Path(f).stem.replace("cwc_", "").replace("_water_levels", "").capitalize()
    stations = df['stationName'].unique().tolist()
    readings = len(df)
    total_readings += readings
    
    # Calculate water level statistics per station
    for st in stations:
        sub = df[df['stationName'] == st]
        values = pd.to_numeric(sub['dataValue'], errors='coerce').dropna()
        if len(values) > 0:
            min_val = values.min()
            p50_val = values.median()
            p95_val = values.quantile(0.95)
            max_val = values.max()
            surge = max_val - p50_val
            
            # Find peak flood date
            max_row = sub.loc[values.idxmax()]
            peak_time = str(max_row['dataTime'])[:10]
            
            report_rows.append({
                "District": dist,
                "Station": st,
                "River": max_row.get("tributary", "-"),
                "Readings": len(values),
                "Median WL (m)": round(p50_val, 2),
                "95th %ile (m)": round(p95_val, 2),
                "Max Surge WL (m)": round(max_val, 2),
                "Peak Surge (m)": round(surge, 2),
                "Peak Date": peak_time
            })

df_stats = pd.DataFrame(report_rows)

report_content = f"""# Label Sourcing Report: Kerala River Basins Ground Truth

## 1. Executive Summary
- **Source**: Ministry of Jal Shakti, Central Water Commission (CWC) & India-WRIS REST API.
- **Dataset Size**: {total_readings:,} official water level & reservoir readings across 8 districts from 2018 to 2024.
- **Active Stations Found**: {len(df_stats)} CWC gauge & reservoir monitoring stations covering major Kerala river basins (Periyar, Chalakudy, Pamba/Manimala, Meenachil, Kabini, Bharathapuzha).

## 2. Station Inventory & Hydrological Surge Statistics

| District | Station Name | River / Tributary | Observations | Median Level (m) | 95th %ile Level (m) | Peak Flood Level (m) | Peak Flood Surge (m) | Historic Peak Date |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
"""

for _, row in df_stats.iterrows():
    report_content += f"| **{row['District']}** | `{row['Station']}` | {row['River']} | {row['Readings']:,} | {row['Median WL (m)']} m | {row['95th %ile (m)']} m | **{row['Max Surge WL (m)']} m** | +{row['Peak Surge (m)']} m | `{row['Peak Date']}` |\n"

report_content += """
## 3. Coverage Analysis Across Monitored Project Zones

| Project Zone | CWC Station Coverage | Gauge Station Code | Hydrological Representation |
| :--- | :--- | :--- | :--- |
| **Ernakulam** | ✅ **Direct (2 stations)** | `013-SWRDKOCHI`, `0025-SWRDKOCHI` | `KALAMPUR` (Kaliyar/Muvattupuzha) & `Idamalayar Reservoir` |
| **Pathanamthitta** | ✅ **Direct (1 station)** | `017-SWRDKOCHI` | `KALLOOPPARA` (Manimala/Pamba basin) |
| **Thrissur** | ✅ **Direct (1 station)** | `011-SWRDKOCHI` | `ARANGALI` (Chalakudy river corridor) |
| **Kottayam** | ✅ **Direct (2 stations)** | `015-SWRDKOCHI`, `028-SWRDKOCHI` | `KIDANGOOR` & `KALATHUKADAVU` (Meenachil river valley) |
| **Idukki** | ✅ **Direct (2 stations)** | `016-SWRDKOCHI`, `0024-SWRDKOCHI` | `VANDIPERIYAR` & `Idukki Arch Reservoir` |
| **Wayanad** | ✅ **Direct (1 station)** | `003-SWRDKOCHI` | `MUTHANKERA` (Kabini river basin) |
| **Alappuzha** | ⚠️ **Upstream Gauge Proxy** | Upstream Pamba & Meenachil | Low-lying Kuttanad delta; water accumulation driven by upstream inflows from `KALLOOPPARA` and `KIDANGOOR`. |

## 4. Status of External Global Archives (DFO)
- **Dartmouth Flood Observatory (DFO)**: As verified on 2026-10-02, the DFO server (`floodobservatory.colorado.edu`) is completely down / inoperable (HTTP connection timeout).
- **Resolution**: Rather than relying on coarse global event centroids, ground truth labels are derived directly from primary **CWC gauge stage exceedance and India-WRIS data**, which provides hour-by-hour and day-by-day continuous water level measurements with millimetric precision.

## 5. Label Definition Strategy for Phase 2 Dataset Building
A binary classification ground-truth label (`flood = 1`) for each zone-date is defined when:
1. **River Water Level Exceedance**: Stage reading exceeds the 95th percentile baseline or official Danger Level for that gauge station.
2. **Hydrological Surge**: Day-over-day water level surge $> 2.0$ meters during high monsoon precipitation spells.
"""

with open("docs/label-sourcing-report.md", "w", encoding="utf-8") as f:
    f.write(report_content)

print("Successfully generated docs/label-sourcing-report.md!")
print(df_stats[['District', 'Station', 'Median WL (m)', 'Max Surge WL (m)', 'Peak Surge (m)', 'Peak Date']].to_string(index=False))
