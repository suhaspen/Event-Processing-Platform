from __future__ import annotations

from typing import Sequence

from sqlalchemy.orm import Session

from app.db.models import AnalyticsSnapshotRecord
from app.schemas.analytics import AnalyticsByType, AnalyticsSummary


class AnalyticsSnapshotRepository:
    """Persistence for computed analytics roll-ups (append-only snapshots)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save_from_summary(self, summary: AnalyticsSummary) -> AnalyticsSnapshotRecord:
        row = AnalyticsSnapshotRecord(
            snapshot_kind="summary",
            window_hours=summary.window_hours,
            window_start=summary.window_start,
            window_end=summary.window_end,
            total_events=summary.total_events,
            unique_event_types=summary.unique_event_types,
            counts_by_type=[c.model_dump() for c in summary.counts_by_type],
        )
        self._session.add(row)
        return row

    def save_from_by_type(self, data: AnalyticsByType) -> AnalyticsSnapshotRecord:
        row = AnalyticsSnapshotRecord(
            snapshot_kind="by_type",
            window_hours=data.window_hours,
            window_start=data.window_start,
            window_end=data.window_end,
            total_events=None,
            unique_event_types=None,
            counts_by_type=[c.model_dump() for c in data.counts_by_type],
        )
        self._session.add(row)
        return row

    def list_recent(self, *, limit: int = 50) -> Sequence[AnalyticsSnapshotRecord]:
        q = (
            self._session.query(AnalyticsSnapshotRecord)
            .order_by(AnalyticsSnapshotRecord.created_at.desc())
            .limit(limit)
        )
        return q.all()
