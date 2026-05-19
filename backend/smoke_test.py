"""End-to-end smoke test for the EnterpriseCore API."""

import json
import urllib.request
import urllib.error


BASE = "http://127.0.0.1:8000/api/v1"


def call(method: str, path: str, body=None, token: str | None = None) -> tuple[int, dict | str]:
    """Returns (status, json or text)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url=BASE + path,
        method=method,
        data=data,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            text = r.read().decode()
            try:
                return r.status, json.loads(text)
            except json.JSONDecodeError:
                return r.status, text
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main() -> int:
    failures = 0

    def check(label: str, ok: bool, info: str = ""):
        nonlocal failures
        mark = "[PASS]" if ok else "[FAIL]"
        print(f"  {mark}  {label}  {info}")
        if not ok:
            failures += 1

    print("== Health ==")
    s, r = call("GET", "/system/health")
    check("GET /system/health", s == 200 and isinstance(r, dict) and r.get("status") == "ok")

    print("\n== Auth ==")
    s, r = call("POST", "/auth/login", {"email": "admin@enterprisecore.io", "password": "Admin123!"})
    check("admin login", s == 200, f"status={s}")
    access = r["access_token"]
    refresh = r["refresh_token"]
    check("got access token", bool(access) and access.count(".") == 2)
    check("got refresh token", bool(refresh) and refresh.count(".") == 2)

    print("\n== Identity ==")
    s, me = call("GET", "/auth/me", token=access)
    check("GET /auth/me", s == 200, f"status={s}")
    check("admin role correct", me.get("role") == "admin", f"role={me.get('role')}")

    print("\n== Dashboard ==")
    s, d = call("GET", "/system/dashboard", token=access)
    check("GET /system/dashboard", s == 200)
    check("dashboard has users.total", "users" in d and "total" in d["users"], str(d))

    print("\n== Register employee ==")
    s, alice = call("POST", "/auth/register", {"email": "alice@example.com", "full_name": "Alice", "password": "alice12345"})
    check("register alice", s in (200, 201, 409), f"status={s}")
    if s == 201:
        check("alice starts as employee", alice.get("role") == "employee", str(alice))
        alice_id = alice["id"]
    else:
        # Already exists from a previous run
        s2, listed = call("GET", "/users", token=access)
        alice_id = next((u["id"] for u in listed if u["email"] == "alice@example.com"), None)
        check("found existing alice", alice_id is not None)

    print("\n== Admin promotes alice ==")
    s, alice2 = call("PATCH", f"/users/{alice_id}", {"role": "manager"}, token=access)
    check("promote alice to manager", s == 200 and alice2.get("role") == "manager", f"status={s}")

    print("\n== Departments seeded ==")
    s, depts = call("GET", "/departments", token=access)
    check("GET /departments", s == 200)
    check("4 default departments", isinstance(depts, list) and len(depts) >= 4, f"got {len(depts) if isinstance(depts, list) else 'n/a'}")

    print("\n== Broadcast notification ==")
    s, br = call("POST", "/notifications/broadcast", {
        "user_id": 0, "type": "system", "title": "Welcome", "message": "System live."
    }, token=access)
    check("broadcast", s == 200 and br.get("sent", 0) >= 1, str(br))

    print("\n== Unread count for admin ==")
    s, u = call("GET", "/notifications/unread-count", token=access)
    check("admin has unread", s == 200 and u.get("count", 0) >= 1, str(u))

    print("\n== Alice cannot list users ==")
    s, alice_login = call("POST", "/auth/login", {"email": "alice@example.com", "password": "alice12345"})
    check("alice login", s == 200, f"status={s}")
    alice_token = alice_login["access_token"]
    s, _ = call("GET", "/users", token=alice_token)
    check("alice forbidden from /users (manager, not admin)", s == 403, f"status={s}")

    print("\n== Audit log captured login + register + promotion ==")
    s, audit = call("GET", "/audit", token=access)
    check("GET /audit", s == 200)
    actions = {a["action"] for a in audit} if isinstance(audit, list) else set()
    for required in ("auth.login", "user.register", "user.admin_update"):
        check(f"audit contains {required}", required in actions, f"have={sorted(actions)}")

    print("\n== Refresh flow ==")
    s, ref = call("POST", "/auth/refresh", {"refresh_token": refresh})
    check("refresh succeeded", s == 200 and "access_token" in ref, f"status={s}")

    print("\n== Logout revokes refresh ==")
    s, _ = call("POST", "/auth/logout", {"refresh_token": refresh})
    check("logout returns 204", s == 204, f"status={s}")
    s, _ = call("POST", "/auth/refresh", {"refresh_token": refresh})
    check("refresh now rejected", s == 401, f"status={s}")

    print(f"\n========================================")
    print(f"  Total failures: {failures}")
    print(f"========================================")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
