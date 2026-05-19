"""
Shared pytest fixtures.

Every test gets an isolated, in-memory SQLite DB so they don't interfere with
each other and can run in parallel.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Configure the test environment BEFORE app imports.
# DATABASE_URL must be set first so the engine in app.database is built against
# the test-scoped DB rather than touching the real data/enterprisecore.db file.
os.environ["DATABASE_URL"] = "sqlite:///./data/test_enterprisecore.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-at-least-16-chars"
os.environ["FIRST_ADMIN_EMAIL"] = "admin@test.io"
os.environ["FIRST_ADMIN_PASSWORD"] = "Admin123!"
# Tests can hammer auth endpoints; disable in-process throttles.
os.environ["RATE_LIMIT_DISABLED"] = "1"

# Wipe any stale test DB from a previous run BEFORE app.database is imported.
# This ensures init_db() in the lifespan starts from an empty file and creates
# tables with the latest schema (Base.metadata.create_all does NOT alter
# existing tables).
import pathlib
_test_db = pathlib.Path(__file__).resolve().parent.parent / "data" / "test_enterprisecore.db"
if _test_db.exists():
    try:
        _test_db.unlink()
    except OSError:
        pass

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.bootstrap import seed  # noqa: E402


@pytest.fixture
def db_session():
    """Fresh in-memory DB per test, with seed run."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = SessionLocal()
    seed(db)
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    """TestClient with the DB dependency overridden to the per-test session."""
    def _get_db_override():
        try:
            yield db_session
        finally:
            pass  # don't close — the fixture owns it

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(client) -> str:
    """An access token for the seeded admin."""
    r = client.post("/api/v1/auth/login", json={"email": "admin@test.io", "password": "Admin123!"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def employee_token(client) -> str:
    """A freshly-registered Employee token."""
    client.post("/api/v1/auth/register", json={
        "email": "emp@test.io", "full_name": "Employee", "password": "emp12345"
    })
    r = client.post("/api/v1/auth/login", json={"email": "emp@test.io", "password": "emp12345"})
    return r.json()["access_token"]


@pytest.fixture
def employee_headers(employee_token) -> dict:
    return {"Authorization": f"Bearer {employee_token}"}
