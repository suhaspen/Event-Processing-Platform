from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DBSessionDep
from app.api.middleware import HTTP_REQUESTS_REDIS_KEY
from app.core.config import get_settings
from app.repositories.event_repository import EventRepository
from app.schemas.analytics import SystemMetrics
from app.services.processors.analytics_rollup_processor import EVENTS_INGESTED_KEY
from app.services.redis_client import get_redis_client

router = APIRouter(tags=["system"])


def _redis_int(key: str) -> Optional[int]:
    try:
        r = get_redis_client()
        v = r.get(key)
        if v is None:
            return None
        return int(v)
    except Exception:
        return None


def _check_database(db) -> bool:
    try:
        db.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


def _check_redis() -> bool:
    try:
        get_redis_client().ping()
        return True
    except Exception:
        return False


@router.get("/health/live")
def health_live() -> dict[str, Any]:
    """Liveness: process is running (for orchestrators)."""
    return {"status": "alive", "service": "event-platform"}


@router.get("/health/ready")
def health_ready(response: Response, db: DBSessionDep) -> dict[str, Any]:
    """
    Readiness: dependencies required for full API behavior.

    Returns 503 when the database is down, or when Redis is required but unreachable.
    """
    settings = get_settings()
    db_ok = _check_database(db)
    redis_ok = _check_redis()
    ready = db_ok and (redis_ok or not settings.readiness_require_redis)
    body: dict[str, Any] = {
        "status": "ready" if ready else "not_ready",
        "database_connected": db_ok,
        "redis_connected": redis_ok,
        "readiness_require_redis": settings.readiness_require_redis,
    }
    if not ready:
        response.status_code = 503
    return body


@router.get("/health")
def health_check(db: DBSessionDep) -> dict[str, Any]:
    """
    Informational probe: process is up (status \"ok\") with dependency flags.
    Prefer /health/live + /health/ready for orchestrators.
    """
    db_ok = _check_database(db)
    redis_ok = _check_redis()
    return {
        "status": "ok",
        "database_connected": db_ok,
        "redis_connected": redis_ok,
    }


@router.get("/metrics", response_model=SystemMetrics)
def system_metrics(db: DBSessionDep) -> SystemMetrics:
    settings = get_settings()
    repo = EventRepository(db)
    total = repo.count_all()
    redis_ok = _check_redis()
    http_total = _redis_int(HTTP_REQUESTS_REDIS_KEY) if redis_ok else None
    ingest_total = _redis_int(EVENTS_INGESTED_KEY) if redis_ok else None
    return SystemMetrics(
        events_total=total,
        redis_connected=redis_ok,
        cache_ttl_seconds=settings.analytics_cache_ttl_seconds,
        http_requests_total=http_total,
        events_ingested_counter=ingest_total,
    )
