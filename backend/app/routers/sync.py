from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, CurrentUser
from app.models.schemas import SyncBatchRequest, SyncBatchResponse
from app.models.db_models import SyncQueueEntry
from app.services.visit_pipeline import process_voice_visit
import json
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.post("/batch", response_model=SyncBatchResponse)
def sync_batch(payload: SyncBatchRequest, db: Session = Depends(get_db),
                user: CurrentUser = Depends(get_current_user)):
    synced = 0
    failed = 0
    errors: list[str] = []

    for record in payload.records:
        queue_entry = SyncQueueEntry(
            worker_id=payload.worker_id, record_type=record.record_type,
            record_json=json.dumps(record.record_json),
        )
        db.add(queue_entry)
        db.commit()
        db.refresh(queue_entry)

        try:
            if record.record_type == "visit":
                process_voice_visit(
                    db, worker_id=payload.worker_id,
                    patient_id=record.record_json["patient_id"],
                    language_code=record.record_json.get("language_code", "hi"),
                    transcript=record.record_json.get("transcript"),
                    audio_base64=record.record_json.get("audio_base64"),
                )
            queue_entry.status = "synced"
            queue_entry.synced_at = datetime.now(timezone.utc)
            synced += 1
        except Exception as e:
            queue_entry.status = "failed"
            queue_entry.retry_count += 1
            errors.append(f"{record.record_type}: {e}")
            failed += 1
        db.commit()

    return SyncBatchResponse(synced=synced, failed=failed, errors=errors)
