import logging
from typing import Annotated, List, Optional

import redis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from app.services.processors.base_processor import BaseProcessor
from app.services.processors.registry import build_default_processors
from app.services.redis_client import get_redis_client

logger = logging.getLogger(__name__)

DBSessionDep = Annotated[Session, Depends(get_db)]
APIKeyHeaderDep = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_processor_chain() -> List[BaseProcessor]:
    """Pluggable processors run after each event is stored (see ``EventIngestionService``)."""
    return build_default_processors()


def get_redis_optional() -> Optional[redis.Redis]:
    """
    Redis client for ingestion-side processors. Returns None if Redis is unreachable
    so ingestion still succeeds without counters.
    """
    try:
        r = get_redis_client()
        r.ping()
        return r
    except Exception:
        return None


def get_analytics_service(db: DBSessionDep) -> AnalyticsService:
    """
    Analytics read service with Redis-backed caching when available.
    """
    return AnalyticsService(db, redis_client=get_redis_client())


def get_current_user(
    db: DBSessionDep,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_token(credentials.credentials)
    if payload is None or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(User.email == payload["sub"]).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


def get_current_api_user(request: Request, db: DBSessionDep) -> User:
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    user = db.query(User).filter(User.api_key == api_key, User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return user


def rate_limiter(
    request: Request,
    user: User = Depends(get_current_api_user),
):
    """
    Fixed-window rate limiter (Redis INCR + EXPIRE). Configurable via settings.
    """
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    key = f"rate:{user.id}:{client_ip}:{request.url.path}"

    try:
        r = get_redis_client()
        current = r.incr(key)
        if current == 1:
            r.expire(key, settings.rate_limit_window_seconds)

        limit = settings.rate_limit_requests_per_window
        if current > limit:
            logger.warning(
                "rate limit exceeded",
                extra={
                    "component": "rate_limit",
                    "user_id": user.id,
                    "path": request.url.path,
                    "client_ip": client_ip,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Retry after the current window expires.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "rate limiter redis error (fail-open): %s",
            exc,
            extra={"component": "rate_limit"},
        )


def auth_rate_limiter(request: Request) -> None:
    """
    Per-IP limits for unauthenticated auth routes (/signup, /login).
    Fail-open if Redis is unavailable (logged) so the API stays available in dev.
    """
    settings = get_settings()
    try:
        r = get_redis_client()
        r.ping()
    except Exception as exc:
        logger.warning(
            "auth rate limit skipped (redis unavailable): %s",
            exc,
            extra={"component": "auth_rate_limit"},
        )
        return

    client_ip = request.client.host if request.client else "unknown"
    key = f"rate:auth:{client_ip}:{request.url.path}"

    try:
        current = r.incr(key)
        if current == 1:
            r.expire(key, settings.auth_rate_limit_window_seconds)

        if current > settings.auth_rate_limit_requests_per_window:
            logger.warning(
                "auth rate limit exceeded",
                extra={
                    "component": "auth_rate_limit",
                    "path": request.url.path,
                    "client_ip": client_ip,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests from this address. Try again later.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "auth rate limiter error (fail-open): %s",
            exc,
            extra={"component": "auth_rate_limit"},
        )

