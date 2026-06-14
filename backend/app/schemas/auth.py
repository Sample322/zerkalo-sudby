"""Auth + profile schemas (TZ §14.1 ``/api/auth/telegram``, §14.2 ``/api/me``).

``POST /api/auth/telegram`` returns ``{access_token, user, limits, settings}``;
``GET /api/me`` returns the same shape minus the token. ``from_attributes=True`` lets us
build these straight from the ``User`` / ``UserLimits`` ORM rows.

Only non-sensitive profile/limit fields are exposed — no ``JWT_SECRET`` / ``BOT_TOKEN`` and
no internal audit columns ever cross this boundary (threat T-04-08).
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuthRequest(BaseModel):
    """Request body for ``POST /api/auth/telegram``.

    ``init_data`` is the raw ``window.Telegram.WebApp.initData`` string. NOTE: the server
    derives ``telegram_id`` ONLY from inside this validated blob — it never reads an id from
    any other request field (threat T-04-01).
    """

    init_data: str = Field(min_length=1)


class UserOut(BaseModel):
    """Public user profile projection."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str | None = None
    photo_url: str | None = None
    is_premium_telegram: bool = False
    onboarding_completed: bool = False
    last_seen_at: datetime | None = None


class LimitsOut(BaseModel):
    """Weekly free-limit + paid balance projection (TZ §13.11)."""

    model_config = ConfigDict(from_attributes=True)

    free_weekly_limit: int
    free_used_this_week: int
    week_start: date | None = None
    paid_spreads_balance: int
    subscription_spreads_limit: int
    subscription_spreads_used: int


class SettingsOut(BaseModel):
    """User-facing settings flags (onboarding / reversals / history personalization)."""

    model_config = ConfigDict(from_attributes=True)

    reversals_enabled: bool
    allow_history_personalization: bool
    onboarding_completed: bool


class SettingsPatch(BaseModel):
    """Partial-update request for ``PATCH /api/me/settings`` (PROF-02, D-09).

    Every field is optional so any subset can be patched: only the keys actually present in the
    request body are written (``model_dump(exclude_unset=True)`` in the handler), leaving the
    omitted flags untouched — the partial-update invariant. There is deliberately NO ``user_id``
    field: the target row is always the authenticated (JWT ``sub``) user, never the body
    (threat T-05-SPOOF). ``allow_history_personalization`` is the D-05/D-06 consent toggle
    (default OFF on the model); persisting it is Phase 5's entire HIST-05 obligation on the write
    side — the history-personalization feature itself is v2/ENG-02 and is NOT built here.
    """

    reversals_enabled: bool | None = Field(
        default=None, description="Учитывать перевёрнутые карты при раскладе."
    )
    allow_history_personalization: bool | None = Field(
        default=None, description="Согласие на персонализацию по истории раскладов."
    )
    onboarding_completed: bool | None = Field(
        default=None, description="Онбординг пройден."
    )


class AuthResponse(BaseModel):
    """Response for ``POST /api/auth/telegram`` (TZ §14.1)."""

    access_token: str
    user: UserOut
    limits: LimitsOut
    settings: SettingsOut


class MeResponse(BaseModel):
    """Response for ``GET /api/me`` (TZ §14.2) — same shape, no token."""

    user: UserOut
    limits: LimitsOut
    settings: SettingsOut


__all__ = [
    "AuthRequest",
    "UserOut",
    "LimitsOut",
    "SettingsOut",
    "SettingsPatch",
    "AuthResponse",
    "MeResponse",
]
