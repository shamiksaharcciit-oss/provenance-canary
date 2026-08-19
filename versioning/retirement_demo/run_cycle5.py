"""Cycle 5 — the surviving store against corpus v3 (build spec §4). The only stage that spends.

Denominator 27, stated in every number: three probes were retired when the release rewrote their
answer spans, and a monitor whose denominator moves silently across a release is worse than none.
`canary.runner.run_cycle` is imported BY IDENTITY -- cycle 5 is the same loop as cycles 1-4.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

RESULTS = Path(__file__).resolve().parent / "results"
SONNET = "claude-sonnet-5"
CYCLE = "cycle5_after_retirement"


def main() -> int:
    from src import config as C
    from canary.runner import run_cycle
    from versioning.retirement_demo.ledger import RetirementDemoLedger

    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(_ROOT / "cache"))
    store = json.loads((RESULTS / "probe_store_v3.json").read_text(encoding="utf-8"))
    print(f"  surviving store: {store['size']} probes ({store['n_retired']} retired), "
          f"census {store['census']['answerless_packages_checked']} checked / "
          f"{store['census']['gold_overlaps_found']} overlaps")

    ledger = RetirementDemoLedger(RESULTS / "ledger.json")
    path = RESULTS / f"telemetry_{CYCLE}.json"
    if path.exists():
        rec = json.loads(path.read_text(encoding="utf-8"))
        print("  cycle 5 already recorded, skipping")
    else:
        rec = run_cycle(store, SONNET, cfg, Path(cfg["_cache_root"]), ledger, CYCLE, RESULTS)
    r = rec["rates"]
    print(f"  {CYCLE}: requested={rec['model_requested']} served={rec['model_served']} "
          f"DENOMINATOR n={rec['n_probes']}")
    print(f"    wrong_abstention {r['wrong_abstention']['numerator']}/{r['wrong_abstention']['denominator']}  "
          f"same_doc {r['unsupported_answer_same_doc']['numerator']}/{r['unsupported_answer_same_doc']['denominator']}  "
          f"cross_doc {r['unsupported_answer_cross_doc']['numerator']}/{r['unsupported_answer_cross_doc']['denominator']}")
    t = ledger.totals()
    print(f"  ledger: {t['calls']} calls, ceiling {t['ceiling']}, headroom {t['headroom_against_ceiling']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
