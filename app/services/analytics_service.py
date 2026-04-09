from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import List, Optional

import redis

from app.core.config import get_settings
from app.repositories.analytics_snapshot_repository import AnalyticsSnapshotRepository
from app.repositories.event_repository import EventRepository
from app.schemas.analytics import AnalyticsByType, AnalyticsSummary, TypeCount

logger = logging.getLogger(__name__)

_ANALYTICS_KEY_PREFIX = "analytics:"


def invalidate_analytics_cache_remote(client: redis.Redis) -> None:
    """
    Delete cached aggregate keys (used by API workers and Celery tasks).

    Raises redis.RedisError on failure so callers can retry.
    """
    for key in client.scan_iter(f"{_ANALYTICS_KEY_PREFIX}*"):
        client.delete(key)


def run_post_ingestion_analytics_maintenance() -> None:
    """
    Invalidate aggregates then pre-warm common windows (DB + Redis).

    Intended for Celery; uses a fresh DB session and shared Redis client.
    """
    from app.db.session import SessionLocal
    from app.services.redis_client import get_redis_client

    r = get_redis_client()
    invalidate_analytics_cache_remote(r)
    logger.info(
        "post_ingestion_analytics maintenance: cache invalidated",
        extra={"component": "analytics_maintenance"},
    )

    settings = get_settings()
    windows: list[float] = []
    for part in settings.analytics_prewarm_window_hours.split(","):
        p = part.strip()
        if not p:
            continue
        try:
            windows.append(float(p))
        except ValueError:
            logger.warning("skip invalid prewarm window: %r", p)

    db = SessionLocal()
    try:
        svc = AnalyticsService(db, redis_client=r)
        for wh in windows:
            svc.summary(wh)
            svc.by_type(wh)
            logger.info(
                "prewarmed analytics windows",
                extra={
                    "component": "analytics_maintenance",
                    "window_hours": wh,
                },
            )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "post_ingestion_analytics maintenance failed",
            extra={"component": "analytics_maintenance"},
        )
        raise
    finally:
        db.close()


class AnalyticsService:
    """
    Read-side analytics with Redis caching and PostgreSQL snapshot persistence
    for computed roll-ups (written on cache miss).
    """

    def __init__(
        self,
        session,
        *,
        redis_client: Optional[redis.Redis] = None,
    ) -> None:
        self._repo = EventRepository(session)
        self._snapshots = AnalyticsSnapshotRepository(session)
        self._redis = redis_client
        self._settings = get_settings()

    def _cache_get(self, key: str) -> str | None:
        if self._redis is None:
            return None
        try:
            return self._redis.get(key)
        except redis.RedisError as exc:
            logger.warning("redis get failed: %s", exc)
            return None

    def _cache_set(self, key: str, value: str) -> None:
        if self._redis is None:
            return
        try:
            self._redis.setex(
                key,
                self._settings.analytics_cache_ttl_seconds,
                value,
            )
        except redis.RedisError as exc:
            logger.warning("redis set failed: %s", exc)

    def _now(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def invalidate_cache(self) -> None:
        if self._redis is None:
            return
        try:
            invalidate_analytics_cache_remote(self._redis)
        except redis.RedisError as exc:
            logger.warning("redis invalidate failed: %s", exc)

    def summary(self, window_hours: float) -> AnalyticsSummary:
        cache_key = f"analytics:summary:{window_hours}"
        raw = self._cache_get(cache_key)
        if raw:
            data = AnalyticsSummary.model_validate_json(raw)
            return data.model_copy(update={"cached": True})

        end = self._now()
        start = end - timedelta(hours=window_hours)
        rows = self._repo.aggregate_counts_by_type(start)
        total = self._repo.count_since(start)
        counts: List[TypeCount] = [
            TypeCount(event_type=et, count=c) for et, c in rows
        ]
        out = AnalyticsSummary(
            window_hours=window_hours,
            total_events=total,
            unique_event_types=len(counts),
            counts_by_type=counts,
            window_start=start,
            window_end=end,
            cached=False,
        )
        self._snapshots.save_from_summary(out)
        logger.info(
            "analytics summary computed window_h=%s total=%s kinds=%s",
            window_hours,
            total,
            len(counts),
        )
        self._cache_set(cache_key, out.model_dump_json())
        return out

    def by_type(self, window_hours: float) -> AnalyticsByType:
        cache_key = f"analytics:by_type:{window_hours}"
        raw = self._cache_get(cache_key)
        if raw:
            data = AnalyticsByType.model_validate_json(raw)
            return data.model_copy(update={"cached": True})

        end = self._now()
        start = end - timedelta(hours=window_hours)
        rows = self._repo.aggregate_counts_by_type(start)
        counts = [TypeCount(event_type=et, count=c) for et, c in rows]
        out = AnalyticsByType(
            window_hours=window_hours,
            counts_by_type=counts,
            window_start=start,
            window_end=end,
            cached=False,
        )
        self._snapshots.save_from_by_type(out)
        logger.info(
            "analytics by_type computed window_h=%s kinds=%s",
            window_hours,
            len(counts),
        )
        self._cache_set(cache_key, out.model_dump_json())
        return out
