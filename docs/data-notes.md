# Open-Meteo & Kerala Hydrology Data Notes

## 1. Data Attribution
Weather data is sourced from [Open-Meteo](https://open-meteo.com/) under the Creative Commons Attribution 4.0 International (CC BY 4.0) license.
- **Historical reanalysis**: ECMWF ERA5-Land & ERA5 via Open-Meteo Historical Weather API (`https://archive-api.open-meteo.com/v1/archive`).
- **Live & Short-term forecasts**: Numerical Weather Prediction (NWP) models (ECMWF IFS, GFS, DWD ICON) via Open-Meteo Forecast API (`https://api.open-meteo.com/v1/forecast`).

## 2. Reanalysis vs. Forecast Bias (Known Limitation)
- **Historical Data**: ERA5-Land is a reanalysis dataset that harmonizes historical numerical model runs with retrospective observations. It provides a spatially continuous, gridded reanalysis, but is smoothed over roughly 9 km to 11 km grid resolution.
- **Live Forecast Data**: Operational numerical weather predictions (NWP) inherently carry model-specific variance, timing offsets for localized convective cloudbursts, and systematic biases.
- **Mitigation in Pipeline**: To prevent artificial boundary seams during live inference, rolling window features (past 24h, 72h, 7d) are extracted directly from the forecast API's `past_days=7` parameter rather than stitching two disparate data streams across the current-time boundary.

## 3. Dam Operations & Reservoir Releases Limitation
- A major driver of catastrophic flooding in Kerala (notably the August 2018 centenary flood) is the simultaneous opening of sluice gates from major reservoirs (e.g., Idukki, Cheruthoni, Idamalayar, Kakki, Banasura Sagar).
- This machine learning system predicts flood risk primarily from meteorological drivers (cumulative precipitation, soil moisture saturation levels, and terrain attributes). Because official reservoir discharge schedules and gate release telemetry are not accessible in real-time public weather APIs, dam-release-induced river surges may be under-predicted unless accompanied by extreme local rainfall. This is an explicit, documented system limitation.

## 4. Mixed Hazard Dynamics Across Selected Zones
The 7 chosen Kerala zones exhibit distinct flood mechanics:
- **High-relief Catchments (Idukki, Wayanad)**: Characterized by steep Western Ghats terrain. Heavy rainfall triggers rapid flash runoff, river swelling, and co-occurring debris flows/landslides.
- **Midland River Channels (Ernakulam/Aluva, Thrissur/Chalakudy, Pathanamthitta/Kozhencherry, Kottayam/Pala)**: Characterized by riverine inundation when upstream catchments discharge large volumes into narrow river corridors.
- **Low-lying Coastal/Backwater Basin (Alappuzha/Kuttanad)**: Located below sea level. Water accumulates slowly and lingers due to high tidal influence and drainage blockages through the Thanneermukkom barrage and Vembanad Lake.

Performance should be evaluated and monitored per zone rather than averaged as a single homogeneous hazard profile.
