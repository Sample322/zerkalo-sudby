"""DSN normalisation for asyncpg.

A managed-Postgres connection string commonly carries a libpq ``?sslmode=...`` query
parameter. **asyncpg does not understand ``sslmode``** (it raises on the unexpected kwarg) —
the SSL intent must instead be passed as an asyncpg ``connect_args={"ssl": ...}``. This helper
strips ``sslmode`` (and a stray ``ssl=`` libpq value) from the URL and translates it:

- ``require`` / ``prefer`` / ``allow`` → encrypt, do NOT verify the cert (test-grade; the managed
  cert is often not in the slim container's CA store, and a failed verify would crash-loop boot).
- ``verify-ca`` / ``verify-full`` → encrypt AND verify against the system CA store.
- ``disable`` / absent → no SSL.

Both ``app.core.db`` and ``alembic/env.py`` use this so the runtime engine and the migration
engine treat the DSN identically.
"""

from __future__ import annotations

import ssl
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def async_url_and_connect_args(raw_url: str) -> tuple[str, dict]:
    """Return ``(clean_url, connect_args)`` for ``create_async_engine`` from a libpq-style DSN."""
    parts = urlsplit(raw_url)
    query = dict(parse_qsl(parts.query))
    sslmode = (query.pop("sslmode", None) or query.pop("ssl", None) or "").lower()
    clean_url = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )

    connect_args: dict = {}
    if sslmode in {"require", "prefer", "allow", "true"}:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx
    elif sslmode in {"verify-ca", "verify-full"}:
        connect_args["ssl"] = ssl.create_default_context()
    # "disable" / "" → no ssl key (plain connection)

    return clean_url, connect_args


__all__ = ["async_url_and_connect_args"]
