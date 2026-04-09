# Event Processing & Analytics Platform

FastAPI service for **ingesting append-only domain events**, persisting them in **PostgreSQL**, running an optional **post-ingestion processor chain**, exposing **Redis-backed analytics** with **snapshot audit rows**, and optional **Celery** maintenance after ingest (cache invalidate + aggregate pre-warm).

## Architecture (high level)

1. **Client** → `POST /api/v1/events` (or `/batch`) with `X-API-Key`.
2. **EventIngestionService** normalizes payload, enforces **idempotency** (`user_id` + `idempotency_key`), inserts `events`, runs **processors** (Redis counters; optional pairwise ML), persists `event_processor_results`.
3. **Analytics invalidation**: inline Redis `SCAN` delete, **or** enqueue **`post_ingestion_analytics_task`** when `CELERY_BROKER_URL` is set (worker invalidates and **pre-warms** windows from `ANALYTICS_PREWARM_WINDOW_HOURS`).
4. **Reads**: `GET /analytics/*` uses Redis cache + Postgres aggregates + optional `analytics_snapshots` rows.

```
┌─────────┐     ┌──────────────┐     ┌──────────┐     ┌───────┐
│ Client  │────▶│ FastAPI API  │────▶│ Postgres │     │ Redis │
└─────────┘     └──────┬───────┘     └──────────┘     └───┬───┘
                       │                                   │
                       │         ┌──────────────┐          │
                       └────────▶│ Celery worker│──────────┘
                                 └──────────────┘
```

## Stack

- Python 3.11+ (Dockerfile), FastAPI, Pydantic v2, SQLAlchemy 2.x
- PostgreSQL (recommended) or SQLite (`DATABASE_URL`)
- Redis (rate limits, analytics cache, optional Celery broker)
- Celery 5.x (optional background maintenance)

## Repository layout

| Path | Role |
|------|------|
| `app/main.py` | App factory, CORS, middleware, exception handlers |
| `app/api/` | Routers: `auth`, `events`, `analytics`, `system` |
| `app/core/` | `config`, `security`, `logging`, `exceptions` |
| `app/db/` | Engine/session, ORM models |
| `app/services/` | Ingestion, analytics, processors, Redis client |
| `app/workers/` | Celery app + tasks |
| `app/repositories/` | Event, snapshot, processor-result persistence |
| `tests/` | pytest + `TestClient` (SQLite, dependency overrides) |
| `dashboard/` | Vite/React demo UI |

## Configuration

Copy `.env.example` to `.env`. Important variables:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy URL |
| `REDIS_URL` | Cache, rate limits, default Celery broker if broker unset |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | When set, post-ingest analytics maintenance runs async |
| `SECRET_KEY` | JWT signing (**change in production**) |
| `CORS_ALLOW_ORIGINS` | `*` or comma-separated list |
| `RATE_LIMIT_*` / `AUTH_RATE_LIMIT_*` | Redis fixed-window limits |
| `READINESS_REQUIRE_REDIS` | If `true`, `/health/ready` is 503 when Redis is down |
| `ANALYTICS_PREWARM_WINDOW_HOURS` | Comma-separated floats for worker pre-warm (e.g. `1,24`) |
| `ANALYTICS_CACHE_TTL_SECONDS` | Redis TTL for aggregate JSON payloads |

## API (`/api/v1`)

| Method | Path | Notes |
|--------|------|-------|
| POST | `/auth/signup`, `/auth/login` | Per-IP **Redis** rate limits |
| POST | `/auth/api-key` | JWT only; rotate API key |
| POST | `/events`, `/events/batch` | Ingest; per-user Redis rate limits |
| GET | `/events`, `/events/{id}` | List/filter; detail |
| GET | `/analytics/summary`, `/by-type`, `/snapshots` | Aggregates + audit |
| GET | `/health`, `/health/live`, `/health/ready`, `/metrics` | Probes + counters |

**Errors:** Most `HTTPException` responses use `{"error": {"code", "message"}}` (including **429**).

## Health endpoints

- **`/health/live`** — process up (always 200 if the server runs).
- **`/health/ready`** — database required; Redis required only if `READINESS_REQUIRE_REDIS=true` (503 when not satisfied).
- **`/health`** — informational 200 with `database_connected` / `redis_connected` flags (backward compatible).

## Local setup (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Start Postgres and Redis locally, then:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Celery worker** (optional; set `CELERY_BROKER_URL` in `.env`):

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

Dashboard (proxies `/api` when configured in `dashboard/vite.config.ts`):

```bash
cd dashboard && npm install && npm run dev
```

## Docker Compose

Full stack (API + Postgres + Redis + worker):

```bash
docker compose up --build
```

- API: `http://localhost:8000`
- Postgres: `localhost:5432`, database **`event_platform`**
- Override `SECRET_KEY` via environment when deploying.

## AWS EC2 (outline)

1. Launch an EC2 instance (Ubuntu LTS). Open **80/443** (reverse proxy) and **22** (SSH) as needed.
2. Install Docker Engine + Docker Compose plugin (or run **RDS** for Postgres and **ElastiCache** for Redis instead of containers).
3. Copy the project (git clone), create `.env` with production `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `CORS_ALLOW_ORIGINS`, and `CELERY_BROKER_URL` pointing at your Redis.
4. `docker compose up -d` **or** split services: run **RDS + ElastiCache**, point API/worker containers at those endpoints.
5. Put **ALB** or nginx in front; wire **target group health check** to `GET /api/v1/health/ready` (HTTP 200).
6. Use **IAM roles** instead of long-lived keys if you add AWS SDK usage later.

*(This repo ships Compose and a production-oriented Dockerfile; it does not provision AWS resources automatically.)*

## Example request flow

1. `POST /auth/signup` → `POST /auth/login` → receive `access_token` and `api_key`.
2. `POST /api/v1/events` with header `X-API-Key: <api_key>` and JSON body `{ "event_type": "order.placed", "payload": { "sku": "a" } }`.
3. `GET /api/v1/analytics/summary?window_hours=24` — cached after first miss; worker may have pre-warmed windows if Celery is enabled.

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

Tests use SQLite + dependency overrides (processors disabled, Redis optional, auth rate limits no-op).

## Limitations / future work

- **Schema migrations:** `create_all` on startup is dev-friendly; production should use **Alembic** revisions.
- **Idempotency:** application-level check; concurrent duplicate keys can still race without a DB uniqueness constraint.
- **Cache invalidation:** `SCAN` on `analytics:*` is simple but can be expensive at very large key counts.
- **Blocking handlers:** route handlers are sync; heavy work is partially offloaded via **Celery** when configured.
- **Requirements:** some packages (`slowapi`, `boto3`, `xgboost`, etc.) remain optional/future use.

## Post-ingestion processors

See `app/services/processors/` — default order: **ingestion counters** (Redis), **pairwise scoring** (optional, env-gated). Outputs land in `event_processor_results`.

## Offline ML training

```bash
.venv/bin/python -m app.ml.train_model
```

Uses `data/demo_training_matchups.csv` and writes artifacts under `artifacts/`.
