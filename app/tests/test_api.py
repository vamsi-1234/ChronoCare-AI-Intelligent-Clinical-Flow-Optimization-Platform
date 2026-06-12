"""Tests for the core API endpoints."""
from __future__ import annotations

import pytest


class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "version" in body
        assert isinstance(body["database"], bool)

    def test_health_models_keys(self, client):
        models = client.get("/api/v1/health").json()["models"]
        assert "duration_model" in models
        assert "noshow_model" in models


class TestPredictDuration:
    _PAYLOAD = {
        "patient_id": "P001",
        "age": 55,
        "visit_type": "new",
        "specialty": "cardiology",
        "comorbidity_count": 2,
        "physician_id": "D001",
    }

    def test_returns_200(self, client):
        r = client.post("/api/v1/predict-duration", json=self._PAYLOAD)
        assert r.status_code == 200

    def test_prediction_positive(self, client):
        body = client.post("/api/v1/predict-duration", json=self._PAYLOAD).json()
        assert body["predicted_duration_minutes"] > 0

    def test_confidence_interval_ordered(self, client):
        body = client.post("/api/v1/predict-duration", json=self._PAYLOAD).json()
        assert body["lower_bound"] <= body["predicted_duration_minutes"] <= body["upper_bound"]

    def test_explanation_present(self, client):
        body = client.post("/api/v1/predict-duration", json=self._PAYLOAD).json()
        assert "explanation" in body
        assert isinstance(body["explanation"]["top_features"], list)

    def test_nl_explanation_nonempty(self, client):
        body = client.post("/api/v1/predict-duration", json=self._PAYLOAD).json()
        assert len(body["nl_explanation"]) > 0

    def test_invalid_age_rejected(self, client):
        bad = {**self._PAYLOAD, "age": 999}
        r = client.post("/api/v1/predict-duration", json=bad)
        assert r.status_code == 422

    def test_follow_up_shorter_than_new(self, client):
        """Follow-up appointments should (on average) be predicted shorter than new."""
        new_dur = client.post(
            "/api/v1/predict-duration",
            json={**self._PAYLOAD, "visit_type": "new", "age": 45, "comorbidity_count": 1},
        ).json()["predicted_duration_minutes"]
        fu_dur = client.post(
            "/api/v1/predict-duration",
            json={**self._PAYLOAD, "visit_type": "follow-up", "age": 45, "comorbidity_count": 1},
        ).json()["predicted_duration_minutes"]
        # Model was trained on data where new > follow-up – soft assertion
        assert new_dur >= fu_dur - 5  # allow ±5 min slack


class TestPredictNoShow:
    _PAYLOAD = {
        "patient_id": "P001",
        "appointment_time": "2026-06-12T10:00:00",
        "lead_time_days": 14,
        "visit_type": "new",
        "age": 35,
        "specialty": "general_practice",
        "patient_cancellation_count": 0,
    }

    def test_returns_200(self, client):
        r = client.post("/api/v1/predict-no-show", json=self._PAYLOAD)
        assert r.status_code == 200

    def test_probability_in_range(self, client):
        body = client.post("/api/v1/predict-no-show", json=self._PAYLOAD).json()
        assert 0.0 <= body["no_show_probability"] <= 1.0

    def test_risk_category_valid(self, client):
        body = client.post("/api/v1/predict-no-show", json=self._PAYLOAD).json()
        assert body["risk_category"] in {"low", "medium", "high"}

    def test_high_cancellations_raise_risk(self, client):
        """A patient with many cancellations should have higher risk."""
        low = client.post(
            "/api/v1/predict-no-show",
            json={**self._PAYLOAD, "patient_cancellation_count": 0},
        ).json()["no_show_probability"]
        high = client.post(
            "/api/v1/predict-no-show",
            json={**self._PAYLOAD, "patient_cancellation_count": 5},
        ).json()["no_show_probability"]
        assert high > low


def _make_appt(i: int, hour: int = 9, dur: float = 30.0, noshow: float = 0.1) -> dict:
    return {
        "appointment_id": f"SIM{i:03d}",
        "patient_id": f"P{i:03d}",
        "scheduled_start": f"2026-07-01T{hour:02d}:00:00",
        "predicted_duration": dur,
        "no_show_probability": noshow,
        "visit_type": "follow-up",
        "priority": 1,
    }


class TestSimulateDay:
    _DATE = "2026-07-01"

    def test_returns_200(self, client):
        r = client.post(
            "/api/v1/simulate-day",
            json={"physician_id": "D001", "date": self._DATE, "appointments": [_make_appt(i, 8 + i) for i in range(4)]},
        )
        assert r.status_code == 200

    def test_simulated_count_matches_input(self, client):
        body = client.post(
            "/api/v1/simulate-day",
            json={"physician_id": "D001", "date": self._DATE, "appointments": [_make_appt(i, 8 + i) for i in range(4)]},
        ).json()
        assert len(body["simulated_appointments"]) == 4

    def test_metrics_non_negative(self, client):
        body = client.post(
            "/api/v1/simulate-day",
            json={"physician_id": "D001", "date": self._DATE, "appointments": [_make_appt(i, 8 + i) for i in range(4)]},
        ).json()
        assert body["total_waiting_time_minutes"] >= 0
        assert body["max_delay_minutes"] >= 0

    def test_empty_appointments(self, client):
        body = client.post(
            "/api/v1/simulate-day",
            json={"physician_id": "D001", "date": self._DATE, "appointments": []},
        ).json()
        assert body["simulated_appointments"] == []


class TestOptimizeSchedule:
    _APPTS = [
        {
            "appointment_id": f"B{i:03d}",
            "patient_id": f"P{i:03d}",
            "scheduled_start": f"2026-07-01T{9 + i:02d}:00:00",
            "predicted_duration": 20.0 + i * 5,
            "no_show_probability": 0.1 * i,
            "visit_type": "follow-up",
            "priority": i + 1,
        }
        for i in range(4)
    ]

    def test_returns_200(self, client):
        r = client.post(
            "/api/v1/optimize-schedule",
            json={"physician_id": "D001", "date": "2026-07-01", "appointments": self._APPTS},
        )
        assert r.status_code == 200

    def test_improvement_non_negative(self, client):
        body = client.post(
            "/api/v1/optimize-schedule",
            json={"physician_id": "D001", "date": "2026-07-01", "appointments": self._APPTS},
        ).json()
        assert body["improvement_pct"] >= 0

    def test_output_count_matches_input(self, client):
        body = client.post(
            "/api/v1/optimize-schedule",
            json={"physician_id": "D001", "date": "2026-07-01", "appointments": self._APPTS},
        ).json()
        assert len(body["optimized_appointments"]) == len(self._APPTS)
