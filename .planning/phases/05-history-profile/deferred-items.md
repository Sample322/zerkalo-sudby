# Phase 05 — Deferred Items (out-of-scope discoveries)

Discoveries logged during execution that are NOT caused by the current plan's changes.
Per the executor scope boundary, these are recorded but NOT fixed here.

| Discovered During | File | Issue | Notes |
|-------------------|------|-------|-------|
| 05-04 (full `ruff check app/`) | `backend/app/models/spread.py:38,56` | `UP037` — quotes on forward-ref type annotations (`Mapped[list["SpreadPosition"]]`, `Mapped["SpreadType"]`) | Pre-existing since Phase 2; NOT in 05-04's touched files. Auto-fixable with `ruff check --fix`. Out of scope for 05-04 (only `services/reading.py` + `api/readings.py` were modified). Safe to clean up in a dedicated chore or the Phase-5 code-review pass. |
