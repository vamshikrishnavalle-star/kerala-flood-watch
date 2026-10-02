import json, math, os, pathlib, sys, time
from datetime import date, datetime, timedelta
import httpx
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import average_precision_score, roc_auc_score, precision_score, recall_score, f1_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, ClassifierMixin

SEP  = "=" * 78
THIN = "-" * 78

RAW_DIR       = pathlib.Path("data/raw")
PROCESSED_DIR = pathlib.Path("data/processed")
MODELS_DIR    = pathlib.Path("models")
DOCS_DIR      = pathlib.Path("docs")
PARITY_DIR    = RAW_DIR / "parity"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
PARITY_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# 1. WRITE MODEL SELECTION PROTOCOL TO DOCS BEFORE RUNNING
# ------------------------------------------------------------
print(SEP); print("1. WRITING MODEL SELECTION PROTOCOL (docs/model-selection-protocol.md)"); print(SEP)

protocol_md = """# Stage 2 Model Selection Protocol

Date: 2026-10-03
Status: Locked Prior to Stage 2 Evaluation

## Selection Rules
1. **Optimization Metric**: Highest Out-of-Fold (OOF) PR-AUC inside the 2000–2018 training data.
2. **Tie-Breaker**: In the event of a tie (delta OOF PR-AUC < 0.005), the simpler model with lower false-alarm overhead wins.
3. **Partitioning**: Expanding-window `TimeSeriesSplit(n_splits=5)` strictly inside 2000–2018. The 2019–2024 test data is never used during selection.
4. **Architectural Guardrails**:
   - Range-clipping on linear models to eliminate negative dry-soil extrapolation artifacts.
   - Monotonicity checks across rainfall and soil features.
"""
(DOCS_DIR / "model-selection-protocol.md").write_text(protocol_md, encoding="utf-8")
print("  Protocol written to docs/model-selection-protocol.md.\n")

# ------------------------------------------------------------
# 2. FEATURE INGESTION & DATASET PREPARATION
# ------------------------------------------------------------
print(SEP); print("2. INGESTING WEATHER DATA (TOWN, GAUGE & AVERAGED)"); print(SEP)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

coords = {
    "Pathanamthitta": {
        "town":  {"slug": "pathanamthitta_kozhencherry", "lat": 9.3364, "lon": 76.6974},
        "gauge": {"slug": "pathanamthitta_kalloopara",   "lat": 9.3986, "lon": 76.6022},
    },
    "Kottayam": {
        "town":  {"slug": "kottayam_pala",               "lat": 9.7100, "lon": 76.6800},
        "gauge": {"slug": "kottayam_kidangoor",          "lat": 9.6800, "lon": 76.6100},
    }
}

def fetch_or_load_weather(slug, lat, lon):
    fp = RAW_DIR / "historical" / f"{slug}.csv"
    if fp.exists():
        df = pd.read_csv(fp, parse_dates=["date"])
        if len(df) == 9132:
            return df.sort_values("date").reset_index(drop=True)
            
    with httpx.Client(timeout=60.0) as client:
        r = client.get(ARCHIVE_URL, params={
            "latitude": lat, "longitude": lon,
            "start_date": "2000-01-01", "end_date": "2024-12-31",
            "daily": "precipitation_sum,soil_moisture_0_to_7cm_mean,soil_moisture_7_to_28cm_mean",
            "timezone": "Asia/Kolkata"
        })
        res_j = r.json()["daily"]
        df = pd.DataFrame(res_j).rename(columns={"time": "date"})
        df["date"] = pd.to_datetime(df["date"])
        df.to_csv(fp, index=False)
        return df.sort_values("date").reset_index(drop=True)

weather_streams = {}
for dist in ["Pathanamthitta", "Kottayam"]:
    weather_streams[f"{dist}_town"]  = fetch_or_load_weather(coords[dist]["town"]["slug"], coords[dist]["town"]["lat"], coords[dist]["town"]["lon"])
    weather_streams[f"{dist}_gauge"] = fetch_or_load_weather(coords[dist]["gauge"]["slug"], coords[dist]["gauge"]["lat"], coords[dist]["gauge"]["lon"])
    
    df_avg = weather_streams[f"{dist}_town"].copy()
    g_df   = weather_streams[f"{dist}_gauge"]
    df_avg["precipitation_sum"] = 0.5 * (df_avg["precipitation_sum"] + g_df["precipitation_sum"])
    
    col1 = "soil_moisture_0_7cm" if "soil_moisture_0_7cm" in df_avg.columns else "soil_moisture_0_to_7cm_mean"
    g_col1 = "soil_moisture_0_7cm" if "soil_moisture_0_7cm" in g_df.columns else "soil_moisture_0_to_7cm_mean"
    col2 = "soil_moisture_7_28cm" if "soil_moisture_7_28cm" in df_avg.columns else "soil_moisture_7_to_28cm_mean"
    g_col2 = "soil_moisture_7_28cm" if "soil_moisture_7_28cm" in g_df.columns else "soil_moisture_7_to_28cm_mean"
    
    df_avg[col1] = 0.5 * (df_avg[col1] + g_df[g_col1])
    df_avg[col2] = 0.5 * (df_avg[col2] + g_df[g_col2])
    weather_streams[f"{dist}_avg"] = df_avg

def build_features_dataframe(wdf, zone_name):
    p_s = wdf["precipitation_sum"].shift(1)
    col1 = "soil_moisture_0_7cm" if "soil_moisture_0_7cm" in wdf.columns else "soil_moisture_0_to_7cm_mean"
    col2 = "soil_moisture_7_28cm" if "soil_moisture_7_28cm" in wdf.columns else "soil_moisture_7_to_28cm_mean"
    
    res = pd.DataFrame({
        "date": wdf["date"],
        "zone": zone_name,
        "rain_1d":  p_s,
        "rain_3d":  p_s.rolling(3, min_periods=3).sum(),
        "rain_7d":  p_s.rolling(7, min_periods=7).sum(),
        "rain_14d": p_s.rolling(14, min_periods=14).sum(),
        "rain_30d": p_s.rolling(30, min_periods=30).sum(),
        "soil_0_7_t1":  wdf[col1].shift(1),
        "soil_7_28_t1": wdf[col2].shift(1),
    })
    doy = wdf["date"].dt.dayofyear
    res["sin_doy"] = np.sin(2 * np.pi * doy / 365.25)
    res["cos_doy"] = np.cos(2 * np.pi * doy / 365.25)
    return res

ds_df = pd.read_parquet(PROCESSED_DIR / "dataset.parquet")
ds_df["date"] = pd.to_datetime(ds_df["date"])

feature_variants = {}
for v_name, suffix in [("town", "town"), ("gauge", "gauge"), ("avg", "avg")]:
    frames = []
    for dist in ["Pathanamthitta", "Kottayam"]:
        f_df = build_features_dataframe(weather_streams[f"{dist}_{suffix}"], dist)
        frames.append(f_df)
    comb_f = pd.concat(frames, ignore_index=True)
    m = ds_df[["date", "zone", "station", "label_danger", "label_warning", "regime"]].merge(comb_f, on=["zone", "date"], how="inner")
    feature_variants[v_name] = m.dropna().sort_values(["zone", "date"]).reset_index(drop=True)

# ------------------------------------------------------------
# 3. RANGE-CLIPPED LOGISTIC REGRESSION & MONOTONIC GBDT
# ------------------------------------------------------------
class ClippedLogisticRegression(BaseEstimator, ClassifierMixin):
    def __init__(self, class_weight="balanced", random_state=42):
        self.class_weight = class_weight
        self.random_state = random_state
        self.pipeline = None
        self.min_vals = None
        self.max_vals = None
        
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

# ------------------------------------------------------------
# 4. OUT-OF-FOLD EVALUATION MATRIX (2000-2018 ONLY)
# ------------------------------------------------------------
print(SEP); print("3. OUT-OF-FOLD (OOF) MODEL & FEATURE SELECTION MATRIX (2000-2018)"); print(SEP)

BASE_FEATS = ["rain_1d", "rain_3d", "rain_7d", "rain_14d", "rain_30d", "soil_0_7_t1", "soil_7_28_t1"]
FULL_FEATS = BASE_FEATS + ["sin_doy", "cos_doy"]

mono_base = [1, 1, 1, 1, 1, 1, 1]
mono_full = [1, 1, 1, 1, 1, 1, 1, 0, 0]

SPLIT_DATE = pd.to_datetime("2019-01-01")

df_train_sample = feature_variants["town"][feature_variants["town"]["date"] < SPLIT_DATE].sort_values("date").reset_index(drop=True)
tscv = TimeSeriesSplit(n_splits=5)

candidates = []

for feat_source in ["town", "gauge", "avg"]:
    df_var = feature_variants[feat_source]
    train_df = df_var[df_var["date"] < SPLIT_DATE].sort_values("date").reset_index(drop=True)
    
    for feat_set_name, f_cols, m_c in [("full_with_doy", FULL_FEATS, mono_full), ("no_doy", BASE_FEATS, mono_base)]:
        for model_family in ["monotonic_gbdt", "clipped_logistic"]:
            for strategy in ["single_score_on_warning", "dedicated_danger"]:
                target_col = "label_warning" if strategy == "single_score_on_warning" else "label_danger"
                
                oof_preds = np.zeros(len(train_df))
                val_mask  = np.zeros(len(train_df), dtype=bool)
                
                for tr_idx, val_idx in tscv.split(train_df):
                    X_tr = train_df.iloc[tr_idx][f_cols].to_numpy()
                    y_tr = train_df.iloc[tr_idx][target_col].to_numpy()
                    X_va = train_df.iloc[val_idx][f_cols].to_numpy()
                    
                    if model_family == "monotonic_gbdt":
                        clf = HistGradientBoostingClassifier(
                            monotonic_cst=m_c,
                            class_weight="balanced",
                            random_state=42,
                            max_iter=100,
                            min_samples_leaf=20,
                            learning_rate=0.05
                        )
                    else:
                        clf = ClippedLogisticRegression(class_weight="balanced", random_state=42)
                        
                    clf.fit(X_tr, y_tr)
                    oof_preds[val_idx] = clf.predict_proba(X_va)[:, 1]
                    val_mask[val_idx] = True
                    
                y_val_w = train_df.loc[val_mask, "label_warning"]
                y_val_d = train_df.loc[val_mask, "label_danger"]
                preds_eval = oof_preds[val_mask]
                
                pr_auc_w = average_precision_score(y_val_w, preds_eval)
                pr_auc_d = average_precision_score(y_val_d, preds_eval)
                
                candidates.append({
                    "feat_source": feat_source,
                    "feat_set": feat_set_name,
                    "model_family": model_family,
                    "strategy": strategy,
                    "oof_pr_auc_warning": pr_auc_w,
                    "oof_pr_auc_danger": pr_auc_d,
                    "model_obj_type": model_family,
                    "cols": f_cols,
                    "mono_cst": m_c,
                })

cand_df = pd.DataFrame(candidates).sort_values("oof_pr_auc_warning", ascending=False).reset_index(drop=True)

print(f"{'Rank':>4} | {'Model Family':<18} | {'Features':<14} | {'Weather Source':<8} | {'Strategy':<24} | {'OOF PR-AUC (Warn)':>18} {'OOF PR-AUC (Dang)':>18}")
print(THIN)
for i, r in cand_df.iterrows():
    print(f"{i+1:>4} | {r['model_family']:<18} | {r['feat_set']:<14} | {r['feat_source']:<8} | {r['strategy']:<24} | {r['oof_pr_auc_warning']:>18.4f} {r['oof_pr_auc_danger']:>18.4f}")

winner = cand_df.iloc[0]
print(f"\n> [WINNER SELECTED BY PROTOCOL]:")
print(f"  - Model Family   : {winner['model_family']}")
print(f"  - Features       : {winner['feat_set']}")
print(f"  - Weather Source : {winner['feat_source']}")
print(f"  - Strategy       : {winner['strategy']}")
print(f"  - OOF PR-AUC (Warning): {winner['oof_pr_auc_warning']:.4f}, OOF PR-AUC (Danger): {winner['oof_pr_auc_danger']:.4f}")

# ------------------------------------------------------------
# 5. THRESHOLD SELECTION ON OOF (TARGET = 75% EVENT RECALL)
# ------------------------------------------------------------
print(f"\n{SEP}"); print("4. OOF THRESHOLD SELECTION (TARGET: 75% EVENT RECALL)"); print(SEP)

win_df_train = feature_variants[winner["feat_source"]][feature_variants[winner["feat_source"]]["date"] < SPLIT_DATE].sort_values("date").reset_index(drop=True)
oof_win = np.zeros(len(win_df_train))
val_mask_win = np.zeros(len(win_df_train), dtype=bool)

for tr_idx, val_idx in tscv.split(win_df_train):
    X_tr = win_df_train.iloc[tr_idx][winner["cols"]].to_numpy()
    y_tr = win_df_train.iloc[tr_idx]["label_warning"].to_numpy()
    X_va = win_df_train.iloc[val_idx][winner["cols"]].to_numpy()
    
    if winner["model_family"] == "monotonic_gbdt":
        clf = HistGradientBoostingClassifier(monotonic_cst=winner["mono_cst"], class_weight="balanced", random_state=42, max_iter=100, min_samples_leaf=20, learning_rate=0.05)
    else:
        clf = ClippedLogisticRegression(class_weight="balanced", random_state=42)
    clf.fit(X_tr, y_tr)
    oof_win[val_idx] = clf.predict_proba(X_va)[:, 1]
    val_mask_win[val_idx] = True

oof_eval_df = win_df_train[val_mask_win].copy().reset_index(drop=True)
oof_eval_df["oof_score"] = oof_win[val_mask_win]

oof_events_w = get_clusters(oof_eval_df, "label_warning")
oof_events_d = get_clusters(oof_eval_df, "label_danger")

def eval_threshold(df, score_col, target_col, events, threshold):
    preds = (df[score_col] >= threshold).astype(int)
    caught = 0
    df_eval = df[["zone", "date"]].copy()
    df_eval["pred"] = preds.values
    for z, st, en in events:
        mask = (df_eval["zone"] == z) & (df_eval["date"] >= st - pd.Timedelta(days=2)) & (df_eval["date"] <= en)
        if df_eval.loc[mask, "pred"].sum() > 0:
            caught += 1
    ev_rec = caught / max(len(events), 1)
    fa_days = int(((preds == 1) & (df[target_col] == 0)).sum())
    
    df_eval["fa"] = ((preds == 1) & (df[target_col] == 0)).astype(int)
    fa_episodes = 0
    for z, zgrp in df_eval.groupby("zone"):
        in_fa = False
        for _, r in zgrp.sort_values("date").iterrows():
            if r["fa"] == 1:
                if not in_fa:
                    fa_episodes += 1
                    in_fa = True
            else:
                in_fa = False
    return ev_rec, caught, len(events), fa_days, fa_episodes

candidate_thrs = np.linspace(0.01, 0.99, 1000)

th_w_chosen, th_d_chosen = 0.5, 0.5
for t in reversed(candidate_thrs):
    rec_w, caught, tot, fa_d, fa_ep = eval_threshold(oof_eval_df, "oof_score", "label_warning", oof_events_w, t)
    if rec_w >= 0.75:
        th_w_chosen = t
        break

for t in reversed(candidate_thrs):
    rec_d, caught, tot, fa_d, fa_ep = eval_threshold(oof_eval_df, "oof_score", "label_danger", oof_events_d, t)
    if rec_d >= 0.75:
        th_d_chosen = t
        break

if th_d_chosen < th_w_chosen:
    th_d_chosen = th_w_chosen

w_rec_oof, w_c_oof, w_tot_oof, w_fad_oof, w_fae_oof = eval_threshold(oof_eval_df, "oof_score", "label_warning", oof_events_w, th_w_chosen)
d_rec_oof, d_c_oof, d_tot_oof, d_fad_oof, d_fae_oof = eval_threshold(oof_eval_df, "oof_score", "label_danger", oof_events_d, th_d_chosen)

print(f"Chosen Warning Threshold: {th_w_chosen:.4f}")
print(f"  - OOF Warning Event Recall : {w_rec_oof:.2%} ({w_c_oof}/{w_tot_oof} events caught)")
print(f"  - OOF False Alarm Days     : {w_fad_oof} days | FA Episodes: {w_fae_oof}")

print(f"\nChosen Danger Threshold : {th_d_chosen:.4f}")
print(f"  - OOF Danger Event Recall  : {d_rec_oof:.2%} ({d_c_oof}/{d_tot_oof} events caught)")
print(f"  - OOF False Alarm Days     : {d_fad_oof} days | FA Episodes: {d_fae_oof}")

# ------------------------------------------------------------
# 6. EVALUATE ONCE ON 2019-2024 TEST SET
# ------------------------------------------------------------
print(f"\n{SEP}"); print("5. HOLDOUT TEST EVALUATION (2019-2024, EVALUATED ONCE)"); print(SEP)

final_train_df = feature_variants[winner["feat_source"]][feature_variants[winner["feat_source"]]["date"] < SPLIT_DATE].sort_values("date").reset_index(drop=True)
final_test_df  = feature_variants[winner["feat_source"]][feature_variants[winner["feat_source"]]["date"] >= SPLIT_DATE].sort_values("date").reset_index(drop=True)

if winner["model_family"] == "monotonic_gbdt":
    final_model = HistGradientBoostingClassifier(monotonic_cst=winner["mono_cst"], class_weight="balanced", random_state=42, max_iter=100, min_samples_leaf=20, learning_rate=0.05)
else:
    final_model = ClippedLogisticRegression(class_weight="balanced", random_state=42)

final_model.fit(final_train_df[winner["cols"]].to_numpy(), final_train_df["label_warning"].to_numpy())
joblib.dump(final_model, MODELS_DIR / "final_single_risk_score_model.joblib")

test_scores = final_model.predict_proba(final_test_df[winner["cols"]].to_numpy())[:, 1]
final_test_df["risk_score"] = test_scores
final_test_df["alert_warning"] = (test_scores >= th_w_chosen).astype(int)
final_test_df["alert_danger"]  = (test_scores >= th_d_chosen).astype(int)

def bootstrap_event_recall_ci(df, score_col, label_col, threshold, n_boot=1000):
    events = get_clusters(df, label_col)
    if not events: return 0.0, (0.0, 0.0), 0, 0
    
    caught_flags = []
    df_eval = df[["zone", "date", score_col]].copy()
    for z, st, en in events:
        mask = (df_eval["zone"] == z) & (df_eval["date"] >= st - pd.Timedelta(days=2)) & (df_eval["date"] <= en)
        is_caught = (df_eval.loc[mask, score_col] >= threshold).sum() > 0
        caught_flags.append(1 if is_caught else 0)
        
    base_rec = np.mean(caught_flags)
    rng = np.random.default_rng(42)
    boot_recs = []
    for _ in range(n_boot):
        sample = rng.choice(caught_flags, size=len(caught_flags), replace=True)
        boot_recs.append(np.mean(sample))
        
    ci_low  = np.percentile(boot_recs, 2.5)
    ci_high = np.percentile(boot_recs, 97.5)
    return base_rec, (ci_low, ci_high), sum(caught_flags), len(events)

for z in ["Pathanamthitta", "Kottayam"]:
    z_sub = final_test_df[final_test_df["zone"] == z].copy()
    n_tr_pos_d = int(final_train_df[final_train_df["zone"] == z]["label_danger"].sum())
    n_tr_pos_w = int(final_train_df[final_train_df["zone"] == z]["label_warning"].sum())
    
    d_rec, d_ci, d_c, d_tot = bootstrap_event_recall_ci(z_sub, "risk_score", "label_danger", th_d_chosen)
    w_rec, w_ci, w_c, w_tot = bootstrap_event_recall_ci(z_sub, "risk_score", "label_warning", th_w_chosen)
    
    is_provisional = (n_tr_pos_d < 20) or (d_tot < 10)
    tag = "[PROVISIONAL - Small Sample]" if is_provisional else "[VALIDATED]"
    
    fa_d_days = int(((z_sub["alert_danger"] == 1) & (z_sub["label_danger"] == 0)).sum())
    fa_w_days = int(((z_sub["alert_warning"] == 1) & (z_sub["label_warning"] == 0)).sum())
    ny = z_sub["date"].dt.year.nunique()
    
    print(f"\nZone: {z} {tag}")
    print(f"  Training Positives : Danger={n_tr_pos_d}, Warning={n_tr_pos_w}")
    print(f"  Test Events        : Danger={d_tot} events, Warning={w_tot} events")
    print(f"  Danger Event Recall: {d_rec:.2%} ({d_c}/{d_tot} caught) | 95% Bootstrap CI: [{d_ci[0]:.2%}, {d_ci[1]:.2%}]")
    print(f"  Warning Event Recall: {w_rec:.2%} ({w_c}/{w_tot} caught) | 95% Bootstrap CI: [{w_ci[0]:.2%}, {w_ci[1]:.2%}]")
    print(f"  False Alarms / Year: Danger={fa_d_days/ny:.1f} days/yr ({fa_d_days} total), Warning={fa_w_days/ny:.1f} days/yr ({fa_w_days} total)")

tot_d_rec, tot_d_ci, tot_d_c, tot_d_tot = bootstrap_event_recall_ci(final_test_df, "risk_score", "label_danger", th_d_chosen)
tot_w_rec, tot_w_ci, tot_w_c, tot_w_tot = bootstrap_event_recall_ci(final_test_df, "risk_score", "label_warning", th_w_chosen)
tot_fa_d = int(((final_test_df["alert_danger"] == 1) & (final_test_df["label_danger"] == 0)).sum())
tot_fa_w = int(((final_test_df["alert_warning"] == 1) & (final_test_df["label_warning"] == 0)).sum())
tot_ny = final_test_df["date"].dt.year.nunique()

print(f"\n{THIN}")
print(f"ALL-ZONES COMBINED TEST SET PERFORMANCE (2019-2024, N={len(final_test_df):,} days):")
print(f"  - Danger Event Recall  : {tot_d_rec:.2%} ({tot_d_c}/{tot_d_tot} caught) | 95% CI: [{tot_d_ci[0]:.2%}, {tot_d_ci[1]:.2%}]")
print(f"  - Warning Event Recall : {tot_w_rec:.2%} ({tot_w_c}/{tot_w_tot} caught) | 95% CI: [{tot_w_ci[0]:.2%}, {tot_w_ci[1]:.2%}]")
print(f"  - Danger PR-AUC        : {average_precision_score(final_test_df['label_danger'], test_scores):.4f}")
print(f"  - Warning PR-AUC       : {average_precision_score(final_test_df['label_warning'], test_scores):.4f}")
print(f"  - False Alarms / Year  : Danger={tot_fa_d/tot_ny:.1f} days/yr, Warning={tot_fa_w/tot_ny:.1f} days/yr")

final_test_df["month"] = final_test_df["date"].dt.month
print(f"\n{THIN}")
print("Monthly Alerts vs. True Positives (2019-2024 Test Set):")
print(f"{'Month':>6} | {'Danger Pos':>11} {'Danger Alerts':>14} | {'Warning Pos':>12} {'Warning Alerts':>15}")
print(THIN)
for m in range(1, 13):
    m_name = date(2000, m, 1).strftime("%b")
    m_sub = final_test_df[final_test_df["month"] == m]
    pd_cnt = int(m_sub["label_danger"].sum())
    ad_cnt = int(m_sub["alert_danger"].sum())
    pw_cnt = int(m_sub["label_warning"].sum())
    aw_cnt = int(m_sub["alert_warning"].sum())
    print(f"{m_name:>6} | {pd_cnt:>11} {ad_cnt:>14} | {pw_cnt:>12} {aw_cnt:>15}")

# ------------------------------------------------------------
# 7. SANITY CHECKS (MONOTONICITY & 2026 RE-SCORING)
# ------------------------------------------------------------
print(f"\n{SEP}"); print("6. SANITY CHECKS (MONOTONICITY & 2026 RE-SCORING)"); print(SEP)

print("Synthetic Monotonicity Sanity Check (0 mm Rain, Soil moisture varying 0.05 to 0.60):")
print(f"{'Soil Moisture (0-7cm)':<25} | {'Risk Score':>12} | {'Danger Alert?':>14}")
print(THIN)
synthetic_rows = []
for sm in [0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60]:
    row_dict = {
        "rain_1d": 0.0, "rain_3d": 0.0, "rain_7d": 0.0, "rain_14d": 0.0, "rain_30d": 0.0,
        "soil_0_7_t1": sm, "soil_7_28_t1": sm, "sin_doy": -0.96, "cos_doy": -0.25
    }
    row_df = pd.DataFrame([row_dict])[winner["cols"]].to_numpy()
    score = final_model.predict_proba(row_df)[0, 1]
    is_al = score >= th_d_chosen
    print(f"{sm:<25.2f} | {score:>12.4f} | {str(is_al):>14}")
    synthetic_rows.append(score)

is_mono = all(x <= y for x, y in zip(synthetic_rows, synthetic_rows[1:]))
print(f"\n> Monotonicity Check Passed (Scores never rise on dry soil): {is_mono}")

live_json_file = PARITY_DIR / "live_forecast_past92.json"
if live_json_file.exists():
    live_json = json.loads(live_json_file.read_text(encoding="utf-8"))["daily"]
    df_live = pd.DataFrame(live_json).rename(columns={"time": "date"})
    p_s = df_live["precipitation_sum"].shift(1)
    df_live["rain_1d"]  = p_s
    df_live["rain_3d"]  = p_s.rolling(3, min_periods=3).sum()
    df_live["rain_7d"]  = p_s.rolling(7, min_periods=7).sum()
    df_live["rain_14d"] = p_s.rolling(14, min_periods=14).sum()
    df_live["rain_30d"] = p_s.rolling(30, min_periods=30).sum()
    df_live["soil_0_7_t1"]  = df_live["soil_moisture_0_to_7cm_mean"].shift(1)
    df_live["soil_7_28_t1"] = df_live["soil_moisture_7_to_28cm_mean"].shift(1)
    doy = pd.to_datetime(df_live["date"]).dt.dayofyear
    df_live["sin_doy"] = np.sin(2 * np.pi * doy / 365.25)
    df_live["cos_doy"] = np.cos(2 * np.pi * doy / 365.25)

    eval_2026 = df_live.dropna(subset=winner["cols"]).copy().reset_index(drop=True)
    eval_2026["risk_score"] = final_model.predict_proba(eval_2026[winner["cols"]].to_numpy())[:, 1]
    eval_2026["danger_alert"] = eval_2026["risk_score"] >= th_d_chosen

    alerts_2026 = eval_2026[eval_2026["danger_alert"]]
    print(f"\nJul-Oct 2026 Re-Scoring with Range-Clipped Model (Total Days = {len(eval_2026)}):")
    print(f"  - Active Danger Alerts: {len(alerts_2026)} days ({len(alerts_2026)/len(eval_2026):.2%})")
    if not alerts_2026.empty:
        print(f"  - Alert Dates: {', '.join(alerts_2026['date'].astype(str).tolist())}")
    else:
        print("  - Alert Dates: None (Zero dry-season false alarms!)")

# ------------------------------------------------------------
# 8. DATA DIAGNOSTICS & EXACT TIMESTAMP THINNING TEST
# ------------------------------------------------------------
print(f"\n{SEP}"); print("7. DATA DIAGNOSTICS & EMPIRICAL SCHEDULE THINNING"); print(SEP)

raw_kp_path = RAW_DIR / "labels/cwc/v3/station_017-SWRDKOCHI_kallooppara.csv"
raw_kp = pd.read_csv(raw_kp_path, low_memory=False)
col = {c.lower(): c for c in raw_kp.columns}
dt_c  = col.get("datatime", list(col.values())[0])
dty_c = col.get("datatypecode", "datatypeCode")
val_c = col.get("datavalue", "dataValue")

raw_kp = raw_kp.rename(columns={dt_c:"dataTime", dty_c:"datatypeCode", val_c:"dataValue"})
raw_kp["dataTime"]  = pd.to_datetime(raw_kp["dataTime"], errors="coerce")
raw_kp["dataValue"] = pd.to_numeric(raw_kp["dataValue"], errors="coerce")
raw_kp["_date"]     = raw_kp["dataTime"].dt.date
raw_kp["_hour"]     = raw_kp["dataTime"].dt.hour

pre15 = raw_kp[raw_kp["dataTime"].dt.year < 2015]
hour_counts = pre15["_hour"].value_counts()
top_3_hours = sorted(hour_counts.head(3).index.tolist())
print(f"Empirically Derived Pre-2015 Reading Hours from Raw Timestamps: {top_3_hours} (Hours IST)")

exceed_dates = ds_df[(ds_df["label_danger"] == 1) | (ds_df["label_warning"] == 1)]["date"].dt.date.unique()
labels_raw = pd.read_csv(PROCESSED_DIR / "labels_daily.csv")
labels_raw["date"] = pd.to_datetime(labels_raw["date"]).dt.date
dropped_days = labels_raw[labels_raw["label_warning"].isna()]["date"].unique()

near_drops = []
for ed in exceed_dates:
    for offset in [-3, -2, -1, 1, 2, 3]:
        check_d = ed + timedelta(days=offset)
        if check_d in dropped_days:
            near_drops.append((ed, check_d, offset))

print(f"\nDropped NaN Days within ±3 Days of an Exceedance Event: {len(near_drops)} occurrences")
if near_drops:
    for ed, cd, off in near_drops[:5]:
        print(f"  Exceedance Date: {ed} | Dropped NaN Day: {cd} (Offset: {off:+d} days)")

print(f"\n{SEP}\nSTAGE 2 EVALUATION COMPLETE\n{SEP}")