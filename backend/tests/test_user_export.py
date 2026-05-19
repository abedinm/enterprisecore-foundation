"""User export + admin user creation."""

import csv
import io
import json


def test_admin_create_user(client, admin_headers):
    r = client.post("/api/v1/users", json={
        "email": "new@test.io",
        "full_name": "New User",
        "password": "newpassword",
        "role": "manager",
        "is_active": True,
        "is_verified": True,
    }, headers=admin_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "manager"
    assert body["is_verified"] is True


def test_admin_create_duplicate_email_returns_409(client, admin_headers):
    client.post("/api/v1/users", json={
        "email": "dup@test.io", "full_name": "X", "password": "secret123"
    }, headers=admin_headers)
    r = client.post("/api/v1/users", json={
        "email": "dup@test.io", "full_name": "Y", "password": "secret123"
    }, headers=admin_headers)
    assert r.status_code == 409


def test_employee_cannot_use_admin_create(client, employee_headers):
    r = client.post("/api/v1/users", json={
        "email": "nope@test.io", "full_name": "Nope", "password": "secret123"
    }, headers=employee_headers)
    assert r.status_code == 403


def test_export_csv_default(client, admin_headers):
    r = client.get("/api/v1/users/export", headers=admin_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    # Parse the CSV
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows) >= 1
    assert "email" in rows[0]
    assert "hashed_password" not in rows[0]  # MUST NOT leak


def test_export_json(client, admin_headers):
    r = client.get("/api/v1/users/export?format=json", headers=admin_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    data = json.loads(r.text)
    assert isinstance(data, list)
    assert "email" in data[0]
    assert "hashed_password" not in data[0]


def test_employee_cannot_export(client, employee_headers):
    r = client.get("/api/v1/users/export", headers=employee_headers)
    assert r.status_code == 403
