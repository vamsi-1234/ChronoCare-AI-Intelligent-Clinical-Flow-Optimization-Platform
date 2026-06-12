"""Generate realistic synthetic clinical scheduling data for ChronoCare AI.

v2 improvements over v1:
- 5000 records (up from 2000)
- Much cleaner feature → target correlations (less noise)
- New `cancellation_count` feature with strong no-show signal
- Physician bias is consistent (same physician always runs slightly long/short)
- Duration noise reduced to ±2 min (was ±5-10 min)

Usage:
    python scripts/generate_data.py --n 5000 --out data/synthetic_clinic_data.csv
"""
from __future__ import annotations

import argparse
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

SEED = 42
rng = np.random.default_rng(SEED)
random.seed(SEED)

SPECIALTIES = [
    "cardiology", "dermatology", "general_practice",
    "neurology", "oncology", "orthopedics",
    "pediatrics", "psychiatry", "radiology", "urology",
]

# (base_duration_mean, base_std) per specialty
SPECIALTY_BASE: dict[str, tuple[float, float]] = {
    "cardiology":        (28.0, 2.0),
    "dermatology":       (15.0, 1.5),
    "general_practice":  (18.0, 2.0),
    "neurology":         (32.0, 2.5),
    "oncology":          (36.0, 3.0),
    "orthopedics":       (22.0, 2.0),
    "pediatrics":        (18.0, 1.5),
    "psychiatry":        (42.0, 3.0),
    "radiology":         (20.0, 2.0),
    "urology":           (23.0, 2.0),
}

NUM_PHYSICIANS = 20
NUM_PATIENTS   = 600


def _generate_physicians(n: int) -> list[dict]:
    physicians = []
    for i in range(1, n + 1):
        specialty = random.choice(SPECIALTIES)
        base_mean, _ = SPECIALTY_BASE[specialty]
        # Each physician has a consistent personal bias (-3 to +4 min)
        bias = float(rng.uniform(-3, 4))
        physicians.append({
            "physician_id": f"D{i:03d}",
            "specialty": specialty,
            "avg_duration": round(base_mean + bias, 1),
            "physician_bias": bias,
        })
    return physicians


def _generate_patients(n: int) -> list[dict]:
    patients = []
    for i in range(1, n + 1):
        age = int(np.clip(rng.beta(3, 2) * 80 + 10, 1, 95))
        # Base no-show tendency (some patients are chronic no-showers)
        base_noshow = float(rng.beta(2, 12))
        # How many times have they previously cancelled (strong predictor)
        cancellation_count = int(rng.choice([0, 1, 2, 3, 4, 5], p=[0.55, 0.20, 0.12, 0.07, 0.04, 0.02]))
        patients.append({
            "patient_id": f"P{i:04d}",
            "age": age,
            "base_noshow_rate": base_noshow,
            "cancellation_count": cancellation_count,
        })
    return patients


def _generate_appointment(
    appt_id: int,
    patient: dict,
    physician: dict,
    ref_date: datetime,
    visit_history: list[dict],
) -> dict:
    specialty = physician["specialty"]
    base_mean, base_std = SPECIALTY_BASE[specialty]

    visit_type = random.choices(["new", "follow-up"], weights=[0.30, 0.70])[0]

    # Appointment time: Mon-Fri, 8 AM – 4 PM
    day_offset = random.randint(0, 364)
    appt_date = ref_date + timedelta(days=day_offset)
    while appt_date.weekday() >= 5:
        appt_date += timedelta(days=1)

    # Hours 8-16 inclusive (9 values)
    hour = random.choices(
        list(range(8, 17)),
        weights=[0.16, 0.15, 0.14, 0.13, 0.11, 0.09, 0.09, 0.07, 0.06],
    )[0]
    minute = random.choice([0, 15, 30, 45])
    appt_dt = appt_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    lead_time = int(rng.choice(range(1, 90), p=[1 / (i + 1) / sum(1 / (j + 1) for j in range(89)) for i in range(89)]))

    comorbidity_count = int(np.clip(rng.poisson(1.2 * (patient["age"] / 60)), 0, 10))

    # ── Actual duration: DETERMINISTIC base + small noise ──────────────
    duration = (
        base_mean
        + physician["physician_bias"]                # consistent physician style
        + (5.0 if visit_type == "new" else 0.0)     # new = longer
        + comorbidity_count * 2.0                   # each comorbidity adds ~2 min
        + float(rng.normal(0, base_std * 0.4))      # MUCH less noise than v1
    )
    duration = max(5.0, duration)

    # Patient history
    patient_visits = [v for v in visit_history if v["patient_id"] == patient["patient_id"]]
    patient_visit_count = len(patient_visits)
    patient_avg_duration = (
        float(np.mean([v["duration"] for v in patient_visits])) if patient_visits else base_mean
    )
    historical_no_shows = [v for v in patient_visits if not v["attended"]]
    patient_no_show_rate = (
        len(historical_no_shows) / patient_visit_count if patient_visit_count > 0
        else patient["base_noshow_rate"]
    )

    # Consecutive no-show streak (most recent visits first)
    no_show_streak = 0
    for v in reversed(patient_visits):
        if not v["attended"]:
            no_show_streak += 1
        else:
            break

    # Days since last visit (proxy for engagement / care continuity)
    if patient_visits:
        last_visit_date = patient_visits[-1].get("visit_date")
        days_since_last_visit = (appt_dt - last_visit_date).days if last_visit_date else 180
        days_since_last_visit = max(0, min(days_since_last_visit, 730))
    else:
        days_since_last_visit = 180  # first-time patients treated as long-lapsed

    # ── No-show probability: STRONG deterministic signal ──────────────
    noshow_prob = (
        patient["base_noshow_rate"]                                     # personal tendency
        + patient["cancellation_count"] * 0.08                          # each cancellation +8%
        + no_show_streak * 0.12                                         # streak: each consecutive +12%
        + (0.06 if days_since_last_visit > 180 else 0)                  # long gap = disengaged
        + (0.12 if lead_time >= 21 else 0.05 if lead_time <= 3 else 0)  # lead-time effect
        + (0.04 if visit_type == "new" else 0)                          # new patients slightly more
        + (0.03 if hour >= 15 else 0)                                   # afternoon appointments
        + (0.02 if appt_dt.weekday() == 4 else 0)                       # Friday appointments
        + float(rng.normal(0, 0.02))                                    # tiny noise
    )
    noshow_prob = float(np.clip(noshow_prob, 0.03, 0.80))
    attended = int(rng.random() > noshow_prob)

    return {
        "appointment_id": f"A{appt_id:06d}",
        "patient_id": patient["patient_id"],
        "physician_id": physician["physician_id"],
        "appointment_time": appt_dt.isoformat(),
        "visit_type": visit_type,
        "specialty": specialty,
        "age": patient["age"],
        "comorbidity_count": comorbidity_count,
        "lead_time_days": lead_time,
        "hour_of_day": hour,
        "day_of_week": appt_dt.weekday(),
        "patient_visit_count": patient_visit_count,
        "patient_avg_duration": round(patient_avg_duration, 2),
        "patient_no_show_rate": round(patient_no_show_rate, 4),
        "patient_cancellation_count": patient["cancellation_count"],
        "patient_no_show_streak": no_show_streak,
        "days_since_last_visit": days_since_last_visit,
        "physician_avg_duration": round(physician["avg_duration"], 2),
        "physician_workload": random.randint(0, 10),
        "appointment_sequence": random.randint(1, 15),
        "actual_duration": round(duration, 1),
        "attended": attended,
        "no_show_probability": round(noshow_prob, 4),
    }


def generate_data(n: int = 5000, out: str = "data/synthetic_clinic_data.csv") -> pd.DataFrame:
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    physicians = _generate_physicians(NUM_PHYSICIANS)
    patients   = _generate_patients(NUM_PATIENTS)
    ref_date   = datetime(2025, 1, 1)

    visit_history: list[dict] = []
    records = []

    for i in range(1, n + 1):
        patient    = random.choice(patients)
        physician  = random.choice(physicians)
        rec        = _generate_appointment(i, patient, physician, ref_date, visit_history)
        records.append(rec)
        visit_history.append({
            "patient_id": rec["patient_id"],
            "physician_id": rec["physician_id"],
            "duration": rec["actual_duration"],
            "attended": rec["attended"],
            "visit_date": datetime.fromisoformat(rec["appointment_time"]),
        })

    df = pd.DataFrame(records)
    df.to_csv(out_path, index=False)

    noshow_rate = 1 - df["attended"].mean()
    avg_dur     = df["actual_duration"].mean()
    dur_std     = df["actual_duration"].std()
    logger.info(
        "Generated %d records → %s\n"
        "  No-show rate: %.1f%%  |  Avg duration: %.1f ± %.1f min",
        len(df), out_path, noshow_rate * 100, avg_dur, dur_std,
    )
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic clinic data")
    parser.add_argument("--n",   type=int, default=5000)
    parser.add_argument("--out", type=str, default="data/synthetic_clinic_data.csv")
    args = parser.parse_args()
    generate_data(n=args.n, out=args.out)

