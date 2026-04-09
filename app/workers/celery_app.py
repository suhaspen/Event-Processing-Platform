from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()
broker = settings.celery_broker_url or settings.redis_url
backend = settings.celery_result_backend or settings.celery_broker_url or settings.redis_url

celery_app = Celery(
    "event_platform",
    broker=broker,
    backend=backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    task_time_limit=120,
    task_soft_time_limit=90,
    imports=("app.workers.tasks",),
)

celery_app.set_default()
