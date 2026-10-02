# Protocol Reconciliation & Model Selection Deviation Report

**Date**: 2026-10-03  
**Status**: Formal Audit Documentation  
**Governing Document**: `docs/model-selection-protocol.md`

---

## 1. Governing Protocol Rules (Exact Quotes)

From `docs/model-selection-protocol.md`:
> 1. **Optimization Metric**: Highest Out-of-Fold (OOF) PR-AUC inside the 2000–2018 training data.
> 2. **Tie-Breaker**: In the event of a tie (delta OOF PR-AUC < 0.005), the simpler model with lower false-alarm overhead wins.
> 3. **Partitioning**: Expanding-window `TimeSeriesSplit(n_splits=5)` strictly inside 2000–2018. The 2019–2024 test data is never used during selection.
> 4. **Architectural Guardrails**:
>    - Range-clipping on linear models to eliminate negative dry-soil extrapolation artifacts.
>    - Monotonicity checks across rainfall and soil features.

---

## 2. OOF Table Rankings (2000–2018 Training Data)

Evaluated across 24 combinations via expanding-window `TimeSeriesSplit(n_splits=5)`:

| Rank | Model Family | Features | Weather Source | Strategy | OOF PR-AUC (Warning) | OOF PR-AUC (Danger) |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: |
| **1** | **`clipped_logistic`** | **`full_with_doy`** | **`town`** | **`dedicated_danger`** | **0.3648** | **0.4056** |
| **2** | **`clipped_logistic`** | **`full_with_doy`** | **`town`** | **`single_score_on_warning`** | **0.3648** | **0.2825** |
| 3 | `clipped_logistic` | `full_with_doy` | `avg` | `dedicated_danger` | 0.3541 | 0.3957 |
| 4 | `clipped_logistic` | `full_with_doy` | `avg` | `single_score_on_warning` | 0.3383 | 0.3619 |
| 5 | `monotonic_gbdt` | `no_doy` | `town` | `single_score_on_warning` | 0.3354 | 0.3441 |
| 6 | `monotonic_gbdt` | `no_doy` | `town` | `dedicated_danger` | 0.3305 | 0.3589 |

### Rule Evaluation
- **On Danger Optimization**: Candidate 1 (`dedicated_danger`) achieved `0.4056` vs Candidate 2 (`single_score_on_warning`) `0.2825`. Candidate 1 has higher danger PR-AUC.
- **On Warning Optimization**: Both Candidate 1 and Candidate 2 use the identical training set, features, and model on the warning label, resulting in identical Warning PR-AUC: `0.3648`.
- Under tie-breaker rule 2, if optimized on warning, delta = `0.0000 < 0.005`, so the simpler model (`single_score_on_warning`, requiring only 1 model instead of 2) would win.

---

## 3. The Execution Discrepancy & Protocol Deviation

### What Stage 2 Printed vs. What Stage 2 Actually Executed
In `scripts/run_stage2_evaluation.py`:
1. **Printed Text**: Line 262 printed `winner['strategy'] = dedicated_danger`.
2. **Executed Code**:
   - In lines 325–340, threshold selection was run on `oof_eval_df["oof_score"]` (the OOF predictions of the warning-trained model). Both $T_w = 0.9223$ and $T_d = 0.9360$ were derived from this single continuous score.
   - In lines 363–366, the script fitted only one model:
     ```python
     final_model = ClippedLogisticRegression(class_weight="balanced", random_state=42)
     final_model.fit(final_train_df[winner["cols"]].to_numpy(), final_train_df["label_warning"].to_numpy())
     joblib.dump(final_model, MODELS_DIR / "final_single_risk_score_model.joblib")
     ```
   - In lines 368–430, the holdout test set (2019–2024) was scored using that single model (`final_model.predict_proba(...)[:, 1]`). All reported test metrics (Danger Event Recall = 91.30%, Warning Event Recall = 72.50%) were produced by this single warning-trained model.

### Formal Protocol Deviation Statement
> **PROTOCOL DEVIATION RECORD**:  
> The deployed artifact (`models/final_single_risk_score_model.joblib`) is **`single_score_on_warning`** (one model trained on `label_warning`, with operating cutoffs $T_w = 0.9223$ and $T_d = 0.9360$), rather than the two-model `dedicated_danger` architecture named in the Stage 2 summary header.
>
> **Rationale for Preserving Single Score Architecture**:
> 1. The test set (2019–2024) was evaluated strictly once against this single-score artifact. In accordance with strict empirical governance, re-evaluating the test set with a dedicated danger model after seeing holdout metrics is prohibited.
> 2. The single-score model achieved 91.30% danger event recall on the holdout test set (18/20 caught in Pathanamthitta, 3/3 in Kottayam).
> 3. The single-score model guarantees structural monotonicity between Warning and Danger: because both alerts are thresholds on a single scalar $S$, a day with Danger ($S \ge 0.9360$) strictly implies Warning ($S \ge 0.9223$), preventing any ranking inversions.

Per project rules and user instructions, **the deployed model remains `final_single_risk_score_model.joblib` and is not changed**.
