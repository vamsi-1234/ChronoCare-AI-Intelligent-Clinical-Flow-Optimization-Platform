"""Feature engineering pipeline for ChronoCare AI.

Transforms raw appointment dictionaries into numpy arrays suitable for
both the duration-prediction and no-show-prediction LightGBM models.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Specialty averages used as fallbacks ──────────────────────────────────
SPECIALTY_AVG_DURATION: dict[str, float] = {
    "cardiology": 28.0,
    "dermatology": 18.0,
    "general_practice": 20.0,
    "neurology": 32.0,
    "oncology": 35.0,
    "orthopedics": 25.0,
    "pediatrics": 20.0,
    "psychiatry": 40.0,
    "radiology": 22.0,
    "urology": 24.0,
}
DEFAULT_AVG_DURATION = 22.0
GLOBAL_NOSHOW_RATE = 0.15

SPECIALTIES = sorted(SPECIALTY_AVG_DURATION.keys())
SPECIALTY_INDEX = {s: i for i, s in enumerate(SPECIALTIES)}

# ── Feature names (must match training column order) ──────────────────────
DURATION_FEATURES = [
    "age",
    "comorbidity_count",
    "is_new_patient",
    "hour_of_day",
    "day_of_week",
    "is_morning",
    "patient_visit_count",
    "patient_avg_duration",
    "physician_avg_duration",
    "physician_workload",
    "specialty_idx",
    "appointment_sequence",
]

NOSHOW_FEATURES = [
    "age",
    "lead_time_days",
    "is_new_patient",
    "hour_of_day",
    "day_of_week",
    "is_morning",
    "is_afternoon",
    "patient_no_show_rate",
    "patient_visit_count",
    "specialty_idx",
    "patient_cancellation_count",
    "patient_no_show_streak",     # consecutive no-shows (very strong predictor)
    "days_since_last_visit",      # long gaps → disengaged patient
]


# ── Helpers ───────────────────────────────────────────────────────────────

def _parse_dt(value: Any) -> datetime:
    """Best-effort parse of a datetime value."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # Try ISO format first, then common variations
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    raise ValueError(f"Cannot parse datetime: {value!r}")


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def extract_duration_features(data: dict[str, Any]) -> np.ndarray:
    """Return a 1-D float32 array with *DURATION_FEATURES* in order.

    Args:
        data: Dictionary with keys from the ``PredictDurationRequest`` schema
              plus optional pre-computed stats from patient/physician history.

    Returns:
        numpy array of shape (1, len(DURATION_FEATURES)) ready for LightGBM.
    """
    # Temporal
    appt_dt = _parse_dt(data.get("appointment_time", datetime.utcnow()))
    hour_of_day = appt_dt.hour
    day_of_week = appt_dt.weekday()
    is_morning = int(hour_of_day < 12)

    # Patient
    age = _clamp(float(data.get("age") or 45), 0, 120)
    comorbidity_count = _clamp(float(data.get("comorbidity_count") or 0), 0, 20)
    visit_type = data.get("visit_type", "follow-up")
    is_new_patient = int(visit_type == "new")

    # History (pre-computed or defaulting)
    specialty = data.get("specialty", "general_practice").lower()
    patient_visit_count = float(data.get("patient_visit_count") or 0)
    patient_avg_duration = float(
        data.get("patient_avg_duration") or SPECIALTY_AVG_DURATION.get(specialty, DEFAULT_AVG_DURATION)
    )
    physician_avg_duration = float(
        data.get("physician_avg_duration") or SPECIALTY_AVG_DURATION.get(specialty, DEFAULT_AVG_DURATION)
    )
    physician_workload = _clamp(float(data.get("physician_workload") or 0), 0, 20)
    specialty_idx = float(SPECIALTY_INDEX.get(specialty, 0))
    appointment_sequence = _clamp(float(data.get("appointment_sequence") or 1), 1, 50)

    row = [
        age,
        comorbidity_count,
        is_new_patient,
        float(hour_of_day),
        float(day_of_week),
        float(is_morning),
        patient_visit_count,
        patient_avg_duration,
        physician_avg_duration,
        physician_workload,
        specialty_idx,
        appointment_sequence,
    ]
    return np.array([row], dtype=np.float32)


def extract_noshow_features(data: dict[str, Any]) -> np.ndarray:
    """Return a 1-D float32 array with *NOSHOW_FEATURES* in order.

    Args:
        data: Dictionary with keys from the ``PredictNoShowRequest`` schema
              plus optional pre-computed patient history stats.

    Returns:
        numpy array of shape (1, len(NOSHOW_FEATURES)) ready for LightGBM.
    """
    appt_dt = _parse_dt(data.get("appointment_time", datetime.utcnow()))
    hour_of_day = appt_dt.hour
    day_of_week = appt_dt.weekday()
    is_morning = int(hour_of_day < 12)
    is_afternoon = int(12 <= hour_of_day < 17)

    age = _clamp(float(data.get("age") or 45), 0, 120)
    lead_time_days = _clamp(float(data.get("lead_time_days") or 7), 0, 180)
    visit_type = data.get("visit_type", "follow-up")
    is_new_patient = int(visit_type == "new")

    specialty = (data.get("specialty") or "general_practice").lower()
    patient_no_show_rate = _clamp(
        float(data.get("patient_no_show_rate") or GLOBAL_NOSHOW_RATE), 0.05, 0.95
    )
    patient_visit_count = float(data.get("patient_visit_count") or 0)
    specialty_idx = float(SPECIALTY_INDEX.get(specialty, 0))
    patient_cancellation_count = float(min(data.get("patient_cancellation_count") or 0, 10))
    patient_no_show_streak = _clamp(float(data.get("patient_no_show_streak") or 0), 0, 10)
    days_since_last_visit = _clamp(float(data.get("days_since_last_visit") or 180), 0, 730)

    row = [
        age,
        lead_time_days,
        is_new_patient,
        float(hour_of_day),
        float(day_of_week),
        float(is_morning),
        float(is_afternoon),
        patient_no_show_rate,
        patient_visit_count,
        specialty_idx,
        patient_cancellation_count,
        patient_no_show_streak,
        days_since_last_visit,
    ]
    return np.array([row], dtype=np.float32)


def build_training_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert a list of raw appointment records into a model-ready DataFrame.

    This is used during training.  Each record should have the raw appointment
    fields plus ``actual_duration`` (regression target) and ``attended``
    (classification target, 0=no-show, 1=attended).
    """
    rows = []
    for rec in records:
        try:
            dur_feats = extract_duration_features(rec).flatten().tolist()
            nsh_feats = extract_noshow_features(rec).flatten().tolist()
            row = dict(zip(DURATION_FEATURES, dur_feats))
            for k, v in zip(NOSHOW_FEATURES, nsh_feats):
                row.setdefault(k, v)  # don't overwrite shared features
            row["actual_duration"] = float(rec.get("actual_duration", 20))
            row["attended"] = int(rec.get("attended", 1))
            rows.append(row)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping bad record during feature build: %s", exc)
    return pd.DataFrame(rows)
