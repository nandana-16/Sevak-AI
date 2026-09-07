from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.scoping import audit
from app.core.security import create_access_token, get_current_worker, verify_pin
from app.models.db import Worker
from app.models.schemas import LoginRequest, LoginResponse, WorkerOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    phone = "".join(c for c in payload.phone if c.isdigit())[-10:]
    worker = db.scalars(select(Worker).where(Worker.phone == phone)).first()

    # One message for both cases, so the endpoint cannot be used to find out
    # which phone numbers belong to registered workers.
    if worker is None or not verify_pin(payload.pin, worker.pin_hash) or not worker.active:
        raise HTTPException(status_code=401, detail="Incorrect phone number or PIN")

    audit(db, worker, "login", "worker", worker.id)
    db.commit()

    return LoginResponse(
        access_token=create_access_token(worker.id, worker.role),
        worker=WorkerOut.model_validate(worker),
    )


@router.get("/me", response_model=WorkerOut)
def me(worker: Worker = Depends(get_current_worker)) -> WorkerOut:
    return WorkerOut.model_validate(worker)
