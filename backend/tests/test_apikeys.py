"""API Key CRUD + permissions."""


def test_admin_can_create_key(client, admin_headers):
    r = client.post("/api/v1/api-keys", json={"name": "test key"}, headers=admin_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "test key"
    assert "raw_key" in body and len(body["raw_key"]) > 10
    assert "prefix" in body and len(body["prefix"]) == 8
    assert body["revoked"] is False


def test_raw_key_only_returned_at_creation(client, admin_headers):
    client.post("/api/v1/api-keys", json={"name": "k1"}, headers=admin_headers)
    listed = client.get("/api/v1/api-keys", headers=admin_headers).json()
    assert len(listed) == 1
    assert "raw_key" not in listed[0]


def test_employee_cannot_create_key(client, employee_headers):
    r = client.post("/api/v1/api-keys", json={"name": "should fail"}, headers=employee_headers)
    assert r.status_code == 403


def test_revoke_marks_key_revoked(client, admin_headers):
    created = client.post("/api/v1/api-keys", json={"name": "k"}, headers=admin_headers).json()
    r = client.post(f"/api/v1/api-keys/{created['id']}/revoke", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["revoked"] is True


def test_delete_removes_key(client, admin_headers):
    created = client.post("/api/v1/api-keys", json={"name": "k"}, headers=admin_headers).json()
    assert client.delete(f"/api/v1/api-keys/{created['id']}", headers=admin_headers).status_code == 204
    assert client.get("/api/v1/api-keys", headers=admin_headers).json() == []


def test_user_cannot_revoke_someone_elses_key(client, admin_headers):
    # Admin creates a key.
    admin_key = client.post("/api/v1/api-keys", json={"name": "admins"}, headers=admin_headers).json()
    # A new developer user tries to revoke it.
    client.post("/api/v1/auth/register", json={"email": "dev@test.io", "full_name": "Dev", "password": "dev12345"})
    # Admin promotes them.
    listed = client.get("/api/v1/users", headers=admin_headers).json()
    dev_id = next(u["id"] for u in listed if u["email"] == "dev@test.io")
    client.patch(f"/api/v1/users/{dev_id}", json={"role": "developer"}, headers=admin_headers)
    # Dev logs in.
    dev_token = client.post("/api/v1/auth/login", json={"email": "dev@test.io", "password": "dev12345"}).json()["access_token"]
    dev_headers = {"Authorization": f"Bearer {dev_token}"}

    r = client.post(f"/api/v1/api-keys/{admin_key['id']}/revoke", headers=dev_headers)
    assert r.status_code == 403
