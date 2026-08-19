"""Published-number reconciliation. ZERO CALLS, READ-ONLY over v1*/.

Every abstention-derived figure that appears in a record-published results document, with its
published value, its value under classifier v2, its value under classifier v3, and the
reply-level provenance of every delta.

Figures are located by reading the published documents' own numbers and recomputing from the
persisted replies those numbers were derived from. Nothing under `v1*/` is modified; no document
is edited. Correcting the documents is the ruling side's.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline_swap.classifier_v2 import is_not_found_v2                 # noqa: E402
from pipeline_swap.classifier_v3 import is_not_found_v3                 # noqa: E402
from src.v17.reading import is_not_found as is_not_found_v1             # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"
V19, V111 = ROOT / "v19" / "results_run", ROOT / "v111" / "results_run"
FNS = {"v1": is_not_found_v1, "v2": is_not_found_v2, "v3": is_not_found_v3}


def _delta_ids(items, sense):
    """(ids that flip v1->v2, ids that flip v2->v3). `sense` is 'refusal' or 'answer'."""
    d12 = [i for i, t in items if is_not_found_v2(t) and not is_not_found_v1(t)]
    d23 = [i for i, t in items if is_not_found_v3(t) and not is_not_found_v2(t)]
    return d12, d23


def counted(items, mode):
    """`mode='refusal'` counts abstentions; `mode='answer'` counts non-abstentions."""
    out = {}
    for v, fn in FNS.items():
        n = sum(1 for _i, t in items if fn(t))
        out[v] = n if mode == "refusal" else len(items) - n
    return out


def v19_arm(name, arm):
    p = V19 / f"{name}.json"
    return [(r["query_id"], r["arms"][arm]["answer"])
            for r in json.loads(p.read_text(encoding="utf-8"))["rows"]]


def v111_arm(stage, arm, variant=None):
    p = V111 / f"answers_{stage}.json"
    out = []
    for cid, t in json.loads(p.read_text(encoding="utf-8")).items():
        parts = cid.split("-")
        if parts[2] != arm:
            continue
        if variant and parts[4] != variant:
            continue
        out.append((cid, t))
    return out


def row(figure, document, published, items, mode):
    c = counted(items, mode)
    d12, d23 = _delta_ids(items, mode)
    return {"figure": figure, "document": document, "published": published,
            "denominator": len(items),
            "v1_recomputed": c["v1"], "v2": c["v2"], "v3": c["v3"],
            "matches_published": c["v1"] == published,
            "delta_v1_to_v2": c["v2"] - c["v1"] if mode == "refusal" else c["v2"] - c["v1"],
            "delta_v2_to_v3": c["v3"] - c["v2"],
            "provenance_v1_to_v2": d12, "provenance_v2_to_v3": d23}


def main() -> int:
    rows = []
    D19, D111 = "Results_v19_ReadingResidual.md", "Results_v111_ReadingRobustness.md"

    # --- v1.9 §3: main_A NOT FOUND asymmetry (abstention counts)
    for arm, pub in (("F768", 1), ("U768", 15), ("U256", 14)):
        rows.append(row(f"v1.9 §3 NOT FOUND, main_A {arm}", D19, pub,
                        v19_arm("main_A", arm), "refusal"))
    # --- v1.9 §6: Track B NOT FOUND (quarantined table, still published)
    for arm, pub in (("F768", 67), ("U768", 60), ("U256", 60)):
        rows.append(row(f"v1.9 §6 NOT FOUND, main_B {arm} (quarantined)", D19, pub,
                        v19_arm("main_B", arm), "refusal"))
    # --- v1.11 §1: PS-1 same-doc false answers (answer counts)
    for arm, pub in (("f768", 38), ("u768", 50)):
        rows.append(row(f"v1.11 §1 same-doc false answers, {arm.upper()} (F_SAFE input)",
                        D111, pub, v111_arm("ea", arm, "sdoc"), "answer"))
    # --- v1.11 §1: cross-doc answered counts
    for arm, pub in (("f768", 28), ("u768", 35)):
        rows.append(row(f"v1.11 §1 cross-doc answered, {arm.upper()}", D111, pub,
                        v111_arm("ea", arm, "xdoc"), "answer"))
    # --- v1.11 §3: E-B Haiku abstentions (published as zero)
    for arm, pub in (("f768", 0), ("u768", 0)):
        rows.append(row(f"v1.11 §3 NOT FOUND, E-B Haiku {arm.upper()}", D111, pub,
                        v111_arm("eb", arm), "refusal"))
    # --- v1.11 §4: E-C prompt-variant abstentions
    for stage, variant, arm, pub in (("ec", "v1", "f768", 0), ("ec", "v1", "u768", 2),
                                     ("ec", "v2", "f768", 1), ("ec", "v2", "u768", 3)):
        rows.append(row(f"v1.11 §4 NOT FOUND, E-C {variant.upper()} {arm.upper()}", D111, pub,
                        v111_arm(f"{stage}-{variant}", arm), "refusal"))
    # --- v1.11 §5: E-E abstentions
    for arm, pub in (("c768", 6), ("u768", 17)):
        rows.append(row(f"v1.11 §5 NOT FOUND, E-E {arm.upper()}", D111, pub,
                        v111_arm("ee", arm), "refusal"))

    rec = {"_note": ("published = the value printed in the record document; v1_recomputed "
                     "reproduces it from the persisted replies; v2 and v3 are the versioned "
                     "classifiers. Nothing under v1*/ modified; no document edited."),
           "rows": rows,
           "totals": {"figures": len(rows),
                      "reproduce_published": sum(1 for r in rows if r["matches_published"]),
                      "changed_by_v2": sum(1 for r in rows if r["delta_v1_to_v2"]),
                      "changed_by_v3": sum(1 for r in rows if r["delta_v2_to_v3"])}}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "reconciliation.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")

    w = max(len(r["figure"]) for r in rows)
    print(f"  {'figure':{w}} {'n':>4} {'pub':>5} {'v1':>4} {'v2':>4} {'v3':>4}  repro  d12  d23")
    for r in rows:
        print(f"  {r['figure']:{w}} {r['denominator']:4} {r['published']:5} "
              f"{r['v1_recomputed']:4} {r['v2']:4} {r['v3']:4}  "
              f"{'ok' if r['matches_published'] else 'MISMATCH':>5} "
              f"{r['delta_v1_to_v2']:+4} {r['delta_v2_to_v3']:+4}")
    print(f"\n  {rec['totals']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
