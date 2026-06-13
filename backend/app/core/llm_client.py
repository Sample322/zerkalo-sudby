"""Module-level Anthropic async client singleton (Phase 4 KEYSTONE).

The single ``AsyncAnthropic`` instance every LLM-touching service shares
(``LLMService.generate`` for the reading + ``SafetyService.classify`` for the gate).

Security (T-04-10 / V8): the client reads ``ANTHROPIC_API_KEY`` from the environment via the
SDK's own default lookup — the key is **never** passed explicitly here, never logged, never
echoed. ``ANTHROPIC_API_KEY`` is already a required no-default secret (``app.core.config``), so
the process fails fast at import if it is missing; this module does not re-read or expose it.

Async (RESEARCH Pitfall 6): we use ``AsyncAnthropic`` (never the sync ``Anthropic``) so
``await client.messages.parse(...)`` does not block the FastAPI event loop during a generation.
"""

from __future__ import annotations

from anthropic import AsyncAnthropic

# Reads ANTHROPIC_API_KEY from env via the SDK default. Do NOT pass the key explicitly and do
# NOT log it — the key crosses into the SDK only, never into application logs or responses.
client: AsyncAnthropic = AsyncAnthropic()


__all__ = ["client"]
