import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";

// Self-hosted ritual typography (bundled — no external CDN, reliable over filtered networks).
// Playfair Display = the high-contrast display face (headings, card names, eyebrows);
// Cormorant Garamond = the elegant body face (questions, interpretations, the итог). Both carry
// Cyrillic — the @fontsource weight css ships every subset, the browser lazy-loads cyrillic
// woff2 via unicode-range, so Russian copy renders in the real face (never a fallback).
import "@fontsource/playfair-display/500.css";
import "@fontsource/playfair-display/600.css";
import "@fontsource/playfair-display/700.css";
import "@fontsource/cormorant-garamond/400.css";
import "@fontsource/cormorant-garamond/500.css";
import "@fontsource/cormorant-garamond/600.css";
import "@fontsource/cormorant-garamond/400-italic.css";
import "@fontsource/cormorant-garamond/500-italic.css";

import App from "./App.tsx";
import { queryClient } from "./lib/queryClient";
import "./index.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root not found");
}

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
