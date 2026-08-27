"""Agent 5 (Escalation) background sweep — fires an alert to the BMO for any HIGH-risk
case that has gone unactioned past the 48-hour threshold (FR-06.1)."""
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.db_models import RiskFlag, Visit, Patient, Worker
from app.services.whatsapp import send_whatsapp_message
from app.services.audit import log_action


def run_escalation_sweep(db: Session) -> int:
    threshold = timedelta(hours=settings.escalation_threshold_hours)
    now = datetime.now(timezone.utc)

    candidates = (
        db.query(RiskFlag)
        .filter(RiskFlag.risk_level == "HIGH", RiskFlag.actioned_at.is_(None), RiskFlag.escalated_at.is_(None))
        .all()
    )

    fired = 0
    for flag in candidates:
        flagged_at = flag.created_at.replace(tzinfo=timezone.utc) if flag.created_at.tzinfo is None else flag.created_at
        if now - flagged_at < threshold:
            continue

        visit = db.get(Visit, flag.visit_id)
        patient = db.get(Patient, visit.patient_id) if visit else None
        worker = db.get(Worker, visit.worker_id) if visit else None

        message = (
            f"ESCALATION: {patient.name if patient else 'A patient'} was flagged HIGH risk "
            f"{round((now - flagged_at).total_seconds() / 3600, 1)}h ago by "
            f"{worker.name if worker else 'an ASHA worker'} with no recorded follow-up action. "
            f"Please review urgently."
        )
        send_whatsapp_message("bmo", message)
        flag.escalated_at = now
        log_action(db, None, "escalation_fired", flag.flag_id, "risk_flag", message)
        fired += 1

    if fired:
        db.commit()
    return fired
