from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Security

from app.api.deps import (
    APIKeyHeaderDep,
    DBSessionDep,
    get_analytics_service,
    get_current_api_user,
    rate_limiter,
)
from app.models.user import User
from app.repositories.analytics_snapshot_repository import AnalyticsSnapshotRepository
from app.schemas.analytics import (
    AnalyticsByType,
    AnalyticsSnapshotListResponse,
    AnalyticsSnapshotOut,
    AnalyticsSummary,
)
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    dependencies=[Depends(rate_limiter)],
)
def analytics_summary(
    db: DBSessionDep,
    api_key: str = Security(APIKeyHeaderDep),
    _: User = Depends(get_current_api_user),
    analytics: AnalyticsService = Depends(get_analytics_service),
    window_hours: float = 24.0,
) -> AnalyticsSummary:
    window_hours = max(0.1, min(window_hours, 24 * 365))
    out = analytics.summary(window_hours)
    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("commit after analytics summary failed: %s", exc)
        db.rollback()
        raise
    return out


@router.get(
    "/by-type",
    response_model=AnalyticsByType,
    dependencies=[Depends(rate_limiter)],
)
def analytics_by_type(
    db: DBSessionDep,
    api_key: str = Security(APIKeyHeaderDep),
    _: User = Depends(get_current_api_user),
    analytics: AnalyticsService = Depends(get_analytics_service),
    window_hours: float = 24.0,
) -> AnalyticsByType:
    window_hours = max(0.1, min(window_hours, 24 * 365))
    out = analytics.by_type(window_hours)
    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("commit after analytics by_type failed: %s", exc)
        db.rollback()
        raise
    return out


@router.get(
    "/snapshots",
    response_model=AnalyticsSnapshotListResponse,
    dependencies=[Depends(rate_limiter)],
)
def list_analytics_snapshots(
    db: DBSessionDep,
    api_key: str = Security(APIKeyHeaderDep),
    _: User = Depends(get_current_api_user),
    limit: int = 20,
) -> AnalyticsSnapshotListResponse:
    """Read persisted aggregate snapshots (no Redis)."""
    limit = max(1, min(limit, 100))
    repo = AnalyticsSnapshotRepository(db)
    rows = repo.list_recent(limit=limit)
    return AnalyticsSnapshotListResponse(
        items=[AnalyticsSnapshotOut.model_validate(r) for r in rows],
    )
