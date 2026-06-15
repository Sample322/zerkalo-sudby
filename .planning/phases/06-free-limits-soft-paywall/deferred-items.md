# Phase 06 — Deferred Items

Out-of-scope discoveries during execution, carried forward (NOT fixed in this phase per the
executor SCOPE BOUNDARY rule — only issues directly caused by the current task are auto-fixed).

| Found During | Location | Issue | Disposition |
|--------------|----------|-------|-------------|
| 06-02 (full `ruff check app/`) | `backend/app/models/spread.py:38,56` | `UP037` — quotes on forward-ref type annotations (`Mapped[list["SpreadPosition"]]`, `Mapped["SpreadType"]`) | Pre-existing since Phase 2 (already logged in `05-history-profile/deferred-items.md`); NOT in any 06-02 touched file. Auto-fixable with `ruff check --fix`. Out of scope for 06-02 (only `services/reading.py`, `schemas/reading.py`, `tests/integration/test_readings_limit.py` were modified). Clean up in the deferred Phase-4/5/6 `/gsd-code-review` pass. |
