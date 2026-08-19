"""Scope extension: S1 and S4 over the frozen v1.9 and v1.11 answer populations. ZERO CALLS.

Measures the frozen record's exposure to the same classifier defect. READ-ONLY over `v19/` and
`v111/`; nothing there is touched, and no number anywhere is changed. Counts per arm per screen,
with hits quoted.
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

from pipeline_swap.typology import (HEDGE_RE, S1_CONTENT_FLOOR, SENTINEL_VARIANT_RE)  # noqa: E402
from src.v17.reading import NOT_FOUND, is_not_found                                    # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"
V19 = ROOT / "v19" / "results_run"
V111 = ROOT / "v111" / "results_run"


def screens_for(text: str) -> list[str]:
    """S1 and S4 only, per the scope extension. Same definitions as the typology."""
    hits = []
    if NOT_FOUND in text and len(text.replace(NOT_FOUND, "").strip()) >= S1_CONTENT_FLOOR:
        hits.append("S1")
    if not is_not_found(text) and SENTINEL_VARIANT_RE.search(text):
        hits.append("S4")
    return hits


def bare_sentinel(text: str) -> bool:
    return bool(re.fullmatch(r"(?i)not\s+found[.!;:,]*", text.strip())) and not is_not_found(text)


def populations():
    """(population, arm, id, text) rows from the frozen answer files."""
    for name in ("main_A", "main_B"):
        p = V19 / f"{name}.json"
        if p.exists():
            for r in json.loads(p.read_text(encoding="utf-8"))["rows"]:
                for arm, a in r["arms"].items():
                    yield (f"v19/{name}", arm, r["query_id"], a["answer"])
    p = V19 / "pr3.json"
    if p.exists():
        for r in json.loads(p.read_text(encoding="utf-8"))["rows"]:
            for arm, d in r.get("reps", {}).items():
                for i, t in enumerate(d["answers"]):
                    yield ("v19/pr3", arm, f"{r['query_id']}#r{i}", t)
    p = V19 / "control.json"
    if p.exists():
        for track, v in json.loads(p.read_text(encoding="utf-8"))["tracks"].items():
            for r in v["rows"]:
                yield (f"v19/control-{track}", "correct", r["query_id"], r["answer_correct"])
                yield (f"v19/control-{track}", "mismatched", r["query_id"], r["answer_mismatched"])
    for p in sorted(V111.glob("answers_*.json")):
        stage = p.stem.replace("answers_", "")
        if stage == "all":
            continue
        for cid, t in json.loads(p.read_text(encoding="utf-8")).items():
            arm = cid.split("-")[2] if cid.count("-") >= 2 else "?"
            yield (f"v111/{stage}", arm, cid, t)


def main() -> int:
    rows = list(populations())
    per = {}
    hits = []
    for pop, arm, ident, text in rows:
        key = (pop, arm)
        d = per.setdefault(key, Counter())
        d["population"] += 1
        s = screens_for(text)
        for x in s:
            d[x] += 1
        if bare_sentinel(text):
            d["bare_sentinel"] += 1
        if s or bare_sentinel(text):
            hits.append({"population": pop, "arm": arm, "id": ident,
                         "screens": s, "bare_sentinel": bare_sentinel(text), "text": text[:400]})

    rec = {"_note": ("read-only scan of frozen v1.9 / v1.11 answer populations; no number in "
                     "those experiments is changed by this and nothing under v1*/ was touched"),
           "screen_definitions": {
               "S1": f"sentinel present AND >= {S1_CONTENT_FLOOR} non-sentinel chars remain",
               "S4": ("classified ANSWER by v1 but the text matches the "
                      "sentinel-variant pattern (word-boundary, case-insensitive)"),
               "bare_sentinel": "whole reply is the sentinel plus trailing punctuation only"},
           "by_population_arm": {f"{p}|{a}": dict(c) for (p, a), c in sorted(per.items())},
           "totals": {"population": len(rows),
                      "S1": sum(c["S1"] for c in per.values()),
                      "S4": sum(c["S4"] for c in per.values()),
                      "bare_sentinel": sum(c["bare_sentinel"] for c in per.values())},
           "hits": hits}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "exposure_scan.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")

    print(f"  population {rec['totals']['population']} replies")
    print(f"  {'population|arm':34} {'n':>6} {'S1':>5} {'S4':>5} {'bare':>6}")
    for k, c in rec["by_population_arm"].items():
        print(f"  {k:34} {c['population']:6} {c.get('S1',0):5} {c.get('S4',0):5} "
              f"{c.get('bare_sentinel',0):6}")
    print(f"  {'TOTAL':34} {rec['totals']['population']:6} {rec['totals']['S1']:5} "
          f"{rec['totals']['S4']:5} {rec['totals']['bare_sentinel']:6}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
