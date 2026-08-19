"""Pipeline-swap ledger — own ceiling 110, both surfaces pinned (build spec §3)."""
from __future__ import annotations
from pathlib import Path
from v18.ledger import CeilingBreached, SpendLedger

SWAP_CEILING = 110


class PipelineSwapLedger(SpendLedger):
    def __init__(self, path: Path):
        super().__init__(path)
        d = self.read()
        if d.get("experiment") != "pipeline-swap":
            d.update({"experiment": "pipeline-swap", "ceiling": SWAP_CEILING,
                      "frozen_projection": None,
                      "_note": "append-only. Ceiling is this build's 110, not v1.8's 25,000."})
            self._write(d)

    def totals(self) -> dict:
        t = super().totals()
        t["ceiling"] = SWAP_CEILING
        t["headroom_against_ceiling"] = SWAP_CEILING - t["calls"]
        t["frozen_projection"] = None
        return t

    def record(self, stage: str, calls: int, input_tokens: int = 0, output_tokens: int = 0,
               batch_id: str | None = None, note: str = "") -> dict:
        t = super().record(stage, calls, input_tokens, output_tokens, batch_id, note)
        if t["calls"] > SWAP_CEILING:
            raise CeilingBreached(
                f"recorded spend {t['calls']:,} passed this build's {SWAP_CEILING:,} ceiling.")
        return t
