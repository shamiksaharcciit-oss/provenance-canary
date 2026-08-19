"""Follow-up: per-arm S1 across the full v1.11 record, plus v1.9's S1 hits located and quoted.

ZERO CALLS, READ-ONLY over v1*/. Nothing there is modified. Counts and quotes only.

The v3 rule classifies a sentinel-led reply REFUSAL regardless of following prose. Its safety on
the frozen record therefore depends on what that prose actually says, so every S1 residue is
extracted verbatim and screened -- deterministically -- for whether it reads as an explanation of
absence or as an assertion of content. The screen is stated, not trusted: `ABSENCE_MARKERS` below.
Replies whose residue carries no absence marker are quoted in full for inspection.
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

from pipeline_swap.classifier_v3 import is_not_found_v3, residue        # noqa: E402
from pipeline_swap.typology import S1_CONTENT_FLOOR                     # noqa: E402
from src.v17.reading import NOT_FOUND, is_not_found as v1               # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"
V19, V111 = ROOT / "v19" / "results_run", ROOT / "v111" / "results_run"

#: A residue carrying any of these reads as an explanation of ABSENCE, not an assertion.
ABSENCE_MARKERS = ("does not contain", "does not include", "does not mention", "does not specify",
                   "does not detail", "does not provide", "not contain", "no information",
                   "not mentioned", "not present", "not specified", "not provided", "cannot",
                   "unable to", "does not appear", "is not", "are not", "only discusses",
                   "only states", "only contains", "instead", "not the", "no mention",
                   "nothing in the", "not available", "does not")
ABS_RE = re.compile("|".join(re.escape(m) for m in ABSENCE_MARKERS), re.I)


def is_s1(text: str) -> bool:
    return NOT_FOUND in text and len(text.replace(NOT_FOUND, "").strip()) >= S1_CONTENT_FLOOR


def v111_rows():
    for p in sorted(V111.glob("answers_*.json")):
        stage = p.stem.replace("answers_", "")
        if stage == "all":
            continue
        for cid, t in json.loads(p.read_text(encoding="utf-8")).items():
            parts = cid.split("-")
            arm, variant = parts[2], parts[4]
            yield (stage, arm, variant, cid, t)


def v19_rows():
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


def scan(rows, label):
    per, hits = {}, []
    for pop, arm, slot, ident, text in rows:
        key = f"{pop}|{arm}"
        c = per.setdefault(key, Counter())
        c["n"] += 1
        if is_s1(text):
            c["S1"] += 1
            res = residue(text)
            asserts = bool(res) and not ABS_RE.search(res)
            if asserts:
                c["S1_no_absence_marker"] += 1
            if is_not_found_v3(text):
                c["S1_leads_with_sentinel"] += 1
            hits.append({"record": label, "population": pop, "arm": arm, "slot": slot,
                         "id": ident, "v1_refusal": v1(text), "v3_refusal": is_not_found_v3(text),
                         "residue_has_absence_marker": not asserts,
                         "residue": res, "text": text})
    return per, hits


def main() -> int:
    p111, h111 = scan(v111_rows(), "v1.11")
    p19, h19 = scan(v19_rows(), "v1.9")
    hits = h111 + h19
    asserting = [h for h in hits if not h["residue_has_absence_marker"]]

    rec = {"_note": ("read-only over v1.9 and v1.11 persisted replies; nothing under v1*/ was "
                     "modified. Counts and quotes only; no conclusion is drawn."),
           "absence_marker_screen": list(ABSENCE_MARKERS),
           "haiku_arms": ["v1.11 stage `eb` — the PH-1/PH-2 arms, claude-haiku-4-5-20251001"],
           "v111_per_arm": {k: dict(c) for k, c in sorted(p111.items())},
           "v19_per_arm": {k: dict(c) for k, c in sorted(p19.items())},
           "s1_total": len(hits),
           "s1_leading_sentinel": sum(1 for h in hits if h["v3_refusal"]),
           "s1_without_absence_marker": len(asserting),
           "s1_hits": hits}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "exposure_s1.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")

    print("  v1.11 per arm (stage `eb` = Haiku, the PH arms):")
    print(f"  {'population|arm':26}{'n':>6}{'S1':>5}{'leads':>7}{'no-absence':>12}")
    for k, c in rec["v111_per_arm"].items():
        tag = "  <- HAIKU" if k.startswith("eb|") else ""
        print(f"  {k:26}{c['n']:6}{c.get('S1',0):5}{c.get('S1_leads_with_sentinel',0):7}"
              f"{c.get('S1_no_absence_marker',0):12}{tag}")
    print("\n  v1.9 per arm:")
    for k, c in rec["v19_per_arm"].items():
        if c.get("S1"):
            print(f"  {k:26}{c['n']:6}{c.get('S1',0):5}{c.get('S1_leads_with_sentinel',0):7}"
                  f"{c.get('S1_no_absence_marker',0):12}")
    print(f"\n  S1 total {rec['s1_total']}   leading-sentinel {rec['s1_leading_sentinel']}   "
          f"WITHOUT absence marker {rec['s1_without_absence_marker']}")
    for h in asserting:
        print(f"\n  [no absence marker] {h['record']} {h['population']}|{h['arm']} "
              f"{h['id']} slot={h['slot']} v3={h['v3_refusal']}")
        print(f"    {h['residue'][:320]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
