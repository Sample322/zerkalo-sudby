"""Unit tests — Telegram initData two-stage HMAC + JWT (AUTH-02 / AUTH-04).

These run WITHOUT a database (pure crypto / token round-trip). They lock the security
spine: a forged hash, a tampered field, a stale ``auth_date``, or a missing ``hash`` are
all rejected, and the JWT helpers round-trip while pinning HS256 (so an ``alg:none`` token
is refused).

The valid sample is built by ``conftest.make_init_data`` using ``TEST_BOT_TOKEN`` — the
validator MUST accept exactly what that signer produces (RESEARCH Pattern 3).
"""

from __future__ import annotations

import time
from urllib.parse import parse_qsl, urlencode

import jwt
import pytest

from app.core.security import decode_jwt, encode_jwt
from app.services.telegram_auth import parse_user, validate_init_data
from tests.conftest import SAMPLE_USER, TEST_BOT_TOKEN, make_init_data

# --- validate_init_data: happy path ------------------------------------------------


def test_valid_initdata_validates_and_exposes_user() -> None:
    """A correctly-signed initData validates and ``user`` parses to the telegram_id."""
    init_data = make_init_data(TEST_BOT_TOKEN)

    pairs = validate_init_data(init_data, TEST_BOT_TOKEN, max_age=86400)

    user = parse_user(pairs)
    assert user["id"] == SAMPLE_USER["id"]


# --- validate_init_data: rejection paths (the four mandated failure modes) ----------


def test_forged_hash_rejected() -> None:
    """AUTH-02: a forged ``hash`` (random hex substituted) must be rejected."""
    init_data = make_init_data(TEST_BOT_TOKEN)
    fields = dict(parse_qsl(init_data, strict_parsing=True))
    fields["hash"] = "0" * 64  # plausible-length but wrong hex

    with pytest.raises(ValueError):
        validate_init_data(urlencode(fields), TEST_BOT_TOKEN, max_age=86400)


def test_tampered_field_rejected() -> None:
    """AUTH-02: mutating a field after signing (hash no longer matches) is rejected."""
    init_data = make_init_data(TEST_BOT_TOKEN)
    fields = dict(parse_qsl(init_data, strict_parsing=True))
    # Tamper the user blob but keep the OLD hash -> data_check_string changes, hash stale.
    fields["user"] = fields["user"].replace(str(SAMPLE_USER["id"]), "999999999")

    with pytest.raises(ValueError):
        validate_init_data(urlencode(fields), TEST_BOT_TOKEN, max_age=86400)


def test_stale_auth_date_rejected() -> None:
    """AUTH-02: an ``auth_date`` older than the freshness window is rejected."""
    stale = int(time.time()) - 100_000  # well beyond a 24h window
    init_data = make_init_data(TEST_BOT_TOKEN, auth_date=stale)

    with pytest.raises(ValueError):
        validate_init_data(init_data, TEST_BOT_TOKEN, max_age=86400)


def test_missing_hash_rejected() -> None:
    """AUTH-02: initData with no ``hash`` field is rejected."""
    init_data = make_init_data(TEST_BOT_TOKEN)
    fields = dict(parse_qsl(init_data, strict_parsing=True))
    fields.pop("hash")

    with pytest.raises(ValueError):
        validate_init_data(urlencode(fields), TEST_BOT_TOKEN, max_age=86400)


def test_wrong_bot_token_rejected() -> None:
    """AUTH-02: a signature made with a different bot token does not validate."""
    init_data = make_init_data("999999:A_DIFFERENT_BOT_TOKEN")

    with pytest.raises(ValueError):
        validate_init_data(init_data, TEST_BOT_TOKEN, max_age=86400)


# --- JWT helpers: round-trip + algorithm pinning -----------------------------------


def test_jwt_round_trip() -> None:
    """encode_jwt -> decode_jwt round-trips sub + telegram_id and sets iat/exp."""
    token = encode_jwt(sub="user-uuid-123", telegram_id=555000111)

    payload = decode_jwt(token)

    assert payload["sub"] == "user-uuid-123"
    assert payload["telegram_id"] == 555000111
    assert "iat" in payload
    assert "exp" in payload


def test_jwt_expired_rejected() -> None:
    """An already-expired token raises ExpiredSignatureError on decode."""
    token = encode_jwt(sub="user-uuid-123", telegram_id=555000111, expires_in=-10)

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_jwt(token)


def test_jwt_alg_none_rejected() -> None:
    """AUTH-03 (T-04-03): an ``alg:none`` (unsigned) token must be refused.

    decode_jwt pins ``algorithms=["HS256"]`` so an attacker cannot strip the signature
    by switching the header alg to ``none``.
    """
    forged = jwt.encode(
        {"sub": "attacker", "telegram_id": 1}, key=None, algorithm="none"
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_jwt(forged)


def test_jwt_wrong_secret_rejected() -> None:
    """A token signed with a different secret fails signature verification."""
    forged = jwt.encode(
        {"sub": "attacker", "telegram_id": 1, "exp": int(time.time()) + 60},
        "a-different-secret",
        algorithm="HS256",
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_jwt(forged)
