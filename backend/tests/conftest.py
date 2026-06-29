"""Wave-0 shared test fixtures.

This conftest is the substrate every later plan's verifications depend on (Plans 02-04).
It provides:
  * deterministic test env so ``app.core.config`` can be imported (the module instantiates
    ``settings = Settings()`` at import — required secrets must be present);
  * an async in-process ``client`` (httpx ``ASGITransport`` — no live server);
  * a ``db_session`` bound to the test database with per-test rollback;
  * a ``redis_client``;
  * ``make_init_data(...)`` — a deterministic Telegram ``initData`` signer that matches
    RESEARCH Pattern 3's two-stage HMAC, so unit tests can build valid / tampered / stale
    variants without a live Telegram session.

Integration fixtures that need Postgres/Redis ``pytest.skip`` when the dependency is
unreachable, so the suite stays green (and fully collectable) without ``docker compose up``
while still exercising real behavior when the stack is live.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from collections.abc import AsyncIterator
from urllib.parse import urlencode

import pytest

# --- Test environment: set BEFORE importing anything under app.* -------------------
# app.core.config runs `settings = Settings()` at import, so required secrets must exist.
# A real .env in the repo root is NOT loaded for tests because we point env_file elsewhere
# via these explicit values taking precedence; we also pin a deterministic BOT_TOKEN.
TEST_BOT_TOKEN = "123456:TEST_BOT_TOKEN_for_initdata_signing"

_TEST_ENV_DEFAULTS = {
    "BOT_TOKEN": TEST_BOT_TOKEN,
    # Default to the compose service ports on localhost; override via real env in CI.
    "DATABASE_URL": "postgresql+asyncpg://zerkalo:zerkalo@localhost:5432/zerkalo",
    "REDIS_URL": "redis://localhost:6379/0",
    "JWT_SECRET": "test-jwt-secret-not-for-production",
    "ANTHROPIC_API_KEY": "test-anthropic-key",
    "ADMIN_TELEGRAM_IDS": "111,222",
    # Phase-7 (ЮKassa) fail-fast config secrets (threat T-07-SECRET-LEAK: test-only dummies,
    # NEVER real credentials, never logged). Plan 02 adds ``YOOKASSA_SHOP_ID`` /
    # ``YOOKASSA_SECRET_KEY`` as required (no-default) settings; they must be present in the env
    # BEFORE ``app.core.config`` instantiates ``Settings()`` at import, or every test that imports
    # an app module would fail collection. The real ЮKassa surface is never reached — see
    # ``tests/integration/fakes_payments.py`` (FakeYooKassa is the only ЮKassa client in the suite).
    "YOOKASSA_SHOP_ID": "test_shop",
    "YOOKASSA_SECRET_KEY": "test_secret",
}
for _key, _value in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _value)

# Now safe to import app modules (config will validate against the env above).
from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal, engine  # noqa: E402
from app.core.redis import redis_client as _redis_client  # noqa: E402
from app.main import app  # noqa: E402
from app.models.base import Base  # noqa: E402

# A sample Telegram user blob (the value of the `user` key inside initData).
SAMPLE_USER: dict[str, object] = {
    "id": 555000111,
    "first_name": "Тест",
    "last_name": "Пользователь",
    "username": "test_seeker",
    "language_code": "ru",
}


def make_init_data(
    bot_token: str,
    user: dict | None = None,
    auth_date: int | None = None,
    extra: dict[str, str] | None = None,
) -> str:
    """Build a correctly-signed Telegram ``initData`` query string.

    Mirrors RESEARCH Pattern 3 exactly so the produced ``hash`` validates against the
    Plan-04 validator:
        secret_key = HMAC_SHA256(key=b"WebAppData", msg=bot_token)
        hash       = HMAC_SHA256(key=secret_key, msg=data_check_string).hexdigest()
    where ``data_check_string`` is the ``\\n``-joined, key-sorted ``k=v`` of every field
    EXCEPT ``hash`` (values are the raw, un-URL-encoded strings).

    Returns the URL-encoded ``initData`` string (as Telegram delivers it). Tampered or
    stale variants are produced by mutating ``user``/``auth_date`` or post-editing the
    returned string.
    """
    if user is None:
        user = SAMPLE_USER
    if auth_date is None:
        auth_date = int(time.time())

    fields: dict[str, str] = {
        "auth_date": str(auth_date),
        "query_id": "AAHtest_query_id",
        "user": json.dumps(user, separators=(",", ":"), ensure_ascii=False),
    }
    if extra:
        fields.update(extra)

    data_check_string = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    return urlencode({**fields, "hash": computed_hash})


# --- Async fixtures ---------------------------------------------------------------


@pytest.fixture
async def client() -> AsyncIterator[object]:
    """In-process async HTTP client (no live server) via httpx ASGITransport."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture(scope="session")
async def _db_ready() -> bool:
    """Create all tables once per session against the test DB.

    Skips the whole DB-dependent suite if Postgres is unreachable (e.g. Docker not up),
    so unit tests still run. Later plans run ``alembic upgrade head`` instead of
    ``create_all`` once the migration exists (Plan 02).
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return True
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Postgres unreachable for integration tests: {exc}")


@pytest.fixture
async def db_session(_db_ready: bool) -> AsyncIterator[object]:
    """Per-test ``AsyncSession`` wrapped in a transaction that is rolled back."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture
async def redis_client() -> AsyncIterator[object]:
    """Shared async Redis client; skips when Redis is unreachable."""
    try:
        await _redis_client.ping()
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Redis unreachable for integration tests: {exc}")
    yield _redis_client


__all__ = ["make_init_data", "TEST_BOT_TOKEN", "SAMPLE_USER", "settings"]
