"""
Two-factor authentication endpoints.

Flow:
  1. POST /2fa/enroll    — generates a secret, returns it + QR. NOT yet enabled.
  2. POST /2fa/verify    — user submits the first valid code; we set enabled=True
                           and issue backup codes (returned once).
  3. POST /2fa/disable   — user submits a current code to disable 2FA.
  4. GET  /2fa/status    — quick check for UI.

When 2FA is enabled, /auth/login requires a `code` field (TOTP or backup).
That logic lives in routes/auth.py.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, get_current_active_user, client_ip
from app.core.audit import log_action
from app.core import totp
from app.models.user import User
from app.models.two_factor import TwoFactor
from app.schemas.two_factor import (
    TwoFactorStatus, TwoFactorEnrollResponse,
    TwoFactorVerifyRequest, TwoFactorVerifyResponse, TwoFactorDisableRequest,
)


router = APIRouter()


@router.get("/status", response_model=TwoFactorStatus)
def status_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = db.scalar(select(TwoFactor).where(TwoFactor.user_id == current_user.id))
    return TwoFactorStatus(enabled=bool(row and row.enabled))


@router.post("/enroll", response_model=TwoFactorEnrollResponse)
def enroll(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Begin enrollment. Returns secret + QR. Caller scans then POSTs /verify."""
    existing = db.scalar(select(TwoFactor).where(TwoFactor.user_id == current_user.id))
    if existing and existing.enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA already enabled")

    secret = totp.new_secret()
    uri = totp.otpauth_uri(
        secret=secret, account_email=current_user.email, issuer="EnterpriseCore"
    )
    qr_svg = totp.qr_svg_for_uri(uri)

    if existing:
        existing.secret = secret
        existing.backup_codes_hashed = "[]"
    else:
        db.add(TwoFactor(user_id=current_user.id, secret=secret, enabled=False))
    log_action(
        db, user_id=current_user.id, action="2fa.enroll_begin",
        ip_address=client_ip(request),
    )
    db.commit()

    return TwoFactorEnrollResponse(secret=secret, otpauth_uri=uri, qr_svg=qr_svg)


@router.post("/verify", response_model=TwoFactorVerifyResponse)
def verify(
    body: TwoFactorVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Confirm enrollment by submitting a fresh code. Returns backup codes ONCE."""
    row = db.scalar(select(TwoFactor).where(TwoFactor.user_id == current_user.id))
    if not row:
        raise HTTPException(status_code=400, detail="No 2FA enrollment in progress")
    if row.enabled:
        raise HTTPException(status_code=400, detail="2FA already enabled")
    if not totp.verify_totp(row.secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid code")

    plain_codes, hashed_codes = totp.generate_backup_codes()
    row.enabled = True
    row.enabled_at = datetime.utcnow()
    row.backup_codes_hashed = totp.hashes_to_json(hashed_codes)
    row.last_used_at = datetime.utcnow()

    log_action(
        db, user_id=current_user.id, action="2fa.enabled",
        ip_address=client_ip(request),
    )
    db.commit()
    return TwoFactorVerifyResponse(enabled=True, backup_codes=plain_codes)


@router.post("/disable", status_code=status.HTTP_204_NO_CONTENT)
def disable(
    body: TwoFactorDisableRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Require a current code to disable, so a stolen session alone can't turn it off."""
    row = db.scalar(select(TwoFactor).where(TwoFactor.user_id == current_user.id))
    if not row or not row.enabled:
        raise HTTPException(status_code=400, detail="2FA not enabled")
    if not totp.verify_totp(row.secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid code")
    db.delete(row)
    log_action(
        db, user_id=current_user.id, action="2fa.disabled",
        ip_address=client_ip(request),
    )
    db.commit()
    return None
