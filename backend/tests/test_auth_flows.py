"""Password reset + email verification."""


def test_password_reset_full_flow(client):
    # Register
    client.post("/api/v1/auth/register", json={"email": "r@test.io", "full_name": "R", "password": "originalpw"})

    # Request reset
    r = client.post("/api/v1/auth/password-reset/request", json={"email": "r@test.io"})
    assert r.status_code == 200
    token = r.json()["dev_token"]
    assert token

    # Confirm with new password
    r = client.post("/api/v1/auth/password-reset/confirm", json={
        "token": token, "new_password": "brand-new-password"
    })
    assert r.status_code == 204

    # Old password fails, new works
    assert client.post("/api/v1/auth/login", json={"email": "r@test.io", "password": "originalpw"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "r@test.io", "password": "brand-new-password"}).status_code == 200


def test_password_reset_token_single_use(client):
    client.post("/api/v1/auth/register", json={"email": "s@test.io", "full_name": "S", "password": "first1234"})
    token = client.post("/api/v1/auth/password-reset/request", json={"email": "s@test.io"}).json()["dev_token"]

    # First use succeeds
    assert client.post("/api/v1/auth/password-reset/confirm", json={
        "token": token, "new_password": "second1234"
    }).status_code == 204

    # Second use fails
    assert client.post("/api/v1/auth/password-reset/confirm", json={
        "token": token, "new_password": "third1234"
    }).status_code == 400


def test_password_reset_unknown_email_doesnt_leak(client):
    r = client.post("/api/v1/auth/password-reset/request", json={"email": "ghost@test.io"})
    assert r.status_code == 200  # never 404 — no enumeration
    assert r.json()["dev_token"] is None  # but no token issued internally either


def test_email_verification_flips_is_verified(client, admin_headers):
    client.post("/api/v1/auth/register", json={"email": "v@test.io", "full_name": "V", "password": "secret123"})

    # Verify it's currently unverified
    listed = client.get("/api/v1/users", headers=admin_headers).json()
    user = next(u for u in listed if u["email"] == "v@test.io")
    # Look up the full record
    me_at_start = client.get(f"/api/v1/users/{user['id']}", headers=admin_headers).json()
    assert me_at_start["is_verified"] is False

    token = client.post("/api/v1/auth/verify-email/request", json={"email": "v@test.io"}).json()["dev_token"]
    assert token
    assert client.post("/api/v1/auth/verify-email/confirm", json={"token": token}).status_code == 204

    me_after = client.get(f"/api/v1/users/{user['id']}", headers=admin_headers).json()
    assert me_after["is_verified"] is True


def test_already_verified_user_gets_no_token(client):
    client.post("/api/v1/auth/register", json={"email": "v2@test.io", "full_name": "V", "password": "secret123"})
    t1 = client.post("/api/v1/auth/verify-email/request", json={"email": "v2@test.io"}).json()["dev_token"]
    client.post("/api/v1/auth/verify-email/confirm", json={"token": t1})

    # Re-requesting for an already-verified email returns no token.
    second = client.post("/api/v1/auth/verify-email/request", json={"email": "v2@test.io"}).json()
    assert second["dev_token"] is None
