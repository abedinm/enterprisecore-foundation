"""Project & task CRUD + permission boundaries."""


def test_manager_can_create_project(client, admin_headers):
    # Promote a registered user to manager
    client.post("/api/v1/auth/register", json={"email": "mgr@test.io", "full_name": "Mgr", "password": "secret123"})
    users = client.get("/api/v1/users", headers=admin_headers).json()
    mid = next(u["id"] for u in users if u["email"] == "mgr@test.io")
    client.patch(f"/api/v1/users/{mid}", json={"role": "manager"}, headers=admin_headers)

    token = client.post("/api/v1/auth/login", json={"email": "mgr@test.io", "password": "secret123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/v1/projects", json={"name": "Apollo", "description": "moon"}, headers=headers)
    assert r.status_code == 201
    assert r.json()["name"] == "Apollo"


def test_employee_cannot_create_project(client, employee_headers):
    r = client.post("/api/v1/projects", json={"name": "Nope"}, headers=employee_headers)
    assert r.status_code == 403


def test_task_lifecycle(client, admin_headers):
    p = client.post("/api/v1/projects", json={"name": "P", "description": ""}, headers=admin_headers).json()
    t = client.post("/api/v1/tasks", json={
        "title": "Build it", "project_id": p["id"], "priority": "high"
    }, headers=admin_headers)
    assert t.status_code == 201
    tid = t.json()["id"]

    # Update status
    upd = client.patch(f"/api/v1/tasks/{tid}", json={"status": "in_progress"}, headers=admin_headers)
    assert upd.status_code == 200
    assert upd.json()["status"] == "in_progress"

    # Mark done
    done = client.patch(f"/api/v1/tasks/{tid}", json={"status": "done"}, headers=admin_headers)
    assert done.json()["status"] == "done"

    # Delete
    assert client.delete(f"/api/v1/tasks/{tid}", headers=admin_headers).status_code == 204
