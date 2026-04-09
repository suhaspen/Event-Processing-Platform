from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TypeCount(BaseModel):
    event_type: str
    count: int


class AnalyticsSummary(BaseModel):
    """Roll-up metrics for a time window."""

    window_hours: float = Field(..., description="Lookback window in hours")
    total_events: int
    unique_event_types: int
    counts_by_type: List[TypeCount]
    window_start: datetime
    window_end: datetime
    cached: bool = False


class AnalyticsByType(BaseModel):
    window_hours: float
    counts_by_type: List[TypeCount]
    window_start: datetime
    window_end: datetime
    cached: bool = False


class SystemMetrics(BaseModel):
    """Operational counters for dashboards / probes."""

    events_total: int
    redis_connected: bool
    cache_ttl_seconds: int
    http_requests_total: Optional[int] = Field(
        default=None,
        description="From Redis when available (see RequestContextMiddleware).",
    )
    events_ingested_counter: Optional[int] = Field(
        default=None,
        description="From Redis ingestion processor when available.",
    )


class AnalyticsSnapshotOut(BaseModel):
    """Stored aggregate snapshot (written on analytics cache miss)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    snapshot_kind: str
    window_hours: float
    window_start: datetime
    window_end: datetime
    total_events: int | None
    unique_event_types: int | None
    counts_by_type: List[Dict[str, Any]]
    created_at: datetime


class AnalyticsSnapshotListResponse(BaseModel):
    items: List[AnalyticsSnapshotOut]
