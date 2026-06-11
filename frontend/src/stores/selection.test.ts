import { beforeEach, describe, expect, test } from "vitest";

import type { MockReading } from "../reading/types";
import {
  canStart,
  questionValidity,
  useSelection,
} from "./selection";

// Reset the WHOLE store (existing selection + the Phase-3 flow slice) before each test,
// mirroring the existing setState-in-beforeEach + getState() drive style.
beforeEach(() => {
  useSelection.setState({
    topic: null,
    deckSlug: null,
    spreadSlug: null,
    question: "",
    reversalsEnabled: false,
    step: "onboarding",
    history: [],
    reading: null,
  });
});

// A minimal, fully-typed MockReading for the reading-slot tests (shape only; content is
// exercised by createReading.test.ts).
function makeReading(): MockReading {
  return {
    question: "вопрос",
    topic: "love",
    deckSlug: "moon_mirror",
    spreadSlug: "three_card",
    createdAt: "2026-06-11T00:00:00.000Z",
    cards: [],
    summary: {
      linkage: "связка",
      mainFactor: "фактор",
      attention: "внимание",
      softAdvice: "совет",
      closingPhrase: "фраза",
    },
  };
}

describe("useSelection (existing selection — no regression)", () => {
  test("initial selection state is all null", () => {
    const s = useSelection.getState();
    expect(s.topic).toBeNull();
    expect(s.deckSlug).toBeNull();
    expect(s.spreadSlug).toBeNull();
  });

  test("setDeck updates only deckSlug (no cross-field mutation)", () => {
    useSelection.getState().setDeck("moon_mirror");
    const s = useSelection.getState();
    expect(s.deckSlug).toBe("moon_mirror");
    expect(s.topic).toBeNull();
    expect(s.spreadSlug).toBeNull();
  });
});

describe("question validity (HOME-01 / HOME-02 / D-13)", () => {
  test("empty question is valid (general reading — no hint)", () => {
    expect(questionValidity("")).toEqual({ status: "valid" });
    expect(questionValidity("   ")).toEqual({ status: "valid" });
  });

  test("1–9 chars is too short (gentle hint)", () => {
    expect(questionValidity("a").status).toBe("tooShort");
    expect(questionValidity("123456789").status).toBe("tooShort");
  });

  test("10–500 chars is valid", () => {
    expect(questionValidity("0123456789").status).toBe("valid");
    expect(questionValidity("a".repeat(500)).status).toBe("valid");
  });

  test("setQuestion clamps stored text at the 500-char max (>500 never stored)", () => {
    useSelection.getState().setQuestion("x".repeat(600));
    expect(useSelection.getState().question.length).toBe(500);
    // Clamped text is still valid (well past the 10-char floor).
    expect(questionValidity(useSelection.getState().question).status).toBe("valid");
  });

  test("setQuestion mutates only `question` (no cross-field mutation)", () => {
    useSelection.setState({ topic: "love", deckSlug: "moon_mirror" });
    useSelection.getState().setQuestion("про любовь и выбор");
    const s = useSelection.getState();
    expect(s.question).toBe("про любовь и выбор");
    expect(s.topic).toBe("love");
    expect(s.deckSlug).toBe("moon_mirror");
  });
});

describe("canStart gate (HOME-07)", () => {
  test("true only when topic AND deck AND spread are all set", () => {
    expect(
      canStart({ topic: "love", deckSlug: "moon_mirror", spreadSlug: "three_card" }),
    ).toBe(true);
  });

  test("false when any of topic/deck/spread is missing", () => {
    expect(canStart({ topic: null, deckSlug: "d", spreadSlug: "s" })).toBe(false);
    expect(canStart({ topic: "love", deckSlug: null, spreadSlug: "s" })).toBe(false);
    expect(canStart({ topic: "love", deckSlug: "d", spreadSlug: null })).toBe(false);
    expect(canStart({ topic: null, deckSlug: null, spreadSlug: null })).toBe(false);
  });
});

describe("reversals toggle (D-07)", () => {
  test("toggleReversals flips only reversalsEnabled", () => {
    useSelection.setState({ topic: "love" });
    expect(useSelection.getState().reversalsEnabled).toBe(false);
    useSelection.getState().toggleReversals();
    expect(useSelection.getState().reversalsEnabled).toBe(true);
    expect(useSelection.getState().topic).toBe("love");
    useSelection.getState().toggleReversals();
    expect(useSelection.getState().reversalsEnabled).toBe(false);
  });
});

describe("step machine + history-backed in-app back (D-02 / D-03)", () => {
  test("goTo sets step and pushes the previous step onto history", () => {
    useSelection.getState().goTo("selection");
    expect(useSelection.getState().step).toBe("selection");
    expect(useSelection.getState().history).toEqual(["onboarding"]);

    useSelection.getState().goTo("ritual");
    expect(useSelection.getState().step).toBe("ritual");
    expect(useSelection.getState().history).toEqual(["onboarding", "selection"]);
  });

  test("back pops history and restores the prior step", () => {
    useSelection.getState().goTo("selection");
    useSelection.getState().goTo("ritual");
    useSelection.getState().back();
    expect(useSelection.getState().step).toBe("selection");
    expect(useSelection.getState().history).toEqual(["onboarding"]);
  });

  test("back is a no-op when history is empty", () => {
    expect(useSelection.getState().history).toEqual([]);
    useSelection.getState().back();
    expect(useSelection.getState().step).toBe("onboarding");
    expect(useSelection.getState().history).toEqual([]);
  });
});

describe("startReadingAgain preserves question + topic (D-04)", () => {
  test("returns to selection WITHOUT clearing question or topic", () => {
    useSelection.setState({
      step: "result",
      topic: "love",
      deckSlug: "moon_mirror",
      spreadSlug: "three_card",
      question: "про работу",
    });
    useSelection.getState().startReadingAgain();
    const s = useSelection.getState();
    expect(s.step).toBe("selection");
    expect(s.question).toBe("про работу");
    expect(s.topic).toBe("love");
    // deck/spread stay as-is (re-selectable on the selection screen, not cleared).
    expect(s.deckSlug).toBe("moon_mirror");
    expect(s.spreadSlug).toBe("three_card");
  });

  test("does NOT clear the prior reading slot", () => {
    const reading = makeReading();
    useSelection.setState({ step: "result", reading });
    useSelection.getState().startReadingAgain();
    expect(useSelection.getState().reading).toBe(reading);
  });
});

describe("reading slot — the 03-03 writer → 03-04/05/06 reader contract", () => {
  test("setReading writes the reading slot", () => {
    const reading = makeReading();
    useSelection.getState().setReading(reading);
    expect(useSelection.getState().reading).toEqual(reading);
  });

  test("setReading(null) clears the slot back to null", () => {
    useSelection.getState().setReading(makeReading());
    useSelection.getState().setReading(null);
    expect(useSelection.getState().reading).toBeNull();
  });

  test("setReading mutates ONLY reading (no cross-field mutation)", () => {
    useSelection.setState({
      topic: "love",
      deckSlug: "moon_mirror",
      spreadSlug: "three_card",
      question: "вопрос",
      step: "ritual",
    });
    useSelection.getState().setReading(makeReading());
    const s = useSelection.getState();
    expect(s.topic).toBe("love");
    expect(s.deckSlug).toBe("moon_mirror");
    expect(s.spreadSlug).toBe("three_card");
    expect(s.question).toBe("вопрос");
    expect(s.step).toBe("ritual");
  });
});
