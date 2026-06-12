"""Patient CRUD and visit history endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.orm_models import FullPatient, PatientVisitHistory, User
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])


# ── Schemas ───────────────────────────────────────────────────────────────

class PatientCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    date_of_birth: Optional[str] = None    # YYYY-MM-DD
    gender: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None


class VisitHistoryCreate(BaseModel):
    visit_date: str                        # YYYY-MM-DD
    visit_type: str = "follow-up"
    specialty: Optional[str] = None
    physician_id: Optional[str] = None
    attended: bool = True
    actual_duration: Optional[int] = None
    notes: Optional[str] = None


def _patient_out(p: FullPatient) -> dict[str, Any]:
    return {
        "id": p.id,
        "patient_code": p.patient_code,
        "full_name": p.full_name,
        "date_of_birth": p.date_of_birth,
        "gender": p.gender,
        "contact_phone": p.contact_phone,
        "contact_email": p.contact_email,
        "address": p.address,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "visit_count": len(p.visit_history),
        "no_show_count": sum(1 for v in p.visit_history if not v.attended),
        # ML-ready features
        "no_show_streak": _compute_streak(p.visit_history),
        "days_since_last_visit": _days_since_last(p.visit_history),
    }


def _compute_streak(history: list) -> int:
    """Count consecutive no-shows from most recent visit backwards."""
    streak = 0
    for v in sorted(history, key=lambda h: h.visit_date, reverse=True):
        if not v.attended:
            streak += 1
        else:
            break
    return streak


def _days_since_last(history: list) -> Optional[float]:
    if not history:
        return None
    last = max(history, key=lambda h: h.visit_date)
    try:
        delta = datetime.utcnow().date() - datetime.strptime(last.visit_date, "%Y-%m-%d").date()
        return float(delta.days)
    except Exception:
        return None


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("", summary="Search patients")
def search_patients(
    q: Optional[str] = Query(default=None, description="Search by name or patient code"),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    query = db.query(FullPatient)
    if q:
        like = f"%{q}%"
        query = query.filter(
            FullPatient.full_name.ilike(like) | FullPatient.patient_code.ilike(like)
        )
    patients = query.order_by(FullPatient.full_name).limit(limit).all()
    return [_patient_out(p) for p in patients]


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create patient")
def create_patient(
    body: PatientCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    # Auto-generate patient_code: P + 4 uppercase hex chars
    code = "P" + uuid.uuid4().hex[:4].upper()
    while db.query(FullPatient).filter_by(patient_code=code).first():
        code = "P" + uuid.uuid4().hex[:4].upper()

    patient = FullPatient(patient_code=code, **body.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return _patient_out(patient)


@router.get("/{patient_id}", summary="Get patient by ID")
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    p = db.get(FullPatient, patient_id)
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    return _patient_out(p)


@router.get("/{patient_id}/history", summary="Get patient visit history")
def get_history(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    p = db.get(FullPatient, patient_id)
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    return [
        {
            "id": v.id,
            "visit_date": v.visit_date,
            "visit_type": v.visit_type,
            "specialty": v.specialty,
            "physician_id": v.physician_id,
            "attended": v.attended,
            "actual_duration": v.actual_duration,
            "notes": v.notes,
        }
        for v in sorted(p.visit_history, key=lambda h: h.visit_date, reverse=True)
    ]


@router.post("/{patient_id}/history", status_code=201, summary="Add visit history entry")
def add_history(
    patient_id: int,
    body: VisitHistoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    p = db.get(FullPatient, patient_id)
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    entry = PatientVisitHistory(patient_id=patient_id, **body.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "visit_date": entry.visit_date, "attended": entry.attended}
