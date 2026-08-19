"""Follow-up: the v1.9 populations, per arm, per verdict slot. ZERO CALLS, READ-ONLY.

Ordered by the 6be78a7 ruling. The summary scan reported v1.9 in aggregate, which leaves one
number unresolved: v1.9's abstention asymmetry — `F768` 1 against `U768` 15 on `main_A` — is the
most legible figure the reading claim produced, and it is a count of exactly the thing classifier
v1 miscounts.

This table resolves that exposure and nothing else. Both classifier readings are shown side by
side as **counts**. v1 remains the classifier of record for every v1.9 number; nothing here
re-scores v1.9, and nothing under `v1*/` is modified or written.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline_swap.classifier_v2 import is_not_found_v2                # noqa: E402
from pipeline_swap.typology import S1_CONTENT_FLOOR, SENTINEL_VARIANT_RE  # noqa: E402
from src.v17.reading import NOT_FOUND, is_not_found as v1              # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"
V19 = ROOT / "v19" / "results_run"
BARE_RE = re.compile(r"(?i)^\s*not\s+found[.!;:,]*\s*$")


def rows():
    """(population, arm, slot, id, text) over every persisted v1.9 reply."""
    for name in ("main_A", "main_B"):
        p = V19 / f"{name}.json"
        if p.exists():
            for r in json.loads(p.read_text(encoding="utf-8"))["rows"]:
                for arm, a in r["arms"].items():
                    yield (name, arm, "answer", r["query_id"], a["answer"])
    p = V19 / "pr3.json"
    if p.exists():
        for r in json.loads(p.read_text(encoding="utf-8"))["rows"]:
            for arm, d in r.get("reps", {}).items():
                for i, t in enumerate(d["answers"]):
                    yield ("pr3", arm, f"rep{i}", r["query_id"], t)
    p = V19 / "control.json"
    if p.exists():
        for track, v in json.loads(p.read_text(encoding="utf-8"))["tracks"].items():
            for r in v["rows"]:
                yield (f"control-{track}", "F768", "correct", r["query_id"], r["answer_correct"])
                yield (f"control-{track}", "F768", "mismatched", r["query_id"],
                       r["answer_mismatched"])


def main() -> int:
    per: dict[tuple, Counter] = {}
    hits = []
    for pop, arm, slot, ident, text in rows():
        c = per.setdefault((pop, arm, slot), Counter())
        c["n"] += 1
        r1, r2 = v1(text), is_not_found_v2(text)
        c["refusal_v1"] += int(r1)
        c["refusal_v2"] += int(r2)
        if NOT_FOUND in text and len(text.replace(NOT_FOUND, "").strip()) >= S1_CONTENT_FLOOR:
            c["S1"] += 1
        if not r1 and SENTINEL_VARIANT_RE.search(text):
            c["S4"] += 1
        if BARE_RE.match(text) and not r1:
            c["bare_flip"] += 1
            hits.append({"population": pop, "arm": arm, "slot": slot, "id": ident,
                         "text": text.strip()})

    table = {f"{p}|{a}|{s}": dict(c) for (p, a, s), c in sorted(per.items())}
    rec = {"_note": ("read-only over v1.9's persisted replies. v1 is the classifier of record "
                     "for every v1.9 number; nothing here re-scores v1.9 and nothing under v1*/ "
                     "was modified."),
           "per_arm": table,
           "bare_sentinel_flips": hits,
           "totals": {k: sum(c.get(k, 0) for c in per.values())
                      for k in ("n", "refusal_v1", "refusal_v2", "S1", "S4", "bare_flip")}}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "exposure_v19_perarm.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")

    print(f"  {'population|arm|slot':34}{'n':>5}{'S1':>4}{'S4':>4}{'REFUSAL v1':>12}"
          f"{'REFUSAL v2':>12}{'flips':>7}")
    for k, c in table.items():
        print(f"  {k:34}{c['n']:5}{c.get('S1',0):4}{c.get('S4',0):4}"
              f"{c.get('refusal_v1',0):12}{c.get('refusal_v2',0):12}{c.get('bare_flip',0):7}")
    t = rec["totals"]
    print(f"  {'TOTAL':34}{t['n']:5}{t['S1']:4}{t['S4']:4}{t['refusal_v1']:12}"
          f"{t['refusal_v2']:12}{t['bare_flip']:7}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
