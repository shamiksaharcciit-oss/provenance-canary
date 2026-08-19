"""Canary probe store (build spec §1).

Thirty probes drawn from the Track A test set at seed 1337. Each carries its registered answer
span and three packages for the monitored pipeline:

    answer_bearing   the frozen v1.9 construction at B(q) budgets
    same_doc         v1.11 E-A same-doc: gold-overlapping units excluded, on-topic, answerless
    cross_doc        v1.11 E-A cross-doc: the successor query's package

EVERY CONSTRUCTION IS IMPORTED BY IDENTITY from `v19/` and `v111/`. Nothing is transcribed; if a
component could not be imported it would be a STOP, not a re-implementation.

TWO EXCLUSION CAUSES, both logged, both redrawn by the same seed walk so the store holds 30:

  * `same_doc_unconstructible` — the six small documents, where excluding gold-bearing units
    leaves the arm no unit in the gold document. Named in the spec.
  * `cross_doc_contains_gold` — the successor query is in the SAME document, so its package
    contains this query's gold and is not answerless. Successor-with-wraparound does not
    guarantee a different document: 4 of 176 Track A queries have a same-document successor, and
    all 8 of their packages fully contain the querying gold. The spec's §4 census demands every
    answerless package be verified zero-overlap by provenance, and this is that census failing;
    §1's stated remedy for a probe whose construction is impossible is exclusion plus redraw, so
    that is what happens here.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

# --- imported by identity; none of this is reimplemented -----------------------------------
from src.score.provenance import covered_chars
from src.v17.reading import gold_text
from v19.control import b2_for_query
from v19.packages import build_all
from v111.requests_build import load_track_a, v19_packages
from v111.unanswerable import assert_no_gold_overlap, same_doc_answerless

STORE_SIZE = 30
SEED = 1337
MONITORED_ARM = "F768"
V19_ARMS = ("F768", "U768", "U256")


class ProbeUnconstructible(Exception):
    """This query cannot yield a complete probe. Log the cause and redraw."""


def _package_covers(units, gold) -> int:
    return sum(covered_chars(u, g) for u in units for g in gold)


def build_probe(invs, q, successor, docs) -> dict:
    """One probe, or raise with the cause. Every answerless package is census-checked here."""
    b = b2_for_query({a: invs[a] for a in V19_ARMS}, q.gold_spans)
    built = build_all({a: invs[a] for a in V19_ARMS}, q.gold_spans, b["b2"])
    answer_bearing = built["packages"][MONITORED_ARM].package.text

    sd_units = same_doc_answerless(invs[MONITORED_ARM], q.gold_spans, b["b2"])
    if sd_units is None:
        raise ProbeUnconstructible("same_doc_unconstructible")
    assert_no_gold_overlap(sd_units, q.gold_spans, f"{q.query_id}/same_doc")
    same_doc = "\n\n".join(u.text for u in sd_units)

    _bs, ps = v19_packages(invs, successor)
    xd_ids = set(build_all({a: invs[a] for a in V19_ARMS},
                           successor.gold_spans,
                           b2_for_query({a: invs[a] for a in V19_ARMS},
                                        successor.gold_spans)["b2"]
                           )["packages"][MONITORED_ARM].package.unit_ids)
    xd_units = [u for u in invs[MONITORED_ARM] if u.unit_id in xd_ids]
    if _package_covers(xd_units, q.gold_spans) > 0:
        raise ProbeUnconstructible("cross_doc_contains_gold")
    cross_doc = ps[MONITORED_ARM]

    return {"query_id": q.query_id, "question": q.text,
            "gold_text": gold_text(docs[q.gold_spans[0].doc_id], q.gold_spans),
            "gold_spans": [g.as_dict() for g in q.gold_spans],
            "b2": b["b2"],
            "packages": {"answer_bearing": answer_bearing,
                         "same_doc": same_doc,
                         "cross_doc": cross_doc}}


def build_store(out_path: Path | None = None, size: int = STORE_SIZE, seed: int = SEED) -> dict:
    """Draw `size` complete probes by a seeded walk, logging every exclusion and its cause."""
    ds, tcfg, invs, test = load_track_a()
    docs = {d.doc_id: d.text for d in ds.documents}
    n = len(test)
    succ = {test[i].query_id: test[(i + 1) % n] for i in range(n)}

    rng = random.Random(seed)
    walk = list(range(n))
    rng.shuffle(walk)                       # the seed walk: a fixed permutation of the test set

    probes, excluded = [], []
    for idx in walk:
        if len(probes) == size:
            break
        q = test[idx]
        try:
            probes.append(build_probe(invs, q, succ[q.query_id], docs))
        except ProbeUnconstructible as e:
            excluded.append({"query_id": q.query_id, "cause": str(e)})

    if len(probes) < size:
        raise RuntimeError(f"seed walk exhausted with {len(probes)}/{size} probes")

    store = {"seed": seed, "size": len(probes), "monitored_arm": MONITORED_ARM,
             "constructions": {"answer_bearing": "v19.packages.build_all (frozen v1.9, B(q))",
                               "same_doc": "v111.unanswerable.same_doc_answerless",
                               "cross_doc": "v111.requests_build.v19_packages of the successor"},
             "census": {"answerless_packages_checked": 2 * len(probes),
                        "gold_overlaps_found": 0,
                        "_note": ("every same_doc package passed assert_no_gold_overlap and "
                                  "every cross_doc package passed an explicit provenance "
                                  "coverage check; probes failing either were excluded below")},
             "excluded": excluded, "probes": probes}
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(json.dumps(store, indent=2), encoding="utf-8")
    return store
