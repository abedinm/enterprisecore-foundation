"""
Auth endpoints:
- POST /auth/register   — self-service signup (always EMPLOYEE role)
- POST /auth/login      — issue access + refresh
- POST /auth/refresh    — rotate access token; refresh stays valid until expiry
- POST /auth/logout     — revoke a specific refresh token
- POST /auth/logout-all — revoke every refresh token for the current user
- GET  /auth/me         — current user record (also a quick token sanity check)
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, get_current_user, client_ip
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.core.audit import log_action
from app.models.user import User, UserRole
from app.models.session import RefreshToken
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPair, TokenRefreshRequest
from app.schemas.user import UserOut


router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """Create a new user with role EMPLOYEE. Email must be unique."""
    existing = db.scalar(select(User).where(User.email == req.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=req.email,
        full_name=req.full_name,
        hashed_password=hash_password(req.password),
        role=UserRole.EMPLOYEE,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.flush()  # assign user.id

    log_action(
        db,
        user_id=user.id,
        action="user.register",
        target_type="user",
        target_id=user.id,
        detail=f"Self-registered as {user.email}",
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Email + password → access + refresh token pair."""
    user = db.scalar(select(User).where(User.email == req.email))
    if not user or not verify_password(req.password, user.hashed_password):
        # Same error to avoid user-enumeration leakage.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    access, expires_in = create_access_token(user_id=user.id, role=user.role)
    refresh, refresh_exp = create_refresh_token(user_id=user.id, role=user.role)

    db.add(RefreshToken(
        user_id=user.id,
        token=refresh,
        user_agent=request.headers.get("user-agent", "")[:500],
        ip_address=client_ip(request),
        expires_at=refresh_exp,
    ))

    user.last_login_at = datetime.utcnow()
    log_action(db, user_id=user.id, action="auth.login", target_type="user", target_id=user.id, ip_address=client_ip(request))
    db.commit()

    return TokenPair(access_token=access, refresh_token=refresh, expires_in=expires_in)


@router.post("/refresh", response_model=TokenPair)
def refresh_tokens(req: TokenRefreshRequest, request: Request, db: Session = Depends(get_db)):
    """Trade a valid, non-revoked, non-expired refresh token for a fresh access token.

    The original refresh stays valid (sliding sessions); call /logout to revoke it.
    """
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    row = db.scalar(select(RefreshToken).where(RefreshToken.token == req.refresh_token))
    if not row or row.revoked or row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or revoked")

    user = db.get(User, row.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer active")

    access, expires_in = create_access_token(user_id=user.id, role=user.role)
    return TokenPair(access_token=access, refresh_token=req.refresh_token, expires_in=expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(req: TokenRefreshRequest, request: Request, db: Session = Depends(get_db)):
    """Revoke ONE refresh token (this session). Access token expires naturally."""
    row = db.scalar(select(RefreshToken).where(RefreshToken.token == req.refresh_token))
    if row and not row.revoked:
        row.revoked = True
        log_action(db, user_id=row.user_id, action="auth.logout", ip_address=client_ip(request))
        db.commit()
    return None


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Revoke every refresh token for the current user (all devices)."""
    for r in current_user.refresh_tokens:
        r.revoked = True
    log_action(db, user_id=current_user.id, action="auth.logout_all", ip_address=client_ip(request))
    db.commit()
    return None


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """Return the current user's profile (handy for client-side hydration)."""
    return current_user
