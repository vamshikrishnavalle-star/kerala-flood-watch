"""Test suite for Phase 6 Streamlit Dashboard (src/dashboard/app.py).

All network calls are strictly mocked with zero live socket access.
Zero usage of forbidden vocabulary ('probability', 'calibrated').
"""

import os
import pathlib
import pytest
from unittest.mock import patch
import httpx
from streamlit.testing.v1 import AppTest

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
DASHBOARD_FILE = str(ROOT_DIR / "src" / "dashboard" / "app.py")


def test_no_forbidden_terminology():
    """Grep-style test: verify src/dashboard/ contains no occurrences of forbidden terms."""
    dashboard_dir = ROOT_DIR / "src" / "dashboard"
    py_files = list(dashboard_dir.glob("*.py"))
    assert len(py_files) > 0, "No python files found in src/dashboard/"

    forbidden = ["probability", "calibrated"]
    violations = []
    for f in py_files:
        content = f.read_text(encoding="utf-8").lower()
        for term in forbidden:
            if term in content:
                violations.append(f"{f.name}: contains '{term}'")

    assert not violations, f"Forbidden terminology found in dashboard code: {violations}"


class MockHttpxResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400 or self._data is None:
            raise httpx.HTTPStatusError("Mock error", request=None, response=None)


def get_mock_payload(endpoint: str, params=None):
    endpoint = endpoint.strip("/")
    if "api/status" in endpoint:
        return {
            "status": "healthy",
            "uptime_seconds": 120.0,
            "model_version": "v2.0-single_score_on_warning",
            "last_refresh": "2026-10-03T00:00:00Z",
            "freshness_status": "fresh"
        }
    elif "api/zones" in endpoint:
        return [
            {
                "slug": "pathanamthitta_kozhencherry",
                "name": "Kozhencherry (Manimala Basin)",
                "district": "Pathanamthitta",
                "latitude": 9.3364,
                "longitude": 76.6974,
                "river_basin": "Manimala",
                "hydrological_type": "riverine",
                "zone_status": "validated",
                "has_validated_model": True
            },
            {
                "slug": "kottayam_pala",
                "name": "Pala (Meenachil Basin)",
                "district": "Kottayam",
                "latitude": 9.71,
                "longitude": 76.68,
                "river_basin": "Meenachil",
                "hydrological_type": "midland_riverine",
                "zone_status": "provisional",
                "has_validated_model": True
            },
            {
                "slug": "wayanad_vythiri",
                "name": "Vythiri (Kabini Basin)",
                "district": "Wayanad",
                "latitude": 11.55,
                "longitude": 76.04,
                "river_basin": "Kabini",
                "hydrological_type": "highland_tributary",
                "zone_status": "no_validated_model",
                "has_validated_model": False
            }
        ]
    elif "pathanamthitta_kozhencherry" in endpoint and "predict" in endpoint:
        return {
            "zone_slug": "pathanamthitta_kozhencherry",
            "zone_status": "validated",
            "status": "ok",
            "risk_score": 0.4200,
            "warning_flag": False,
            "danger_flag": False,
            "alert_level": "NORMAL",
            "data_as_of": "2026-10-03T00:00:00Z",
            "model_version": "v2.0-single_score_on_warning",
            "experimental_outlook_days_1_to_3": [
                {"lead_day": 1, "forecast_rainfall_mm": 15.0, "projected_risk_score": 0.3500, "projected_alert_level": "NORMAL"},
                {"lead_day": 2, "forecast_rainfall_mm": 25.0, "projected_risk_score": 0.4800, "projected_alert_level": "NORMAL"},
                {"lead_day": 3, "forecast_rainfall_mm": 10.0, "projected_risk_score": 0.2800, "projected_alert_level": "NORMAL"}
            ]
        }
    elif "kottayam_pala" in endpoint and "predict" in endpoint:
        return {
            "zone_slug": "kottayam_pala",
            "zone_status": "provisional",
            "status": "ok",
            "risk_score": 0.7200,
            "warning_flag": False,
            "danger_flag": False,
            "alert_level": "NORMAL",
            "reliability_note": (
                "PROVISIONAL STATUS: Low sample reliability. Ground-truth CWC telemetry at Kidangoor began "
                "only in June 2015 (no data for 2000-2014). Holdout evaluation contains only 3 danger events "
                "(3 of 57 danger-alert episodes real in the test years) with an episode-level precision of 5.26% "
                "and 33.7 false-alarm days/year. Scores must be interpreted with caution."
            ),
            "data_as_of": "2026-10-03T00:00:00Z",
            "model_version": "v2.0-single_score_on_warning"
        }
    elif "wayanad_vythiri" in endpoint and "predict" in endpoint:
        return {
            "zone_slug": "wayanad_vythiri",
            "zone_status": "no_validated_model",
            "status": "unvalidated_zone",
            "risk_score": None,
            "warning_flag": None,
            "danger_flag": None,
            "alert_level": None,
            "weather": {
                "rain_yesterday_mm": 14.2,
                "rain_3d_sum_mm": 45.0,
                "rain_7d_sum_mm": 88.5,
                "soil_moisture_0_7cm": 0.412,
                "soil_moisture_7_28cm": 0.435
            },
            "data_as_of": "2026-10-03T00:00:00Z",
            "model_version": "v2.0-single_score_on_warning"
        }
    elif "api/whatif" in endpoint:
        extra_val = float(params.get("extra_rain_mm", 0.0)) if params else 0.0
        return {
            "zone_slug": "pathanamthitta_kozhencherry",
            "extra_rain_mm_requested": extra_val,
            "extra_rain_mm_applied": extra_val,
            "slider_max_bound_mm": 138.1,
            "base_risk_score": 0.0479,
            "simulated_risk_score": 0.2935 if extra_val > 0 else 0.0479,
            "simulated_warning_flag": False,
            "simulated_danger_flag": False,
            "simulated_alert_level": "NORMAL",
            "saturation_note": "Score saturates at the training clip bound."
        }
    elif "api/metrics" in endpoint:
        return {
            "precision_recall_audit": [
                {
                    "dataset": "HOLDOUT_2019_2024",
                    "zone": "Pathanamthitta",
                    "target": "danger",
                    "threshold": 0.9360,
                    "tp_days": 42,
                    "fp_days": 138,
                    "day_prec": 0.2333,
                    "day_rec": 0.7778,
                    "caught_events": 20,
                    "total_events": 23,
                    "event_rec": 0.8696,
                    "total_alert_episodes": 48,
                    "ep_prec": 0.4167
                },
                {
                    "dataset": "HOLDOUT_2019_2024",
                    "zone": "Kottayam",
                    "target": "danger",
                    "threshold": 0.9360,
                    "tp_days": 7,
                    "fp_days": 202,
                    "day_prec": 0.0335,
                    "day_rec": 1.0,
                    "caught_events": 3,
                    "total_events": 3,
                    "event_rec": 1.0,
                    "total_alert_episodes": 57,
                    "ep_prec": 0.0526
                }
            ],
            "dataset_per_zone_year": []
        }
    elif "api/history" in endpoint:
        return [
            {
                "id": 1,
                "timestamp": "2026-10-03T00:00:00Z",
                "zone_slug": "pathanamthitta_kozhencherry",
                "risk_score": 0.4200,
                "warning_flag": 0,
                "danger_flag": 0,
                "alert_level": "NORMAL",
                "is_stale": 0,
                "status": "ok"
            }
        ]
    return None


def mock_httpx_get(self, url, params=None, **kwargs):
    payload = get_mock_payload(url, params=params)
    if payload is None:
        return MockHttpxResponse(None, status_code=404)
    return MockHttpxResponse(payload, status_code=200)


def test_dashboard_operations_page():
    """Verify operations page: map labels, Day 0 vs 1-3, and footer disclaimer."""
    with patch.object(httpx.Client, "get", new=mock_httpx_get):
        at = AppTest.from_file(DASHBOARD_FILE).run(timeout=20)

    assert not at.exception
    # Verify page title and header
    assert any("Kerala River Basin Flood Operations" in str(t.value) for t in at.title)
    # Verify footer is present
    assert any("Illustrative, not official guidance" in str(m.value) for m in at.markdown)
    # Verify temporal split labels
    assert any("risk today given rainfall through yesterday" in str(m.value).lower() for m in at.markdown)
    assert any("experimental, not validated" in str(c.value).lower() for c in at.caption)


def test_dashboard_unvalidated_zone_never_renders_score():
    """Verify selecting an unvalidated zone shows weather only and zero risk scores."""
    with patch.object(httpx.Client, "get", new=mock_httpx_get):
        at = AppTest.from_file(DASHBOARD_FILE).run(timeout=20)
        # Select Vythiri (unvalidated zone)
        at.selectbox[0].select("Vythiri (Kabini Basin)").run(timeout=20)

    assert not at.exception
    # Assert info banner shows 'NO VALIDATED MODEL'
    assert any("NO VALIDATED MODEL" in str(i.value) for i in at.info)
    # Assert metric displays weather, not risk score
    metric_labels = [str(m.label).lower() for m in at.metric]
    assert any("rain yesterday" in l for l in metric_labels)
    assert not any("risk score" in l for l in metric_labels)


def test_dashboard_kottayam_banner_with_counts():
    """Verify Kottayam displays provisional status and exact episode counts from API."""
    with patch.object(httpx.Client, "get", new=mock_httpx_get):
        at = AppTest.from_file(DASHBOARD_FILE).run(timeout=20)
        at.selectbox[0].select("Pala (Meenachil Basin)").run(timeout=20)

    assert not at.exception
    # Assert provisional warning banner
    assert any("PROVISIONAL STATUS, LOW RELIABILITY" in str(w.value) for w in at.warning)
    # Assert dynamic episode counts in info box
    assert any("3 of 57 danger-alert episodes" in str(i.value) for i in at.info)


def test_dashboard_insufficient_data():
    """Verify insufficient_data status suppresses score and displays warning."""
    def _mock_insufficient_get(self, url, params=None, **kwargs):
        if "api/status" in url:
            return MockHttpxResponse({"status": "healthy", "model_version": "v2.0", "freshness_status": "fresh"})
        if "api/zones" in url:
            return MockHttpxResponse([{"slug": "pathanamthitta_kozhencherry", "name": "Kozhencherry", "zone_status": "validated", "latitude": 9.33, "longitude": 76.69}])
        if "predict" in url:
            return MockHttpxResponse({
                "zone_slug": "pathanamthitta_kozhencherry",
                "zone_status": "validated",
                "status": "insufficient_data",
                "risk_score": None,
                "alert_level": None
            })
        return MockHttpxResponse(None, status_code=404)

    with patch.object(httpx.Client, "get", new=_mock_insufficient_get):
        at = AppTest.from_file(DASHBOARD_FILE).run(timeout=20)

    assert not at.exception
    assert any("INSUFFICIENT DATA" in str(e.value) for e in at.error)
    # Ensure no risk score metric is rendered
    assert not any("risk score" in str(m.label).lower() for m in at.metric)


def test_dashboard_whatif_page():
    """Verify what-if sensitivity analysis page binds slider max to runtime API bound."""
    with patch.object(httpx.Client, "get", new=mock_httpx_get):
        at = AppTest.from_file(DASHBOARD_FILE).run(timeout=20)
        at.sidebar.radio[0].set_value("2. Sensitivity Analysis (What-If)").run(timeout=20)

    assert not at.exception
    assert any("Sensitivity Analysis" in str(t.value) for t in at.title)
    # Slider max must equal the runtime API bound 138.1 mm
    assert len(at.slider) > 0
    assert at.slider[0].max == 138.1
    # Check saturation note is rendered
    assert any("Score saturates at the training clip bound." in str(i.value) for i in at.info)


def test_dashboard_performance_page():
    """Verify performance page renders audit table with precision beside recall and limitations."""
    with patch.object(httpx.Client, "get", new=mock_httpx_get):
        at = AppTest.from_file(DASHBOARD_FILE).run(timeout=20)
        at.sidebar.radio[0].set_value("3. Performance & Limitations").run(timeout=20)

    assert not at.exception
    assert any("Model Performance Audit" in str(t.value) for t in at.title)
    # Regression test notice must be rendered
    assert any("5-date test is a deterministic regression check" in str(i.value) for i in at.info)
    assert any("2018-08-16 is strictly in-sample" in str(i.value) for i in at.info)


def test_dashboard_api_failure_displays_error():
    """Verify clear error message is shown with zero default numbers when API fails."""
    def _mock_fail(self, url, params=None, **kwargs):
        raise httpx.ConnectError("Connection refused")

    with patch.object(httpx.Client, "get", new=_mock_fail):
        at = AppTest.from_file(DASHBOARD_FILE).run(timeout=20)

    assert not at.exception
    # Assert clear error message
    assert any("Backend API unavailable" in str(e.value) for e in at.error)
    # Assert zero metrics are rendered
    assert len(at.metric) == 0
