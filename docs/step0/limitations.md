# System & Model Limitations (Authoritative Audit)

**Date**: 2026-10-03  
**Governing Documents**: `docs/model-selection-protocol.md`, `docs/protocol-reconciliation.md`

---

## 1. Single Risk Score Architecture & Danger Discrimination Trade-off
- **Protocol Winner Discrepancy**: The dedicated danger model achieved an Out-of-Fold (OOF) Danger PR-AUC of **0.4056** versus **0.2825** for the deployed single-score architecture. 
- **Operational Impact**: Danger discrimination in the deployed single-score model is weaker than a specialized danger classifier would have achieved. However, because the single-score model was evaluated on the 2019–2024 holdout test set (achieving 91.30% danger event recall) and guarantees ranking monotonicity (Danger strictly implies Warning), **no model change was made** in order to honor strict holdout governance.

## 2. Soil Layer Multi-Collinearity & Inverse Topsoil Sensitivity
- **Opposing Layer Signs**: In `models/scorer_v2.json`, the standardized coefficient for topsoil (`soil_0_7_t1`) is **-0.5995 (NEGATIVE)** while rootzone soil (`soil_7_28_t1`) is **+1.0401 (POSITIVE)**.
- **Physical Co-drying**: When both layers dry together realistically, net sensitivity is positive ($0.0588$ at extreme dry soil to $0.1982$ at saturated soil with zero rain).
- **Artificial Decoupling Anomaly**: If an artificial synthetic input has dry topsoil ($0.239$) and saturated subsoil ($0.518$), the negative topsoil weight adds $+2.26$ to the logit.
- **Bounding**: Under zero rain, the maximum possible risk score across any soil combination within the clipped training bounds is **0.2050**, which is far below the warning threshold ($0.9223$) and danger threshold ($0.9360$).

## 3. Pre-2015 Historical Sampling Bias & Positives Undercounting
- **Schedule Thinning**: Empirical analysis of 16,496 pre-2015 Kallooppara timestamps confirms that **99.73%** of observations were taken strictly at `[8, 13, 18]` IST (08:00, 13:00, 18:00).
- **Missed Danger Crests**: Controlled thinning tests on 2,036 post-2015 hourly days prove that a 3-reading daily protocol **misses 24.64% of true danger exceedance days** (17 of 69 days missed) and attenuates recorded peak water levels by up to $1.43\text{ meters}$.
- **Exceedance Rate Disparity**: Thinning explains only part of the 1.79% vs 3.75% rate difference between pre-2015 (1.79% danger days) and post-2015 (3.75% danger days); intensified climate-driven extreme monsoon rainfall post-2018 also contributed significantly.

## 4. Unobserved Exceedances Due to Telemetry Outages
- **Gaps During Floods**: In July 2021, a telemetry sensor dropout on **2021-07-19** directly followed consecutive danger/warning exceedance days on **2021-07-16** ($6.10\text{ m}$), **2021-07-17** ($6.08\text{ m}$), and **2021-07-18** ($5.01\text{ m}$).
- **Impact**: Some true flood exceedances during extreme events remain unobserved and unrecorded in the benchmark ground truth.

## 5. Unverified 2026 Alert Blocks
- **Data Latency**: Most 2026 alert blocks are unverified because 2026 CWC data was unavailable (India-WRIS real-time telemetry for 2026 has not completed official quality-controlled validation). Operational alert dates in 2026 cannot be evaluated against confirmed flood crests.

## 6. Kottayam Basin Provisional Status
- **Short Telemetry History**: The Kidangoor gauge on the Meenachil River has zero telemetric records prior to June 6, 2015.
- **Small Sample Size**: With only $N_{\text{tr,pos}} = 7$ danger days and $N_{\text{test,events}} = 3$ test danger events, metrics for Kottayam carry wide uncertainty margins and are explicitly flagged as `[PROVISIONAL - Small Sample]`.
