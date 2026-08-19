"""Part A — rebuild all three package types for `U256` against corpus v3, under the amendment.

The monitored pipeline changes from `F768` to `U256`. The store's registered spans and the
construction code are pipeline-independent; only the units they assemble change. That is the
demonstration.

**THE AMENDMENT (ruling of 5 August).** Probe `A-014-aster-router::f1`'s cross-doc construction
needs its test-list successor's package, and that successor is `A-030-kestrel-broker::syn` — one
of the three probes retired when the v3 release rewrote its answer span. The construction cannot
be applied. The governing rule is the design's own: **constructions depending on a disturbed span
retire with it.** So that probe's *cross-doc leg alone* cascade-retires with the new cause
`depends_on_retired_span(...)`; its answer-bearing and same-document legs stay live. The
successor-walk was rejected as inventing a rule the construction does not have.

Consequently the denominators are per counter and are stated everywhere:

    wrong abstention  /27      same-document  /27      cross-document  /26
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.datasets.base import GoldSpan                                     # noqa: E402
from src.score.provenance import covered_chars                             # noqa: E402
from v19.control import b2_for_query                                       # noqa: E402
from v19.packages import build_all                                         # noqa: E402
from v111.unanswerable import assert_no_gold_overlap, same_doc_answerless  # noqa: E402
from versioning.migrate import migrate_document                            # noqa: E402
from versioning.store_migrate import build_v2_inventories                  # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"
V3_CORPUS = ROOT / "versioning" / "retirement_demo" / "corpus_v3"
STORE_V3 = ROOT / "versioning" / "retirement_demo" / "results" / "probe_store_v3.json"
MONITORED_ARM = "U256"
ARMS = ("F768", "U768", "U256")


class CensusOverlap(AssertionError):
    """A rebuilt answerless package overlaps its span. STOP."""


def run() -> dict:
    from src import config as C
    from src.datasets import load_track_dataset
    from src.run import split_dev_test

    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"
    traw = C.load_track("A")
    ds = load_track_dataset(traw, cfg["seed"])
    dv = traw.get("params", {}).get("dev_fraction")
    if dv is None:
        dv = cfg.get("sweep", {}).get("dev_fraction", 0.2)
    _dev, test = split_dev_test(ds, dv, cfg["seed"])
    n = len(test)
    succ = {test[i].query_id: test[(i + 1) % n] for i in range(n)}
    v1 = {d.doc_id: d.text for d in ds.documents}
    v3 = {p.stem: p.read_text(encoding="utf-8") for p in V3_CORPUS.glob("*.txt")}

    store = json.loads(STORE_V3.read_text(encoding="utf-8"))
    retired_ids = {t["query_id"] for t in store["retirement_log"]}
    invs = build_v2_inventories(v3, cfg)          # generic over a corpus; v3, U256 among the arms

    probes, cascade, checked, overlaps = [], [], 0, 0
    for p in store["probes"]:
        g = p["gold_spans"][0]
        doc = g["doc_id"]
        gold = [GoldSpan(doc_id=doc, start_char=g["start_char"], end_char=g["end_char"])]
        b = b2_for_query({a: invs[a] for a in ARMS}, gold)
        built = build_all({a: invs[a] for a in ARMS}, gold, b["b2"])
        pkgs = {"answer_bearing": built["packages"][MONITORED_ARM].package.text}

        sd = same_doc_answerless(invs[MONITORED_ARM], gold, b["b2"])
        assert sd is not None, f"{p['query_id']}: same-doc unconstructible for {MONITORED_ARM}"
        assert_no_gold_overlap(sd, gold, f"{p['query_id']}/same_doc@v3/{MONITORED_ARM}")
        checked += 1
        pkgs["same_doc"] = "\n\n".join(u.text for u in sd)

        # ---- cross-doc: the test-list successor's package, or cascade-retire the leg
        s = succ[p["query_id"]]
        if s.query_id in retired_ids:
            cascade.append({"query_id": p["query_id"], "leg": "cross_doc",
                            "cause": f"depends_on_retired_span({s.query_id})",
                            "action": ("LEG RETIRED — the construction depends on a span retired "
                                       "in the v3 release; constructions depending on a disturbed "
                                       "span retire with it"),
                            "successor": s.query_id})
        else:
            sg = s.gold_spans[0]
            m = migrate_document(v1[sg.doc_id], v3[sg.doc_id],
                                 [(sg.start_char, sg.end_char)])[0]
            assert m["outcome"] != "DISTURBED", f"{p['query_id']}: successor span disturbed"
            sgold = [GoldSpan(doc_id=sg.doc_id, start_char=m["new_start"], end_char=m["new_end"])]
            sb = b2_for_query({a: invs[a] for a in ARMS}, sgold)
            sbuilt = build_all({a: invs[a] for a in ARMS}, sgold, sb["b2"])
            cross = sbuilt["packages"][MONITORED_ARM].package.text
            ids = set(sbuilt["packages"][MONITORED_ARM].package.unit_ids)
            cov = sum(covered_chars(u, gg) for u in invs[MONITORED_ARM]
                      if u.unit_id in ids for gg in gold)
            checked += 1
            if cov > 0:
                overlaps += 1
                raise CensusOverlap(f"{p['query_id']}: cross-doc package overlaps its own span")
            pkgs["cross_doc"] = cross

        probes.append({"query_id": p["query_id"], "question": p["question"],
                       "gold_text": p["gold_text"], "gold_spans": [x.as_dict() for x in gold],
                       "b2": b["b2"], "legs": sorted(pkgs), "packages": pkgs})

    denom = {"wrong_abstention": sum(1 for x in probes if "answer_bearing" in x["packages"]),
             "same_doc": sum(1 for x in probes if "same_doc" in x["packages"]),
             "cross_doc": sum(1 for x in probes if "cross_doc" in x["packages"])}
    rec = {"monitored_arm": MONITORED_ARM, "previous_monitored_arm": "F768",
           "corpus": "v3", "size": len(probes),
           "amendment": ("per-counter denominators; A-014's cross-doc leg cascade-retired"),
           "cascade_retirements": cascade,
           "denominators": denom,
           "census": {"answerless_packages_checked": checked, "gold_overlaps_found": overlaps,
                      "expected_checks": denom["same_doc"] + denom["cross_doc"]},
           "probes": probes}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "probe_store_u256.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return rec


if __name__ == "__main__":
    r = run()
    print(f"  monitored {r['previous_monitored_arm']} -> {r['monitored_arm']} on corpus {r['corpus']}")
    print(f"  probes {r['size']}  denominators {r['denominators']}")
    print(f"  census {r['census']['answerless_packages_checked']} checked "
          f"(expected {r['census']['expected_checks']}), {r['census']['gold_overlaps_found']} overlaps")
    for c in r["cascade_retirements"]:
        print(f"    CASCADE  {c['query_id']:30} leg={c['leg']}  cause={c['cause']}")
