"""Canary ledger — its own ceiling, binding, per the standing order (§4).

The generalised order from v1.11's Gate 1: *no experiment-scoped parameter (model, ceiling,
budget, guard, path) is ever inherited from another experiment's defaults; every
cross-experiment import overrides them explicitly, and a test asserts the override.*

`v18.ledger.SpendLedger` gives crash-survivable atomic storage and an append-only entry shape,
both wanted. Its ceiling is v1.8's 25,000, which is not this build's. The canary ceiling is
**400 calls** and it is enforced here.
"""
from __future__ import annotations

from pathlib import Path

from v18.ledger import CeilingBreached, SpendLedger

CANARY_CEILING = 400


class CanaryLedger(SpendLedger):
    """`SpendLedger` storage under the canary's own ceiling."""

    def __init__(self, path: Path):
        super().__init__(path)
        data = self.read()
        if data.get("experiment") != "canary-prototype":
            data.update({"experiment": "canary-prototype", "ceiling": CANARY_CEILING,
                         "frozen_projection": None,
                         "_note": ("append-only; actuals from API usage. Ceiling is the "
                                   "canary's 400, not v1.8's 25,000.")})
            self._write(data)

    def totals(self) -> dict:
        """The parent reads `CALL_CEILING` from v1.8's module, so its `totals()` REPORTS v1.8's
        25,000 even here — enforcement was overridden, reporting was not. A ledger that binds at
        400 while telling the reader 400 is 1.6% of its budget is a different defect from the one
        the subclass fixed, and the same genus: a foreign default reaching in.
        """
        t = super().totals()
        t["ceiling"] = CANARY_CEILING
        t["headroom_against_ceiling"] = CANARY_CEILING - t["calls"]
        t["frozen_projection"] = None
        return t

    def record(self, stage: str, calls: int, input_tokens: int = 0, output_tokens: int = 0,
               batch_id: str | None = None, note: str = "") -> dict:
        totals = super().record(stage, calls, input_tokens, output_tokens, batch_id, note)
        if totals["calls"] > CANARY_CEILING:
            raise CeilingBreached(
                f"recorded spend {totals['calls']:,} passed the canary's {CANARY_CEILING:,} "
                f"call ceiling (§3). STOP.")
        return totals
