from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventCreate(BaseModel):
    """Inbound event for ingestion (single)."""

    event_type: str = Field(..., min_length=1, max_length=128)
    source: Optional[str] = Field(default=None, max_length=256)
    payload: Dict[str, Any] = Field(default_factory=dict)
    occurred_at: Optional[datetime] = None
    idempotency_key: Optional[str] = Field(
        default=None,
        max_length=128,
        description="If set, duplicate submissions with the same key return the original event.",
    )

    @field_validator("event_type")
    @classmethod
    def event_type_slug(cls, value: str) -> str:
        v = value.strip()
        if not v:
            raise ValueError("event_type must be non-empty")
        return v

    @field_validator("idempotency_key")
    @classmethod
    def idempotency_trim(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        t = value.strip()
        return t or None


class EventBatchCreate(BaseModel):
    """Batch ingestion (bounded)."""

    events: List[EventCreate] = Field(..., min_length=1, max_length=500)


class ProcessorOutputOut(BaseModel):
    """One processor run persisted for an event."""

    processor_name: str
    skipped: bool
    output: Dict[str, Any]
    message: Optional[str] = None
    created_at: datetime


class EventOut(BaseModel):
    """Stored event returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    source: Optional[str]
    payload: Dict[str, Any]
    occurred_at: datetime
    created_at: datetime
    user_id: Optional[int]
    idempotency_key: Optional[str] = None
    deduplicated: bool = Field(
        default=False,
        description="True when this response replayed an existing idempotency key.",
    )
    processor_outputs: List[ProcessorOutputOut] = Field(default_factory=list)


class EventListResponse(BaseModel):
    items: List[EventOut]
    total: int
    limit: int
    offset: int


class EventBatchOut(BaseModel):
    items: List[EventOut]
    count: int
    created_count: int = Field(
        ...,
        description="Items that resulted in a new persisted row this request.",
    )
    deduplicated_count: int = Field(
        ...,
        description="Items that matched an existing idempotency key (no new row).",
    )
