"""Tests for appointments service (DB-backed)."""
from __future__ import annotations

import pytest

from app.services.appointments import (
    seed_sample_appointments,
    list_appointments,
    get_appointment,
    create_appointment,
    update_status,
    VALID_STATUSES,
)

_DATE = "2099-01-15"   # far-future date so tests don't clash with seeded data
_PHYS = "DTEST"


class TestSeedAndList:
    def test_seed_creates_8_appointments(self):
        seed_sample_appointments(_DATE, _PHYS)
        rows = list_appointments(date=_DATE, physician_id=_PHYS)
        assert len(rows) == 8

    def test_seed_is_idempotent(self):
        seed_sample_appointments(_DATE, _PHYS)
        seed_sample_appointments(_DATE, _PHYS)  # second call should not add more
        rows = list_appointments(date=_DATE, physician_id=_PHYS)
        assert len(rows) == 8

    def test_list_sorted_by_time(self):
        seed_sample_appointments(_DATE, _PHYS)
        rows = list_appointments(date=_DATE, physician_id=_PHYS)
        times = [r["scheduled_start"] for r in rows]
        assert times == sorted(times)

    def test_filter_by_physician(self):
        seed_sample_appointments(_DATE, "DOTHER")
        seed_sample_appointments(_DATE, _PHYS)
        rows = list_appointments(date=_DATE, physician_id=_PHYS)
        assert all(r["physician_id"] == _PHYS for r in rows)

    def test_appointments_have_required_fields(self):
        seed_sample_appointments(_DATE, _PHYS)
        rows = list_appointments(date=_DATE, physician_id=_PHYS)
        required = {"appointment_id", "patient_id", "physician_id", "specialty", "status"}
        for row in rows:
            assert required.issubset(row.keys())


class TestCreateAndGet:
    def test_create_returns_appointment(self):
        appt = create_appointment({
            "patient_id": "PX01",
            "physician_id": "DX01",
            "date": "2099-02-01",
            "scheduled_start": "2099-02-01T09:00:00",
            "specialty": "neurology",
            "age": 40,
            "visit_type": "new",
        })
        assert appt["appointment_id"].startswith("A")
        assert appt["status"] == "pending"

    def test_get_returns_same_record(self):
        appt = create_appointment({
            "patient_id": "PX02",
            "physician_id": "DX01",
            "date": "2099-02-02",
            "scheduled_start": "2099-02-02T10:00:00",
            "specialty": "dermatology",
            "age": 30,
            "visit_type": "follow-up",
        })
        fetched = get_appointment(appt["appointment_id"])
        assert fetched is not None
        assert fetched["appointment_id"] == appt["appointment_id"]
        assert fetched["specialty"] == "dermatology"

    def test_get_nonexistent_returns_none(self):
        assert get_appointment("DOES_NOT_EXIST") is None


class TestUpdateStatus:
    def test_valid_status_transition(self):
        appt = create_appointment({
            "patient_id": "PX03",
            "physician_id": "DX01",
            "date": "2099-02-03",
            "scheduled_start": "2099-02-03T11:00:00",
            "specialty": "oncology",
            "age": 60,
            "visit_type": "follow-up",
        })
        updated = update_status(appt["appointment_id"], "in_progress")
        assert updated["status"] == "in_progress"

    @pytest.mark.parametrize("status", list(VALID_STATUSES))
    def test_all_valid_statuses_accepted(self, status):
        appt = create_appointment({
            "patient_id": "PX04",
            "physician_id": "DX01",
            "date": "2099-02-04",
            "scheduled_start": "2099-02-04T12:00:00",
            "specialty": "pediatrics",
            "age": 8,
            "visit_type": "new",
        })
        result = update_status(appt["appointment_id"], status)
        assert result["status"] == status

    def test_invalid_status_returns_none(self):
        appt = create_appointment({
            "patient_id": "PX05",
            "physician_id": "DX01",
            "date": "2099-02-05",
            "scheduled_start": "2099-02-05T13:00:00",
            "specialty": "cardiology",
            "age": 55,
            "visit_type": "follow-up",
        })
        result = update_status(appt["appointment_id"], "invalid_status")
        assert result is None

    def test_update_nonexistent_returns_none(self):
        assert update_status("GHOST_ID", "completed") is None
