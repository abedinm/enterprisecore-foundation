"""
SQLAlchemy engine + session factory + declarative Base.

The DB lives at backend/data/enterprisecore.db by default.
Use the `get_db` dependency in route handlers to obtain a session.
"""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

from app.config import settings, BASE_DIR


# Ensure the data directory exists for SQLite file storage.
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

# SQLite needs `check_same_thread=False` to be used across FastAPI's thread pool.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and ensures it's closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Create all tables. Imports the models module so that all model classes
    are registered against `Base.metadata` before create_all runs.
    """
    from app import models  # noqa: F401  (side-effect: registers models)
    Base.metadata.create_all(bind=engine)
