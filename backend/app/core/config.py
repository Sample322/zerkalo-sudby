"""Application configuration via pydantic-settings.

Security spine (INFRA-04): required secrets have **no defaults**, so instantiating
``Settings()`` at import time raises ``ValidationError`` and the process refuses to
start when any required secret is missing (fail-fast).

Footgun guarded here (RESEARCH Pitfall 2): pydantic-settings JSON-decodes complex
types (``list``/``dict``) from env vars by default. ``ADMIN_TELEGRAM_IDS=111,222`` would
raise a JSON-decode error. ``Annotated[list[int], NoDecode]`` + a ``mode="before"``
validator opts out of JSON decoding and splits the comma-separated string instead.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Required secrets: missing any of these => ValidationError at import (fail-fast) ---
    BOT_TOKEN: str
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@postgres:5432/db
    REDIS_URL: str  # redis://redis:6379/0
    JWT_SECRET: str
    # LLM key — required at startup per INFRA-04 even though unused until Phase 4.
    ANTHROPIC_API_KEY: str

    # --- Admin allowlist — MUST bypass JSON decoding (Pitfall 2) ---
    ADMIN_TELEGRAM_IDS: Annotated[list[int], NoDecode] = []

    # --- Optional / tunable ---
    JWT_EXPIRE_SECONDS: int = 60 * 60 * 24 * 7  # 7-day session token
    INITDATA_MAX_AGE_SECONDS: int = 86400  # 24h initData freshness window
    WEBHOOK_SECRET: str | None = None  # X-Telegram-Bot-Api-Secret-Token (Phase 7)
    LOG_LEVEL: str = "INFO"
    # Optional error-tracking DSN (INFRA-05). Unset => Sentry init is a strict no-op;
    # full dashboards/alerting are deferred to Phase 8 (RESEARCH Open Question #4).
    SENTRY_DSN: str | None = None

    # --- CORS (deploy) ---
    # Comma-separated allowed origins for the Mini App frontend. On timeweb this is the
    # nginx static app's HTTPS URL (the frontend calls this API cross-origin with a Bearer
    # JWT — no cookies). Empty => CORS middleware is NOT installed (same-origin / dev).
    # NoDecode + split avoids the JSON-decode footgun, same as ADMIN_TELEGRAM_IDS.
    CORS_ORIGINS: Annotated[list[str], NoDecode] = []

    @field_validator("ADMIN_TELEGRAM_IDS", mode="before")
    @classmethod
    def _parse_ids(cls, v: object) -> object:
        """Split a comma-separated env string into a list of ints.

        Accepts ``"111,222"`` -> ``[111, 222]``. Already-parsed lists pass through so
        a Python-side default / programmatic override still works.
        """
        if isinstance(v, str):
            return [int(x) for x in v.split(",") if x.strip()]
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_origins(cls, v: object) -> object:
        """Split a comma-separated env string into a list of origin URLs.

        Accepts ``"https://a.example,https://b.example"`` -> ``[...]``. Already-parsed
        lists pass through. Trailing slashes are stripped so an origin matches the
        browser's ``Origin`` header (which never has a trailing slash).
        """
        if isinstance(v, str):
            return [o.strip().rstrip("/") for o in v.split(",") if o.strip()]
        return v


# Instantiated at import -> fail-fast on any missing required secret.
settings = Settings()  # type: ignore[call-arg]
