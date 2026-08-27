from datetime import datetime, timezone, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import require_roles, CurrentUser
from app.core.village_geo import village_coords
from app.models.db_models import Visit, Patient, Action, Worker, HmisReport
from app.models.schemas import HeatmapPoint, DashboardMetrics

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/heatmap", response_model=list[HeatmapPoint])
def heatmap(db: Session = Depends(get_db), user: CurrentUser = Depends(require_roles("anm", "bmo", "admin"))):
    rows = (
        db.query(Patient.village, Visit.risk_level, func.count(Visit.visit_id))
        .join(Visit, Visit.patient_id == Patient.patient_id)
        .filter(Visit.risk_level.isnot(None))
        .group_by(Patient.village, Visit.risk_level)
        .all()
    )
    points = []
    for village, risk_level, count in rows:
        if not village:
            continue
        lat, lng = village_coords(village)
        points.append(HeatmapPoint(lat=lat, lng=lng, village=village, risk_level=risk_level, patient_count=count))
    return points


@router.get("/metrics", response_model=DashboardMetrics)
def metrics(db: Session = Depends(get_db), user: CurrentUser = Depends(require_roles("anm", "bmo", "admin"))):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    visits_today = db.query(Visit).filter(Visit.created_at >= today_start).count()
    high_risk_cases = db.query(Visit).filter(Visit.risk_level == "HIGH", Visit.created_at >= today_start).count()
    pending_followups = (
        db.query(Action)
        .filter(Action.type == "followup", Action.status != "complete",
                Action.due_at.isnot(None), Action.due_at >= datetime.now(timezone.utc))
        .count()
    )

    total_workers = db.query(Worker).filter(Worker.role == "asha").count()
    now = datetime.now(timezone.utc)
    workers_with_report = (
        db.query(HmisReport.worker_id)
        .filter(HmisReport.month == now.month, HmisReport.year == now.year)
        .distinct()
        .count()
    )
    hmis_completion_rate = round((workers_with_report / total_workers) * 100, 1) if total_workers else 0.0

    return DashboardMetrics(
        visits_today=visits_today, high_risk_cases=high_risk_cases,
        pending_followups=pending_followups, hmis_completion_rate=hmis_completion_rate,
    )
