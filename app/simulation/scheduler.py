"""Discrete-event schedule simulation engine for ChronoCare AI.

Simulates a full physician day at 1-minute resolution, propagating delays
from one appointment to the next and identifying at-risk slots.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_DELAY_RISK_THRESHOLD_MINUTES = 15.0
_DEFAULT_BUFFER_MINUTES = 5.0
_DEFAULT_DURATION_MINUTES = 20.0


def simulate_day(data: dict[str, Any]) -> dict[str, Any]:
    """Simulate delay propagation across a physician's daily schedule.

    Args:
        data: Dictionary matching ``SimulateDayRequest`` schema (already
              model_dump()'d by the route handler).

    Returns:
        Dictionary matching ``SimulateDayResponse`` schema.
    """
    physician_id: str = data.get("physician_id", "UNKNOWN")
    date_str: str = data.get("date", datetime.utcnow().date().isoformat())
    appointments: list[dict] = data.get("appointments", [])
    constraints: dict = data.get("constraints", {})

    buffer_minutes: float = float(constraints.get("buffer_minutes", _DEFAULT_BUFFER_MINUTES))
    work_end_hour: int = int(constraints.get("work_end_hour", 17))
    lunch_start_hour: int = int(constraints.get("lunch_start_hour", 12))
    lunch_duration: float = float(constraints.get("lunch_duration_minutes", 60))

    # Parse date for work-end reference
    try:
        work_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        work_date = datetime.utcnow().date()

    work_end_dt = datetime.combine(work_date, datetime.min.time()).replace(hour=work_end_hour)
    lunch_start_dt = datetime.combine(work_date, datetime.min.time()).replace(hour=lunch_start_hour)
    lunch_end_dt = lunch_start_dt + timedelta(minutes=lunch_duration)

    # Sort appointments by scheduled start
    def _parse_dt(v: Any) -> datetime:
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
        raise ValueError(f"Cannot parse datetime: {v!r}")

    appointments.sort(key=lambda a: _parse_dt(a["scheduled_start"]))

    current_clock = None  # will be set to first appointment start
    simulated: list[dict] = []
    total_waiting = 0.0
    physician_idle = 0.0
    max_delay = 0.0

    for appt in appointments:
        sched_start = _parse_dt(appt["scheduled_start"])
        duration = float(appt.get("predicted_duration") or _DEFAULT_DURATION_MINUTES)
        no_show_prob = float(appt.get("no_show_probability") or 0.0)

        if current_clock is None:
            current_clock = sched_start  # first appointment anchors the clock

        # Skip over lunch break if current_clock has entered it
        if current_clock < lunch_end_dt and sched_start >= lunch_start_dt:
            # Appointment is after lunch – make sure we honour the break
            if current_clock < lunch_end_dt:
                physician_idle += (lunch_end_dt - current_clock).total_seconds() / 60
                current_clock = lunch_end_dt

        # Physician is idle if they finish early before this appointment
        if current_clock < sched_start:
            physician_idle += (sched_start - current_clock).total_seconds() / 60
            current_clock = sched_start

        actual_start = current_clock
        delay = (actual_start - sched_start).total_seconds() / 60
        delay = max(0.0, delay)  # no negative delays

        # Patient waiting time = how long they've been waiting past scheduled start
        patient_wait = max(0.0, (actual_start - sched_start).total_seconds() / 60)
        total_waiting += patient_wait

        # If no-show is very likely, patient doesn't come but slot is lost
        effective_duration = 0.0 if no_show_prob > 0.8 else duration
        actual_end = actual_start + timedelta(minutes=effective_duration + buffer_minutes)
        current_clock = actual_end

        is_at_risk = delay >= _DELAY_RISK_THRESHOLD_MINUTES
        max_delay = max(max_delay, delay)

        simulated.append({
            "appointment_id": appt["appointment_id"],
            "patient_id": appt["patient_id"],
            "scheduled_start": sched_start.isoformat(),
            "predicted_start": actual_start.isoformat(),
            "predicted_end": (actual_start + timedelta(minutes=effective_duration)).isoformat(),
            "delay_minutes": round(delay, 1),
            "is_at_risk": is_at_risk,
        })

    schedule_overrun = 0.0
    if current_clock and current_clock > work_end_dt:
        schedule_overrun = (current_clock - work_end_dt).total_seconds() / 60

    at_risk_count = sum(1 for a in simulated if a["is_at_risk"])
    recommendations = _generate_recommendations(simulated, max_delay, schedule_overrun, buffer_minutes)

    return {
        "physician_id": physician_id,
        "date": date_str,
        "simulated_appointments": simulated,
        "total_waiting_time_minutes": round(total_waiting, 1),
        "max_delay_minutes": round(max_delay, 1),
        "schedule_overrun_minutes": round(schedule_overrun, 1),
        "physician_idle_time_minutes": round(physician_idle, 1),
        "at_risk_count": at_risk_count,
        "recommendations": recommendations,
    }


def _generate_recommendations(
    simulated: list[dict],
    max_delay: float,
    overrun: float,
    buffer: float,
) -> list[str]:
    recs: list[str] = []

    if max_delay > 30:
        recs.append(
            f"Maximum delay exceeds 30 minutes. Consider rescheduling low-priority "
            f"follow-up appointments to reduce downstream impact."
        )
    elif max_delay > _DELAY_RISK_THRESHOLD_MINUTES:
        recs.append("Some appointments are at risk of delays >15 minutes. Monitor in real-time.")

    if overrun > 0:
        recs.append(
            f"Schedule is projected to overrun by {overrun:.0f} minutes. "
            "Consider reducing buffer or rescheduling the last appointment."
        )

    at_risk_ids = [a["appointment_id"] for a in simulated if a["is_at_risk"]]
    if at_risk_ids:
        recs.append(
            f"Appointments at risk: {', '.join(at_risk_ids[:5])}. "
            "Notify affected patients proactively."
        )

    if not recs:
        recs.append("Schedule looks well-balanced with no significant delay risks detected.")

    return recs
