"""Auth + RBAC tests."""


def test_health_no_auth_required(client):
    r = client.get("/api/v1/system/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_admin_login_returns_token_pair(client):
    r = client.post("/api/v1/auth/login", json={"email": "admin@test.io", "password": "Admin123!"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["access_token"].count(".") == 2


def test_login_wrong_password_returns_401(client):
    r = client.post("/api/v1/auth/login", json={"email": "admin@test.io", "password": "wrong"})
    assert r.status_code == 401


def test_register_then_login(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "new@test.io", "full_name": "New User", "password": "secret123",
    })
    assert r.status_code == 201
    assert r.json()["role"] == "employee"

    r2 = client.post("/api/v1/auth/login", json={"email": "new@test.io", "password": "secret123"})
    assert r2.status_code == 200


def test_register_duplicate_email_returns_409(client):
    payload = {"email": "dup@test.io", "full_name": "Dup", "password": "secret123"}
    client.post("/api/v1/auth/register", json=payload)
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409


def test_me_returns_current_user(client, admin_headers):
    r = client.get("/api/v1/auth/me", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "admin@test.io"
    assert body["role"] == "admin"


def test_me_without_token_returns_401(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_with_bad_token_returns_401(client):
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert r.status_code == 401


def test_refresh_token_flow(client):
    login = client.post("/api/v1/auth/login", json={"email": "admin@test.io", "password": "Admin123!"}).json()
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_logout_revokes_refresh_token(client):
    login = client.post("/api/v1/auth/login", json={"email": "admin@test.io", "password": "Admin123!"}).json()
    r = client.post("/api/v1/auth/logout", json={"refresh_token": login["refresh_token"]})
    assert r.status_code == 204
    # Now the refresh token should be rejected.
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert r2.status_code == 401


def test_employee_cannot_list_users(client, employee_headers):
    r = client.get("/api/v1/users", headers=employee_headers)
    assert r.status_code == 403


def test_admin_can_list_users(client, admin_headers):
    r = client.get("/api/v1/users", headers=admin_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_admin_can_promote_employee(client, admin_headers):
    client.post("/api/v1/auth/register", json={"email": "u@test.io", "full_name": "U", "password": "secret123"})
    listed = client.get("/api/v1/users", headers=admin_headers).json()
    uid = next(u["id"] for u in listed if u["email"] == "u@test.io")
    r = client.patch(f"/api/v1/users/{uid}", json={"role": "manager"}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["role"] == "manager"


def test_cannot_delete_system_admin(client, admin_headers):
    r = client.delete("/api/v1/users/1", headers=admin_headers)
    assert r.status_code == 400


def test_password_change_revokes_sessions(client):
    # Register + login
    client.post("/api/v1/auth/register", json={"email": "pw@test.io", "full_name": "PW", "password": "oldsecret"})
    login = client.post("/api/v1/auth/login", json={"email": "pw@test.io", "password": "oldsecret"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    r = client.post("/api/v1/users/me/password", json={
        "current_password": "oldsecret", "new_password": "newsecret"
    }, headers=headers)
    assert r.status_code == 204

    # Old refresh is now revoked.
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}).status_code == 401

    # Old password no longer works.
    assert client.post("/api/v1/auth/login", json={"email": "pw@test.io", "password": "oldsecret"}).status_code == 401

    # New password works.
    assert client.post("/api/v1/auth/login", json={"email": "pw@test.io", "password": "newsecret"}).status_code == 200
