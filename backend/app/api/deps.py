"""
FastAPI dependencies shared across routes.

Authentication supports two credential types in `Authorization: Bearer <X>`:
  1. JWT access tokens (issued by /auth/login)
  2. Raw API keys (issued by /api-keys, owner-scoped)

API keys are tried only if the token doesn't decode as a valid JWT, so JWT
remains the fast path. On successful API-key match we bump `last_used_at`.
"""

from datetime import datetime
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.core.security import decode_token, verify_api_key
from app.models.user import User
from app.models.apikey import APIKey


# auto_error=False so we can fall through to API-key check and return a
# unified 401 instead of FastAPI's terse default.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def _user_from_jwt(token: str, db: Session) -> Optional[User]:
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return None
    return db.get(User, user_id)


def _user_from_api_key(token: str, db: Session) -> Optional[User]:
    """Match `token` against every non-revoked API key. Slow but simple — fine
    for an internal-scale app. If this is ever hot, add a prefix index column.
    """
    # Cheap pre-filter: only check keys whose stored prefix matches the token's start.
    if len(token) < 8:
        return None
    prefix = token[:8]
    candidates = db.scalars(
        select(APIKey).where(APIKey.prefix == prefix, APIKey.revoked.is_(False))
    ).all()
    for k in candidates:
        if verify_api_key(token, k.hashed_key):
            k.last_used_at = datetime.utcnow()
            db.commit()
            return db.get(User, k.user_id)
    return None


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolves the calling identity. Accepts JWT first, then API key fallback."""
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise creds_exc

    user = _user_from_jwt(token, db) or _user_from_api_key(token, db)
    if not user:
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
