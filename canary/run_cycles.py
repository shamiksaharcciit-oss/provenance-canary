"""Canary demonstration run (build spec §2): baseline, stability, induced change.

Cycle 1 and 2 are identical configurations on `claude-sonnet-5`; cycle 3 swaps the generator to
`claude-haiku-4-5-20251001` and changes nothing else, simulating an unannounced production model
swap. Nothing is tuned to enlarge the movement — the cycles are reported as they land.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT = ROOT / "canary" / "results"
SONNET = "claude-sonnet-5"
HAIKU = "claude-haiku-4-5-20251001"
CYCLES = (("cycle1_baseline", SONNET), ("cycle2_stability", SONNET),
          ("cycle3_model_swap", HAIKU))


def main() -> int:
    from src import config as C
    from canary.ledger import CanaryLedger
    from canary.runner import run_cycle
    from canary.store import build_store

    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    store_path = OUT / "probe_store.json"
    store = (json.loads(store_path.read_text(encoding="utf-8")) if store_path.exists()
             else build_store(store_path))
    print(f"  store {store['size']} probes; census {store['census']['answerless_packages_checked']} "
          f"answerless checked, {store['census']['gold_overlaps_found']} overlaps, "
          f"{len(store['excluded'])} excluded")

    ledger = CanaryLedger(OUT / "ledger.json")
    recs = []
    for cid, model in CYCLES:
        path = OUT / f"telemetry_{cid}.json"
        if path.exists():
            rec = json.loads(path.read_text(encoding="utf-8"))
            print(f"  {cid}: already recorded, skipping")
        else:
            rec = run_cycle(store, model, cfg, Path(cfg["_cache_root"]), ledger, cid, OUT)
        recs.append(rec)
        r = rec["rates"]
        print(f"  {cid:20} {rec['model_requested']:26} "
              f"wrong_abstention {r['wrong_abstention']['numerator']}/{r['wrong_abstention']['denominator']}  "
              f"unsupported same_doc {r['unsupported_answer_same_doc']['numerator']}/"
              f"{r['unsupported_answer_same_doc']['denominator']}  "
              f"cross_doc {r['unsupported_answer_cross_doc']['numerator']}/"
              f"{r['unsupported_answer_cross_doc']['denominator']}  "
              f"({rec['cost']['llm_calls']} calls)")

    tot = ledger.totals()
    (OUT / "cycles_summary.json").write_text(json.dumps(
        {"cycles": [{k: v for k, v in r.items() if k != "probes"} for r in recs],
         "ledger_totals": tot}, indent=2), encoding="utf-8")
    print(f"  ledger: {tot['calls']} calls of 400")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
