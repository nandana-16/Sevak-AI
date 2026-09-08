"""Patient roster and profiles.

Every query here goes through app.core.scoping, so a worker can only ever
reach the patients assigned to them.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.agents import context as patient_context
from app.core import aadhaar as aadhaar_lib
from app.core.database import get_db
from app.core.immunisation import SCHEDULE as IMMUNISATION_SCHEDULE
from app.core.scoping import audit, get_patient_or_404, patient_query
from app.core.security import get_current_worker, hash_aadhaar
from app.models.db import (
    InfantRecord,
    MedicalCondition,
    Patient,
    PatientCategory,
    PregnancyRecord,
    RiskLevel,
    ScheduledVisit,
    ScheduleStatus,
    Vaccination,
    Worker,
)
from app.models.schemas import (
    AadhaarCheckRequest,
    AadhaarCheckResponse,
    ConditionOut,
    InfantOut,
    PatientCreate,
    PatientDetail,
    PatientSummary,
    PregnancyOut,
    VaccinationOut,
    VisitSummary,
)
from app.services import visit_service

router = APIRouter(prefix="/api/patients", tags=["patients"])

RISK_SORT = {RiskLevel.red: 0, RiskLevel.yellow: 1, RiskLevel.unknown: 2, RiskLevel.green: 3}


def _summary(db: Session, patient: Patient) -> PatientSummary:
    return PatientSummary(
        id=patient.id,
        name=patient.name,
        age_label=patient_context.age_label(patient),
        gender=patient.gender,
        category=patient.category,
        village=patient.village,
        current_risk=patient.current_risk,
        last_visit_at=patient.last_visit_at,
        last_visit_summary=patient.last_visit_summary,
        next_visit_due=visit_service.next_due_date(db, patient.id),
        aadhaar_verified=patient.aadhaar_verified,
    )


@router.get("", response_model=list[PatientSummary])
def list_patients(
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
    search: str | None = Query(None, description="Name or village"),
    village: str | None = None,
    category: PatientCategory | None = None,
    risk: RiskLevel | None = None,
    due_only: bool = Query(False, description="Only patients with a visit due"),
    limit: int = Query(200, le=500),
) -> list[PatientSummary]:
    stmt = patient_query(db, worker)

    if search:
        needle = f"%{search.strip()}%"
        stmt = stmt.where(or_(Patient.name.ilike(needle), Patient.village.ilike(needle)))
    if village:
        stmt = stmt.where(Patient.village == village)
    if category:
        stmt = stmt.where(Patient.category == category)
    if risk:
        stmt = stmt.where(Patient.current_risk == risk)
    if due_only:
        due = select(ScheduledVisit.patient_id).where(
            ScheduledVisit.status == ScheduleStatus.pending,
            ScheduledVisit.due_date <= date.today(),
        )
        stmt = stmt.where(Patient.id.in_(due))

    patients = db.scalars(stmt.limit(limit)).all()
    summaries = [_summary(db, p) for p in patients]
    # Riskiest first, then most overdue: the order a worker plans their day in.
    summaries.sort(
        key=lambda s: (
            RISK_SORT.get(s.current_risk, 2),
            s.next_visit_due or date.max,
            s.name,
        )
    )
    return summaries


@router.get("/villages", response_model=list[str])
def list_villages(
    db: Session = Depends(get_db), worker: Worker = Depends(get_current_worker)
) -> list[str]:
    """Populates the region filter with only the villages this worker covers."""
    stmt = patient_query(db, worker).with_only_columns(Patient.village).distinct()
    return sorted({v for v in db.scalars(stmt).all() if v})


@router.post("/aadhaar/check", response_model=AadhaarCheckResponse)
def check_aadhaar(
    payload: AadhaarCheckRequest,
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
) -> AadhaarCheckResponse:
    """Validate a number before registration, without storing anything."""
    result = aadhaar_lib.verify(payload.aadhaar)
    already = False
    if result.valid:
        already = db.scalars(
            select(Patient.id).where(Patient.aadhaar_hash == hash_aadhaar(payload.aadhaar))
        ).first() is not None
    return AadhaarCheckResponse(
        valid=result.valid,
        reason="This Aadhaar is already registered" if already else result.reason,
        last4=result.last4,
        already_registered=already,
        method=result.method,
    )


@router.post("", response_model=PatientDetail, status_code=201)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
) -> PatientDetail:
    aadhaar_hash = None
    last4 = None
    verified = False

    if payload.aadhaar:
        if not payload.aadhaar_consent_given:
            raise HTTPException(
                status_code=400,
                detail="Record the patient's consent before linking an Aadhaar number",
            )
        result = aadhaar_lib.verify(payload.aadhaar)
        if not result.valid:
            raise HTTPException(status_code=400, detail=result.reason)

        aadhaar_hash = hash_aadhaar(payload.aadhaar)
        if db.scalars(select(Patient.id).where(Patient.aadhaar_hash == aadhaar_hash)).first():
            raise HTTPException(
                status_code=409, detail="A patient with this Aadhaar is already registered"
            )
        last4 = result.last4
        verified = True

    patient = Patient(
        name=payload.name.strip(),
        dob=payload.dob,
        age_years_approx=payload.age_years_approx,
        gender=payload.gender,
        blood_group=payload.blood_group,
        phone=payload.phone,
        category=payload.category,
        village=payload.village or worker.village,
        block=worker.block,
        district=worker.district,
        address=payload.address,
        guardian_name=payload.guardian_name or payload.mother_name,
        household_id=payload.household_id,
        aadhaar_hash=aadhaar_hash,
        aadhaar_last4=last4,
        aadhaar_verified=verified,
        aadhaar_verified_at=datetime.now(timezone.utc) if verified else None,
        aadhaar_consent_given=payload.aadhaar_consent_given,
        aadhaar_verification_method="offline_verhoeff" if verified else None,
        assigned_worker_id=worker.id,
    )
    db.add(patient)
    db.flush()

    for name in payload.conditions:
        if name.strip():
            db.add(MedicalCondition(patient_id=patient.id, name=name.strip(), ongoing=True))

    if payload.category == PatientCategory.pregnant:
        from datetime import timedelta

        db.add(
            PregnancyRecord(
                patient_id=patient.id,
                lmp=payload.lmp,
                edd=payload.lmp + timedelta(days=280) if payload.lmp else None,
                gravida=payload.gravida,
                para=payload.para,
                high_risk_factors=[],
            )
        )

    if payload.category == PatientCategory.infant:
        db.add(
            InfantRecord(
                patient_id=patient.id,
                birth_weight_kg=payload.birth_weight_kg,
                gestation_weeks=payload.gestation_weeks,
            )
        )
        if payload.dob:
            _create_immunisation_schedule(db, patient.id, payload.dob)

    audit(db, worker, "register_patient", "patient", patient.id)
    db.commit()
    db.refresh(patient)
    return _detail(db, patient)


def _create_immunisation_schedule(db: Session, patient_id: str, dob: date) -> None:
    """Lay out the National Immunization Schedule so due dates exist from day
    one rather than being remembered by the worker."""
    from datetime import timedelta

    for vaccine, dose, weeks in IMMUNISATION_SCHEDULE:
        db.add(
            Vaccination(
                patient_id=patient_id,
                vaccine=vaccine,
                dose_label=dose,
                due_date=dob + timedelta(weeks=weeks),
                given=False,
            )
        )


def _detail(db: Session, patient: Patient) -> PatientDetail:
    base = _summary(db, patient)
    today = date.today()

    pregnancy = None
    if patient.pregnancy:
        pregnancy = PregnancyOut.model_validate(patient.pregnancy)
        pregnancy.gestation_weeks = patient_context.gestation_weeks(patient)
        pregnancy.high_risk_factors = patient.pregnancy.high_risk_factors or []

    vaccinations = []
    for row in sorted(patient.vaccinations, key=lambda v: (v.due_date or date.max)):
        item = VaccinationOut.model_validate(row)
        item.overdue = bool(not row.given and row.due_date and row.due_date < today)
        vaccinations.append(item)

    return PatientDetail(
        **base.model_dump(),
        dob=patient.dob,
        blood_group=patient.blood_group,
        phone=patient.phone,
        address=patient.address,
        guardian_name=patient.guardian_name,
        household_id=patient.household_id,
        block=patient.block,
        district=patient.district,
        aadhaar_masked=aadhaar_lib.mask(patient.aadhaar_last4),
        conditions=[ConditionOut.model_validate(c) for c in patient.conditions],
        vaccinations=vaccinations,
        pregnancy=pregnancy,
        infant=InfantOut.model_validate(patient.infant_record) if patient.infant_record else None,
        recent_visits=[VisitSummary.model_validate(v) for v in patient.visits[:10]],
    )


@router.get("/{patient_id}", response_model=PatientDetail)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
) -> PatientDetail:
    patient = get_patient_or_404(db, worker, patient_id)
    audit(db, worker, "view_patient", "patient", patient.id)
    db.commit()
    return _detail(db, patient)


@router.post("/{patient_id}/vaccinations/{vaccination_id}/given", response_model=VaccinationOut)
def mark_vaccination_given(
    patient_id: str,
    vaccination_id: str,
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
    batch_no: str | None = None,
) -> VaccinationOut:
    patient = get_patient_or_404(db, worker, patient_id)
    row = db.scalars(
        select(Vaccination).where(
            Vaccination.id == vaccination_id, Vaccination.patient_id == patient.id
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Vaccination record not found")

    row.given = True
    row.given_date = date.today()
    row.batch_no = batch_no
    audit(db, worker, "vaccination_given", "vaccination", row.id, row.vaccine)
    db.commit()

    item = VaccinationOut.model_validate(row)
    item.overdue = False
    return item


@router.get("/{patient_id}/stats", response_model=dict)
def patient_stats(
    patient_id: str,
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
) -> dict:
    patient = get_patient_or_404(db, worker, patient_id)
    return {
        "total_visits": len(patient.visits),
        "vaccinations_due": sum(
            1 for v in patient.vaccinations
            if not v.given and v.due_date and v.due_date <= date.today()
        ),
        "ongoing_conditions": sum(1 for c in patient.conditions if c.ongoing),
    }
