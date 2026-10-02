# AI-Powered Disaster Prediction & Emergency Response System

An empirical AI-driven flood prediction and early warning platform for Kerala river basins built with Python, CWC River Stage Telemetry, Open-Meteo ERA5 Reanalysis, Machine Learning, FastAPI, and an interactive dashboard.

---

## Model Benchmark & Evaluation (Authoritative Step 0 Audit)

> [!IMPORTANT]
> The table below reflects the final, locked **Step 0 / Stage 2 empirical evaluation** using `models/scorer_v2.json` on the expanding-window training period (2000–2018) and the single-pass holdout test set (2019–2024). All earlier benchmark tables are **SUPERSEDED**.
> 
> - **Operational Thresholds**: Warning Threshold $T_w = 0.9223$, Danger Threshold $T_d = 0.9360$.
> - **Terminology Standard**: All scores are uncalibrated continuous risk scores $[0.0, 1.0]$. The words "probability" and "calibrated" are not used.

### Holdout Test Set Performance (2019–2024, Single-Pass Evaluation)

| Basin / Station | Status | Target | Alert Days | True Pos Days | Day Precision | Caught Events / Total | Event Recall (95% CI) | Alert Episodes | Episode Precision | False Alarm Rate |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Pathanamthitta**<br>*(Manimala / Kallooppara)* | **VALIDATED** | Warning | 181 | 62 | 34.25% | 21 / 32 | **65.62%** `[50.0%, 81.2%]` | 57 | 36.84% | 19.8 days/yr |
| | | Danger | 167 | 40 | 23.95% | 18 / 20 | **90.00%** `[75.0%, 100.0%]` | 57 | 31.58% | 21.2 days/yr |
| **Kottayam**<br>*(Meenachil / Kidangoor)* | **PROVISIONAL**<br>*(Small Sample)* | Warning | 228 | 26 | 11.40% | 8 / 8 | **100.00%** `[100.0%, 100.0%]` | 59 | 13.56% | 33.7 days/yr |
| | | Danger | 209 | 7 | 3.35% | 3 / 3 | **100.00%** `[100.0%, 100.0%]` | 57 | 5.26% | 33.7 days/yr |
| **POOLED COMBINED** | — | Warning | 409 | 88 | 21.52% | 29 / 40 | **72.50%** `[57.5%, 85.0%]` | 116 | 25.00% | 53.5 days/yr |
| | | Danger | 376 | 47 | 12.50% | 21 / 23 | **91.30%** `[78.3%, 100.0%]` | 114 | 18.42% | 54.8 days/yr |

*Test PR-AUC*: Warning PR-AUC = `0.4269`, Danger PR-AUC = `0.2689`.

---

## Out-of-Fold (OOF) Model Selection (2000–2018 Training Record)

- **Partitioning**: Expanding-window `TimeSeriesSplit(n_splits=5)` strictly inside 2000–2018 ($N=8,146$ days).
- **Architecture**: `ClippedLogisticRegression(class_weight='balanced')` with feature clipping to empirical training bounds $[x_{\min}, x_{\max}]$.
- **OOF Performance**:
  - Warning Threshold ($T_w = 0.9223$): Event Recall = **76.36%** (42/55 events caught, 132 alert episodes, Episode Precision = 31.82%).
  - Danger Threshold ($T_d = 0.9360$): Event Recall = **76.92%** (20/26 events caught, 123 alert episodes, Episode Precision = 16.26%).
- **Formal Protocol Deviation**: Documented in [`docs/protocol-reconciliation.md`](docs/protocol-reconciliation.md). The deployed model is a single warning-trained score with two thresholds ($T_w=0.9223, T_d=0.9360$), guaranteeing ranking monotonicity ($S \ge T_d \implies S \ge T_w$).

---

## System Architecture

```text
.
├── docs/
│   ├── step0/                        # Step 0 verified audit reports & CSVs
│   │   ├── dataset_per_zone_year.csv # Authoritative per-zone dataset breakdown
│   │   ├── positives_reconciliation.csv # Reconciled positive counts
│   │   ├── precision_recall_audit.csv   # Exact day and episode precision/recall table
│   │   ├── limitations.md            # System, data, and model limitations
│   │   └── thinning_test_results.txt # Pre-2015 3-reading sampling bias test
│   ├── model-selection-protocol.md   # Pre-registered selection protocol
│   └── protocol-reconciliation.md    # Formal protocol deviation record
├── models/
│   ├── scorer_v2.json                # Standalone machine-precision inference configuration
│   └── final_single_risk_score_model.joblib # Serialized model artifact
├── src/
│   ├── models/
│   │   └── inference.py              # Operational inference engine (loads scorer_v2.json)
│   ├── api/
│   │   └── main.py                   # FastAPI REST backend application
│   └── ingest/
│       └── zones.py                  # Kerala flood zone definitions & coordinates
└── tests/
    └── test_phase5_api.py            # Comprehensive Phase 5 test suite
```

---

## Operational REST API Endpoints

The FastAPI service runs on port `8000`:

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/status` | `GET` | System health, uptime, model version, and data freshness. |
| `/api/zones` | `GET` | Monitored Kerala zones, coordinates, and validation status. |
| `/api/predict/{zone_slug}` | `GET` | Day 0 validated risk score, alert level, and Days 1–3 experimental outlook. |
| `/api/metrics` | `GET` | Dynamic precision, recall, and false-alarm metrics from Step 0 CSVs. |
| `/api/whatif` | `GET` | Bounded sensitivity analysis for hypothetical rainfall added to yesterday. |
| `/api/history` | `GET` | Historical predictions logged to SQLite. |

---

## Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Test Suite
```bash
pytest tests/test_phase5_api.py -v
```

### 3. Launch FastAPI Server
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```