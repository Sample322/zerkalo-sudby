"""Integration — soft-error shape, no stacktrace leak (INFRA-05, TZ §29.2).

A forced unhandled error returns a soft in-character JSON body with HTTP 500 and NO stack
trace / exception class / file path. HTTPException-based responses (401/403/422) are
unaffected — that is asserted by the auth tests; here we only force the 500 path.

This needs no database: the throwaway route raises before touching any dependency.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# A distinctive secret string the handler must NOT echo back to the client.
_SECRET_DETAIL = "INTERNAL_SECRET_abc123_do_not_leak"


@pytest.fixture
def boom_app():
    """Register a throwaway route that raises, then remove it after the test."""

    @app.get("/__boom__")
    async def _boom() -> None:  # pragma: no cover - body always raises
        raise RuntimeError(_SECRET_DETAIL)

    yield app

    # Remove the temporary route so it never leaks into other tests.
    app.router.routes = [
        r
        for r in app.router.routes
        if getattr(r, "path", None) != "/__boom__"
    ]


async def test_no_stacktrace_leak(boom_app) -> None:
    """INFRA-05: a forced internal error returns soft JSON, never a stack trace."""
    # raise_app_exceptions=False so the test client returns the handler's 500 response
    # (instead of re-raising) — we are asserting what the *client* sees.
    transport = ASGITransport(app=boom_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/__boom__")

    assert resp.status_code == 500
    body = resp.json()
    # Soft, in-character payload is present.
    assert body["error"] == "soft"
    assert body["message"]

    # NOTHING internal leaked into the response body.
    raw = resp.text
    assert _SECRET_DETAIL not in raw
    assert "Traceback" not in raw
    assert "RuntimeError" not in raw
    assert "telegram_auth" not in raw  # no module/file path
    assert ".py" not in raw
