import sys, os, pathlib, json, hashlib
import numpy as np
import pandas as pd
import joblib

class ClippedLogisticRegression:
    pass

sys.modules['__main__'].ClippedLogisticRegression = ClippedLogisticRegression

MODELS_DIR = pathlib.Path("models")
joblib_path = MODELS_DIR / "final_single_risk_score_model.joblib"
with open(joblib_path, "rb") as f:
    joblib_sha256 = hashlib.sha256(f.read()).hexdigest()

model = joblib.load(joblib_path)
scaler = model.pipeline.named_steps["scaler"]
clf = model.pipeline.named_steps["clf"]

feature_order = [
    "rain_1d", "rain_3d", "rain_7d", "rain_14d", "rain_30d",
    "soil_0_7_t1", "soil_7_28_t1", "sin_doy", "cos_doy"
]

means = [float(x) for x in scaler.mean_]
scales = [float(x) for x in scaler.scale_]
std_coefs = [float(x) for x in clf.coef_[0]]
std_intercept = float(clf.intercept_[0])
min_vals = [float(x) for x in model.min_vals]
max_vals = [float(x) for x in model.max_vals]

# Full 64-bit raw representation
raw_coefs = [sc / s for sc, s in zip(std_coefs, scales)]
raw_intercept = std_intercept - sum(sc * (m / s) for sc, m, s in zip(std_coefs, means, scales))

# Exact regenerated thresholds
th_w_chosen = 0.9223
th_d_chosen = 0.9360

scorer_dict = {
    "metadata": {
        "model_name": "kerala_river_flood_risk_scorer",
        "version": "v2.0-single_score_on_warning",
        "training_period": "2000-01-01 to 2018-12-31",
        "model_family": "ClippedLogisticRegression",
        "class_weight": "balanced",
        "random_state": 42,
        "source_joblib_sha256": joblib_sha256,
        "score_type": "risk_score_uncalibrated",
        "score_range": [0.0, 1.0]
    },
    "feature_order": feature_order,
    "clip_ranges": {
        feat: [min_vals[i], max_vals[i]]
        for i, feat in enumerate(feature_order)
    },
    "standardizer": {
        "mean": means,
        "scale": scales
    },
    "classifier": {
        "standardized_coefficients": std_coefs,
        "standardized_intercept": std_intercept,
        "raw_coefficients": raw_coefs,
        "raw_intercept": raw_intercept
    },
    "thresholds": {
        "warning": th_w_chosen,
        "danger": th_d_chosen
    },
    "alert_rules": {
        "warning_flag": "risk_score >= thresholds.warning",
        "danger_flag": "risk_score >= thresholds.danger",
        "alert_level": "ALERT if (warning_flag or danger_flag) else NORMAL"
    }
}

json_path = MODELS_DIR / "scorer_v2.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(scorer_dict, f, indent=2)

print(f"Scorer exported with exact IEEE 754 precision to {json_path}")
