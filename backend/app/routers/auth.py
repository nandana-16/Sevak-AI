from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_pin, create_access_token
from app.models.db_models import Worker
from app.models.schemas import LoginRequest, LoginResponse
from app.services.audit import log_action

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    worker = db.query(Worker).filter(Worker.phone == payload.phone).first()
    if not worker or not verify_pin(payload.pin, worker.pin_hash):
        raise HTTPException(status_code=401, detail="Invalid phone or PIN")

    token = create_access_token(subject=worker.phone, role=worker.role, worker_id=worker.worker_id)
    log_action(db, worker.worker_id, "login", worker.worker_id, "worker")
    return LoginResponse(access_token=token, role=worker.role, worker_id=worker.worker_id, name=worker.name)
