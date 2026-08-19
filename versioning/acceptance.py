"""Acceptance against ground truth (build spec §4). Zero model calls.

Runs the migrator over every registered span and compares each outcome to
`expected_outcomes.json`. Expected: 100% agreement. Any disagreement is reported span by span,
naming what each artifact says — the expectation file may be wrong, the migrator may be wrong,
and which is which is the ruling side's call, not this module's.

The byte-identity invariant is asserted inside the migrator itself, so it holds independently of
whether the expectations file is right about anything.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

V = ROOT / "versioning"


def load_v1_docs() -> dict[str, str]:
    from src import config as C
    from src.datasets import load_track_dataset
    cfg = C.load_default()
    ds = load_track_dataset(C.load_track("A"), cfg["seed"])
    return {d.doc_id: d.text for d in ds.documents}


def load_v2_docs() -> dict[str, str]:
    return {p.stem: p.read_text(encoding="utf-8") for p in (V / "corpus_v2").glob("*.txt")}


def run(out_path: Path | None = None) -> dict:
    from versioning.migrate import migrate_document

    exp = json.loads((V / "expected_outcomes.json").read_text(encoding="utf-8"))
    v1, v2 = load_v1_docs(), load_v2_docs()

    by_doc: dict[str, list[tuple[int, int]]] = {}
    for e in exp["expected"]:
        by_doc.setdefault(e["doc_id"], []).append((e["start"], e["end"]))

    got: dict[tuple, dict] = {}
    for doc_id, spans in by_doc.items():
        for rec in migrate_document(v1[doc_id], v2[doc_id], sorted(set(spans))):
            got[(doc_id, rec["orig_start"], rec["orig_end"])] = rec

    rows, disagreements = [], []
    for e in exp["expected"]:
        g = got[(e["doc_id"], e["start"], e["end"])]
        agree = g["outcome"] == e["outcome"]
        if agree and e["outcome"] == "UNCHANGED" and e["delta"] is not None:
            agree = g["delta"] == e["delta"]
        row = {"doc_id": e["doc_id"], "span": [e["start"], e["end"]], "class": e["class"],
               "expected": {"outcome": e["outcome"], "delta": e["delta"]},
               "migrator": {"outcome": g["outcome"], "delta": g.get("delta"),
                            "cause": g.get("cause")},
               "agree": agree}
        rows.append(row)
        if not agree:
            disagreements.append(row)

    per_class = Counter(e["class"] for e in exp["expected"])
    per_outcome = Counter(r["migrator"]["outcome"] for r in rows)
    agree_by_class = {c: sum(1 for r in rows if r["class"] == c and r["agree"])
                      for c in sorted(per_class)}
    rec = {"spans_checked": len(rows), "agreements": sum(1 for r in rows if r["agree"]),
           "disagreements": len(disagreements),
           "agreement_rate": round(sum(1 for r in rows if r["agree"]) / len(rows), 6),
           "spans_per_class": dict(per_class), "agreements_per_class": agree_by_class,
           "migrator_outcomes": dict(per_outcome),
           "verified_byte_identity": sum(1 for r in got.values() if r.get("verified")),
           "disagreement_rows": disagreements, "rows": rows}
    if out_path:
        out_path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return rec


if __name__ == "__main__":
    r = run(V / "acceptance.json")
    print(f"  spans {r['spans_checked']}  agree {r['agreements']}  disagree {r['disagreements']} "
          f"({r['agreement_rate']:.4%})")
    print(f"  per class: {r['spans_per_class']}")
    print(f"  agreements per class: {r['agreements_per_class']}")
    print(f"  migrator outcomes: {r['migrator_outcomes']}")
    print(f"  byte-identity verified on: {r['verified_byte_identity']} migrated spans")
    for d in r["disagreement_rows"][:8]:
        print(f"    DISAGREE {d['doc_id']} {d['span']} class={d['class']} "
              f"expected={d['expected']} migrator={d['migrator']}")
