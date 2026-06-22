# Промты для карт колод — GPT-Image

Система промтов для генерации 78 карт под каждую из 6 колод. Картинки рисуются **без текста** —
название карты + золотую рамку добавляет само приложение (`CardArt`). Залил картинки → проставил
`image_url`/`thumbnail_url` в `deck_cards` → карты появились.

---

## Настройки GPT-Image

- **Размер:** `1024×1536` (вертикаль, соотношение 2:3 — формат карты таро).
- **Качество:** high.
- **Один субъект по центру**, full-bleed (рисунок на всю карту).
- **Консистентность:** для одной колоды держи ОДИН и тот же «style block» (см. ниже) неизменным —
  меняется только субъект карты. Это даёт единую серию.

## Универсальный технический хвост (добавляй в КОНЕЦ каждого промта)

```
Vertical tarot card illustration, 2:3 portrait. Single centered subject, full-bleed artwork.
NO text, NO title, NO numerals, NO words, NO border or frame. Cohesive series style, symbolic
and atmospheric, refined hand-painted detail, soft inner glow, dark background. Not cartoonish.
```

---

## 6 STYLE-блоков (префикс под каждую колоду)

### 1. Классические Арканы (`classic_arcana`)
```
Classic traditional tarot art. Warm candlelit palette of deep umber brown (#1E1510), antique
gold (#C9A45C), cream parchment (#F3E3C3) and burnt sienna (#6B3F1D). Rider-Waite-inspired
symbolism in refined, timeless hand-painted detail with gold-leaf accents; balanced symmetrical
composition; serene, wise and clear; aged-manuscript texture, soft warm glow.
```

### 2. Лунное Зеркало (`moon_mirror`)
```
Dreamlike lunar tarot art. Nocturnal palette of deep midnight indigo (#0B1026), periwinkle blue
(#5E6AD2), moonlit silver-blue (#C7D2FE) and pale cyan glow (#9BD5FF). Imagery of the moon, still
water, reflections, tides, mist and silence; soft luminous glow, flowing watery forms, ethereal
and intuitive, starlight, a quiet meditative mood, gentle reflective surfaces.
```

### 3. Тени Арканов (`shadow_arcana`)
```
Psychological shadow tarot art. Twilight palette of near-black (#08070A), deep aubergine
(#2A1838), violet (#8B5CF6) and pale lilac (#D6C7FF). Imagery of shadow, a single candle, a
closed door, a mirror in half-light, inner thresholds; chiaroscuro lighting, deep contrast,
introspective and honest but never frightening, elegant darkness, a single soft violet light source.
```

### 4. Сердечный Оракул (`heart_oracle`)
```
Tender romantic oracle art. Warm rose palette of deep wine (#1A0710, #8F1D46), soft blush pink
(#E8A0B8) and pale rose (#F6D7DE). Imagery of threads, hearts, distance and attraction, warmth,
waiting and connection between people; delicate, gentle, intimate; soft diffuse light, flowing
ribbons and petals; emotionally warm and reassuring.
```

### 5. Колода Пути (`path_deck`)
```
Grounded strategic path tarot art. Daylight palette of slate charcoal (#101318), muted
bronze-gold (#C2A46D), cool stone grey (#697386) and pale sand (#E5D3A3). Imagery of roads,
crossroads, maps, bridges, stairways, horizons and stepping stones; clear, composed,
architectural; open daylight skies; a sense of direction and the next step; less mysticism, more clarity.
```

### 6. Лесной Оракул (`forest_oracle`)
```
Storybook forest oracle art. Palette of deep forest green (#07130D, #1F5A3D), warm ember amber
(#D08A2D) and soft moss gold (#D7C58A). Imagery of forest, paths, hearth-fire, water, a doorway,
wind, roots, light and shadow among trees; lush natural symbolism, warm firelight glow through
woods, enchanted but grounded, painterly fairytale atmosphere without cartoonish humor.
```

---

## Сборка промта

```
[STYLE-блок колоды]  +  [субъект карты]  +  [технический хвост]
```

**Пример** (Звезда, для Лунного Зеркала):
> Dreamlike lunar tarot art. Nocturnal palette of deep midnight indigo… *(весь блок 2)* … A kneeling
> figure pouring water by a still pool under one great star and seven small stars, calm night sky.
> Vertical tarot card illustration, 2:3 portrait… *(весь технический хвост)*

---

## Субъекты — Старшие Арканы (22)

Имя из БД → визуальный субъект (RWS-канон, перепиши «reimagined in this deck's style»).

| # | Карта | Субъект (англ., в промт) |
|---|-------|--------------------------|
| 0 | Шут | A youth stepping off a cliff edge, a small white dog, a white rose, a bundle on a staff, bright sky |
| 1 | Маг | A figure one hand raised to the sky one to the earth, an infinity symbol above, the four suit emblems on a table |
| 2 | Жрица | A veiled priestess seated between two pillars (one dark, one light), a crescent moon, a scroll |
| 3 | Императрица | A crowned woman on a cushioned throne in a field of wheat, a crown of twelve stars, lush nature |
| 4 | Император | A bearded ruler on a stone throne with ram-head carvings, a scepter, barren mountains |
| 5 | Иерофант | A hierophant between two pillars raising a hand in blessing, two acolytes, crossed keys |
| 6 | Влюблённые | A man and a woman beneath a radiant angel, a tree behind each, the sun above |
| 7 | Колесница | An armored figure in a chariot drawn by two sphinxes (one black, one white), a starry canopy |
| 8 | Сила | A serene woman gently closing a lion's jaws, an infinity symbol above her head |
| 9 | Отшельник | A robed elder on a peak holding a lantern containing a star, a long staff, night |
| 10 | Колесо Фортуны | A great wheel inscribed with symbols, a sphinx atop, winged creatures in the corners |
| 11 | Справедливость | An enthroned figure holding an upright sword and balanced scales, between two pillars |
| 12 | Повешенный | A figure suspended upside-down by one foot from a tau-shaped tree, a soft halo |
| 13 | Смерть | A skeletal rider in armor on a pale white horse, a banner bearing a white rose |
| 14 | Умеренность | A winged figure pouring liquid between two cups, one foot in water one on land |
| 15 | Дьявол | A horned figure on a pedestal above two loosely chained figures, an inverted torch |
| 16 | Башня | A tall tower struck by lightning, a crown thrown off, two figures falling, flames |
| 17 | Звезда | A kneeling figure pouring water by a still pool under one great star and seven small stars |
| 18 | Луна | A full moon with a faint face, two towers, a winding path, a dog and a wolf, a crayfish in water |
| 19 | Солнце | A radiant sun with a face, a child on a white horse, sunflowers, a low wall |
| 20 | Суд | A great angel sounding a trumpet, figures rising with open arms from below |
| 21 | Мир | A dancing figure within an oval laurel wreath, four winged creatures in the corners |

> Если в БД порядок 8/11 (Сила/Справедливость) иной — субъекты привязаны к ИМЕНИ, не к номеру, так что ок.

## Субъекты — Младшие Арканы (56)

GPT-Image хорошо знает канон Райдера-Уэйта. Для Младших проще ссылаться на канон:

```
[STYLE-блок]  +  "The classic Rider-Waite-Smith scene for the {РАНГ} of {МАСТЬ}, reimagined in
this deck's style"  +  [технический хвост]
```

**Масти (стихия/тема — для атмосферы сцены):**
- **Жезлы / Wands** — огонь: воля, страсть, действие, рост.
- **Кубки / Cups** — вода: чувства, любовь, интуиция, связи.
- **Мечи / Swords** — воздух: мысль, конфликт, правда, ясность.
- **Пентакли / Pentacles** — земля: материя, работа, деньги, тело.

**Ранги:** Туз (Ace — одиночный эмблемный символ масти, выходящий из облака-руки), 2–10 (сцены),
Паж/Рыцарь/Королева/Король (Page/Knight/Queen/King — придворные фигуры с эмблемой масти).

---

## Масштаб и порядок (рекомендация)

- 78 карт × 6 колод = **468 картинок**. Делай **колодами целиком**, не вперемешку.
- Старт: 1–2 самые ходовые колоды ПОЛНОСТЬЮ (напр. «Классические Арканы» + «Лунное Зеркало»).
  Пока у колоды нет полного сета — она показывает буквенный fallback (лучше иметь полные колоды,
  чем у всех по половине).
- В каждой колоде начни с **22 Старших** (самые узнаваемые), потом 56 Младших.

## Консистентность (важно)

- Один и тот же STYLE-блок дословно на всю колоду.
- Та же палитра, та же «камера»/композиция, тот же уровень детализации.
- Если GPT-Image даёт референс-картинку — генери остальные «in the same style as the reference».
- Тёмный фон у всех (карты лягут на обсидиановый UI с золотой рамкой).

## Заливка в приложение

1. Экспорт в `webp` (или `png`), вертикаль 2:3 (напр. 800×1200 + thumbnail 200×300).
2. Залить на статику/S3 timeweb.
3. Я проставлю `image_url` + `thumbnail_url` в `deck_cards` (по `deck_slug` + карте) — фронт-код уже
   рисует `<img>` когда url есть (`CardArt`).
