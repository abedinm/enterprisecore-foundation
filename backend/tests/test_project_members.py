"""Project membership: many-to-many with per-project roles."""

import pytest


@pytest.fixture
def project_with_members(client, admin_headers):
    """Returns (project, [bob, carol]) — both registered, both added as contributors."""
    project = client.post("/api/v1/projects", json={"name": "Alpha"}, headers=admin_headers).json()

    client.post("/api/v1/auth/register", json={"email": "bob@p.io", "full_name": "Bob", "password": "bob12345"})
    client.post("/api/v1/auth/register", json={"email": "carol@p.io", "full_name": "Carol", "password": "carol123"})
    users = client.get("/api/v1/users", headers=admin_headers).json()
    bob = next(u for u in users if u["email"] == "bob@p.io")
    carol = next(u for u in users if u["email"] == "carol@p.io")

    client.post(f"/api/v1/projects/{project['id']}/members",
                json={"user_id": bob["id"], "role": "contributor"}, headers=admin_headers)
    client.post(f"/api/v1/projects/{project['id']}/members",
                json={"user_id": carol["id"], "role": "lead"}, headers=admin_headers)

    return project, bob, carol


def test_member_list_returns_added_users(client, admin_headers, project_with_members):
    project, bob, carol = project_with_members
    members = client.get(f"/api/v1/projects/{project['id']}/members", headers=admin_headers).json()
    emails = {m["user_email"] for m in members}
    assert "bob@p.io" in emails
    assert "carol@p.io" in emails


def test_cannot_add_member_twice(client, admin_headers, project_with_members):
    project, bob, _ = project_with_members
    r = client.post(f"/api/v1/projects/{project['id']}/members",
                    json={"user_id": bob["id"], "role": "viewer"}, headers=admin_headers)
    assert r.status_code == 409


def test_update_member_role(client, admin_headers, project_with_members):
    project, bob, _ = project_with_members
    r = client.patch(f"/api/v1/projects/{project['id']}/members/{bob['id']}",
                     json={"role": "viewer"}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["role"] == "viewer"


def test_employee_member_can_see_project(client, admin_headers, project_with_members):
    project, bob, _ = project_with_members
    bob_token = client.post("/api/v1/auth/login", json={"email": "bob@p.io", "password": "bob12345"}).json()["access_token"]
    bob_hdr = {"Authorization": f"Bearer {bob_token}"}
    r = client.get(f"/api/v1/projects/{project['id']}", headers=bob_hdr)
    assert r.status_code == 200


def test_employee_non_member_cannot_see_project(client, admin_headers, project_with_members):
    project, _bob, _carol = project_with_members
    # Register an outsider
    client.post("/api/v1/auth/register", json={"email": "out@p.io", "full_name": "Out", "password": "out12345"})
    out_token = client.post("/api/v1/auth/login", json={"email": "out@p.io", "password": "out12345"}).json()["access_token"]
    r = client.get(f"/api/v1/projects/{project['id']}", headers={"Authorization": f"Bearer {out_token}"})
    assert r.status_code == 403


def test_lead_can_add_more_members(client, admin_headers, project_with_members):
    """Carol was added as a lead — she should be able to add others."""
    project, _bob, carol = project_with_members
    client.post("/api/v1/auth/register", json={"email": "dave@p.io", "full_name": "Dave", "password": "dave1234"})
    dave = next(u for u in client.get("/api/v1/users", headers=admin_headers).json() if u["email"] == "dave@p.io")

    carol_token = client.post("/api/v1/auth/login", json={"email": "carol@p.io", "password": "carol123"}).json()["access_token"]
    r = client.post(f"/api/v1/projects/{project['id']}/members",
                    json={"user_id": dave["id"], "role": "contributor"},
                    headers={"Authorization": f"Bearer {carol_token}"})
    assert r.status_code == 201


def test_contributor_cannot_add_members(client, admin_headers, project_with_members):
    project, bob, _ = project_with_members
    client.post("/api/v1/auth/register", json={"email": "eve@p.io", "full_name": "Eve", "password": "eve12345"})
    eve = next(u for u in client.get("/api/v1/users", headers=admin_headers).json() if u["email"] == "eve@p.io")

    bob_token = client.post("/api/v1/auth/login", json={"email": "bob@p.io", "password": "bob12345"}).json()["access_token"]
    r = client.post(f"/api/v1/projects/{project['id']}/members",
                    json={"user_id": eve["id"], "role": "contributor"},
                    headers={"Authorization": f"Bearer {bob_token}"})
    assert r.status_code == 403


def test_member_self_remove(client, admin_headers, project_with_members):
    project, bob, _ = project_with_members
    bob_token = client.post("/api/v1/auth/login", json={"email": "bob@p.io", "password": "bob12345"}).json()["access_token"]
    r = client.delete(f"/api/v1/projects/{project['id']}/members/{bob['id']}",
                      headers={"Authorization": f"Bearer {bob_token}"})
    assert r.status_code == 204
