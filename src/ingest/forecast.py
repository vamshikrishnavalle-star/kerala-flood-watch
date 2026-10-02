"""Live and short-term forecast weather ingestion from Open-Meteo Forecast API."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

from src.ingest.client import DataQualityError, OpenMeteoClient
from src.ingest.zones import FloodZone

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_live_forecast(
    zone: FloodZone,
    client: OpenMeteoClient,
    past_days: int = 7,
    forecast_days: int = 3,
    output_dir: Optional[Path] = None,
    force_refresh: bool = True,
) -> Tuple[pd.DataFrame, Optional[float]]:
    """Fetch hourly live and short-term forecast weather with past trailing window.

    Using past_days=7 guarantees that rolling 24h, 72h, and 7-day windows are
    derived from one continuous stream without stitching artifacts across the live boundary.
    """
    params = {
        "latitude": zone.latitude,
        "longitude": zone.longitude,
        "past_days": past_days,
        "forecast_days": forecast_days,
        "hourly": [
            "precipitation",
            "rain",
            "temperature_2m",
            "relative_humidity_2m",
            "soil_moisture_0_to_1cm",
            "soil_moisture_1_to_3cm",
            "soil_moisture_3_to_9cm",
            "soil_moisture_9_to_27cm",
        ],
        "timezone": "Asia/Kolkata",
    }

    cache_key = f"forecast_{zone.slug}"

    data = client.fetch_with_retry(
        url=FORECAST_URL,
        params=params,
        cache_key=cache_key,
        force_refresh=force_refresh,
    )

    if "hourly" not in data:
        raise DataQualityError("Forecast response missing 'hourly' section.")

    hourly = data["hourly"]
    required_hourly = [
        "time",
        "precipitation",
        "temperature_2m",
        "soil_moisture_0_to_1cm",
        "soil_moisture_1_to_3cm",
        "soil_moisture_3_to_9cm",
        "soil_moisture_9_to_27cm",
    ]

    for req in required_hourly:
        if req not in hourly or not hourly[req]:
            raise DataQualityError(f"Mandatory hourly field '{req}' missing from forecast response.")

    elevation = data.get("elevation")

    # Build depth-weighted surface soil moisture proxy (0-7cm) matching historical ERA5
    sm_0_1 = hourly["soil_moisture_0_to_1cm"]
    sm_1_3 = hourly["soil_moisture_1_to_3cm"]
    sm_3_9 = hourly["soil_moisture_3_to_9cm"]
    sm_9_27 = hourly["soil_moisture_9_to_27cm"]

    sm_0_7_proxy = [
        client.calculate_depth_weighted_soil_moisture(s0, s1, s3)
        if (s0 is not None and s1 is not None and s3 is not None)
        else None
        for s0, s1, s3 in zip(sm_0_1, sm_1_3, sm_3_9)
    ]

    df_hourly = pd.DataFrame({
        "timestamp": hourly["time"],
        "zone_slug": zone.slug,
        "precipitation_mm": hourly["precipitation"],
        "rain_mm": hourly.get("rain", hourly["precipitation"]),
        "temperature_2m": hourly["temperature_2m"],
        "relative_humidity_2m": hourly.get("relative_humidity_2m"),
        "soil_moisture_0_7cm": sm_0_7_proxy,
        "soil_moisture_7_28cm": sm_9_27,  # 9-27cm proxy for root-zone
    })

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / f"forecast_{zone.slug}.csv"
        df_hourly.to_csv(csv_path, index=False)
        logger.info(f"Saved forecast records to {csv_path}")

    return df_hourly, elevation
