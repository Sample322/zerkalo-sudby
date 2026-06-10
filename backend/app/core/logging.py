"""Structured stdlib logging setup (INFRA-05 groundwork).

JSON-line logs to stdout so timeweb.cloud / Docker log drivers can parse them. Called
once on startup from the app lifespan. The full Sentry wiring is deferred to the
deploy/polish phase (RESEARCH Open Question #4); this module gives the soft-error path
a place to log detailed context server-side while the client only ever sees soft JSON.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    """Minimal JSON-line formatter — no third-party dependency."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Surface any structured extras attached via logger.info(..., extra={...}).
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_KEYS and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


# Attributes present on every LogRecord — excluded from the structured-extras sweep.
_RESERVED_LOG_KEYS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime", "taskName"}


def configure_logging() -> None:
    """Install the JSON formatter on the root logger at the configured level."""
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
