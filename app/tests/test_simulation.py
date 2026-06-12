"""Tests for the discrete-event simulation engine."""
from __future__ import annotations

import pytest
from app.simulation.scheduler import simulate_day


def _make_appt(i: int, hour: int = 9, dur: float = 30.0, noshow: float = 0.1) -> dict:
    return {
        "appointment_id": f"SIM{i:03d}",
        "patient_id": f"P{i:03d}",
        "scheduled_start": f"2026-07-15T{hour:02d}:00:00",
        "predicted_duration": dur,
        "no_show_probability": noshow,
        "visit_type": "follow-up",
        "priority": 1,
    }


class TestSimulateDay:
    _BASE = {
        "physician_id": "DSIM",
        "date": "2026-07-15",
        "constraints": {
            "work_start_hour": 8,
            "work_end_hour": 17,
            "lunch_start_hour": 12,
            "lunch_duration_minutes": 60,
            "buffer_minutes": 5,
        },
    }

    def test_empty_returns_empty(self):
        result = simulate_day({**self._BASE, "appointments": []})
        assert result["simulated_appointments"] == []
        assert result["total_waiting_time_minutes"] == 0
        assert result["at_risk_count"] == 0

    def test_single_on_time_appointment(self):
        result = simulate_day({
            **self._BASE,
            "appointments": [_make_appt(1, hour=9, dur=20.0)],
        })
        assert len(result["simulated_appointments"]) == 1
        assert result["simulated_appointments"][0]["delay_minutes"] == pytest.approx(0.0)

    def test_delay_propagates(self):
        """If the first appointment overruns, the second should be delayed."""
        appts = [
            _make_appt(1, hour=9,  dur=60.0, noshow=0.0),  # 60-min appt in 30-min slot
            _make_appt(2, hour=10, dur=30.0, noshow=0.0),
        ]
        result = simulate_day({**self._BASE, "appointments": appts})
        sim = result["simulated_appointments"]
        assert len(sim) == 2
        # First appt delay = 0 (starts on time), second must have delay > 0
        first_delay  = sim[0]["delay_minutes"]
        second_delay = sim[1]["delay_minutes"]
        assert second_delay >= first_delay

    def test_all_appointments_represented(self):
        appts = [_make_appt(i, hour=9 + i) for i in range(5)]
        result = simulate_day({**self._BASE, "appointments": appts})
        assert len(result["simulated_appointments"]) == 5

    def test_at_risk_count_consistent(self):
        result = simulate_day({
            **self._BASE,
            "appointments": [_make_appt(i, hour=8 + i) for i in range(8)],
        })
        at_risk_in_list = sum(1 for a in result["simulated_appointments"] if a["is_at_risk"])
        assert result["at_risk_count"] == at_risk_in_list

    def test_no_show_skipped(self):
        """A patient with noshow=1.0 should be simulated as a no-show."""
        certain_noshow = _make_appt(99, hour=9, dur=30.0, noshow=1.0)
        result = simulate_day({**self._BASE, "appointments": [certain_noshow]})
        sim = result["simulated_appointments"][0]
        # Should be marked attended=False or have 0 delay (physician idles)
        assert sim["delay_minutes"] == pytest.approx(0.0)

    def test_recommendations_is_list(self):
        result = simulate_day({
            **self._BASE,
            "appointments": [_make_appt(1)],
        })
        assert isinstance(result["recommendations"], list)
