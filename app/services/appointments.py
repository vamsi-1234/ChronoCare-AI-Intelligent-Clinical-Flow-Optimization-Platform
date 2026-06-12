"""DB-backed appointments store with AI pre-assessment.

All state is persisted to the SQLite/PostgreSQL database via SQLAlchemy so that
appointments survive backend restarts.  The public API (function signatures) is
identical to the previous in-memory version; callers do not need to change.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from app.db.database import SessionLocal
from app.db.orm_models import DailyAppointmentRecord

logger = logging.getLogger(__name__)

VALID_STATUSES = {"pending", "in_progress", "completed", "no_show"}

_SAMPLES = [
    {"patient_id": "P0023", "age": 62, "visit_type": "new",       "specialty": "cardiology",       "comorbidity_count": 3, "hour": 9,  "minute": 0,  "priority": 4},
    {"patient_id": "P0091", "age": 34, "visit_type": "follow-up", "specialty": "general_practice", "comorbidity_count": 0, "hour": 9,  "minute": 30, "priority": 2},
    {"patient_id": "P0145", "age": 55, "visit_type": "new",       "specialty": "neurology",        "comorbidity_count": 2, "hour": 10, "minute": 0,  "priority": 3},
    {"patient_id": "P0078", "age": 41, "visit_type": "follow-up", "specialty": "cardiology",       "comorbidity_count": 1, "hour": 10, "minute": 45, "priority": 1},
    {"patient_id": "P0203", "age": 28, "visit_type": "new",       "specialty": "dermatology",      "comorbidity_count": 0, "hour": 11, "minute": 15, "priority": 2},
    {"patient_id": "P0312", "age": 71, "visit_type": "follow-up", "specialty": "oncology",         "comorbidity_count": 4, "hour": 13, "minute": 0,  "priority": 5},
    {"patient_id": "P0089", "age": 47, "visit_type": "follow-up", "specialty": "orthopedics",      "comorbidity_count": 1, "hour": 13, "minute": 45, "priority": 2},
    {"patient_id": "P0167", "age": 8,  "visit_type": "new",       "specialty": "pediatrics",       "comorbidity_count": 0, "hour": 14, "minute": 30, "priority": 3},
]


def _row_to_dict(row: DailyAppointmentRecord) -> dict[str, Any]:
    return row.to_dict()


# ── Public API ────────────────────────────────────────────────────────────────

def seed_sample_appointments(date: str, physician_id: str = "D001") -> None:
    """Seed sample appointments for a date (idempotent – skips if already seeded)."""
    with SessionLocal() as db:
        existing = (
            db.query(DailyAppointmentRecord)
            .filter_by(date=date, physician_id=physician_id)
            .first()
        )
        if existing:
            return

        base = datetime.strptime(date, "%Y-%m-%d")
        for s in _SAMPLES:
            appt_id = f"A{str(uuid.uuid4())[:8].upper()}"
            appt_time = base.replace(hour=s["hour"], minute=s["minute"])
            db.add(DailyAppointmentRecord(
                appointment_id=appt_id,
                patient_id=s["patient_id"],
                physician_id=physician_id,
                date=date,
                scheduled_start=appt_time.isoformat(),
                visit_type=s["visit_type"],
                specialty=s["specialty"],
                age=s["age"],
                comorbidity_count=s["comorbidity_count"],
                priority=s["priority"],
                status="pending",
            ))
        db.commit()
    logger.info("Seeded %d appointments for %s / %s", len(_SAMPLES), physician_id, date)


def list_appointments(
    date: Optional[str] = None, physician_id: Optional[str] = None
) -> list[dict[str, Any]]:
    with SessionLocal() as db:
        q = db.query(DailyAppointmentRecord)
        if date:
            q = q.filter_by(date=date)
        if physician_id:
            q = q.filter_by(physician_id=physician_id)
        rows = q.order_by(DailyAppointmentRecord.scheduled_start).all()
        return [_row_to_dict(r) for r in rows]


def get_appointment(appointment_id: str) -> Optional[dict[str, Any]]:
    with SessionLocal() as db:
        row = db.get(DailyAppointmentRecord, appointment_id)
        return _row_to_dict(row) if row else None


def create_appointment(data: dict[str, Any]) -> dict[str, Any]:
    appt_id = data.get("appointment_id") or f"A{str(uuid.uuid4())[:8].upper()}"
    with SessionLocal() as db:
        row = DailyAppointmentRecord(
            appointment_id=appt_id,
            patient_id=data.get("patient_id", ""),
            physician_id=data.get("physician_id", ""),
            date=data.get("date", datetime.utcnow().date().isoformat()),
            scheduled_start=data.get("scheduled_start", datetime.utcnow().isoformat()),
            visit_type=data.get("visit_type", "follow-up"),
            specialty=data.get("specialty", "general_practice"),
            age=data.get("age", 45),
            comorbidity_count=data.get("comorbidity_count", 0),
            priority=data.get("priority", 1),
            status=data.get("status", "pending"),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _row_to_dict(row)


def assess_appointment(appointment_id: str) -> Optional[dict[str, Any]]:
    """Run duration + no-show predictions and persist results."""
    with SessionLocal() as db:
        row = db.get(DailyAppointmentRecord, appointment_id)
        if not row:
            return None

        from app.services.predict import predict_duration, predict_no_show

        dur = predict_duration({
            "age": row.age,
            "visit_type": row.visit_type,
            "specialty": row.specialty,
            "comorbidity_count": row.comorbidity_count,
            "physician_id": row.physician_id,
            "appointment_time": row.scheduled_start,
        })
        nsh = predict_no_show({
            "appointment_time": row.scheduled_start,
            "lead_time_days": 7,
            "visit_type": row.visit_type,
            "age": row.age,
            "specialty": row.specialty,
        })

        row.predicted_duration      = dur.get("predicted_duration_minutes")
        row.no_show_probability     = nsh.get("no_show_probability")
        row.risk_category           = nsh.get("risk_category", "low")
        row.nl_duration_explanation = dur.get("nl_explanation", "")
        row.nl_noshow_explanation   = nsh.get("nl_explanation", "")
        row.duration_lower          = dur.get("lower_bound")
        row.duration_upper          = dur.get("upper_bound")
        row.duration_confidence     = dur.get("confidence_pct")
        row.assessed_at             = datetime.utcnow().isoformat()
        row.updated_at              = datetime.utcnow()

        db.commit()
        db.refresh(row)
        return _row_to_dict(row)


def apply_simulation_results(simulation_result: dict[str, Any]) -> None:
    """Merge delay info from a simulate-day response into stored appointments."""
    with SessionLocal() as db:
        for slot in simulation_result.get("simulated_appointments", []):
            row = db.get(DailyAppointmentRecord, slot["appointment_id"])
            if row:
                row.delay_minutes   = slot["delay_minutes"]
                row.is_at_risk      = slot["is_at_risk"]
                row.predicted_start = slot["predicted_start"]
                row.updated_at      = datetime.utcnow()
        db.commit()


def update_status(appointment_id: str, new_status: str) -> Optional[dict[str, Any]]:
    if new_status not in VALID_STATUSES:
        return None
    with SessionLocal() as db:
        row = db.get(DailyAppointmentRecord, appointment_id)
        if not row:
            return None
        row.status     = new_status
        row.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(row)
        return _row_to_dict(row)
