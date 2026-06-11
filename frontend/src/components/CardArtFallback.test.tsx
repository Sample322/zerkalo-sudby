import { render } from "@testing-library/react";
import { expect, test } from "vitest";

import { CardArt } from "./CardArtFallback";

test("renders an atmospheric fallback (role=img, no <img>) when src is null (DECK-05)", () => {
  const { container } = render(<CardArt src={null} alt="Колода Луны" />);

  const fallback = container.querySelector('[role="img"]');
  expect(fallback).not.toBeNull();
  expect(fallback?.getAttribute("aria-label")).toBe("Колода Луны");
  // No <img> -> no network request for absent art.
  expect(container.querySelector("img")).toBeNull();
});

test("renders a real <img> when a src is provided", () => {
  const { container } = render(<CardArt src="/art/moon.png" alt="Карта" />);

  const img = container.querySelector("img");
  expect(img).not.toBeNull();
  expect(img?.getAttribute("src")).toBe("/art/moon.png");
});
