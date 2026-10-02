import sys, os, json, glob
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LogisticRegression

# 0. Register class for joblib unpickling
class ClippedLogisticRegression(BaseEstimator, ClassifierMixin):
    def __init__(self, clip_ranges=None, **kwargs):
        self.clip_ranges = clip_ranges
        self.kwargs = kwargs
        self.clf = LogisticRegression(**kwargs)
    def fit(self, X, y):
        return self
    def predict_proba(self, X):
        return self.clf.predict_proba(X)

sys.modules['__main__'].ClippedLogisticRegression = ClippedLogisticRegression

out_dir = Path("docs/step0")
out_dir.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# 1. PER-ZONE DATASET AUDIT
# -----------------------------------------------------------------------------
print("=" * 80)
print("1. PER-ZONE DATASET AUDIT (data/processed/dataset.parquet)")
print("=" * 80)
df = pd.read_parquet("data/processed/dataset.parquet")
df["date"] = pd.to_datetime(df["date"])
df["year"] = df["date"].dt.year

print(f"Total Rows in dataset: {len(df)}")
print(f"Date Span: {df['date'].min().date()} to {df['date'].max().date()}")
print(f"Stations present: {df[['zone', 'station']].drop_duplicates().to_dict('records')}\n")

zone_summary = []
for (z, yr), g in df.groupby(["zone", "year"]):
    n_rows = len(g)
    warn_pos = int(g["label_warning"].sum())
    dang_pos = int(g["label_danger"].sum())
    min_d, max_d = g["date"].min(), g["date"].max()
    expected_days = (max_d - min_d).days + 1
    zone_summary.append({
        "zone": z, "year": yr, "rows": n_rows,
        "warning_pos": warn_pos, "danger_pos": dang_pos,
        "min_date": str(min_d.date()), "max_date": str(max_d.date()),
        "missing_days_in_span": expected_days - n_rows
    })

sum_df = pd.DataFrame(zone_summary)
sum_df.to_csv(out_dir / "dataset_per_zone_year.csv", index=False)

# Display table
piv = sum_df.pivot(index="year", columns="zone", values=["rows", "warning_pos", "danger_pos", "missing_days_in_span"])
print("Per-Zone Year Summary:")
print(piv.to_string())

# Verification of Kottayam pre-2015
kot_pre2015 = df[(df["zone"] == "Kottayam") & (df["year"] < 2015)]
print(f"\nEmpirical Fact: Kottayam rows before 2015 = {len(kot_pre2015)}")
kot_first = df[df["zone"] == "Kottayam"]["date"].min()
print(f"Earliest date for Kottayam in dataset: {kot_first.date()}")

# -----------------------------------------------------------------------------
# 2. POSITIVES RECONCILIATION
# -----------------------------------------------------------------------------
print("\n" + "=" * 80)
print("2. POSITIVES RECONCILIATION (Train 2000-2018 vs Test 2019-2024)")
print("=" * 80)
train_df = df[df["year"] <= 2018]
test_df = df[df["year"] >= 2019]

print("TRAINING PERIOD (2000-2018):")
for z in sorted(df["zone"].unique()):
    sub = train_df[train_df["zone"] == z]
    print(f"  {z:16s}: Rows = {len(sub):5d}, Warn Pos = {sub['label_warning'].sum():3d}, Dang Pos = {sub['label_danger'].sum():3d}")
print(f"  POOLED TRAIN    : Rows = {len(train_df):5d}, Warn Pos = {train_df['label_warning'].sum():3d}, Dang Pos = {train_df['label_danger'].sum():3d}")

print("\nHOLDOUT TEST PERIOD (2019-2024):")
for z in sorted(df["zone"].unique()):
    sub = test_df[test_df["zone"] == z]
    print(f"  {z:16s}: Rows = {len(sub):5d}, Warn Pos = {sub['label_warning'].sum():3d}, Dang Pos = {sub['label_danger'].sum():3d}")
print(f"  POOLED TEST     : Rows = {len(test_df):5d}, Warn Pos = {test_df['label_warning'].sum():3d}, Dang Pos = {test_df['label_danger'].sum():3d}")

y2018 = df[df["year"] == 2018]
print(f"\n2018 POOLED ONLY: Warn Pos = {y2018['label_warning'].sum():3d}, Dang Pos = {y2018['label_danger'].sum():3d}")

# -----------------------------------------------------------------------------
# 3. ARTIFACT & COEFFICIENT RECONCILIATION
# -----------------------------------------------------------------------------
print("\n" + "=" * 80)
print("3. ARTIFACT & COEFFICIENT RECONCILIATION")
print("=" * 80)
art = joblib.load("models/final_single_risk_score_model.joblib")
print("Keys in artifact:", list(art.keys()))
print("Thresholds:", art.get("thresholds"))
fn = art["feature_names"]
clip_ranges = art["clip_ranges"]

coeff_rows = []
for m_key in ("pipeline_warning", "pipeline_danger"):
    pipe = art[m_key]
    scaler = pipe[0]
    clf = pipe[-1]
    
    means = scaler.mean_
    scales = scaler.scale_
    std_coefs = clf.coef_[0]
    std_intercept = clf.intercept_[0]
    raw_coefs = std_coefs / scales
    # Mathematical raw intercept: beta0_raw = beta0_std - sum(beta_std * mu / sigma)
    raw_intercept = std_intercept - np.sum(std_coefs * (means / scales))
    
    print(f"\nModel: {m_key}")
    print(f"  Pipeline: {pipe}")
    print(f"  class_weight: {getattr(clf, 'class_weight', None)}")
    print(f"  Standardized Intercept: {std_intercept:.4f}")
    print(f"  Calculated Raw Intercept: {raw_intercept:.4f}")
    
    for f, sc, rc, m, s in zip(fn, std_coefs, raw_coefs, means, scales):
        coeff_rows.append({
            "model": m_key, "feature": f, "mean": round(m, 4), "std": round(s, 4),
            "std_coef": round(sc, 4), "raw_coef": round(rc, 6)
        })

c_df = pd.DataFrame(coeff_rows)
c_df.to_csv(out_dir / "reconciled_coefficients.csv", index=False)
print("\nCoefficients Table:")
print(c_df.to_string())

# -----------------------------------------------------------------------------
# 4. SYNTHETIC INPUT SWEEPS & LOGIT DECOMPOSITION
# -----------------------------------------------------------------------------
print("\n" + "=" * 80)
print("4. SYNTHETIC INPUT SWEEPS & LOGIT DECOMPOSITION")
print("=" * 80)

def score_and_decompose(r1, soil, doy=227):
    f_raw = {
        "rainfall_1d": r1, "rainfall_3d": 1.5 * r1, "rainfall_7d": 2.5 * r1,
        "rainfall_14d": 4.0 * r1, "rainfall_30d": 8.0 * r1,
        "soil_moisture_0_to_7cm_mean": soil,
        "sin_doy": np.sin(2 * np.pi * doy / 365.25),
        "cos_doy": np.cos(2 * np.pi * doy / 365.25)
    }
    f_clipped = {n: min(max(f_raw[n], clip_ranges[n][0]), clip_ranges[n][1]) for n in fn}
    x_df = pd.DataFrame([[f_clipped[n] for n in fn]], columns=fn)
    results = {}
    for m_key in ("pipeline_warning", "pipeline_danger"):
        pipe = art[m_key]
        scaler = pipe[0]
        clf = pipe[-1]
        z = (x_df.values[0] - scaler.mean_) / scaler.scale_
        contrib = z * clf.coef_[0]
        total_logit = clf.intercept_[0] + np.sum(contrib)
        score = 1.0 / (1.0 + np.exp(-total_logit))
        results[m_key] = {
            "score": round(score, 4),
            "total_logit": round(total_logit, 4),
            "contrib": dict(zip(fn, np.round(contrib, 4)))
        }
    return f_clipped, results

sweep_rows = []
for r in (0, 25, 50, 75, 100, 125, 150):
    _, res = score_and_decompose(r, 0.42)
    w_s = res["pipeline_warning"]["score"]
    d_s = res["pipeline_danger"]["score"]
    sweep_rows.append({
        "rainfall_1d": r, "soil": 0.42,
        "warn_score": w_s, "dang_score": d_s,
        "warn_eff": max(w_s, d_s),
        "dang_logit": res["pipeline_danger"]["total_logit"]
    })
    print(f"Rain {r:3d} mm, Soil 0.42 -> Warn: {w_s:.4f} | Dang: {d_s:.4f} | Dang Logit: {res['pipeline_danger']['total_logit']:.2f}")

pd.DataFrame(sweep_rows).to_csv(out_dir / "sweep_rainfall.csv", index=False)

print("\nSoil Sensitivity at 0 mm Rain (Danger Model):")
soil_rows = []
for s in (0.05, 0.118, 0.25, 0.384, 0.48, 0.542, 0.60):
    f_clip, res = score_and_decompose(0, s)
    w_s = res["pipeline_warning"]["score"]
    d_s = res["pipeline_danger"]["score"]
    soil_rows.append({
        "input_soil": s, "clipped_soil": f_clip["soil_moisture_0_to_7cm_mean"],
        "warn_score": w_s, "dang_score": d_s,
        "dang_logit": res["pipeline_danger"]["total_logit"]
    })
    print(f"Soil {s:.3f} (clipped {f_clip['soil_moisture_0_to_7cm_mean']:.3f}) -> Warn: {w_s:.4f} | Dang: {d_s:.4f} | Dang Logit: {res['pipeline_danger']['total_logit']:.2f}")

pd.DataFrame(soil_rows).to_csv(out_dir / "sweep_soil_sensitivity.csv", index=False)

# -----------------------------------------------------------------------------
# 5. DOCUMENT LIMITATIONS
# -----------------------------------------------------------------------------
with open(out_dir / "limitations.md", "w") as f:
    f.write("""# Model Limitations

## Danger Model Inverse Soil Sensitivity under Dry Conditions
Due to collinearity between rolling rainfall accumulation (7d, 14d, 30d) and topsoil moisture during peak monsoon flood crests in 2000-2018, the danger logistic regression model assigns a negative coefficient to soil moisture.

With zero rainfall, as soil moisture drops across the clipped range (0.542 -> 0.118 m^3/m^3), the danger logit increases by +1.34, raising the uncalibrated danger risk score from 0.0075 to 0.0281 (a 3.7x increase).

While 0.0281 remains orders of magnitude below the danger threshold (0.9360), this is an empirical artifact of unconstrained linear models. Per strict protocol, the model is not retrained after holdout evaluation.
""")
print("\nLimitations saved to docs/step0/limitations.md")
print("All outputs saved to docs/step0/.")
