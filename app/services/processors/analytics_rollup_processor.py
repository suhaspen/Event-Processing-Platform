from __future__ import annotations

import logging
from typing import Optional

import redis

from app.services.processors.base_processor import (
    BaseProcessor,
    ProcessingContext,
    ProcessorResult,
)

logger = logging.getLogger(__name__)

EVENTS_INGESTED_KEY = "platform:events_ingested_total"
BY_TYPE_PREFIX = "platform:events_by_type:"


class AnalyticsRollupProcessor(BaseProcessor):
    """
    Lightweight ingestion-side counters for observability (Redis).

    This is not a substitute for read-time aggregate APIs; it feeds ``/metrics``.
    """

    @property
    def name(self) -> str:
        return "ingestion_counters"

    def should_process(self, ctx: ProcessingContext) -> bool:
        return ctx.redis_client is not None

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        r: Optional[redis.Redis] = ctx.redis_client
        if r is None:
            return ProcessorResult(
                processor_name=self.name,
                skipped=True,
                message="no redis client",
            )
        try:
            r.incr(EVENTS_INGESTED_KEY)
            r.incr(f"{BY_TYPE_PREFIX}{ctx.event.event_type}")
        except redis.RedisError as exc:
            logger.warning("ingestion counter redis error: %s", exc)
            return ProcessorResult(
                processor_name=self.name,
                skipped=True,
                message=str(exc),
            )
        return ProcessorResult(
            processor_name=self.name,
            skipped=False,
            output={
                "events_ingested_key": EVENTS_INGESTED_KEY,
                "event_type": ctx.event.event_type,
            },
        )
