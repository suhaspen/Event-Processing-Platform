from __future__ import annotations

import logging

import redis
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(redis.RedisError, ConnectionError, OSError),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=5,
    name="app.workers.tasks.post_ingestion_analytics_task",
)
def post_ingestion_analytics_task(self) -> str:
    """
    Invalidate analytics cache and pre-warm configured windows after new events.

    Retries on Redis / broker I/O failures with exponential backoff.
    """
    from app.services.analytics_service import run_post_ingestion_analytics_maintenance

    logger.info(
        "celery task post_ingestion_analytics started",
        extra={"component": "celery", "task_id": self.request.id},
    )
    try:
        run_post_ingestion_analytics_maintenance()
    except Exception as exc:
        logger.exception(
            "celery task post_ingestion_analytics failed: %s",
            exc,
            extra={"component": "celery", "task_id": self.request.id},
        )
        raise
    logger.info(
        "celery task post_ingestion_analytics finished",
        extra={"component": "celery", "task_id": self.request.id},
    )
    return "ok"
