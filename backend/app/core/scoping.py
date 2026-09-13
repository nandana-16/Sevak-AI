"""Roster scoping.

Every read or write of patient data funnels through here. Routers never build
their own `Patient` filters, so there is exactly one place where the rule
"a worker only sees the people assigned to them" can be got wrong.

An ASHA sees their own roster. An ANM sees the rosters of the workers who
report to her. An admin sees everything.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.db import AuditLog, Patient, Role, Worker


def visible_worker_ids(db: Session, worker: Worker) -> list[str] | None:
    """Worker ids whose patients this user may see. None means 'all'."""
    if worker.role == Role.admin:
        return None
    if worker.role == Role.bmo:
        # A BMO oversees a block, not a fixed reporting line - PHCs and their
        # ANMs get reorganised, and a dashboard that silently lost half a block
        # after a transfer would be worse than useless. Scope on geography.
        return db.scalars(
            select(Worker.id).where(
                Worker.block == worker.block,
                Worker.active.is_(True),
            )
        ).all()
    if worker.role == Role.anm:
        reports = db.scalars(
            select(Worker.id).where(Worker.supervisor_id == worker.id)
        ).all()
        return [worker.id, *reports]
    return [worker.id]


def patient_query(db: Session, worker: Worker) -> Select:
    stmt = select(Patient).where(Patient.active.is_(True))
    allowed = visible_worker_ids(db, worker)
    if allowed is not None:
        stmt = stmt.where(Patient.assigned_worker_id.in_(allowed))
    return stmt


def get_patient_or_404(db: Session, worker: Worker, patient_id: str) -> Patient:
    patient = db.scalars(
        patient_query(db, worker).where(Patient.id == patient_id)
    ).first()
    if patient is None:
        # Deliberately identical to the response for a patient that exists but
        # belongs to someone else: the difference would leak the roster.
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def audit(
    db: Session,
    worker: Worker | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    detail: str | None = None,
) -> None:
    db.add(
        AuditLog(
            worker_id=worker.id if worker else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
        )
    )
