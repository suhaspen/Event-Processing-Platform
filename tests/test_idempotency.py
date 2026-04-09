from __future__ import annotations

import importlib
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.repositories.event_repository import EventRepository


@pytest.fixture
def threaded_engine():
    """Shared SQLite for multi-threaded repository checks (check_same_thread=False)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    importlib.import_module("app.db.models")
    importlib.import_module("app.models.user")
    Base.metadata.create_all(bind=engine)
    return engine


def test_batch_mixed_created_and_deduplicated(client):
    """Batch must not fail when one item repeats an idempotency key; summary counts are accurate."""
    r = client.post(
        "/api/v1/events/batch",
        json={
            "events": [
                {
                    "event_type": "batch.a",
                    "idempotency_key": "idem-batch-shared",
                    "payload": {"n": 1},
                },
                {
                    "event_type": "batch.b",
                    "idempotency_key": "idem-batch-shared",
                    "payload": {"n": 2},
                },
                {"event_type": "batch.c", "payload": {}},
            ]
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 3
    assert body["created_count"] == 2
    assert body["deduplicated_count"] == 1
    items = body["items"]
    assert sum(1 for it in items if it.get("deduplicated")) == 1
    assert items[0]["id"] == items[1]["id"]
    assert items[2]["id"] != items[0]["id"]


def test_no_duplicate_rows_for_same_idempotency_key(client):
    """Two sequential ingests with the same key produce one row."""
    key = "idem-single-row"
    for _ in range(3):
        client.post(
            "/api/v1/events",
            json={
                "event_type": "t",
                "idempotency_key": key,
                "payload": {},
            },
        )
    lst = client.get("/api/v1/events", params={"limit": 100})
    assert lst.status_code == 200
    data = lst.json()
    matching = [i for i in data["items"] if i.get("idempotency_key") == key]
    assert len(matching) == 1


def test_second_insert_dedupes_after_commit(threaded_engine):
    """
    After the first row commits, a second insert with the same key hits UNIQUE,
    IntegrityError is handled, and we return the existing row with ``created=False``.
    """
    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=threaded_engine, future=True
    )
    results: list[tuple[int, bool]] = []

    def attempt() -> tuple[int, bool]:
        db = SessionLocal()
        try:
            repo = EventRepository(db)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            row, created = repo.insert(
                event_type="concurrent",
                source=None,
                payload={},
                occurred_at=now,
                user_id=None,
                idempotency_key="idem-thread",
            )
            db.commit()
            return row.id, created
        finally:
            db.close()

    results.append(attempt())
    results.append(attempt())

    ids = {r[0] for r in results}
    assert len(ids) == 1
    assert sum(1 for _id, c in results if c) == 1
    assert sum(1 for _id, c in results if not c) == 1
