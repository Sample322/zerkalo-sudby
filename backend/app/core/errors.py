"""Global soft-error handling (INFRA-05) — never leak internals across the error boundary.

When an *unhandled* exception escapes a handler, the client must see a soft, in-character
JSON message — never a stack trace, exception class, or file path (threat T-04-06; TZ §29.2).
The full detail is logged server-side (``logger.exception``) so operators can debug.

This handler is registered for the bare ``Exception`` type only. FastAPI's own
``HTTPException`` and ``RequestValidationError`` handlers are left intact, so 401 / 403 / 422
keep their precise semantics — this is purely the last-resort 500 path.
"""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.errors")

# In-character RU copy — no AI/brand-violating words, no internals (PROJECT brand voice).
_SOFT_MESSAGE = "Колода сейчас молчит. Попробуй чуть позже."


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler: log the real error server-side, return soft JSON to the client."""
    logger.exception(
        "unhandled_exception",
        extra={
            "event": "error.unhandled",
            "path": request.url.path,
            "method": request.method,
        },
    )
    return JSONResponse(
        status_code=500,
        content={"error": "soft", "message": _SOFT_MESSAGE},
    )


__all__ = ["unhandled_exception_handler"]
