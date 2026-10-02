"""FastAPI application entrypoint."""

from datetime import datetime, timezone
from fastapi import FastAPI
from src.config import settings

app = FastAPI(
    title="AI-Powered Disaster Prediction and Emergency Response System",
    description="Flood prediction and real-time emergency response platform",
    version="0.1.0",
)


@app.get("/api/health")
def health_check():
    """Health check endpoint verifying API readiness and configuration."""
    return {
        "status": "healthy",
        "service": "disaster-prediction-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "region": settings.REGION_NAME,
    }
