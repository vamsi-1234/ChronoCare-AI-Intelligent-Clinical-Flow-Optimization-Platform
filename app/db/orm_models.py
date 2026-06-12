"""SQLAlchemy ORM models for ChronoCare AI.

Imported as ``orm_models`` to avoid shadowing the ``app.ml.models`` module.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    DateTime,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(String(50), primary_key=True, index=True)
    age = Column(Integer, CheckConstraint("age >= 0 AND age <= 120"))
    created_at = Column(DateTime, default=datetime.utcnow)

    appointments = relationship("Appointment", back_populates="patient")
    visit_history = relationship("VisitHistory", back_populates="patient")


class Physician(Base):
    __tablename__ = "physicians"

    physician_id = Column(String(50), primary_key=True, index=True)
    specialty = Column(String(100), nullable=False)
    department = Column(String(100))
    avg_consultation_duration = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    appointments = relationship("Appointment", back_populates="physician")
    visit_history = relationship("VisitHistory", back_populates="physician")


class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id = Column(String(50), primary_key=True, index=True)
    patient_id = Column(String(50), ForeignKey("patients.patient_id"), index=True)
    physician_id = Column(String(50), ForeignKey("physicians.physician_id"), index=True)
    appointment_time = Column(DateTime, nullable=False, index=True)
    visit_type = Column(
        String(20),
        CheckConstraint("visit_type IN ('new', 'follow-up')"),
    )
    specialty = Column(String(100), nullable=False)
    comorbidity_count = Column(Integer, default=0)
    actual_duration = Column(Integer)
    predicted_duration = Column(Integer)
    attended = Column(Boolean)
    no_show_probability = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="appointments")
    physician = relationship("Physician", back_populates="appointments")


class VisitHistory(Base):
    __tablename__ = "visit_history"

    visit_id = Column(String(50), primary_key=True, index=True)
    patient_id = Column(String(50), ForeignKey("patients.patient_id"), index=True)
    physician_id = Column(String(50), ForeignKey("physicians.physician_id"), index=True)
    visit_date = Column(DateTime, nullable=False)
    duration = Column(Integer, nullable=False)
    visit_type = Column(String(20))
    attended = Column(Boolean, nullable=False)

    patient = relationship("Patient", back_populates="visit_history")
    physician = relationship("Physician", back_populates="visit_history")


class DailyAppointmentRecord(Base):
    """Persisted daily-board appointment entry.

    One row per appointment on the daily board.  Created when the board is
    first loaded for a physician/date and updated as assessments, simulation
    results, and status changes come in.
    """
    __tablename__ = "daily_appointments"

    appointment_id    = Column(String(50), primary_key=True, index=True)
    patient_id        = Column(String(50), nullable=False, index=True)
    physician_id      = Column(String(50), nullable=False, index=True)
    date              = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    scheduled_start   = Column(String(30), nullable=False)
    visit_type        = Column(String(20), default="follow-up")
    specialty         = Column(String(100), nullable=False)
    age               = Column(Integer, default=45)
    comorbidity_count = Column(Integer, default=0)
    priority          = Column(Integer, default=1)
    status            = Column(String(20), default="pending")
    # AI assessment (filled by /assess)
    predicted_duration        = Column(Float)
    no_show_probability       = Column(Float)
    risk_category             = Column(String(20))
    nl_duration_explanation   = Column(String(2000))
    nl_noshow_explanation     = Column(String(2000))
    duration_lower            = Column(Float)
    duration_upper            = Column(Float)
    duration_confidence       = Column(Float)
    assessed_at               = Column(String(30))
    # Simulation results (filled by /simulate-day)
    delay_minutes    = Column(Float)
    is_at_risk       = Column(Boolean)
    predicted_start  = Column(String(30))
    # Timestamps
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

