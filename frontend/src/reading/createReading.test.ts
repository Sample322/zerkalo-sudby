// Phase-4 seam tests (D-07): createReading no longer builds a local fixture — it POSTs to
// /api/readings through the apiFetch Bearer seam and maps the backend ReadingOut onto the
// UNCHANGED MockReading shape. The mock-only reversals/rng tests are gone (orientation is
// now server-decided, D-13 70/30 on the backend). `fetch` is stubbed; no live backend.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Analytics is fire-and-forget (its own /api/events fetch) — no-op it so these tests can assert the
// exact /api/readings fetch behaviour (one call) without the extra reading_* analytics call.
vi.mock("../api/events", () => ({ track: () => {} }));

import { useSession } from "../stores/session";
import { BANNED_BRAND_TOKENS } from "./copy";
import { createReading, ReadingError } from "./createReading";
import type { ReadingOutResponse } from "./types";

const POSITIONS = [
  { title: "Суть" },
  { title: "Препятствие" },
  { title: "Совет" },
];

function baseParams(overrides: Record<string, unknown> = {}) {
  return {
    question: "Что мне важно увидеть в отношениях?",
    topic: "love",
    deckSlug: "moon_mirror",
    spreadSlug: "three_card",
    reversalsEnabled: true,
    positions: POSITIONS,
    ...overrides,
  };
}

// A completed backend ReadingOut (the §14.5 contract). Field names are the backend
// snake_case shape ReadingCardOut / ReadingSummaryOut; the mapping camelCase's them.
function completedReadingOut(
  overrides: Partial<ReadingOutResponse> = {},
): ReadingOutResponse {
  return {
    reading_id: "11111111-1111-1111-1111-111111111111",
    status: "completed",
    cards: [
      {
        name: "Звезда",
        position_title: "Суть",
        orientation: "upright",
        short_meaning: "Тихая надежда и ясность намерения.",
        interpretation: "В центре ситуации — спокойная вера в то, что важное уже зреет.",
        deck_accent: "Колода произносит это тихо, своим языком.",
      },
      {
        name: "Башня",
        position_title: "Препятствие",
        orientation: "reversed",
        short_meaning: "Перемена, которая давно назрела.",
        interpretation: "Старое держится из привычки — отпускание освободит силы.",
        deck_accent: "В голосе колоды слышится мягкое напоминание.",
      },
      {
        name: "Солнце",
        position_title: "Совет",
        orientation: "upright",
        short_meaning: "Доверься тёплому, ясному движению.",
        interpretation: "Маленькая открытость сейчас стоит больше осторожного молчания.",
        deck_accent: "Колода добавляет к этому тёплый оттенок смысла.",
      },
    ],
    summary: {
      linkage: "Карты складываются в один внутренний поворот.",
      main_factor: "Главное сейчас — спокойное внимание к тому, что уже происходит.",
      attention: "Стоит заметить чувства, которые проявляются не сразу.",
      soft_advice: "Двигайся мягко и без спешки — у этой темы свой ритм.",
      closing_phrase: "Колода остаётся рядом: выбор всегда остаётся за тобой.",
    },
    remaining_limits: 2,
    ...overrides,
  };
}

/** Stub the global fetch with a scripted Response and capture the request for assertions. */
function stubFetch(body: unknown, init: ResponseInit = { status: 200 }) {
  const calls: { url: string; init: RequestInit }[] = [];
  const fetchMock = vi.fn(async (url: string | URL, requestInit: RequestInit = {}) => {
    calls.push({ url: String(url), init: requestInit });
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}

beforeEach(() => {
  // apiFetch reads the JWT from the session store; seed one so the Bearer header is attached.
  useSession.setState({ jwt: "test-jwt-token" });
});

afterEach(() => {
  vi.restoreAllMocks();
  useSession.setState({ jwt: null });
});

describe("createReading — real POST /api/readings via apiFetch (D-07 mechanical swap)", () => {
  it("is async and resolves to a MockReading on a completed response", async () => {
    stubFetch(completedReadingOut());
    const result = createReading(baseParams());
    expect(result).toBeInstanceOf(Promise);
    const reading = await result;
    expect(reading.cards).toHaveLength(POSITIONS.length);
  });

  // [test_posts_to_readings_endpoint] + [test_request_body_shape]
  it("POSTs to /api/readings with the §14.5 body field names + the Bearer header", async () => {
    const calls = stubFetch(completedReadingOut());
    await createReading(baseParams());

    expect(calls).toHaveLength(1);
    expect(calls[0].url).toContain("/api/readings");
    expect(calls[0].init.method).toBe("POST");

    const headers = new Headers(calls[0].init.headers);
    expect(headers.get("Authorization")).toBe("Bearer test-jwt-token");
    expect(headers.get("Content-Type")).toBe("application/json");

    const sent = JSON.parse(String(calls[0].init.body));
    expect(sent).toEqual({
      question: "Что мне важно увидеть в отношениях?",
      topic: "love",
      deck_slug: "moon_mirror",
      spread_slug: "three_card",
      reversals_enabled: true,
      answer_style: "berezhny", // default when the caller doesn't pass answerStyle
    });
    // The mock-only `positions`/`rng` must NOT leak into the request body.
    expect(sent).not.toHaveProperty("positions");
    expect(sent).not.toHaveProperty("rng");
  });

  // [test_request_body_shape] — null question for a general reading (HOME-02 / D-13).
  it("sends question:null for an empty general reading (HOME-02)", async () => {
    const calls = stubFetch(completedReadingOut());
    await createReading(baseParams({ question: null }));
    const sent = JSON.parse(String(calls[0].init.body));
    expect(sent.question).toBeNull();
  });

  // [test_maps_readingout_to_mockreading]
  it("maps every per-card field ReadingOut → MockReading (snake → camel)", async () => {
    stubFetch(completedReadingOut());
    const reading = await createReading(baseParams());

    expect(reading.cards.map((c) => c.name)).toEqual(["Звезда", "Башня", "Солнце"]);
    expect(reading.cards.map((c) => c.positionTitle)).toEqual([
      "Суть",
      "Препятствие",
      "Совет",
    ]);
    expect(reading.cards.map((c) => c.orientation)).toEqual([
      "upright",
      "reversed",
      "upright",
    ]);
    const first = reading.cards[0];
    expect(first.shortMeaning).toBe("Тихая надежда и ясность намерения.");
    expect(first.interpretation).toBe(
      "В центре ситуации — спокойная вера в то, что важное уже зреет.",
    );
    expect(first.deckAccent).toBe("Колода произносит это тихо, своим языком.");
    // shortPhrase has no backend field — it is sourced from the in-character copy bank.
    for (const card of reading.cards) {
      expect(card.shortPhrase).toBeTruthy();
    }
  });

  // [test_maps_readingout_to_mockreading] — the 5 summary fields via the documented name map.
  it("maps all five summary fields (connection→linkage, attention_point→attention, …)", async () => {
    stubFetch(completedReadingOut());
    const { summary } = await createReading(baseParams());
    expect(summary.linkage).toBe("Карты складываются в один внутренний поворот.");
    expect(summary.mainFactor).toBe(
      "Главное сейчас — спокойное внимание к тому, что уже происходит.",
    );
    expect(summary.attention).toBe(
      "Стоит заметить чувства, которые проявляются не сразу.",
    );
    expect(summary.softAdvice).toBe(
      "Двигайся мягко и без спешки — у этой темы свой ритм.",
    );
    expect(summary.closingPhrase).toBe(
      "Колода остаётся рядом: выбор всегда остаётся за тобой.",
    );
  });

  it("passes the inputs through; createdAt is a valid ISO string", async () => {
    stubFetch(completedReadingOut());
    const reading = await createReading(baseParams());
    expect(reading.topic).toBe("love");
    expect(reading.deckSlug).toBe("moon_mirror");
    expect(reading.spreadSlug).toBe("three_card");
    expect(reading.question).toBe("Что мне важно увидеть в отношениях?");
    expect(reading.createdAt).toBe(new Date(reading.createdAt).toISOString());
  });

  // [test_failure_rejects] — non-OK HTTP status.
  it("rejects on a non-OK response (so the caller shows §9.8 and does not advance)", async () => {
    stubFetch({ detail: "boom" }, { status: 500 });
    await expect(createReading(baseParams())).rejects.toThrow();
  });

  // [test_failure_rejects] — soft 200 honest-fail body (status=failed, cards=[]).
  it("rejects on a soft honest-fail body (status='failed', cards empty)", async () => {
    stubFetch(
      completedReadingOut({
        status: "failed",
        cards: [],
        summary: {
          linkage: "",
          main_factor: "",
          attention: "",
          soft_advice:
            "Колода замолчала на мгновение. Попробуй открыть расклад ещё раз — вопрос уже сохранён.",
          closing_phrase: "",
        },
        remaining_limits: 3,
      }),
    );
    await expect(createReading(baseParams())).rejects.toThrow();
  });

  // [test_mapped_copy_brand_safe]
  it("the mapped card + summary copy is brand-safe (SAFE-06, incl. ИИ)", async () => {
    stubFetch(completedReadingOut());
    const reading = await createReading(baseParams());
    const text = [
      ...reading.cards.flatMap((c) => [
        c.name,
        c.shortMeaning,
        c.interpretation,
        c.deckAccent,
        c.shortPhrase,
      ]),
      ...Object.values(reading.summary),
    ].join(" ");
    expect(BANNED_BRAND_TOKENS.test(text)).toBe(false);
  });
});

// Phase-6 (D-08) — createReading rejects with a DISCRIMINABLE ReadingError so ONE catch in
// CatalogScreen routes the throttle (429), the paywall (200 reason='paywall'), and a
// generation failure to three distinct surfaces — never conflated. The success path,
// signature, and MockReading return type are UNCHANGED (D-05/D-07 guard).
describe("createReading — discriminated ReadingError (D-08 error transport)", () => {
  it("throws ReadingError{kind:'throttle'} on HTTP 429 (the Redis burst gate, 06-03)", async () => {
    stubFetch({ detail: "throttled" }, { status: 429 });
    await expect(createReading(baseParams())).rejects.toMatchObject({
      name: "ReadingError",
      kind: "throttle",
    });
    // Belt: it is the typed subclass, not a bare Error.
    await expect(createReading(baseParams())).rejects.toBeInstanceOf(ReadingError);
  });

  it("throws ReadingError{kind:'paywall', resetAt} on a 200 limit-block body (reason='paywall', 06-02)", async () => {
    // The 06-02 soft paywall body: HTTP 200, status!='completed', reason='paywall',
    // reset_at = week_start + 7d. NO draw (cards empty / summary may be null).
    stubFetch(
      completedReadingOut({
        status: "blocked",
        cards: [],
        summary: null,
        reason: "paywall",
        reset_at: "2026-06-20T12:00:00Z",
        remaining_limits: 0,
      }),
    );
    let caught: unknown;
    try {
      await createReading(baseParams());
    } catch (err) {
      caught = err;
    }
    expect(caught).toBeInstanceOf(ReadingError);
    const error = caught as ReadingError;
    expect(error.kind).toBe("paywall");
    expect(error.resetAt).toBe("2026-06-20T12:00:00Z");
  });

  it("throws ReadingError{kind:'failure'} on a non-OK status that is NOT 429", async () => {
    stubFetch({ detail: "boom" }, { status: 500 });
    await expect(createReading(baseParams())).rejects.toMatchObject({
      name: "ReadingError",
      kind: "failure",
    });
  });

  it("throws ReadingError{kind:'failure'} on a 200 honest-fail body (non-completed, NOT paywall)", async () => {
    // The Phase-4 honest-fail soft body: status=failed, empty cards, no `reason='paywall'`.
    stubFetch(
      completedReadingOut({
        status: "failed",
        cards: [],
        summary: {
          linkage: "",
          main_factor: "",
          attention: "",
          soft_advice:
            "Колода замолчала на мгновение. Попробуй открыть расклад ещё раз — вопрос уже сохранён.",
          closing_phrase: "",
        },
        remaining_limits: 3,
      }),
    );
    const error = (await createReading(baseParams()).catch((e) => e)) as ReadingError;
    expect(error).toBeInstanceOf(ReadingError);
    expect(error.kind).toBe("failure");
    expect(error.resetAt ?? null).toBeNull();
  });
});
