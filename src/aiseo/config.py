"""Settings via pydantic-settings, loads from .env file."""

from __future__ import annotations

from contextvars import ContextVar, Token

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """AI SEO Platform configuration. All API keys are optional (BYOK)."""

    # LLM Provider Keys (all optional)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    perplexity_api_key: str | None = None
    xai_api_key: str | None = None

    # Search Volume Keys (all optional)
    google_ads_developer_token: str | None = None
    google_ads_client_id: str | None = None
    semrush_api_key: str | None = None
    ahrefs_api_key: str | None = None

    # Infrastructure
    database_url: str = "sqlite:///aiseo.db"
    redis_url: str = "redis://localhost:6379/0"

    # Scan defaults
    default_query_count: int = 50
    max_queries_per_scan: int = 200
    scan_timeout_seconds: int = 300

    model_config = {"env_file": ".env", "env_prefix": "AISEO_"}


def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


_request_api_key_overrides: ContextVar[dict[str, str]] = ContextVar(
    "request_api_key_overrides",
    default={},
)


def set_request_api_key_overrides(overrides: dict[str, str]) -> Token:
    """Set request-scoped API key overrides from incoming headers."""
    return _request_api_key_overrides.set(overrides)


def reset_request_api_key_overrides(token: Token) -> None:
    """Reset request-scoped API key overrides."""
    _request_api_key_overrides.reset(token)


def get_effective_api_key(setting_name: str) -> str | None:
    """Get API key from request overrides first, then server settings."""
    override = _request_api_key_overrides.get().get(setting_name)
    if override:
        return override
    settings = get_settings()
    return getattr(settings, setting_name, None)


def get_request_api_key_override(setting_name: str) -> str | None:
    """Get API key override provided in the current request context only."""
    return _request_api_key_overrides.get().get(setting_name)
