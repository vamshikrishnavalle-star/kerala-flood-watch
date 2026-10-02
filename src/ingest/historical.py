"""Historical weather data ingestion from Open-Meteo Archive API."""

from datetime import date, datetime, timedelta
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

from src.ingest.client import OpenMeteoClient
from src.ingest.zones import FloodZone

logger = logging.getLogger(__name__)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_historical_year(
    zone: FloodZone,
    year: int,
    client: OpenMeteoClient,
    force_refresh: bool = False,
) -> Tuple[pd.DataFrame, Optional[float]]:
    """Fetch one year of historical weather data for a zone with caching."""
    current_year = date.today().year

    # Define date range for the year
    start_date = f"{year}-01-01"
    if year == current_year:
        # Re-fetch recent days because ERA5T reanalysis is updated continuously
        end_date = (date.today() - timedelta(days=2)).isoformat()
        is_completed_year = False
    else:
        end_date = f"{year}-12-31"
        is_completed_year = True

    params = {
        "latitude": zone.latitude,
        "longitude": zone.longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": [
            "precipitation_sum",
            "rain_sum",
            "temperature_2m_max",
            "temperature_2m_min",
            "soil_moisture_0_to_7cm_mean",
            "soil_moisture_7_to_28cm_mean",
        ],
        "timezone": "Asia/Kolkata",
    }

    cache_key = f"hist_{zone.slug}_{year}"
    # Completed past years are cached permanently; current year is refreshed if recent
    should_refresh = force_refresh or (not is_completed_year)

    data = client.fetch_with_retry(
        url=ARCHIVE_URL,
        params=params,
        cache_key=cache_key if is_completed_year else None,
        force_refresh=should_refresh,
    )

    client.validate_historical_payload(data)

    elevation = data.get("elevation")
    daily = data["daily"]

    df = pd.DataFrame({
        "date": daily["time"],
        "zone_slug": zone.slug,
        "precipitation_sum": daily["precipitation_sum"],
        "rain_sum": daily.get("rain_sum", daily["precipitation_sum"]),
        "temperature_2m_max": daily["temperature_2m_max"],
        "temperature_2m_min": daily["temperature_2m_min"],
        "soil_moisture_0_7cm": daily["soil_moisture_0_to_7cm_mean"],
        "soil_moisture_7_28cm": daily["soil_moisture_7_to_28cm_mean"],
    })

    return df, elevation


def fetch_historical_series(
    zone: FloodZone,
    start_year: int,
    end_year: int,
    client: OpenMeteoClient,
    output_dir: Optional[Path] = None,
    force_refresh: bool = False,
) -> Tuple[pd.DataFrame, Optional[float]]:
    """Fetch multi-year historical dataset for a zone from start_year to end_year."""
    frames: List[pd.DataFrame] = []
    zone_elevation: Optional[float] = None

    for yr in range(start_year, end_year + 1):
        logger.info(f"Fetching historical weather for {zone.slug} ({yr})...")
        df_year, elev = fetch_historical_year(zone, yr, client, force_refresh=force_refresh)
        if elev is not None:
            zone_elevation = elev
        frames.append(df_year)

    combined_df = pd.concat(frames, ignore_index=True)
    combined_df["date"] = pd.to_datetime(combined_df["date"])
    combined_df = combined_df.sort_values("date").drop_duplicates(subset=["date", "zone_slug"]).reset_index(drop=True)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / f"{zone.slug}.csv"
        combined_df.to_csv(csv_path, index=False)
        logger.info(f"Saved {len(combined_df)} records to {csv_path}")

    return combined_df, zone_elevation
