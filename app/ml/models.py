"""ML model loader, predictor and explainer for ChronoCare AI.

Two models are served:
  - ``duration_model``  : LightGBM regressor – appointment duration (minutes)
  - ``noshow_model``    : LightGBM classifier – P(no-show)

Both fall back to rule-based heuristics when not yet trained.
SHAP explanations are generated on demand.
"""
from __future__ import annotations

import logging
import os
import warnings
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np

# Suppress cosmetic sklearn/LightGBM warnings about feature names
warnings.filterwarnings("ignore", message="X does not have valid feature names")
warnings.filterwarnings("ignore", message="LightGBM binary classifier with TreeExplainer")

from app.ml.features import (
    DURATION_FEATURES,
    NOSHOW_FEATURES,
    SPECIALTY_AVG_DURATION,
    DEFAULT_AVG_DURATION,
    GLOBAL_NOSHOW_RATE,
    extract_duration_features,
    extract_noshow_features,
)

logger = logging.getLogger(__name__)

MODELS_DIR = Path(os.getenv("MODELS_DIR", "models"))

# ── Singleton model containers ────────────────────────────────────────────
_duration_model: Any = None
_noshow_model: Any = None
_duration_explainer: Any = None
_noshow_explainer: Any = None
_models_loaded = False


# ── Loading ───────────────────────────────────────────────────────────────

def load_models() -> None:
    """Load trained LightGBM models from *MODELS_DIR*.

    Silently skips missing files – the fallback predictors are used instead.
    """
    global _duration_model, _noshow_model
    global _duration_explainer, _noshow_explainer, _models_loaded

    dur_path = MODELS_DIR / "duration_model.pkl"
    nsh_path = MODELS_DIR / "noshow_model.pkl"

    if dur_path.exists():
        try:
            _duration_model = joblib.load(dur_path)
            logger.info("Duration model loaded from %s", dur_path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load duration model: %s", exc)
    else:
        logger.warning("Duration model not found at %s – using fallback", dur_path)

    if nsh_path.exists():
        try:
            _noshow_model = joblib.load(nsh_path)
            logger.info("No-show model loaded from %s", nsh_path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load no-show model: %s", exc)
    else:
        logger.warning("No-show model not found at %s – using fallback", nsh_path)

    # Build SHAP explainers eagerly to avoid first-request lag
    if _duration_model is not None:
        try:
            import shap
            _duration_explainer = shap.TreeExplainer(_duration_model)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SHAP duration explainer init failed: %s", exc)

    if _noshow_model is not None:
        try:
            import shap
            _noshow_explainer = shap.TreeExplainer(_noshow_model)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SHAP no-show explainer init failed: %s", exc)

    _models_loaded = True


def models_ready() -> dict[str, bool]:
    return {
        "duration_model": _duration_model is not None,
        "noshow_model": _noshow_model is not None,
    }


# ── Explanation helpers ───────────────────────────────────────────────────

def _build_explanation(
    explainer: Any,
    feature_names: list[str],
    X: np.ndarray,
    top_n: int = 5,
) -> dict[str, Any]:
    """Return a SHAP-based explanation dict for a single prediction row."""
    try:
        shap_values = explainer.shap_values(X)
        # For classifiers shap_values may be a list [class0, class1]
        if isinstance(shap_values, list):
            sv = shap_values[1][0]
        else:
            sv = shap_values[0]
        base = float(explainer.expected_value) if not isinstance(
            explainer.expected_value, (list, np.ndarray)
        ) else float(explainer.expected_value[1])

        features_list = []
        for name, val, contrib in zip(feature_names, X[0], sv):
            features_list.append(
                {"name": name, "value": round(float(val), 3), "contribution": round(float(contrib), 3)}
            )
        features_list.sort(key=lambda x: abs(x["contribution"]), reverse=True)

        return {
            "base_value": round(base, 3),
            "top_features": features_list[:top_n],
        }
    except Exception as exc:  # noqa: BLE001
        logger.debug("SHAP explanation failed: %s", exc)
        return {"base_value": None, "top_features": []}


def _generate_nl_explanation_duration(features: dict[str, Any], prediction: float) -> str:
    parts = []
    comorbidities = features.get("comorbidity_count", 0)
    if comorbidities >= 3:
        parts.append(f"high comorbidity count ({int(comorbidities)})")
    visit_type = features.get("visit_type", "follow-up")
    if visit_type == "new":
        parts.append("first-time visit")
    if features.get("physician_workload", 0) >= 6:
        parts.append("high physician workload")
    specialty = features.get("specialty", "")
    if specialty in ("psychiatry", "oncology", "neurology"):
        parts.append(f"{specialty} appointment")
    base = "Longer duration predicted" if prediction > 25 else "Standard duration predicted"
    reason = (" due to " + ", ".join(parts)) if parts else ""
    return f"{base}{reason}."


def _generate_nl_explanation_noshow(features: dict[str, Any], probability: float) -> str:
    parts = []
    lead_time = float(features.get("lead_time_days") or 7)
    if lead_time <= 2:
        parts.append(f"short lead time ({int(lead_time)} days)")
    elif lead_time >= 21:
        parts.append(f"long lead time ({int(lead_time)} days)")
    visit_type = features.get("visit_type", "follow-up")
    if visit_type == "new":
        parts.append("new patient with no attendance history")
    no_show_rate = float(features.get("patient_no_show_rate") or 0.15)
    if no_show_rate > 0.3:
        parts.append(f"high historical no-show rate ({no_show_rate:.0%})")
    risk = "elevated" if probability > 0.4 else ("moderate" if probability > 0.2 else "low")
    reason = (" due to " + ", ".join(parts)) if parts else ""
    return f"No-show risk is {risk} ({probability:.0%}){reason}."


# ── Fallback predictors ───────────────────────────────────────────────────

def _fallback_duration(data: dict[str, Any]) -> tuple[float, float, float]:
    """Returns (lower, prediction, upper) using specialty average."""
    specialty = data.get("specialty", "general_practice").lower()
    base = SPECIALTY_AVG_DURATION.get(specialty, DEFAULT_AVG_DURATION)
    # New patients and those with many comorbidities take longer
    adjustment = 0.0
    if data.get("visit_type") == "new":
        adjustment += 4.0
    adjustment += min(float(data.get("comorbidity_count", 0)) * 1.5, 10.0)
    pred = base + adjustment
    return pred - 6.0, pred, pred + 6.0


def _fallback_noshow(data: dict[str, Any]) -> float:
    """Returns no-show probability using baseline adjustments."""
    prob = float(data.get("patient_no_show_rate", GLOBAL_NOSHOW_RATE))
    lead_time = float(data.get("lead_time_days", 7))
    if lead_time <= 1:
        prob += 0.05
    elif lead_time >= 30:
        prob += 0.08
    if data.get("visit_type") == "new":
        prob += 0.03
    return min(max(prob, 0.05), 0.95)


# ── Public API ────────────────────────────────────────────────────────────

def predict_duration(data: dict[str, Any]) -> dict[str, Any]:
    """Predict appointment duration.

    Returns:
        dict with keys:
          - ``predicted_duration_minutes`` (float)
          - ``lower_bound`` (float)
          - ``upper_bound`` (float)
          - ``confidence_pct`` (float)
          - ``explanation`` (dict)
          - ``nl_explanation`` (str)
          - ``used_fallback`` (bool)
    """
    X = extract_duration_features(data)

    used_fallback = _duration_model is None

    if not used_fallback:
        try:
            pred = float(_duration_model.predict(X)[0])
            # Use quantile regressors if stored alongside main model
            lower = pred - 6.0
            upper = pred + 6.0
            if hasattr(_duration_model, "predict_quantile"):
                lower = float(_duration_model.predict_quantile(X, 0.1)[0])
                upper = float(_duration_model.predict_quantile(X, 0.9)[0])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Duration model predict error: %s — using fallback", exc)
            used_fallback = True

    if used_fallback:
        lower, pred, upper = _fallback_duration(data)

    pred = max(5.0, pred)
    lower = max(3.0, lower)
    upper = max(pred + 1, upper)
    interval_width = upper - lower
    confidence_pct = max(0.0, 100.0 - interval_width * 1.5)

    expl = {}
    if _duration_explainer is not None and not used_fallback:
        expl = _build_explanation(_duration_explainer, DURATION_FEATURES, X)

    return {
        "predicted_duration_minutes": round(pred, 1),
        "lower_bound": round(lower, 1),
        "upper_bound": round(upper, 1),
        "confidence_pct": round(confidence_pct, 1),
        "explanation": expl,
        "nl_explanation": _generate_nl_explanation_duration(data, pred),
        "used_fallback": used_fallback,
    }


def predict_noshow(data: dict[str, Any]) -> dict[str, Any]:
    """Predict no-show probability.

    Returns:
        dict with keys:
          - ``no_show_probability`` (float 0-1)
          - ``risk_category`` (str: low/medium/high)
          - ``explanation`` (dict)
          - ``nl_explanation`` (str)
          - ``used_fallback`` (bool)
    """
    X = extract_noshow_features(data)
    used_fallback = _noshow_model is None

    if not used_fallback:
        try:
            prob = float(_noshow_model.predict_proba(X)[0][1])
        except Exception as exc:  # noqa: BLE001
            logger.warning("No-show model predict error: %s — using fallback", exc)
            used_fallback = True

    if used_fallback:
        prob = _fallback_noshow(data)

    # Cap min risk at 5% per requirements
    prob = max(0.05, min(0.95, prob))

    if prob < 0.2:
        risk = "low"
    elif prob < 0.4:
        risk = "medium"
    else:
        risk = "high"

    expl = {}
    if _noshow_explainer is not None and not used_fallback:
        expl = _build_explanation(_noshow_explainer, NOSHOW_FEATURES, X)

    return {
        "no_show_probability": round(prob, 4),
        "risk_category": risk,
        "explanation": expl,
        "nl_explanation": _generate_nl_explanation_noshow(data, prob),
        "used_fallback": used_fallback,
    }
