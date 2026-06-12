"""In-memory schedule state store.

Powers the /waiting-time/{id} endpoint with real data from simulate-day.
Updated every time /simulate-day is called.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Key: "{physician_id}:{date}"  →  {appointment_id: slot_info}
_state: dict[str, dict[str, Any]] = {}


def update_from_simulation(result: dict[str, Any]) -> None:
    """Store simulation results indexed by physician+date."""
    physician_id = result.get("physician_id", "UNKNOWN")
    date = result.get("date", "")
    key = f"{physician_id}:{date}"

    slot_map: dict[str, Any] = {}
    for slot in result.get("simulated_appointments", []):
        appt_id = slot["appointment_id"]
        try:
            sched_dt = datetime.fromisoformat(slot["scheduled_start"])
            pred_dt = datetime.fromisoformat(slot["predicted_start"])
            wait = max(0.0, (pred_dt - sched_dt).total_seconds() / 60)
        except Exception:
            wait = 0.0

        slot_map[appt_id] = {
            "estimated_wait_minutes": round(wait, 1),
            "predicted_start": slot["predicted_start"],
            "predicted_end": slot["predicted_end"],
            "delay_minutes": slot["delay_minutes"],
            "is_at_risk": slot["is_at_risk"],
            "confidence": "high" if wait < 5 else ("medium" if wait < 15 else "low"),
            "last_updated": datetime.utcnow().isoformat(),
        }

    _state[key] = slot_map
    logger.info("Schedule state updated for %s (%d appointments)", key, len(slot_map))


def get_waiting_time(appointment_id: str) -> Optional[dict[str, Any]]:
    """Look up live waiting time for an appointment ID across all stored states."""
    for slot_map in _state.values():
        if appointment_id in slot_map:
            info = slot_map[appointment_id]
            return {
                "appointment_id": appointment_id,
                "estimated_wait_minutes": info["estimated_wait_minutes"],
                "confidence": info["confidence"],
                "last_updated": info["last_updated"],
            }
    return None


def get_schedule_state(physician_id: str, date: str) -> dict[str, Any]:
    return _state.get(f"{physician_id}:{date}", {})
