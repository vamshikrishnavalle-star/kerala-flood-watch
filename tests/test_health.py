"""Smoke test for the API health check endpoint."""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health_check():
    """Verify that /api/health responds with status 200 and healthy status payload."""
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["service"] == "disaster-prediction-api"
    assert "timestamp" in payload
