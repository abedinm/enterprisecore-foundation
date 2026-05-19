"""TOTP 2FA enrollment, verification, login gating, and backup codes."""

import pyotp
import pytest


def _enroll(client, headers) -> tuple[str, list[str]]:
    """Run the enroll + verify dance. Returns (secret, backup_codes)."""
    enroll = client.post("/api/v1/2fa/enroll", headers=headers).json()
    secret = enroll["secret"]
    code = pyotp.TOTP(secret).now()
    verify = client.post("/api/v1/2fa/verify", json={"code": code}, headers=headers).json()
    return secret, verify["backup_codes"]


@pytest.fixture
def user_with_2fa(client):
    """Registers fresh user, enrolls 2FA. Returns (email, password, secret, backup_codes)."""
    client.post("/api/v1/auth/register", json={
        "email": "tfa@test.io", "full_name": "TFA", "password": "tfasecret"
    })
    login = client.post("/api/v1/auth/login", json={"email": "tfa@test.io", "password": "tfasecret"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    secret, codes = _enroll(client, headers)
    return "tfa@test.io", "tfasecret", secret, codes


def test_status_starts_disabled(client, admin_headers):
    r = client.get("/api/v1/2fa/status", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["enabled"] is False


def test_enroll_returns_secret_and_qr(client, admin_headers):
    r = client.post("/api/v1/2fa/enroll", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body["secret"]) >= 16
    assert body["otpauth_uri"].startswith("otpauth://totp/")
    assert "<svg" in body["qr_svg"]


def test_verify_with_correct_code_enables(client, admin_headers):
    enroll = client.post("/api/v1/2fa/enroll", headers=admin_headers).json()
    code = pyotp.TOTP(enroll["secret"]).now()
    r = client.post("/api/v1/2fa/verify", json={"code": code}, headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert len(body["backup_codes"]) == 8
    # Now /status reflects it.
    s = client.get("/api/v1/2fa/status", headers=admin_headers).json()
    assert s["enabled"] is True


def test_verify_with_wrong_code_rejected(client, admin_headers):
    client.post("/api/v1/2fa/enroll", headers=admin_headers)
    r = client.post("/api/v1/2fa/verify", json={"code": "000000"}, headers=admin_headers)
    assert r.status_code == 400


def test_login_with_2fa_requires_code(client, user_with_2fa):
    email, password, secret, _ = user_with_2fa
    # No code — should fail with 403 "Two-factor code required"
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 403
    assert "two-factor" in r.json()["detail"].lower()

    # Correct code → OK
    r2 = client.post("/api/v1/auth/login", json={
        "email": email, "password": password, "code": pyotp.TOTP(secret).now()
    })
    assert r2.status_code == 200
    assert "access_token" in r2.json()


def test_login_with_wrong_2fa_code_fails(client, user_with_2fa):
    email, password, _secret, _ = user_with_2fa
    r = client.post("/api/v1/auth/login", json={
        "email": email, "password": password, "code": "000000"
    })
    assert r.status_code == 401


def test_backup_code_works_once(client, user_with_2fa):
    email, password, _secret, codes = user_with_2fa
    code = codes[0]

    # First use succeeds
    r1 = client.post("/api/v1/auth/login", json={
        "email": email, "password": password, "code": code
    })
    assert r1.status_code == 200

    # Reuse fails
    r2 = client.post("/api/v1/auth/login", json={
        "email": email, "password": password, "code": code
    })
    assert r2.status_code == 401


def test_disable_requires_valid_code(client, user_with_2fa):
    email, password, secret, _ = user_with_2fa
    # Log in fully first
    login = client.post("/api/v1/auth/login", json={
        "email": email, "password": password, "code": pyotp.TOTP(secret).now()
    }).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    # Wrong code rejected
    bad = client.post("/api/v1/2fa/disable", json={"code": "000000"}, headers=headers)
    assert bad.status_code == 400

    # Correct code disables
    ok = client.post("/api/v1/2fa/disable", json={"code": pyotp.TOTP(secret).now()}, headers=headers)
    assert ok.status_code == 204

    # /status flips back to disabled, and login no longer needs code
    s = client.get("/api/v1/2fa/status", headers=headers).json()
    assert s["enabled"] is False
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
