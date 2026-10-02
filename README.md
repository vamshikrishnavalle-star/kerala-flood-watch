# AI-Powered Disaster Prediction and Emergency Response System

An AI-driven flood prediction and real-time emergency response platform built with Python 3.11, FastAPI, Machine Learning (XGBoost, SVM, SHAP), and a lightweight interactive web dashboard.

---

## Project Structure

```text
.
├── .agent/
│   ├── rules/
│   │   └── project-rules.md       # Standing project guidelines
│   └── workflows/
│       ├── run-checks.md          # /run-checks workflow
│       ├── new-feature.md         # /new-feature workflow
│       ├── report-metrics.md      # /report-metrics workflow
│       └── commit-phase.md        # /commit-phase workflow
├── docs/
│   ├── PRD.md                     # Product Requirements Document
│   └── antigravity-implementation-guide.md
├── data/                          # Raw & processed data (git-ignored)
│   ├── raw/
│   └── processed/
├── notebooks/                     # Exploratory analysis notebooks
├── scripts/                       # Training, evaluation & simulation scripts
├── src/
│   ├── __init__.py
│   ├── config.py                  # Pydantic environment configuration loader
│   ├── ingest/                    # Weather & hydrological data ingestion
│   ├── features/                  # Leak-free feature engineering pipeline
│   ├── models/                    # ML models, calibration, and SHAP explainability
│   ├── api/                       # FastAPI application & endpoints
│   ├── alerts/                    # Telegram alert dispatching logic
│   └── advisory/                  # Template & LLM advisory generation
├── web/                           # Dashboard UI (HTML, CSS, Leaflet, Chart.js)
├── tests/                         # Automated test suite
│   ├── __init__.py
│   └── test_health.py             # Phase 0 smoke test
├── .env.example                   # Environment configuration template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Getting Started

### 1. Prerequisites
- Python 3.11 (or 3.11+)
- Git

### 2. Environment Setup

#### Create and activate virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Install dependencies
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

Edit `.env` to configure your settings (e.g. `REGION_NAME`, `ALERT_THRESHOLD`). Never commit `.env` to version control.

### 4. Running the Development Server
```bash
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```
- Interactive API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check Endpoint: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 5. Running Tests
```bash
pytest
```
Or for concise output:
```bash
pytest -q
```
