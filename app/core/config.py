from functools import lru_cache
from pathlib import Path
from typing import Any, Optional
import os

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # Make dotenv optional
    def load_dotenv() -> None:  # type: ignore[no-redef]
        return

try:  # Prefer pydantic-settings when available
    from pydantic import field_validator
    from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore
except ImportError:  # Fallback: use plain pydantic BaseModel
    from pydantic import BaseModel as BaseSettings, ConfigDict, field_validator  # type: ignore

    SettingsConfigDict = ConfigDict  # type: ignore[misc,assignment]


# Load environment variables from .env early so both BaseSettings and the
# fallback BaseModel can see them.
load_dotenv()


class Settings(BaseSettings):
    """
    Central application configuration loaded from environment variables.

    Event processing platform: ingestion, persistence, analytics, caching.
    """

    model_config = SettingsConfigDict(
        env_file=str(Path(".") / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    # Core app
    app_name: str = "Event Processing & Analytics Platform"
    debug: bool = False
    environment: str = "local"  # e.g. local | staging | production

    api_v1_prefix: str = "/api/v1"

    # CORS: comma-separated origins, or "*" for allow all (dev only)
    cors_allow_origins: str = "*"

    # Auth: JWT signing + API keys (see routes_auth, deps)
    secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    access_token_expire_minutes: int = 60 * 24
    algorithm: str = "HS256"

    # Database
    #
    # Primary configuration is via DATABASE_URL. We default to a local
    # PostgreSQL instance for development, with SQLite as a fallback
    # only if no DATABASE_URL is provided.
    database_url: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/event_platform"
    )

    # Redis (rate limiting + analytics cache)
    redis_url: str = "redis://localhost:6379/0"
    analytics_cache_ttl_seconds: int = 30

    # API rate limits (Redis-backed; see deps.rate_limiter)
    rate_limit_requests_per_window: int = 100
    rate_limit_window_seconds: int = 60

    # Auth endpoints (/signup, /login): per-IP abuse protection
    auth_rate_limit_requests_per_window: int = 30
    auth_rate_limit_window_seconds: int = 60

    # Readiness: if true, /health/ready returns 503 when Redis is unreachable
    readiness_require_redis: bool = True

    # Background jobs (Celery). When unset, post-ingest analytics maintenance runs inline.
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None
    # Comma-separated hours for worker pre-warm after cache invalidation (e.g. "1,24")
    analytics_prewarm_window_hours: str = "1,24"

    # ML model configuration
    #
    # These map directly to the requested environment variables.
    model_path: Path = Path("artifacts/win_prob_model.pkl")
    model_metadata_path: Path = Path("artifacts/win_prob_model_metadata.json")
    model_version: str = "baseline_logreg_v1"

    # Training data (CSV columns remain historical names: team_a_elo, etc.)
    training_data_path: Path = Path("data/demo_training_matchups.csv")

    # Elo baseline: rating bump when the primary side has home-style advantage
    home_field_elo_bonus: float = 55.0

    # Optional post-ingestion processor (off by default; core API works without it)
    enable_pairwise_scoring_processor: bool = False
    pairwise_scoring_event_types: str = "pairwise.score.request"

    @field_validator("celery_broker_url", "celery_result_backend", mode="before")
    @classmethod
    def empty_optional_urls(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        return v

    def resolved_database_url(self) -> str:
        """
        Return an effective database URL.

        If DATABASE_URL is supplied directly, it will be used as-is.
        Otherwise we prefer the Postgres development URL above. As a
        last-resort fallback (e.g. for quick demos without Postgres),
        you can set DATABASE_URL to a SQLite URL such as
        'sqlite:///./event_platform.db'.
        """
        return os.getenv("DATABASE_URL", self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


