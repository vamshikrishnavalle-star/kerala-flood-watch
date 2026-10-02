import sys, os, pathlib
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import average_precision_score
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

class ClippedLogisticRegression(BaseEstimator, ClassifierMixin):
    def __init__(self, class_weight=None, random_state=42):
        self.class_weight = class_weight
        self.random_state = random_state
    def fit(self, X, y):
        X_arr = np.asarray(X)
        self.min_vals = np.min(X_arr, axis=0)
        self.max_vals = np.max(X_arr, axis=0)
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(class_weight=self.class_weight, random_state=self.random_state, max_iter=1000))
        ])
        self.pipeline.fit(X_arr, y)
        self.classes_ = self.pipeline.named_steps["clf"].classes_
        return self
    def predict_proba(self, X):
        X_arr = np.asarray(X)
        X_clipped = np.clip(X_arr, self.min_vals, self.max_vals)
        return self.pipeline.predict_proba(X_clipped)

sys.modules['__main__'].ClippedLogisticRegression = ClippedLogisticRegression

out_dir = pathlib.Path("docs/step0")
out_dir.mkdir(parents=True, exist_ok=True)

PROCESSED_DIR = pathlib.Path("data/processed")
RAW_DIR = pathlib.Path("data/raw")
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

feature_cols = ["rain_1d", "rain_3d", "rain_7d", "rain_14d", "rain_30d", "soil_0_7_t1", "soil_7_28_t1", "sin_doy", "cos_doy"]
SPLIT_DATE = pd.to_datetime("2019-01-01")

train_df = full_df[full_df["date"] < SPLIT_DATE].sort_values("date").reset_index(drop=True)
test_df  = full_df[full_df["date"] >= SPLIT_DATE].sort_values("date").reset_index(drop=True)

# 2. OOF Predictions on 2000-2018
tscv = TimeSeriesSplit(n_splits=5)
oof_scores = np.zeros(len(train_df))
val_mask = np.zeros(len(train_df), dtype=bool)

for tr_idx, val_idx in tscv.split(train_df):
    X_tr = train_df.iloc[tr_idx][feature_cols].to_numpy()
    y_tr = train_df.iloc[tr_idx]["label_warning"].to_numpy()
    X_va = train_df.iloc[val_idx][feature_cols].to_numpy()
    
    clf = ClippedLogisticRegression(class_weight="balanced", random_state=42)
    clf.fit(X_tr, y_tr)
    oof_scores[val_idx] = clf.predict_proba(X_va)[:, 1]
    val_mask[val_idx] = True

oof_df = train_df[val_mask].copy().reset_index(drop=True)
oof_df["oof_score"] = oof_scores[val_mask]

# Load model and compute test scores
final_model = joblib.load("models/final_single_risk_score_model.joblib")
test_df["risk_score"] = final_model.predict_proba(test_df[feature_cols].to_numpy())[:, 1]

th_w = 0.9223
th_d = 0.9360

def get_clusters(df, label_col):
    events = []
    for zone, zgrp in df.groupby("zone"):
        z_sorted = zgrp.sort_values("date").reset_index()
        in_event = False
        start_idx = None
        for i, row in z_sorted.iterrows():
            if row[label_col] == 1:
                if not in_event:
                    in_event = True
                    start_idx = i
            else:
                if in_event:
                    events.append((zone, z_sorted.loc[start_idx, "date"], z_sorted.loc[i-1, "date"]))
                    in_event = False
        if in_event:
            events.append((zone, z_sorted.loc[start_idx, "date"], z_sorted.loc[len(z_sorted)-1, "date"]))
    return events

def compute_metrics(df, score_col, label_col, threshold):
    preds = (df[score_col] >= threshold).values.astype(int)
    labels = df[label_col].values.astype(int)
    
    tp_days = int(((preds == 1) & (labels == 1)).sum())
    fp_days = int(((preds == 1) & (labels == 0)).sum())
    fn_days = int(((preds == 0) & (labels == 1)).sum())
    tn_days = int(((preds == 0) & (labels == 0)).sum())
    
    day_prec = tp_days / max(tp_days + fp_days, 1)
    day_rec = tp_days / max(tp_days + fn_days, 1)
    
    events = get_clusters(df, label_col)
    
    # Event Recall
    caught = 0
    df_eval = df[["zone", "date"]].copy()
    df_eval["pred"] = preds
    for z, st, en in events:
        mask = (df_eval["zone"] == z) & (df_eval["date"] >= st - pd.Timedelta(days=2)) & (df_eval["date"] <= en)
        if df_eval.loc[mask, "pred"].sum() > 0:
            caught += 1
    event_rec = caught / max(len(events), 1)
    
    # Alert episodes (contiguous blocks of pred == 1)
    # Count alert episodes per zone
    alert_episodes = 0
    fa_episodes = 0
    for z, zgrp in df.assign(pred=preds).groupby("zone"):
        p_arr = zgrp["pred"].values
        l_arr = zgrp[label_col].values
        
        in_al = False
        ep_has_tp = False
        for p, l in zip(p_arr, l_arr):
            if p == 1:
                if not in_al:
                    alert_episodes += 1
                    in_al = True
                if l == 1:
                    ep_has_tp = True
            else:
                if in_al:
                    if not ep_has_tp:
                        fa_episodes += 1
                    in_al = False
                    ep_has_tp = False
        if in_al and not ep_has_tp:
            fa_episodes += 1
            
    ep_prec = caught / max(alert_episodes, 1)
    
    return {
        "tp_days": tp_days,
        "fp_days": fp_days,
        "alert_days": tp_days + fp_days,
        "day_prec": round(day_prec, 4),
        "day_rec": round(day_rec, 4),
        "caught_events": caught,
        "total_events": len(events),
        "event_rec": round(event_rec, 4),
        "total_alert_episodes": alert_episodes,
        "fa_episodes": fa_episodes,
        "ep_prec": round(ep_prec, 4)
    }

records = []

# OOF Per Zone
for z in ["Pathanamthitta", "Kottayam"]:
    z_df = oof_df[oof_df["zone"] == z].sort_values("date").reset_index(drop=True)
    mw = compute_metrics(z_df, "oof_score", "label_warning", th_w)
    md = compute_metrics(z_df, "oof_score", "label_danger", th_d)
    records.append({"dataset": "OOF_2000_2018", "zone": z, "target": "warning", "threshold": th_w, **mw})
    records.append({"dataset": "OOF_2000_2018", "zone": z, "target": "danger", "threshold": th_d, **md})

# OOF Combined (Summed episodes and days across zones)
mw_oof_all = compute_metrics(oof_df, "oof_score", "label_warning", th_w)
md_oof_all = compute_metrics(oof_df, "oof_score", "label_danger", th_d)
records.append({"dataset": "OOF_2000_2018", "zone": "COMBINED_POOLED", "target": "warning", "threshold": th_w, **mw_oof_all})
records.append({"dataset": "OOF_2000_2018", "zone": "COMBINED_POOLED", "target": "danger", "threshold": th_d, **md_oof_all})

# Test Per Zone
for z in ["Pathanamthitta", "Kottayam"]:
    z_df = test_df[test_df["zone"] == z].sort_values("date").reset_index(drop=True)
    mw = compute_metrics(z_df, "risk_score", "label_warning", th_w)
    md = compute_metrics(z_df, "risk_score", "label_danger", th_d)
    records.append({"dataset": "HOLDOUT_2019_2024", "zone": z, "target": "warning", "threshold": th_w, **mw})
    records.append({"dataset": "HOLDOUT_2019_2024", "zone": z, "target": "danger", "threshold": th_d, **md})

# Test Combined
mw_test_all = compute_metrics(test_df, "risk_score", "label_warning", th_w)
md_test_all = compute_metrics(test_df, "risk_score", "label_danger", th_d)
records.append({"dataset": "HOLDOUT_2019_2024", "zone": "COMBINED_POOLED", "target": "warning", "threshold": th_w, **mw_test_all})
records.append({"dataset": "HOLDOUT_2019_2024", "zone": "COMBINED_POOLED", "target": "danger", "threshold": th_d, **md_test_all})

res_df = pd.DataFrame(records)
res_df.to_csv(out_dir / "precision_recall_audit.csv", index=False)
print("=" * 80)
print("PRECISION & RECALL AUDIT (DAY-LEVEL & EPISODE-LEVEL)")
print("=" * 80)
print(res_df[["dataset", "zone", "target", "alert_days", "tp_days", "day_prec", "caught_events", "total_events", "event_rec", "total_alert_episodes", "ep_prec"]].to_string(index=False))
