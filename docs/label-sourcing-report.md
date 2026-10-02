# Label Sourcing Report: Kerala River Basins Ground Truth

## 1. Executive Summary
- **Source**: Ministry of Jal Shakti, Central Water Commission (CWC) & India-WRIS REST API.
- **Dataset Size**: 56,000 official water level & reservoir readings across 8 districts from 2018 to 2024.
- **Active Stations Found**: 12 CWC gauge & reservoir monitoring stations covering major Kerala river basins (Periyar, Chalakudy, Pamba/Manimala, Meenachil, Kabini, Bharathapuzha).

## 2. Station Inventory & Hydrological Surge Statistics

| District | Station Name | River / Tributary | Observations | Median Level (m) | 95th %ile Level (m) | Peak Flood Level (m) | Peak Flood Surge (m) | Historic Peak Date |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Ernakulam** | `KALAMPUR` | Kaliyar | 1,000 | 9.72 m | 12.65 m | **17.57 m** | +7.85 m | `2018-08-19` |
| **Ernakulam** | `Idamalayar Reservoir` | - | 6,000 | 159.66 m | 528.12 m | **704.79 m** | +545.13 m | `2019-07-22` |
| **Idukki** | `VANDIPERIYAR` | - | 1,000 | 791.93 m | 793.0 m | **795.54 m** | +3.61 m | `2018-08-19` |
| **Idukki** | `Idukki (Eb)/Idukki Arch Reservoir` | - | 6,000 | 723.86 m | 2374.97 m | **4000.89 m** | +3277.02 m | `2020-06-20` |
| **Kottayam** | `KIDANGOOR` | - | 1,000 | 2.55 m | 6.31 m | **8.08 m** | +5.53 m | `2018-07-17` |
| **Kottayam** | `KALATHUKADAVU` | - | 6,000 | 1.67 m | 30.93 m | **31.1 m** | +29.42 m | `2020-06-05` |
| **Malappuram** | `KARATHODU` | - | 1,000 | 4.41 m | 9.13 m | **14.4 m** | +9.99 m | `2018-08-18` |
| **Malappuram** | `CHAKKALAKUTH` | Kudhirapuzha | 6,000 | 12.13 m | 14.12 m | **1307.0 m** | +1294.87 m | `2019-07-09` |
| **Palakkad** | `KUMBIDI` | - | 7,000 | 3.55 m | 6.77 m | **10.8 m** | +7.25 m | `2018-08-18` |
| **Pathanamthitta** | `KALLOOPPARA` | Manimala | 7,000 | 2.84 m | 4.67 m | **8.84 m** | +6.0 m | `2018-08-18` |
| **Thrissur** | `ARANGALI` | Chalakudy | 7,000 | 1.51 m | 4.04 m | **9.76 m** | +8.25 m | `2024-07-31` |
| **Wayanad** | `MUTHANKERA` | Kabini | 6,999 | 707.66 m | 711.09 m | **1705.53 m** | +997.87 m | `2024-08-06` |

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
