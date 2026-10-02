# AI-Powered Disaster Prediction & Emergency Response System

An AI-driven flood prediction and early warning platform for Kerala river basins built with Python, CWC River Stage Telemetry, Open-Meteo ERA5 Reanalysis, Machine Learning, and an interactive dashboard.

---

## Project Structure

```text
.
├── .agent/
│   ├── rules/
│   │   └── project-rules.md          # Standing project guidelines
│   └── workflows/
│       ├── run-checks.md             # /run-checks workflow
│       ├── new-feature.md            # /new-feature workflow
│       ├── report-metrics.md         # /report-metrics workflow
│       └── commit-phase.md           # /commit-phase workflow
├── docs/
│   ├── PRD.md                        # Product Requirements Document
│   ├── data-notes.md                 # Data provenance, label definitions & caveats
│   ├── data-audit.md                 # Dataset audit & event-level positives
│   └── label-sourcing-report.md      # CWC bulletin levels & datum validation
├── data/                             # Data directory (git-ignored raw binaries)
│   ├── raw/
│   │   ├── labels/cwc/               # Raw CWC water level bulletins & series
│   │   ├── historical/               # ERA5 weather & soil moisture series
│   │   └── station_zone_map.csv      # Verified gauge-to-district mapping
│   └── processed/
│       ├── dataset.parquet           # Clean leak-free training dataset
│       └── metrics.csv               # Model evaluation metrics matrix
├── models/                           # Trained ML model artifacts (.joblib)
├── scripts/                          # Ingestion, audit, training & verification scripts
│   ├── fetch_data.py                 # Weather data ingestion pipeline
│   ├── build_step2.py                # Dataset builder
│   ├── audit_dataset.py              # Dataset validation & cluster audit
│   └── train_and_evaluate.py         # Leak-free training & holdout evaluation
├── src/
│   ├── __init__.py
│   ├── config.py                     # Pydantic environment configuration
│   ├── ingest/                       # Weather & hydrological ingestion modules
│   │   ├── client.py                 # Open-Meteo API client with retry & cache
│   │   ├── historical.py             # Historical weather extractor
│   │   └── zones.py                  # Kerala flood zone definitions & coords
│   ├── features/                     # Feature extraction pipeline
│   └── models/                       # Model definitions & inference
└── tests/
    └── test_dataset.py               # Automated data integrity & leak-prevention tests
```

---

## System Overview

1. **Hydrological Ground-Truth**:
   - Official river gauge thresholds from Central Water Commission (CWC) Daily Flood Bulletins.
   - Verified datum series (`HHS`) for monitored river stations (Kallooppara on Manimala River, Kidangoor on Meenachil River).
   - Dynamic sampling regime handling (3-readings/day historical vs hourly modern era) with strict NaN dropping and zero synthetic leakage.

2. **Hydrometeorological Feature Pipeline**:
   - Open-Meteo ERA5 Reanalysis archive (2000–2024 continuous).
   - Strictly causal $t-1$ features: 1d, 3d, 7d, 14d, 30d rolling rainfall sums, multi-layer soil moisture, and seasonal day-of-year embeddings.
   - Zero day-$t$ contamination.

3. **Machine Learning & Early Warning**:
   - Temporal holdout evaluation: Train (2000–2018), Test (2019–2024).
   - Baseline, Logistic Regression, and Class-Weighted Gradient Boosting models.
   - Evaluated on Danger and Warning thresholds with event-level recall ($[t_{start}-2, t_{end}]$) and false alarm tracking.

---

## Quickstart

### 1. Environment Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Data Pipeline & Audit
```bash
python scripts/fetch_data.py --zone pathanamthitta_kozhencherry --start-year 2000 --end-year 2024
python scripts/fetch_data.py --zone kottayam_pala --start-year 2000 --end-year 2024
python scripts/audit_dataset.py
```

### 3. Run Tests
```bash
pytest tests/ -v
```

### 4. Train Models & Evaluate
```bash
python scripts/train_and_evaluate.py
```
