from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "database_connected" in data
    assert "redis_connected" in data


def test_health_live() -> None:
    resp = client.get("/api/v1/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


def test_health_ready_without_redis_ok_when_not_required() -> None:
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database_connected"] is True
    assert body["status"] == "ready"


def test_metrics_endpoint() -> None:
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "events_total" in data
    assert "cache_ttl_seconds" in data
    assert "http_requests_total" in data
    assert "events_ingested_counter" in data


def test_ingest_list_and_get_event() -> None:
    body = {
        "event_type": "order.placed",
        "source": "demo",
        "payload": {"order_id": "o1", "amount": 42.5},
    }
    r = client.post("/api/v1/events", json=body)
    assert r.status_code == 200
    created = r.json()
    assert created["event_type"] == "order.placed"
    assert created["payload"]["order_id"] == "o1"
    eid = created["id"]

    r2 = client.get(f"/api/v1/events/{eid}")
    assert r2.status_code == 200
    assert r2.json()["id"] == eid

    r3 = client.get("/api/v1/events", params={"limit": 10})
    assert r3.status_code == 200
    lst = r3.json()
    assert lst["total"] >= 1
    assert len(lst["items"]) >= 1


def test_analytics_summary() -> None:
    client.post(
        "/api/v1/events",
        json={"event_type": "click", "payload": {"x": 1}},
    )
    r = client.get("/api/v1/analytics/summary", params={"window_hours": 24})
    assert r.status_code == 200
    data = r.json()
    assert data["total_events"] >= 1
    assert data["cached"] is False


def test_analytics_snapshot_persisted() -> None:
    client.post(
        "/api/v1/events",
        json={"event_type": "snapshot.test", "payload": {}},
    )
    r = client.get("/api/v1/analytics/summary", params={"window_hours": 12})
    assert r.status_code == 200
    snaps = client.get("/api/v1/analytics/snapshots", params={"limit": 10})
    assert snaps.status_code == 200
    body = snaps.json()
    assert len(body["items"]) >= 1
    assert body["items"][0]["snapshot_kind"] == "summary"
    assert body["items"][0]["total_events"] >= 1


def test_ingest_idempotent() -> None:
    body = {
        "event_type": "payment.initiated",
        "payload": {"x": 1},
        "idempotency_key": "idem-test-1",
    }
    r1 = client.post("/api/v1/events", json=body)
    r2 = client.post("/api/v1/events", json=body)
    assert r1.status_code == 200
    assert r2.status_code == 200
    d1, d2 = r1.json(), r2.json()
    assert d1["id"] == d2["id"]
    assert d1.get("deduplicated") is False
    assert d2.get("deduplicated") is True


def test_list_events_filter_by_source() -> None:
    client.post(
        "/api/v1/events",
        json={"event_type": "t", "source": "alpha", "payload": {}},
    )
    client.post(
        "/api/v1/events",
        json={"event_type": "t", "source": "beta", "payload": {}},
    )
    r = client.get("/api/v1/events", params={"source": "alpha", "limit": 20})
    assert r.status_code == 200
    data = r.json()
    assert all(item.get("source") == "alpha" for item in data["items"])
