from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from app.schemas.events import EventCreate


class EventNormalizer:
    """
    Normalizes inbound events before persistence.

    Keeps processing logic out of HTTP handlers and repositories.
    """

    @staticmethod
    def normalize(
        data: EventCreate,
        *,
        default_occurred_at: Optional[datetime] = None,
    ) -> Tuple[str, Optional[str], Dict[str, Any], datetime]:
        now = default_occurred_at or datetime.now(timezone.utc).replace(tzinfo=None)
        occurred = data.occurred_at or now
        if occurred.tzinfo is not None:
            occurred = occurred.replace(tzinfo=None)
        payload = dict(data.payload) if data.payload is not None else {}
        return (
            data.event_type.strip(),
            data.source.strip() if data.source else None,
            payload,
            occurred,
        )
