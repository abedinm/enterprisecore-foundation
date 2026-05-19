"""Cross-domain search visibility and accuracy."""

import pytest


@pytest.fixture
def populated(client, admin_headers):
    """Seed: a user named 'Maverick', a project 'Apollo', a task 'Mission briefing'."""
    client.post("/api/v1/users", json={
        "email": "maverick@test.io", "full_name": "Maverick Pilot",
        "password": "topgun12345", "role": "employee"
    }, headers=admin_headers)
    project = client.post("/api/v1/projects", json={
        "name": "Apollo", "description": "moon mission"
    }, headers=admin_headers).json()
    task = client.post("/api/v1/tasks", json={
        "title": "Mission briefing", "project_id": project["id"], "description": "Apollo prep"
    }, headers=admin_headers).json()
    return project, task


def test_admin_finds_user(client, admin_headers, populated):
    r = client.get("/api/v1/search?q=maverick", headers=admin_headers)
    assert r.status_code == 200
    kinds = {h["kind"] for h in r.json()["results"]}
    assert "user" in kinds


def test_employee_does_not_see_users_in_search(client, admin_headers, employee_headers, populated):
    """Employee searches for an admin's name — should NOT see user hits."""
    r = client.get("/api/v1/search?q=maverick", headers=employee_headers)
    assert r.status_code == 200
    kinds = {h["kind"] for h in r.json()["results"]}
    assert "user" not in kinds


def test_admin_finds_project(client, admin_headers, populated):
    r = client.get("/api/v1/search?q=apollo", headers=admin_headers).json()
    assert any(h["kind"] == "project" and h["title"] == "Apollo" for h in r["results"])


def test_admin_finds_task(client, admin_headers, populated):
    r = client.get("/api/v1/search?q=briefing", headers=admin_headers).json()
    assert any(h["kind"] == "task" for h in r["results"])


def test_scope_users_returns_only_users(client, admin_headers, populated):
    r = client.get("/api/v1/search?q=a&scope=users", headers=admin_headers).json()
    assert all(h["kind"] == "user" for h in r["results"])


def test_query_with_no_matches_returns_empty(client, admin_headers, populated):
    r = client.get("/api/v1/search?q=zzz-no-such-thing", headers=admin_headers).json()
    assert r["total"] == 0


def test_finds_comments(client, admin_headers, populated):
    _project, task = populated
    client.post(f"/api/v1/tasks/{task['id']}/comments", json={"body": "needs more thrust"}, headers=admin_headers)
    r = client.get("/api/v1/search?q=thrust", headers=admin_headers).json()
    assert any(h["kind"] == "comment" for h in r["results"])
