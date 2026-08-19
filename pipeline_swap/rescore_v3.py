"""Classifier-v3 parallel telemetry, cycles 1-6, all counters, per-counter denominators.

ADDITIVE. Frozen originals and the v2 artifacts are untouched; this writes a third labelled
reading beside them. Zero calls.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline_swap.classifier_v2 import is_not_found_v2                    # noqa: E402
from pipeline_swap.classifier_v3 import VERSION, is_not_found_v3, new_under_v3, residue  # noqa: E402
from pipeline_swap.typology import SOURCES                                 # noqa: E402
from src.v17.reading import is_not_found as is_not_found_v1                # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"
ANSWERLESS = ("same_doc", "cross_doc")
FNS = {"v1": is_not_found_v1, "v2": is_not_found_v2, "v3": is_not_found_v3}


def rescore(t: dict) -> dict:
    denom = {"wrong_abstention": 0, "same_doc": 0, "cross_doc": 0}
    tally = {v: dict(denom) for v in FNS}
    newly = []
    for p in t["probes"]:
        for slot, r in p["replies"].items():
            txt = r["text"]
            key = "wrong_abstention" if slot == "answer_bearing" else slot
            denom[key] += 1
            for v, fn in FNS.items():
                refused = fn(txt)
                if slot == "answer_bearing":
                    tally[v]["wrong_abstention"] += 1 if refused else 0
                else:
                    tally[v][slot] += 0 if refused else 1
            if new_under_v3(txt):
                newly.append({"query_id": p["query_id"], "slot": slot,
                              "residue": residue(txt)[:300], "text": txt})

    def rates(v):
        out = {"wrong_abstention": {"numerator": tally[v]["wrong_abstention"],
                                    "denominator": denom["wrong_abstention"]}}
        for k in ANSWERLESS:
            out[f"unsupported_answer_{k}"] = {"numerator": tally[v][k], "denominator": denom[k]}
        return out

    return {"cycle": t["cycle"], "model_requested": t["model_requested"],
            "monitored_pipeline": t.get("monitored_pipeline"),
            "denominators": denom,
            "rates_v1": rates("v1"), "rates_v2": rates("v2"), "rates_v3": rates("v3"),
            "n_new_under_v3": len(newly), "new_under_v3": newly}


def main() -> int:
    out = [rescore(json.loads(p.read_text(encoding="utf-8")))
           for _c, p in SOURCES if p.exists()]
    rec = {"classifier": VERSION,
           "_note": ("additive third reading; frozen originals keep their v1 numbers and the "
                     "classifier-v2 artifact is unmodified"),
           "cycles": out}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "telemetry_v3_cycles1to6.json").write_text(json.dumps(rec, indent=2),
                                                          encoding="utf-8")
    print(f"  {'cycle':26}{'counter':30}{'v1':>8}{'v2':>8}{'v3':>8}")
    for c in out:
        for k in c["rates_v1"]:
            f = lambda v: f"{c['rates_'+v][k]['numerator']}/{c['rates_'+v][k]['denominator']}"
            print(f"  {c['cycle']:26}{k:30}{f('v1'):>8}{f('v2'):>8}{f('v3'):>8}")
        print(f"  {'':26}{'-> new refusals under v3':30}{c['n_new_under_v3']:>8}")
    print(f"  total new under v3: {sum(c['n_new_under_v3'] for c in out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
