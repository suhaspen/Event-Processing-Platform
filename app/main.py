from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import routes_analytics, routes_auth, routes_events, routes_system
from app.api.middleware import RequestContextMiddleware
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging_config import configure_logging
from app.db.session import Base, engine
from app.db import models  # noqa: F401  - register ORM metadata
from app.models import user  # noqa: F401  - users table for FKs


def _parse_cors_origins(raw: str) -> list[str]:
    """Comma-separated list, or '*' for allow-all (development only)."""
    stripped = raw.strip()
    if stripped == "*":
        return ["*"]
    return [o.strip() for o in stripped.split(",") if o.strip()]


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_parse_cors_origins(settings.cors_allow_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    @app.exception_handler(AppError)
    async def app_error_handler(_request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, list):
            message = "; ".join(str(x) for x in detail)
        else:
            message = str(detail)
        if exc.status_code == 429:
            code = "rate_limited"
        elif exc.status_code == 401:
            code = "unauthorized"
        elif exc.status_code == 404:
            code = "not_found"
        elif exc.status_code == 400:
            code = "bad_request"
        else:
            code = "http_error"
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": message}},
        )

    app.include_router(routes_auth.router, prefix=settings.api_v1_prefix)
    app.include_router(routes_events.router, prefix=settings.api_v1_prefix)
    app.include_router(routes_analytics.router, prefix=settings.api_v1_prefix)
    app.include_router(routes_system.router, prefix=settings.api_v1_prefix)

    @app.on_event("startup")
    def on_startup() -> None:
        configure_logging()
        Base.metadata.create_all(bind=engine)

    return app


app = create_app()
