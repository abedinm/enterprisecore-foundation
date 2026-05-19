"""Task comment CRUD + access rules."""

import pytest


@pytest.fixture
def task_setup(client, admin_headers):
    """Admin creates a project + task, then registers Bob (employee) and adds him
    as a contributor. Returns (project_id, task_id, bob_token)."""
    project = client.post("/api/v1/projects", json={"name": "Comm"}, headers=admin_headers).json()
    task = client.post("/api/v1/tasks", json={"title": "Talk it out", "project_id": project["id"]}, headers=admin_headers).json()

    client.post("/api/v1/auth/register", json={"email": "bob@c.io", "full_name": "Bob", "password": "bob12345"})
    users = client.get("/api/v1/users", headers=admin_headers).json()
    bob = next(u for u in users if u["email"] == "bob@c.io")
    client.post(f"/api/v1/projects/{project['id']}/members",
                json={"user_id": bob["id"], "role": "contributor"}, headers=admin_headers)

    bob_token = client.post("/api/v1/auth/login", json={"email": "bob@c.io", "password": "bob12345"}).json()["access_token"]
    return project["id"], task["id"], bob_token


def test_member_can_post_and_list(client, admin_headers, task_setup):
    project_id, task_id, bob_token = task_setup
    bob_h = {"Authorization": f"Bearer {bob_token}"}
    r = client.post(f"/api/v1/tasks/{task_id}/comments", json={"body": "Hello team"}, headers=bob_h)
    assert r.status_code == 201
    assert r.json()["body"] == "Hello team"
    assert r.json()["author_name"] == "Bob"

    listed = client.get(f"/api/v1/tasks/{task_id}/comments", headers=admin_headers).json()
    assert len(listed) == 1


def test_non_member_cannot_see_comments(client, admin_headers, task_setup):
    project_id, task_id, _ = task_setup
    client.post("/api/v1/auth/register", json={"email": "out@c.io", "full_name": "Out", "password": "out12345"})
    out_token = client.post("/api/v1/auth/login", json={"email": "out@c.io", "password": "out12345"}).json()["access_token"]
    r = client.get(f"/api/v1/tasks/{task_id}/comments", headers={"Authorization": f"Bearer {out_token}"})
    assert r.status_code == 403


def test_author_can_edit_own_comment(client, admin_headers, task_setup):
    _, task_id, bob_token = task_setup
    bob_h = {"Authorization": f"Bearer {bob_token}"}
    cid = client.post(f"/api/v1/tasks/{task_id}/comments", json={"body": "v1"}, headers=bob_h).json()["id"]
    r = client.patch(f"/api/v1/tasks/{task_id}/comments/{cid}", json={"body": "v2"}, headers=bob_h)
    assert r.status_code == 200
    assert r.json()["body"] == "v2"
    assert r.json()["edited_at"] is not None


def test_other_user_cannot_edit_others_comment(client, admin_headers, task_setup):
    _, task_id, bob_token = task_setup
    bob_h = {"Authorization": f"Bearer {bob_token}"}
    cid = client.post(f"/api/v1/tasks/{task_id}/comments", json={"body": "mine"}, headers=bob_h).json()["id"]
    # Admin is not the author — should be rejected from editing
    r = client.patch(f"/api/v1/tasks/{task_id}/comments/{cid}", json={"body": "hacked"}, headers=admin_headers)
    assert r.status_code == 403


def test_admin_can_delete_others_comment(client, admin_headers, task_setup):
    _, task_id, bob_token = task_setup
    bob_h = {"Authorization": f"Bearer {bob_token}"}
    cid = client.post(f"/api/v1/tasks/{task_id}/comments", json={"body": "delete-me"}, headers=bob_h).json()["id"]
    r = client.delete(f"/api/v1/tasks/{task_id}/comments/{cid}", headers=admin_headers)
    assert r.status_code == 204
    assert client.get(f"/api/v1/tasks/{task_id}/comments", headers=admin_headers).json() == []


def test_author_can_delete_own(client, admin_headers, task_setup):
    _, task_id, bob_token = task_setup
    bob_h = {"Authorization": f"Bearer {bob_token}"}
    cid = client.post(f"/api/v1/tasks/{task_id}/comments", json={"body": "mine"}, headers=bob_h).json()["id"]
    r = client.delete(f"/api/v1/tasks/{task_id}/comments/{cid}", headers=bob_h)
    assert r.status_code == 204
