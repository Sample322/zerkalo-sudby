import { beforeEach, describe, expect, test } from "vitest";

import { useSelection } from "./selection";

beforeEach(() => {
  useSelection.setState({ topic: null, deckSlug: null, spreadSlug: null });
});

describe("useSelection", () => {
  test("initial state is all null", () => {
    const s = useSelection.getState();
    expect(s.topic).toBeNull();
    expect(s.deckSlug).toBeNull();
    expect(s.spreadSlug).toBeNull();
  });

  test("setDeck updates only deckSlug (no server data, no cross-field mutation)", () => {
    useSelection.getState().setDeck("moon_mirror");
    const s = useSelection.getState();
    expect(s.deckSlug).toBe("moon_mirror");
    expect(s.topic).toBeNull();
    expect(s.spreadSlug).toBeNull();
  });
});
