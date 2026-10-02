# Joblib Artifact Inspection & Architecture Report
Artifact Path: models/final_single_risk_score_model.joblib
SHA256: 3089cdac1d8ef3ba7ed165cf01f70f971224d7a68b545ce06520ac1ab501761e

## 1. Object Type & Attributes
- Python Object Type: <class '__main__.ClippedLogisticRegression'>
- Object Module: __main__.ClippedLogisticRegression
- Object Attributes in `__dict__`: ['class_weight', 'random_state', 'pipeline', 'min_vals', 'max_vals', 'classes_']
- Class Weight: balanced
- Random State: 42
- Classes in Classifier: [0, 1]

## 2. Where Model Components & Parameters Are Stored
- Scaler Pipeline Step: `model.pipeline.named_steps['scaler']` (<class 'sklearn.preprocessing._data.StandardScaler'>)
  - Scaler Mean: Array of shape (9,)
  - Scaler Scale: Array of shape (9,)
- Classifier Pipeline Step: `model.pipeline.named_steps['clf']` (<class 'sklearn.linear_model._logistic.LogisticRegression'>)
  - Standardized Coefficients: Array of shape (1, 9)
  - Standardized Intercept: -3.8292359086896908
- Clip Ranges: Stored in `model.min_vals` (shape (9,)) and `model.max_vals` (shape (9,))

## 3. Where Thresholds & Feature Order Are Stored
- Feature Order: NOT stored in the .joblib artifact. Feature order was hardcoded in `run_stage2_evaluation.py` as `['rain_1d', 'rain_3d', 'rain_7d', 'rain_14d', 'rain_30d', 'soil_0_7_t1', 'soil_7_28_t1', 'sin_doy', 'cos_doy']`.
- Thresholds (0.9223 / 0.9360): NOT stored in the .joblib artifact. They were derived from the OOF predictions during evaluation and recorded in `run_stage2_evaluation.py`.

## 4. Class Definition & API Importability Vulnerability
- Definition Location: `ClippedLogisticRegression` was defined directly in the `__main__` scope of `scripts/run_stage2_evaluation.py`.
- Vulnerability: When unpickled in another module (such as a FastAPI backend or test suite), Python attempts to import `__main__.ClippedLogisticRegression`, raising `AttributeError: module '__main__' has no attribute 'ClippedLogisticRegression'` unless explicitly patched.
- Remediation: Exporting all fitted weights, clip bounds, thresholds, and metadata to a decoupled `models/scorer_v2.json` completely eliminates this pickle vulnerability, requires zero custom unpickling code, and makes inference 100% transparent and portable.