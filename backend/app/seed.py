"""Synthetic roster for development and demos.

Deliberately small - four ASHA workers with about forty patients each - so the
data can be reasoned about and a demo can be rehearsed. The mix of categories,
risk levels and overdue immunisations is chosen to exercise every screen in the
app rather than to look impressive in a row count.

Run:  python -m app.seed [--reset]
"""

from __future__ import annotations

import argparse
import logging
import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete

from app.core.database import SessionLocal, engine, init_db
from app.core.security import hash_aadhaar, hash_pin
from app.models.db import (
    AuditLog,
    Base,
    Escalation,
    InfantRecord,
    MedicalCondition,
    Patient,
    PatientCategory,
    PregnancyRecord,
    RiskLevel,
    Role,
    ScheduledVisit,
    ScheduleStatus,
    Vaccination,
    Visit,
    Worker,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("seed")

rng = random.Random(20260908)

# --- Reference data --------------------------------------------------------

DISTRICT = "Jaipur"
BLOCK = "Sanganer"
VILLAGES = ["Bagru", "Chaksu", "Phagi", "Madhorajpur", "Kishanpura", "Nevta"]

FEMALE_NAMES = [
    "Sunita", "Meera", "Kavita", "Pooja", "Anita", "Rekha", "Savitri", "Lakshmi",
    "Geeta", "Radha", "Shanti", "Kamla", "Manju", "Sarita", "Nirmala", "Usha",
    "Pushpa", "Sushila", "Babita", "Rukmani", "Seema", "Kiran", "Asha", "Nisha",
]
MALE_NAMES = [
    "Ramesh", "Suresh", "Mahesh", "Rakesh", "Dinesh", "Mukesh", "Vijay", "Ajay",
    "Sanjay", "Rajesh", "Mohan", "Sohan", "Kailash", "Prakash", "Naresh", "Girdhari",
]
SURNAMES = [
    "Sharma", "Verma", "Meena", "Gurjar", "Yadav", "Saini", "Jat", "Kumawat",
    "Bairwa", "Regar", "Prajapat", "Choudhary",
]

BLOOD_GROUPS = ["O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-"]
BLOOD_WEIGHTS = [37, 22, 26, 7, 3, 2, 2, 1]

CHRONIC = [
    "Anaemia", "Hypertension", "Type 2 diabetes", "Hypothyroidism", "Asthma",
    "Tuberculosis (treated)", "Epilepsy",
]
PAST = [
    "Malaria", "Typhoid", "Dengue", "Chickenpox", "Jaundice", "Pneumonia",
]

# National Immunization Schedule, infant portion: (vaccine, dose, weeks after birth)
IMMUNISATION_SCHEDULE = [
    ("BCG", None, 0),
    ("Hepatitis B", "Birth dose", 0),
    ("OPV", "0", 0),
    ("OPV", "1", 6),
    ("Pentavalent", "1", 6),
    ("Rotavirus", "1", 6),
    ("fIPV", "1", 6),
    ("PCV", "1", 6),
    ("OPV", "2", 10),
    ("Pentavalent", "2", 10),
    ("Rotavirus", "2", 10),
    ("OPV", "3", 14),
    ("Pentavalent", "3", 14),
    ("Rotavirus", "3", 14),
    ("fIPV", "2", 14),
    ("PCV", "2", 14),
    ("Measles-Rubella", "1", 39),      # 9 months
    ("PCV Booster", None, 39),
    ("JE", "1", 39),
    ("Vitamin A", "1st dose", 39),
]

HIGH_RISK_FACTORS = [
    "Severe anaemia", "Previous caesarean section", "Age over 35",
    "Short stature", "Bad obstetric history", "Twin pregnancy",
    "Pregnancy induced hypertension", "Gestational diabetes",
]


def _valid_aadhaar() -> str:
    """Generate a number that passes our own Verhoeff check, so the
    registration flow can be demonstrated end to end."""
    from app.core.aadhaar import _D, _P

    inverse = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)
    body = str(rng.randint(2, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(10))
    check = 0
    for index, digit in enumerate(reversed(body)):
        check = _D[check][_P[(index + 1) % 8][int(digit)]]
    return body + str(inverse[check])


def _phone() -> str:
    return f"9{rng.randint(100000000, 999999999)}"


def _name(gender: str) -> str:
    first = rng.choice(FEMALE_NAMES if gender == "female" else MALE_NAMES)
    return f"{first} {rng.choice(SURNAMES)}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def reset(db) -> None:
    for model in (AuditLog, Escalation, ScheduledVisit, Visit, Vaccination,
                  InfantRecord, PregnancyRecord, MedicalCondition, Patient, Worker):
        db.execute(delete(model))
    db.commit()


def make_workers(db) -> list[Worker]:
    supervisor = Worker(
        name="Dr. Anita Meena",
        phone="9000000001",
        pin_hash=hash_pin("1234"),
        role=Role.anm,
        village="Sanganer PHC",
        block=BLOCK,
        district=DISTRICT,
        state="Rajasthan",
        preferred_language="hi",
    )
    db.add(supervisor)
    db.flush()

    workers = []
    for index, (name, village) in enumerate(
        [
            ("Sunita Devi", "Bagru"),
            ("Kamla Sharma", "Chaksu"),
            ("Rekha Meena", "Phagi"),
            ("Pushpa Gurjar", "Madhorajpur"),
        ],
        start=2,
    ):
        worker = Worker(
            name=name,
            phone=f"900000000{index}",
            pin_hash=hash_pin("1234"),
            role=Role.asha,
            village=village,
            block=BLOCK,
            district=DISTRICT,
            state="Rajasthan",
            supervisor_id=supervisor.id,
            preferred_language="hi",
        )
        db.add(worker)
        workers.append(worker)

    db.flush()
    return workers


def add_vaccinations(db, patient: Patient, dob: date) -> None:
    today = date.today()
    for vaccine, dose, weeks in IMMUNISATION_SCHEDULE:
        due = dob + timedelta(weeks=weeks)
        if due > today + timedelta(days=400):
            continue
        # Most due doses are given; leave a realistic minority overdue.
        given = due <= today and rng.random() < 0.82
        db.add(
            Vaccination(
                patient_id=patient.id,
                vaccine=vaccine,
                dose_label=dose,
                due_date=due,
                given=given,
                given_date=due + timedelta(days=rng.randint(0, 6)) if given else None,
                batch_no=f"B{rng.randint(1000, 9999)}" if given else None,
            )
        )


def make_patient(db, worker: Worker, category: PatientCategory) -> Patient:
    today = date.today()

    if category == PatientCategory.infant:
        gender = rng.choice(["female", "male"])
        dob = today - timedelta(days=rng.randint(2, 330))
    elif category == PatientCategory.child:
        gender = rng.choice(["female", "male"])
        dob = today - timedelta(days=rng.randint(400, 1800))
    elif category in (PatientCategory.pregnant, PatientCategory.postnatal):
        gender = "female"
        dob = today - timedelta(days=rng.randint(19, 38) * 365)
    elif category == PatientCategory.elderly:
        gender = rng.choice(["female", "male"])
        dob = today - timedelta(days=rng.randint(61, 84) * 365)
    else:
        gender = rng.choice(["female", "male"])
        dob = today - timedelta(days=rng.randint(19, 58) * 365)

    aadhaar = _valid_aadhaar()
    is_minor = category in (PatientCategory.infant, PatientCategory.child)

    patient = Patient(
        name=_name(gender),
        dob=dob,
        gender=gender,
        blood_group=rng.choices(BLOOD_GROUPS, weights=BLOOD_WEIGHTS)[0],
        phone=None if is_minor else _phone(),
        category=category,
        village=worker.village,
        block=BLOCK,
        district=DISTRICT,
        address=f"House {rng.randint(1, 240)}, {worker.village}",
        household_id=f"HH{rng.randint(10000, 99999)}",
        guardian_name=_name("female") if is_minor else None,
        # Infants are usually registered against a guardian's Aadhaar, so a
        # realistic roster has some without their own.
        aadhaar_hash=None if (is_minor and rng.random() < 0.5) else hash_aadhaar(aadhaar),
        aadhaar_last4=None if (is_minor and rng.random() < 0.5) else aadhaar[-4:],
        aadhaar_verified=not is_minor or rng.random() > 0.5,
        aadhaar_verified_at=_now() - timedelta(days=rng.randint(10, 600)),
        aadhaar_consent_given=True,
        aadhaar_verification_method="offline_verhoeff",
        assigned_worker_id=worker.id,
    )
    db.add(patient)
    db.flush()

    if category == PatientCategory.pregnant:
        weeks = rng.randint(6, 38)
        lmp = today - timedelta(weeks=weeks)
        high_risk = rng.sample(HIGH_RISK_FACTORS, k=rng.choice([0, 0, 0, 1, 1, 2]))
        db.add(
            PregnancyRecord(
                patient_id=patient.id,
                lmp=lmp,
                edd=lmp + timedelta(days=280),
                gravida=rng.randint(1, 4),
                para=rng.randint(0, 3),
                anc_visits_completed=min(4, weeks // 9),
                tt_doses=min(2, weeks // 14),
                ifa_tablets_given=weeks * rng.randint(4, 7),
                last_hb=round(rng.uniform(6.4, 12.8), 1),
                last_bp_systolic=rng.choice([106, 110, 114, 118, 122, 128, 134, 142, 150]),
                last_bp_diastolic=rng.choice([68, 70, 74, 78, 82, 86, 90, 96]),
                last_weight_kg=round(rng.uniform(41, 68), 1),
                high_risk_factors=high_risk,
                planned_delivery_place=rng.choice(
                    ["Sanganer PHC", "CHC Bagru", "Jaipur District Hospital"]
                ),
            )
        )

    if category == PatientCategory.infant:
        db.add(
            InfantRecord(
                patient_id=patient.id,
                birth_weight_kg=round(rng.uniform(1.9, 3.6), 2),
                gestation_weeks=rng.choice([34, 36, 37, 38, 39, 40, 40, 41]),
                delivery_type=rng.choice(["Normal", "Normal", "Normal", "Caesarean"]),
                place_of_birth=rng.choice(["Sanganer PHC", "CHC Bagru", "Home"]),
                exclusive_breastfeeding=rng.random() < 0.7,
                last_weight_kg=round(rng.uniform(2.4, 9.0), 2),
                last_muac_cm=round(rng.uniform(10.8, 15.0), 1),
            )
        )
        add_vaccinations(db, patient, dob)
    elif category == PatientCategory.child:
        add_vaccinations(db, patient, dob)

    for name in rng.sample(CHRONIC, k=rng.choice([0, 0, 0, 1, 1, 2])):
        db.add(
            MedicalCondition(
                patient_id=patient.id,
                name=name,
                diagnosed_on=today - timedelta(days=rng.randint(90, 2500)),
                ongoing=True,
            )
        )
    for name in rng.sample(PAST, k=rng.choice([0, 0, 1, 1, 2])):
        db.add(
            MedicalCondition(
                patient_id=patient.id,
                name=name,
                diagnosed_on=today - timedelta(days=rng.randint(200, 3000)),
                ongoing=False,
            )
        )

    return patient


CATEGORY_MIX = (
    [PatientCategory.pregnant] * 9
    + [PatientCategory.infant] * 8
    + [PatientCategory.child] * 7
    + [PatientCategory.postnatal] * 3
    + [PatientCategory.adult] * 9
    + [PatientCategory.elderly] * 4
)

SUMMARY_TEMPLATES = {
    RiskLevel.green: [
        "Routine check, no complaints; counselled on diet and rest.",
        "Doing well, weight steady; reminded about next ANC visit.",
        "No danger signs; family counselled on hygiene and feeding.",
    ],
    RiskLevel.yellow: [
        "Mild anaemia noted; advised IFA daily and doctor review this week.",
        "Blood pressure slightly raised; asked to see ANM within a few days.",
        "Fever for two days without danger signs; to be re-checked shortly.",
    ],
    RiskLevel.red: [
        "Severe anaemia found; referred to CHC same day.",
        "High BP with headache; accompanied to facility for urgent review.",
        "Infant feeding poorly and lethargic; referred immediately.",
    ],
}


def make_history(db, patient: Patient, worker: Worker) -> None:
    """A few past visits so profiles are not blank on first open."""
    count = rng.randint(1, 4)
    last_visit: Visit | None = None

    for index in range(count):
        days_ago = 14 * (count - index) + rng.randint(0, 6)
        when = _now() - timedelta(days=days_ago)
        level = rng.choices(
            [RiskLevel.green, RiskLevel.yellow, RiskLevel.red], weights=[68, 26, 6]
        )[0]
        visit = Visit(
            client_uuid=f"seed-{patient.id[:8]}-{index}",
            patient_id=patient.id,
            worker_id=worker.id,
            visited_at=when,
            synced_at=when,
            language="hi",
            status="complete",
            risk_level=level,
            risk_rationale="Recorded during a previous round.",
            risk_confidence=0.8,
            summary=rng.choice(SUMMARY_TEMPLATES[level]),
            recommended_actions=[],
            guideline_citations=[],
            danger_signs=[],
            degraded_steps=[],
        )
        db.add(visit)
        last_visit = visit

    db.flush()
    if last_visit:
        patient.last_visit_at = last_visit.visited_at
        patient.last_visit_summary = last_visit.summary
        patient.current_risk = last_visit.risk_level

        # Follow-ups spread across the coming days so the plan screen has
        # something in it, plus a few overdue ones.
        offset = {RiskLevel.red: 1, RiskLevel.yellow: 4}.get(last_visit.risk_level, 21)
        due = date.today() + timedelta(days=rng.randint(-4, offset))
        db.add(
            ScheduledVisit(
                patient_id=patient.id,
                worker_id=worker.id,
                due_date=due,
                reason=f"Follow-up after {last_visit.risk_level.value} classification",
                priority=last_visit.risk_level,
                status=ScheduleStatus.pending,
                created_by_visit_id=last_visit.id,
            )
        )


def seed(reset_first: bool = False) -> None:
    init_db()
    db = SessionLocal()
    try:
        if reset_first:
            reset(db)
            log.info("Cleared existing rows")

        if db.query(Worker).count():
            log.info("Database already seeded; pass --reset to rebuild")
            return

        workers = make_workers(db)
        total = 0
        for worker in workers:
            mix = CATEGORY_MIX[:]
            rng.shuffle(mix)
            for category in mix[: rng.randint(36, 42)]:
                patient = make_patient(db, worker, category)
                make_history(db, patient, worker)
                total += 1
            db.commit()
            log.info("  %-16s %d patients", worker.name, len(worker.patients))

        db.commit()
        log.info("Seeded %d workers and %d patients", len(workers) + 1, total)
        log.info("Login: phone 9000000002 / PIN 1234  (ASHA Sunita Devi)")
        log.info("       phone 9000000001 / PIN 1234  (ANM supervisor)")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    if args.reset:
        Base.metadata.create_all(engine)
    seed(reset_first=args.reset)
