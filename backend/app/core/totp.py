"""TOTP helpers (enroll + verify) using pyotp."""

import json
import secrets
from typing import List, Tuple

import pyotp
import qrcode
import qrcode.image.svg

from app.core.security import hash_password, verify_password


# ── Secret + QR ─────────────────────────────────────────────────────────────
def new_secret() -> str:
    """Returns a fresh base32 secret suitable for TOTP."""
    return pyotp.random_base32()


def otpauth_uri(*, secret: str, account_email: str, issuer: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=account_email, issuer_name=issuer)


def qr_svg_for_uri(uri: str) -> str:
    """Inline SVG representation of the provisioning URI."""
    factory = qrcode.image.svg.SvgImage
    img = qrcode.make(uri, image_factory=factory, box_size=8, border=2)
    # qrcode-svg produces XML — wrap to bytes-decoded string.
    from io import BytesIO
    buf = BytesIO()
    img.save(buf)
    return buf.getvalue().decode("utf-8")


# ── Verify ──────────────────────────────────────────────────────────────────
def verify_totp(secret: str, code: str) -> bool:
    """6-digit TOTP code. Allows a 30-second clock-skew window."""
    if not code or not code.isdigit() or len(code) != 6:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


# ── Backup codes ────────────────────────────────────────────────────────────
def generate_backup_codes(count: int = 8) -> Tuple[List[str], List[str]]:
    """Returns (plaintext, hashed). Plaintext is shown ONCE to the user."""
    plain = [secrets.token_hex(4).upper() for _ in range(count)]   # 8-char hex
    hashed = [hash_password(c) for c in plain]
    return plain, hashed


def consume_backup_code(stored_json: str, code: str) -> Tuple[bool, str]:
    """If `code` matches any unused hashed backup code, mark it consumed
    (by removing it from the list) and return (True, new_json). Else
    return (False, stored_json).
    """
    if not code:
        return False, stored_json
    try:
        hashes: list[str] = json.loads(stored_json) or []
    except json.JSONDecodeError:
        return False, stored_json
    for i, h in enumerate(hashes):
        if verify_password(code, h):
            hashes.pop(i)
            return True, json.dumps(hashes)
    return False, stored_json


def hashes_to_json(hashes: List[str]) -> str:
    return json.dumps(hashes)
