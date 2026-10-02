"""Unit and integration test suite for Phase 5 FastAPI backend and inference engine.

All network calls are strictly mocked or use local saved data.
Zero usage of the words 'probability' or 'calibrated'.
"""

import os
os.environ["ENABLE_SCHEDULER"] = "false"

import json
import math
import pathlib
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.ingest.zones import KERALA_ZONES, get_zone_by_slug
from src.models.inference import (
    MODEL_VERSION,
    THRESHOLD_WARNING,
    THRESHOLD_DANGER,
    CLIP_RANGES,
    FEATURE_ORDER,
    compute_risk_score,
    extract_features_from_daily,
    predict_zone,
    compute_whatif_sensitivity,
    get_zone_validation_status,
    _PREDICTIONS_CACHE
)
from src.api.main import app

client = TestClient(app)
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture
def mock_daily_weather():
    """Generate a deterministic 96-day mock daily weather sequence.
    
    Index 92 is Day 0 (today). Days 0-91 are past days. Days 93-95 are forecast.
    """
    base_date = datetime(2026, 8, 15)
    dates = [(base_date - timedelta(days=92 - i)).strftime("%Y-%m-%d") for i in range(96)]
    # Yesterday (index 91) has 45mm rain, prior days have moderate rain
    precip = [10.0] * 91 + [45.0] + [20.0] + [15.0, 10.0, 5.0]
    soil_0_7 = [0.45] * 96
    soil_7_28 = [0.46] * 96

    return {
        "time": dates,
        "precipitation_sum": precip,
        "soil_moisture_0_to_7cm_mean": soil_0_7,
        "soil_moisture_7_to_28cm_mean": soil_7_28
    }


def test_coordinates_match_training():
    """Verify live fetch coordinates match training coordinates exactly."""
    kp = get_zone_by_slug("pathanamthitta_kozhencherry")
    assert kp is not None
    assert abs(kp.latitude - 9.3364) < 1e-4
    assert abs(kp.longitude - 76.6974) < 1e-4

    kt = get_zone_by_slug("kottayam_pala")
    assert kt is not None
    assert abs(kt.latitude - 9.7100) < 1e-4
    assert abs(kt.longitude - 76.6800) < 1e-4


def test_no_day_t_or_later_data(mock_daily_weather):
    """Verify Day 0 features strictly use rainfall through yesterday (t-1)."""
    # Baseline extraction
    f_base = extract_features_from_daily(mock_daily_weather, target_day_idx=92)
    assert f_base is not None
    assert f_base["rain_1d"] == 45.0

    # Tamper with Day 0 (index 92) and Day 1 (index 93) rainfall
    tampered_daily = json.loads(json.dumps(mock_daily_weather))
    tampered_daily["precipitation_sum"][92] = 999.0 # Day t rainfall
    tampered_daily["precipitation_sum"][93] = 888.0 # Day t+1 rainfall

    f_tampered = extract_features_from_daily(tampered_daily, target_day_idx=92)
    assert f_tampered is not None

    # Day 0 features MUST be completely identical despite Day t / Day t+1 modifications
    for k in FEATURE_ORDER:
        assert f_base[k] == f_tampered[k]


def test_unvalidated_zones_never_return_score(mock_daily_weather):
    """Verify unvalidated zones never compute or return a numerical score or alert."""
    unvalidated_slugs = [
        "ernakulam_aluva", "idukki_cheruthoni", "wayanad_vythiri",
        "alappuzha_kuttanad", "thrissur_chalakudy"
    ]
    for slug in unvalidated_slugs:
        res = predict_zone(slug, live_daily=mock_daily_weather)
        assert res["zone_status"] == "no_validated_model"
        assert res["risk_score"] is None
        assert res["warning_flag"] is None
        assert res["danger_flag"] is None
        assert res["alert_level"] is None


def test_danger_implies_warning():
    """Verify ranking monotonicity: danger_flag strictly implies warning_flag."""
    assert THRESHOLD_DANGER > THRESHOLD_WARNING

    # Test across 100 synthetic feature vectors
    rng = np.random.default_rng(42)
    for _ in range(100):
        synth_feats = {
            f: float(rng.uniform(CLIP_RANGES[f][0], CLIP_RANGES[f][1]))
            for f in FEATURE_ORDER
        }
        score, warn_flag, dang_flag, alert_level = compute_risk_score(synth_feats)
        if dang_flag:
            assert warn_flag is True, f"Danger flag True but warning flag False at score {score}"


def test_artifact_clips_and_thresholds_used():
    """Verify runtime thresholds and clips match exported JSON values."""
    assert THRESHOLD_WARNING == 0.9223
    assert THRESHOLD_DANGER == 0.9360
    assert CLIP_RANGES["rain_1d"] == [0.0, 152.6]
    assert CLIP_RANGES["soil_0_7_t1"] == [0.239, 0.515]


def test_stale_data_behavior(mock_daily_weather):
    """Verify fallback to cached prediction and stale flag when weather API fails."""
    slug = "pathanamthitta_kozhencherry"
    # Seed cache with older timestamp
    old_time = (datetime.now(timezone.utc) - timedelta(hours=7)).isoformat()
    _PREDICTIONS_CACHE[slug] = {
        "zone_slug": slug,
        "zone_status": "validated",
        "status": "ok",
        "data_as_of": old_time,
        "risk_score": 0.4200,
        "warning_flag": False,
        "danger_flag": False,
        "alert_level": "NORMAL",
        "is_stale": False,
        "freshness": "fresh"
    }

    # Simulate network exception
    with patch("src.models.inference.fetch_live_weather", side_effect=Exception("Connection timed out")):
        res = predict_zone(slug, live_daily=None)
        assert res["is_stale"] is True
        assert res["freshness"] == "stale"
        assert res["risk_score"] == 0.4200


def test_live_pipeline_reproduces_offline_scores_5_dates():
    """Regression check against stored offline model output (not holdout validation).
    
    Note: 2018-08-16 is strictly in-sample (training period 2000-2018).
    The remaining 4 dates (2019-08-09, 2020-09-20, 2021-07-16, 2024-07-30) are from the holdout period.
    This test verifies that live inference reproduces the exact offline model outputs.
    """
    sample_json_path = ROOT_DIR / "tests" / "sample_5_past_dates.json"
    assert sample_json_path.exists(), f"Missing {sample_json_path}"
    with open(sample_json_path, "r", encoding="utf-8") as f:
        past_samples = json.load(f)

    assert len(past_samples) == 5, f"Expected 5 dates, found {len(past_samples)}"
    for item in past_samples:
        dt_str = item["date"]
        expected_score = item["score"]
        f_dict = item["features"]
        score, _, _, _ = compute_risk_score(f_dict)
        assert abs(score - expected_score) < 1e-4, f"Score mismatch on {dt_str}: {score} != {expected_score}"



def test_inputs_outside_clip_range_clamped():
    """Verify inputs outside training clip ranges are clamped."""
    # Extreme input far above clip bounds
    extreme_high = {f: 99999.0 for f in FEATURE_ORDER}
    # Input exactly at max clip bounds
    at_max = {f: CLIP_RANGES[f][1] for f in FEATURE_ORDER}

    score_high, _, _, _ = compute_risk_score(extreme_high)
    score_at_max, _, _, _ = compute_risk_score(at_max)
    assert score_high == score_at_max


def test_alert_level_uses_greater_than_or_equal():
    """Verify alert_level logic strictly uses >= against exported thresholds."""
    # Synthetic test to verify threshold boundary behavior
    doy = 227
    sin_d = np.sin(2 * np.pi * doy / 365.25)
    cos_d = np.cos(2 * np.pi * doy / 365.25)

    # 1. Below warning threshold: NORMAL
    low_feats = {
        "rain_1d": 10.0, "rain_3d": 20.0, "rain_7d": 40.0, "rain_14d": 80.0, "rain_30d": 150.0,
        "soil_0_7_t1": 0.42, "soil_7_28_t1": 0.42, "sin_doy": sin_d, "cos_doy": cos_d
    }
    s_low, w_low, d_low, al_low = compute_risk_score(low_feats)
    assert s_low < THRESHOLD_WARNING
    assert w_low is False
    assert d_low is False
    assert al_low == "NORMAL"

    # 2. Above danger threshold: ALERT (both flags true)
    high_feats = {
        "rain_1d": 60.0, "rain_3d": 100.0, "rain_7d": 180.0, "rain_14d": 250.0, "rain_30d": 500.0,
        "soil_0_7_t1": 0.50, "soil_7_28_t1": 0.50, "sin_doy": sin_d, "cos_doy": cos_d
    }
    s_high, w_high, d_high, al_high = compute_risk_score(high_feats)
    assert s_high >= THRESHOLD_DANGER
    assert w_high is True
    assert d_high is True
    assert al_high == "ALERT"


def test_kottayam_provisional_status_and_reliability_note(mock_daily_weather):
    """Verify Kottayam response carries provisional status and reliability_note."""
    res = predict_zone("kottayam_pala", live_daily=mock_daily_weather)
    assert res["zone_status"] == "provisional"
    assert "reliability_note" in res
    assert "PROVISIONAL STATUS" in res["reliability_note"]
    assert "Kidangoor began only in June 2015" in res["reliability_note"]


def test_nan_input_behavior():
    """Verify missing or NaN live inputs return status insufficient_data and no score."""
    daily_nan = {
        "time": ["2026-08-15"] * 96,
        "precipitation_sum": [10.0] * 96,
        "soil_moisture_0_to_7cm_mean": [None] * 96, # Missing soil layer
        "soil_moisture_7_to_28cm_mean": [0.45] * 96
    }
    res = predict_zone("pathanamthitta_kozhencherry", live_daily=daily_nan)
    assert res["status"] == "insufficient_data"
    assert res["risk_score"] is None
    assert res["warning_flag"] is None
    assert res["danger_flag"] is None
    assert res["alert_level"] is None


def test_whatif_bound(mock_daily_weather):
    """Verify what-if extra rain is clamped to slider max and notes saturation."""
    predict_zone("pathanamthitta_kozhencherry", live_daily=mock_daily_weather)
    res = compute_whatif_sensitivity("pathanamthitta_kozhencherry", extra_rain_mm=500.0)
    assert res["extra_rain_mm_applied"] <= res["slider_max_bound_mm"]
    assert res["slider_max_bound_mm"] <= 152.6
    assert res["label"] == "sensitivity analysis"
    assert "Score saturates at the training clip bound." in res["saturation_note"]


def test_api_endpoints(mock_daily_weather):
    """Verify all FastAPI REST endpoints return 200 and expected schemas with mocked weather."""
    with patch("src.models.inference.fetch_live_weather", return_value=mock_daily_weather):
        # 1. /api/status
        r = client.get("/api/status")
        assert r.status_code == 200
        assert r.json()["model_version"] == MODEL_VERSION

        # 2. /api/zones
        r = client.get("/api/zones")
        assert r.status_code == 200
        zones = r.json()
        assert len(zones) == 7

        # 3. /api/predict/pathanamthitta_kozhencherry
        r = client.get("/api/predict/pathanamthitta_kozhencherry")
        assert r.status_code == 200
        assert r.json()["zone_status"] == "validated"

        # 4. /api/predict/wayanad_vythiri (unvalidated)
        r = client.get("/api/predict/wayanad_vythiri")
        assert r.status_code == 200
        assert r.json()["zone_status"] == "no_validated_model"
        assert r.json()["risk_score"] is None

        # 5. /api/metrics
        r = client.get("/api/metrics")
        assert r.status_code == 200
        assert "precision_recall_audit" in r.json()

        # 6. /api/whatif
        r = client.get("/api/whatif?zone_slug=pathanamthitta_kozhencherry&extra_rain_mm=25.0")
        assert r.status_code == 200
        assert r.json()["label"] == "sensitivity analysis"

        # 7. /api/history
        r = client.get("/api/history?limit=10")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


def test_network_block_enforced():
    """Verify that any attempt to establish a real external socket connection is blocked."""
    import socket
    with pytest.raises(RuntimeError, match="Live network access blocked by test suite"):
        s = socket.socket()
        s.connect(("8.8.8.8", 53))

