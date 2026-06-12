"""SQLAlchemy database engine and session setup for ChronoCare AI.

Defaults to SQLite (zero-config local development). Switch to PostgreSQL
by setting DATABASE_URL in the environment or .env file.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./chronocare.db")

# SQLite needs check_same_thread=False; PostgreSQL does not
_connect_args: dict[str, Any] = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
    echo=False,
)

# Enable WAL mode for better SQLite concurrency
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection: Any, _: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


# Allow `with SessionLocal() as db:` syntax
Session.__enter__ = lambda self: self  # type: ignore[attr-defined]
Session.__exit__ = lambda self, *_: self.close()  # type: ignore[attr-defined]


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency – yields a DB session, guaranteeing cleanup."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables (idempotent)."""
    # Import models so their metadata is registered before create_all
    from app.db import orm_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database initialised at: %s", DATABASE_URL)


def health_check() -> bool:
    """Return True if the DB is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("DB health check failed: %s", exc)
        return False
