"""Soft-delete + restore for users / projects / tasks."""


def test_archive_user_excludes_from_default_list(client, admin_headers):
    client.post("/api/v1/auth/register", json={"email": "arch@test.io", "full_name": "A", "password": "secret123"})
    users_before = client.get("/api/v1/users", headers=admin_headers).json()
    uid = next(u["id"] for u in users_before if u["email"] == "arch@test.io")

    # Archive
    r = client.post(f"/api/v1/users/{uid}/archive", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["deleted_at"] is not None
    assert r.json()["is_active"] is False

    # Default list excludes them
    after = client.get("/api/v1/users", headers=admin_headers).json()
    assert all(u["id"] != uid for u in after)

    # include_archived=true brings them back
    with_arch = client.get("/api/v1/users?include_archived=true", headers=admin_headers).json()
    assert any(u["id"] == uid for u in with_arch)


def test_archived_user_cannot_login(client, admin_headers):
    client.post("/api/v1/auth/register", json={"email": "ban@test.io", "full_name": "B", "password": "secret123"})
    uid = next(u["id"] for u in client.get("/api/v1/users", headers=admin_headers).json() if u["email"] == "ban@test.io")
    client.post(f"/api/v1/users/{uid}/archive", headers=admin_headers)

    r = client.post("/api/v1/auth/login", json={"email": "ban@test.io", "password": "secret123"})
    assert r.status_code == 403


def test_restore_user_reactivates(client, admin_headers):
    client.post("/api/v1/auth/register", json={"email": "rest@test.io", "full_name": "R", "password": "secret123"})
    uid = next(u["id"] for u in client.get("/api/v1/users", headers=admin_headers).json() if u["email"] == "rest@test.io")
    client.post(f"/api/v1/users/{uid}/archive", headers=admin_headers)
    r = client.post(f"/api/v1/users/{uid}/restore", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["deleted_at"] is None
    assert r.json()["is_active"] is True

    # Login now works again
    assert client.post("/api/v1/auth/login", json={"email": "rest@test.io", "password": "secret123"}).status_code == 200


def test_cannot_archive_system_admin(client, admin_headers):
    r = client.post("/api/v1/users/1/archive", headers=admin_headers)
    assert r.status_code == 400


def test_restore_a_live_user_returns_400(client, admin_headers):
    client.post("/api/v1/auth/register", json={"email": "live@test.io", "full_name": "L", "password": "secret123"})
    uid = next(u["id"] for u in client.get("/api/v1/users", headers=admin_headers).json() if u["email"] == "live@test.io")
    r = client.post(f"/api/v1/users/{uid}/restore", headers=admin_headers)
    assert r.status_code == 400


def test_archive_project(client, admin_headers):
    p = client.post("/api/v1/projects", json={"name": "Archive me"}, headers=admin_headers).json()
    r = client.post(f"/api/v1/projects/{p['id']}/archive", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["deleted_at"] is not None

    # Default list excludes
    listed = client.get("/api/v1/projects", headers=admin_headers).json()
    assert all(x["id"] != p["id"] for x in listed)

    # include_archived shows it
    all_p = client.get("/api/v1/projects?include_archived=true", headers=admin_headers).json()
    assert any(x["id"] == p["id"] for x in all_p)

    # Restore
    r2 = client.post(f"/api/v1/projects/{p['id']}/restore", headers=admin_headers)
    assert r2.status_code == 200
    assert r2.json()["deleted_at"] is None


def test_archive_task(client, admin_headers):
    p = client.post("/api/v1/projects", json={"name": "P"}, headers=admin_headers).json()
    t = client.post("/api/v1/tasks", json={"title": "Archivable", "project_id": p["id"]}, headers=admin_headers).json()
    r = client.post(f"/api/v1/tasks/{t['id']}/archive", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["deleted_at"] is not None
    # Default list excludes
    listed = client.get("/api/v1/tasks", headers=admin_headers).json()
    assert all(x["id"] != t["id"] for x in listed)
    # Restore
    rr = client.post(f"/api/v1/tasks/{t['id']}/restore", headers=admin_headers)
    assert rr.status_code == 200
