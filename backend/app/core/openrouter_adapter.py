"""OpenRouter-backed adapter that mimics the Anthropic ``messages.parse`` interface.

The LLM-touching services (``LLMService.generate`` for the reading, ``SafetyService.classify``
for the gate) call ``client.messages.parse(...)`` and read ``response.parsed_output`` /
``.stop_reason`` / ``.usage.input_tokens`` / ``.usage.output_tokens`` / ``.model``. That is the
Anthropic SDK surface.

To run on OpenRouter (an OpenAI-compatible gateway) without rewriting those services, this module
exposes the SAME duck-typed surface on top of the OpenAI SDK's structured-outputs
``beta.chat.completions.parse``. ``llm_client.py`` builds this adapter instead of ``AsyncAnthropic``
when ``OPENROUTER_API_KEY`` is set. All callers, tests, and the resilience contract stay unchanged.

A single OpenRouter model id (``settings.OPENROUTER_MODEL``, e.g. ``openai/gpt-4o-mini``) backs
every call — the incoming Anthropic alias (``claude-haiku-4-5`` / ``claude-sonnet-4-6``) is ignored,
so the Haiku→Sonnet "escalation" retry simply retries on the same cheap model. Good enough for a
test deploy; swap the model via env without touching code.
"""

from __future__ import annotations

from dataclasses import dataclass

from openai import AsyncOpenAI

# OpenAI ``finish_reason`` → Anthropic ``stop_reason`` so the services' Pitfall-2 check
# (``stop_reason in {"refusal", "max_tokens"}`` → corrective retry) keeps working.
_FINISH_TO_STOP = {
    "stop": "end_turn",
    "length": "max_tokens",
    "content_filter": "refusal",
}


@dataclass(frozen=True)
class _Usage:
    """Mirrors ``response.usage`` with Anthropic field names the services read."""

    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class _ParsedResponse:
    """Mirrors the subset of the Anthropic ``messages.parse`` response the services use."""

    parsed_output: object
    stop_reason: str
    usage: _Usage
    model: str


class _Messages:
    """Exposes ``.parse(...)`` matching the Anthropic ``client.messages.parse`` signature."""

    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    async def parse(
        self,
        *,
        model: str | None = None,  # incoming Anthropic alias — ignored (we use self._model)
        max_tokens: int | None = None,
        system: str | None = None,
        messages: list[dict] | None = None,
        output_format: type | None = None,
        temperature: float | None = None,
        timeout: float | None = None,
    ) -> _ParsedResponse:
        oai_messages: list[dict] = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        oai_messages.extend(messages or [])

        completion = await self._client.beta.chat.completions.parse(
            model=self._model,
            messages=oai_messages,
            response_format=output_format,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
        choice = completion.choices[0]
        message = choice.message
        # A model refusal yields ``message.refusal`` set + ``parsed`` None — surface it as the
        # Anthropic "refusal" stop reason so the caller's corrective retry fires (never a fake read).
        if getattr(message, "refusal", None):
            stop_reason = "refusal"
        else:
            stop_reason = _FINISH_TO_STOP.get(choice.finish_reason or "stop", "end_turn")

        usage = completion.usage
        return _ParsedResponse(
            parsed_output=message.parsed,
            stop_reason=stop_reason,
            usage=_Usage(
                input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
                output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            ),
            model=completion.model or self._model,
        )


class OpenRouterClient:
    """Drop-in replacement for ``AsyncAnthropic`` exposing only ``.messages.parse``."""

    def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.messages = _Messages(self._client, model)


__all__ = ["OpenRouterClient"]
