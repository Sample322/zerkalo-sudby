"""Admin routes — guarded by the server-side ``ADMIN_TELEGRAM_IDS`` allowlist (AUTH-05).

* ``GET /api/admin/ping``  — the testable allowlist probe (403 for non-admins).
* ``GET /api/admin/stats`` — read-only product statistics (NO personal data): user + reading
  counts and the per-deck / per-topic / per-answer-style distributions that power the testing
  dashboard (e.g. which answer style users pick most). Every value is an aggregate COUNT — no
  questions, names, or identifiers cross the boundary.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_admin
from app.core.config import settings
from app.models import Deck, Reading, User
from app.models.enums import ReadingStatus
from app.services.answer_style import ANSWER_STYLE_LABELS

router = APIRouter(prefix="/admin", tags=["admin"])

# Topic slug -> RU label (mirrors the frontend TOPICS), so the dashboard reads in Russian.
_TOPIC_LABELS: dict[str, str] = {
    "love": "Любовь",
    "work": "Работа",
    "money": "Деньги",
    "choice": "Выбор",
    "day": "День",
    "self_reflection": "Саморефлексия",
    "general": "Общий вопрос",
}


class StatItem(BaseModel):
    """One bucket of a distribution: a stable key, a human label, and the count."""

    key: str
    label: str
    count: int


class AdminStatsOut(BaseModel):
    """Aggregate product stats (no PII) for the admin dashboard."""

    total_users: int
    unlimited_users: int
    active_users_7d: int
    total_readings: int
    completed_readings: int
    failed_readings: int
    readings_today: int
    readings_7d: int
    by_deck: list[StatItem]
    by_topic: list[StatItem]
    by_answer_style: list[StatItem]


@router.get("/ping")
async def admin_ping(admin: User = Depends(require_admin)) -> dict[str, bool]:
    """Allowlist probe — reachable only by an admin ``telegram_id`` (else 403)."""
    return {"ok": True}


@router.get("/stats", response_model=AdminStatsOut)
async def admin_stats(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> AdminStatsOut:
    """Compute the dashboard aggregates in a handful of grouped COUNT queries (admin-only)."""
    # readings.created_at is a naive TIMESTAMP (server_default func.now()) — compare against naive UTC.
    now = datetime.now(UTC).replace(tzinfo=None)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    async def count(stmt) -> int:
        return int((await session.scalar(stmt)) or 0)

    total_users = await count(select(func.count()).select_from(User))
    unlimited_users = (
        await count(
            select(func.count())
            .select_from(User)
            .where(User.telegram_id.in_(settings.UNLIMITED_TELEGRAM_IDS))
        )
        if settings.UNLIMITED_TELEGRAM_IDS
        else 0
    )
    total_readings = await count(select(func.count()).select_from(Reading))
    completed = await count(
        select(func.count()).select_from(Reading).where(Reading.status == ReadingStatus.COMPLETED)
    )
    failed = await count(
        select(func.count()).select_from(Reading).where(Reading.status == ReadingStatus.FAILED)
    )
    readings_today = await count(
        select(func.count()).select_from(Reading).where(Reading.created_at >= day_ago)
    )
    readings_7d = await count(
        select(func.count()).select_from(Reading).where(Reading.created_at >= week_ago)
    )
    active_users_7d = await count(
        select(func.count(func.distinct(Reading.user_id))).where(Reading.created_at >= week_ago)
    )

    deck_rows = (
        await session.execute(
            select(Deck.slug, Deck.title, func.count(Reading.id))
            .join(Reading, Reading.deck_id == Deck.id)
            .group_by(Deck.slug, Deck.title)
            .order_by(func.count(Reading.id).desc())
        )
    ).all()
    by_deck = [StatItem(key=slug, label=title, count=int(c)) for slug, title, c in deck_rows]

    topic_rows = (
        await session.execute(
            select(Reading.topic, func.count(Reading.id))
            .group_by(Reading.topic)
            .order_by(func.count(Reading.id).desc())
        )
    ).all()
    by_topic = [
        StatItem(key=tp or "—", label=_TOPIC_LABELS.get(tp or "", tp or "Без темы"), count=int(c))
        for tp, c in topic_rows
    ]

    style_rows = (
        await session.execute(
            select(Reading.answer_style, func.count(Reading.id))
            .group_by(Reading.answer_style)
            .order_by(func.count(Reading.id).desc())
        )
    ).all()
    by_answer_style = [
        StatItem(key=st or "—", label=ANSWER_STYLE_LABELS.get(st or "", "Не указан"), count=int(c))
        for st, c in style_rows
    ]

    return AdminStatsOut(
        total_users=total_users,
        unlimited_users=unlimited_users,
        active_users_7d=active_users_7d,
        total_readings=total_readings,
        completed_readings=completed,
        failed_readings=failed,
        readings_today=readings_today,
        readings_7d=readings_7d,
        by_deck=by_deck,
        by_topic=by_topic,
        by_answer_style=by_answer_style,
    )


__all__ = ["router"]
