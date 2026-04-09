from __future__ import annotations

import logging
import os
import sys

from app.core.request_context import get_request_id


class _RequestIdFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.request_id = get_request_id()  # type: ignore[attr-defined]
        return super().format(record)


def configure_logging(level: int | None = None) -> None:
    """
    Idempotent stdout logging for API and services.
    Set ``LOG_LEVEL`` (e.g. DEBUG, INFO, WARNING) to override the default INFO.
    Log lines include ``request_id`` when ``RequestContextMiddleware`` is installed.
    """
    root = logging.getLogger()
    if root.handlers:
        return
    if level is None:
        level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        _RequestIdFormatter(
            "%(asctime)s | %(levelname)s | rid=%(request_id)s | %(name)s | %(message)s",
        )
    )
    root.addHandler(handler)
    root.setLevel(level)
