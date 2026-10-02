"""CLI script to ingest historical and forecast weather for Kerala flood zones."""

import argparse
from datetime import date
import logging
from pathlib import Path
import sys
import time

from src.ingest.client import OpenMeteoClient
from src.ingest.historical import fetch_historical_series
from src.ingest.forecast import fetch_live_forecast
from src.ingest.zones import KERALA_ZONES, get_all_zones, get_zone_by_slug, save_zones_to_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fetch_data")


def main():
    parser = argparse.ArgumentParser(description="Fetch historical and forecast weather for Kerala flood zones.")
    parser.add_argument("--zone", type=str, default=None, help="Zone slug to fetch (defaults to all zones).")
    parser.add_argument("--start-year", type=int, default=2000, help="Start year for historical data (default: 2000).")
    parser.add_argument("--end-year", type=int, default=date.today().year, help="End year for historical data.")
    parser.add_argument("--live", action="store_true", help="Fetch live and short-term forecast data.")
    parser.add_argument("--force-refresh", action="store_true", help="Bypass cache and force re-fetch.")
    args = parser.parse_args()

    client = OpenMeteoClient()
    zones = [get_zone_by_slug(args.zone)] if args.zone else get_all_zones()

    if not zones or any(z is None for z in zones):
        logger.error(f"Invalid zone slug: {args.zone}. Available zones: {list(KERALA_ZONES.keys())}")
        sys.exit(1)

    data_dir = Path("data/raw")
    hist_dir = data_dir / "historical"
    forecast_dir = data_dir / "forecast"

    elevations = {}

    try:
        for zone in zones:
            logger.info(f"=== Processing Zone: {zone.name} ({zone.slug}) ===")

            # 1. Historical fetch
            df_hist, elev = fetch_historical_series(
                zone=zone,
                start_year=args.start_year,
                end_year=args.end_year,
                client=client,
                output_dir=hist_dir,
                force_refresh=args.force_refresh,
            )
            if elev is not None:
                elevations[zone.slug] = elev
                logger.info(f"Recorded elevation for {zone.slug}: {elev} m")

            # 2. Live forecast fetch if requested
            if args.live:
                df_fcst, fcst_elev = fetch_live_forecast(
                    zone=zone,
                    client=client,
                    output_dir=forecast_dir,
                    force_refresh=args.force_refresh,
                )
                if fcst_elev is not None and zone.slug not in elevations:
                    elevations[zone.slug] = fcst_elev

            # Polite delay between zones to respect Open-Meteo limits
            time.sleep(1.0)

        # Save zones metadata with recorded elevations to data/raw/zones.csv
        zones_csv = data_dir / "zones.csv"
        save_zones_to_csv(zones_csv, zones_with_elevation=elevations)
        logger.info(f"Updated zones catalog with elevation at {zones_csv}")

    finally:
        client.close()

    logger.info("Data ingestion completed successfully.")


if __name__ == "__main__":
    main()
