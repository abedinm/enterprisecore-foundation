"""Notifications: per-user CRUD + admin send/broadcast."""


def test_initially_no_notifications(client, admin_headers):
    r = client.get("/api/v1/notifications", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_broadcast_creates_one_per_user(client, admin_headers):
    # Add another user so we have >1
    client.post("/api/v1/auth/register", json={"email": "u1@test.io", "full_name": "U1", "password": "secret123"})

    r = client.post("/api/v1/notifications/broadcast", json={
        "user_id": 0, "type": "system", "title": "Hello", "message": "Welcome"
    }, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["sent"] >= 2

    # Admin has at least one unread now.
    count = client.get("/api/v1/notifications/unread-count", headers=admin_headers).json()
    assert count["count"] >= 1


def test_employee_cannot_broadcast(client, employee_headers):
    r = client.post("/api/v1/notifications/broadcast", json={
        "user_id": 0, "type": "system", "title": "Spam", "message": "x"
    }, headers=employee_headers)
    assert r.status_code == 403


def test_mark_read_and_delete(client, admin_headers):
    client.post("/api/v1/notifications/broadcast", json={
        "user_id": 0, "type": "info", "title": "Read me", "message": "x"
    }, headers=admin_headers)
    items = client.get("/api/v1/notifications", headers=admin_headers).json()
    nid = items[0]["id"]

    assert client.post(f"/api/v1/notifications/{nid}/read", headers=admin_headers).status_code == 204
    items2 = client.get("/api/v1/notifications", headers=admin_headers).json()
    assert next(n for n in items2 if n["id"] == nid)["read"] is True

    assert client.delete(f"/api/v1/notifications/{nid}", headers=admin_headers).status_code == 204
    items3 = client.get("/api/v1/notifications", headers=admin_headers).json()
    assert not any(n["id"] == nid for n in items3)
