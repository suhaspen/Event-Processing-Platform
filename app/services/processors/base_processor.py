from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import redis
from sqlalchemy.orm import Session

from app.db.models import EventRecord


@dataclass
class ProcessingContext:
    """
    Everything a processor needs after the event row exists in the DB (post-flush).
    """

    event: EventRecord
    session: Session
    redis_client: Optional[redis.Redis] = None


@dataclass
class ProcessorResult:
    """Outcome of one processor execution (persisted to ``event_processor_results``)."""

    processor_name: str
    skipped: bool = False
    output: Dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None


class BaseProcessor(ABC):
    """
    Pluggable unit of work triggered after an event is stored.

    Implementations should be side-effect safe when ``should_process`` is false.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier stored with persisted outputs."""

    def should_process(self, ctx: ProcessingContext) -> bool:
        return True

    @abstractmethod
    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """Execute logic; return structured output for auditing / downstream use."""
