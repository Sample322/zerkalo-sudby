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

from pydantic import field_validator, model_validator
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

    # --- LLM provider keys: at least ONE is required (enforced below). ---
    # ANTHROPIC_API_KEY → the CLAUDE.md-default provider (anthropic SDK messages.parse).
    # OPENROUTER_API_KEY → an OpenAI-compatible gateway used via the adapter (cheap test models).
    ANTHROPIC_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    # Single OpenRouter model id backing every call when OPENROUTER_API_KEY is set. Cheap default
    # for a test deploy; tune via env without code changes (e.g. anthropic/claude-3.5-haiku).
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"

    # --- Admin allowlist — MUST bypass JSON decoding (Pitfall 2) ---
    ADMIN_TELEGRAM_IDS: Annotated[list[int], NoDecode] = []

    # --- Unlimited allowlist — admin + invited testers get uncapped readings (the consume gate
    # is bypassed for these telegram_ids). Comma-separated, same NoDecode split as the admins. ---
    UNLIMITED_TELEGRAM_IDS: Annotated[list[int], NoDecode] = []

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

    @field_validator("ADMIN_TELEGRAM_IDS", "UNLIMITED_TELEGRAM_IDS", mode="before")
    @classmethod
    def _parse_ids(cls, v: object) -> object:
        """Split a comma-separated env string into a list of ints.

        Accepts ``"111,222"`` -> ``[111, 222]``. Already-parsed lists pass through so
        a Python-side default / programmatic override still works.
        """
        if isinstance(v, str):
            return [int(x) for x in v.split(",") if x.strip()]
        return v

    def is_unlimited(self, telegram_id: int) -> bool:
        """True when this user (admin or invited tester) bypasses the weekly free-reading cap."""
        return telegram_id in self.UNLIMITED_TELEGRAM_IDS

    def is_admin(self, telegram_id: int) -> bool:
        """True when this user is on the admin allowlist (server-side dashboard access)."""
        return telegram_id in self.ADMIN_TELEGRAM_IDS

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

    @model_validator(mode="after")
    def _require_llm_key(self) -> Settings:
        """Fail-fast unless at least one LLM provider key is configured (INFRA-04 spirit)."""
        if not self.ANTHROPIC_API_KEY and not self.OPENROUTER_API_KEY:
            raise ValueError(
                "An LLM provider key is required: set ANTHROPIC_API_KEY or OPENROUTER_API_KEY."
            )
        return self


# Instantiated at import -> fail-fast on any missing required secret.
settings = Settings()  # type: ignore[call-arg]
