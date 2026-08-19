"""Retirement-demo ledger — own ceiling, both surfaces pinned (build spec §5).

The standing rule in its earned form: a parameter has as many surfaces as it has readers, and
the binding test must pin every surface, not only the one that throws. `SpendLedger` exposes
`record()` (enforces) and `totals()` (reports); both read v1.8's constant, so both are overridden.
"""
from __future__ import annotations

from pathlib import Path

from v18.ledger import CeilingBreached, SpendLedger

DEMO_CEILING = 110


class RetirementDemoLedger(SpendLedger):
    def __init__(self, path: Path):
        super().__init__(path)
        d = self.read()
        if d.get("experiment") != "retirement-demo":
            d.update({"experiment": "retirement-demo", "ceiling": DEMO_CEILING,
                      "frozen_projection": None,
                      "_note": "append-only. Ceiling is this build's 110, not v1.8's 25,000."})
            self._write(d)

    def totals(self) -> dict:
        t = super().totals()
        t["ceiling"] = DEMO_CEILING
        t["headroom_against_ceiling"] = DEMO_CEILING - t["calls"]
        t["frozen_projection"] = None
        return t

    def record(self, stage: str, calls: int, input_tokens: int = 0, output_tokens: int = 0,
               batch_id: str | None = None, note: str = "") -> dict:
        t = super().record(stage, calls, input_tokens, output_tokens, batch_id, note)
        if t["calls"] > DEMO_CEILING:
            raise CeilingBreached(
                f"recorded spend {t['calls']:,} passed this build's {DEMO_CEILING:,} call "
                f"ceiling (§5). STOP.")
        return t
