# Label Sourcing & Historical Coverage Audit Report (Kerala CWC Gauges)

## 1. Executive Summary & Provenance Protocol
- **Source**: Ministry of Jal Shakti, Central Water Commission (CWC) & India-WRIS REST API (`https://indiawris.gov.in/Dataset/River Water Level`).
- **Standard of Integrity**: Ground-truth danger/warning levels are **NOT inferred, estimated, or reused from memory**. All level fields in this report are left blank until verified from official documents and entered into `data/raw/labels/cwc/danger_levels_manual.csv`.
- **Reservoir Exclusion**: All reservoir storage stations (e.g. Idamalayar, Idukki Arch Reservoir) are strictly excluded from river stage modeling.

## 2. Active River Gauge Stations & Datum Audit

| Station Code | Station Name | River / Tributary | District | Unit | Min Reading | Median Reading | Max Reading | Observed Datum Structure |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `016-SWRDKOCHI` | **VANDIPERIYAR** | Idukki | Idukki | `m` | 0.00 m | 791.42 m | 795.54 m | Absolute Elevation above MSL (Values ~791.4 m MSL) |
| `017-SWRDKOCHI` | **KALLOOPPARA** | Pathanamthitta | Pathanamthitta | `m` | 0.00 m | 1.98 m | 9.20 m | Local Gauge Height above zero (Values ~2.0 m above bed zero) |
| `013-SWRDKOCHI` | **KALAMPUR** | Ernakulam | Ernakulam | `m` | 4.40 m | 9.38 m | 17.57 m | Local Gauge Height above zero (Values ~9.4 m above bed zero) |
| `015-SWRDKOCHI` | **KIDANGOOR** | Kottayam | Kottayam | `m` | 0.43 m | 1.68 m | 8.08 m | Local Gauge Height above zero (Values ~1.7 m above bed zero) |
| `011-SWRDKOCHI` | **ARANGALI** | Thrissur | Thrissur | `m` | 0.01 m | 0.98 m | 9.76 m | Local Gauge Height above zero (Values ~1.0 m above bed zero) |
| `003-SWRDKOCHI` | **MUTHANKERA** | Wayanad | Wayanad | `m` | -0.99 m | 707.97 m | 1695.53 m | Absolute Elevation above MSL (Values ~708.0 m MSL) |
| `008-SWRDKOCHI` | **KUMBIDI** | Palakkad | Palakkad | `m` | 0.97 m | 4.03 m | 10.80 m | Local Gauge Height above zero (Values ~4.0 m above bed zero) |
| `006-SWRDKOCHI` | **KARATHODU** | Malappuram | Malappuram | `m` | 2.08 m | 3.95 m | 14.40 m | Local Gauge Height above zero (Values ~4.0 m above bed zero) |

### Key Datum Findings:
1. **High-Altitude Western Ghats Catchment (`VANDIPERIYAR` & `MUTHANKERA`)**: Readings are recorded in **meters above Mean Sea Level (m MSL)** (e.g., ~790m–795m MSL in Vandiperiyar, ~705m–715m MSL in Muthankera). Official danger levels entered in `danger_levels_manual.csv` for these stations **must be in m MSL**.
2. **Midland & Lowland River Stations (`KALAMPUR`, `KALLOOPPARA`, `ARANGALI`, `KIDANGOOR`, `KUMBIDI`, `KARATHODU`)**: Readings are recorded as **gauge height above local riverbed zero** (e.g. 1.0m to 17.5m). Official danger levels for these stations **must match staff gauge height**.

## 3. Historical Coverage & Gap Analysis (2000–2024)

| Station Name | District | Year | Monsoon Days with Data (Jun–Oct) | Monsoon Missing Days | Full Year Days with Data | Full Year Missing Days |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `VANDIPERIYAR` | Idukki | 2000 | 153 / 153 | **0** | 366 / 366 | **0** |
| `VANDIPERIYAR` | Idukki | 2001 | 153 / 153 | **0** | 365 / 365 | **0** |
| `VANDIPERIYAR` | Idukki | 2002 | 153 / 153 | **0** | 365 / 365 | **0** |
| `VANDIPERIYAR` | Idukki | 2003 | 153 / 153 | **0** | 365 / 365 | **0** |
| `VANDIPERIYAR` | Idukki | 2004 | 153 / 153 | **0** | 366 / 366 | **0** |
| `VANDIPERIYAR` | Idukki | 2005 | 153 / 153 | **0** | 365 / 365 | **0** |
| `VANDIPERIYAR` | Idukki | 2006 | 153 / 153 | **0** | 365 / 365 | **0** |
| `VANDIPERIYAR` | Idukki | 2007 | 153 / 153 | **0** | 365 / 365 | **0** |
| `VANDIPERIYAR` | Idukki | 2008 | 153 / 153 | **0** | 366 / 366 | **0** |
| `VANDIPERIYAR` | Idukki | 2009 | 150 / 153 | **3** | 362 / 365 | **3** |
| `VANDIPERIYAR` | Idukki | 2010 | 153 / 153 | **0** | 365 / 365 | **0** |
| `VANDIPERIYAR` | Idukki | 2011 | 153 / 153 | **0** | 365 / 365 | **0** |
| `VANDIPERIYAR` | Idukki | 2012 | 153 / 153 | **0** | 366 / 366 | **0** |
| `VANDIPERIYAR` | Idukki | 2013 | 153 / 153 | **0** | 365 / 365 | **0** |
| `VANDIPERIYAR` | Idukki | 2014 | 153 / 153 | **0** | 365 / 365 | **0** |
| `VANDIPERIYAR` | Idukki | 2015 | 153 / 153 | **0** | 184 / 365 | **181** |
| `VANDIPERIYAR` | Idukki | 2016 | 151 / 153 | **2** | 182 / 366 | **184** |
| `VANDIPERIYAR` | Idukki | 2017 | 137 / 153 | **16** | 198 / 365 | **167** |
| `VANDIPERIYAR` | Idukki | 2018 | 133 / 153 | **20** | 133 / 365 | **232** |
| `KALLOOPPARA` | Pathanamthitta | 2000 | 153 / 153 | **0** | 366 / 366 | **0** |
| `KALLOOPPARA` | Pathanamthitta | 2001 | 153 / 153 | **0** | 365 / 365 | **0** |
| `KALLOOPPARA` | Pathanamthitta | 2002 | 153 / 153 | **0** | 365 / 365 | **0** |
| `KALLOOPPARA` | Pathanamthitta | 2003 | 153 / 153 | **0** | 365 / 365 | **0** |
| `KALLOOPPARA` | Pathanamthitta | 2004 | 153 / 153 | **0** | 366 / 366 | **0** |
| `KALLOOPPARA` | Pathanamthitta | 2005 | 153 / 153 | **0** | 365 / 365 | **0** |
| `KALLOOPPARA` | Pathanamthitta | 2006 | 153 / 153 | **0** | 365 / 365 | **0** |
| `KALLOOPPARA` | Pathanamthitta | 2007 | 153 / 153 | **0** | 365 / 365 | **0** |
| `KALLOOPPARA` | Pathanamthitta | 2008 | 153 / 153 | **0** | 366 / 366 | **0** |
| `KALLOOPPARA` | Pathanamthitta | 2009 | 150 / 153 | **3** | 362 / 365 | **3** |
| `KALLOOPPARA` | Pathanamthitta | 2010 | 153 / 153 | **0** | 365 / 365 | **0** |
| `KALLOOPPARA` | Pathanamthitta | 2011 | 153 / 153 | **0** | 365 / 365 | **0** |
| `KALLOOPPARA` | Pathanamthitta | 2012 | 153 / 153 | **0** | 366 / 366 | **0** |
| `KALLOOPPARA` | Pathanamthitta | 2013 | 153 / 153 | **0** | 365 / 365 | **0** |
| `KALLOOPPARA` | Pathanamthitta | 2014 | 153 / 153 | **0** | 365 / 365 | **0** |
| `KALLOOPPARA` | Pathanamthitta | 2015 | 147 / 153 | **6** | 177 / 365 | **188** |
| `KALLOOPPARA` | Pathanamthitta | 2016 | 144 / 153 | **9** | 166 / 366 | **200** |
| `KALLOOPPARA` | Pathanamthitta | 2017 | 115 / 153 | **38** | 175 / 365 | **190** |
| `KALLOOPPARA` | Pathanamthitta | 2018 | 141 / 153 | **12** | 141 / 365 | **224** |
| `KALLOOPPARA` | Pathanamthitta | 2019 | 22 / 153 | **131** | 22 / 365 | **343** |
| `KALLOOPPARA` | Pathanamthitta | 2020 | 22 / 153 | **131** | 22 / 366 | **344** |
| `KALLOOPPARA` | Pathanamthitta | 2021 | 27 / 153 | **126** | 27 / 365 | **338** |
| `KALLOOPPARA` | Pathanamthitta | 2022 | 23 / 153 | **130** | 23 / 365 | **342** |
| `KALLOOPPARA` | Pathanamthitta | 2023 | 21 / 153 | **132** | 21 / 365 | **344** |
| `KALLOOPPARA` | Pathanamthitta | 2024 | 29 / 153 | **124** | 29 / 366 | **337** |
| `KALAMPUR` | Ernakulam | 2015 | 148 / 153 | **5** | 179 / 365 | **186** |
| `KALAMPUR` | Ernakulam | 2016 | 149 / 153 | **4** | 180 / 366 | **186** |
| `KALAMPUR` | Ernakulam | 2017 | 137 / 153 | **16** | 191 / 365 | **174** |
| `KALAMPUR` | Ernakulam | 2018 | 136 / 153 | **17** | 136 / 365 | **229** |
| `KIDANGOOR` | Kottayam | 2015 | 148 / 153 | **5** | 179 / 365 | **186** |
| `KIDANGOOR` | Kottayam | 2016 | 135 / 153 | **18** | 166 / 366 | **200** |
| `KIDANGOOR` | Kottayam | 2017 | 138 / 153 | **15** | 199 / 365 | **166** |
| `KIDANGOOR` | Kottayam | 2018 | 132 / 153 | **21** | 132 / 365 | **233** |
| `ARANGALI` | Thrissur | 2015 | 148 / 153 | **5** | 179 / 365 | **186** |
| `ARANGALI` | Thrissur | 2016 | 142 / 153 | **11** | 173 / 366 | **193** |
| `ARANGALI` | Thrissur | 2017 | 136 / 153 | **17** | 197 / 365 | **168** |
| `ARANGALI` | Thrissur | 2018 | 137 / 153 | **16** | 137 / 365 | **228** |
| `ARANGALI` | Thrissur | 2019 | 22 / 153 | **131** | 22 / 365 | **343** |
| `ARANGALI` | Thrissur | 2020 | 22 / 153 | **131** | 22 / 366 | **344** |
| `ARANGALI` | Thrissur | 2021 | 26 / 153 | **127** | 26 / 365 | **339** |
| `ARANGALI` | Thrissur | 2022 | 24 / 153 | **129** | 24 / 365 | **341** |
| `ARANGALI` | Thrissur | 2023 | 21 / 153 | **132** | 21 / 365 | **344** |
| `ARANGALI` | Thrissur | 2024 | 28 / 153 | **125** | 28 / 366 | **338** |
| `MUTHANKERA` | Wayanad | 2015 | 146 / 153 | **7** | 177 / 365 | **188** |
| `MUTHANKERA` | Wayanad | 2016 | 143 / 153 | **10** | 174 / 366 | **192** |
| `MUTHANKERA` | Wayanad | 2017 | 145 / 153 | **8** | 206 / 365 | **159** |
| `MUTHANKERA` | Wayanad | 2018 | 150 / 153 | **3** | 150 / 365 | **215** |
| `MUTHANKERA` | Wayanad | 2019 | 16 / 153 | **137** | 16 / 365 | **349** |
| `MUTHANKERA` | Wayanad | 2020 | 26 / 153 | **127** | 26 / 366 | **340** |
| `MUTHANKERA` | Wayanad | 2021 | 19 / 153 | **134** | 19 / 365 | **346** |
| `MUTHANKERA` | Wayanad | 2022 | 21 / 153 | **132** | 21 / 365 | **344** |
| `MUTHANKERA` | Wayanad | 2023 | 51 / 153 | **102** | 51 / 365 | **314** |
| `MUTHANKERA` | Wayanad | 2024 | 46 / 153 | **107** | 46 / 366 | **320** |
| `KUMBIDI` | Palakkad | 2015 | 146 / 153 | **7** | 177 / 365 | **188** |
| `KUMBIDI` | Palakkad | 2016 | 144 / 153 | **9** | 175 / 366 | **191** |
| `KUMBIDI` | Palakkad | 2017 | 137 / 153 | **16** | 198 / 365 | **167** |
| `KUMBIDI` | Palakkad | 2018 | 151 / 153 | **2** | 151 / 365 | **214** |
| `KUMBIDI` | Palakkad | 2019 | 27 / 153 | **126** | 27 / 365 | **338** |
| `KUMBIDI` | Palakkad | 2020 | 22 / 153 | **131** | 22 / 366 | **344** |
| `KUMBIDI` | Palakkad | 2021 | 26 / 153 | **127** | 26 / 365 | **339** |
| `KUMBIDI` | Palakkad | 2022 | 23 / 153 | **130** | 23 / 365 | **342** |
| `KUMBIDI` | Palakkad | 2023 | 21 / 153 | **132** | 21 / 365 | **344** |
| `KUMBIDI` | Palakkad | 2024 | 30 / 153 | **123** | 30 / 366 | **336** |
| `KARATHODU` | Malappuram | 2015 | 146 / 153 | **7** | 177 / 365 | **188** |
| `KARATHODU` | Malappuram | 2016 | 153 / 153 | **0** | 184 / 366 | **182** |
| `KARATHODU` | Malappuram | 2017 | 151 / 153 | **2** | 212 / 365 | **153** |
| `KARATHODU` | Malappuram | 2018 | 139 / 153 | **14** | 139 / 365 | **226** |

## 4. Zone Mapping & Governance Decisions

| Project Zone (`src/ingest/zones.py`) | Mapped CWC Gauge | Status in ML Model Training | Rationale |
| :--- | :--- | :--- | :--- |
| `ernakulam_aluva` | `013-SWRDKOCHI` (`KALAMPUR`) | **Candidate** | CWC River staff gauge on Kaliyar/Muvattupuzha basin in Ernakulam. |
| `pathanamthitta_kozhencherry` | `017-SWRDKOCHI` (`KALLOOPPARA`) | **Candidate** | CWC River staff gauge on Manimala/Pamba basin. |
| `thrissur_chalakudy` | `011-SWRDKOCHI` (`ARANGALI`) | **Candidate** | CWC River staff gauge on Chalakudy river corridor. |
| `kottayam_pala` | `015-SWRDKOCHI` (`KIDANGOOR`) | **Candidate** | CWC River staff gauge on Meenachil river valley (`KALATHUKADAVU` excluded due to no official DL metadata). |
| `idukki_cheruthoni` | `016-SWRDKOCHI` (`VANDIPERIYAR`) | **Candidate** | CWC Upper Periyar river gauge (Datum in m MSL). |
| `wayanad_vythiri` | `003-SWRDKOCHI` (`MUTHANKERA`) | **EXCLUDED** (Pending DL) | Retained for weather monitoring; excluded from model training unless user supplies verified official DL. |
| `alappuzha_kuttanad` | *None* | **EXCLUDED** | No CWC river gauge exists inside Alappuzha district bounds. Retained for weather monitoring only. |

### External Candidate Stations:
- **`008-SWRDKOCHI` (`KUMBIDI`, Palakkad)**: Full 2015–2024 data downloaded; available if Palakkad is added as a training zone.
- **`006-SWRDKOCHI` (`KARATHODU`, Malappuram)**: Full 2015–2024 data downloaded; available if Malappuram is added as a training zone.

## 5. Next Steps: Manual Danger Levels Entry
Open `data/raw/labels/cwc/danger_levels_manual.csv` and enter official danger/warning levels with exact document references. `scripts/count_exceedances.py` will read exclusively from that file.
