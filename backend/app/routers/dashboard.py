"""Supervisor dashboard.

Two audiences, one set of endpoints, separated by what `visible_worker_ids`
returns:

* **ANM** - a handful of ASHA workers she supervises directly. Her question is
  "who needs me today, and is anyone falling behind?"
* **BMO** - the whole block. His question is "which PHC areas are drifting, and
  is anything sitting unactioned?"

So the same shapes serve both, but the BMO's numbers aggregate over more
workers. Nothing here can reach outside the caller's scope: every query starts
from `visible_worker_ids`, the same function the worker app uses.

Deliberately *not* a separate reporting database. At this size the operational
tables answer these questions directly, and a second copy of the data is a
second thing to get out of sync.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.scoping import visible_worker_ids
from app.core.security import require_supervisor
from app.models.db import (
    Escalation,
    Patient,
    RiskLevel,
    Role,
    ScheduledVisit,
    ScheduleStatus,
    Visit,
    VisitStatus,
    Worker,
)
from app.models.schemas import (
    BlockAreaRow,
    DashboardSummary,
    WorkerPerformanceRow,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _scope(db: Session, supervisor: Worker) -> list[str] | None:
    return visible_worker_ids(db, supervisor)


def _field_workers(db: Session, supervisor: Worker) -> list[Worker]:
    """The ASHAs whose work is being supervised. A BMO's block also contains
    ANMs and the BMO; they carry no roster of their own, so counting them as
    field workers would flatter the averages."""
    allowed = _scope(db, supervisor)
    stmt = select(Worker).where(Worker.active.is_(True), Worker.role == Role.asha)
    if allowed is not None:
        stmt = stmt.where(Worker.id.in_(allowed))
    return list(db.scalars(stmt.order_by(Worker.village, Worker.name)).all())


@router.get("/summary", response_model=DashboardSummary)
def summary(
    db: Session = Depends(get_db),
    supervisor: Worker = Depends(require_supervisor),
    days: int = Query(7, ge=1, le=90, description="Window for the activity counts"),
) -> DashboardSummary:
    allowed = _scope(db, supervisor)
    today = date.today()
    since = datetime.now(timezone.utc) - timedelta(days=days)

    patients = select(Patient).where(Patient.active.is_(True))
    visits = select(Visit)
    scheduled = select(ScheduledVisit).where(
        ScheduledVisit.status == ScheduleStatus.pending
    )
    escalations = select(Escalation).where(Escalation.resolved.is_(False))
    if allowed is not None:
        patients = patients.where(Patient.assigned_worker_id.in_(allowed))
        visits = visits.where(Visit.worker_id.in_(allowed))
        scheduled = scheduled.where(ScheduledVisit.worker_id.in_(allowed))
        escalations = escalations.where(Escalation.worker_id.in_(allowed))

    rows = list(db.scalars(patients).all())
    by_risk = Counter(p.current_risk.value for p in rows)

    recent = list(db.scalars(visits.where(Visit.visited_at >= since)).all())
    open_escalations = list(db.scalars(escalations).all())

    # An escalation nobody has acknowledged after two days is the number a
    # supervisor most needs surfaced - it means a red-flagged patient may have
    # been left. Counted separately rather than buried in the total.
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=2)
    stale = sum(1 for e in open_escalations if _aware(e.raised_at) < stale_cutoff)

    due = list(db.scalars(scheduled).all())

    return DashboardSummary(
        role=supervisor.role.value,
        scope_label=_scope_label(supervisor),
        window_days=days,
        total_patients=len(rows),
        red=by_risk.get("red", 0),
        yellow=by_risk.get("yellow", 0),
        green=by_risk.get("green", 0),
        unknown=by_risk.get("unknown", 0),
        field_workers=len(_field_workers(db, supervisor)),
        visits_in_window=len(recent),
        visits_today=sum(1 for v in recent if _aware(v.visited_at).date() == today),
        failed_visits=sum(1 for v in recent if v.status == VisitStatus.failed),
        # Visits the pipeline could not fully analyse. A supervisor should know
        # how much of what they are reading was produced by rules alone.
        degraded_visits=sum(1 for v in recent if v.degraded_steps),
        open_escalations=len(open_escalations),
        stale_escalations=stale,
        overdue_visits=sum(1 for s in due if s.due_date < today),
        due_today=sum(1 for s in due if s.due_date == today),
    )


@router.get("/workers", response_model=list[WorkerPerformanceRow])
def workers(
    db: Session = Depends(get_db),
    supervisor: Worker = Depends(require_supervisor),
    days: int = Query(7, ge=1, le=90),
) -> list[WorkerPerformanceRow]:
    """Per-worker view. Ordered by what needs attention, not alphabetically."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    today = date.today()
    rows: list[WorkerPerformanceRow] = []

    for worker in _field_workers(db, supervisor):
        patients = list(
            db.scalars(
                select(Patient).where(
                    Patient.assigned_worker_id == worker.id,
                    Patient.active.is_(True),
                )
            ).all()
        )
        visits = list(
            db.scalars(
                select(Visit).where(
                    Visit.worker_id == worker.id, Visit.visited_at >= since
                )
            ).all()
        )
        overdue = db.scalar(
            select(func.count())
            .select_from(ScheduledVisit)
            .where(
                ScheduledVisit.worker_id == worker.id,
                ScheduledVisit.status == ScheduleStatus.pending,
                ScheduledVisit.due_date < today,
            )
        ) or 0
        open_escalations = db.scalar(
            select(func.count())
            .select_from(Escalation)
            .where(Escalation.worker_id == worker.id, Escalation.resolved.is_(False))
        ) or 0

        # Deliberately NOT max() over `visits`: that list is limited to the
        # activity window, so a worker whose last visit was three weeks ago
        # would read as "no visits recorded" - indistinguishable from someone
        # who has never worked at all. A supervisor acts very differently on
        # those two, so ask the database for the real last visit.
        last_visit_raw = db.scalar(
            select(func.max(Visit.visited_at)).where(Visit.worker_id == worker.id)
        )
        last_visit = _aware(last_visit_raw) if last_visit_raw else None
        rows.append(
            WorkerPerformanceRow(
                worker_id=worker.id,
                name=worker.name,
                phone=worker.phone,
                village=worker.village,
                patients=len(patients),
                red_patients=sum(1 for p in patients if p.current_risk == RiskLevel.red),
                yellow_patients=sum(
                    1 for p in patients if p.current_risk == RiskLevel.yellow
                ),
                visits_in_window=len(visits),
                overdue_visits=int(overdue),
                open_escalations=int(open_escalations),
                last_visit_at=last_visit,
                # Days since this worker last recorded anything. The single
                # most useful signal that somebody has stopped working, or that
                # their phone has stopped syncing.
                days_since_last_visit=(
                    (datetime.now(timezone.utc) - last_visit).days if last_visit else None
                ),
            )
        )

    rows.sort(
        key=lambda r: (
            -r.open_escalations,
            -r.overdue_visits,
            -r.red_patients,
            r.name,
        )
    )
    return rows


@router.get("/areas", response_model=list[BlockAreaRow])
def areas(
    db: Session = Depends(get_db),
    supervisor: Worker = Depends(require_supervisor),
) -> list[BlockAreaRow]:
    """Village-level roll-up. This is the BMO's view: an ANM sees her handful
    of workers, a BMO needs to see which areas are drifting."""
    allowed = _scope(db, supervisor)
    today = date.today()

    stmt = select(Patient).where(Patient.active.is_(True))
    if allowed is not None:
        stmt = stmt.where(Patient.assigned_worker_id.in_(allowed))
    patients = list(db.scalars(stmt).all())

    overdue_stmt = select(ScheduledVisit).where(
        ScheduledVisit.status == ScheduleStatus.pending,
        ScheduledVisit.due_date < today,
    )
    if allowed is not None:
        overdue_stmt = overdue_stmt.where(ScheduledVisit.worker_id.in_(allowed))
    overdue_by_patient = {s.patient_id for s in db.scalars(overdue_stmt).all()}

    grouped: dict[str, list[Patient]] = {}
    for patient in patients:
        grouped.setdefault(patient.village or "Unassigned", []).append(patient)

    rows = [
        BlockAreaRow(
            village=village,
            patients=len(group),
            red=sum(1 for p in group if p.current_risk == RiskLevel.red),
            yellow=sum(1 for p in group if p.current_risk == RiskLevel.yellow),
            overdue_visits=sum(1 for p in group if p.id in overdue_by_patient),
            pregnant=sum(1 for p in group if p.category.value == "pregnant"),
            infants=sum(1 for p in group if p.category.value == "infant"),
        )
        for village, group in grouped.items()
    ]
    rows.sort(key=lambda r: (-r.red, -r.overdue_visits, r.village))
    return rows


def _aware(value: datetime) -> datetime:
    """SQLite hands back naive datetimes; comparisons here are all in UTC."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _scope_label(supervisor: Worker) -> str:
    if supervisor.role == Role.bmo:
        return f"{supervisor.block} block"
    if supervisor.role == Role.anm:
        return supervisor.village or "Your workers"
    return "All areas"
