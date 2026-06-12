"""Training pipeline for ChronoCare AI ML models.

Usage (from project root):
    python -m app.ml.train --data data/synthetic_clinic_data.csv

Or via the helper script:
    python scripts/train_models.py
"""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    mean_absolute_error,
    root_mean_squared_error,
    r2_score,
    roc_auc_score,
    brier_score_loss,
)

logger = logging.getLogger(__name__)

MODELS_DIR = Path(os.getenv("MODELS_DIR", "models"))


def _build_lgbm_duration(X_train: np.ndarray, y_train: np.ndarray):  # type: ignore[return]
    """Train a LightGBM Regressor for duration prediction."""
    from lightgbm import LGBMRegressor  # type: ignore

    model = LGBMRegressor(
        objective="regression",
        num_leaves=31,
        learning_rate=0.05,
        n_estimators=200,
        max_depth=6,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=0.1,
        random_state=42,
        verbose=-1,
    )
    model.fit(X_train, y_train)
    return model


def _build_lgbm_noshow(X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray, y_val: np.ndarray):  # type: ignore[return]
    """Train a LightGBM Classifier for no-show prediction with early stopping."""
    from lightgbm import LGBMClassifier, early_stopping, log_evaluation  # type: ignore

    model = LGBMClassifier(
        objective="binary",
        num_leaves=63,          # deeper trees capture more patterns
        learning_rate=0.02,     # lower LR with more estimators
        n_estimators=1000,      # will be cut short by early stopping
        max_depth=7,
        min_child_samples=15,
        is_unbalance=True,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=0.2,
        random_state=42,
        verbose=-1,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[
            early_stopping(stopping_rounds=50, verbose=False),
            log_evaluation(period=0),
        ],
    )
    return model


def train_models(data_path: str | Path, models_dir: str | Path = MODELS_DIR) -> dict:
    """Train both models and save them to *models_dir*.

    Args:
        data_path: Path to the synthetic CSV dataset.
        models_dir: Directory to save serialised models.

    Returns:
        Dictionary with evaluation metrics for both models.
    """
    from app.ml.features import (
        build_training_dataframe,
        DURATION_FEATURES,
        NOSHOW_FEATURES,
    )

    models_dir = Path(models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading training data from %s …", data_path)
    raw = pd.read_csv(data_path)
    logger.info("Loaded %d records", len(raw))

    records = raw.to_dict(orient="records")
    df = build_training_dataframe(records)
    logger.info("Feature matrix built: %d rows × %d cols", len(df), df.shape[1])

    # ── Duration model ────────────────────────────────────────────────────
    X_dur = df[DURATION_FEATURES].values.astype(np.float32)
    y_dur = df["actual_duration"].values.astype(np.float32)

    X_tr, X_te, y_tr, y_te = train_test_split(X_dur, y_dur, test_size=0.2, random_state=42)
    logger.info("Training duration model …")
    dur_model = _build_lgbm_duration(X_tr, y_tr)

    y_pred_dur = dur_model.predict(X_te)
    dur_metrics = {
        "MAE": round(float(mean_absolute_error(y_te, y_pred_dur)), 3),
        "RMSE": round(float(root_mean_squared_error(y_te, y_pred_dur)), 3),
        "R2": round(float(r2_score(y_te, y_pred_dur)), 3),
    }
    logger.info("Duration model metrics: %s", dur_metrics)

    dur_path = models_dir / "duration_model.pkl"
    joblib.dump(dur_model, dur_path)
    logger.info("Duration model saved to %s", dur_path)

    # ── No-show model ─────────────────────────────────────────────────────
    X_nsh = df[NOSHOW_FEATURES].values.astype(np.float32)
    y_nsh = df["attended"].values.astype(np.int32)
    # Flip: attended=1 means no-show=0 for LightGBM "did not attend" target
    y_nsh_target = (1 - y_nsh)  # 1 = no-show

    X_tr2, X_te2, y_tr2, y_te2 = train_test_split(X_nsh, y_nsh_target, test_size=0.2, random_state=42)
    logger.info("Training no-show model …")
    nsh_model = _build_lgbm_noshow(X_tr2, y_tr2, X_te2, y_te2)

    y_pred_nsh = nsh_model.predict_proba(X_te2)[:, 1]
    nsh_metrics = {
        "AUC_ROC": round(float(roc_auc_score(y_te2, y_pred_nsh)), 3),
        "Brier": round(float(brier_score_loss(y_te2, y_pred_nsh)), 3),
    }
    logger.info("No-show model metrics: %s", nsh_metrics)

    nsh_path = models_dir / "noshow_model.pkl"
    joblib.dump(nsh_model, nsh_path)
    logger.info("No-show model saved to %s", nsh_path)

    return {"duration": dur_metrics, "noshow": nsh_metrics}


# ── CLI entrypoint ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    parser = argparse.ArgumentParser(description="Train ChronoCare AI models")
    parser.add_argument("--data", default="data/synthetic_clinic_data.csv")
    parser.add_argument("--models-dir", default="models")
    args = parser.parse_args()
    results = train_models(args.data, args.models_dir)
    print("\n=== Training Complete ===")
    for model_name, metrics in results.items():
        print(f"\n{model_name.upper()} MODEL:")
        for k, v in metrics.items():
            print(f"  {k}: {v}")
