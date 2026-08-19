"""Continuity demonstration — cycle 4 (build spec §1.4). The only part that calls a model.

The migrated store, run against version 2, on the baseline generator. Same telemetry format as
cycles 1-3; the denominator is the SURVIVING probe count and is stated explicitly, because a
monitor whose denominator changes silently across a corpus release is worse than no monitor.

`canary.runner.run_cycle` is imported BY IDENTITY -- cycle 4 is the same loop as cycles 1-3, not
a reimplementation of it, which is the whole claim continuity rests on.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

V = ROOT / "versioning" / "results"
SONNET = "claude-sonnet-5"
CYCLE = "cycle4_after_release"


def main() -> int:
    from src import config as C
    from canary.runner import run_cycle          # identity import: the same loop
    from versioning.ledger import VersioningLedger

    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    store = json.loads((V / "probe_store_v2.json").read_text(encoding="utf-8"))
    print(f"  migrated store: {store['size']} probes ({store['n_retired']} retired), "
          f"census {store['census']['answerless_packages_checked']} checked / "
          f"{store['census']['gold_overlaps_found']} overlaps")

    path = V / f"telemetry_{CYCLE}.json"
    ledger = VersioningLedger(V / "ledger.json")
    if path.exists():
        rec = json.loads(path.read_text(encoding="utf-8"))
        print("  cycle 4 already recorded, skipping")
    else:
        rec = run_cycle(store, SONNET, cfg, Path(cfg["_cache_root"]), ledger, CYCLE, V)
    r = rec["rates"]
    print(f"  {CYCLE}: requested={rec['model_requested']} served={rec['model_served']} "
          f"n={rec['n_probes']}")
    print(f"    wrong_abstention {r['wrong_abstention']['numerator']}/{r['wrong_abstention']['denominator']}  "
          f"same_doc {r['unsupported_answer_same_doc']['numerator']}/{r['unsupported_answer_same_doc']['denominator']}  "
          f"cross_doc {r['unsupported_answer_cross_doc']['numerator']}/{r['unsupported_answer_cross_doc']['denominator']}")
    t = ledger.totals()
    print(f"  ledger: {t['calls']} calls, ceiling {t['ceiling']}, headroom {t['headroom_against_ceiling']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
