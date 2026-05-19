"""Rate limiting (currently disabled in test env, but ensure config-driven behaviour)."""

import importlib
import os


def test_limiter_disabled_in_tests():
    """conftest sets RATE_LIMIT_DISABLED=1, so the limiter should be inactive."""
    from app.core import rate_limit
    importlib.reload(rate_limit)
    assert rate_limit.limiter.enabled is False


def test_login_not_throttled_in_test_env(client):
    """If we hammer login, all attempts should resolve (right or wrong) — not 429."""
    for _ in range(20):
        r = client.post("/api/v1/auth/login", json={"email": "admin@test.io", "password": "Admin123!"})
        assert r.status_code in (200, 401), f"got {r.status_code}"
