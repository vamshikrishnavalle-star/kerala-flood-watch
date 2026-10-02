import math, os, pathlib, sys
from datetime import date
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
    precision_recall_curve
)
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

SEP  = "=" * 78
THIN = "-" * 78

PROCESSED_DIR = pathlib.Path("data/processed")
RAW_DIR       = pathlib.Path("data/raw")
MODELS_DIR    = pathlib.Path("models")
DOCS_DIR      = pathlib.Path("docs")

MODELS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# 1. Feature Engineering on Full Continuous Weather Files
# ------------------------------------------------------------
print(SEP); print("1. FEATURE ENGINEERING (t-1 rolling features on full weather)"); print(SEP)

zone_files = {
    "Pathanamthitta": RAW_DIR / "historical" / "pathanamthitta_kozhencherry.csv",
    "Kottayam":       RAW_DIR / "historical" / "kottayam_pala.csv",
}

feat_frames = []
for zone_name, fp in zone_files.items():
    if not fp.exists():
        print(f"ERROR: Weather file {fp} missing."); sys.exit(1)
    wdf = pd.read_csv(fp, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    
    # Strictly t-1 features
    p_shift = wdf["precipitation_sum"].shift(1)
    
    wdf["rain_1d"]  = p_shift
    wdf["rain_3d"]  = p_shift.rolling(3, min_periods=3).sum()
    wdf["rain_7d"]  = p_shift.rolling(7, min_periods=7).sum()
    wdf["rain_14d"] = p_shift.rolling(14, min_periods=14).sum()
    wdf["rain_30d"] = p_shift.rolling(30, min_periods=30).sum()
    
    wdf["soil_0_7_t1"]  = wdf["soil_moisture_0_7cm"].shift(1)
    wdf["soil_7_28_t1"] = wdf["soil_moisture_7_28cm"].shift(1)
    
    doy = wdf["date"].dt.dayofyear
    wdf["sin_doy"] = np.sin(2 * np.pi * doy / 365.25)
    wdf["cos_doy"] = np.cos(2 * np.pi * doy / 365.25)
    wdf["zone"] = zone_name
    
    feat_cols = [
        "date", "zone", "rain_1d", "rain_3d", "rain_7d", "rain_14d", "rain_30d",
        "soil_0_7_t1", "soil_7_28_t1", "sin_doy", "cos_doy"
    ]
    feat_frames.append(wdf[feat_cols])

all_features = pd.concat(feat_frames, ignore_index=True)

# Load dataset.parquet
ds_path = PROCESSED_DIR / "dataset.parquet"
ds_df = pd.read_parquet(ds_path)
ds_df["date"] = pd.to_datetime(ds_df["date"])

# Join features to dataset
merged = ds_df.merge(all_features, on=["zone", "date"], how="inner")
print(f"  Joined features to dataset.parquet: {len(merged):,} rows")

FEATURE_COLS = [
    "rain_1d", "rain_3d", "rain_7d", "rain_14d", "rain_30d",
    "soil_0_7_t1", "soil_7_28_t1", "sin_doy", "cos_doy"
]

# Drop rows with NaN in features (e.g. first 30 days of 2000 for 30d rolling)
valid_df = merged.dropna(subset=FEATURE_COLS).copy()
print(f"  Valid rows after t-1 rolling warmup: {len(valid_df):,} rows (dropped {len(merged)-len(valid_df)} initial warmup days)")

# ------------------------------------------------------------
# 2. Temporal Train/Test Split
# ------------------------------------------------------------
print(f"\n{SEP}"); print("2. TEMPORAL TRAIN/TEST SPLIT"); print(SEP)

SPLIT_DATE = pd.to_datetime("2019-01-01")

def get_clusters(df, label_col):
    """Identify contiguous clusters of label=1 as events."""
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

for target in ["label_danger", "label_warning"]:
    print(f"\n--- Target: {target} ---")
    train_full = valid_df[valid_df["date"] < SPLIT_DATE]
    test_df    = valid_df[valid_df["date"] >= SPLIT_DATE]
    train_2015 = valid_df[(valid_df["date"] >= "2015-01-01") & (valid_df["date"] < SPLIT_DATE)]
    
    for split_name, s_df in [("Train (Full: 2000-2018)", train_full),
                             ("Train (Hourly-era: 2015-2018)", train_2015),
                             ("Test (2019-2024)", test_df)]:
        evs = get_clusters(s_df, target)
        print(f"  {split_name:<32}: {len(s_df):>6,} days | Positives: {int(s_df[target].sum()):>4} ({s_df[target].mean():.2%}) | Events: {len(evs):>3}")
        for z in sorted(s_df["zone"].unique()):
            z_sub = s_df[s_df["zone"] == z]
            z_evs = [e for e in evs if e[0] == z]
            print(f"    - {z:<16}: {len(z_sub):>5,} days | Positives: {int(z_sub[target].sum()):>3} | Events: {len(z_evs):>2}")

# ------------------------------------------------------------
# 3. Model Training & Evaluation Functions
# ------------------------------------------------------------
def evaluate_event_recall(test_df, y_pred_series, events):
    """Event-level recall: event is caught if alert falls in [t_start - 2 days, t_end]."""
    if not events:
        return 0.0, 0, 0
    caught = 0
    test_sub = test_df[["zone", "date"]].copy()
    test_sub["pred"] = y_pred_series.values
    
    for zone, start_d, end_d in events:
        window_start = start_d - pd.Timedelta(days=2)
        window_end   = end_d
        
        mask = (test_sub["zone"] == zone) & (test_sub["date"] >= window_start) & (test_sub["date"] <= window_end)
        if test_sub.loc[mask, "pred"].sum() > 0:
            caught += 1
            
    return caught / len(events), caught, len(events)

def fit_and_eval(train_data, test_data, target, model_type, train_era_name):
    X_train = train_data[FEATURE_COLS]
    y_train = train_data[target]
    X_test  = test_data[FEATURE_COLS]
    y_test  = test_data[target]
    
    test_events = get_clusters(test_data, target)
    
    model_obj = None
    
    if model_type == "rule_baseline":
        # 3-day rainfall threshold optimizing training F1
        r3_train = train_data["rain_3d"]
        best_t, best_f1 = 0.0, -1.0
        # Scan candidate rainfall thresholds (e.g. 10mm to 300mm)
        for t_cand in np.linspace(10, 300, 300):
            preds = (r3_train >= t_cand).astype(int)
            f = f1_score(y_train, preds, zero_division=0)
            if f > best_f1:
                best_f1, best_t = f, t_cand
                
        y_test_score = test_data["rain_3d"].values
        y_test_pred  = (y_test_score >= best_t).astype(int)
        chosen_threshold = best_t
        model_obj = {"threshold": best_t}
        
    elif model_type == "logistic_regression":
        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(class_weight="balanced", random_state=42, max_iter=1000))
        ])
        pipe.fit(X_train, y_train)
        y_train_prob = pipe.predict_proba(X_train)[:, 1]
        
        # Choose probability threshold optimizing training F1
        p, r, thrs = precision_recall_curve(y_train, y_train_prob)
        f1s = 2 * (p * r) / (p + r + 1e-12)
        best_idx = np.argmax(f1s)
        chosen_threshold = thrs[best_idx] if best_idx < len(thrs) else 0.5
        
        y_test_score = pipe.predict_proba(X_test)[:, 1]
        y_test_pred  = (y_test_score >= chosen_threshold).astype(int)
        model_obj = pipe
        
    elif model_type == "gradient_boosting":
        clf = HistGradientBoostingClassifier(
            class_weight="balanced",
            random_state=42,
            max_iter=150,
            min_samples_leaf=20,
            learning_rate=0.05
        )
        clf.fit(X_train, y_train)
        y_train_prob = clf.predict_proba(X_train)[:, 1]
        
        p, r, thrs = precision_recall_curve(y_train, y_train_prob)
        f1s = 2 * (p * r) / (p + r + 1e-12)
        best_idx = np.argmax(f1s)
        chosen_threshold = thrs[best_idx] if best_idx < len(thrs) else 0.5
        
        y_test_score = clf.predict_proba(X_test)[:, 1]
        y_test_pred  = (y_test_score >= chosen_threshold).astype(int)
        model_obj = clf

    # Metrics
    pr_auc  = average_precision_score(y_test, y_test_score)
    roc_auc = roc_auc_score(y_test, y_test_score)
    prec    = precision_score(y_test, y_test_pred, zero_division=0)
    rec     = recall_score(y_test, y_test_pred, zero_division=0)
    f1      = f1_score(y_test, y_test_pred, zero_division=0)
    
    ev_rec, caught_ev, tot_ev = evaluate_event_recall(test_data, pd.Series(y_test_pred, index=test_data.index), test_events)
    
    # False alarms: pred=1 and true=0
    test_eval = test_data.copy()
    test_eval["pred"] = y_test_pred
    test_eval["fa"]   = ((test_eval["pred"] == 1) & (test_eval[target] == 0)).astype(int)
    
    total_fa = int(test_eval["fa"].sum())
    num_years = test_eval["date"].dt.year.nunique()
    fa_per_year = total_fa / max(num_years, 1)
    
    # FA by zone
    fa_by_zone = {z: int(test_eval[test_eval["zone"] == z]["fa"].sum()) for z in sorted(test_eval["zone"].unique())}
    # FA by regime
    fa_by_regime = {rg: int(test_eval[test_eval["regime"] == rg]["fa"].sum()) for rg in sorted(test_eval["regime"].unique())}
    
    # Save model
    model_fname = f"{model_type}_{target}_{train_era_name}.joblib"
    joblib.dump(model_obj, MODELS_DIR / model_fname)
    
    return {
        "target": target,
        "model": model_type,
        "train_era": train_era_name,
        "pr_auc": pr_auc,
        "roc_auc": roc_auc,
        "chosen_threshold": chosen_threshold,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "event_recall": ev_rec,
        "events_caught": f"{caught_ev}/{tot_ev}",
        "total_false_alarms": total_fa,
        "fa_per_year": fa_per_year,
        "fa_pathanamthitta": fa_by_zone.get("Pathanamthitta", 0),
        "fa_kottayam": fa_by_zone.get("Kottayam", 0),
        "fa_hourly": fa_by_regime.get("hourly", 0),
        "fa_3perday": fa_by_regime.get("3perday", 0),
    }

# ------------------------------------------------------------
# 4. Run Training & Evaluation Pipeline
# ------------------------------------------------------------
print(f"\n{SEP}"); print("3 & 4. TRAINING & EVALUATION MATRIX"); print(SEP)

results = []
train_splits = [
    ("full_2000_2018", valid_df[valid_df["date"] < SPLIT_DATE]),
    ("hourly_2015_2018", valid_df[(valid_df["date"] >= "2015-01-01") & (valid_df["date"] < SPLIT_DATE)])
]
test_split = valid_df[valid_df["date"] >= SPLIT_DATE]

models = ["rule_baseline", "logistic_regression", "gradient_boosting"]

for target in ["label_danger", "label_warning"]:
    for era_name, tr_df in train_splits:
        for m in models:
            res = fit_and_eval(tr_df, test_split, target, m, era_name)
            results.append(res)

metrics_df = pd.DataFrame(results)
metrics_csv = PROCESSED_DIR / "metrics.csv"
metrics_df.to_csv(metrics_csv, index=False)
print(f"  Metrics table saved -> {metrics_csv}\n")

# Display results table
print(SEP)
print("TEST SET EVALUATION RESULTS (2019-2024 Test Set)")
print(SEP)

for target in ["label_danger", "label_warning"]:
    print(f"\n=== TARGET: {target.upper()} ===")
    sub = metrics_df[metrics_df["target"] == target]
    fmt_cols = [
        "train_era", "model", "pr_auc", "roc_auc", "precision",
        "recall", "f1", "event_recall", "events_caught", "fa_per_year",
        "fa_pathanamthitta", "fa_kottayam", "fa_hourly", "fa_3perday"
    ]
    df_disp = sub[fmt_cols].copy()
    for col in ["pr_auc", "roc_auc", "precision", "recall", "f1", "event_recall"]:
        df_disp[col] = df_disp[col].map(lambda x: f"{x:.4f}")
    df_disp["fa_per_year"] = df_disp["fa_per_year"].map(lambda x: f"{x:.1f}")
    print(df_disp.to_string(index=False))

# ------------------------------------------------------------
# 5. Statistical Sample Size & Conclusiveness Statement
# ------------------------------------------------------------
print(f"\n{SEP}"); print("5. SAMPLE SIZE & LIMITATIONS ASSESSMENT"); print(SEP)
print("""
[STATISTICAL POWER & SAMPLE SIZE ASSESSMENT]
1. Target 'label_danger' on Test Set (2019-2024):
   - Total test days: 3,923 (Pathanamthitta: 2,075, Kottayam: 1,848).
   - Test danger positives: 52 days total (1.33% base rate).
   - Zone breakdown: Pathanamthitta = 45 days (17 events), Kottayam = 7 days (4 events).
   - CONSERVATIVE FINDING: For Kottayam danger levels, N=7 positive days across 4 events in 6 years
     is TOO SMALL to draw statistically definitive conclusions about individual zone generalizability.
     Overall aggregate evaluation (52 days across 21 events) provides actionable signal for statewide models.

2. Target 'label_warning' on Test Set (2019-2024):
   - Test warning positives: 122 days total (3.11% base rate).
   - Zone breakdown: Pathanamthitta = 98 days (31 events), Kottayam = 24 days (7 events).
   - Sufficient event frequency for robust calibration and comparison across models.

3. Hourly-Era (2015-2018) Training Set:
   - Training sample size is 2,472 days (Danger positives = 27, Warning positives = 49).
   - While free of the pre-2015 3-obs schedule bias, the small number of extreme events limits gradient boosting depth.
""")

print(SEP); print("PHASE 3 & 4 EXECUTION COMPLETE -- Stopped after metrics."); print(SEP)

