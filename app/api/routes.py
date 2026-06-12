"""API routes for ChronoCare AI.

Endpoints:
  GET  /api/v1/health
  POST /api/v1/predict-duration
  POST /api/v1/predict-no-show
  POST /api/v1/simulate-day
  POST /api/v1/optimize-schedule
  GET  /api/v1/waiting-time/{appointment_id}
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.api.schemas import (
    HealthResponse,
    OptimizeScheduleRequest,
    OptimizeScheduleResponse,
    PredictDurationRequest,
    PredictDurationResponse,
    PredictNoShowRequest,
    PredictNoShowResponse,
    SimulateDayRequest,
    SimulateDayResponse,
    WaitingTimeResponse,
)
from app.ml.models import models_ready
from app.db.database import health_check as db_health
from app.services.predict import predict_duration, predict_no_show
from app.services.optimize import optimize_schedule
from app.services.schedule_state import update_from_simulation, get_waiting_time
from app.simulation.scheduler import simulate_day

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

API_VERSION = "1.0.0"


# ── Health ─────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["System"])
def health() -> dict[str, Any]:
    """Return application health including model and database status."""
    return {
        "status": "ok",
        "version": API_VERSION,
        "models": models_ready(),
        "database": db_health(),
    }


# ── Duration prediction ────────────────────────────────────────────────────

@router.post(
    "/predict-duration",
    response_model=PredictDurationResponse,
    tags=["Predictions"],
    summary="Predict appointment duration",
)
def predict_duration_endpoint(request: PredictDurationRequest) -> dict[str, Any]:
    """Predict the expected duration of an appointment with a 90% confidence interval.

    Returns a prediction, lower/upper bounds, and an explainability breakdown.
    """
    data = request.model_dump()
    if data.get("appointment_time") is None:
        data["appointment_time"] = datetime.utcnow()
    try:
        result = predict_duration(data)
    except Exception as exc:
        logger.exception("Duration prediction error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {exc}",
        ) from exc

    # Normalise explanation sub-keys for the Pydantic schema
    result["explanation"] = _normalise_explanation(result.get("explanation", {}))
    return result


# ── No-show prediction ─────────────────────────────────────────────────────

@router.post(
    "/predict-no-show",
    response_model=PredictNoShowResponse,
    tags=["Predictions"],
    summary="Predict no-show probability",
)
def predict_noshow_endpoint(request: PredictNoShowRequest) -> dict[str, Any]:
    """Predict the probability that a patient will not attend their appointment."""
    data = request.model_dump()
    try:
        result = predict_no_show(data)
    except Exception as exc:
        logger.exception("No-show prediction error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {exc}",
        ) from exc

    result["explanation"] = _normalise_explanation(result.get("explanation", {}))
    return result


# ── Day simulation ─────────────────────────────────────────────────────────

@router.post(
    "/simulate-day",
    response_model=SimulateDayResponse,
    tags=["Scheduling"],
    summary="Simulate daily schedule and delay propagation",
)
def simulate_day_endpoint(request: SimulateDayRequest) -> dict[str, Any]:
    """Simulate the full day schedule for a physician, predicting delay cascades.

    Identifies appointments at risk of >15-minute delays and provides
    actionable recommendations.
    """
    data = request.model_dump()
    try:
        result = simulate_day(data)
    except Exception as exc:
        logger.exception("Simulation error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {exc}",
        ) from exc
    # Store for live waiting-time queries
    update_from_simulation(result)
    return result


# ── Schedule optimisation ──────────────────────────────────────────────────

@router.post(
    "/optimize-schedule",
    response_model=OptimizeScheduleResponse,
    tags=["Scheduling"],
    summary="Optimise appointment schedule",
)
def optimize_schedule_endpoint(request: OptimizeScheduleRequest) -> dict[str, Any]:
    """Return an optimised appointment order that minimises waiting time,
    workload variance, and schedule overrun.
    """
    data = request.model_dump()
    try:
        result = optimize_schedule(data)
    except Exception as exc:
        logger.exception("Optimisation error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimisation failed: {exc}",
        ) from exc
    return result


# ── Waiting time ───────────────────────────────────────────────────────────

@router.get(
    "/waiting-time/{appointment_id}",
    response_model=WaitingTimeResponse,
    tags=["Scheduling"],
    summary="Get estimated waiting time for an appointment",
)
def waiting_time_endpoint(appointment_id: str) -> dict[str, Any]:
    """Return the current estimated waiting time for a given appointment.

    Populated with real data after /simulate-day has been called for the day.
    Returns a low-confidence placeholder if no simulation has been run yet.
    """
    live = get_waiting_time(appointment_id)
    if live:
        return live
    # Placeholder – no simulation run yet for this appointment
    return {
        "appointment_id": appointment_id,
        "estimated_wait_minutes": 0.0,
        "confidence": "low",
        "last_updated": datetime.utcnow(),
    }


# ── Helper ─────────────────────────────────────────────────────────────────

def _normalise_explanation(raw: dict[str, Any]) -> dict[str, Any]:
    """Ensure the explanation dict matches the ``Explanation`` schema."""
    if not raw:
        return {"base_value": None, "top_features": []}
    features = raw.get("top_features") or raw.get("features") or []
    return {
        "base_value": raw.get("base_value"),
        "top_features": [
            {
                "name": f.get("name", ""),
                "value": float(f.get("value", 0)),
                "contribution": float(f.get("contribution", 0)),
            }
            for f in features
        ],
    }

