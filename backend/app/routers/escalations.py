"""Red-flag escalations, raised automatically when a visit classifies red."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.scoping import audit, visible_worker_ids
from app.core.security import get_current_worker
from app.models.db import Escalation, Patient, Worker
from app.models.schemas import EscalationOut

router = APIRouter(prefix="/api/escalations", tags=["escalations"])


@router.get("", response_model=list[EscalationOut])
def list_escalations(
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
    include_resolved: bool = False,
    limit: int = 50,
) -> list[EscalationOut]:
    allowed = visible_worker_ids(db, worker)
    stmt = (
        select(Escalation, Patient, Worker)
        .join(Patient, Patient.id == Escalation.patient_id)
        .join(Worker, Worker.id == Escalation.worker_id)
        .order_by(Escalation.raised_at.desc())
        .limit(min(limit, 200))
    )
    if not include_resolved:
        stmt = stmt.where(Escalation.resolved.is_(False))
    if allowed is not None:
        stmt = stmt.where(Escalation.worker_id.in_(allowed))

    out = []
    for escalation, patient, raiser in db.execute(stmt).all():
        item = EscalationOut.model_validate(escalation)
        item.patient_name = patient.name
        item.worker_name = raiser.name
        out.append(item)
    return out


@router.post("/{escalation_id}/acknowledge", response_model=EscalationOut)
def acknowledge(
    escalation_id: str,
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
    note: str | None = None,
) -> EscalationOut:
    escalation = db.get(Escalation, escalation_id)
    allowed = visible_worker_ids(db, worker)
    if escalation is None or (allowed is not None and escalation.worker_id not in allowed):
        raise HTTPException(status_code=404, detail="Escalation not found")

    escalation.acknowledged_at = datetime.now(timezone.utc)
    escalation.acknowledged_by = worker.id
    escalation.resolution_note = note
    escalation.resolved = True
    audit(db, worker, "acknowledge_escalation", "escalation", escalation.id)
    db.commit()

    patient = db.get(Patient, escalation.patient_id)
    raiser = db.get(Worker, escalation.worker_id)
    item = EscalationOut.model_validate(escalation)
    item.patient_name = patient.name if patient else ""
    item.worker_name = raiser.name if raiser else ""
    return item
