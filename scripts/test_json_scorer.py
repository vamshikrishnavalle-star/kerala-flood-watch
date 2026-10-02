import sys, os, pathlib, json
import numpy as np
import pandas as pd
import joblib
from sklearn.base import BaseEstimator, ClassifierMixin

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

PROCESSED_DIR = pathlib.Path("data/processed")
RAW_DIR = pathlib.Path("data/raw")
MODELS_DIR = pathlib.Path("models")
out_dir = pathlib.Path("docs/step0")

# 1. Load JSON Scorer
json_path = MODELS_DIR / "scorer_v2.json"
assert json_path.exists(), f"Missing {json_path}"
with open(json_path, "r", encoding="utf-8") as f:
    scorer_cfg = json.load(f)

# 2. Pure JSON Predictor Function (zero sklearn dependency)
def predict_with_json(X_df, cfg):
    fn = cfg["feature_order"]
    X = X_df[fn].to_numpy().astype(float)
    
    # Clip ranges
    mins = np.array([cfg["clip_ranges"][f][0] for f in fn])
    maxs = np.array([cfg["clip_ranges"][f][1] for f in fn])
    X_clip = np.clip(X, mins, maxs)
    
    # Standardize
    mu = np.array(cfg["standardizer"]["mean"])
    sigma = np.array(cfg["standardizer"]["scale"])
    Z = (X_clip - mu) / sigma
    
    # Standardized Logit
    beta = np.array(cfg["classifier"]["standardized_coefficients"])
    beta0 = cfg["classifier"]["standardized_intercept"]
    logit = beta0 + np.dot(Z, beta)
    
    scores = 1.0 / (1.0 + np.exp(-logit))
    
    th_w = cfg["thresholds"]["warning"]
    th_d = cfg["thresholds"]["danger"]
    
    warn_flags = (scores >= th_w).astype(int)
    dang_flags = (scores >= th_d).astype(int)
    alert_levels = np.where(dang_flags == 1, "DANGER", np.where(warn_flags == 1, "WARNING", "NORMAL"))
    
    return scores, warn_flags, dang_flags, alert_levels

# 3. Load Joblib model
joblib_model = joblib.load(MODELS_DIR / "final_single_risk_score_model.joblib")

# 4. Load full dataset with features
ds_df = pd.read_parquet(PROCESSED_DIR / "dataset.parquet")
ds_df["date"] = pd.to_datetime(ds_df["date"])

coords = {
    "Pathanamthitta": {"town": {"slug": "pathanamthitta_kozhencherry"}},
    "Kottayam": {"town": {"slug": "kottayam_pala"}}
}

weather_dfs = []
for z in ["Pathanamthitta", "Kottayam"]:
    slug = coords[z]["town"]["slug"]
    wdf = pd.read_csv(RAW_DIR / "historical" / f"{slug}.csv")
    wdf["date"] = pd.to_datetime(wdf["date"])
    p_s = wdf["precipitation_sum"].shift(1)
    
    col1 = "soil_moisture_0_7cm" if "soil_moisture_0_7cm" in wdf.columns else "soil_moisture_0_to_7cm_mean"
    col2 = "soil_moisture_7_28cm" if "soil_moisture_7_28cm" in wdf.columns else "soil_moisture_7_to_28cm_mean"
    
    fdf = pd.DataFrame({
        "date": wdf["date"],
        "zone": z,
        "rain_1d": p_s,
        "rain_3d": p_s.rolling(3, min_periods=3).sum(),
        "rain_7d": p_s.rolling(7, min_periods=7).sum(),
        "rain_14d": p_s.rolling(14, min_periods=14).sum(),
        "rain_30d": p_s.rolling(30, min_periods=30).sum(),
        "soil_0_7_t1": wdf[col1].shift(1),
        "soil_7_28_t1": wdf[col2].shift(1),
    })
    doy = fdf["date"].dt.dayofyear
    fdf["sin_doy"] = np.sin(2 * np.pi * doy / 365.25)
    fdf["cos_doy"] = np.cos(2 * np.pi * doy / 365.25)
    weather_dfs.append(fdf)

comb_w = pd.concat(weather_dfs, ignore_index=True)
full_df = ds_df[["date", "zone", "station", "label_danger", "label_warning", "regime"]].merge(comb_w, on=["zone", "date"], how="inner")
full_df = full_df.dropna(subset=["rain_30d", "soil_0_7_t1", "soil_7_28_t1"]).sort_values("date").reset_index(drop=True)

fn = scorer_cfg["feature_order"]

# 5. Run Parity Comparison
print("=" * 80)
print("PARITY TEST: JSON SCORER vs. JOBLIB ARTIFACT")
print("=" * 80)

# A. Full Dataset (12,129 rows)
scores_json, w_flags_json, d_flags_json, al_json = predict_with_json(full_df, scorer_cfg)
scores_joblib = joblib_model.predict_proba(full_df[fn].to_numpy())[:, 1]
w_flags_joblib = (scores_joblib >= scorer_cfg["thresholds"]["warning"]).astype(int)
d_flags_joblib = (scores_joblib >= scorer_cfg["thresholds"]["danger"]).astype(int)

diff_full = np.abs(scores_json - scores_joblib)
max_diff = np.max(diff_full)
mean_diff = np.mean(diff_full)
w_mismatch = np.sum(w_flags_json != w_flags_joblib)
d_mismatch = np.sum(d_flags_json != d_flags_joblib)

print(f"Dataset Evaluation (N = {len(full_df):,} rows):")
print(f"  - Maximum Absolute Difference : {max_diff:.2e}")
print(f"  - Mean Absolute Difference    : {mean_diff:.2e}")
print(f"  - Warning Flag Mismatches     : {w_mismatch} / {len(full_df)}")
print(f"  - Danger Flag Mismatches      : {d_mismatch} / {len(full_df)}")

assert max_diff < 1e-9, f"Max difference exceeded 1e-9: {max_diff}"
assert w_mismatch == 0, f"Warning flag mismatch detected: {w_mismatch}"
assert d_mismatch == 0, f"Danger flag mismatch detected: {d_mismatch}"

# B. Holdout Test Set (2019-2024, N = 3,983 rows)
test_mask = full_df["date"] >= "2019-01-01"
test_max_diff = np.max(diff_full[test_mask])
print(f"\nHoldout Test Set Evaluation (2019-2024, N = {np.sum(test_mask):,} rows):")
print(f"  - Maximum Absolute Difference : {test_max_diff:.2e}")
print(f"  - Warning Flag Mismatches     : {np.sum(w_flags_json[test_mask] != w_flags_joblib[test_mask])}")
print(f"  - Danger Flag Mismatches      : {np.sum(d_flags_json[test_mask] != d_flags_joblib[test_mask])}")

assert test_max_diff < 1e-9

# C. Synthetic Extremes & Clamping Test
synth_data = pd.DataFrame([
    # Extreme low
    {f: -999.0 for f in fn},
    # Extreme high
    {f: 9999.0 for f in fn},
    # Normal case
    {"rain_1d": 50.0, "rain_3d": 100.0, "rain_7d": 150.0, "rain_14d": 200.0, "rain_30d": 300.0,
     "soil_0_7_t1": 0.42, "soil_7_28_t1": 0.42, "sin_doy": 0.0, "cos_doy": 1.0}
])
s_json, _, _, _ = predict_with_json(synth_data, scorer_cfg)
s_joblib = joblib_model.predict_proba(synth_data[fn].to_numpy())[:, 1]
synth_max_diff = np.max(np.abs(s_json - s_joblib))
print(f"\nSynthetic Extreme Boundary Checks:")
print(f"  - Synthetic Max Absolute Diff : {synth_max_diff:.2e}")
assert synth_max_diff < 1e-9

parity_report = f"""JSON Scorer Parity Verification Report
================================================================================
Source Joblib SHA256: {scorer_cfg['metadata']['source_joblib_sha256']}
JSON Scorer Path: models/scorer_v2.json

Parity Results across Full Dataset (N = {len(full_df):,} rows):
- Maximum Absolute Risk Score Difference: {max_diff:.2e} (< 1e-9 requirement PASSED)
- Mean Absolute Risk Score Difference: {mean_diff:.2e}
- Warning Flag Concordance: 100.00% (0 mismatches across {len(full_df)} rows)
- Danger Flag Concordance: 100.00% (0 mismatches across {len(full_df)} rows)

Holdout Test Period (2019-2024, N = {np.sum(test_mask):,} rows):
- Max Absolute Difference: {test_max_diff:.2e} (< 1e-9 requirement PASSED)
- Flag Concordance: 100.00%

Synthetic Boundary Parity:
- Max Absolute Difference on Extreme Out-of-Bounds Inputs: {synth_max_diff:.2e}

Conclusion:
The pure JSON scorer (models/scorer_v2.json) perfectly reproduces the joblib model 
to machine precision (< 1e-9) while eliminating all custom pickling class dependencies.
"""

(out_dir / "json_scorer_parity_test.txt").write_text(parity_report, encoding="utf-8")
print("\nSUCCESS: All parity tests passed to < 1e-9 tolerance!")
print("Saved report to docs/step0/json_scorer_parity_test.txt.")
