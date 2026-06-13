"""SAFE-06 (backend) — the brand-voice ban-list, the post-generation output guard (READ-11).

This is the **backend port** of the canonical frontend ``BANNED_BRAND_TOKENS`` regex
(``frontend/src/reading/copy.ts``). One source of truth (W-1): the backend mirror has the SAME
alternatives — ``ai | нейросет | модель | сгенерирован`` plus the Cyrillic-word-boundary «ии»
branch — so the standalone-«ИИ» logic that must NOT false-positive on benign words containing
the «ии» bigram (гармонии / линии / версии / комиссии) is solved in exactly one place.

The «ии» alternative is anchored to Cyrillic-word boundaries — ``(?:^|[^а-яё])ии(?:[^а-яё]|$)``
(``re.IGNORECASE`` folds the class so it also excludes ``А-ЯЁ``/``Ё``) — so it matches a bare
«ИИ» and «сгенерировано ИИ» / «вопрос к ИИ.» WITHOUT matching inside гармонии / линии / версии.

**Disposition — LOG + FLAG, do NOT fail the reading (RESEARCH Open Question 2):** ``ReadingService``
(Plan 05) runs this over the generated text after a successful generation and *flags / logs* a
brand-voice slip; it never turns a completed reading into a failure on a guard hit. A flagged
reading is still delivered — the guard is an observability + content-quality signal, not a gate.
"""

from __future__ import annotations

import re

# Canonical SAFE-06 ban-list (mirrors frontend reading/copy.ts BANNED_BRAND_TOKENS, W-1).
# Compiled, reusable, case-insensitive. Match via ``.search`` (stateless — no lastIndex).
BANNED_BRAND_TOKENS: re.Pattern[str] = re.compile(
    r"ai|нейросет|модель|сгенерирован|(?:^|[^а-яё])ии(?:[^а-яё]|$)",
    re.IGNORECASE,
)


def contains_banned_brand_token(text: str) -> bool:
    """True if ``text`` contains any banned brand token (AI/нейросеть/модель/сгенерировано/ИИ).

    Mirrors the frontend ``containsBannedBrandToken`` word-boundary semantics exactly, so benign
    words that merely contain the «ии» bigram do not false-positive. LOG + FLAG disposition: the
    caller (ReadingService, Plan 05) flags/logs on True — it does not fail the reading.
    """
    return BANNED_BRAND_TOKENS.search(text) is not None


__all__ = ["BANNED_BRAND_TOKENS", "contains_banned_brand_token"]
