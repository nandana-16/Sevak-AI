"""Synthetic demo dataset generator (SRS 12.2): 500 ASHA workers, 5,000 patients,
3 months of visit history — zero real patient data, per DPDP compliance (NFR-SC5).

Historical visits are generated directly with realistic distributions (not run
through the live LLM pipeline — that would be extremely slow for 5,000+ patients).
The live demo pipeline is exercised for real via the API for the featured demo
patient, Meera Patil, and any visit an operator records live.

Run: venv/Scripts/python.exe -m synthetic_data.generate
"""
import json
import random
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from faker import Faker
from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_pin
from app.models import db_models as m

fake = Faker("en_IN")
Faker.seed(42)
random.seed(42)

VILLAGES = [
    "Wagholi", "Hadapsar", "Manjari", "Loni Kalbhor", "Uruli Kanchan", "Saswad",
    "Khed Shivapur", "Bhor", "Velhe", "Mulshi", "Paud", "Talegaon", "Chakan",
    "Rajgurunagar", "Shirur", "Baramati", "Indapur", "Daund", "Purandar", "Junnar",
]

DRIVER_LIBRARY = {
    "HIGH": [
        {"observation": "BP 148/96", "protocol_reference": "NHM-MH-04",
         "reason": "Blood pressure exceeds the 140/90 mmHg pre-eclampsia threshold."},
        {"observation": "Severe headache reported", "protocol_reference": "NHM-MH-06",
         "reason": "Severe headache in pregnancy is a pre-eclampsia warning sign."},
        {"observation": "MUAC 11.2 cm", "protocol_reference": "NHM-CH-04",
         "reason": "MUAC below 11.5 cm indicates severe acute malnutrition."},
    ],
    "MEDIUM": [
        {"observation": "IFA non-compliance, 2 weeks", "protocol_reference": "NHM-MH-02",
         "reason": "Missed iron-folic acid supplementation increases anemia risk."},
        {"observation": "Household isolation noted", "protocol_reference": "NHM-SOC-01",
         "reason": "Social isolation correlates with delayed care-seeking."},
        {"observation": "Immunization 5 weeks behind schedule", "protocol_reference": "NHM-CH-06",
         "reason": "Child is behind the national immunization schedule."},
    ],
    "LOW": [
        {"observation": "All vitals within normal range", "protocol_reference": "NHM-MH-01",
         "reason": "Routine antenatal screening shows no abnormal findings."},
    ],
}

RISK_SCORE_MAP = {"HIGH": 0.9, "MEDIUM": 0.6, "LOW": 0.2}
RISK_WEIGHTS = [("LOW", 0.70), ("MEDIUM", 0.20), ("HIGH", 0.10)]


def weighted_risk() -> str:
    r = random.random()
    cumulative = 0.0
    for level, w in RISK_WEIGHTS:
        cumulative += w
        if r <= cumulative:
            return level
    return "LOW"


def make_worker(role="asha", district="Pune", sub_centre=None, village=None, phone=None, name=None, pin="1234"):
    return m.Worker(
        name=name or fake.name(),
        phone=phone or fake.unique.msisdn()[-10:],
        pin_hash=hash_pin(pin),
        role=role,
        language_pref=random.choice(["hi", "mr", "ta", "te", "bn"]),
        sub_centre_id=sub_centre or f"SC-{random.randint(1, 60):03d}",
        district=district,
        village=village or random.choice(VILLAGES),
    )


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    existing = db.query(m.Worker).count()
    if existing > 0:
        print(f"Database already has {existing} workers. Skipping generation to avoid duplicates. "
              f"Delete backend/data/sevakai.db to regenerate from scratch.")
        return

    print("Creating demo accounts (fixed credentials for team + judges)...")
    demo_asha = make_worker(role="asha", name="Sunita Sharma", phone="9999900001",
                             village="Wagholi", sub_centre="SC-001")
    demo_anm = make_worker(role="anm", name="Kavita Joshi", phone="9999900002",
                            village="Wagholi", sub_centre="SC-001")
    demo_bmo = make_worker(role="bmo", name="Rajesh Kulkarni", phone="9999900003",
                            village="Wagholi", sub_centre="SC-001")
    demo_admin = make_worker(role="admin", name="Admin User", phone="9999900004",
                              village="Wagholi", sub_centre="SC-001")
    db.add_all([demo_asha, demo_anm, demo_bmo, demo_admin])
    db.flush()

    meera = m.Patient(
        worker_id=demo_asha.worker_id, name="Meera Patil", age=28, gender="female",
        village="Wagholi", phone=fake.unique.msisdn()[-10:], category="pregnant",
        pregnancy_stage_months=6,
    )
    db.add(meera)
    db.flush()

    prior_visit_time = datetime.now(timezone.utc) - timedelta(days=7)
    prior_visit = m.Visit(
        patient_id=meera.patient_id, worker_id=demo_asha.worker_id,
        transcript="Meera Patil, 28 saal, 6 mahine ki pregnancy. BP normal tha, sab theek laga.",
        language_code="hi",
        structured_json=json.dumps({
            "patient_name": "Meera Patil", "age": 28,
            "vitals": {"bp_systolic": 118, "bp_diastolic": 76, "temperature_f": None, "weight_kg": 58},
            "pregnancy_stage_months": 6, "medication_compliance": "compliant",
            "social_risk_factors": [], "symptoms_mentioned": [], "confidence": 0.9,
        }),
        risk_score=0.2, risk_level="LOW", pipeline_status="complete",
        created_at=prior_visit_time,
    )
    db.add(prior_visit)
    db.flush()
    db.add(m.RiskFlag(visit_id=prior_visit.visit_id, risk_level="LOW",
                       drivers_json=json.dumps(DRIVER_LIBRARY["LOW"]), created_at=prior_visit_time))

    print("Generating 500 ASHA workers...")
    workers = [demo_asha]
    for _ in range(500):
        workers.append(make_worker())
    db.add_all(workers[1:])
    db.flush()

    print("Generating 5,000 patients...")
    patients = [meera]
    categories = [("pregnant", 0.4), ("child", 0.25), ("general", 0.35)]
    for _ in range(4999):
        worker = random.choice(workers)
        cat_r = random.random()
        cum = 0.0
        category = "general"
        for c, w in categories:
            cum += w
            if cat_r <= cum:
                category = c
                break
        patient = m.Patient(
            worker_id=worker.worker_id,
            name=fake.name(),
            age=random.randint(0, 5) if category == "child" else random.randint(16, 45),
            gender=random.choice(["male", "female"]),
            village=worker.village,
            phone=fake.unique.msisdn()[-10:],
            category=category,
            pregnancy_stage_months=random.randint(1, 9) if category == "pregnant" else None,
        )
        patients.append(patient)
    db.add_all(patients[1:])
    db.flush()
    print(f"  {len(patients)} patients created.")

    print("Generating ~3 months of visit history (this may take a minute)...")
    now = datetime.now(timezone.utc)
    visit_count = 0
    unactioned_high_count = 0

    for patient in patients:
        if patient is meera:
            continue
        num_visits = random.randint(1, 4)
        for _ in range(num_visits):
            days_ago = random.randint(1, 90)
            visit_time = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            risk_level = weighted_risk()

            structured = {
                "patient_name": patient.name, "age": patient.age,
                "vitals": {
                    "bp_systolic": random.randint(140, 160) if risk_level == "HIGH" and patient.category == "pregnant" else random.randint(100, 130),
                    "bp_diastolic": random.randint(90, 100) if risk_level == "HIGH" and patient.category == "pregnant" else random.randint(65, 85),
                    "temperature_f": None, "weight_kg": None,
                },
                "pregnancy_stage_months": patient.pregnancy_stage_months,
                "medication_compliance": random.choice(["compliant", "non_compliant", "unknown"]),
                "social_risk_factors": random.sample(
                    ["household_isolation", "absent_spouse", "economic_stress"], k=random.choice([0, 0, 1])
                ),
                "symptoms_mentioned": [], "confidence": round(random.uniform(0.7, 0.95), 2),
            }

            visit = m.Visit(
                patient_id=patient.patient_id, worker_id=patient.worker_id,
                transcript=f"[Synthetic historical visit for {patient.name}]",
                language_code="hi", structured_json=json.dumps(structured),
                risk_score=RISK_SCORE_MAP[risk_level], risk_level=risk_level,
                pipeline_status="complete", created_at=visit_time,
                synced_at=visit_time,
            )
            db.add(visit)
            db.flush()

            drivers = random.sample(DRIVER_LIBRARY[risk_level], k=min(2, len(DRIVER_LIBRARY[risk_level]))) \
                if risk_level != "LOW" else DRIVER_LIBRARY["LOW"]
            flag = m.RiskFlag(visit_id=visit.visit_id, risk_level=risk_level,
                               drivers_json=json.dumps(drivers), created_at=visit_time)

            # Leave ~15% of older HIGH-risk cases unactioned so the escalation
            # sweep/dashboard has real overdue cases to demonstrate.
            if risk_level == "HIGH" and days_ago > 3 and random.random() < 0.15:
                unactioned_high_count += 1
            else:
                if risk_level == "HIGH":
                    flag.actioned_at = visit_time + timedelta(hours=random.randint(1, 40))
            db.add(flag)

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

            visit_count += 1

        if visit_count % 1000 < num_visits:
            db.commit()
            print(f"  ...{visit_count} visits so far")

    db.commit()
    print(f"Done. {len(patients)} patients, {visit_count} visits, "
          f"{unactioned_high_count} unactioned HIGH-risk cases left for escalation demo.")
    print("\nDemo login credentials (phone / PIN):")
    print("  ASHA worker (Sunita Sharma): 9999900001 / 1234")
    print("  ANM supervisor (Kavita Joshi): 9999900002 / 1234")
    print("  BMO (Rajesh Kulkarni): 9999900003 / 1234")
    print("  Admin: 9999900004 / 1234")
    print(f"  Demo patient for live pipeline walkthrough: Meera Patil (patient_id={meera.patient_id})")
    db.close()


if __name__ == "__main__":
    main()
