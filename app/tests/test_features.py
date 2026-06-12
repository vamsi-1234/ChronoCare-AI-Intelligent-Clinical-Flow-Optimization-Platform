"""Tests for feature extraction functions."""
from __future__ import annotations

import numpy as np
import pytest

from app.ml.features import (
    DURATION_FEATURES,
    NOSHOW_FEATURES,
    extract_duration_features,
    extract_noshow_features,
)

_BASE_DUR = {
    "patient_id": "P001",
    "age": 45,
    "visit_type": "follow-up",
    "specialty": "cardiology",
    "comorbidity_count": 1,
    "physician_id": "D001",
    "appointment_time": "2026-06-12T09:00:00",
}

_BASE_NSH = {
    "patient_id": "P001",
    "appointment_time": "2026-06-12T09:00:00",
    "lead_time_days": 7,
    "visit_type": "follow-up",
    "age": 45,
    "specialty": "cardiology",
}


class TestDurationFeatures:
    def test_output_shape(self):
        arr = extract_duration_features(_BASE_DUR)
        assert arr.shape == (1, len(DURATION_FEATURES))

    def test_dtype_float32(self):
        arr = extract_duration_features(_BASE_DUR)
        assert arr.dtype == np.float32

    def test_age_propagated(self):
        arr45 = extract_duration_features({**_BASE_DUR, "age": 45})
        arr70 = extract_duration_features({**_BASE_DUR, "age": 70})
        age_idx = DURATION_FEATURES.index("age")
        assert arr45[0, age_idx] == pytest.approx(45.0)
        assert arr70[0, age_idx] == pytest.approx(70.0)

    def test_is_new_patient_flag(self):
        arr_new = extract_duration_features({**_BASE_DUR, "visit_type": "new"})
        arr_fu = extract_duration_features({**_BASE_DUR, "visit_type": "follow-up"})
        idx = DURATION_FEATURES.index("is_new_patient")
        assert arr_new[0, idx] == 1.0
        assert arr_fu[0, idx] == 0.0

    def test_none_safe_comorbidity(self):
        """None comorbidity should not raise; defaults to 0."""
        arr = extract_duration_features({**_BASE_DUR, "comorbidity_count": None})
        idx = DURATION_FEATURES.index("comorbidity_count")
        assert arr[0, idx] == pytest.approx(0.0)

    def test_missing_appointment_time_uses_now(self):
        data = {k: v for k, v in _BASE_DUR.items() if k != "appointment_time"}
        arr = extract_duration_features(data)
        assert arr.shape == (1, len(DURATION_FEATURES))


class TestNoShowFeatures:
    def test_output_shape(self):
        arr = extract_noshow_features(_BASE_NSH)
        assert arr.shape == (1, len(NOSHOW_FEATURES))

    def test_dtype_float32(self):
        arr = extract_noshow_features(_BASE_NSH)
        assert arr.dtype == np.float32

    def test_lead_time_propagated(self):
        arr = extract_noshow_features({**_BASE_NSH, "lead_time_days": 30})
        idx = NOSHOW_FEATURES.index("lead_time_days")
        assert arr[0, idx] == pytest.approx(30.0)

    def test_morning_afternoon_flags_mutually_exclusive(self):
        # 9 AM → morning, not afternoon
        arr_am = extract_noshow_features({**_BASE_NSH, "appointment_time": "2026-06-12T09:00:00"})
        am_idx = NOSHOW_FEATURES.index("is_morning")
        af_idx = NOSHOW_FEATURES.index("is_afternoon")
        assert arr_am[0, am_idx] == 1.0
        assert arr_am[0, af_idx] == 0.0

        # 14:00 → afternoon, not morning
        arr_pm = extract_noshow_features({**_BASE_NSH, "appointment_time": "2026-06-12T14:00:00"})
        assert arr_pm[0, am_idx] == 0.0
        assert arr_pm[0, af_idx] == 1.0

    def test_cancellation_count_capped(self):
        """Values >10 should be capped at 10."""
        arr = extract_noshow_features({**_BASE_NSH, "patient_cancellation_count": 99})
        idx = NOSHOW_FEATURES.index("patient_cancellation_count")
        assert arr[0, idx] == pytest.approx(10.0)

    def test_none_cancellation_defaults_zero(self):
        arr = extract_noshow_features({**_BASE_NSH, "patient_cancellation_count": None})
        idx = NOSHOW_FEATURES.index("patient_cancellation_count")
        assert arr[0, idx] == pytest.approx(0.0)
