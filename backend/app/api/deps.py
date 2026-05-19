"""
FastAPI dependencies shared across routes:
- get_db: DB session
- get_current_user: decodes bearer token, returns User or 401
- get_current_active_user: also enforces is_active
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import decode_token
from app.models.user import User


# OAuth2PasswordBearer + auto_error=False lets us return a friendlier 401.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        print("[auth] no token presented")
        raise creds_exc

    payload = decode_token(token)
    print(f"[auth] decoded payload: {payload}")
    if not payload or payload.get("type") != "access":
        print(f"[auth] reject: payload={payload}")
        raise creds_exc

    user_id_raw = payload.get("sub")
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        print(f"[auth] sub not int: {user_id_raw!r}")
        raise creds_exc

    user = db.get(User, user_id)
    if not user:
        print(f"[auth] no user found for id {user_id}")
        raise creds_exc
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


def client_ip(request: Request) -> str:
    """Best-effort client IP — falls back to direct socket if no proxy headers."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""
