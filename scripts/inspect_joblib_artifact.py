import sys, os, pathlib, hashlib
import joblib

out_dir = pathlib.Path("docs/step0")
out_dir.mkdir(parents=True, exist_ok=True)

class ClippedLogisticRegression:
    pass

sys.modules['__main__'].ClippedLogisticRegression = ClippedLogisticRegression

model_path = pathlib.Path("models/final_single_risk_score_model.joblib")
with open(model_path, "rb") as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()

model = joblib.load(model_path)

scaler = model.pipeline.named_steps["scaler"]
clf = model.pipeline.named_steps["clf"]

report_lines = [
    "# Joblib Artifact Inspection & Architecture Report",
    f"Artifact Path: models/final_single_risk_score_model.joblib",
    f"SHA256: {sha256_hash}\n",
    "## 1. Object Type & Attributes",
    f"- Python Object Type: {type(model)}",
    f"- Object Module: {model.__class__.__module__}.{model.__class__.__name__}",
    f"- Object Attributes in `__dict__`: {list(model.__dict__.keys())}",
    f"- Class Weight: {getattr(model, 'class_weight', None)}",
    f"- Random State: {getattr(model, 'random_state', None)}",
    f"- Classes in Classifier: {getattr(model, 'classes_', None).tolist()}\n",
    "## 2. Where Model Components & Parameters Are Stored",
    f"- Scaler Pipeline Step: `model.pipeline.named_steps['scaler']` ({type(scaler)})",
    f"  - Scaler Mean: Array of shape {scaler.mean_.shape}",
    f"  - Scaler Scale: Array of shape {scaler.scale_.shape}",
    f"- Classifier Pipeline Step: `model.pipeline.named_steps['clf']` ({type(clf)})",
    f"  - Standardized Coefficients: Array of shape {clf.coef_.shape}",
    f"  - Standardized Intercept: {clf.intercept_[0]}",
    f"- Clip Ranges: Stored in `model.min_vals` (shape {model.min_vals.shape}) and `model.max_vals` (shape {model.max_vals.shape})\n",
    "## 3. Where Thresholds & Feature Order Are Stored",
    "- Feature Order: NOT stored in the .joblib artifact. Feature order was hardcoded in `run_stage2_evaluation.py` as `['rain_1d', 'rain_3d', 'rain_7d', 'rain_14d', 'rain_30d', 'soil_0_7_t1', 'soil_7_28_t1', 'sin_doy', 'cos_doy']`.",
    "- Thresholds (0.9223 / 0.9360): NOT stored in the .joblib artifact. They were derived from the OOF predictions during evaluation and recorded in `run_stage2_evaluation.py`.\n",
    "## 4. Class Definition & API Importability Vulnerability",
    "- Definition Location: `ClippedLogisticRegression` was defined directly in the `__main__` scope of `scripts/run_stage2_evaluation.py`.",
    "- Vulnerability: When unpickled in another module (such as a FastAPI backend or test suite), Python attempts to import `__main__.ClippedLogisticRegression`, raising `AttributeError: module '__main__' has no attribute 'ClippedLogisticRegression'` unless explicitly patched.",
    "- Remediation: Exporting all fitted weights, clip bounds, thresholds, and metadata to a decoupled `models/scorer_v2.json` completely eliminates this pickle vulnerability, requires zero custom unpickling code, and makes inference 100% transparent and portable."
]

report_text = "\n".join(report_lines)
(out_dir / "joblib_artifact_inspection.md").write_text(report_text, encoding="utf-8")
print(report_text)
