"""Unit tests for the fail-fast config (INFRA-04).

These PASS now — they exercise ``Settings`` directly and need no DB/Redis.
Covers VALIDATION.md node IDs: ``test_missing_secret_fails_fast`` (secret-failfast) and
``test_admin_ids_csv_parsed`` (admin-ids-parse).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings

_ALL_SECRETS = {
    "BOT_TOKEN": "t",
    "DATABASE_URL": "postgresql+asyncpg://u:p@h:5432/d",
    "REDIS_URL": "redis://h:6379/0",
    "JWT_SECRET": "j",
    "ANTHROPIC_API_KEY": "a",
}


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every settings-relevant env var so only kwargs/defaults apply."""
    for key in (*_ALL_SECRETS, "ADMIN_TELEGRAM_IDS", "WEBHOOK_SECRET", "LOG_LEVEL"):
        monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize("missing", sorted(_ALL_SECRETS))
def test_missing_secret_fails_fast(monkeypatch: pytest.MonkeyPatch, missing: str) -> None:
    """Omitting any required secret raises ValidationError (process-start fail-fast)."""
    _clear_env(monkeypatch)
    kwargs = {k: v for k, v in _ALL_SECRETS.items() if k != missing}

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None, **kwargs)

    reported_missing = {err["loc"][0] for err in exc_info.value.errors()}
    assert missing in reported_missing


def test_admin_ids_csv_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    """``ADMIN_TELEGRAM_IDS="111,222"`` parses to ``[111, 222]`` — no JSON-decode crash."""
    _clear_env(monkeypatch)
    settings = Settings(_env_file=None, ADMIN_TELEGRAM_IDS="111,222", **_ALL_SECRETS)

    assert settings.ADMIN_TELEGRAM_IDS == [111, 222]
    assert all(isinstance(x, int) for x in settings.ADMIN_TELEGRAM_IDS)


def test_admin_ids_defaults_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """No allowlist configured -> empty list (deny-all admin by default)."""
    _clear_env(monkeypatch)
    settings = Settings(_env_file=None, **_ALL_SECRETS)

    assert settings.ADMIN_TELEGRAM_IDS == []


def test_admin_ids_handles_whitespace_and_blanks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stray spaces / trailing commas are tolerated by the validator."""
    _clear_env(monkeypatch)
    settings = Settings(_env_file=None, ADMIN_TELEGRAM_IDS=" 111 , 222 ,", **_ALL_SECRETS)

    assert settings.ADMIN_TELEGRAM_IDS == [111, 222]
