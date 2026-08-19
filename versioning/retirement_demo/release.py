"""Corpus version 3 and its ground truth (build spec §§1-2). Zero model calls.

**This release is targeted, and says so.** The fa9e587 build's seed walk missed every probe
span — the honest outcome of a no-hand-picking rule, and the reason the retirement path went
undemonstrated. This build exists to exercise a code path, not to measure nature, so its edits
are aimed deliberately at probe answer spans. What stays seed-governed is *which* probes: the
store is walked in its fixed order and the first three probes lying in three distinct documents
are the targets, so nobody chose convenient ones. The walk is logged.

The release, on top of corpus v2:

    3 x E4   rewrite a sentence INSIDE a target probe's answer span   -> DISTURBED
    1 x E1   insertion before a span in another probe-bearing document -> UNCHANGED, +delta
    1 x E2   deletion before a span in another probe-bearing document  -> UNCHANGED, -delta
    rest     untouched                                                 -> UNCHANGED, delta 0

`expected_outcomes.json` is computed from edit and span coordinates alone and written before the
migrator runs, exactly as in the parent build. Single-hop v2 -> v3; multi-hop stays out of scope.

The edit taxonomy, its application and its expectation arithmetic are **imported by identity**
from `versioning.edits` — this module supplies a new edit list, not a new generator.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from versioning.edits import Edit, INSERT_TEXT, REWRITE_TEXT, apply_edit, expected_for_span

ROOT = Path(__file__).resolve().parents[2]
V2_CORPUS = ROOT / "versioning" / "corpus_v2"
STORE_V2 = ROOT / "versioning" / "results" / "probe_store_v2.json"
HERE = Path(__file__).resolve().parent
V3_CORPUS = HERE / "corpus_v3"
MIN_SPAN_FOR_E4 = 40


def load_v2() -> dict[str, str]:
    return {p.stem: p.read_text(encoding="utf-8") for p in V2_CORPUS.glob("*.txt")}


def load_store() -> dict:
    return json.loads(STORE_V2.read_text(encoding="utf-8"))


def targeting_walk(store: dict, n_targets: int = 3) -> tuple[list[dict], list[dict]]:
    """First `n_targets` probes in distinct documents, in store order. Returns (targets, log)."""
    seen: list[str] = []
    targets, log = [], []
    for i, p in enumerate(store["probes"]):
        g = p["gold_spans"][0]
        doc, span = g["doc_id"], (g["start_char"], g["end_char"])
        if len(targets) == n_targets:
            break
        if doc in seen:
            log.append({"index": i, "query_id": p["query_id"], "doc_id": doc,
                        "decision": "skipped", "reason": "document already targeted"})
            continue
        if span[1] - span[0] < MIN_SPAN_FOR_E4:
            log.append({"index": i, "query_id": p["query_id"], "doc_id": doc,
                        "decision": "skipped",
                        "reason": f"span {span[1]-span[0]} chars < {MIN_SPAN_FOR_E4} needed for E4"})
            continue
        seen.append(doc)
        targets.append({"index": i, "query_id": p["query_id"], "doc_id": doc, "span": list(span)})
        log.append({"index": i, "query_id": p["query_id"], "doc_id": doc, "decision": "TARGET"})
    return targets, log


def pick_benign(store: dict, target_docs: set[str], v2: dict[str, str]) -> list[dict]:
    """Two other probe-bearing documents, in store order: one for E1, one for E2."""
    out, seen = [], set(target_docs)
    for p in store["probes"]:
        if len(out) == 2:
            break
        g = p["gold_spans"][0]
        doc = g["doc_id"]
        if doc in seen:
            continue
        kind = "E1" if not out else "E2"
        if kind == "E2":
            head = v2[doc][: g["start_char"]]
            i = head.find("\n\n")
            j = head.find("\n\n", i + 2) if i >= 0 else -1
            if i < 0 or j < 0 or j - i < 20:
                continue                      # no deletable paragraph before the span
        seen.add(doc)
        out.append({"query_id": p["query_id"], "doc_id": doc,
                    "span": [g["start_char"], g["end_char"]], "target_class": kind})
    return out


def build_v3(out_dir: Path = HERE) -> dict:
    v2 = load_v2()
    store = load_store()
    targets, walk_log = targeting_walk(store)
    assert len(targets) == 3, f"targeting walk yielded {len(targets)} targets"
    benign = pick_benign(store, {t["doc_id"] for t in targets}, v2)
    assert len(benign) == 2, f"benign selection yielded {len(benign)}"

    edits: list[Edit] = []
    for t in targets:
        s, e = t["span"]
        m = s + (e - s) // 3
        edits.append(Edit(t["doc_id"], "rewrite", "E4", a=m, b=min(e - 1, m + 15),
                          payload=REWRITE_TEXT))
    for b in benign:
        s, _e = b["span"]
        if b["target_class"] == "E1":
            edits.append(Edit(b["doc_id"], "insert", "E1", a=max(0, s - 1), payload=INSERT_TEXT))
        else:
            head = v2[b["doc_id"]][:s]
            i = head.find("\n\n")
            j = head.find("\n\n", i + 2)
            edits.append(Edit(b["doc_id"], "delete", "E2", a=i + 2, b=j))

    edit_by_doc = {e.doc_id: e for e in edits}
    v3 = {d: (apply_edit(t, edit_by_doc[d]) if d in edit_by_doc else t) for d, t in v2.items()}

    expected = []
    for p in store["probes"]:
        g = p["gold_spans"][0]
        doc, s, t = g["doc_id"], g["start_char"], g["end_char"]
        if doc in edit_by_doc:
            exp = expected_for_span(edit_by_doc[doc], s, t)
        else:
            exp = {"outcome": "UNCHANGED", "delta": 0, "class": "E6"}
        expected.append({"query_id": p["query_id"], "doc_id": doc, "start": s, "end": t, **exp})

    V3_CORPUS.mkdir(parents=True, exist_ok=True)
    for doc, text in v3.items():
        (V3_CORPUS / f"{doc}.txt").write_text(text, encoding="utf-8")

    from collections import Counter
    per_class = Counter(x["class"] for x in expected)
    per_outcome = Counter(x["outcome"] for x in expected)
    rec = {"release": "v2 -> v3", "hop": "single", "targeted": True,
           "targeting_rule": "first 3 probes in 3 distinct documents, store order",
           "targets": targets, "targeting_walk": walk_log, "benign": benign,
           "edits": [asdict(e) | {"payload_len": len(e.payload), "payload": ""} for e in edits],
           "n_edited_documents": len(edit_by_doc), "n_documents": len(v2),
           "spans_total": len(expected), "spans_per_class": dict(per_class),
           "spans_per_outcome": dict(per_outcome), "expected": expected}
    (out_dir / "expected_outcomes_v3.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return rec


if __name__ == "__main__":
    r = build_v3()
    print(f"  targets: {[t['query_id'] for t in r['targets']]}")
    print(f"  benign:  {[(b['query_id'], b['target_class']) for b in r['benign']]}")
    print(f"  edited documents {r['n_edited_documents']} of {r['n_documents']}")
    print(f"  expected per class:   {r['spans_per_class']}")
    print(f"  expected per outcome: {r['spans_per_outcome']}")
    print(f"  walk: {len(r['targeting_walk'])} entries, "
          f"{sum(1 for e in r['targeting_walk'] if e['decision']=='skipped')} skipped")
