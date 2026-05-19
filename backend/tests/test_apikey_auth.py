"""API keys can be used as bearer credentials in lieu of a JWT."""


def test_api_key_authenticates_like_a_jwt(client, admin_headers):
    # Create a key
    created = client.post("/api/v1/api-keys", json={"name": "ci"}, headers=admin_headers).json()
    raw = created["raw_key"]

    # Use the raw key as the Bearer token
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {raw}"})
    assert r.status_code == 200
    assert r.json()["email"] == "admin@test.io"


def test_revoked_api_key_no_longer_authenticates(client, admin_headers):
    created = client.post("/api/v1/api-keys", json={"name": "ci2"}, headers=admin_headers).json()
    raw = created["raw_key"]

    # Works before revocation
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {raw}"}).status_code == 200

    # Revoke
    client.post(f"/api/v1/api-keys/{created['id']}/revoke", headers=admin_headers)

    # No longer works
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {raw}"}).status_code == 401


def test_api_key_inherits_owner_role(client, admin_headers):
    """An admin's API key should be able to do admin things."""
    raw = client.post("/api/v1/api-keys", json={"name": "k"}, headers=admin_headers).json()["raw_key"]
    r = client.get("/api/v1/users", headers={"Authorization": f"Bearer {raw}"})
    assert r.status_code == 200


def test_api_key_last_used_at_bumps(client, admin_headers):
    created = client.post("/api/v1/api-keys", json={"name": "lu"}, headers=admin_headers).json()
    assert created["last_used_at"] is None
    raw = created["raw_key"]

    # Use the key
    client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {raw}"})

    # last_used_at should now be set
    listed = client.get("/api/v1/api-keys", headers=admin_headers).json()
    assert listed[0]["last_used_at"] is not None
