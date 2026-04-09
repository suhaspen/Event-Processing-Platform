from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Security, status

from app.api.deps import (
    APIKeyHeaderDep,
    DBSessionDep,
    get_analytics_service,
    get_current_api_user,
    get_processor_chain,
    get_redis_optional,
    rate_limiter,
)
from app.models.user import User
from app.repositories.event_repository import EventRepository
from app.repositories.processor_result_repository import ProcessorResultRepository
from app.schemas.events import (
    EventBatchCreate,
    EventBatchOut,
    EventCreate,
    EventListResponse,
    EventOut,
    ProcessorOutputOut,
)
from app.services.analytics_service import AnalyticsService
from app.services.event_ingestion_service import EventIngestionService
from app.services.processors.base_processor import BaseProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


def _event_to_out(
    row,
    *,
    include_processor_outputs: bool,
    db,
    deduplicated: bool = False,
) -> EventOut:
    outputs: List[ProcessorOutputOut] = []
    if include_processor_outputs:
        repo = ProcessorResultRepository(db)
        for r in repo.list_for_event(row.id):
            outputs.append(
                ProcessorOutputOut(
                    processor_name=r.processor_name,
                    skipped=r.skipped,
                    output=r.output_json,
                    message=r.message,
                    created_at=r.created_at,
                )
            )
    base = EventOut.model_validate(row)
    return base.model_copy(
        update={"processor_outputs": outputs, "deduplicated": deduplicated},
    )


@router.post(
    "",
    response_model=EventOut,
    dependencies=[Depends(rate_limiter)],
)
def ingest_event(
    body: EventCreate,
    db: DBSessionDep,
    api_key: str = Security(APIKeyHeaderDep),
    user: User = Depends(get_current_api_user),
    analytics: AnalyticsService = Depends(get_analytics_service),
    processors: List[BaseProcessor] = Depends(get_processor_chain),
    redis_client=Depends(get_redis_optional),
) -> EventOut:
    service = EventIngestionService(
        db,
        user_id=user.id,
        processors=processors,
        analytics=analytics,
        redis_client=redis_client,
    )
    result = service.ingest_one(body)
    row = result.record
    db.commit()
    db.refresh(row)
    logger.info(
        "ingested event id=%s type=%s user_id=%s created=%s",
        row.id,
        row.event_type,
        user.id,
        result.newly_created,
    )
    return _event_to_out(
        row,
        include_processor_outputs=True,
        db=db,
        deduplicated=not result.newly_created,
    )


@router.post(
    "/batch",
    response_model=EventBatchOut,
    dependencies=[Depends(rate_limiter)],
)
def ingest_events_batch(
    body: EventBatchCreate,
    db: DBSessionDep,
    api_key: str = Security(APIKeyHeaderDep),
    user: User = Depends(get_current_api_user),
    analytics: AnalyticsService = Depends(get_analytics_service),
    processors: List[BaseProcessor] = Depends(get_processor_chain),
    redis_client=Depends(get_redis_optional),
) -> EventBatchOut:
    service = EventIngestionService(
        db,
        user_id=user.id,
        processors=processors,
        analytics=analytics,
        redis_client=redis_client,
    )
    results = service.ingest_batch(body)
    db.commit()
    created = sum(1 for r in results if r.newly_created)
    deduped = sum(1 for r in results if not r.newly_created)
    out_items: List[EventOut] = []
    for ir in results:
        db.refresh(ir.record)
        out_items.append(
            _event_to_out(
                ir.record,
                include_processor_outputs=False,
                db=db,
                deduplicated=not ir.newly_created,
            )
        )
    logger.info(
        "ingested batch count=%s created=%s deduplicated=%s user_id=%s",
        len(results),
        created,
        deduped,
        user.id,
    )
    return EventBatchOut(
        items=out_items,
        count=len(results),
        created_count=created,
        deduplicated_count=deduped,
    )


@router.get(
    "/{event_id}",
    response_model=EventOut,
    dependencies=[Depends(rate_limiter)],
)
def get_event(
    event_id: int,
    db: DBSessionDep,
    api_key: str = Security(APIKeyHeaderDep),
    _: User = Depends(get_current_api_user),
) -> EventOut:
    repo = EventRepository(db)
    row = repo.get_by_id(event_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    return _event_to_out(row, include_processor_outputs=True, db=db)


@router.get(
    "",
    response_model=EventListResponse,
    dependencies=[Depends(rate_limiter)],
)
def list_events(
    db: DBSessionDep,
    api_key: str = Security(APIKeyHeaderDep),
    _: User = Depends(get_current_api_user),
    event_type: str | None = None,
    source: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> EventListResponse:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    repo = EventRepository(db)
    items, total = repo.list_events(
        event_type=event_type,
        source=source,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )
    return EventListResponse(
        items=[_event_to_out(i, include_processor_outputs=False, db=db) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )
