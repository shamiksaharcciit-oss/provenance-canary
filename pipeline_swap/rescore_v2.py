"""Corrected cycles 1-5 telemetry under classifier-v2. ADDITIVE ONLY, zero calls.

Reads the frozen telemetry read-only and writes parallel artifacts labelled `classifier-v2`
under pipeline_swap/. Nothing under canary/ or versioning/ is touched; the originals keep their
v1 numbers and remain the record of what was published.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline_swap.classifier_v2 import VERSION, disagrees, is_not_found_v2   # noqa: E402
from pipeline_swap.typology import SOURCES                                    # noqa: E402
from src.v17.reading import is_not_found as is_not_found_v1                   # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"
ANSWERLESS = ("same_doc", "cross_doc")


def rescore_one(t: dict) -> dict:
    """Recount one cycle under v2. Per-counter denominators, from what each probe actually has."""
    counts = {"wrong_abstention": 0, "unsupported_answer": {k: 0 for k in ANSWERLESS}}
    denom = {"wrong_abstention": 0, **{k: 0 for k in ANSWERLESS}}
    flips = []
    for p in t["probes"]:
        for slot, r in p["replies"].items():
            txt = r["text"]
            refusal_v2 = is_not_found_v2(txt)
            if slot == "answer_bearing":
                denom["wrong_abstention"] += 1
                counts["wrong_abstention"] += 1 if refusal_v2 else 0
            else:
                denom[slot] += 1
                counts["unsupported_answer"][slot] += 0 if refusal_v2 else 1
            if disagrees(txt):
                flips.append({"query_id": p["query_id"], "slot": slot,
                              "v1": "ANSWER" if not is_not_found_v1(txt) else "REFUSAL",
                              "v2": "REFUSAL" if refusal_v2 else "ANSWER", "text": txt})
    rates = {"wrong_abstention": {"numerator": counts["wrong_abstention"],
                                  "denominator": denom["wrong_abstention"]}}
    for k in ANSWERLESS:
        rates[f"unsupported_answer_{k}"] = {"numerator": counts["unsupported_answer"][k],
                                            "denominator": denom[k]}
    for v in rates.values():
        v["rate"] = round(v["numerator"] / v["denominator"], 6) if v["denominator"] else None
    return {"cycle": t["cycle"], "classifier": VERSION, "model_requested": t["model_requested"],
            "monitored_pipeline": t.get("monitored_pipeline"),
            "rates_v2": rates, "rates_v1_as_published": t["rates"],
            "n_flips": len(flips), "flips": flips}


def main() -> int:
    out = []
    for cycle, path in SOURCES:
        if not path.exists():
            continue
        t = json.loads(path.read_text(encoding="utf-8"))
        out.append(rescore_one(t))
    RESULTS.mkdir(parents=True, exist_ok=True)
    rec = {"classifier": VERSION, "source": "frozen telemetry, read-only",
           "_note": ("additive correction; the frozen originals are unmodified and keep their "
                     "v1 numbers as the record of what was published"),
           "cycles": out}
    (RESULTS / "telemetry_v2_cycles1to5.json").write_text(json.dumps(rec, indent=2),
                                                          encoding="utf-8")
    print(f"  {'cycle':26} {'counter':22} {'v1':>9} {'v2':>9}  flips")
    for c in out:
        for k, v2 in c["rates_v2"].items():
            v1 = c["rates_v1_as_published"].get(k, {})
            print(f"  {c['cycle']:26} {k:22} "
                  f"{str(v1.get('numerator','-'))+'/'+str(v1.get('denominator','-')):>9} "
                  f"{str(v2['numerator'])+'/'+str(v2['denominator']):>9}"
                  f"{('  '+str(c['n_flips'])) if k=='wrong_abstention' else ''}")
    print(f"  total flips v1->v2: {sum(c['n_flips'] for c in out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
