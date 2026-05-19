"""Department CRUD + member assignment."""


def test_default_departments_seeded(client, admin_headers):
    r = client.get("/api/v1/departments", headers=admin_headers)
    assert r.status_code == 200
    names = [d["name"] for d in r.json()]
    for expected in ("Engineering", "Product", "Operations", "People"):
        assert expected in names


def test_add_and_remove_member(client, admin_headers):
    depts = client.get("/api/v1/departments", headers=admin_headers).json()
    eng = next(d for d in depts if d["name"] == "Engineering")

    # Create a fresh user
    client.post("/api/v1/auth/register", json={"email": "m@test.io", "full_name": "M", "password": "secret123"})
    users = client.get("/api/v1/users", headers=admin_headers).json()
    uid = next(u["id"] for u in users if u["email"] == "m@test.io")

    # Initially: no members
    members = client.get(f"/api/v1/departments/{eng['id']}/members", headers=admin_headers).json()
    assert all(u["id"] != uid for u in members)

    # Add
    r = client.post(f"/api/v1/departments/{eng['id']}/members/{uid}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["department_id"] == eng["id"]

    # Listing shows them
    members2 = client.get(f"/api/v1/departments/{eng['id']}/members", headers=admin_headers).json()
    assert any(u["id"] == uid for u in members2)

    # Remove
    assert client.delete(f"/api/v1/departments/{eng['id']}/members/{uid}", headers=admin_headers).status_code == 204
    members3 = client.get(f"/api/v1/departments/{eng['id']}/members", headers=admin_headers).json()
    assert all(u["id"] != uid for u in members3)


def test_employee_can_read_but_not_create_department(client, admin_headers, employee_headers):
    # Read OK
    assert client.get("/api/v1/departments", headers=employee_headers).status_code == 200
    # Create fails
    assert client.post("/api/v1/departments", json={"name": "Sneaky"}, headers=employee_headers).status_code == 403


def test_deleting_department_detaches_members(client, admin_headers):
    # New dept
    new = client.post("/api/v1/departments", json={"name": "Temp", "description": ""}, headers=admin_headers).json()

    # Register and assign a user
    client.post("/api/v1/auth/register", json={"email": "t@test.io", "full_name": "T", "password": "secret123"})
    users = client.get("/api/v1/users", headers=admin_headers).json()
    uid = next(u["id"] for u in users if u["email"] == "t@test.io")
    client.post(f"/api/v1/departments/{new['id']}/members/{uid}", headers=admin_headers)

    # Delete dept
    assert client.delete(f"/api/v1/departments/{new['id']}", headers=admin_headers).status_code == 204

    # User still exists, with department_id cleared
    me = client.get(f"/api/v1/users/{uid}", headers=admin_headers).json()
    assert me["department_id"] is None
