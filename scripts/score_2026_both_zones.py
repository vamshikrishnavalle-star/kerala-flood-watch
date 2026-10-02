import sys, os, pathlib, json
import numpy as np
import pandas as pd
import joblib
import httpx
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

class ClippedLogisticRegression(BaseEstimator, ClassifierMixin):
    def __init__(self, class_weight=None, random_state=42):
        self.class_weight = class_weight
        self.random_state = random_state
    def fit(self, X, y):
        return self
    def predict_proba(self, X):
        X_arr = np.asarray(X)
        X_clipped = np.clip(X_arr, self.min_vals, self.max_vals)
        return self.pipeline.predict_proba(X_clipped)

sys.modules['__main__'].ClippedLogisticRegression = ClippedLogisticRegression

out_dir = pathlib.Path("docs/step0")
out_dir.mkdir(parents=True, exist_ok=True)

model = joblib.load("models/final_single_risk_score_model.joblib")
feature_cols = ["rain_1d", "rain_3d", "rain_7d", "rain_14d", "rain_30d", "soil_0_7_t1", "soil_7_28_t1", "sin_doy", "cos_doy"]

th_w = 0.9223
th_d = 0.9360

coords = {
    "pathanamthitta_kozhencherry": {"lat": 9.3364, "lon": 76.6974, "zone": "Pathanamthitta"},
    "kottayam_pala": {"lat": 9.7100, "lon": 76.6800, "zone": "Kottayam"}
}

def get_2026_features(lat, lon):
    # Fetch from Open-Meteo archive/forecast for 2026
    url = "https://archive-api.open-meteo.com/v1/archive"
    with httpx.Client(timeout=60.0) as client:
        r = client.get(url, params={
            "latitude": lat, "longitude": lon,
            "start_date": "2026-05-01", "end_date": "2026-10-02",
            "daily": "precipitation_sum,soil_moisture_0_to_7cm_mean,soil_moisture_7_to_28cm_mean",
            "timezone": "Asia/Kolkata"
        })
        daily = r.json().get("daily", {})
    df = pd.DataFrame(daily).rename(columns={"time": "date"})
    p_s = df["precipitation_sum"].shift(1)
    df["rain_1d"] = p_s
    df["rain_3d"] = p_s.rolling(3, min_periods=3).sum()
    df["rain_7d"] = p_s.rolling(7, min_periods=7).sum()
    df["rain_14d"] = p_s.rolling(14, min_periods=14).sum()
    df["rain_30d"] = p_s.rolling(30, min_periods=30).sum()
    df["soil_0_7_t1"] = df["soil_moisture_0_to_7cm_mean"].shift(1)
    df["soil_7_28_t1"] = df["soil_moisture_7_to_28cm_mean"].shift(1)
    doy = pd.to_datetime(df["date"]).dt.dayofyear
    df["sin_doy"] = np.sin(2 * np.pi * doy / 365.25)
    df["cos_doy"] = np.cos(2 * np.pi * doy / 365.25)
    
    # Filter 2026-06-01 to 2026-10-02
    df = df[(df["date"] >= "2026-06-01") & (df["date"] <= "2026-10-02")].copy().reset_index(drop=True)
    return df

counts_summary = []

for slug, c_info in coords.items():
    csv_file = out_dir / f"alerts_2026_{slug}.csv"
    try:
        df_feat = get_2026_features(c_info["lat"], c_info["lon"])
        X = df_feat[feature_cols].to_numpy()
        scores = model.predict_proba(X)[:, 1]
        df_feat["risk_score"] = np.round(scores, 4)
        df_feat["alert_warning"] = (scores >= th_w).astype(int)
        df_feat["alert_danger"] = (scores >= th_d).astype(int)
        df_feat["alert_level"] = np.where(scores >= th_d, "DANGER", np.where(scores >= th_w, "WARNING", "NORMAL"))
        
        save_cols = ["date", "risk_score", "alert_level", "alert_warning", "alert_danger"] + feature_cols
        df_feat[save_cols].to_csv(csv_file, index=False)
        
        n_days = len(df_feat)
        n_warn = int((df_feat["alert_level"] == "WARNING").sum())
        n_dang = int((df_feat["alert_level"] == "DANGER").sum())
        n_norm = int((df_feat["alert_level"] == "NORMAL").sum())
        
        counts_summary.append({
            "zone": c_info["zone"], "slug": slug, "total_days": n_days,
            "normal_days": n_norm, "warning_days": n_warn, "danger_days": n_dang,
            "danger_alert_dates": df_feat[df_feat["alert_level"] == "DANGER"]["date"].tolist(),
            "warning_alert_dates": df_feat[df_feat["alert_level"] == "WARNING"]["date"].tolist()
        })
        print(f"Scored {slug}: {n_days} days. Danger={n_dang}, Warning={n_warn}, Normal={n_norm}")
    except Exception as e:
        print(f"Error fetching/scoring {slug}: {e}")

with open(out_dir / "alerts_2026_summary.json", "w") as f:
    json.dump(counts_summary, f, indent=2)

print("2026 re-scoring complete.")
