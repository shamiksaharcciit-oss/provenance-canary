"""Cycle 6 — the monitored pipeline changes to U256 (build spec Part A §4).

**A NECESSARY DIVERGENCE, DECLARED.** The spec says run the cycle via `canary.runner.run_cycle`
by identity. That function cannot express what the amendment requires: it assumes every probe has
all three legs (A-014's cross-doc leg is cascade-retired) and it reports a single denominator
(the amendment mandates per-counter denominators). It also scores under one classifier, and the
Part B ruling requires cycle 6 scored under v1 and v2 side by side.

So the loop lives here. Everything that *scores or calls* is still imported by identity: the
prompt renderer and pinned client from `canary.runner`, the v1 classifier from `v111.unanswerable`
via that module, and `is_not_found_v2` from this build's versioned instrument. Only the iteration
and tallying are local, and those are what the amendment changed.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canary.runner import make_client, render                    # noqa: E402  identity imports
from pipeline_swap.classifier_v2 import is_not_found_v2          # noqa: E402
from pipeline_swap.ledger import PipelineSwapLedger              # noqa: E402
from src.v17.reading import is_not_found as is_not_found_v1      # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"
SONNET = "claude-sonnet-5"
CYCLE = "cycle6_pipeline_swap"
ANSWERLESS = ("same_doc", "cross_doc")


def main() -> int:
    from src import config as C

    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    store = json.loads((RESULTS / "probe_store_u256.json").read_text(encoding="utf-8"))
    path = RESULTS / f"telemetry_{CYCLE}.json"
    if path.exists():
        rec = json.loads(path.read_text(encoding="utf-8"))
        print("  cycle 6 already recorded, skipping")
    else:
        cl = make_client(SONNET, cfg, Path(cfg["_cache_root"]))
        ledger = PipelineSwapLedger(RESULTS / "ledger.json")
        rows, t0 = [], time.time()
        tally = {v: {"wrong_abstention": 0, "same_doc": 0, "cross_doc": 0} for v in ("v1", "v2")}
        denom = {"wrong_abstention": 0, "same_doc": 0, "cross_doc": 0}
        for p in store["probes"]:
            row = {"query_id": p["query_id"], "replies": {}}
            for slot, pkg in p["packages"].items():
                text = cl.complete_uncached(render(pkg, p["question"]))
                r1, r2 = is_not_found_v1(text), is_not_found_v2(text)
                key = "wrong_abstention" if slot == "answer_bearing" else slot
                denom[key] += 1
                for v, refused in (("v1", r1), ("v2", r2)):
                    if slot == "answer_bearing":
                        tally[v]["wrong_abstention"] += 1 if refused else 0
                    else:
                        tally[v][slot] += 0 if refused else 1
                row["replies"][slot] = {"text": text, "refusal_v1": r1, "refusal_v2": r2}
            row["retired_legs"] = [c["leg"] for c in store["cascade_retirements"]
                                   if c["query_id"] == p["query_id"]]
            rows.append(row)
        seen = sorted(set(cl.models_seen))
        assert seen == [SONNET], f"APPARATUS-STOP: response.model {seen} != [{SONNET!r}]"
        cs = cl.cost_summary()
        ledger.record(stage=CYCLE, calls=cs["llm_calls"], input_tokens=cs["input_tokens"],
                      output_tokens=cs["output_tokens"], note=f"cycle 6 on {SONNET}, U256")

        def rates(v):
            return {"wrong_abstention": {"numerator": tally[v]["wrong_abstention"],
                                         "denominator": denom["wrong_abstention"]},
                    **{f"unsupported_answer_{k}": {"numerator": tally[v][k],
                                                   "denominator": denom[k]} for k in ANSWERLESS}}
        rec = {"cycle": CYCLE,
               "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "monitored_pipeline": store["monitored_arm"],
               "previous_monitored_pipeline": store["previous_monitored_arm"],
               "corpus": store["corpus"], "model_requested": SONNET, "model_served": seen,
               "denominators": denom, "cascade_retirements": store["cascade_retirements"],
               "rates": rates("v1"), "rates_v2": rates("v2"),
               "_note": "per-counter denominators; scored under classifier v1 and v2 side by side",
               "cost": cs, "seconds": round(time.time() - t0, 1), "probes": rows}
        RESULTS.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rec, indent=2), encoding="utf-8")

    print(f"  {CYCLE}: {rec['previous_monitored_pipeline']} -> {rec['monitored_pipeline']} "
          f"on corpus {rec['corpus']}, served {rec['model_served']}")
    for v, key in (("v1", "rates"), ("v2", "rates_v2")):
        r = rec[key]
        print(f"    {v}: wrong_abstention {r['wrong_abstention']['numerator']}/"
              f"{r['wrong_abstention']['denominator']}  "
              f"same_doc {r['unsupported_answer_same_doc']['numerator']}/"
              f"{r['unsupported_answer_same_doc']['denominator']}  "
              f"cross_doc {r['unsupported_answer_cross_doc']['numerator']}/"
              f"{r['unsupported_answer_cross_doc']['denominator']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
