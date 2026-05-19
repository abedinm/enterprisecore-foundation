"""Additional smoke tests for: API Keys, password reset, email verify, dept members."""

import json
import urllib.request
import urllib.error


BASE = "http://127.0.0.1:8000/api/v1"


def call(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, method=method, data=data,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            text = r.read().decode()
            try: return r.status, json.loads(text)
            except json.JSONDecodeError: return r.status, text
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main():
    failures = 0
    def check(label, ok, info=""):
        nonlocal failures
        mark = "[PASS]" if ok else "[FAIL]"
        print(f"  {mark}  {label}  {info}")
        if not ok: failures += 1

    # Bootstrap: admin login
    s, login = call("POST", "/auth/login", {"email": "admin@enterprisecore.io", "password": "Admin123!"})
    check("admin login", s == 200)
    admin_token = login["access_token"]

    print("\n== API Keys ==")
    s, list1 = call("GET", "/api-keys", token=admin_token)
    check("list (initially empty)", s == 200 and isinstance(list1, list))

    s, created = call("POST", "/api-keys", {"name": "GitHub Actions CI"}, token=admin_token)
    check("create returns 201", s == 201, f"status={s}")
    check("response includes raw_key", "raw_key" in created and len(created.get("raw_key", "")) > 10)
    check("response includes prefix", "prefix" in created and len(created["prefix"]) == 8)
    key_id = created["id"]

    s, list2 = call("GET", "/api-keys", token=admin_token)
    check("list now has 1 key", s == 200 and len(list2) == 1)
    check("list does NOT leak raw_key", "raw_key" not in list2[0])

    s, _ = call("POST", f"/api-keys/{key_id}/revoke", token=admin_token)
    check("revoke", s == 200)
    s, after = call("GET", "/api-keys", token=admin_token)
    check("key now revoked=True", after[0]["revoked"] is True)

    s, _ = call("DELETE", f"/api-keys/{key_id}", token=admin_token)
    check("delete returns 204", s == 204)
    s, gone = call("GET", "/api-keys", token=admin_token)
    check("list now empty again", len(gone) == 0)

    # An employee should NOT be able to create keys (developer/admin only)
    s, _ = call("POST", "/auth/register", {"email": "bob@example.com", "full_name": "Bob", "password": "bob12345"})
    s, bob_login = call("POST", "/auth/login", {"email": "bob@example.com", "password": "bob12345"})
    bob_token = bob_login["access_token"]
    s, _ = call("POST", "/api-keys", {"name": "Trying"}, token=bob_token)
    check("employee Bob forbidden from creating keys", s == 403, f"status={s}")

    print("\n== Password reset ==")
    s, resp = call("POST", "/auth/password-reset/request", {"email": "bob@example.com"})
    check("request returns 200", s == 200, f"status={s}")
    check("dev_token returned (no SMTP)", isinstance(resp.get("dev_token"), str) and len(resp["dev_token"]) > 20)
    reset_token = resp["dev_token"]

    # Wrong (but well-formed) token
    bogus = "a" * 40
    s, _ = call("POST", "/auth/password-reset/confirm", {"token": bogus, "new_password": "newpass1234"})
    check("invalid token rejected", s == 400, f"status={s}")

    # Real token
    s, _ = call("POST", "/auth/password-reset/confirm", {"token": reset_token, "new_password": "newbobpass1234"})
    check("valid token accepted", s == 204)

    # New password works
    s, _ = call("POST", "/auth/login", {"email": "bob@example.com", "password": "newbobpass1234"})
    check("new password works", s == 200)

    # Old password rejected
    s, _ = call("POST", "/auth/login", {"email": "bob@example.com", "password": "bob12345"})
    check("old password rejected", s == 401)

    # Token cannot be reused
    s, _ = call("POST", "/auth/password-reset/confirm", {"token": reset_token, "new_password": "tryagain12345"})
    check("token cannot be reused", s == 400)

    # Unknown email still 200 (no enumeration)
    s, resp = call("POST", "/auth/password-reset/request", {"email": "nobody@example.com"})
    check("unknown email also returns 200", s == 200)
    check("unknown email gets no dev_token", resp.get("dev_token") is None)

    print("\n== Email verification ==")
    s, resp = call("POST", "/auth/verify-email/request", {"email": "bob@example.com"})
    check("request 200", s == 200)
    check("dev_token returned", isinstance(resp.get("dev_token"), str))
    verify_token = resp["dev_token"]

    s, _ = call("POST", "/auth/verify-email/confirm", {"token": verify_token})
    check("verify confirmed", s == 204)

    # Bob's profile should now reflect is_verified
    s, bob_login2 = call("POST", "/auth/login", {"email": "bob@example.com", "password": "newbobpass1234"})
    s, me = call("GET", "/auth/me", token=bob_login2["access_token"])
    check("bob is now verified", me.get("is_verified") is True, f"got={me.get('is_verified')}")

    # Verified user requesting a new token gets no dev_token (already verified)
    s, resp = call("POST", "/auth/verify-email/request", {"email": "bob@example.com"})
    check("re-request for verified user has no dev_token", resp.get("dev_token") is None)

    print("\n== Department members ==")
    s, depts = call("GET", "/departments", token=admin_token)
    check("departments seeded", s == 200 and len(depts) >= 4)
    eng = next(d for d in depts if d["name"] == "Engineering")

    # Find bob's id
    s, users = call("GET", "/users", token=admin_token)
    bob = next(u for u in users if u["email"] == "bob@example.com")

    s, _ = call("POST", f"/departments/{eng['id']}/members/{bob['id']}", token=admin_token)
    check("add bob to engineering", s == 200)

    s, members = call("GET", f"/departments/{eng['id']}/members", token=admin_token)
    check("members list contains bob", any(m["id"] == bob["id"] for m in members))

    s, me = call("GET", "/auth/me", token=bob_login2["access_token"])
    check("bob.department_id is now eng.id", me.get("department_id") == eng["id"])

    s, _ = call("DELETE", f"/departments/{eng['id']}/members/{bob['id']}", token=admin_token)
    check("remove bob from engineering", s == 204)
    s, members2 = call("GET", f"/departments/{eng['id']}/members", token=admin_token)
    check("members list no longer contains bob", not any(m["id"] == bob["id"] for m in members2))

    print(f"\n========================================")
    print(f"  Total failures: {failures}")
    print(f"========================================")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
