"""Optional Sentry initialization (INFRA-05 seam) — a strict no-op when unconfigured.

``init_sentry()`` does nothing unless ``SENTRY_DSN`` is set, and it never raises if the
``sentry-sdk`` package is not installed (the import is guarded). Full observability —
dashboards, alerting, performance tracing — is deferred to Phase 8; this is just the
minimal seam so the deploy phase can flip it on with an env var.
"""

from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger("app.sentry")


def init_sentry() -> bool:
    """Initialize Sentry iff ``SENTRY_DSN`` is set and ``sentry-sdk`` is importable.

    Returns ``True`` if Sentry was initialized, ``False`` otherwise (the common dev case).
    Never raises — a missing DSN or a missing package is a quiet no-op.
    """
    if not settings.SENTRY_DSN:
        return False

    try:
        import sentry_sdk
    except ImportError:
        logger.warning(
            "sentry_dsn_set_but_sdk_missing",
            extra={"event": "sentry.sdk_missing"},
        )
        return False

    sentry_sdk.init(dsn=settings.SENTRY_DSN)
    logger.info("sentry_initialized", extra={"event": "sentry.initialized"})
    return True


__all__ = ["init_sentry"]
