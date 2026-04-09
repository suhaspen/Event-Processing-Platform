from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.request_context import set_request_id
from app.services.redis_client import get_redis_client

logger = logging.getLogger(__name__)

HTTP_REQUESTS_REDIS_KEY = "platform:http_requests_total"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Assign X-Request-ID (echo client value or generate), bind logging context,
    and increment a coarse HTTP request counter in Redis when available.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get("X-Request-ID")
        rid = set_request_id(incoming)
        try:
            r = get_redis_client()
            r.incr(HTTP_REQUESTS_REDIS_KEY)
        except Exception:
            pass
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
