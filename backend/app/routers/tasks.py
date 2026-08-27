from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, CurrentUser
from app.models.db_models import Action, Visit, Patient

router = APIRouter(prefix="/api/v1", tags=["tasks"])

URGENCY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


@router.get("/workers/{worker_id}/tasks")
def get_worker_tasks(worker_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    rows = (
        db.query(Action, Visit, Patient)
        .join(Visit, Visit.visit_id == Action.visit_id)
        .join(Patient, Patient.patient_id == Visit.patient_id)
        .filter(Visit.worker_id == worker_id, Action.type == "followup", Action.status != "complete")
        .all()
    )
    now = datetime.now(timezone.utc)
    tasks = []
    for action, visit, patient in rows:
        due_at = action.due_at.replace(tzinfo=timezone.utc) if action.due_at and action.due_at.tzinfo is None else action.due_at
        tasks.append({
            "action_id": action.action_id,
            "patient_name": patient.name,
            "patient_id": patient.patient_id,
            "risk_level": visit.risk_level,
            "content": action.content,
            "due_at": due_at,
            "overdue": bool(due_at and due_at < now),
        })
    tasks.sort(key=lambda t: URGENCY_ORDER.get(t["risk_level"], 3))
    return tasks


@router.post("/tasks/{action_id}/complete")
def complete_task(action_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    action = db.get(Action, action_id)
    if action:
        action.status = "complete"
        db.commit()
    return {"status": "complete"}
