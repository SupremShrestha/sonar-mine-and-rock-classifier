"""
Loads the trained sonar model once and exposes predict() / validate_feature_row().

The artifacts are loaded at startup (see PredictorConfig.ready) so a prediction
request never pays the cost of reading them from disk.
"""
import json
import warnings
from pathlib import Path

import joblib
import numpy as np
from sklearn.exceptions import InconsistentVersionWarning

ML_MODELS_DIR = Path(__file__).resolve().parent / "ml_models"

N_FEATURES = 60
FEATURE_MIN = 0.0
FEATURE_MAX = 1.0
LABEL_NAMES = {"M": "Mine", "R": "Rock"}

_model = None
_scaler = None
_label_encoder = None
_sample_rows = None


def load_artifacts():
    global _model, _scaler, _label_encoder, _sample_rows

    with warnings.catch_warnings():
        # The artifacts were saved with scikit-learn 1.6.1. Accuracy on the
        # held-out rows was checked to be unchanged on newer versions; re-check
        # any time with:  python manage.py check_model
        warnings.simplefilter("ignore", InconsistentVersionWarning)
        _model = joblib.load(ML_MODELS_DIR / "sonar_model.joblib")
        _scaler = joblib.load(ML_MODELS_DIR / "sonar_scaler.joblib")
        _label_encoder = joblib.load(ML_MODELS_DIR / "sonar_label_encoder.joblib")

    with open(ML_MODELS_DIR / "sample_rows.json") as f:
        _sample_rows = json.load(f)


def get_sample_rows():
    if _sample_rows is None:
        load_artifacts()
    return _sample_rows


def predict(features):
    """Classify one row of 60 sonar values (freq_1 ... freq_60).

    Returns a dict with predicted_label ('M'/'R'), predicted_name,
    confidence (probability of the predicted class) and class_probabilities.
    """
    if _model is None:
        load_artifacts()

    X = np.array(features, dtype=float).reshape(1, -1)
    X_scaled = _scaler.transform(X)

    predicted = _label_encoder.inverse_transform(_model.predict(X_scaled))[0]
    probabilities = {
        str(label): float(p)
        for label, p in zip(_label_encoder.classes_, _model.predict_proba(X_scaled)[0])
    }

    return {
        "predicted_label": str(predicted),
        "predicted_name": LABEL_NAMES.get(str(predicted), str(predicted)),
        "confidence": probabilities[str(predicted)],
        "class_probabilities": probabilities,
    }


def validate_feature_row(values):
    """Check that `values` is a valid 60-number sonar row.

    Returns (cleaned_floats, None) on success or (None, error_message) on failure.
    """
    if len(values) != N_FEATURES:
        return None, f"Expected exactly {N_FEATURES} numeric values, got {len(values)}."

    cleaned = []
    for i, raw in enumerate(values, start=1):
        try:
            v = float(raw)
        except (TypeError, ValueError):
            return None, f"Column {i} ('{raw}') is not a valid number."
        if not (FEATURE_MIN <= v <= FEATURE_MAX):
            return None, (
                f"Column {i} = {v} is outside the expected "
                f"[{FEATURE_MIN}, {FEATURE_MAX}] range for sonar energy values."
            )
        cleaned.append(v)

    return cleaned, None