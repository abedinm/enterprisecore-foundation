"""2FA schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field


class TwoFactorStatus(BaseModel):
    enabled: bool


class TwoFactorEnrollResponse(BaseModel):
    """First step: returns the secret + a QR-code-ready otpauth URI.

    The user scans the QR in an authenticator app, then POSTs the
    6-digit code to /2fa/verify to finalize enrollment.
    """
    secret: str
    otpauth_uri: str
    qr_svg: str  # inline SVG that the frontend can render directly


class TwoFactorVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class TwoFactorVerifyResponse(BaseModel):
    enabled: bool
    backup_codes: List[str]  # plaintext, shown ONCE


class TwoFactorDisableRequest(BaseModel):
    """To disable, the user must prove possession of a current code."""
    code: str = Field(min_length=6, max_length=8)


class LoginWith2FA(BaseModel):
    """Login that may include a TOTP code or a backup code.

    Backend behaviour:
      - If user has 2FA disabled: ignore `code`; behave like normal login.
      - If 2FA is enabled and `code` is missing: 403 + needs_2fa=True.
      - If `code` is wrong: 401.
    """
    email: str
    password: str
    code: Optional[str] = None  # 6-digit TOTP OR 8-char backup code


class Needs2FAResponse(BaseModel):
    needs_2fa: bool = True
    detail: str = "Two-factor code required"
