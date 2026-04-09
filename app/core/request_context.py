from __future__ import annotations

import uuid
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return request_id_ctx.get() or "-"


def set_request_id(value: str | None) -> str:
    rid = value or uuid.uuid4().hex
    request_id_ctx.set(rid)
    return rid
