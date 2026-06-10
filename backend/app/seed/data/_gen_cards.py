"""One-shot generator for cards.json — the 78 universal tarot cards.

Run once to (re)produce ``cards.json``: 22 Major Arcana (number 0-21, suit NULL) +
56 Minor (4 suits x ranks ace..king, number 1-14). Meanings are PLACEHOLDER but
non-empty and STYLE-FREE (universal layer only — no deck imagery, no commercial
deck references). Full literary copy is a later content task.

This file is not imported by the app; it documents how cards.json was produced and
lets the row set be regenerated deterministically.
"""

from __future__ import annotations

import json
from pathlib import Path

# Original, style-free Russian titles for the 22 Major Arcana (universal names).
MAJORS: list[str] = [
    "Шут",
    "Маг",
    "Жрица",
    "Императрица",
    "Император",
    "Иерофант",
    "Влюблённые",
    "Колесница",
    "Сила",
    "Отшельник",
    "Колесо Фортуны",
    "Справедливость",
    "Повешенный",
    "Смерть",
    "Умеренность",
    "Дьявол",
    "Башня",
    "Звезда",
    "Луна",
    "Солнце",
    "Суд",
    "Мир",
]

MAJORS_EN: list[str] = [
    "The Fool",
    "The Magician",
    "The High Priestess",
    "The Empress",
    "The Emperor",
    "The Hierophant",
    "The Lovers",
    "The Chariot",
    "Strength",
    "The Hermit",
    "Wheel of Fortune",
    "Justice",
    "The Hanged Man",
    "Death",
    "Temperance",
    "The Devil",
    "The Tower",
    "The Star",
    "The Moon",
    "The Sun",
    "Judgement",
    "The World",
]

# Minor suits: (slug, Russian noun, English noun, elemental keyword).
SUITS: list[tuple[str, str, str, str]] = [
    ("wands", "Жезлов", "Wands", "энергии и действия"),
    ("cups", "Кубков", "Cups", "чувств и отношений"),
    ("swords", "Мечей", "Swords", "мыслей и решений"),
    ("pentacles", "Пентаклей", "Pentacles", "дел и ресурсов"),
]

# Rank labels 1..14 (ace..king) — Russian and English.
RANKS_RU: list[str] = [
    "Туз",
    "Двойка",
    "Тройка",
    "Четвёрка",
    "Пятёрка",
    "Шестёрка",
    "Семёрка",
    "Восьмёрка",
    "Девятка",
    "Десятка",
    "Паж",
    "Рыцарь",
    "Королева",
    "Король",
]
RANKS_EN: list[str] = [
    "Ace",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Page",
    "Knight",
    "Queen",
    "King",
]


def _major(number: int, title: str, title_en: str) -> dict:
    slug = f"major_{number:02d}_{title_en.lower().replace('the ', '').replace(' ', '_')}"
    return {
        "slug": slug,
        "arcana_type": "major",
        "suit": None,
        "number": number,
        "title": title,
        "title_en": title_en,
        "keywords_upright": ["старший аркан", "ключевой урок", "поворот"],
        "keywords_reversed": ["задержка", "внутреннее сопротивление", "пересмотр"],
        "meaning_upright": (
            f"«{title}» в прямом положении — значимый аркан этапа: ключевая тема, "
            f"которую подсвечивает расклад. Универсальное значение, без привязки к колоде."
        ),
        "meaning_reversed": (
            f"«{title}» в перевёрнутом положении — не беда, а задержка, блокировка или "
            f"нераскрытая сторона той же энергии; повод посмотреть на тему внимательнее."
        ),
        "advice_upright": (
            "Прислушайся к теме этой карты как к мягкой подсказке и сделай спокойный шаг."
        ),
        "advice_reversed": (
            "Не торопись: дай энергии раскрыться и пересмотри то, что пока буксует."
        ),
    }


def _minor(suit_slug: str, suit_ru: str, suit_en: str, element: str, rank: int) -> dict:
    title = f"{RANKS_RU[rank - 1]} {suit_ru}"
    title_en = f"{RANKS_EN[rank - 1]} of {suit_en}"
    return {
        "slug": f"{suit_slug}_{rank:02d}",
        "arcana_type": "minor",
        "suit": suit_slug,
        "number": rank,
        "title": title,
        "title_en": title_en,
        "keywords_upright": [f"масть {element}", "повседневная динамика", "оттенок"],
        "keywords_reversed": ["задержка", "дисбаланс", "переосмысление"],
        "meaning_upright": (
            f"«{title}» в прямом положении — карта масти {element}: рабочий оттенок "
            f"ситуации в этой сфере. Универсальное значение, без стиля колоды."
        ),
        "meaning_reversed": (
            f"«{title}» в перевёрнутом положении — та же тема {element} в виде задержки, "
            f"дисбаланса или сигнала пересмотреть подход; не плохой знак."
        ),
        "advice_upright": (
            "Обрати внимание на этот оттенок ситуации и действуй соразмерно, без спешки."
        ),
        "advice_reversed": (
            "Сбавь темп и мягко пересмотри то, что в этой сфере пока идёт через сопротивление."
        ),
    }


def build_cards() -> list[dict]:
    cards: list[dict] = []
    for number, (title, title_en) in enumerate(zip(MAJORS, MAJORS_EN, strict=True)):
        cards.append(_major(number, title, title_en))
    for suit_slug, suit_ru, suit_en, element in SUITS:
        for rank in range(1, 15):
            cards.append(_minor(suit_slug, suit_ru, suit_en, element, rank))
    return cards


def main() -> None:
    cards = build_cards()
    assert len(cards) == 78, f"expected 78 cards, got {len(cards)}"
    slugs = {c["slug"] for c in cards}
    assert len(slugs) == 78, "card slugs are not unique"
    out = Path(__file__).with_name("cards.json")
    out.write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(cards)} cards -> {out}")


if __name__ == "__main__":
    main()
