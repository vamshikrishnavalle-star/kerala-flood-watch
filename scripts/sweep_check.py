import sys, os, pathlib
import numpy as np
import pandas as pd
import joblib
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

# Register ClippedLogisticRegression for unpickling
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

# Load artifact
model_path = pathlib.Path("models/final_single_risk_score_model.joblib")
model = joblib.load(model_path)

scaler = model.pipeline.named_steps["scaler"]
clf = model.pipeline.named_steps["clf"]

feature_names = [
    "rain_1d", "rain_3d", "rain_7d", "rain_14d", "rain_30d",
    "soil_0_7_t1", "soil_7_28_t1", "sin_doy", "cos_doy"
]

means = scaler.mean_
scales = scaler.scale_
std_coefs = clf.coef_[0]
std_intercept = clf.intercept_[0]
min_vals = model.min_vals
max_vals = model.max_vals

raw_coefs = std_coefs / scales
raw_intercept = std_intercept - np.sum(std_coefs * (means / scales))

# 1. Output Coefficient Table & Raw Intercept
coef_df = pd.DataFrame({
    "feature": feature_names,
    "mean": means,
    "scale": scales,
    "clip_min": min_vals,
    "clip_max": max_vals,
    "std_coef": std_coefs,
    "raw_coef": raw_coefs,
    "direction": ["Increasing" if c > 0 else "Decreasing (NEGATIVE)" for c in std_coefs]
})

print("=" * 80)
print("1. MODEL COEFFICIENTS & RAW RECONCILIATION")
print("=" * 80)
print(coef_df.to_string(index=False))
print(f"\nStandardized Intercept: {std_intercept:.6f}")
print(f"Calculated Raw Intercept: {raw_intercept:.6f}")
print(f"Formula: beta0_raw = beta0_std - sum(beta_std * mean / scale)")
print(f"       = {std_intercept:.4f} - ({np.sum(std_coefs * (means / scales)):.4f}) = {raw_intercept:.4f}")

coef_df.to_csv(out_dir / "reconciled_coefficients.csv", index=False)

with open(out_dir / "raw_intercept_explanation.txt", "w") as f:
    f.write(f"""Raw Intercept Mathematical Derivation:
Standardized Intercept (beta0_std): {std_intercept:.6f}
Sum of (beta_std * mu / sigma): {np.sum(std_coefs * (means / scales)):.6f}
Calculated Raw Intercept (beta0_raw): {raw_intercept:.6f}

Formula:
logit = beta0_std + sum(beta_std * (X_clipped - mu) / sigma)
      = [beta0_std - sum(beta_std * mu / sigma)] + sum((beta_std / sigma) * X_clipped)
      = beta0_raw + sum(beta_raw * X_clipped)

Negative Coefficients Disclosed:
1. rain_14d: beta_std = {std_coefs[3]:.4f} (collinear with rain_3d, rain_7d, rain_30d)
2. soil_0_7_t1: beta_std = {std_coefs[5]:.4f} (collinear with soil_7_28_t1 which has beta_std = +{std_coefs[6]:.4f})
""")

# 2. Synthetic Sweeps
print("\n" + "=" * 80)
print("2. SYNTHETIC INPUT SWEEPS & LOGIT DECOMPOSITIONS")
print("=" * 80)

# Day of year 227 (August 15): sin_doy = sin(2*pi*227/365.25), cos_doy = cos(2*pi*227/365.25)
doy = 227
sin_d = np.sin(2 * np.pi * doy / 365.25)
cos_d = np.cos(2 * np.pi * doy / 365.25)

# A. Sweep Rainfall with Soil = 0.42
rain_sweep_records = []
decomp_rows = []

for r in [0, 25, 50, 75, 100, 125, 150]:
    raw_vec = np.array([r, 1.5 * r, 2.5 * r, 4.0 * r, 8.0 * r, 0.42, 0.42, sin_d, cos_d])
    clip_vec = np.clip(raw_vec, min_vals, max_vals)
    z_vec = (clip_vec - means) / scales
    contribs = z_vec * std_coefs
    total_logit = std_intercept + np.sum(contribs)
    score = 1.0 / (1.0 + np.exp(-total_logit))
    
    # Model's predict_proba
    pred_score = model.predict_proba([raw_vec])[0, 1]
    
    row_dict = {
        "rain_1d": r, "soil": 0.42,
        "total_logit": round(total_logit, 4),
        "score_manual": round(score, 4),
        "score_predict_proba": round(pred_score, 4)
    }
    for fn, cb in zip(feature_names, contribs):
        row_dict[f"contrib_{fn}"] = round(cb, 4)
    decomp_rows.append(row_dict)
    
    print(f"Rain {r:3d} mm, Soil 0.42 -> Logit: {total_logit:6.2f} | Score: {pred_score:.4f}")

decomp_df = pd.DataFrame(decomp_rows)
decomp_df.to_csv(out_dir / "sweep_rainfall_decomposition.csv", index=False)

# B. Sweep Soil Moisture with 0 mm Rain
print("\nSoil Moisture Sweep with 0 mm Rain (Checking Sensitivity across Training Range):")
soil_rows = []
for s in [0.05, 0.118, 0.239, 0.30, 0.384, 0.434, 0.48, 0.515, 0.60]:
    raw_vec = np.array([0.0, 0.0, 0.0, 0.0, 0.0, s, s, sin_d, cos_d])
    clip_vec = np.clip(raw_vec, min_vals, max_vals)
    z_vec = (clip_vec - means) / scales
    contribs = z_vec * std_coefs
    total_logit = std_intercept + np.sum(contribs)
    pred_score = model.predict_proba([raw_vec])[0, 1]
    
    s_dict = {
        "input_soil": s,
        "clipped_soil_0_7": round(clip_vec[5], 4),
        "clipped_soil_7_28": round(clip_vec[6], 4),
        "total_logit": round(total_logit, 4),
        "risk_score": round(pred_score, 4)
    }
    for fn, cb in zip(feature_names, contribs):
        s_dict[f"contrib_{fn}"] = round(cb, 4)
    soil_rows.append(s_dict)
    print(f"Soil input: {s:5.3f} (clipped: 0-7cm={clip_vec[5]:.3f}, 7-28cm={clip_vec[6]:.3f}) -> Logit: {total_logit:6.2f} | Score: {pred_score:.4f}")

soil_df = pd.DataFrame(soil_rows)
soil_df.to_csv(out_dir / "sweep_soil_sensitivity.csv", index=False)

print("\nSaved sweep results to docs/step0/.")
