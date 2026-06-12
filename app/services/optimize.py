"""Schedule optimisation service for ChronoCare AI.

Booking-optimizer approach
──────────────────────────
Takes a list of patients to be scheduled for a day and assigns optimal
start times by:

1. Trying four different ordering strategies (priority-first, show-first,
   short-first, hybrid).
2. For each ordering, assigning start times based on **predicted durations**
   (not fixed 30-minute slots).
3. Comparing each ordering against the **naive 30-minute-slot baseline** to
   compute the improvement percentage.
4. Returning the ordering with the lowest weighted objective score.

Why this matters
────────────────
- A 40-minute cardiology appointment assigned a 30-minute slot causes every
  subsequent patient to wait.  Using predicted durations eliminates this.
- Reordering high-priority / likely-to-show patients to morning slots reduces
  total cascading delay.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_DURATION = 20.0
_NAIVE_SLOT = 30.0  # minutes per slot in the baseline scenario


# ── Internal helpers ──────────────────────────────────────────────────────

def _parse_dt(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {v!r}")


def _skip_lunch(clock: datetime, duration: float, lunch_start: datetime, lunch_end: datetime) -> datetime:
    """Advance clock past lunch if the appointment would overlap."""
    if lunch_start <= clock < lunch_end:
        return lunch_end
    if clock < lunch_start and clock + timedelta(minutes=duration) > lunch_start:
        return lunch_end
    return clock


def _assign_slots(
    appointments: list[dict],
    day_start: datetime,
    lunch_start: datetime,
    lunch_end: datetime,
    buffer: float,
    slot_duration: float | None = None,
) -> list[dict]:
    """Assign start times sequentially.

    If *slot_duration* is None, use each appointment's predicted_duration.
    Returns list of dicts with 'optimized_start' added.
    """
    clock = day_start
    result = []
    for appt in appointments:
        dur = float(slot_duration or appt.get("predicted_duration") or _DEFAULT_DURATION)
        clock = _skip_lunch(clock, dur, lunch_start, lunch_end)
        result.append({**appt, "optimized_start": clock.isoformat(), "_dur": dur})
        clock += timedelta(minutes=dur + buffer)
    return result


def _simulate_wait(slots: list[dict], day_end: datetime) -> tuple[float, float]:
    """Given assigned slots, compute total patient waiting time and overrun.

    Patients arrive at their 'optimized_start'.  Waiting time is non-zero
    only when a physician runs over (which doesn't happen in smart-slot mode).
    For the *naive-baseline* comparison we also run this function.
    """
    clock: datetime | None = None
    total_wait = 0.0

    for slot in slots:
        sched = _parse_dt(slot["optimized_start"])
        dur = float(slot.get("_dur") or slot.get("predicted_duration") or _DEFAULT_DURATION)
        if clock is None:
            clock = sched
        if clock < sched:
            clock = sched  # physician idles
        wait = max(0.0, (clock - sched).total_seconds() / 60)
        total_wait += wait
        clock += timedelta(minutes=dur)

    overrun = max(0.0, (clock - day_end).total_seconds() / 60) if clock else 0.0
    return total_wait, overrun


# ── Ordering strategies ────────────────────────────────────────────────────

def _sort_priority_first(appts: list[dict]) -> list[dict]:
    """Urgent and short appointments first."""
    return sorted(appts, key=lambda a: (
        -int(a.get("priority") or 1),
        float(a.get("predicted_duration") or _DEFAULT_DURATION),
    ))


def _sort_show_first(appts: list[dict]) -> list[dict]:
    """Patients most likely to attend go first (lower no-show risk first)."""
    return sorted(appts, key=lambda a: (
        float(a.get("no_show_probability") or 0.15),
        -int(a.get("priority") or 1),
    ))


def _sort_short_first(appts: list[dict]) -> list[dict]:
    """Shortest-processing-time (SPT) – minimises average wait."""
    return sorted(appts, key=lambda a: float(a.get("predicted_duration") or _DEFAULT_DURATION))


def _sort_hybrid(appts: list[dict]) -> list[dict]:
    """New patients and high-priority in morning, likely no-shows at end."""
    return sorted(appts, key=lambda a: (
        float(a.get("no_show_probability") or 0.15),          # likely-shows first
        -int((a.get("visit_type") or "follow-up") == "new"),  # new patients before follow-ups
        -int(a.get("priority") or 1),
        float(a.get("predicted_duration") or _DEFAULT_DURATION),
    ))


# ── Public API ─────────────────────────────────────────────────────────────

def optimize_schedule(data: dict[str, Any]) -> dict[str, Any]:
    """Return an optimised booking schedule with improvement vs 30-min-slot baseline.

    Args:
        data: Dictionary matching ``OptimizeScheduleRequest`` schema.

    Returns:
        Dictionary matching ``OptimizeScheduleResponse`` schema.
    """
    physician_id: str = data.get("physician_id", "UNKNOWN")
    date_str: str = data.get("date", datetime.utcnow().date().isoformat())
    appointments: list[dict] = list(data.get("appointments", []))
    constraints: dict = data.get("constraints", {})
    alpha: float = float(data.get("alpha", 0.5))
    gamma: float = float(data.get("gamma", 0.2))

    if not appointments:
        return _empty_response(physician_id, date_str)

    buffer: float = float(constraints.get("buffer_minutes", 5))
    work_start_hour: int = int(constraints.get("work_start_hour", 8))
    work_end_hour: int = int(constraints.get("work_end_hour", 17))
    lunch_start_hour: int = int(constraints.get("lunch_start_hour", 12))
    lunch_dur: float = float(constraints.get("lunch_duration_minutes", 60))

    try:
        work_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        work_date = datetime.utcnow().date()

    day_start = datetime.combine(work_date, datetime.min.time()).replace(hour=work_start_hour)
    day_end   = datetime.combine(work_date, datetime.min.time()).replace(hour=work_end_hour)
    lunch_start = datetime.combine(work_date, datetime.min.time()).replace(hour=lunch_start_hour)
    lunch_end   = lunch_start + timedelta(minutes=lunch_dur)

    # ── Baseline: naive 30-minute fixed slots in ORIGINAL order ───────────
    baseline_slots = _assign_slots(
        appointments, day_start, lunch_start, lunch_end, buffer,
        slot_duration=_NAIVE_SLOT,
    )
    baseline_wait, baseline_overrun = _simulate_wait(baseline_slots, day_end)

    # ── Try four orderings with PREDICTED-DURATION slots ──────────────────
    strategies = [
        _sort_priority_first,
        _sort_show_first,
        _sort_short_first,
        _sort_hybrid,
    ]
    strategy_names = ["priority-first", "show-first", "short-first", "hybrid"]

    best_wait, best_overrun = float("inf"), float("inf")
    best_order: list[dict] = appointments
    best_strategy = "original"

    for strategy, name in zip(strategies, strategy_names):
        ordered = strategy(appointments)
        slots = _assign_slots(ordered, day_start, lunch_start, lunch_end, buffer)
        wait, overrun = _simulate_wait(slots, day_end)
        score = alpha * wait + gamma * overrun
        best_score = alpha * best_wait + gamma * best_overrun
        if score < best_score:
            best_wait, best_overrun = wait, overrun
            best_order = ordered
            best_strategy = name

    # Build final schedule with optimised start times
    final_slots = _assign_slots(best_order, day_start, lunch_start, lunch_end, buffer)

    improvement_pct = 0.0
    if baseline_wait > 0:
        improvement_pct = max(0.0, (baseline_wait - best_wait) / baseline_wait * 100)

    # Savings summary
    saved_wait = round(baseline_wait - best_wait, 1)

    summary = (
        f"Schedule optimised for {len(final_slots)} appointments using the "
        f"'{best_strategy}' strategy. "
        f"Expected total waiting time: {best_wait:.0f} min "
        f"(vs {baseline_wait:.0f} min with fixed 30-min slots — "
        f"{improvement_pct:.1f}% reduction, saving ~{saved_wait} min). "
        f"Projected overrun: {best_overrun:.0f} min."
    )

    return {
        "physician_id": physician_id,
        "date": date_str,
        "optimized_appointments": [
            {
                "appointment_id": appt["appointment_id"],
                "patient_id": appt["patient_id"],
                "original_start": _parse_dt(appt["scheduled_start"]).isoformat(),
                "optimized_start": slot["optimized_start"],
                "predicted_duration": round(float(appt.get("predicted_duration") or _DEFAULT_DURATION), 1),
            }
            for appt, slot in zip(best_order, final_slots)
        ],
        "expected_total_waiting_time": round(best_wait, 1),
        "expected_overrun_minutes": round(best_overrun, 1),
        "improvement_pct": round(improvement_pct, 1),
        "is_optimal": True,
        "nl_summary": summary,
    }


def _empty_response(physician_id: str, date_str: str) -> dict[str, Any]:
    return {
        "physician_id": physician_id,
        "date": date_str,
        "optimized_appointments": [],
        "expected_total_waiting_time": 0.0,
        "expected_overrun_minutes": 0.0,
        "improvement_pct": 0.0,
        "is_optimal": True,
        "nl_summary": "No appointments provided.",
    }


