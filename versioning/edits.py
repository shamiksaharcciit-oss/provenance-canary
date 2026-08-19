"""Versioned corpus and its ground truth (build spec §1.1).

Track A is **version 1** and is never modified. This module generates a deterministic version 2
of a 15-document subset and — before any migrator exists — computes, from edit coordinates and
registered-span coordinates alone, the **expected outcome per span**.

That ordering is the point. The expectations file is ground truth precisely because it is derived
from the edit's own arithmetic rather than from what the migrator later reports; §4 compares the
two and a disagreement names which artifact says what.

THE TAXONOMY. One edit per selected document, so each span's class follows from its geometry
against that edit:

    E1  insertion before a span        -> UNCHANGED, positive delta
    E2  deletion before a span         -> UNCHANGED, negative delta
    E3  edit strictly after a span     -> UNCHANGED, zero delta
    E4  edit intersecting a span       -> DISTURBED
    E5  block relocation containing a span -> MOVED
    E6  untouched document             -> UNCHANGED, zero delta

**Why E5 moves its block to position 0.** Diff opcodes are monotonic, so a block moved to the
front cannot be represented as equal-in-place: the matcher must delete it from its old location
and insert it at the new one. That makes the MOVED case reachable by construction rather than by
luck about which alignment the matcher happens to prefer. Spans after the block shift by −(b−a)
from the removal and +(b−a) from the insertion — net zero; spans before it shift +(b−a).
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

SEED = 1337
N_EDITED = 15
CLASSES = ("E1", "E2", "E3", "E4", "E5")
MIN_PER_CLASS = 3

INSERT_TEXT = ("\n\nRevision note: this section was reviewed during the quarterly documentation "
               "audit and carried forward without change to its technical content.\n\n")
REWRITE_TEXT = "this behaviour was restated during the audit"


@dataclass
class Edit:
    doc_id: str
    kind: str                 # insert | delete | rewrite | relocate
    target_class: str         # the class this edit was placed to realise
    a: int                    # primary coordinate (insertion point, or block start)
    b: int = 0                # block end / deletion end
    paste_at: int = 0         # relocation destination
    payload: str = ""


def apply_edit(text: str, e: Edit) -> str:
    if e.kind == "insert":
        return text[:e.a] + e.payload + text[e.a:]
    if e.kind == "delete":
        return text[:e.a] + text[e.b:]
    if e.kind == "rewrite":
        return text[:e.a] + e.payload + text[e.b:]
    if e.kind == "relocate":
        block = text[e.a:e.b]
        rest = text[:e.a] + text[e.b:]
        return rest[:e.paste_at] + block + rest[e.paste_at:]
    raise ValueError(f"unknown edit kind {e.kind!r}")


def expected_for_span(e: Edit, s: int, t: int) -> dict:
    """Expected outcome for span [s,t) under edit `e`, from coordinates alone."""
    if e.kind == "insert":
        if e.a <= s:
            return {"outcome": "UNCHANGED", "delta": len(e.payload), "class": "E1"}
        if e.a >= t:
            return {"outcome": "UNCHANGED", "delta": 0, "class": "E3"}
        return {"outcome": "DISTURBED", "delta": None, "class": "E4"}
    if e.kind == "delete":
        if e.b <= s:
            return {"outcome": "UNCHANGED", "delta": -(e.b - e.a), "class": "E2"}
        if e.a >= t:
            return {"outcome": "UNCHANGED", "delta": 0, "class": "E3"}
        return {"outcome": "DISTURBED", "delta": None, "class": "E4"}
    if e.kind == "rewrite":
        if e.b <= s:
            return {"outcome": "UNCHANGED", "delta": len(e.payload) - (e.b - e.a), "class": "E2"}
        if e.a >= t:
            return {"outcome": "UNCHANGED", "delta": 0, "class": "E3"}
        return {"outcome": "DISTURBED", "delta": None, "class": "E4"}
    if e.kind == "relocate":
        blk = e.b - e.a
        if e.a <= s and t <= e.b:
            return {"outcome": "MOVED", "delta": None, "class": "E5"}
        if t <= e.a:
            return {"outcome": "UNCHANGED", "delta": blk, "class": "E1"}
        if s >= e.b:
            return {"outcome": "UNCHANGED", "delta": 0, "class": "E3"}
        return {"outcome": "DISTURBED", "delta": None, "class": "E4"}
    raise ValueError(e.kind)


def _sentence_bounds(text: str, lo: int, hi: int) -> tuple[int, int] | None:
    """A paragraph-ish block boundary inside [lo,hi), on blank lines where possible."""
    seg = text[lo:hi]
    i = seg.find("\n\n")
    if i < 0:
        return None
    j = seg.find("\n\n", i + 2)
    if j < 0:
        j = len(seg)
    return lo + i + 2, lo + j


def place_edit(doc_id: str, text: str, spans: list[tuple[int, int]], target: str,
               rng: random.Random) -> Edit | None:
    """Place one edit realising `target` for at least one span, or None if impossible."""
    spans = sorted(spans)
    first, last = spans[0], spans[-1]
    if target == "E1":
        if first[0] < 10:
            return None
        return Edit(doc_id, "insert", "E1", a=max(0, first[0] - 1), payload=INSERT_TEXT)
    if target == "E2":
        blk = _sentence_bounds(text, 0, first[0])
        if not blk or blk[1] - blk[0] < 20:
            return None
        return Edit(doc_id, "delete", "E2", a=blk[0], b=blk[1])
    if target == "E3":
        if last[1] >= len(text) - 20:
            return None
        return Edit(doc_id, "insert", "E3", a=len(text) - 1, payload=INSERT_TEXT)
    if target == "E4":
        s, t = first
        if t - s < 40:
            return None
        m = s + (t - s) // 3
        return Edit(doc_id, "rewrite", "E4", a=m, b=min(t - 1, m + 15), payload=REWRITE_TEXT)
    if target == "E5":
        a = max(0, first[0] - 2)
        b = min(len(text), first[1] + 2)
        if a == 0 or b - a < 30:
            return None
        return Edit(doc_id, "relocate", "E5", a=a, b=b, paste_at=0)
    return None


def build_v2(out_dir: Path, seed: int = SEED) -> dict:
    """Generate version 2 plus `expected_outcomes.json`. Deterministic; no model call."""
    import sys
    if str(Path(__file__).resolve().parents[1]) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src import config as C
    from src.datasets import load_track_dataset
    from src.run import split_dev_test

    cfg = C.load_default()
    traw = C.load_track("A")
    ds = load_track_dataset(traw, cfg["seed"])
    dev_frac = traw.get("params", {}).get("dev_fraction")
    if dev_frac is None:
        dev_frac = cfg.get("sweep", {}).get("dev_fraction", 0.2)
    _dev, test = split_dev_test(ds, dev_frac, cfg["seed"])

    spans_by_doc: dict[str, set[tuple[int, int]]] = {}
    for q in test:
        for g in q.gold_spans:
            spans_by_doc.setdefault(g.doc_id, set()).add((g.start_char, g.end_char))
    docs = {d.doc_id: d.text for d in ds.documents}

    rng = random.Random(seed)
    walk = sorted(docs)
    rng.shuffle(walk)

    edits: list[Edit] = []
    edited: dict[str, str] = {}
    extensions: list[dict] = []
    targets = [CLASSES[i % len(CLASSES)] for i in range(N_EDITED)]
    ti = 0
    for doc_id in walk:
        if len(edits) >= N_EDITED:
            break
        if doc_id not in spans_by_doc:
            continue
        target = targets[ti]
        e = place_edit(doc_id, docs[doc_id], sorted(spans_by_doc[doc_id]), target, rng)
        if e is None:
            extensions.append({"doc_id": doc_id, "target": target, "reason": "edit unplaceable"})
            continue
        edits.append(e)
        edited[doc_id] = apply_edit(docs[doc_id], e)
        ti += 1

    expected = []
    edit_by_doc = {e.doc_id: e for e in edits}
    for doc_id in sorted(docs):
        for (s, t) in sorted(spans_by_doc.get(doc_id, ())):
            if doc_id in edit_by_doc:
                exp = expected_for_span(edit_by_doc[doc_id], s, t)
            else:
                exp = {"outcome": "UNCHANGED", "delta": 0, "class": "E6"}
            expected.append({"doc_id": doc_id, "start": s, "end": t, **exp})

    out_dir.mkdir(parents=True, exist_ok=True)
    corpus = out_dir / "corpus_v2"
    corpus.mkdir(exist_ok=True)
    for doc_id, text in docs.items():
        (corpus / f"{doc_id}.txt").write_text(edited.get(doc_id, text), encoding="utf-8")

    from collections import Counter
    per_class = Counter(x["class"] for x in expected)
    rec = {"seed": seed, "n_documents": len(docs), "n_edited": len(edits),
           "n_untouched": len(docs) - len(edits),
           "edits": [asdict(e) | {"payload_len": len(e.payload), "payload": ""} for e in edits],
           "walk_extensions": extensions,
           "spans_total": len(expected), "spans_per_class": dict(per_class),
           "coverage_ok": all(per_class.get(c, 0) >= MIN_PER_CLASS for c in CLASSES),
           "expected": expected}
    (out_dir / "expected_outcomes.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return rec
