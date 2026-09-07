"""Auth primitives.

Workers sign in with phone number + 4-digit PIN. A PIN is weak on its own, so
the app pairs it with device biometrics; the PIN exists because a shared
low-end handset in the field cannot rely on biometrics alone.

Tokens are deliberately long-lived (14 days by default): a worker may not see
a network for days, and an expired token stranding them mid-round is worse
than the marginal risk.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.db import Role, Worker

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()


def verify_pin(pin: str, pin_hash: str) -> bool:
    try:
        return bcrypt.checkpw(pin.encode(), pin_hash.encode())
    except ValueError:
        return False


def create_access_token(worker_id: str, role: Role) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": worker_id, "role": role.value, "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def hash_aadhaar(aadhaar: str) -> str:
    """One-way, salted. Used only to detect a duplicate registration."""
    digits = "".join(c for c in aadhaar if c.isdigit())
    return hmac.new(
        settings.aadhaar_hash_salt.encode(), digits.encode(), hashlib.sha256
    ).hexdigest()


def get_current_worker(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Worker:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sign in again",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_error
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        worker_id = payload.get("sub")
    except JWTError:
        raise credentials_error
    if not worker_id:
        raise credentials_error

    worker = db.get(Worker, worker_id)
    if worker is None or not worker.active:
        raise credentials_error
    return worker


def require_supervisor(worker: Worker = Depends(get_current_worker)) -> Worker:
    if worker.role not in (Role.anm, Role.admin):
        raise HTTPException(status_code=403, detail="Supervisor access required")
    return worker
