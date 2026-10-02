import joblib, numpy as np, pandas as pd, glob
a = joblib.load("models/final_single_risk_score_model.joblib")
print(list(a.keys()))
fn = a["feature_names"]
for k in ("pipeline_warning", "pipeline_danger"):
    clf = a[k][-1]
    print(k, "| class_weight:", getattr(clf, "class_weight", None))
    print(dict(zip(fn, np.round(clf.coef_[0], 4))), "intercept", np.round(clf.intercept_, 4))
def score(r1, soil, doy=227):
    f = {"rainfall_1d": r1, "rainfall_3d": 1.5*r1, "rainfall_7d": 2.5*r1,
         "rainfall_14d": 4*r1, "rainfall_30d": 8*r1,
         "soil_moisture_0_to_7cm_mean": soil,
         "sin_doy": np.sin(2*np.pi*doy/365.25), "cos_doy": np.cos(2*np.pi*doy/365.25)}
    x = [[min(max(f[n], a["clip_ranges"][n][0]), a["clip_ranges"][n][1]) for n in fn]]
    return [round(float(a[k].predict_proba(pd.DataFrame(x, columns=fn))[0, 1]), 4)
            for k in ("pipeline_warning", "pipeline_danger")]
for r in (0, 25, 50, 100, 125): print("rain", r, "soil 0.42 ->", score(r, 0.42))
print("rain 0, soil 0.384 ->", score(0, 0.384))
for f in glob.glob("data/processed/*.parquet"):
    d = pd.read_parquet(f); print(f, d.shape, list(d.columns)[:14])
