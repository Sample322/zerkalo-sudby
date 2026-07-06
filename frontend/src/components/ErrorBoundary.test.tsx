// ErrorBoundary (UI-05) — an unexpected render error shows the in-voice fallback, never a crash or a
// stack trace; a healthy tree renders through untouched.

import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { ErrorBoundary } from "./ErrorBoundary";
import { APP_ERROR_TITLE } from "../reading/copy";

function Boom(): never {
  throw new Error("boom");
}

afterEach(() => vi.restoreAllMocks());

test("renders the in-voice fallback when a child throws (no crash, no stack shown)", () => {
  // React logs the caught error to console.error — silence the expected noise.
  vi.spyOn(console, "error").mockImplementation(() => {});
  render(
    <ErrorBoundary>
      <Boom />
    </ErrorBoundary>,
  );
  expect(screen.getByText(APP_ERROR_TITLE)).toBeTruthy();
});

test("renders children normally when nothing throws", () => {
  render(
    <ErrorBoundary>
      <div>всё спокойно</div>
    </ErrorBoundary>,
  );
  expect(screen.getByText("всё спокойно")).toBeTruthy();
});
