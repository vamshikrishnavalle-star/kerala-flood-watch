"""Kerala River Basin Flood Early Warning Operational Dashboard.

Connects to the FastAPI backend to display real-time flood risk predictions,
interactive sensitivity analyses, empirical evaluation audits, and historical logs.
Strict empirical governance: zero hardcoded metrics, zero forbidden statistical terms.
"""

import os
import pathlib
from typing import Any, Dict, List, Optional
import httpx
import pandas as pd
import streamlit as st
import pydeck as pdk

# API Base URL configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
LIMITATIONS_MD_PATH = ROOT_DIR / "docs" / "step0" / "limitations.md"


def get_api_data(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """Fetch JSON payload from backend API with robust timeout and error handling."""
    url = f"{API_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return None


def render_footer() -> None:
    """Render mandatory public disclaimer footer on every page."""
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #888888; font-size: 0.9rem;'>"
        "<strong>Illustrative, not official guidance</strong> | "
        "State and district disaster management authorities issue official alerts."
        "</p>",
        unsafe_allow_html=True
    )


def main() -> None:
    """Main Streamlit dashboard application entry point."""
    st.set_page_config(
        page_title="Kerala Flood Early Warning System",
        page_icon="🌊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Sidebar Navigation
    st.sidebar.title("🌊 Flood Early Warning")
    st.sidebar.caption("Operational Hydrological Decision Support System")

    nav_choice = st.sidebar.radio(
        "Navigation",
        ["1. Operations", "2. Sensitivity Analysis (What-If)", "3. Performance & Limitations", "4. Prediction History"],
        index=0
    )

    # -----------------------------------------------------------------------------
    # PAGE 1: OPERATIONS
    # -----------------------------------------------------------------------------
    if nav_choice == "1. Operations":
        st.title("Kerala River Basin Flood Operations")

        # 1. System Status & Freshness Banner
        status_data = get_api_data("/api/status")
        if not status_data:
            st.error(
                f"Backend API unavailable at {API_BASE_URL}. "
                "Please ensure the FastAPI service is running (`uvicorn src.api.main:app`). "
                "Cannot display predictions without active backend connection."
            )
            render_footer()
            st.stop()
            return

        model_ver = status_data.get("model_version", "unknown")
        last_refresh = status_data.get("last_refresh", "unknown")
        freshness = status_data.get("freshness_status", "fresh")

        col_stat1, col_stat2, col_stat3 = st.columns(3)
        col_stat1.metric("System Status", status_data.get("status", "unknown").upper())
        col_stat2.metric("Model Version", model_ver)
        col_stat3.metric("Data Freshness", freshness.upper())

        if freshness == "stale":
            st.warning(
                f"⚠️ STALE DATA WARNING: Weather data is older than 6 hours (last refreshed: {last_refresh}). "
                "Live predictions may not reflect recent rainfall."
            )

        # 2. Fetch Zones
        zones_list = get_api_data("/api/zones")
        if not zones_list:
            st.error("Failed to retrieve monitored zones from API.")
            render_footer()
            st.stop()
            return

        # Pre-fetch predictions for map display
        map_rows = []
        zone_preds = {}
        for z in zones_list:
            slug = z["slug"]
            pred = get_api_data(f"/api/predict/{slug}")
            zone_preds[slug] = pred

            v_status = z["zone_status"]
            lat = z["latitude"]
            lon = z["longitude"]
            name = z["name"]

            # Determine visual style and non-color text labels
            if v_status == "validated":
                status_text = "[VALIDATED MODEL]"
                color = [46, 139, 87, 200]  # Sea Green
            elif v_status == "provisional":
                status_text = "[PROVISIONAL MODEL]"
                color = [218, 165, 32, 200]  # Goldenrod
            else:
                status_text = "[NO VALIDATED MODEL - WEATHER ONLY]"
                color = [100, 110, 120, 180]  # Slate Gray

            score_text = "No score"
            alert_tag = ""
            if pred and pred.get("risk_score") is not None:
                r_score = pred["risk_score"]
                score_text = f"Risk Score: {r_score:.4f}"
                alert_tag = f"[{pred.get('alert_level', 'NORMAL')}]"
                if pred.get("alert_level") == "ALERT":
                    color = [220, 20, 60, 220]  # Crimson

            map_rows.append({
                "name": name,
                "slug": slug,
                "lat": lat,
                "lon": lon,
                "status_text": status_text,
                "score_text": score_text,
                "alert_tag": alert_tag,
                "color": color,
                "radius": 15000 if v_status != "no_validated_model" else 10000
            })

        # Map visualization
        st.subheader("Monitored River Basins")
        map_df = pd.DataFrame(map_rows)
        
        view_state = pdk.ViewState(latitude=10.0, longitude=76.6, zoom=7, pitch=0)
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_df,
            get_position=["lon", "lat"],
            get_color="color",
            get_radius="radius",
            pickable=True,
            auto_highlight=True,
        )
        r = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={"text": "{name}\nStatus: {status_text}\n{score_text} {alert_tag}"}
        )
        st.pydeck_chart(r)

        st.caption(
            "Map legend: Green = Validated Basin | Yellow/Amber = Provisional Basin | "
            "Gray = No Validated Model (Weather Monitoring Only) | Red = Active ALERT State"
        )

        # 3. Zone Detail View
        st.markdown("---")
        st.subheader("Basin Operational Detail")

        zone_options = {z["name"]: z["slug"] for z in zones_list}
        selected_name = st.selectbox("Select Monitored Basin:", list(zone_options.keys()))
        selected_slug = zone_options[selected_name]

        zone_info = next(z for z in zones_list if z["slug"] == selected_slug)
        pred_data = zone_preds.get(selected_slug) or get_api_data(f"/api/predict/{selected_slug}")

        if not pred_data:
            st.error(f"Prediction service unavailable for {selected_name}.")
            render_footer()
            st.stop()
            return

        v_status = zone_info["zone_status"]

        # Zone Status Badges & Specific Banners
        if v_status == "validated":
            st.success("✅ **VALIDATED MODEL**: Kallooppara hydrological gauge telemetry on Manimala River (2000–2024).")
        elif v_status == "provisional":
            st.warning("⚠️ **PROVISIONAL STATUS, LOW RELIABILITY**")
            rel_note = pred_data.get("reliability_note", "")
            if rel_note:
                st.info(rel_note)
        else:
            st.info("ℹ️ **NO VALIDATED MODEL**: Ground-truth hydrological gauge data is unvalidated for operational flood risk modeling in this basin. Weather monitoring only.")

        # Check for insufficient data
        if pred_data.get("status") == "insufficient_data":
            st.error("⚠️ **INSUFFICIENT DATA**: Missing or corrupt weather observations through yesterday (t-1). Risk score calculation suppressed.")
        elif v_status == "no_validated_model":
            st.markdown("### Weather Observation (Through Yesterday)")
            w_obs = pred_data.get("weather")
            if w_obs:
                w_col1, w_col2, w_col3, w_col4 = st.columns(4)
                w_col1.metric("Rain Yesterday (t-1)", f"{w_obs['rain_yesterday_mm']:.1f} mm")
                w_col2.metric("Rain 3-Day Sum", f"{w_obs['rain_3d_sum_mm']:.1f} mm")
                w_col3.metric("Rain 7-Day Sum", f"{w_obs['rain_7d_sum_mm']:.1f} mm")
                w_col4.metric("Topsoil Moisture (0-7cm)", f"{w_obs['soil_moisture_0_7cm']:.3f} m³/m³")
            else:
                st.write("Live weather observations currently loading or unavailable.")
            st.caption("No risk score, placeholder, or risk color is computed for unvalidated basins.")
        else:
            # Validated / Provisional with active score
            risk_score = pred_data.get("risk_score")
            alert_level = pred_data.get("alert_level", "NORMAL")
            warn_flag = pred_data.get("warning_flag", False)
            dang_flag = pred_data.get("danger_flag", False)

            # Single ALERT State Display
            score_col1, score_col2 = st.columns([1, 2])
            with score_col1:
                if alert_level == "ALERT":
                    st.error(f"🚨 **ALERT STATE**\n\n### Risk Score: {risk_score:.4f}")
                else:
                    st.success(f"🟢 **NORMAL STATE**\n\n### Risk Score: {risk_score:.4f}")

            with score_col2:
                st.markdown("#### Hydrological Trigger Hierarchy")
                st.markdown(
                    f"- **Warning Flag**: `{'TRIGGERED' if warn_flag else 'INACTIVE'}`  \n"
                    f"- **Danger Flag**: `{'TRIGGERED' if dang_flag else 'INACTIVE'}`"
                )
                st.caption(
                    "Warning and danger flags are internal model thresholds. "
                    "Danger strictly implies Warning. Single ALERT state is active if either threshold is reached."
                )

            # Day 0 vs Days 1-3 Temporal Separation
            st.markdown("#### Operational Time Horizon")
            st.markdown(
                "**Day 0 (Validated)**: *Risk today given rainfall through yesterday (t-1)*. "
                "Evaluated using causal observations strictly prior to today."
            )

            st.markdown("---")
            with st.container():
                st.markdown("##### 🔬 Experimental Outlook (Days 1–3)")
                st.caption("Status: **Experimental, not validated**. Numerical weather prediction lead-day projections.")
                outlook = pred_data.get("experimental_outlook_days_1_to_3", [])
                if outlook:
                    out_cols = st.columns(len(outlook))
                    for idx, o in enumerate(outlook):
                        with out_cols[idx]:
                            st.metric(
                                label=f"Day +{o.get('lead_day')} Outlook",
                                value=f"Score: {o.get('projected_risk_score', 0.0):.4f}",
                                delta=o.get("projected_alert_level")
                            )
                            st.caption(f"Projected Rain: {o.get('forecast_rainfall_mm', 0.0):.1f} mm")
                else:
                    st.write("Experimental outlook data unavailable.")

    # -----------------------------------------------------------------------------
    # PAGE 2: SENSITIVITY ANALYSIS (WHAT-IF)
    # -----------------------------------------------------------------------------
    elif nav_choice == "2. Sensitivity Analysis (What-If)":
        st.title("Sensitivity Analysis (What-If Simulation)")
        st.markdown(
            "*Sensitivity analysis: extra rainfall is added to yesterday's observation "
            "(rain_1d, rain_3d, rain_7d, rain_14d, and rain_30d all rise by that amount); "
            "soil moisture is unchanged.*"
        )

        zones_list = get_api_data("/api/zones")
        if not zones_list:
            st.error("Failed to connect to backend API.")
            render_footer()
            st.stop()
            return

        valid_zones = [z for z in zones_list if z["zone_status"] in ["validated", "provisional"]]
        zone_options = {z["name"]: z["slug"] for z in valid_zones}

        if not zone_options:
            st.info("No validated or provisional models available for what-if simulation.")
            render_footer()
            st.stop()
            return

        selected_name = st.selectbox("Select Basin for Simulation:", list(zone_options.keys()))
        selected_slug = zone_options[selected_name]

        # Query initial simulation to retrieve dynamic runtime slider bound
        init_sim = get_api_data("/api/whatif", params={"zone_slug": selected_slug, "extra_rain_mm": 0.0})
        if not init_sim or "slider_max_bound_mm" not in init_sim:
            st.error(f"What-if simulation service unavailable for {selected_name}.")
            render_footer()
            st.stop()
            return

        slider_bound = float(init_sim["slider_max_bound_mm"])
        base_score = float(init_sim.get("base_risk_score", 0.0))

        st.markdown(f"**Runtime Upper Bound for {selected_name}**: `{slider_bound:.1f} mm` *(min of basin daily max and training clip bound)*")

        extra_mm = st.slider(
            "Hypothetical Additional Rainfall Yesterday (mm):",
            min_value=0.0,
            max_value=slider_bound,
            value=0.0,
            step=1.0
        )

        sim_res = get_api_data("/api/whatif", params={"zone_slug": selected_slug, "extra_rain_mm": extra_mm})
        if sim_res:
            new_score = sim_res.get("simulated_risk_score", base_score)
            sim_alert = sim_res.get("simulated_alert_level", "NORMAL")
            sim_warn = sim_res.get("simulated_warning_flag", False)
            sim_dang = sim_res.get("simulated_danger_flag", False)

            c1, c2, c3 = st.columns(3)
            c1.metric("Base Risk Score", f"{base_score:.4f}")
            c2.metric("Simulated Risk Score", f"{new_score:.4f}", delta=f"{new_score - base_score:+.4f}")
            c3.metric("Simulated Alert Level", sim_alert)

            st.markdown(
                f"- **Simulated Warning Flag**: `{'TRIGGERED' if sim_warn else 'INACTIVE'}`  \n"
                f"- **Simulated Danger Flag**: `{'TRIGGERED' if sim_dang else 'INACTIVE'}`"
            )

            sat_note = sim_res.get("saturation_note")
            if sat_note:
                st.info(f"ℹ️ **Model Behavior**: {sat_note}")
        else:
            st.error("Failed to execute simulation query.")

    # -----------------------------------------------------------------------------
    # PAGE 3: MODEL PERFORMANCE AND LIMITATIONS
    # -----------------------------------------------------------------------------
    elif nav_choice == "3. Performance & Limitations":
        st.title("Model Performance Audit & Empirical Limitations")

        st.info(
            "**Methodological Note**: The 5-date test is a deterministic regression check against stored offline "
            "model output, not holdout validation. Date 2018-08-16 is strictly in-sample (training period 2000–2018)."
        )

        metrics_data = get_api_data("/api/metrics")
        if not metrics_data:
            st.error("Failed to load audit metrics from backend API.")
            render_footer()
            st.stop()
            return

        audit_records = metrics_data.get("precision_recall_audit", [])
        if audit_records:
            st.subheader("Authoritative Precision-Recall Audit")
            st.caption("Rule: Precision, event counts, alert episodes, and false-alarm days are displayed beside every recall figure.")

            audit_df = pd.DataFrame(audit_records)
            display_rows = []
            for _, r in audit_df.iterrows():
                c_ev = r.get("caught_events")
                t_ev = r.get("total_events")
                r_ep = r.get("tp_days")
                tot_ep = r.get("total_alert_episodes")
                
                ev_str = f"{c_ev} / {t_ev} ({r.get('event_rec', 0.0)*100:.1f}%)" if c_ev is not None and t_ev is not None else "N/A"
                ep_prec_str = f"{r.get('ep_prec', 0.0)*100:.2f}% ({tot_ep} episodes)" if tot_ep is not None else "N/A"
                fa_days_str = f"{r.get('fp_days', 0)} days"

                display_rows.append({
                    "Dataset Split": r.get("dataset"),
                    "Basin / Zone": r.get("zone"),
                    "Target Level": r.get("target"),
                    "Threshold": r.get("threshold"),
                    "Event Recall (Caught / Total)": ev_str,
                    "Day Recall": f"{r.get('day_rec', 0.0)*100:.1f}%",
                    "Day Precision": f"{r.get('day_prec', 0.0)*100:.2f}%",
                    "Episode Precision (Total Alerts)": ep_prec_str,
                    "False-Alarm Days": fa_days_str
                })

            st.dataframe(pd.DataFrame(display_rows), use_container_width=True)
            kott_recs = [
                r for r in audit_records
                if str(r.get("zone", "")).lower() == "kottayam" and str(r.get("target", "")).lower() == "danger"
            ]
            if kott_recs:
                kr = kott_recs[0]
                k_caught = kr.get("caught_events")
                k_tot_ev = kr.get("total_events")
                k_tot_ep = kr.get("total_alert_episodes")
                k_ep_prec = float(kr.get("ep_prec", 0.0)) * 100
                k_rec = float(kr.get("event_rec", 0.0)) * 100
                st.caption(
                    f"Note on Kottayam holdout: With {k_caught} true danger events ({k_rec:.1f}% caught of {k_tot_ev}), "
                    f"there are {k_tot_ep} total alert episodes ({k_caught} of {k_tot_ep} real, {k_ep_prec:.2f}% episode precision). "
                    "Counts must be evaluated alongside percentages."
                )
            else:
                st.caption("Counts must be evaluated alongside percentages across all basin evaluations.")

        # Annual Data Availability
        zone_year_records = metrics_data.get("dataset_per_zone_year", [])
        if zone_year_records:
            with st.expander("Annual Ground-Truth Data Availability (2000–2024)"):
                st.dataframe(pd.DataFrame(zone_year_records), use_container_width=True)

        # Render limitations markdown
        st.markdown("---")
        st.subheader("Empirical System Limitations (docs/step0/limitations.md)")
        if LIMITATIONS_MD_PATH.exists():
            with open(LIMITATIONS_MD_PATH, "r", encoding="utf-8") as f:
                limitations_text = f.read()
            st.markdown(limitations_text)
        else:
            st.warning("Limitations report markdown file not found on server disk.")

    # -----------------------------------------------------------------------------
    # PAGE 4: HISTORY
    # -----------------------------------------------------------------------------
    elif nav_choice == "4. Prediction History":
        st.title("Inference Logs & Prediction History")
        st.caption("Backed by SQLite logging database (data/processed/predictions_log.db)")

        zones_list = get_api_data("/api/zones")
        zone_options = {"All Basins": None}
        if zones_list:
            for z in zones_list:
                zone_options[z["name"]] = z["slug"]

        sel_zone_name = st.selectbox("Filter by Basin:", list(zone_options.keys()))
        sel_slug = zone_options[sel_zone_name]

        params = {"limit": 100}
        if sel_slug:
            params["zone_slug"] = sel_slug

        hist_data = get_api_data("/api/history", params=params)
        if hist_data is None:
            st.error("Failed to query prediction history from backend.")
            render_footer()
            st.stop()
            return

        if not hist_data:
            st.info("No prediction history recorded in database yet.")
        else:
            hist_df = pd.DataFrame(hist_data)
            st.subheader("Historical Log Table")
            st.dataframe(hist_df, use_container_width=True)

            # Plot score over time for validated/provisional entries
            scored_df = hist_df[hist_df["risk_score"].notna()].copy()
            if not scored_df.empty and "timestamp" in scored_df.columns:
                st.subheader("Risk Score Trajectory Over Time")
                scored_df["timestamp"] = pd.to_datetime(scored_df["timestamp"])
                chart_df = scored_df.sort_values("timestamp").set_index("timestamp")[["risk_score"]]
                st.line_chart(chart_df)

    # Render Global Footer on Every Page
    render_footer()


if __name__ == "__main__":
    main()
