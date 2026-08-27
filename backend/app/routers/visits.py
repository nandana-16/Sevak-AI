from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, CurrentUser
from app.models.db_models import Patient, Visit, RiskFlag, Action
from app.models.schemas import VoiceVisitRequest, VoiceVisitResponse, PatientOut
from app.services.visit_pipeline import process_voice_visit
from app.services.audit import log_action

router = APIRouter(prefix="/api/v1", tags=["visits"])


@router.post("/visits/voice", response_model=VoiceVisitResponse)
def submit_voice_visit(
    payload: VoiceVisitRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    patient = db.get(Patient, payload.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    try:
        result = process_voice_visit(
            db, worker_id=payload.worker_id, patient_id=payload.patient_id,
            language_code=payload.language_code, transcript=payload.transcript,
            audio_base64=payload.audio_base64,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return VoiceVisitResponse(**result)


@router.get("/patients/{worker_id}", response_model=list[PatientOut])
def get_patients(worker_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    if user.role == "asha" and user.worker_id != worker_id:
        raise HTTPException(status_code=403, detail="Cannot view another worker's patients")

    patients = db.query(Patient).filter(Patient.worker_id == worker_id).all()
    out = []
    for p in patients:
        last_visit = (
            db.query(Visit)
            .filter(Visit.patient_id == p.patient_id)
            .order_by(Visit.created_at.desc())
            .first()
        )
        out.append(PatientOut(
            patient_id=p.patient_id, name=p.name, age=p.age, village=p.village,
            category=p.category,
            last_risk_level=last_visit.risk_level if last_visit else None,
            last_visit_at=last_visit.created_at if last_visit else None,
        ))
    return out


@router.get("/visits/{visit_id}")
def get_visit(visit_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    visit = db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    flag = db.query(RiskFlag).filter(RiskFlag.visit_id == visit_id).first()
    actions = db.query(Action).filter(Action.visit_id == visit_id).all()
    import json
    return {
        "visit_id": visit.visit_id,
        "transcript": visit.transcript,
        "structured_json": json.loads(visit.structured_json) if visit.structured_json else None,
        "risk_level": visit.risk_level,
        "risk_drivers": json.loads(flag.drivers_json) if flag else [],
        "actions": [{"type": a.type, "content": a.content, "status": a.status} for a in actions],
        "created_at": visit.created_at,
    }


@router.post("/visits/{visit_id}/override")
def override_risk(visit_id: str, reason: str, new_level: str, db: Session = Depends(get_db),
                   user: CurrentUser = Depends(get_current_user)):
    if new_level not in ("HIGH", "MEDIUM", "LOW"):
        raise HTTPException(status_code=400, detail="new_level must be HIGH, MEDIUM, or LOW")
    flag = db.query(RiskFlag).filter(RiskFlag.visit_id == visit_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Risk flag not found for this visit")

    flag.overridden_by = user.worker_id
    flag.override_reason = reason
    visit = db.get(Visit, visit_id)
    original_level = flag.risk_level
    visit.risk_level = new_level
    db.commit()

    log_action(db, user.worker_id, "risk_override", visit_id, "visit",
               f"{original_level} -> {new_level}: {reason}")
    return {"status": "overridden", "original_level": original_level, "new_level": new_level}
