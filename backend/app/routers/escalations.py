import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles, CurrentUser
from app.models.db_models import RiskFlag, Visit, Patient, Worker
from app.models.schemas import EscalationOut

router = APIRouter(prefix="/api/v1/escalations", tags=["escalations"])


@router.get("/pending", response_model=list[EscalationOut])
def pending_escalations(limit: int = 20, db: Session = Depends(get_db),
                         user: CurrentUser = Depends(require_roles("anm", "bmo", "admin"))):
    rows = (
        db.query(RiskFlag, Visit, Patient, Worker)
        .join(Visit, Visit.visit_id == RiskFlag.visit_id)
        .join(Patient, Patient.patient_id == Visit.patient_id)
        .join(Worker, Worker.worker_id == Visit.worker_id)
        .filter(RiskFlag.risk_level == "HIGH", RiskFlag.actioned_at.is_(None))
        .order_by(RiskFlag.created_at.asc())
        .limit(limit)
        .all()
    )
    now = datetime.now(timezone.utc)
    out = []
    for flag, visit, patient, worker in rows:
        flagged_at = flag.created_at.replace(tzinfo=timezone.utc) if flag.created_at.tzinfo is None else flag.created_at
        hours_elapsed = round((now - flagged_at).total_seconds() / 3600, 1)
        out.append(EscalationOut(
            flag_id=flag.flag_id, patient_name=patient.name, worker_name=worker.name,
            risk_level=flag.risk_level, flagged_at=flag.created_at, hours_elapsed=hours_elapsed,
        ))
    return out


@router.post("/{flag_id}/action")
def action_escalation(flag_id: str, db: Session = Depends(get_db),
                       user: CurrentUser = Depends(require_roles("anm", "bmo", "admin"))):
    flag = db.get(RiskFlag, flag_id)
    if flag:
        flag.actioned_at = datetime.now(timezone.utc)
        db.commit()
    return {"status": "actioned"}
