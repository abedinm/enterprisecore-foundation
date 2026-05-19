"""
Password reset + email verification.

In a production deployment with SMTP, the `dev_token` field would be omitted
and the token would only be sent via email. Here (no SMTP), the request
endpoint returns the token directly to make the flow testable.
"""

import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, client_ip
from app.core.security import hash_password
from app.core.audit import log_action
from app.core.notifications import notify
from app.core.rate_limit import limiter
from app.models.user import User
from app.models.password_reset import OneTimeToken, OneTimeTokenType
from app.models.notification import NotificationType
from app.schemas.auth_flows import (
    PasswordResetRequest, PasswordResetConfirm,
    EmailVerifyRequest, EmailVerifyConfirm,
    TokenIssuedResponse,
)


router = APIRouter()


# ── Password reset ──────────────────────────────────────────────────────────
@router.post("/password-reset/request", response_model=TokenIssuedResponse)
@limiter.limit("3/minute")
def request_password_reset(
    body: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Always returns 200 with `sent=true` — even if the email isn't registered —
    to avoid disclosing which addresses exist in the system.
    """
    user = db.scalar(select(User).where(User.email == body.email))
    dev_token: str | None = None

    if user:
        # Invalidate prior unused reset tokens for this user.
        prior = db.scalars(
            select(OneTimeToken).where(
                (OneTimeToken.user_id == user.id)
                & (OneTimeToken.type == OneTimeTokenType.PASSWORD_RESET)
                & (OneTimeToken.used_at.is_(None))
            )
        ).all()
        for t in prior:
            t.used_at = datetime.utcnow()

        raw = secrets.token_urlsafe(40)
        token = OneTimeToken(
            user_id=user.id,
            type=OneTimeTokenType.PASSWORD_RESET,
            token=raw,
            expires_at=datetime.utcnow() + timedelta(minutes=30),
        )
        db.add(token)
        log_action(
            db, user_id=user.id, action="auth.password_reset_request",
            target_type="user", target_id=user.id, ip_address=client_ip(request),
        )
        db.commit()
        dev_token = raw  # In real life this would be emailed, not returned.

    return TokenIssuedResponse(
        sent=True,
        dev_token=dev_token,
        message="If the email is registered, a reset link has been sent.",
    )


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_reset(
    body: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db),
):
    """Consume a valid reset token and set a new password."""
    row = db.scalar(select(OneTimeToken).where(OneTimeToken.token == body.token))
    if (
        not row
        or row.type != OneTimeTokenType.PASSWORD_RESET
        or row.used_at is not None
        or row.expires_at < datetime.utcnow()
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    user = db.get(User, row.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User no longer eligible")

    user.hashed_password = hash_password(body.new_password)
    row.used_at = datetime.utcnow()

    # For safety, revoke every active session on password change.
    for r in user.refresh_tokens:
        r.revoked = True

    log_action(
        db, user_id=user.id, action="auth.password_reset_confirm",
        target_type="user", target_id=user.id, ip_address=client_ip(request),
    )
    notify(
        db, user_id=user.id, type=NotificationType.WARNING,
        title="Your password was reset",
        message="If you did not perform this action, contact an administrator immediately.",
    )
    db.commit()
    return None


# ── Email verification ──────────────────────────────────────────────────────
@router.post("/verify-email/request", response_model=TokenIssuedResponse)
def request_email_verification(
    body: EmailVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Issue a verification token for the given email."""
    user = db.scalar(select(User).where(User.email == body.email))
    dev_token: str | None = None

    if user and not user.is_verified:
        # Invalidate prior unused verification tokens.
        prior = db.scalars(
            select(OneTimeToken).where(
                (OneTimeToken.user_id == user.id)
                & (OneTimeToken.type == OneTimeTokenType.EMAIL_VERIFY)
                & (OneTimeToken.used_at.is_(None))
            )
        ).all()
        for t in prior:
            t.used_at = datetime.utcnow()

        raw = secrets.token_urlsafe(40)
        token = OneTimeToken(
            user_id=user.id,
            type=OneTimeTokenType.EMAIL_VERIFY,
            token=raw,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        db.add(token)
        log_action(
            db, user_id=user.id, action="auth.email_verify_request",
            target_type="user", target_id=user.id, ip_address=client_ip(request),
        )
        db.commit()
        dev_token = raw

    return TokenIssuedResponse(
        sent=True,
        dev_token=dev_token,
        message="If the email exists and is unverified, a link has been sent.",
    )


@router.post("/verify-email/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_email_verification(
    body: EmailVerifyConfirm,
    request: Request,
    db: Session = Depends(get_db),
):
    row = db.scalar(select(OneTimeToken).where(OneTimeToken.token == body.token))
    if (
        not row
        or row.type != OneTimeTokenType.EMAIL_VERIFY
        or row.used_at is not None
        or row.expires_at < datetime.utcnow()
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")

    user.is_verified = True
    row.used_at = datetime.utcnow()
    log_action(
        db, user_id=user.id, action="auth.email_verify_confirm",
        target_type="user", target_id=user.id, ip_address=client_ip(request),
    )
    notify(
        db, user_id=user.id, type=NotificationType.SUCCESS,
        title="Email verified",
        message="Thanks for verifying your email address.",
    )
    db.commit()
    return None
