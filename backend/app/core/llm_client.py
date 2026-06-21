"""Module-level LLM async client singleton (Phase 4 KEYSTONE; swappable provider).

The single client every LLM-touching service shares (``LLMService.generate`` for the reading +
``SafetyService.classify`` for the gate). It exposes the Anthropic ``messages.parse`` surface,
regardless of the backing provider:

- **OpenRouter** (when ``OPENROUTER_API_KEY`` is set): an ``OpenRouterClient`` adapter over the
  OpenAI SDK pointed at OpenRouter's base URL (structured outputs via ``beta.chat.completions.parse``).
- **Anthropic** (default, when only ``ANTHROPIC_API_KEY`` is set): the real ``AsyncAnthropic``.

``app.core.config`` requires at least one of the two keys (fail-fast). Keys cross into the SDK
only — never logged, never echoed (T-04-10 / V8).

Async (RESEARCH Pitfall 6): both paths are async (``await client.messages.parse(...)``) so a
generation never blocks the FastAPI event loop.
"""

from __future__ import annotations

from app.core.config import settings


def _build_client() -> object:
    """Pick the provider from config: OpenRouter if its key is set, else Anthropic."""
    if settings.OPENROUTER_API_KEY:
        from app.core.openrouter_adapter import OpenRouterClient

        return OpenRouterClient(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            model=settings.OPENROUTER_MODEL,
        )

    from anthropic import AsyncAnthropic

    # Reads ANTHROPIC_API_KEY from env via the SDK default. Do NOT pass the key explicitly.
    return AsyncAnthropic()


# Duck-typed: both providers expose ``.messages.parse(...)`` → ``.parsed_output`` / ``.usage`` /
# ``.stop_reason`` / ``.model``. The services type-hint ``AsyncAnthropic`` for editor support only.
client: object = _build_client()


__all__ = ["client"]
