"""pytest configuration and shared fixtures for ChronoCare AI tests."""
from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# ── Must set env vars BEFORE any app module is imported ──────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")       # disable Redis in tests
os.environ.setdefault("LOG_LEVEL", "WARNING")

# Import after env vars are set
from app.db import database as _db_module  # noqa: E402
from app.db import orm_models  # noqa: F401, E402  – registers table metadata

# Patch the engine to use StaticPool so all sessions share the same in-memory DB
_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_db_module.engine = _test_engine
_db_module.SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=_test_engine, class_=Session
)
# Restore context-manager support on the patched SessionLocal
Session.__enter__ = lambda self: self  # type: ignore[attr-defined]
Session.__exit__ = lambda self, *_: self.close()  # type: ignore[attr-defined]


@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    """Create all tables once per test session in the shared in-memory DB."""
    from app.db.database import Base
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture
def client():
    """FastAPI TestClient with models loaded."""
    from app.ml.models import load_models
    load_models()
    from app.main import app
    with TestClient(app) as c:
        yield c
