"""Put the database into a known, rehearsable state for a live demo.

A demo that depends on whatever the random seed produced is a demo that breaks
in front of an audience. This script guarantees the specific patients the
runbook in docs/DEMO.md refers to, with the exact starting conditions each
scene needs - and wipes the visits and escalations from previous rehearsals so
the same demo can be run again immediately.

Run:  python -m scripts.demo_reset
      python -m scripts.demo_reset --full    # reseed everything first
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.core.database import SessionLocal, init_db
from app.core.immunisation import SCHEDULE
from app.core.security import hash_aadhaar
from app.models.db import (
    Escalation,
    InfantRecord,
    MedicalCondition,
    Patient,
    PatientCategory,
    PregnancyRecord,
    RiskLevel,
    ScheduledVisit,
    ScheduleStatus,
    Vaccination,
    Visit,
    Worker,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("demo")

DEMO_WORKER_PHONE = "9000000002"          # Sunita Devi, Bagru

# Demo patients are tagged by household id so this script can find and remove
# its own previous output. Without this the script is not re-runnable: renaming
# a demo patient leaves the old row holding the same Aadhaar hash, and that
# column is unique.
DEMO_HOUSEHOLDS = ("HH10012", "HH10058", "HH10091")

# Aadhaar numbers whose Verhoeff check digit is correct, so the registration
# scene works live. Verified by the assertion below rather than trusted - two
# of the first three written by hand here were wrong.
VALID_AADHAAR = ["234116108454", "345678901238", "456789012341"]


def _assert_aadhaar_valid() -> None:
    """Fail here, not in front of an audience."""
    from app.core.aadhaar import verify

    for number in VALID_AADHAAR:
        result = verify(number)
        if not result.valid:
            raise SystemExit(
                f"Demo Aadhaar {number} does not pass the checksum ({result.reason}). "
                "Fix VALID_AADHAAR in scripts/demo_reset.py."
            )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def wipe_demo_history(db, worker: Worker) -> None:
    """Clear this worker's visits, follow-ups and escalations so a rehearsal
    does not leave the next run pre-loaded with red flags."""
    patient_ids = db.scalars(
        select(Patient.id).where(Patient.assigned_worker_id == worker.id)
    ).all()
    if not patient_ids:
        return

    db.execute(delete(Escalation).where(Escalation.patient_id.in_(patient_ids)))
    db.execute(delete(ScheduledVisit).where(ScheduledVisit.patient_id.in_(patient_ids)))
    db.execute(delete(Visit).where(Visit.patient_id.in_(patient_ids)))
    db.commit()


def remove_previous_demo_patients(db) -> None:
    """Delete anything this script created before, with its dependent rows."""
    ids = db.scalars(
        select(Patient.id).where(Patient.household_id.in_(DEMO_HOUSEHOLDS))
    ).all()
    if not ids:
        return
    for model in (Escalation, ScheduledVisit, Visit, Vaccination,
                  InfantRecord, PregnancyRecord, MedicalCondition):
        db.execute(delete(model).where(model.patient_id.in_(ids)))
    db.execute(delete(Patient).where(Patient.id.in_(ids)))
    db.commit()


def ensure_patient(db, worker: Worker, name: str, **fields) -> Patient:
    patient = db.scalars(
        select(Patient).where(
            Patient.assigned_worker_id == worker.id, Patient.name == name
        )
    ).first()
    if patient is None:
        patient = Patient(name=name, assigned_worker_id=worker.id, **fields)
        db.add(patient)
    else:
        for key, value in fields.items():
            setattr(patient, key, value)
    db.flush()
    return patient


def add_history(db, patient: Patient, worker: Worker, days_ago: int,
                level: RiskLevel, summary: str) -> Visit:
    when = _now() - timedelta(days=days_ago)
    visit = Visit(
        client_uuid=f"demo-{patient.id[:8]}-{days_ago}",
        patient_id=patient.id,
        worker_id=worker.id,
        visited_at=when,
        synced_at=when,
        language="hi",
        status="complete",
        risk_level=level,
        risk_rationale="Recorded at a previous visit.",
        risk_confidence=0.85,
        summary=summary,
        recommended_actions=[],
        guideline_citations=[],
        danger_signs=[],
        degraded_steps=[],
    )
    db.add(visit)
    db.flush()
    patient.last_visit_at = when
    patient.last_visit_summary = summary
    patient.current_risk = level
    return visit


def schedule(db, patient: Patient, worker: Worker, due: date, reason: str,
             priority: RiskLevel) -> None:
    db.add(
        ScheduledVisit(
            patient_id=patient.id,
            worker_id=worker.id,
            due_date=due,
            reason=reason,
            priority=priority,
            status=ScheduleStatus.pending,
        )
    )


def build(db) -> None:
    worker = db.scalars(
        select(Worker).where(Worker.phone == DEMO_WORKER_PHONE)
    ).first()
    if worker is None:
        log.error("Demo worker not found. Run: python -m app.seed --reset")
        sys.exit(1)

    remove_previous_demo_patients(db)
    wipe_demo_history(db, worker)
    today = date.today()

    # --- Scene 2 & 3: the hero case -------------------------------------
    # Starts green and unremarkable, so the red classification during the demo
    # is visibly produced by what is said, not pre-baked into the record.
    kavita = ensure_patient(
        db, worker, "Roshni Solanki",
        dob=today - timedelta(days=26 * 365),
        gender="female",
        blood_group="B+",
        phone="9812345670",
        category=PatientCategory.pregnant,
        village=worker.village,
        block=worker.block,
        district=worker.district,
        address="House 12, Bagru",
        household_id="HH10012",
        aadhaar_hash=hash_aadhaar(VALID_AADHAAR[0]),
        aadhaar_last4=VALID_AADHAAR[0][-4:],
        aadhaar_verified=True,
        aadhaar_verified_at=_now() - timedelta(days=200),
        aadhaar_consent_given=True,
        aadhaar_verification_method="offline_verhoeff",
        active=True,
    )
    db.execute(delete(PregnancyRecord).where(PregnancyRecord.patient_id == kavita.id))
    lmp = today - timedelta(weeks=32)
    db.add(
        PregnancyRecord(
            patient_id=kavita.id,
            lmp=lmp,
            edd=lmp + timedelta(days=280),
            gravida=2,
            para=1,
            anc_visits_completed=3,
            tt_doses=2,
            ifa_tablets_given=180,
            last_hb=11.4,
            last_bp_systolic=118,
            last_bp_diastolic=76,
            last_weight_kg=54.0,
            high_risk_factors=[],
            planned_delivery_place="CHC Bagru",
        )
    )
    add_history(db, kavita, worker, days_ago=21, level=RiskLevel.green,
                summary="Routine ANC check, no complaints; counselled on diet and IFA.")
    schedule(db, kavita, worker, today, "Routine ANC follow-up", RiskLevel.green)

    # --- Scene 4: infant profile and immunisation -----------------------
    aarav = ensure_patient(
        db, worker, "Aarav Rathore",
        dob=today - timedelta(days=115),
        gender="male",
        blood_group="O+",
        phone=None,
        category=PatientCategory.infant,
        village=worker.village,
        block=worker.block,
        district=worker.district,
        address="House 58, Bagru",
        household_id="HH10058",
        guardian_name="Sarita Rathore",
        aadhaar_hash=None,
        aadhaar_last4=None,
        aadhaar_verified=False,
        aadhaar_consent_given=False,
        active=True,
    )
    db.execute(delete(InfantRecord).where(InfantRecord.patient_id == aarav.id))
    db.add(
        InfantRecord(
            patient_id=aarav.id,
            birth_weight_kg=2.4,
            gestation_weeks=36,
            delivery_type="Normal",
            place_of_birth="CHC Bagru",
            exclusive_breastfeeding=True,
            last_weight_kg=5.1,
            last_muac_cm=12.2,
        )
    )
    # Rebuild the schedule so the 14-week doses are visibly overdue.
    db.execute(delete(Vaccination).where(Vaccination.patient_id == aarav.id))
    for vaccine, dose, weeks in SCHEDULE:
        due = aarav.dob + timedelta(weeks=weeks)
        if due > today + timedelta(days=400):
            continue
        given = weeks <= 10
        db.add(
            Vaccination(
                patient_id=aarav.id, vaccine=vaccine, dose_label=dose,
                due_date=due, given=given,
                given_date=due + timedelta(days=2) if given else None,
                batch_no="B4471" if given else None,
            )
        )
    add_history(db, aarav, worker, days_ago=12, level=RiskLevel.green,
                summary="Weight gain on track; mother counselled on exclusive breastfeeding.")
    schedule(db, aarav, worker, today - timedelta(days=2),
             "Overdue 14-week immunisation", RiskLevel.yellow)

    # --- Scene 5: the offline case --------------------------------------
    # A separate patient so the offline visit does not disturb the hero case.
    meera = ensure_patient(
        db, worker, "Bhavna Chauhan",
        dob=today - timedelta(days=24 * 365),
        gender="female",
        blood_group="A+",
        phone="9812345671",
        category=PatientCategory.pregnant,
        village=worker.village,
        block=worker.block,
        district=worker.district,
        address="House 91, Bagru",
        household_id="HH10091",
        aadhaar_hash=hash_aadhaar(VALID_AADHAAR[1]),
        aadhaar_last4=VALID_AADHAAR[1][-4:],
        aadhaar_verified=True,
        aadhaar_verified_at=_now() - timedelta(days=120),
        aadhaar_consent_given=True,
        aadhaar_verification_method="offline_verhoeff",
        active=True,
    )
    db.execute(delete(PregnancyRecord).where(PregnancyRecord.patient_id == meera.id))
    lmp2 = today - timedelta(weeks=20)
    db.add(
        PregnancyRecord(
            patient_id=meera.id, lmp=lmp2, edd=lmp2 + timedelta(days=280),
            gravida=1, para=0, anc_visits_completed=2, tt_doses=1,
            ifa_tablets_given=90, last_hb=10.6,
            last_bp_systolic=116, last_bp_diastolic=74, last_weight_kg=48.5,
            high_risk_factors=[], planned_delivery_place="CHC Bagru",
        )
    )
    add_history(db, meera, worker, days_ago=28, level=RiskLevel.green,
                summary="Second ANC visit, mild anaemia; advised iron-rich diet and IFA.")
    schedule(db, meera, worker, today, "Routine ANC follow-up", RiskLevel.green)

    # Make sure nobody else on the roster is red, so the demo's own red flag
    # is the only one on screen and cannot be mistaken for pre-existing data.
    others = db.scalars(
        select(Patient).where(
            Patient.assigned_worker_id == worker.id,
            Patient.current_risk == RiskLevel.red,
        )
    ).all()
    for patient in others:
        patient.current_risk = RiskLevel.green

    db.commit()

    # The runbook tells the presenter to find these by typing a name. If a
    # seeded patient shares it, the search returns two rows and the demo
    # stumbles - so check, rather than assume.
    for name in ("Roshni", "Aarav", "Bhavna"):
        matches = db.scalars(
            select(Patient.name).where(
                Patient.assigned_worker_id == worker.id,
                Patient.name.ilike(f"%{name}%"),
                Patient.active.is_(True),
            )
        ).all()
        if len(matches) != 1:
            log.warning(
                "  ! searching '%s' returns %d patients (%s). Rename the demo "
                "patient in scripts/demo_reset.py so it is unique.",
                name, len(matches), ", ".join(matches),
            )

    # Any pre-existing red would compete with the one the demo produces.
    reds = db.scalars(
        select(Patient.name).where(
            Patient.assigned_worker_id == worker.id,
            Patient.current_risk == RiskLevel.red,
        )
    ).all()
    if reds:
        log.warning("  ! roster already has red patients: %s", ", ".join(reds))

    log.info("Demo state ready for %s (%s)\n", worker.name, worker.phone)
    log.info("  Roshni Solanki   pregnant, 32 weeks, GREEN   <- the hero case")
    log.info("  Aarav Rathore    infant, 16 weeks, immunisation overdue")
    log.info("  Bhavna Chauhan   pregnant, 20 weeks, GREEN   <- use for the offline scene")
    log.info("\n  Valid Aadhaar for the registration scene: %s", VALID_AADHAAR[2])
    log.info("  Sign in: %s / PIN 1234", DEMO_WORKER_PHONE)
    log.info("\n  Runbook: docs/DEMO.md")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true",
                        help="reseed the whole database first")
    args = parser.parse_args()

    _assert_aadhaar_valid()
    init_db()
    if args.full:
        from app.seed import seed
        seed(reset_first=True)

    db = SessionLocal()
    try:
        build(db)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
