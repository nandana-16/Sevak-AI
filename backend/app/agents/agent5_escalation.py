"""Agent 5 — Escalation: computes/monitors the 48-hour unactioned-HIGH-risk window (FR-06)."""
from datetime import datetime, timedelta, timezone

from app.core.config import settings


def compute_escalation_deadline(risk_level: str, flagged_at: datetime | None = None) -> datetime | None:
    if risk_level != "HIGH":
        return None
    flagged_at = flagged_at or datetime.now(timezone.utc)
    return flagged_at + timedelta(hours=settings.escalation_threshold_hours)
