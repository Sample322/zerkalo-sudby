"""Answer-style modifiers (Ясный / Бережный / Таинственный) — an MVP preference knob.

The user picks how a reading should *sound* — from concrete & practical to atmospheric &
mystical. The chosen style appends a short instruction to the system frame (parallel to the deck
modifier) and is recorded on the reading, so the admin stats can show which style users prefer
during testing (then the winner is kept). Brand-safe (SAFE-06): never the words AI / нейросеть /
модель.
"""

from __future__ import annotations

DEFAULT_ANSWER_STYLE = "berezhny"

# slug -> RU display label (mirrors the frontend selector + admin stats).
ANSWER_STYLE_LABELS: dict[str, str] = {
    "yasny": "Ясный",
    "berezhny": "Бережный",
    "tainstvenny": "Таинственный",
}

ANSWER_STYLES: tuple[str, ...] = tuple(ANSWER_STYLE_LABELS)

# The instruction appended to the SYSTEM block for the chosen style.
_MODIFIERS: dict[str, str] = {
    "yasny": (
        "СТИЛЬ ОТВЕТА — ЯСНЫЙ. Отвечай максимально конкретно и по существу заданного вопроса. "
        "Назови ситуацию пользователя своими словами и дай прямой, предметный ответ именно на неё, "
        "а не общие рассуждения о жизни. Делай чёткие формулировки, понятный вывод и один конкретный "
        "следующий шаг. Минимум абстрактных образов и метафор. Оставайся бережным, но говори прямо и по делу."
    ),
    "berezhny": (
        "СТИЛЬ ОТВЕТА — БЕРЕЖНЫЙ. Держи баланс между конкретикой и образностью, но обязательно "
        "отвечай по существу вопроса: называй ситуацию человека своими словами и давай предметный "
        "смысл, добавляя тепло и атмосферу. Мягко подводи к выводу, не дави и не делай резких заявлений."
    ),
    "tainstvenny": (
        "СТИЛЬ ОТВЕТА — ТАИНСТВЕННЫЙ. Говори образно и атмосферно, голосом оракула: метафоры, "
        "символы, мягкие мистические акценты, пространство для собственной интерпретации. Но даже "
        "сквозь образы держи ответ привязанным к конкретному вопросу человека — пусть за метафорой "
        "читается ясный смысл про его ситуацию. Без категоричных предсказаний и без давления."
    ),
}


def normalize_answer_style(style: str | None) -> str:
    """Coerce an incoming style slug to a known one (unknown / None → the default)."""
    return style if style in _MODIFIERS else DEFAULT_ANSWER_STYLE


def answer_style_modifier(style: str | None) -> str:
    """The system-frame instruction for the chosen style (the default's text when unknown)."""
    return _MODIFIERS[normalize_answer_style(style)]


__all__ = [
    "DEFAULT_ANSWER_STYLE",
    "ANSWER_STYLES",
    "ANSWER_STYLE_LABELS",
    "normalize_answer_style",
    "answer_style_modifier",
]
