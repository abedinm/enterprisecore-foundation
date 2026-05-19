"""Schemas for password reset & email verification flows."""

from pydantic import BaseModel, EmailStr, Field


class PasswordResetRequest(BaseModel):
    """Step 1: user gives their email; we always 200 OK to avoid enumeration."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Step 2: user submits the token they received + their new password."""
    token: str = Field(min_length=10, max_length=255)
    new_password: str = Field(min_length=8, max_length=128)


class EmailVerifyRequest(BaseModel):
    """For (re-)requesting a verification email."""
    email: EmailStr


class EmailVerifyConfirm(BaseModel):
    token: str = Field(min_length=10, max_length=255)


class TokenIssuedResponse(BaseModel):
    """
    In a real deployment, the token would only ever be emailed.
    In dev (no SMTP configured), we return it directly so the flow is testable.
    """
    sent: bool
    dev_token: str | None = None
    message: str
