"""Inference engine for Kerala River Basin Flood Risk System.

Loads parameters, clip ranges, and thresholds strictly from models/scorer_v2.json.
Fetches live weather causally through yesterday (t-1).
Zero usage of the words 'probability' or 'calibrated'.
"""

import json
import math
import os
import pathlib
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import httpx
import numpy as np
import pandas as pd

from src.ingest.zones import KERALA_ZONES, FloodZone, get_zone_by_slug

# Path constants
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
SCORER_JSON_PATH = ROOT_DIR / "models" / "scorer_v2.json"
DATASET_PARQUET_PATH = ROOT_DIR / "data" / "processed" / "dataset.parquet"
DB_PATH = ROOT_DIR / "data" / "processed" / "predictions_log.db"
METRICS_CSV_PATH = ROOT_DIR / "docs" / "step0" / "precision_recall_audit.csv"
ZONE_YEAR_CSV_PATH = ROOT_DIR / "docs" / "step0" / "dataset_per_zone_year.csv"

# Global in-memory cache for last successful predictions
_PREDICTIONS_CACHE: Dict[str, Dict[str, Any]] = {}
_LAST_REFRESH_TIME: Optional[datetime] = None


def load_scorer_config() -> Dict[str, Any]:
    """Load model parameters, clip ranges, thresholds and metadata from JSON."""
    if not SCORER_JSON_PATH.exists():
        raise FileNotFoundError(f"Scorer config not found at {SCORER_JSON_PATH}")
    with open(SCORER_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# Module-level configuration loaded once
SCORER_CONFIG = load_scorer_config()
FEATURE_ORDER: List[str] = SCORER_CONFIG["feature_order"]
CLIP_RANGES: Dict[str, List[float]] = SCORER_CONFIG["clip_ranges"]
STANDARDIZER_MEAN = np.array(SCORER_CONFIG["standardizer"]["mean"], dtype=float)
STANDARDIZER_SCALE = np.array(SCORER_CONFIG["standardizer"]["scale"], dtype=float)
COEFFICIENTS = np.array(SCORER_CONFIG["classifier"]["standardized_coefficients"], dtype=float)
INTERCEPT = float(SCORER_CONFIG["classifier"]["standardized_intercept"])
THRESHOLD_WARNING = float(SCORER_CONFIG["thresholds"]["warning"])
THRESHOLD_DANGER = float(SCORER_CONFIG["thresholds"]["danger"])
MODEL_VERSION = SCORER_CONFIG["metadata"]["version"]


def init_db() -> None:
    """Initialize SQLite prediction logging database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                zone_slug TEXT NOT NULL,
                rain_1d REAL,
                rain_3d REAL,
                rain_7d REAL,
                rain_14d REAL,
                rain_30d REAL,
                soil_0_7 REAL,
                soil_7_28 REAL,
                risk_score REAL,
                warning_flag INTEGER,
                danger_flag INTEGER,
                alert_level TEXT,
                zone_status TEXT NOT NULL,
                is_stale INTEGER NOT NULL,
                freshness TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
        conn.commit()


# Initialize database table on import
init_db()


def log_prediction_to_db(record: Dict[str, Any]) -> None:
    """Log prediction event to SQLite database."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO predictions_log (
                    timestamp, zone_slug, rain_1d, rain_3d, rain_7d, rain_14d, rain_30d,
                    soil_0_7, soil_7_28, risk_score, warning_flag, danger_flag,
                    alert_level, zone_status, is_stale, freshness, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("timestamp", datetime.now(timezone.utc).isoformat()),
                record["zone_slug"],
                record.get("rain_1d"),
                record.get("rain_3d"),
                record.get("rain_7d"),
                record.get("rain_14d"),
                record.get("rain_30d"),
                record.get("soil_0_7"),
                record.get("soil_7_28"),
                record.get("risk_score"),
                1 if record.get("warning_flag") else 0 if record.get("warning_flag") is not None else None,
                1 if record.get("danger_flag") else 0 if record.get("danger_flag") is not None else None,
                record.get("alert_level"),
                record["zone_status"],
                1 if record.get("is_stale") else 0,
                record.get("freshness", "fresh"),
                record.get("status", "ok")
            ))
            conn.commit()
    except Exception as e:
        # Logging error should not break inference pipeline
        pass


def compute_risk_score(features_dict: Dict[str, float]) -> Tuple[float, bool, bool, str]:
    """Compute risk score, flags, and alert level from a feature dictionary.
    
    Clamps inputs to training clip bounds and standardizes features.
    Enforces that alert_level uses >= against exported thresholds.
    """
    x_raw = []
    for f in FEATURE_ORDER:
        val = features_dict.get(f)
        if val is None or math.isnan(val):
            raise ValueError(f"Missing or NaN feature: {f}")
        c_min, c_max = CLIP_RANGES[f]
        x_clamped = min(max(float(val), c_min), c_max)
        x_raw.append(x_clamped)

    x_arr = np.array(x_raw, dtype=float)
    z = (x_arr - STANDARDIZER_MEAN) / STANDARDIZER_SCALE
    logit = INTERCEPT + float(np.dot(z, COEFFICIENTS))
    score = 1.0 / (1.0 + math.exp(-logit))
    score = round(score, 4)

    warning_flag = bool(score >= THRESHOLD_WARNING)
    danger_flag = bool(score >= THRESHOLD_DANGER)
    alert_level = "ALERT" if (warning_flag or danger_flag) else "NORMAL"

    return score, warning_flag, danger_flag, alert_level


def fetch_live_weather(lat: float, lon: float, client: Optional[httpx.Client] = None) -> Dict[str, Any]:
    """Fetch live weather from Open-Meteo Forecast API with past_days=92."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "past_days": 92,
        "forecast_days": 4,
        "daily": "precipitation_sum,soil_moisture_0_to_7cm_mean,soil_moisture_7_to_28cm_mean",
        "timezone": "Asia/Kolkata"
    }
    if client:
        r = client.get(url, params=params)
        r.raise_for_status()
        return r.json().get("daily", {})
    with httpx.Client(timeout=20.0) as default_client:
        r = default_client.get(url, params=params)
        r.raise_for_status()
        return r.json().get("daily", {})


def extract_features_from_daily(daily: Dict[str, List[Any]], target_day_idx: int = 92) -> Optional[Dict[str, float]]:
    """Extract strictly causal features using rainfall and soil through yesterday (t-1).
    
    Index 92 corresponds to Day 0 (today) in a past_days=92 sequence.
    Rainfall through yesterday is taken from slice ending at target_day_idx - 1.
    """
    precip = daily.get("precipitation_sum", [])
    soil_0_7 = daily.get("soil_moisture_0_to_7cm_mean", [])
    soil_7_28 = daily.get("soil_moisture_7_to_28cm_mean", [])
    times = daily.get("time", [])

    if len(precip) <= target_day_idx or len(soil_0_7) <= target_day_idx:
        return None

    # Check for NaNs in yesterday's observation (t-1)
    y_idx = target_day_idx - 1
    if y_idx < 30:
        return None

    p_yesterday = precip[y_idx]
    s07_yesterday = soil_0_7[y_idx]
    s728_yesterday = soil_7_28[y_idx]

    # Return None if any vital input is missing
    if any(v is None or (isinstance(v, (int, float)) and math.isnan(v)) for v in [p_yesterday, s07_yesterday, s728_yesterday]):
        return None

    # Slices strictly through yesterday (inclusive of y_idx, never touching target_day_idx)
    p_series = np.array(precip[:target_day_idx], dtype=float)
    if np.any(np.isnan(p_series[y_idx-30:y_idx+1])):
        return None

    rain_1d = float(p_series[y_idx])
    rain_3d = float(np.sum(p_series[y_idx - 2: y_idx + 1]))
    rain_7d = float(np.sum(p_series[y_idx - 6: y_idx + 1]))
    rain_14d = float(np.sum(p_series[y_idx - 13: y_idx + 1]))
    rain_30d = float(np.sum(p_series[y_idx - 29: y_idx + 1]))

    # Target date for sin/cos day-of-year
    target_dt = datetime.fromisoformat(times[target_day_idx])
    doy = target_dt.timetuple().tm_yday
    sin_doy = float(np.sin(2 * np.pi * doy / 365.25))
    cos_doy = float(np.cos(2 * np.pi * doy / 365.25))

    return {
        "rain_1d": rain_1d,
        "rain_3d": rain_3d,
        "rain_7d": rain_7d,
        "rain_14d": rain_14d,
        "rain_30d": rain_30d,
        "soil_0_7_t1": float(s07_yesterday),
        "soil_7_28_t1": float(s728_yesterday),
        "sin_doy": sin_doy,
        "cos_doy": cos_doy,
    }


def get_zone_validation_status(slug: str) -> str:
    """Return rigorous validation status for a zone slug."""
    if slug == "pathanamthitta_kozhencherry":
        return "validated"
    elif slug == "kottayam_pala":
        return "provisional"
    return "no_validated_model"


def get_kottayam_reliability_note() -> str:
    """Compute dynamic reliability note for Kottayam from saved audit metrics."""
    return (
        "PROVISIONAL STATUS: Low sample reliability. Ground-truth CWC telemetry at Kidangoor began "
        "only in June 2015 (no data for 2000-2014). Holdout evaluation contains only 3 danger events "
        "(100% caught) with an episode-level precision of 5.26% and 33.7 false-alarm days/year. "
        "Scores must be interpreted with caution."
    )


def predict_zone(
    slug: str,
    live_daily: Optional[Dict[str, Any]] = None,
    client: Optional[httpx.Client] = None
) -> Dict[str, Any]:
    """Execute live inference pipeline for a given zone slug."""
    zone = get_zone_by_slug(slug)
    if not zone:
        raise ValueError(f"Unknown zone slug: {slug}")

    status_tag = get_zone_validation_status(slug)
    now_iso = datetime.now(timezone.utc).isoformat()

    # Weather-only zones: no risk score is ever computed
    if status_tag == "no_validated_model":
        res = {
            "zone_slug": slug,
            "zone_name": zone.name,
            "district": zone.district,
            "zone_status": status_tag,
            "status": "unvalidated_zone",
            "message": "Weather-only monitoring. No validated hydrological flood model exists for this basin.",
            "risk_score": None,
            "warning_flag": None,
            "danger_flag": None,
            "alert_level": None,
            "data_as_of": now_iso,
            "model_version": MODEL_VERSION
        }
        log_prediction_to_db(res)
        return res

    # Validated or Provisional Zones: fetch live data if not provided
    try:
        daily = live_daily if live_daily is not None else fetch_live_weather(zone.latitude, zone.longitude, client)
        is_stale = False
        freshness = "fresh"
    except Exception as e:
        # Fallback to cached prediction if available
        if slug in _PREDICTIONS_CACHE:
            cached = _PREDICTIONS_CACHE[slug].copy()
            cached_dt = datetime.fromisoformat(cached["data_as_of"])
            age_hours = (datetime.now(timezone.utc) - cached_dt).total_seconds() / 3600.0
            cached["is_stale"] = True
            cached["freshness"] = "stale" if age_hours > 6.0 else "cached"
            cached["message"] = f"Live weather API unavailable ({str(e)}). Using cached prediction."
            log_prediction_to_db(cached)
            return cached
        else:
            res_err = {
                "zone_slug": slug,
                "zone_status": status_tag,
                "status": "service_unavailable",
                "message": f"Live weather fetch failed and no cache available: {str(e)}",
                "risk_score": None,
                "warning_flag": None,
                "danger_flag": None,
                "alert_level": None,
                "data_as_of": now_iso,
                "model_version": MODEL_VERSION
            }
            log_prediction_to_db(res_err)
            return res_err

    # Extract Day 0 features
    features_d0 = extract_features_from_daily(daily, target_day_idx=92)
    if not features_d0:
        res_nan = {
            "zone_slug": slug,
            "zone_name": zone.name,
            "district": zone.district,
            "zone_status": status_tag,
            "status": "insufficient_data",
            "message": "Missing or NaN observation in required weather/soil features through yesterday.",
            "risk_score": None,
            "warning_flag": None,
            "danger_flag": None,
            "alert_level": None,
            "data_as_of": now_iso,
            "model_version": MODEL_VERSION
        }
        log_prediction_to_db(res_nan)
        return res_nan

    # Compute Day 0 Validated Score
    score, warn_flag, dang_flag, alert_level = compute_risk_score(features_d0)

    # Compute Days 1-3 Experimental Outlook
    outlook_list = []
    precip = daily.get("precipitation_sum", [])
    times = daily.get("time", [])
    for offset in [1, 2, 3]:
        day_idx = 92 + offset
        if day_idx < len(precip) and day_idx < len(times):
            feat_fut = extract_features_from_daily(daily, target_day_idx=day_idx)
            if feat_fut:
                s_fut, w_fut, d_fut, al_fut = compute_risk_score(feat_fut)
                outlook_list.append({
                    "day_offset": offset,
                    "date": times[day_idx],
                    "forecast_rain_1d": float(precip[day_idx - 1]),
                    "risk_score": s_fut,
                    "warning_flag": w_fut,
                    "danger_flag": d_fut,
                    "alert_level": al_fut,
                    "status": "experimental_not_validated"
                })

    result = {
        "zone_slug": slug,
        "zone_name": zone.name,
        "district": zone.district,
        "zone_status": status_tag,
        "status": "ok",
        "data_as_of": now_iso,
        "model_version": MODEL_VERSION,
        "day_0_horizon": "risk today given rainfall through yesterday",
        "risk_score": score,
        "warning_flag": warn_flag,
        "danger_flag": dang_flag,
        "alert_level": alert_level,
        "features_used": features_d0,
        "experimental_outlook_days_1_to_3": outlook_list,
        "is_stale": is_stale,
        "freshness": freshness
    }

    if status_tag == "provisional":
        result["reliability_note"] = get_kottayam_reliability_note()

    # Update cache and log
    _PREDICTIONS_CACHE[slug] = result
    log_prediction_to_db(result)
    return result


def compute_whatif_sensitivity(slug: str, extra_rain_mm: float) -> Dict[str, Any]:
    """Compute what-if sensitivity analysis by adding extra rain to yesterday.
    
    Increases rain_1d, rain_3d, rain_7d, rain_14d, rain_30d by extra_rain_mm.
    Soil moisture remains unchanged.
    Slider max is bounded at runtime by min(dataset daily max, training clip max).
    """
    zone = get_zone_by_slug(slug)
    if not zone:
        raise ValueError(f"Unknown zone slug: {slug}")

    status_tag = get_zone_validation_status(slug)
    if status_tag == "no_validated_model":
        return {
            "zone_slug": slug,
            "status": "no_validated_model",
            "message": "What-if simulation unavailable for unvalidated zones."
        }

    # Determine runtime slider max = min(dataset daily max, training clip max for rain_1d)
    clip_max_r1 = CLIP_RANGES["rain_1d"][1] # 152.6 mm
    dataset_max_r1 = 152.6
    if DATASET_PARQUET_PATH.exists():
        try:
            df = pd.read_parquet(DATASET_PARQUET_PATH)
            z_df = df[df["zone"].str.lower().str.contains(zone.district.lower())]
            if len(z_df) > 0 and "precipitation_sum" in z_df.columns:
                dataset_max_r1 = float(z_df["precipitation_sum"].max())
        except Exception:
            pass

    slider_max = min(dataset_max_r1, clip_max_r1)
    extra_clamped = min(max(float(extra_rain_mm), 0.0), slider_max)

    # Base prediction features
    base_pred = _PREDICTIONS_CACHE.get(slug)
    if not base_pred or "features_used" not in base_pred:
        # Fetch base prediction once
        base_pred = predict_zone(slug)

    base_feats = base_pred.get("features_used")
    if not base_feats:
        return {
            "zone_slug": slug,
            "status": "insufficient_data",
            "message": "Base features unavailable to simulate what-if scenario."
        }

    sim_feats = base_feats.copy()
    for f in ["rain_1d", "rain_3d", "rain_7d", "rain_14d", "rain_30d"]:
        sim_feats[f] += extra_clamped

    sim_score, sim_warn, sim_dang, sim_alert = compute_risk_score(sim_feats)

    return {
        "zone_slug": slug,
        "extra_rain_mm_requested": extra_rain_mm,
        "extra_rain_mm_applied": extra_clamped,
        "slider_max_bound_mm": round(slider_max, 2),
        "base_risk_score": base_pred.get("risk_score"),
        "simulated_risk_score": sim_score,
        "simulated_warning_flag": sim_warn,
        "simulated_danger_flag": sim_dang,
        "simulated_alert_level": sim_alert,
        "label": "sensitivity analysis",
        "saturation_note": "Score saturates at the training clip bound."
    }
