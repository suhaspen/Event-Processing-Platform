from __future__ import annotations

import importlib
import os
from typing import Generator

# Pytest runs without Redis; readiness must not hard-fail CI.
os.environ.setdefault("READINESS_REQUIRE_REDIS", "false")

import pytest
from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.db.session import Base, get_db
from app.main import app
from app.services.analytics_service import AnalyticsService


@pytest.fixture(autouse=True)
def _test_app_db() -> Generator[None, None, None]:
    # Single shared in-memory DB for all connections (default :memory: is per-connection).
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Register ORM models without `import app.*` (would shadow `app` below).
    importlib.import_module("app.db.models")
    importlib.import_module("app.models.user")

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine, future=True
    )

    def _get_db() -> Generator[Session, None, None]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def _noop_rate_limit() -> None:
        return None

    def _noop_auth_rate_limit() -> None:
        return None

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[deps.rate_limiter] = _noop_rate_limit
    app.dependency_overrides[deps.auth_rate_limiter] = _noop_auth_rate_limit

    class _FakeUser:
        id = None
        email = "tester@example.com"
        is_active = True

    app.dependency_overrides[deps.get_current_api_user] = lambda: _FakeUser()

    def _analytics(db: Session = Depends(get_db)) -> AnalyticsService:
        return AnalyticsService(db, redis_client=None)

    app.dependency_overrides[deps.get_analytics_service] = _analytics
    app.dependency_overrides[deps.get_processor_chain] = lambda: []
    app.dependency_overrides[deps.get_redis_optional] = lambda: None

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def client():
    """HTTP client against the app (uses ``_test_app_db`` overrides)."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
