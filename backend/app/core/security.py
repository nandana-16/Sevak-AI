from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()


def verify_pin(pin: str, pin_hash: str) -> bool:
    return bcrypt.checkpw(pin.encode(), pin_hash.encode())


def create_access_token(subject: str, role: str, worker_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "role": role, "worker_id": worker_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class CurrentUser:
    def __init__(self, worker_id: str, role: str, phone: str):
        self.worker_id = worker_id
        self.role = role
        self.phone = phone


def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        worker_id: str = payload.get("worker_id")
        role: str = payload.get("role")
        phone: str = payload.get("sub")
        if worker_id is None:
            raise credentials_exception
        return CurrentUser(worker_id=worker_id, role=role, phone=phone)
    except JWTError:
        raise credentials_exception


def require_roles(*roles: str):
    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions for this role")
        return user

    return checker
