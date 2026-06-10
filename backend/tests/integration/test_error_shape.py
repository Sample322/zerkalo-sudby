"""RED stub — soft-error shape, no stacktrace leak (INFRA-05).

Wave-0 placeholder for the VALIDATION.md node ID. Plan 04 (which adds the global
exception handler at the ``app.main`` seam) removes the skip and asserts a forced internal
error returns soft in-character JSON with no stack trace in the body (TZ §29.2).

DO NOT implement here — Plan 04 owns this.
"""

from __future__ import annotations

import pytest

_OWNER = "Wave 0 stub — implemented in Plan 04 (global soft-error handler)"


@pytest.mark.skip(reason=_OWNER)
async def test_no_stacktrace_leak() -> None:
    """INFRA-05: a forced internal error returns soft JSON, never a stack trace."""
    raise NotImplementedError("Plan 04 implements the no-stacktrace-leak assertion")
