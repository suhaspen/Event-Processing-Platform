from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import EventRecord


class EventRepository:
    """PostgreSQL-backed access for event records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_idempotency(
        self,
        *,
        user_id: Optional[int],
        idempotency_key: str,
    ) -> Optional[EventRecord]:
        q = select(EventRecord).where(EventRecord.idempotency_key == idempotency_key)
        if user_id is not None:
            q = q.where(EventRecord.user_id == user_id)
        else:
            q = q.where(EventRecord.user_id.is_(None))
        return self._session.scalars(q).first()

    def insert(
        self,
        *,
        event_type: str,
        source: Optional[str],
        payload: dict,
        occurred_at: datetime,
        user_id: Optional[int],
        idempotency_key: Optional[str] = None,
    ) -> Tuple[EventRecord, bool]:
        """
        Persist a new event.

        When ``idempotency_key`` is set, uses a savepoint + flush so a uniqueness violation
        yields the existing row (``created`` False) without aborting the outer transaction.

        Returns:
            (row, created) — ``created`` is False when this is a duplicate idempotency key.
        """
        row = EventRecord(
            event_type=event_type,
            source=source,
            payload=payload,
            occurred_at=occurred_at,
            user_id=user_id,
            idempotency_key=idempotency_key,
        )

        if not idempotency_key:
            self._session.add(row)
            self._session.flush()
            return row, True

        try:
            with self._session.begin_nested():
                self._session.add(row)
                self._session.flush()
        except IntegrityError:
            # Savepoint rolled back; ``row`` may no longer be attached — do not expunge.
            existing = self.find_by_idempotency(
                user_id=user_id,
                idempotency_key=idempotency_key,
            )
            if existing is None:
                raise
            return existing, False

        return row, True

    def insert_many(
        self,
        rows: Sequence[
            Tuple[str, Optional[str], dict, datetime, Optional[int], Optional[str]]
        ],
    ) -> List[Tuple[EventRecord, bool]]:
        out: List[Tuple[EventRecord, bool]] = []
        for event_type, source, payload, occurred_at, user_id, idem in rows:
            out.append(
                self.insert(
                    event_type=event_type,
                    source=source,
                    payload=payload,
                    occurred_at=occurred_at,
                    user_id=user_id,
                    idempotency_key=idem,
                )
            )
        return out

    def get_by_id(self, event_id: int) -> Optional[EventRecord]:
        return self._session.get(EventRecord, event_id)

    def list_events(
        self,
        *,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[EventRecord], int]:
        base = select(EventRecord)
        count_base = select(func.count()).select_from(EventRecord)
        filters = []
        if event_type:
            filters.append(EventRecord.event_type == event_type)
        if source:
            filters.append(EventRecord.source == source)
        if since:
            filters.append(EventRecord.occurred_at >= since)
        if until:
            filters.append(EventRecord.occurred_at <= until)
        for f in filters:
            base = base.where(f)
            count_base = count_base.where(f)
        total = int(self._session.scalar(count_base) or 0)
        stmt = (
            base.order_by(EventRecord.occurred_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(self._session.scalars(stmt).all())
        return items, total

    def count_since(self, since: datetime) -> int:
        q = select(func.count()).select_from(EventRecord).where(
            EventRecord.occurred_at >= since
        )
        return int(self._session.scalar(q) or 0)

    def aggregate_counts_by_type(
        self, since: datetime
    ) -> List[Tuple[str, int]]:
        stmt = (
            select(EventRecord.event_type, func.count(EventRecord.id))
            .where(EventRecord.occurred_at >= since)
            .group_by(EventRecord.event_type)
            .order_by(func.count(EventRecord.id).desc())
        )
        return list(self._session.execute(stmt).all())

    def count_all(self) -> int:
        q = select(func.count()).select_from(EventRecord)
        return int(self._session.scalar(q) or 0)
