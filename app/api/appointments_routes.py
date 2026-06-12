"""Appointments management and daily-board endpoints."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.appointments import (
    list_appointments,
    get_appointment,
    create_appointment,
    assess_appointment,
    apply_simulation_results,
    update_status,
    seed_sample_appointments,
    VALID_STATUSES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/appointments", tags=["Appointments"])


class CreateAppointmentRequest(BaseModel):
    patient_id: str
    physician_id: str
    scheduled_start: str
    visit_type: str = "follow-up"
    specialty: str = "general_practice"
    age: int = 45
    comorbidity_count: int = 0
    priority: int = 1


class UpdateStatusRequest(BaseModel):
    status: str = Field(..., description="pending | in_progress | completed | no_show")


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/day/{physician_id}/{date}", summary="Get daily appointments")
def get_day_appointments(
    physician_id: str,
    date: str,
    seed: bool = Query(default=True, description="Auto-seed sample data if none exists"),
) -> dict[str, Any]:
    """Return all appointments for a physician on a given date.
    Seeds realistic sample data on first access."""
    if seed:
        try:
            seed_sample_appointments(date, physician_id)
        except Exception as exc:
            logger.warning("Seeding failed: %s", exc)

    appointments = list_appointments(date=date, physician_id=physician_id)
    assessed = sum(1 for a in appointments if a.get("assessed_at"))
    at_risk = sum(1 for a in appointments if a.get("risk_category") == "high")

    return {
        "physician_id": physician_id,
        "date": date,
        "count": len(appointments),
        "assessed_count": assessed,
        "high_risk_count": at_risk,
        "appointments": appointments,
    }


@router.post("", summary="Create appointment")
def create(body: CreateAppointmentRequest) -> dict[str, Any]:
    return create_appointment(body.model_dump())


@router.post("/{appointment_id}/assess", summary="Assess single appointment")
def assess(appointment_id: str) -> dict[str, Any]:
    result = assess_appointment(appointment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return result


@router.post("/assess-all/{physician_id}/{date}", summary="Assess all appointments for a day")
def assess_all(physician_id: str, date: str) -> dict[str, Any]:
    """Run AI assessment (duration + no-show) on every appointment for a physician/date."""
    seed_sample_appointments(date, physician_id)
    appointments = list_appointments(date=date, physician_id=physician_id)
    results, errors = [], 0

    for appt in appointments:
        try:
            results.append(assess_appointment(appt["appointment_id"]))
        except Exception as exc:
            logger.warning("Assessment failed for %s: %s", appt["appointment_id"], exc)
            results.append({**appt, "assessment_error": str(exc)})
            errors += 1

    high_risk = sum(1 for r in results if r and r.get("risk_category") == "high")
    total_pred_wait = sum(
        (r.get("predicted_duration") or 0) for r in results if r
    )

    return {
        "physician_id": physician_id,
        "date": date,
        "assessed": len(results) - errors,
        "errors": errors,
        "high_risk_count": high_risk,
        "total_predicted_minutes": round(total_pred_wait, 1),
        "appointments": results,
    }


@router.post(
    "/apply-simulation/{physician_id}/{date}",
    summary="Merge simulation delay data into stored appointments",
)
def apply_simulation(physician_id: str, date: str, simulation_result: dict[str, Any]) -> dict[str, Any]:
    """Called internally (or by the frontend) after running /simulate-day."""
    apply_simulation_results(simulation_result)
    return {"message": "Simulation results applied", "physician_id": physician_id, "date": date}


@router.put("/{appointment_id}/status", summary="Update appointment status")
def update(appointment_id: str, body: UpdateStatusRequest) -> dict[str, Any]:
    if body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Use one of: {', '.join(VALID_STATUSES)}",
        )
    result = update_status(appointment_id, body.status)
    if not result:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return result


@router.get("/{appointment_id}", summary="Get single appointment")
def get_one(appointment_id: str) -> dict[str, Any]:
    appt = get_appointment(appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt
