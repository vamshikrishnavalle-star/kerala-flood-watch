# AI-Powered Disaster Prediction and Emergency Response System

An AI-driven flood prediction and real-time emergency response platform built with Python 3.11, FastAPI, Machine Learning (XGBoost, SVM, SHAP), and a lightweight interactive web dashboard.

---

## Project Structure

```text
.
â”œâ”€â”€ .agent/
â”‚   â”œâ”€â”€ rules/
â”‚   â”‚   â””â”€â”€ project-rules.md       # Standing project guidelines
â”‚   â””â”€â”€ workflows/
â”‚       â”œâ”€â”€ run-checks.md          # /run-checks workflow
â”‚       â”œâ”€â”€ new-feature.md         # /new-feature workflow
â”‚       â”œâ”€â”€ report-metrics.md      # /report-metrics workflow
â”‚       â””â”€â”€ commit-phase.md        # /commit-phase workflow
â”œâ”€â”€ docs/
â”‚   â”œâ”€â”€ PRD.md                     # Product Requirements Document
â”‚   â””â”€â”€ antigravity-implementation-guide.md
â”œâ”€â”€ data/                          # Raw & processed data (git-ignored)
â”‚   â”œâ”€â”€ raw/
â”‚   â””â”€â”€ processed/
â”œâ”€â”€ notebooks/                     # Exploratory analysis notebooks
â”œâ”€â”€ scripts/                       # Training, evaluation & simulation scripts
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ config.py                  # Pydantic environment configuration loader
â”‚   â”œâ”€â”€ ingest/                    # Weather & hydrological data ingestion
â”‚   â”œâ”€â”€ features/                  # Leak-free feature engineering pipeline
â”‚   â”œâ”€â”€ models/                    # ML models, calibration, and SHAP explainability
â”‚   â”œâ”€â”€ api/                       # FastAPI application & endpoints
â”‚   â”œâ”€â”€ alerts/                    # Telegram alert dispatching logic
â”‚   â””â”€â”€ advisory/                  # Template & LLM advisory generation
â”œâ”€â”€ web/                           # Dashboard UI (HTML, CSS, Leaflet, Chart.js)
â”œâ”€â”€ tests/                         # Automated test suite
â”‚   â”œâ”€â”€ __init__.py
â”‚   â””â”€â”€ test_health.py             # Phase 0 smoke test
â”œâ”€â”€ .env.example                   # Environment configuration template
â”œâ”€â”€ .gitignore
â”œâ”€â”€ requirements.txt
â””â”€â”€ README.md
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


Note: before running the label script, copy configs/danger_levels.csv to data/raw/labels/cwc/danger_levels_manual.csv. The label script is the final version of an iterative process; earlier versions are in scripts/archive/.
