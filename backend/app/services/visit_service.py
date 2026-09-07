"""Turning a submitted visit into a processed record.

This is the seam between the HTTP layer and the agents. It owns three things
the agents deliberately do not:

* idempotency, so an offline retry does not create a second visit,
* writing the results back onto the patient (risk, last-visit note, and any
  vitals worth carrying forward),
* the side effects of a classification - the follow-up on the plan, and the
  escalation when a visit comes back red.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import pipeline, scheduling
from app.models.db import (
    Escalation,
    InputMode,
    Patient,
    RiskLevel,
    ScheduledVisit,
    ScheduleStatus,
    Visit,
    VisitStatus,
    Worker,
)

log = logging.getLogger("sevakai.visits")


def find_existing(db: Session, client_uuid: str) -> Visit | None:
    return db.scalars(select(Visit).where(Visit.client_uuid == client_uuid)).first()


def create_visit(
    db: Session,
    *,
    patient: Patient,
    worker: Worker,
    client_uuid: str,
    transcript: str | None,
    typed_notes: str | None,
    manual_fields: dict,
    input_mode: InputMode,
    language: str,
    visited_at: datetime | None,
    audio_filename: str | None = None,
) -> Visit:
    visit = Visit(
        client_uuid=client_uuid,
        patient_id=patient.id,
        worker_id=worker.id,
        visited_at=visited_at or datetime.now(timezone.utc),
        synced_at=datetime.now(timezone.utc),
        input_mode=input_mode,
        language=language,
        transcript=transcript,
        typed_notes=typed_notes,
        manual_fields=manual_fields or {},
        audio_filename=audio_filename,
        status=VisitStatus.processing,
    )
    db.add(visit)
    db.flush()
    return visit


def process(db: Session, patient: Patient, visit: Visit) -> Visit:
    """Run the agents and persist everything they produced."""
    state = pipeline.run(patient, visit)

    extracted = state.get("extracted") or {}
    vitals = state.get("vitals") or {}

    visit.extracted = extracted
    visit.symptoms = state.get("symptoms") or []
    visit.temperature_c = vitals.get("temperature_c")
    visit.bp_systolic = vitals.get("bp_systolic")
    visit.bp_diastolic = vitals.get("bp_diastolic")
    visit.pulse = vitals.get("pulse")
    visit.weight_kg = vitals.get("weight_kg")
    visit.hb = vitals.get("hb")
    visit.spo2 = vitals.get("spo2")

    try:
        level = RiskLevel(state.get("risk_level", "unknown"))
    except ValueError:
        level = RiskLevel.unknown

    visit.risk_level = level
    visit.risk_rationale = state.get("risk_rationale")
    visit.risk_confidence = state.get("risk_confidence")
    visit.guideline_citations = state.get("citations") or []
    visit.danger_signs = state.get("danger_signs") or []
    visit.recommended_actions = state.get("actions") or []
    visit.summary = state.get("summary")
    visit.degraded_steps = state.get("degraded_steps") or []
    visit.processing_ms = state.get("processing_ms")
    visit.status = VisitStatus.complete

    _update_patient(db, patient, visit, vitals)
    _schedule_follow_up(db, patient, visit, state.get("follow_up_in_days"),
                        state.get("follow_up_reason"))
    if level == RiskLevel.red:
        _raise_escalation(db, patient, visit)

    db.flush()
    return visit


def mark_failed(db: Session, visit: Visit, message: str) -> Visit:
    visit.status = VisitStatus.failed
    visit.error_message = message[:500]
    visit.risk_level = RiskLevel.unknown
    db.flush()
    return visit


def _update_patient(db: Session, patient: Patient, visit: Visit, vitals: dict) -> None:
    patient.current_risk = visit.risk_level
    patient.last_visit_at = visit.visited_at
    patient.last_visit_summary = visit.summary

    # Carry forward readings that belong on the longitudinal record rather
    # than only on this one visit.
    if patient.pregnancy:
        record = patient.pregnancy
        if vitals.get("hb") is not None:
            record.last_hb = vitals["hb"]
        if vitals.get("bp_systolic"):
            record.last_bp_systolic = vitals["bp_systolic"]
            record.last_bp_diastolic = vitals.get("bp_diastolic")
        if vitals.get("weight_kg") is not None:
            record.last_weight_kg = vitals["weight_kg"]
    if patient.infant_record:
        if vitals.get("weight_kg") is not None:
            patient.infant_record.last_weight_kg = vitals["weight_kg"]
        if vitals.get("muac_cm") is not None:
            patient.infant_record.last_muac_cm = vitals["muac_cm"]


def _schedule_follow_up(
    db: Session,
    patient: Patient,
    visit: Visit,
    days: int | None,
    reason: str | None,
) -> None:
    # This visit answers whatever was pending for this patient.
    pending = db.scalars(
        select(ScheduledVisit).where(
            ScheduledVisit.patient_id == patient.id,
            ScheduledVisit.status == ScheduleStatus.pending,
        )
    ).all()
    for item in pending:
        item.status = ScheduleStatus.done
        item.completed_by_visit_id = visit.id

    due = scheduling.follow_up_date(days or 30, visit.visited_at.date())
    db.add(
        ScheduledVisit(
            patient_id=patient.id,
            worker_id=visit.worker_id,
            due_date=due,
            reason=reason or "Follow-up visit",
            priority=visit.risk_level,
            status=ScheduleStatus.pending,
            created_by_visit_id=visit.id,
        )
    )


def _raise_escalation(db: Session, patient: Patient, visit: Visit) -> None:
    reason = visit.risk_rationale or "High risk classification"
    if visit.danger_signs:
        reason = f"{reason} Danger signs: {', '.join(visit.danger_signs[:4])}."
    db.add(
        Escalation(
            patient_id=patient.id,
            visit_id=visit.id,
            worker_id=visit.worker_id,
            reason=reason[:900],
        )
    )
    log.info("Escalation raised for patient %s from visit %s", patient.id, visit.id)


def next_due_date(db: Session, patient_id: str) -> date | None:
    row = db.scalars(
        select(ScheduledVisit.due_date)
        .where(
            ScheduledVisit.patient_id == patient_id,
            ScheduledVisit.status == ScheduleStatus.pending,
        )
        .order_by(ScheduledVisit.due_date)
    ).first()
    return row
