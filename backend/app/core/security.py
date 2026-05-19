"""
Security primitives: password hashing + JWT issuance / decoding.

Tokens carry: sub (user id), role, type (access|refresh), iat, exp, jti (unique id).
Refresh tokens are additionally stored in the DB so that logout actually revokes.
"""

import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings
from app.models.user import UserRole


# bcrypt for password hashes. 12 rounds is a sensible default for this decade.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


# ── Password hashing ────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd_context.verify(plain, hashed)
    except Exception:
        # Malformed hash etc. — never crash auth on bad input.
        return False


# ── JWT helpers ─────────────────────────────────────────────────────────────
def _utcnow() -> datetime:
    """Always returns a tz-aware UTC datetime."""
    return datetime.now(timezone.utc)


def _create_token(*, subject: str, role: UserRole, token_type: str, expires_delta: timedelta) -> Tuple[str, datetime, str]:
    """Return (encoded_token, expires_at, jti).

    `iat` and `exp` are real Unix timestamps (seconds since the UTC epoch).
    Using `time.time()` directly avoids the naive-datetime/.timestamp() trap
    where a non-UTC system clock would produce a timestamp that's already
    expired.
    """
    issued_at = int(time.time())
    exp_at = issued_at + int(expires_delta.total_seconds())
    jti = secrets.token_urlsafe(16)
    payload = {
        "sub": str(subject),
        "role": role.value,
        "type": token_type,
        "iat": issued_at,
        "exp": exp_at,
        "jti": jti,
    }
    encoded = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    # Return a NAIVE UTC datetime — our SQLAlchemy DateTime columns are naive,
    # and `datetime.utcfromtimestamp` consistently treats the epoch as UTC.
    expires_dt = datetime.utcfromtimestamp(exp_at)
    return encoded, expires_dt, jti


def create_access_token(*, user_id: int, role: UserRole) -> Tuple[str, int]:
    """Return (token, expires_in_seconds)."""
    delta = timedelta(minutes=settings.access_token_expire_minutes)
    token, _exp, _jti = _create_token(
        subject=str(user_id), role=role, token_type="access", expires_delta=delta
    )
    return token, int(delta.total_seconds())


def create_refresh_token(*, user_id: int, role: UserRole) -> Tuple[str, datetime]:
    """Return (token, expires_at) — caller must persist the row for revocation."""
    delta = timedelta(days=settings.refresh_token_expire_days)
    token, exp, _jti = _create_token(
        subject=str(user_id), role=role, token_type="refresh", expires_delta=delta
    )
    return token, exp


def decode_token(token: str) -> Optional[dict]:
    """Returns decoded payload or None if invalid / expired."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


# ── API-key helpers (developer role) ────────────────────────────────────────
def generate_api_key() -> Tuple[str, str, str]:
    """Returns (raw_key, prefix, hashed_key). Raw is returned ONCE to the user."""
    raw = secrets.token_urlsafe(32)
    prefix = raw[:8]
    hashed = _pwd_context.hash(raw)
    return raw, prefix, hashed


def verify_api_key(raw: str, hashed: str) -> bool:
    try:
        return _pwd_context.verify(raw, hashed)
    except Exception:
        return False
