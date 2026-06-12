"""Pydantic request/response schemas for ChronoCare AI API."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ── Shared sub-models ─────────────────────────────────────────────────────

class SHAPFeature(BaseModel):
    name: str
    value: float
    contribution: float


class Explanation(BaseModel):
    base_value: Optional[float] = None
    top_features: list[SHAPFeature] = []


# ── Duration prediction ───────────────────────────────────────────────────

class PredictDurationRequest(BaseModel):
    patient_id: str = Field(..., examples=["P12345"])
    age: int = Field(..., ge=0, le=120, examples=[45])
    visit_type: str = Field(..., pattern="^(new|follow-up)$", examples=["follow-up"])
    specialty: str = Field(..., examples=["cardiology"])
    comorbidity_count: int = Field(default=0, ge=0, le=20)
    physician_id: str = Field(..., examples=["D001"])
    appointment_time: Optional[datetime] = Field(
        default=None,
        description="ISO-8601 appointment datetime. Defaults to now.",
    )
    # Optional pre-computed patient/physician stats
    patient_visit_count: Optional[int] = Field(default=None, ge=0)
    patient_avg_duration: Optional[float] = Field(default=None, gt=0)
    physician_avg_duration: Optional[float] = Field(default=None, gt=0)
    physician_workload: Optional[int] = Field(default=0, ge=0)
    appointment_sequence: Optional[int] = Field(default=1, ge=1)

    @field_validator("specialty")
    @classmethod
    def normalise_specialty(cls, v: str) -> str:
        return v.lower().replace(" ", "_")


class PredictDurationResponse(BaseModel):
    predicted_duration_minutes: float
    lower_bound: float
    upper_bound: float
    confidence_pct: float
    explanation: Explanation
    nl_explanation: str
    used_fallback: bool


# ── No-show prediction ────────────────────────────────────────────────────

class PredictNoShowRequest(BaseModel):
    patient_id: str = Field(..., examples=["P12345"])
    appointment_time: datetime = Field(...)
    lead_time_days: float = Field(..., ge=0, le=180, examples=[7])
    visit_type: str = Field(..., pattern="^(new|follow-up)$", examples=["new"])
    age: Optional[int] = Field(default=None, ge=0, le=120)
    specialty: Optional[str] = Field(default=None)
    patient_no_show_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    patient_visit_count: Optional[int] = Field(default=None, ge=0)
    patient_cancellation_count: Optional[int] = Field(default=0, ge=0, le=10)
    patient_no_show_streak: Optional[int] = Field(default=0, ge=0, le=10,
        description="Number of consecutive no-shows in recent visit history")
    days_since_last_visit: Optional[float] = Field(default=None, ge=0, le=730,
        description="Days since the patient's last clinic visit")

    @field_validator("specialty")
    @classmethod
    def normalise_specialty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.lower().replace(" ", "_")
        return v


class PredictNoShowResponse(BaseModel):
    no_show_probability: float
    risk_category: str  # low / medium / high
    explanation: Explanation
    nl_explanation: str
    used_fallback: bool


# ── Appointment for simulation/optimization ───────────────────────────────

class AppointmentSlot(BaseModel):
    appointment_id: str = Field(..., examples=["A001"])
    patient_id: str = Field(..., examples=["P12345"])
    scheduled_start: datetime
    predicted_duration: Optional[float] = Field(default=None, gt=0)
    no_show_probability: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    visit_type: Optional[str] = Field(default="follow-up", pattern="^(new|follow-up)$")
    priority: Optional[int] = Field(default=1, ge=1, le=5, description="1=low, 5=urgent")


class SimulationConstraints(BaseModel):
    work_start_hour: int = Field(default=8, ge=0, le=23)
    work_end_hour: int = Field(default=17, ge=1, le=24)
    lunch_start_hour: int = Field(default=12, ge=0, le=23)
    lunch_duration_minutes: int = Field(default=60, ge=0, le=120)
    buffer_minutes: int = Field(default=5, ge=0, le=30)


# ── Day simulation ────────────────────────────────────────────────────────

class SimulateDayRequest(BaseModel):
    physician_id: str = Field(..., examples=["D001"])
    date: str = Field(..., examples=["2026-06-12"])
    appointments: list[AppointmentSlot]
    constraints: SimulationConstraints = SimulationConstraints()


class SimulatedAppointment(BaseModel):
    appointment_id: str
    patient_id: str
    scheduled_start: datetime
    predicted_start: datetime
    predicted_end: datetime
    delay_minutes: float
    is_at_risk: bool


class SimulateDayResponse(BaseModel):
    physician_id: str
    date: str
    simulated_appointments: list[SimulatedAppointment]
    total_waiting_time_minutes: float
    max_delay_minutes: float
    schedule_overrun_minutes: float
    physician_idle_time_minutes: float
    at_risk_count: int
    recommendations: list[str]


# ── Schedule optimisation ─────────────────────────────────────────────────

class OptimizeScheduleRequest(BaseModel):
    physician_id: str = Field(..., examples=["D001"])
    date: str = Field(..., examples=["2026-06-12"])
    appointments: list[AppointmentSlot]
    constraints: SimulationConstraints = SimulationConstraints()
    alpha: float = Field(default=0.5, ge=0.0, le=1.0, description="Weight: waiting time")
    beta: float = Field(default=0.3, ge=0.0, le=1.0, description="Weight: workload variance")
    gamma: float = Field(default=0.2, ge=0.0, le=1.0, description="Weight: schedule overrun")


class OptimizedAppointment(BaseModel):
    appointment_id: str
    patient_id: str
    original_start: datetime
    optimized_start: datetime
    predicted_duration: float


class OptimizeScheduleResponse(BaseModel):
    physician_id: str
    date: str
    optimized_appointments: list[OptimizedAppointment]
    expected_total_waiting_time: float
    expected_overrun_minutes: float
    improvement_pct: float
    is_optimal: bool
    nl_summary: str


# ── Waiting time ──────────────────────────────────────────────────────────

class WaitingTimeResponse(BaseModel):
    appointment_id: str
    estimated_wait_minutes: float
    confidence: str  # high / medium / low
    last_updated: datetime


# ── Health ────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    models: dict[str, bool]
    database: bool
