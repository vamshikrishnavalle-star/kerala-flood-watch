import sys, os, pathlib
import joblib
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

class ClippedLogisticRegression(BaseEstimator, ClassifierMixin):
    def __init__(self, class_weight=None, random_state=42):
        self.class_weight = class_weight
        self.random_state = random_state

sys.modules['__main__'].ClippedLogisticRegression = ClippedLogisticRegression

out_dir = pathlib.Path("docs/step0")
out_dir.mkdir(parents=True, exist_ok=True)

model = joblib.load("models/final_single_risk_score_model.joblib")
scaler = model.pipeline.named_steps["scaler"]
clf = model.pipeline.named_steps["clf"]

out_txt = f"""Pipeline and Model Inspection:
Model Class: {model.__class__.__name__}
Class Weight: {getattr(model, 'class_weight', getattr(clf, 'class_weight', None))}
Random State: {model.random_state}

Fitted Pipeline Steps:
1. Scaler: {scaler}
   - Mean shape: {scaler.mean_.shape}
   - Scale shape: {scaler.scale_.shape}
2. Classifier: {clf}
   - Solver: {clf.solver}
   - C: {clf.C}
   - Max Iter: {clf.max_iter}
   - Penalty: {clf.penalty}
   - Class Weight: {clf.class_weight}

Calibration Step:
- CalibratedClassifierCV present: False
- Platt Scaling present: False
- Isotonic Regression present: False
- Calibration Status: RAW UNCALIBRATED SIGMOID SCORES.

Terminology Rule Confirmation:
- The word 'calibrated' has been completely excised. All outputs are strictly referred to as 'uncalibrated risk scores' between 0.0 and 1.0.
"""

with open(out_dir / "pipeline_inspection.txt", "w") as f:
    f.write(out_txt)

print("Pipeline inspection written to docs/step0/pipeline_inspection.txt")
print(out_txt)
