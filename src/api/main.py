"""FastAPI backend application for Kerala River Basin Flood Risk System.

Provides REST API endpoints for zone predictions, metrics, what-if simulation, and history.
Strictly zero usage of the words 'probability' or 'calibrated'.
"""

import os
import pathlib
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd

from src.ingest.zones import KERALA_ZONES, get_all_zones, get_zone_by_slug
from src.models.inference import (
    MODEL_VERSION,
    DB_PATH,
    METRICS_CSV_PATH,
    ZONE_YEAR_CSV_PATH,
    predict_zone,
    compute_whatif_sensitivity,
    get_zone_validation_status,
    _LAST_REFRESH_TIME
)

# Start time tracking for uptime
APP_START_TIME = datetime.now(timezone.utc)
# Background Scheduler configuration (default True, disabled in unit tests via ENABLE_SCHEDULER=false)
ENABLE_SCHEDULER: bool = os.environ.get("ENABLE_SCHEDULER", "true").lower() in ("true", "1", "yes")
scheduler = BackgroundScheduler()


def refresh_predictions_job() -> None:
    """Scheduled background job to refresh live predictions every 45 minutes."""
    global _LAST_REFRESH_TIME
    _LAST_REFRESH_TIME = datetime.now(timezone.utc)
    for slug in ["pathanamthitta_kozhencherry", "kottayam_pala"]:
        try:
            predict_zone(slug)
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for background scheduler."""
    if ENABLE_SCHEDULER:
        try:
            refresh_predictions_job()
        except Exception:
            pass
        scheduler.add_job(refresh_predictions_job, "interval", minutes=45, id="weather_refresh")
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown()


app = FastAPI(
    title="Kerala Flood Early Warning System API",
    description="Operational flood risk early warning API for Kerala river basins.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def get_health_check() -> Dict[str, Any]:
    """Health check endpoint for smoke testing and container liveness probes."""
    return {
        "status": "healthy",
        "service": "disaster-prediction-api",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/status")
def get_system_status() -> Dict[str, Any]:
    """Return API health, uptime, model version, and data freshness."""
    now = datetime.now(timezone.utc)
    uptime_sec = (now - APP_START_TIME).total_seconds()
    
    last_refresh_iso = _LAST_REFRESH_TIME.isoformat() if _LAST_REFRESH_TIME else now.isoformat()
    freshness = "fresh"
    if _LAST_REFRESH_TIME:
        age_hours = (now - _LAST_REFRESH_TIME).total_seconds() / 3600.0
        if age_hours > 6.0:
            freshness = "stale"

    return {
        "status": "healthy",
        "uptime_seconds": round(uptime_sec, 1),
        "model_version": MODEL_VERSION,
        "last_refresh": last_refresh_iso,
        "freshness_status": freshness
    }


@app.get("/api/zones")
def list_zones() -> List[Dict[str, Any]]:
    """Return all 7 monitored Kerala flood zones with metadata and validation status."""
    result = []
    for zone in get_all_zones():
        val_status = get_zone_validation_status(zone.slug)
        result.append({
            "slug": zone.slug,
            "name": zone.name,
            "district": zone.district,
            "latitude": zone.latitude,
            "longitude": zone.longitude,
            "river_basin": zone.river_basin,
            "hydrological_type": zone.hydrological_type,
            "zone_status": val_status,
            "has_validated_model": val_status in ["validated", "provisional"]
        })
    return result


@app.get("/api/predict/{zone_slug}")
def get_zone_prediction(zone_slug: str) -> Dict[str, Any]:
    """Retrieve operational Day 0 flood risk prediction and Days 1-3 experimental outlook."""
    zone = get_zone_by_slug(zone_slug)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_slug}' not found.")
    return predict_zone(zone_slug)


@app.get("/api/metrics")
def get_model_metrics() -> Dict[str, Any]:
    """Return out-of-fold and holdout test metrics read dynamically from saved Step 0 CSVs."""
    if not METRICS_CSV_PATH.exists():
        raise HTTPException(status_code=500, detail="Metrics audit file missing from docs/step0/.")

    metrics_df = pd.read_csv(METRICS_CSV_PATH)
    
    # Load dataset per zone year table
    zone_year_records = []
    if ZONE_YEAR_CSV_PATH.exists():
        zone_year_df = pd.read_csv(ZONE_YEAR_CSV_PATH)
        zone_year_records = zone_year_df.to_dict(orient="records")

    return {
        "model_version": MODEL_VERSION,
        "source_audit_file": "docs/step0/precision_recall_audit.csv",
        "precision_recall_audit": metrics_df.to_dict(orient="records"),
        "dataset_per_zone_year": zone_year_records
    }


@app.get("/api/whatif")
def get_whatif_simulation(
    zone_slug: str = Query(..., description="Zone slug to simulate"),
    extra_rain_mm: float = Query(..., ge=0.0, description="Additional rainfall in mm added to yesterday")
) -> Dict[str, Any]:
    """Simulate sensitivity to additional rainfall added to yesterday's observation."""
    zone = get_zone_by_slug(zone_slug)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_slug}' not found.")
    return compute_whatif_sensitivity(zone_slug, extra_rain_mm)


@app.get("/api/history")
def get_prediction_history(
    zone_slug: Optional[str] = Query(None, description="Optional zone slug filter"),
    limit: int = Query(50, ge=1, le=500, description="Maximum records to return")
) -> List[Dict[str, Any]]:
    """Retrieve logged prediction history from SQLite database."""
    if not DB_PATH.exists():
        return []

    query = "SELECT * FROM predictions_log"
    params: List[Any] = []
    if zone_slug:
        query += " WHERE zone_slug = ?"
        params.append(zone_slug)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        rows = cursor.execute(query, params).fetchall()
        return [dict(r) for r in rows]
