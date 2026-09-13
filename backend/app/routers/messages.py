"""The message outbox.

Scoped exactly like everything else: a worker sees the messages arising from
her own roster, an ANM sees her workers', a BMO sees the block. The scope is
taken from `Message.worker_id` - the person responsible for the message, which
for an escalation is the supervisor being notified rather than the ASHA who
triggered it, so an alert appears in the inbox of whoever has to act on it.

Every response carries `simulated`, and it is true for the whole of the default
configuration. See app/services/messaging.py for why.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.scoping import audit, visible_worker_ids
from app.core.security import get_current_worker
from app.models.db import Message, MessageStatus, MessageType, Patient, Worker
from app.models.schemas import DispatchResult, MessageList, MessageOut
from app.services import messaging

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("", response_model=MessageList)
def list_messages(
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
    status: MessageStatus | None = None,
    message_type: MessageType | None = None,
    patient_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> MessageList:
    allowed = visible_worker_ids(db, worker)
    stmt = (
        select(Message)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    if allowed is not None:
        stmt = stmt.where(Message.worker_id.in_(allowed))
    if status is not None:
        stmt = stmt.where(Message.status == status)
    if message_type is not None:
        stmt = stmt.where(Message.message_type == message_type)
    if patient_id is not None:
        # Scoped already by worker_id above, so this cannot widen what is
        # visible - only narrow it to one patient's thread.
        stmt = stmt.where(Message.patient_id == patient_id)

    rows = list(db.scalars(stmt).all())

    # The same filters without the ordering or the page limit.
    total = db.scalar(
        select(func.count()).select_from(stmt.limit(None).order_by(None).subquery())
    ) or 0

    # One lookup for the names rather than one per row.
    patient_ids = {m.patient_id for m in rows if m.patient_id}
    names = {}
    if patient_ids:
        names = {
            p.id: p.name
            for p in db.scalars(select(Patient).where(Patient.id.in_(patient_ids))).all()
        }

    out = []
    for message in rows:
        item = MessageOut.model_validate(message)
        item.message_type = message.message_type.value
        item.status = message.status.value
        item.patient_name = names.get(message.patient_id or "", "")
        out.append(item)

    return MessageList(
        simulated=messaging.is_simulated(),
        provider=messaging.provider_name(),
        total=int(total),
        messages=out,
    )


@router.post("/dispatch", response_model=DispatchResult)
def dispatch(
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
) -> DispatchResult:
    """Send everything whose date has come.

    In a deployment this would be a scheduled job rather than an endpoint. It
    is exposed so the queue can be driven on demand - both for the demo, and
    because a supervisor watching a red case should be able to push the
    outbox rather than wait for a timer.
    """
    result = messaging.dispatch_due(db, visible_worker_ids(db, worker))
    audit(db, worker, "dispatch_messages", "message", None)
    db.commit()
    return DispatchResult(**result)


@router.post("/{message_id}/send", response_model=MessageOut)
def send_one(
    message_id: str,
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
) -> MessageOut:
    """Send a single message now, ignoring its scheduled date."""
    message = db.get(Message, message_id)
    allowed = visible_worker_ids(db, worker)
    if message is None or (allowed is not None and message.worker_id not in allowed):
        raise HTTPException(status_code=404, detail="Message not found")
    if message.status == MessageStatus.sent:
        raise HTTPException(status_code=409, detail="Message has already been sent")
    if not message.to_phone:
        raise HTTPException(
            status_code=409,
            detail="No phone number on file - this one has to be delivered in person",
        )

    messaging.deliver(message)
    audit(db, worker, "send_message", "message", message.id)
    db.commit()

    item = MessageOut.model_validate(message)
    item.message_type = message.message_type.value
    item.status = message.status.value
    patient = db.get(Patient, message.patient_id) if message.patient_id else None
    item.patient_name = patient.name if patient else ""
    return item
