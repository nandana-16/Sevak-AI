"""One-off data-realism fixups run after the main generator:
1. Mark historical follow-up actions whose due date has already passed as complete
   (a real deployment wouldn't have 12,000 permanently-open follow-ups sitting there).
2. Seed a handful of "today" visits so the dashboard opens with a non-zero baseline
   (matching the SRS demo script's "3 HIGH risk pins on open" framing) before the
   live Meera Patil walkthrough adds one more.

Run once: venv/Scripts/python.exe -m synthetic_data.post_seed_fixups
"""
import json
import random
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models import db_models as m
from synthetic_data.generate import DRIVER_LIBRARY, RISK_SCORE_MAP

random.seed(7)


def backfill_completed_followups(db):
    now = datetime.now(timezone.utc)
    stale = (
        db.query(m.Action)
        .filter(m.Action.type == "followup", m.Action.status != "complete", m.Action.due_at.isnot(None))
        .all()
    )
    count = 0
    for action in stale:
        due = action.due_at.replace(tzinfo=timezone.utc) if action.due_at.tzinfo is None else action.due_at
        if due < now:
            action.status = "complete"
            count += 1
    db.commit()
    print(f"Marked {count} overdue historical follow-ups as complete.")


def seed_todays_baseline(db, n_high=3, n_other=4):
    patients = db.query(m.Patient).filter(m.Patient.name != "Meera Patil").limit(200).all()
    sample = random.sample(patients, min(len(patients), n_high + n_other))
    now = datetime.now(timezone.utc)
    created = 0

    for i, patient in enumerate(sample):
        risk_level = "HIGH" if i < n_high else random.choice(["MEDIUM", "LOW"])
        structured = {
            "patient_name": patient.name, "age": patient.age,
            "vitals": {
                "bp_systolic": random.randint(142, 158) if risk_level == "HIGH" else random.randint(105, 128),
                "bp_diastolic": random.randint(92, 100) if risk_level == "HIGH" else random.randint(68, 84),
                "temperature_f": None, "weight_kg": None,
            },
            "pregnancy_stage_months": patient.pregnancy_stage_months,
            "medication_compliance": "non_compliant" if risk_level == "HIGH" else "compliant",
            "social_risk_factors": [], "symptoms_mentioned": [], "confidence": 0.85,
        }
        visit_time = now - timedelta(minutes=random.randint(5, 240))
        visit = m.Visit(
            patient_id=patient.patient_id, worker_id=patient.worker_id,
            transcript=f"[Synthetic baseline visit for {patient.name}]",
            language_code="hi", structured_json=json.dumps(structured),
            risk_score=RISK_SCORE_MAP[risk_level], risk_level=risk_level,
            pipeline_status="complete", created_at=visit_time, synced_at=visit_time,
        )
        db.add(visit)
        db.flush()
        drivers = DRIVER_LIBRARY[risk_level]
        db.add(m.RiskFlag(visit_id=visit.visit_id, risk_level=risk_level,
                           drivers_json=json.dumps(drivers), created_at=visit_time))
        if risk_level == "HIGH":
            db.add(m.Action(visit_id=visit.visit_id, type="referral",
                             content=f"Referral generated for {patient.name}.",
                             status="sent", sent_at=visit_time, created_at=visit_time))
        db.add(m.Action(visit_id=visit.visit_id, type="whatsapp",
                         content=f"Visit summary sent for {patient.name}.",
                         status="sent", sent_at=visit_time, created_at=visit_time))
        due_days = {"HIGH": 2, "MEDIUM": 7, "LOW": 30}[risk_level]
        db.add(m.Action(visit_id=visit.visit_id, type="followup",
                         content=f"Follow-up due in {due_days} days.",
                         due_at=visit_time + timedelta(days=due_days), created_at=visit_time))
        created += 1

    db.commit()
    print(f"Seeded {created} baseline visits for today ({n_high} HIGH risk).")


if __name__ == "__main__":
    db = SessionLocal()
    backfill_completed_followups(db)
    seed_todays_baseline(db)
    db.close()
