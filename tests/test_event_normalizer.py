from __future__ import annotations

from datetime import datetime, timezone

from app.processing.event_normalizer import EventNormalizer
from app.schemas.events import EventCreate


def test_event_normalizer_strips_timezone_on_occurred_at() -> None:
    dt = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    ev = EventCreate(
        event_type=" signup ",
        source=" web ",
        payload={"k": "v"},
        occurred_at=dt,
    )
    t, s, p, o = EventNormalizer.normalize(ev)
    assert t == "signup"
    assert s == "web"
    assert p == {"k": "v"}
    assert o.tzinfo is None
