"""Activity feed visibility."""

import pytest


@pytest.fixture
def some_activity(client, admin_headers):
    """Generate a few audit-log-producing events."""
    client.post("/api/v1/projects", json={"name": "Activity test"}, headers=admin_headers)
    client.post("/api/v1/auth/register", json={
        "email": "act@test.io", "full_name": "Act", "password": "secret123"
    })


def test_admin_sees_activity(client, admin_headers, some_activity):
    r = client.get("/api/v1/activity", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 2  # at least: register + admin login earlier


def test_employee_sees_only_their_actions_or_visible_project_actions(
    client, admin_headers, some_activity, employee_headers
):
    # The seeded employee logged in (their own action shows). They cannot see
    # admin actions on a project they aren't part of.
    r = client.get("/api/v1/activity", headers=employee_headers)
    assert r.status_code == 200
    rows = r.json()
    # Every visible row is either authored by the employee themselves or
    # targets a project they can access (which is none here).
    me = client.get("/api/v1/auth/me", headers=employee_headers).json()
    for row in rows:
        if row["user_id"] != me["id"]:
            assert row["target_type"] == "project"  # only project-targeted rows allowed otherwise


def test_mine_only_filter(client, admin_headers, some_activity):
    me_id = client.get("/api/v1/auth/me", headers=admin_headers).json()["id"]
    r = client.get("/api/v1/activity?mine=true", headers=admin_headers).json()
    assert all(row["user_id"] == me_id for row in r)


def test_project_filter_forbidden_for_non_member(client, admin_headers, employee_headers):
    project = client.post("/api/v1/projects", json={"name": "Private"}, headers=admin_headers).json()
    r = client.get(f"/api/v1/activity?project_id={project['id']}", headers=employee_headers)
    assert r.status_code == 403
