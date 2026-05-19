"""Auth request/response schemas."""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)
    # Optional TOTP or backup code; required only when the account has 2FA enabled.
    code: Optional[str] = Field(default=None, min_length=6, max_length=8)


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    # Self-registration always becomes EMPLOYEE; admins can promote later.


class TokenPair(BaseModel):
    """Standard pair returned from login / refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds for access_token


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenPayload(BaseModel):
    """Decoded JWT body (internal use)."""
    sub: str  # user id (as string)
    role: UserRole
    type: str  # "access" or "refresh"
    exp: int
    iat: int
    jti: Optional[str] = None
