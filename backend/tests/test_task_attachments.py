"""Task attachment upload/download/delete + size and MIME guards."""

import io
import pytest


@pytest.fixture
def task_setup(client, admin_headers):
    p = client.post("/api/v1/projects", json={"name": "Files"}, headers=admin_headers).json()
    t = client.post("/api/v1/tasks", json={"title": "Need a file", "project_id": p["id"]}, headers=admin_headers).json()
    return t["id"]


def test_upload_and_list(client, admin_headers, task_setup):
    tid = task_setup
    payload = b"This is a small text file used for upload testing."
    r = client.post(
        f"/api/v1/tasks/{tid}/attachments",
        files={"file": ("hello.txt", io.BytesIO(payload), "text/plain")},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["filename"] == "hello.txt"
    assert body["size_bytes"] == len(payload)
    assert body["content_type"] == "text/plain"

    listed = client.get(f"/api/v1/tasks/{tid}/attachments", headers=admin_headers).json()
    assert len(listed) == 1


def test_download_returns_file_bytes(client, admin_headers, task_setup):
    tid = task_setup
    payload = b"download me"
    up = client.post(
        f"/api/v1/tasks/{tid}/attachments",
        files={"file": ("hi.txt", io.BytesIO(payload), "text/plain")},
        headers=admin_headers,
    ).json()
    r = client.get(f"/api/v1/tasks/{tid}/attachments/{up['id']}/download", headers=admin_headers)
    assert r.status_code == 200
    assert r.content == payload
    assert "attachment" in r.headers.get("content-disposition", "")


def test_rejects_disallowed_mime(client, admin_headers, task_setup):
    tid = task_setup
    r = client.post(
        f"/api/v1/tasks/{tid}/attachments",
        files={"file": ("evil.exe", io.BytesIO(b"MZ\x00"), "application/x-msdownload")},
        headers=admin_headers,
    )
    assert r.status_code == 415


def test_rejects_oversize(client, admin_headers, task_setup, monkeypatch):
    """Set the cap to 1 MB and try uploading 2 MB."""
    from app.config import settings as s
    monkeypatch.setattr(s, "max_upload_mb", 1)

    tid = task_setup
    big = b"a" * (2 * 1024 * 1024)
    r = client.post(
        f"/api/v1/tasks/{tid}/attachments",
        files={"file": ("big.txt", io.BytesIO(big), "text/plain")},
        headers=admin_headers,
    )
    assert r.status_code == 413


def test_non_member_cannot_upload(client, admin_headers, task_setup):
    tid = task_setup
    client.post("/api/v1/auth/register", json={"email": "out@a.io", "full_name": "Out", "password": "out12345"})
    out_token = client.post("/api/v1/auth/login", json={"email": "out@a.io", "password": "out12345"}).json()["access_token"]
    r = client.post(
        f"/api/v1/tasks/{tid}/attachments",
        files={"file": ("x.txt", io.BytesIO(b"x"), "text/plain")},
        headers={"Authorization": f"Bearer {out_token}"},
    )
    assert r.status_code == 403


def test_uploader_can_delete(client, admin_headers, task_setup):
    tid = task_setup
    up = client.post(
        f"/api/v1/tasks/{tid}/attachments",
        files={"file": ("delete-me.txt", io.BytesIO(b"bye"), "text/plain")},
        headers=admin_headers,
    ).json()
    r = client.delete(f"/api/v1/tasks/{tid}/attachments/{up['id']}", headers=admin_headers)
    assert r.status_code == 204
    assert client.get(f"/api/v1/tasks/{tid}/attachments", headers=admin_headers).json() == []
