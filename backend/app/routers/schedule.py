"""The worker's visit plan, produced by the scheduling agent."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.scoping import audit, visible_worker_ids
from app.core.security import get_current_worker
from app.models.db import Patient, RiskLevel, ScheduledVisit, ScheduleStatus, Worker
from app.models.schemas import CompleteScheduleRequest, ScheduledVisitOut

router = APIRouter(prefix="/api/schedule", tags=["schedule"])

PRIORITY_SORT = {RiskLevel.red: 0, RiskLevel.yellow: 1, RiskLevel.green: 2, RiskLevel.unknown: 3}


def _rows(db: Session, worker: Worker, start: date, end: date) -> list[ScheduledVisitOut]:
    allowed = visible_worker_ids(db, worker)
    stmt = (
        select(ScheduledVisit, Patient)
        .join(Patient, Patient.id == ScheduledVisit.patient_id)
        .where(
            ScheduledVisit.status == ScheduleStatus.pending,
            ScheduledVisit.due_date >= start,
            ScheduledVisit.due_date <= end,
        )
    )
    if allowed is not None:
        stmt = stmt.where(ScheduledVisit.worker_id.in_(allowed))

    today = date.today()
    out = []
    for scheduled, patient in db.execute(stmt).all():
        item = ScheduledVisitOut.model_validate(scheduled)
        item.patient_name = patient.name
        item.patient_village = patient.village
        item.overdue = scheduled.due_date < today
        out.append(item)

    # Overdue first, then by urgency, then by date: the order the round
    # should actually be walked.
    out.sort(
        key=lambda i: (not i.overdue, PRIORITY_SORT.get(i.priority, 3), i.due_date)
    )
    return out


@router.get("/today", response_model=list[ScheduledVisitOut])
def today(
    db: Session = Depends(get_db), worker: Worker = Depends(get_current_worker)
) -> list[ScheduledVisitOut]:
    """Everything due today, plus anything already overdue."""
    return _rows(db, worker, date(2000, 1, 1), date.today())


@router.get("", response_model=list[ScheduledVisitOut])
def upcoming(
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
    days: int = Query(14, ge=1, le=90),
) -> list[ScheduledVisitOut]:
    return _rows(db, worker, date(2000, 1, 1), date.today() + timedelta(days=days))


@router.post("/{schedule_id}/complete", response_model=ScheduledVisitOut)
def complete(
    schedule_id: str,
    payload: CompleteScheduleRequest,
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
) -> ScheduledVisitOut:
    scheduled = db.get(ScheduledVisit, schedule_id)
    allowed = visible_worker_ids(db, worker)
    if scheduled is None or (allowed is not None and scheduled.worker_id not in allowed):
        raise HTTPException(status_code=404, detail="Scheduled visit not found")

    scheduled.status = ScheduleStatus.done
    scheduled.completed_by_visit_id = payload.visit_id
    audit(db, worker, "complete_scheduled_visit", "scheduled_visit", scheduled.id)
    db.commit()

    patient = db.get(Patient, scheduled.patient_id)
    item = ScheduledVisitOut.model_validate(scheduled)
    item.patient_name = patient.name if patient else ""
    item.patient_village = patient.village if patient else None
    return item


@router.post("/{schedule_id}/snooze", response_model=ScheduledVisitOut)
def snooze(
    schedule_id: str,
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
    days: int = Query(1, ge=1, le=30),
) -> ScheduledVisitOut:
    """Nobody was home. Push the visit without losing it."""
    scheduled = db.get(ScheduledVisit, schedule_id)
    allowed = visible_worker_ids(db, worker)
    if scheduled is None or (allowed is not None and scheduled.worker_id not in allowed):
        raise HTTPException(status_code=404, detail="Scheduled visit not found")
    if scheduled.priority == RiskLevel.red:
        raise HTTPException(
            status_code=400,
            detail="A high-risk follow-up cannot be postponed. Record the visit or "
                   "escalate it to your ANM.",
        )

    scheduled.due_date = max(date.today(), scheduled.due_date) + timedelta(days=days)
    audit(db, worker, "snooze_scheduled_visit", "scheduled_visit", scheduled.id, f"+{days}d")
    db.commit()

    patient = db.get(Patient, scheduled.patient_id)
    item = ScheduledVisitOut.model_validate(scheduled)
    item.patient_name = patient.name if patient else ""
    item.patient_village = patient.village if patient else None
    item.overdue = scheduled.due_date < date.today()
    return item
