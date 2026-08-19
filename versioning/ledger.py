"""Versioning ledger — own ceiling, pinned on BOTH surfaces (build spec §3, §5).

The generalised standing order, in the form the canary's second defect earned: *a parameter has
as many surfaces as it has readers, and the binding test must pin every surface, not only the one
that throws.* `SpendLedger` exposes two — `record()` enforces and `totals()` reports — and both
read v1.8's `CALL_CEILING`. Overriding only the throwing one produces a ledger that binds at 120
while telling its reader the budget is 25,000.
"""
from __future__ import annotations

from pathlib import Path

from v18.ledger import CeilingBreached, SpendLedger

VERSIONING_CEILING = 120


class VersioningLedger(SpendLedger):
    def __init__(self, path: Path):
        super().__init__(path)
        data = self.read()
        if data.get("experiment") != "versioning-prototype":
            data.update({"experiment": "versioning-prototype", "ceiling": VERSIONING_CEILING,
                         "frozen_projection": None,
                         "_note": ("append-only. Ceiling is the versioning build's 120, not "
                                   "v1.8's 25,000.")})
            self._write(data)

    def totals(self) -> dict:
        """The reporting surface."""
        t = super().totals()
        t["ceiling"] = VERSIONING_CEILING
        t["headroom_against_ceiling"] = VERSIONING_CEILING - t["calls"]
        t["frozen_projection"] = None
        return t

    def record(self, stage: str, calls: int, input_tokens: int = 0, output_tokens: int = 0,
               batch_id: str | None = None, note: str = "") -> dict:
        """The enforcement surface."""
        totals = super().record(stage, calls, input_tokens, output_tokens, batch_id, note)
        if totals["calls"] > VERSIONING_CEILING:
            raise CeilingBreached(
                f"recorded spend {totals['calls']:,} passed the versioning build's "
                f"{VERSIONING_CEILING:,} call ceiling (§3). STOP.")
        return totals
