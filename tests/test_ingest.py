"""Unit tests for weather data ingestion, validation, and soil moisture proxies with mocked responses."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import httpx
import pytest

from src.ingest.client import DataQualityError, OpenMeteoClient
from src.ingest.historical import fetch_historical_year
from src.ingest.forecast import fetch_live_forecast
from src.ingest.zones import KERALA_ZONES, get_all_zones


@pytest.fixture
def mock_archive_payload():
    """Sample valid Open-Meteo Archive API JSON payload."""
    return {
        "latitude": 10.1076,
        "longitude": 76.3516,
        "elevation": 14.0,
        "daily": {
            "time": ["2018-08-15", "2018-08-16", "2018-08-17"],
            "precipitation_sum": [182.5, 235.0, 110.2],
            "rain_sum": [182.5, 235.0, 110.2],
            "temperature_2m_max": [27.8, 26.5, 28.1],
            "temperature_2m_min": [23.1, 22.8, 23.4],
            "soil_moisture_0_to_7cm_mean": [0.48, 0.52, 0.51],
            "soil_moisture_7_to_28cm_mean": [0.45, 0.49, 0.50],
        },
    }


@pytest.fixture
def mock_forecast_payload():
    """Sample valid Open-Meteo Forecast API JSON payload."""
    return {
        "latitude": 10.1076,
        "longitude": 76.3516,
        "elevation": 14.0,
        "hourly": {
            "time": ["2026-10-02T00:00", "2026-10-02T01:00"],
            "precipitation": [5.2, 8.4],
            "rain": [5.2, 8.4],
            "temperature_2m": [25.0, 24.8],
            "relative_humidity_2m": [92, 95],
            "soil_moisture_0_to_1cm": [0.40, 0.42],
            "soil_moisture_1_to_3cm": [0.38, 0.39],
            "soil_moisture_3_to_9cm": [0.35, 0.36],
            "soil_moisture_9_to_27cm": [0.32, 0.33],
        },
    }


def test_zones_configuration():
    """Verify all 7 Kerala zones have valid coordinates, rationale, and slugs."""
    zones = get_all_zones()
    assert len(zones) == 7
    for zone in zones:
        assert zone.slug in KERALA_ZONES
        assert 8.0 <= zone.latitude <= 13.0  # Latitude bounds for Kerala
        assert 74.0 <= zone.longitude <= 78.0  # Longitude bounds for Kerala
        assert len(zone.rationale) > 10


def test_depth_weighted_soil_moisture_calculation():
    """Verify depth-weighted soil moisture formula and bounds validation."""
    client = OpenMeteoClient()
    # (1 * 0.40 + 2 * 0.30 + 4 * 0.20) / 7 = (0.40 + 0.60 + 0.80) / 7 = 1.80 / 7 = 0.25714...
    result = client.calculate_depth_weighted_soil_moisture(0.40, 0.30, 0.20)
    assert pytest.approx(result, rel=1e-3) == (1.80 / 7.0)

    # Reject out-of-bounds soil moisture
    with pytest.raises(DataQualityError):
        client.calculate_depth_weighted_soil_moisture(1.5, 0.3, 0.2)


def test_historical_payload_schema_and_types(tmp_path, mock_archive_payload):
    """Verify schema, column names, types, and elevation extraction."""
    mock_http = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_archive_payload
    mock_http.get.return_value = mock_resp

    client = OpenMeteoClient(cache_dir=tmp_path, http_client=mock_http)
    zone = KERALA_ZONES["ernakulam_aluva"]

    df, elevation = fetch_historical_year(zone, 2018, client=client)

    assert elevation == 14.0
    expected_cols = [
        "date",
        "zone_slug",
        "precipitation_sum",
        "rain_sum",
        "temperature_2m_max",
        "temperature_2m_min",
        "soil_moisture_0_7cm",
        "soil_moisture_7_28cm",
    ]
    assert list(df.columns) == expected_cols
    assert len(df) == 3
    assert df.loc[df["date"] == "2018-08-16", "precipitation_sum"].iloc[0] == 235.0


def test_null_rejection_data_quality_error():
    """Verify that excessive nulls trigger DataQualityError."""
    client = OpenMeteoClient()
    bad_payload = {
        "daily": {
            "time": ["2020-01-01", "2020-01-02", "2020-01-03"],
            "precipitation_sum": [None, None, 10.0],  # 66% nulls -> must fail
            "temperature_2m_max": [30.0, 31.0, 30.5],
            "temperature_2m_min": [22.0, 23.0, 22.5],
            "soil_moisture_0_to_7cm_mean": [0.3, 0.3, 0.3],
            "soil_moisture_7_to_28cm_mean": [0.4, 0.4, 0.4],
        }
    }
    with pytest.raises(DataQualityError):
        client.validate_historical_payload(bad_payload)


def test_forecast_ingestion_with_soil_proxy(mock_forecast_payload):
    """Verify hourly forecast parsing and depth-weighted proxy computation."""
    mock_http = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_forecast_payload
    mock_http.get.return_value = mock_resp

    client = OpenMeteoClient(http_client=mock_http)
    zone = KERALA_ZONES["ernakulam_aluva"]

    df, elev = fetch_live_forecast(zone, client=client, past_days=7, forecast_days=3)

    assert elev == 14.0
    assert "soil_moisture_0_7cm" in df.columns
    assert "soil_moisture_7_28cm" in df.columns
    assert len(df) == 2

    # Check proxy calculation for hour 0: (1*0.40 + 2*0.38 + 4*0.35) / 7 = 2.56 / 7 = 0.3657
    expected_sm0 = (1 * 0.40 + 2 * 0.38 + 4 * 0.35) / 7.0
    assert pytest.approx(df["soil_moisture_0_7cm"].iloc[0], rel=1e-3) == expected_sm0
    assert df["soil_moisture_7_28cm"].iloc[0] == 0.32


def test_client_caching_behavior(tmp_path, mock_archive_payload):
    """Verify cache avoids redundant HTTP calls."""
    mock_http = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_archive_payload
    mock_http.get.return_value = mock_resp

    client = OpenMeteoClient(cache_dir=tmp_path, http_client=mock_http)
    url = "https://test.open-meteo.com"
    params = {"lat": 10.0}

    # First fetch: should make HTTP call and cache
    res1 = client.fetch_with_retry(url, params, cache_key="test_cache")
    assert mock_http.get.call_count == 1

    # Second fetch with same cache_key: should read from disk cache
    res2 = client.fetch_with_retry(url, params, cache_key="test_cache")
    assert mock_http.get.call_count == 1  # Still 1 call
    assert res1 == res2
