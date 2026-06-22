import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";

// Self-hosted ritual typography (bundled — no external CDN, reliable over filtered networks).
// Forum = the display face (headings, card names, eyebrows) — Roman inscriptional capitals with
// an ancient, mystical character. Lora = the body face (questions, interpretations, the итог) —
// a warm, substantial, highly readable serif. Both carry Cyrillic — the @fontsource weight css
// ships every subset and the browser lazy-loads the cyrillic woff2 via unicode-range, so Russian
// copy always renders in the real face.
import "@fontsource/forum/400.css";
import "@fontsource/lora/400.css";
import "@fontsource/lora/500.css";
import "@fontsource/lora/600.css";
import "@fontsource/lora/400-italic.css";
import "@fontsource/lora/500-italic.css";

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
