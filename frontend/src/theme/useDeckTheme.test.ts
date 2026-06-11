import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, test } from "vitest";

import { useSelection } from "../stores/selection";
import { useDeckTheme } from "./useDeckTheme";

beforeEach(() => {
  useSelection.setState({ topic: null, deckSlug: null, spreadSlug: null });
});

afterEach(() => {
  document.documentElement.removeAttribute("data-deck");
});

test("flips data-deck on deck selection and clears it on null (UI-02)", () => {
  renderHook(() => useDeckTheme());

  act(() => {
    useSelection.getState().setDeck("moon_mirror");
  });
  expect(document.documentElement.dataset.deck).toBe("moon_mirror");

  act(() => {
    useSelection.getState().setDeck(null);
  });
  expect(document.documentElement.dataset.deck).toBe("");
});
