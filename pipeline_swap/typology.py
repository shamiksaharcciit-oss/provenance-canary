"""Part B — classifier failure typology from persisted replies. ZERO MODEL CALLS.

Describes the boundary the classifier draws; **never moves it.** No reply's verdict is changed
by anything here. Screens may overlap and say so; every reply is counted once in the population.

THE CLASSIFIER'S ACTUAL NORMALISATION IS `.strip()` AND NOTHING ELSE.
`src.v17.reading.is_not_found` is `answer.strip() == "NOT FOUND"`. The build spec's S4 asks for
"variants that normalization had to rescue (case, punctuation, embedding in a sentence)" — but
this classifier rescues none of those. A reply of `not found.` is classified ANSWER, not rescued.
S4 is therefore defined as the honest complement: replies the classifier called ANSWER whose text
nevertheless *reads* as an abstention. Those are the cases a rescuing normalisation would have
caught and this one does not, which is the same information the spec wanted, arrived at from the
classifier that exists rather than the one assumed.

Screen definitions, fixed here in code and printed in the report:

  S1  sentinel plus content   the sentinel appears AND >= 20 non-sentinel characters remain
  S2  hedged assertion        ANSWER-classified, matching a fixed hedging lexicon (below)
  S3  near-empty answer       ANSWER-classified, < 3 characters after stripping
  S4  unrescued sentinel      ANSWER-classified, but the text matches a sentinel variant
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.v17.reading import NOT_FOUND, is_not_found        # noqa: E402  identity import

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"

#: Frozen, listed, and printed in the report. Word-boundary matched, case-insensitive.
HEDGE_LEXICON = ("may", "might", "possibly", "perhaps", "appears to", "seems to",
                 "not certain", "cannot confirm", "unclear", "unable to determine",
                 "does not explicitly", "not specified", "no explicit", "likely")
HEDGE_RE = re.compile(r"\b(" + "|".join(re.escape(h) for h in HEDGE_LEXICON) + r")\b", re.I)
#: A sentinel variant: the two words adjacent, any case, any surrounding punctuation.
SENTINEL_VARIANT_RE = re.compile(r"\bnot\s+found\b", re.I)
S1_CONTENT_FLOOR = 20
S3_LENGTH_FLOOR = 3

SOURCES = [
    ("cycle1_baseline", ROOT / "canary/results/telemetry_cycle1_baseline.json"),
    ("cycle2_stability", ROOT / "canary/results/telemetry_cycle2_stability.json"),
    ("cycle3_model_swap", ROOT / "canary/results/telemetry_cycle3_model_swap.json"),
    ("cycle4_after_release", ROOT / "versioning/results/telemetry_cycle4_after_release.json"),
    ("cycle5_after_retirement",
     ROOT / "versioning/retirement_demo/results/telemetry_cycle5_after_retirement.json"),
    ("cycle6_pipeline_swap", RESULTS / "telemetry_cycle6_pipeline_swap.json"),
]


def collect() -> list[dict]:
    """Every persisted reply, one row each. Missing cycles are skipped and reported."""
    rows = []
    for cycle, path in SOURCES:
        if not path.exists():
            continue
        t = json.loads(path.read_text(encoding="utf-8"))
        for p in t["probes"]:
            for slot, r in p["replies"].items():
                rows.append({"cycle": cycle, "model": t["model_requested"],
                             "query_id": p["query_id"], "slot": slot, "text": r["text"],
                             "verdict": "REFUSAL" if is_not_found(r["text"]) else "ANSWER"})
    return rows


def screen(row: dict) -> list[str]:
    txt = row["text"]
    stripped = txt.strip()
    hits = []
    if NOT_FOUND in txt:
        residue = txt.replace(NOT_FOUND, "").strip()
        if len(residue) >= S1_CONTENT_FLOOR:
            hits.append("S1")
    if row["verdict"] == "ANSWER":
        if HEDGE_RE.search(txt):
            hits.append("S2")
        if len(stripped) < S3_LENGTH_FLOOR:
            hits.append("S3")
        if SENTINEL_VARIANT_RE.search(txt):
            hits.append("S4")
    return hits


def run(supplementary: bool = True) -> dict:
    rows = collect()
    for r in rows:
        r["screens"] = screen(r)

    from collections import Counter, defaultdict
    cycles = sorted({r["cycle"] for r in rows})
    per_screen = {s: {"total": 0, "per_cycle": {c: 0 for c in cycles},
                      "verdicts": Counter()} for s in ("S1", "S2", "S3", "S4")}
    for r in rows:
        for s in r["screens"]:
            per_screen[s]["total"] += 1
            per_screen[s]["per_cycle"][r["cycle"]] += 1
            per_screen[s]["verdicts"][r["verdict"]] += 1

    shortlist = [{"cycle": r["cycle"], "query_id": r["query_id"], "slot": r["slot"],
                  "verdict": r["verdict"], "screens": r["screens"], "text": r["text"]}
                 for r in rows if {"S1", "S2"} & set(r["screens"])]

    supp = None
    if supplementary:
        supp = {"population": 0, "screens": Counter()}
        for p in sorted((ROOT / "v111/results_run").glob("answers_*.json")):
            for cid, text in json.loads(p.read_text(encoding="utf-8")).items():
                row = {"text": text, "verdict": "REFUSAL" if is_not_found(text) else "ANSWER"}
                supp["population"] += 1
                for s in screen(row):
                    supp["screens"][s] += 1
        supp["screens"] = dict(supp["screens"])

    rec = {
        "population": len(rows),
        "cycles_included": cycles,
        "cycles_missing": [c for c, p in SOURCES if not p.exists()],
        "verdict_distribution": dict(Counter(r["verdict"] for r in rows)),
        "screen_definitions": {
            "S1": f"sentinel present AND >= {S1_CONTENT_FLOOR} non-sentinel chars remain",
            "S2": f"ANSWER-classified AND matches hedging lexicon {list(HEDGE_LEXICON)}",
            "S3": f"ANSWER-classified AND < {S3_LENGTH_FLOOR} chars after strip",
            "S4": ("ANSWER-classified AND text matches /\\bnot\\s+found\\b/i — the classifier's "
                   "normalisation is .strip() only, so these were NOT rescued"),
        },
        "screens": {s: {"total": v["total"], "per_cycle": v["per_cycle"],
                        "verdicts": dict(v["verdicts"])} for s, v in per_screen.items()},
        "overlap_note": ("screens may overlap; the population count is exact and each reply is "
                         "counted once in it"),
        "n_in_any_screen": sum(1 for r in rows if r["screens"]),
        "shortlist_size": len(shortlist),
        "supplementary_v111": supp,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "typology.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    (RESULTS / "typology_shortlist.json").write_text(json.dumps(shortlist, indent=2),
                                                     encoding="utf-8")
    return rec


if __name__ == "__main__":
    r = run()
    print(f"  population {r['population']} replies over {len(r['cycles_included'])} cycles "
          f"{r['cycles_included']}")
    print(f"  missing cycles: {r['cycles_missing']}")
    print(f"  verdicts: {r['verdict_distribution']}")
    for s, v in r["screens"].items():
        print(f"  {s}: total {v['total']:4}  verdicts {v['verdicts']}  per-cycle {v['per_cycle']}")
    print(f"  in any screen: {r['n_in_any_screen']}   S1/S2 shortlist: {r['shortlist_size']}")
    if r["supplementary_v111"]:
        print(f"  supplementary v1.11 population {r['supplementary_v111']['population']}, "
              f"screens {r['supplementary_v111']['screens']}")
