from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import EventProcessorResult


class ProcessorResultRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(
        self,
        *,
        event_id: int,
        processor_name: str,
        skipped: bool,
        output: Dict[str, Any],
        message: Optional[str] = None,
    ) -> EventProcessorResult:
        row = EventProcessorResult(
            event_id=event_id,
            processor_name=processor_name,
            skipped=skipped,
            output_json=output,
            message=message,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list_for_event(self, event_id: int) -> List[EventProcessorResult]:
        return (
            self._session.query(EventProcessorResult)
            .filter(EventProcessorResult.event_id == event_id)
            .order_by(EventProcessorResult.id.asc())
            .all()
        )
