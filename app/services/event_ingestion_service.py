from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import EventRecord
from app.processing.event_normalizer import EventNormalizer
from app.repositories.event_repository import EventRepository
from app.repositories.processor_result_repository import ProcessorResultRepository
from app.schemas.events import EventBatchCreate, EventCreate
from app.services.analytics_service import AnalyticsService
from app.services.processors.base_processor import BaseProcessor, ProcessingContext

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestResult:
    """Outcome of ingesting one event (single or batch item)."""

    record: EventRecord
    newly_created: bool


class EventIngestionService:
    """
    Core ingestion pipeline (explicit order):

    1. Validate + normalize inbound payload (Pydantic + ``EventNormalizer``).
    2. Idempotency: when ``idempotency_key`` is set, insert under a savepoint; on unique
       violation, return the existing row (no duplicate rows under concurrency).
    3. Persist the event (``INSERT``).
    4. Run registered processors (counters, optional domain extensions, …) and persist
       each ``ProcessorResult`` to ``event_processor_results``.
    5. Invalidate read-side analytics cache (aggregates are recomputed on next query).

    Pairwise scoring and other optional processors must not be required for steps 1–3.
    """

    def __init__(
        self,
        session: Session,
        *,
        user_id: Optional[int],
        processors: Sequence[BaseProcessor],
        analytics: Optional[AnalyticsService] = None,
        redis_client=None,
    ) -> None:
        self._session = session
        self._repo = EventRepository(session)
        self._proc_results = ProcessorResultRepository(session)
        self._user_id = user_id
        self._processors = list(processors)
        self._analytics = analytics
        self._redis = redis_client

    def ingest_one(
        self,
        data: EventCreate,
        *,
        defer_cache_invalidation: bool = False,
    ) -> IngestResult:
        event_type, source, payload, occurred_at = EventNormalizer.normalize(data)

        row, created = self._repo.insert(
            event_type=event_type,
            source=source,
            payload=payload,
            occurred_at=occurred_at,
            user_id=self._user_id,
            idempotency_key=data.idempotency_key,
        )
        if created:
            self._run_processors(row)
            if self._analytics is not None and not defer_cache_invalidation:
                settings = get_settings()
                if settings.celery_broker_url:
                    import app.workers.celery_app  # noqa: F401  # registers default Celery app
                    from app.workers.tasks import post_ingestion_analytics_task

                    post_ingestion_analytics_task.delay()
                    logger.info(
                        "enqueued post_ingestion_analytics_task",
                        extra={"event_id": row.id, "component": "ingestion"},
                    )
                else:
                    self._analytics.invalidate_cache()
        elif data.idempotency_key:
            logger.info(
                "idempotent replay event_id=%s key=%s",
                row.id,
                data.idempotency_key,
                extra={"component": "ingestion", "deduplicated": True},
            )

        return IngestResult(record=row, newly_created=created)

    def ingest_batch(self, batch: EventBatchCreate) -> List[IngestResult]:
        out: List[IngestResult] = []
        n = len(batch.events)
        for i, item in enumerate(batch.events):
            last = i == n - 1
            out.append(self.ingest_one(item, defer_cache_invalidation=not last))
        return out

    def _run_processors(self, row: EventRecord) -> None:
        ctx = ProcessingContext(
            event=row,
            session=self._session,
            redis_client=self._redis,
        )
        for proc in self._processors:
            if not proc.should_process(ctx):
                continue
            try:
                result = proc.process(ctx)
            except Exception as exc:  # noqa: BLE001
                logger.exception("processor %s failed", proc.name)
                self._proc_results.save(
                    event_id=row.id,
                    processor_name=proc.name,
                    skipped=True,
                    output={},
                    message=str(exc),
                )
                continue
            self._proc_results.save(
                event_id=row.id,
                processor_name=result.processor_name,
                skipped=result.skipped,
                output=result.output or {},
                message=result.message,
            )
