import { fireEvent, render } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import type { Deck } from "../api/decks";
import { DeckCarousel } from "./DeckCarousel";

const DECKS: Deck[] = Array.from({ length: 6 }, (_, i) => ({
  slug: `deck_${i}`,
  title: `Колода ${i}`,
  subtitle: null,
  description: null,
  atmosphere: "ночь",
  tone: "мягкий",
  prompt_modifier: null,
  visual_style: {},
  recommended_topics: ["general"],
  access_type: "free",
  sort_order: i,
}));

test("renders every deck and forwards selection by slug", () => {
  const onSelect = vi.fn();
  const { getByText } = render(
    <DeckCarousel decks={DECKS} selectedSlug={null} onSelect={onSelect} />,
  );

  for (const deck of DECKS) {
    expect(getByText(deck.title)).toBeTruthy();
  }

  fireEvent.click(getByText("Колода 0"));
  expect(onSelect).toHaveBeenCalledWith("deck_0");
});

test("renders nothing-broken for an empty deck list", () => {
  const { container } = render(
    <DeckCarousel decks={[]} selectedSlug={null} onSelect={() => {}} />,
  );
  expect(container.querySelector('[role="list"]')).toBeNull();
});
