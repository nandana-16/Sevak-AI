"""Visit submission and retrieval.

Two entry points, because the phone has two situations:

* POST /api/visits          - the normal case. Text is already available,
                              either from on-device speech recognition or the
                              keyboard.
* POST /api/visits/audio    - a recording made where on-device recognition
                              could not run. The audio is transcribed here and
                              then goes through the identical pipeline.

Both are idempotent on `client_uuid`, which the phone generates before the
first attempt. Re-sending a queued visit is always safe.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.scoping import audit, get_patient_or_404
from app.core.security import get_current_worker
from app.models.db import InputMode, ScheduledVisit, ScheduleStatus, Visit, Worker
from app.models.schemas import VisitCreate, VisitDetail
from app.services import stt, visit_service

log = logging.getLogger("sevakai.api.visits")
router = APIRouter(prefix="/api/visits", tags=["visits"])

MAX_AUDIO_BYTES = 25 * 1024 * 1024
ALLOWED_AUDIO_SUFFIXES = {".m4a", ".mp4", ".aac", ".wav", ".ogg", ".opus", ".mp3", ".webm", ".flac"}


def _to_detail(db: Session, visit: Visit) -> VisitDetail:
    due = db.scalars(
        select(ScheduledVisit.due_date).where(
            ScheduledVisit.created_by_visit_id == visit.id,
            ScheduledVisit.status == ScheduleStatus.pending,
        )
    ).first()
    detail = VisitDetail.model_validate(visit)
    detail.next_visit_due = due
    detail.refer_to_facility = visit.risk_level.value == "red"
    detail.symptoms = visit.symptoms or []
    detail.danger_signs = visit.danger_signs or []
    detail.guideline_citations = visit.guideline_citations or []
    detail.recommended_actions = visit.recommended_actions or []
    detail.degraded_steps = visit.degraded_steps or []
    return detail


@router.post("", response_model=VisitDetail, status_code=201)
def submit_visit(
    payload: VisitCreate,
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
) -> VisitDetail:
    if not (payload.transcript or payload.typed_notes or payload.manual_fields):
        raise HTTPException(
            status_code=400,
            detail="Provide speech, typed notes, or at least one measurement",
        )

    existing = visit_service.find_existing(db, payload.client_uuid)
    if existing is not None:
        # An offline retry of something already accepted. Return what we have
        # rather than creating a duplicate record.
        return _to_detail(db, existing)

    patient = get_patient_or_404(db, worker, payload.patient_id)
    visit = visit_service.create_visit(
        db,
        patient=patient,
        worker=worker,
        client_uuid=payload.client_uuid,
        transcript=payload.transcript,
        typed_notes=payload.typed_notes,
        manual_fields=payload.manual_fields,
        input_mode=payload.input_mode,
        language=payload.language,
        visited_at=payload.visited_at,
    )

    try:
        visit_service.process(db, patient, visit)
    except Exception as exc:
        log.exception("Failed to process visit %s", visit.id)
        visit_service.mark_failed(db, visit, str(exc))

    audit(db, worker, "submit_visit", "visit", visit.id, f"risk={visit.risk_level.value}")
    db.commit()
    db.refresh(visit)
    return _to_detail(db, visit)


@router.post("/audio", response_model=VisitDetail, status_code=201)
async def submit_visit_audio(
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
    client_uuid: str = Form(...),
    patient_id: str = Form(...),
    language: str = Form("hi"),
    typed_notes: str | None = Form(None),
    manual_fields: str | None = Form(None),
    visited_at: datetime | None = Form(None),
    audio: UploadFile = File(...),
) -> VisitDetail:
    existing = visit_service.find_existing(db, client_uuid)
    if existing is not None:
        return _to_detail(db, existing)

    patient = get_patient_or_404(db, worker, patient_id)

    suffix = ("." + audio.filename.rsplit(".", 1)[-1].lower()) if "." in (audio.filename or "") else ""
    if suffix not in ALLOWED_AUDIO_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format '{suffix}'")

    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Audio file was empty")
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Recording is too large")

    filename = f"{uuid.uuid4().hex}{suffix}"
    (settings.audio_path / filename).write_bytes(data)

    fields: dict = {}
    if manual_fields:
        try:
            parsed = json.loads(manual_fields)
            if isinstance(parsed, dict):
                fields = parsed
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="manual_fields must be JSON")

    visit = visit_service.create_visit(
        db,
        patient=patient,
        worker=worker,
        client_uuid=client_uuid,
        transcript=None,
        typed_notes=typed_notes,
        manual_fields=fields,
        input_mode=InputMode.voice_offline,
        language=language,
        visited_at=visited_at,
        audio_filename=filename,
    )

    try:
        visit.transcript = stt.transcribe(settings.audio_path / filename, language)
        visit_service.process(db, patient, visit)
    except stt.TranscriptionError as exc:
        # The recording is kept, so it can be retried or played back by a
        # supervisor rather than silently lost.
        log.warning("Transcription failed for visit %s: %s", visit.id, exc)
        visit_service.mark_failed(db, visit, f"Could not transcribe the recording: {exc}")
    except Exception as exc:
        log.exception("Failed to process audio visit %s", visit.id)
        visit_service.mark_failed(db, visit, str(exc))

    audit(db, worker, "submit_visit_audio", "visit", visit.id)
    db.commit()
    db.refresh(visit)
    return _to_detail(db, visit)


@router.get("/{visit_id}", response_model=VisitDetail)
def get_visit(
    visit_id: str,
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
) -> VisitDetail:
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(status_code=404, detail="Visit not found")
    # Reuse the roster check rather than trusting the visit's own worker id.
    get_patient_or_404(db, worker, visit.patient_id)
    return _to_detail(db, visit)


@router.get("", response_model=list[VisitDetail])
def list_visits(
    patient_id: str,
    db: Session = Depends(get_db),
    worker: Worker = Depends(get_current_worker),
    limit: int = 20,
) -> list[VisitDetail]:
    get_patient_or_404(db, worker, patient_id)
    visits = db.scalars(
        select(Visit)
        .where(Visit.patient_id == patient_id)
        .order_by(Visit.visited_at.desc())
        .limit(min(limit, 100))
    ).all()
    return [_to_detail(db, v) for v in visits]
