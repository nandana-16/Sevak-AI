from sqlalchemy.orm import Session

from app.models.db_models import AuditLog


def log_action(db: Session, user_id: str | None, action_type: str, record_id: str | None,
                record_type: str | None, detail: str | None = None, ip_address: str | None = None):
    entry = AuditLog(
        user_id=user_id, action_type=action_type, record_id=record_id,
        record_type=record_type, detail=detail, ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
