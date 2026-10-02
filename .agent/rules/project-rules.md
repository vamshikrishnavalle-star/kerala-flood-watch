# Project Rules: Disaster Prediction System
Follow docs/PRD.md (v1.1). Flood is the only required hazard.

## Stack (do not add dependencies without asking)
Python 3.11, FastAPI, SQLAlchemy + SQLite, APScheduler, scikit-learn,
XGBoost, SHAP, joblib. Dashboard: static HTML + vanilla JS, Leaflet,
Chart.js. No Node, no build step.

## Working rules
- Always write an implementation plan first. Keep changes small: one feature per task.
- After every task, run `pytest` and report results honestly.
- Never edit a test just to make it pass. If a test must change, say why.
- Never invent or fabricate data, metrics, or API responses. If data is
  missing, stop and ask.
- Use chronological train/validation/test splits only. Never tune on the test set.
- Training and inference must share one saved feature pipeline (with a test).
- Always report precision, recall, F1, ROC-AUC, PR-AUC, Brier score, and
  false-alarm rate. Never accuracy alone. Flag suspiciously high scores (ROC-AUC > 0.98) as possible leakage.
- The LLM only rephrases model output into advisories. It never decides risk.
  Every LLM call needs a template fallback and error handling.
- Secrets live in `.env`. Never print or commit them.
- Predictions support human decisions: UI shows confidence and a disclaimer.
- Prefer simple, commented code over clever code.
