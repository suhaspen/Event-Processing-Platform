from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, func, literal, text

from app.db.session import Base

# Sentinel for UNIQUE index: real user ids are positive FKs; NULL user_id maps here.
_IDEMPOTENCY_USER_SCOPE_SENTINEL = -1


class EventRecord(Base):
    """
    Append-only domain event stored for processing and analytics.

    Idempotency: partial UNIQUE on (COALESCE(user_id, -1), idempotency_key) when key is set,
    so concurrent inserts dedupe at the database (see ``EventRepository.insert``).
    """

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(128), nullable=False, index=True)
    source = Column(String(256), nullable=True, index=True)
    payload = Column(JSON, nullable=False)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    idempotency_key = Column(String(128), nullable=True, index=True)

    __table_args__ = (
        Index(
            "ux_events_user_idem_scope",
            func.coalesce(user_id, literal(_IDEMPOTENCY_USER_SCOPE_SENTINEL)),
            idempotency_key,
            unique=True,
            sqlite_where=text("idempotency_key IS NOT NULL"),
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )


class EventProcessorResult(Base):
    """Persisted output of a processor run for a single event (audit / downstream reads)."""

    __tablename__ = "event_processor_results"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    processor_name = Column(String(64), nullable=False, index=True)
    skipped = Column(Boolean, default=False, nullable=False)
    output_json = Column(JSON, nullable=False)
    message = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AnalyticsSnapshotRecord(Base):
    """
    Persisted materialization of a computed analytics view (audit + cold recovery).

    Written when aggregates are computed on a cache miss, in addition to Redis caching.
    """

    __tablename__ = "analytics_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_kind = Column(String(32), nullable=False, index=True)
    window_hours = Column(Float, nullable=False)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    total_events = Column(Integer, nullable=True)
    unique_event_types = Column(Integer, nullable=True)
    counts_by_type = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
