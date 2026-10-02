"""Resilient HTTP client for Open-Meteo APIs with retries, caching, and data validation."""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger(__name__)


class DataQualityError(Exception):
    """Raised when weather API response fails quality and null checks."""
    pass


class OpenMeteoClient:
    """HTTP client handling Open-Meteo requests with retries, rate-limiting, and caching."""

    def __init__(
        self,
        timeout_seconds: float = 15.0,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        cache_dir: Optional[Path] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.cache_dir = cache_dir or Path("data/raw/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._client = http_client or httpx.Client(timeout=timeout_seconds)

    def fetch_with_retry(
        self,
        url: str,
        params: Dict[str, Any],
        cache_key: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """Fetch URL with exponential backoff retries and local disk caching."""
        cache_file = self.cache_dir / f"{cache_key}.json" if cache_key else None

        # Return cached response if valid and refresh not requested
        if cache_file and cache_file.exists() and not force_refresh:
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed reading cache file {cache_file}: {e}. Re-fetching.")

        last_exception: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.get(url, params=params)

                # Rate limiting or temporary server issues
                if response.status_code == 429 or response.status_code >= 500:
                    wait_time = self.backoff_factor ** attempt
                    logger.warning(
                        f"HTTP {response.status_code} from {url}. Retrying in {wait_time:.1f}s (Attempt {attempt}/{self.max_retries})"
                    )
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                data = response.json()

                # Cache valid response if requested
                if cache_file:
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(data, f)

                return data

            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_exception = exc
                wait_time = self.backoff_factor ** attempt
                logger.warning(
                    f"Request failed: {exc}. Retrying in {wait_time:.1f}s (Attempt {attempt}/{self.max_retries})"
                )
                time.sleep(wait_time)

        raise RuntimeError(
            f"Failed to fetch data from {url} after {self.max_retries} attempts: {last_exception}"
        ) from last_exception

    @staticmethod
    def validate_historical_payload(data: Dict[str, Any]) -> None:
        """Validate historical weather payload structure, columns, and check for unexpected nulls."""
        if "daily" not in data:
            raise DataQualityError("Historical response missing 'daily' section.")

        daily = data["daily"]
        required_fields = [
            "time",
            "precipitation_sum",
            "temperature_2m_max",
            "temperature_2m_min",
            "soil_moisture_0_to_7cm_mean",
            "soil_moisture_7_to_28cm_mean",
        ]

        for field in required_fields:
            if field not in daily:
                raise DataQualityError(f"Mandatory column '{field}' missing from daily data.")

            values = daily[field]
            if not values:
                raise DataQualityError(f"Field '{field}' returned empty list.")

            # Calculate null ratio
            null_count = sum(1 for v in values if v is None)
            null_ratio = null_count / len(values)

            # Strict threshold: completely missing or > 10% nulls in historical record is rejected
            if null_ratio > 0.10:
                raise DataQualityError(
                    f"Excessive null values in '{field}': {null_count}/{len(values)} ({null_ratio:.1%})."
                )

    @staticmethod
    def calculate_depth_weighted_soil_moisture(
        sm_0_1: float, sm_1_3: float, sm_3_9: float
    ) -> float:
        """Calculate proxy for 0-7cm soil moisture using depth-weighted layers.

        Formula: (1 * sm_0_1 + 2 * sm_1_3 + 4 * sm_3_9) / 7
        Aligns live ECMWF/GFS soil levels to ERA5-Land 0-7cm standard.
        """
        for val in (sm_0_1, sm_1_3, sm_3_9):
            if val is not None and not (0.0 <= val <= 1.0):
                raise DataQualityError(f"Soil moisture reading {val} outside physical bounds [0, 1].")

        return (1.0 * sm_0_1 + 2.0 * sm_1_3 + 4.0 * sm_3_9) / 7.0

    def close(self):
        """Close underlying HTTP client."""
        self._client.close()
