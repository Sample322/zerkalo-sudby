"""LIMIT-04 (red stub) — ``determine_access`` bucket-order seam (pure fn, no DB).

Plan 06-02 creates ``determine_access(limits) -> Bucket`` + the ``Bucket`` StrEnum in
``app.services.reading`` (RESEARCH Pattern 4 / D-06). The order is **free → subscription → paid**
(spend expiring buckets first, preserve permanent ``paid_spreads_balance`` last). This phase only
ever populates ``free``; the sub/paid arms are the Phase-7 seam, asserted here so a later author
cannot silently break the order.

These are ``xfail(strict=False)`` until Plan 02 lands — they **xpass** the moment the symbol
exists and behaves. The import is done INSIDE each test so a missing symbol surfaces as the
xfailed assertion (not a collection-time ImportError that would error the whole module).

A tiny ``_Limits`` stand-in mimics the ``UserLimits`` attributes the pure fn reads — no DB, no
session, so these run even without Postgres.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest


@dataclass
class _Limits:
    """Minimal duck-typed stand-in for ``UserLimits`` (only the fields ``determine_access`` reads)."""

    free_weekly_limit: int = 3
    free_used_this_week: int = 0
    week_start: object = None
    subscription_spreads_limit: int = 0
    subscription_spreads_used: int = 0
    paid_spreads_balance: int = 0


@pytest.mark.xfail(strict=False, reason="Plan 06-02 implements determine_access + Bucket")
def test_free_when_room_or_stale() -> None:
    """FREE is returned whenever the free bucket has room (the common path this phase)."""
    from app.services.reading import Bucket, determine_access

    assert determine_access(_Limits(free_used_this_week=0)) is Bucket.FREE
    assert determine_access(_Limits(free_used_this_week=2)) is Bucket.FREE  # 1 slot left


@pytest.mark.xfail(strict=False, reason="Plan 06-02 implements determine_access + Bucket")
def test_bucket_order() -> None:
    """Phase-7 seam: with free exhausted but sub AND paid both > 0, SUBSCRIPTION wins over PAID.

    Proves expiring buckets are spent before the permanent ``paid_spreads_balance`` (D-06).
    """
    from app.services.reading import Bucket, determine_access

    exhausted_free = _Limits(
        free_weekly_limit=3,
        free_used_this_week=3,
        subscription_spreads_limit=10,
        subscription_spreads_used=0,
        paid_spreads_balance=5,
    )
    assert determine_access(exhausted_free) is Bucket.SUBSCRIPTION


@pytest.mark.xfail(strict=False, reason="Plan 06-02 implements determine_access + Bucket")
def test_none_when_exhausted() -> None:
    """NONE only when every bucket is empty (→ the soft paywall, this phase)."""
    from app.services.reading import Bucket, determine_access

    all_empty = _Limits(
        free_weekly_limit=3,
        free_used_this_week=3,
        subscription_spreads_limit=0,
        subscription_spreads_used=0,
        paid_spreads_balance=0,
    )
    assert determine_access(all_empty) is Bucket.NONE
