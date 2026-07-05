"""Guard: no test imports the real ЮKassa SDK (T-07-TEST-LIVE, self-enforcing).

``FakeYooKassa`` (``tests/integration/fakes_payments.py``) is the ONLY ЮKassa surface the suite ever
touches — no test may import the real ``yookassa`` package or name its live host, which would risk a
real API call / real money moving in CI. The P7 security audit verified this by a manual grep; this
test makes the invariant self-enforcing against future drift (a new test that ``import``s the SDK
fails here loudly, with the offending file named).

No DB / network — a pure source scan over ``backend/tests``.
"""

from __future__ import annotations

import re
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent

# A REAL-SDK import: ``import yookassa`` / ``from yookassa import …`` at line start (``\b`` so it does
# NOT match our ``fakes_payments`` / prose mentions, and the keyword anchor ignores docstring text).
_REAL_SDK_IMPORT = re.compile(r"^\s*(?:import\s+yookassa\b|from\s+yookassa\b)", re.MULTILINE)

# The live ЮKassa API host — assembled from parts so THIS guard file does not itself contain the
# literal it forbids (it scans every OTHER test module for it).
_LIVE_HOST = "api." + "yookassa" + ".ru"


def test_no_test_imports_real_yookassa_sdk() -> None:
    """Fail if any test module imports the real ЮKassa SDK or names its live host."""
    self_path = Path(__file__).resolve()
    offenders: list[str] = []
    for path in _TESTS_DIR.rglob("*.py"):
        if path.resolve() == self_path:
            continue  # skip self — it necessarily references the forbidden tokens
        source = path.read_text(encoding="utf-8")
        if _REAL_SDK_IMPORT.search(source) or _LIVE_HOST in source:
            offenders.append(path.relative_to(_TESTS_DIR).as_posix())

    assert not offenders, (
        "Real ЮKassa SDK import / live host found in tests — use FakeYooKassa instead "
        f"(threat T-07-TEST-LIVE). Offending files: {', '.join(offenders)}"
    )
