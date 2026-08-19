"""Migration, retirement, census and acceptance for the v3 release (build spec §3). Zero calls.

The whole point of this module is the branch the parent build never reached live: three probes
whose answer spans were rewritten under them must classify DISTURBED, must **not** be migrated,
and must be retired with a cause naming the intersecting edit. The retirement log is a
first-class deliverable — a probe silently carried past a disturbed span is a probe whose ground
truth has quietly stopped being true, which is worse than having no probe.

Everything load-bearing is imported by identity: the migrator from `versioning.migrate`, the
inventory builder from `versioning.store_migrate`, and the package constructions from `v19`/`v111`
through it.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.datasets.base import GoldSpan                                   # noqa: E402
from src.score.provenance import covered_chars                           # noqa: E402
from v19.control import b2_for_query                                     # noqa: E402
from v19.packages import build_all                                       # noqa: E402
from v111.unanswerable import assert_no_gold_overlap, same_doc_answerless  # noqa: E402
from versioning.migrate import migrate_document                          # noqa: E402
from versioning.store_migrate import build_v2_inventories                # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
V3_CORPUS = HERE / "corpus_v3"
V2_CORPUS = _ROOT / "versioning" / "corpus_v2"
STORE_V2 = _ROOT / "versioning" / "results" / "probe_store_v2.json"
MONITORED_ARM = "F768"
V19_ARMS = ("F768", "U768", "U256")


class CensusOverlap(AssertionError):
    """A rebuilt answerless package overlaps its migrated span. STOP."""


def _docs(d: Path) -> dict[str, str]:
    return {p.stem: p.read_text(encoding="utf-8") for p in d.glob("*.txt")}


def run() -> dict:
    from src import config as C

    v2, v3 = _docs(V2_CORPUS), _docs(V3_CORPUS)
    store = json.loads(STORE_V2.read_text(encoding="utf-8"))
    expected = json.loads((HERE / "expected_outcomes_v3.json").read_text(encoding="utf-8"))
    exp_by_q = {e["query_id"]: e for e in expected["expected"]}
    edit_by_doc = {e["doc_id"]: e for e in expected["edits"]}

    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(_ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"

    # ---- migrate every probe span v2 -> v3
    migrations, retired, survivors = [], [], []
    for p in store["probes"]:
        g = p["gold_spans"][0]
        doc = g["doc_id"]
        rec = migrate_document(v2[doc], v3[doc], [(g["start_char"], g["end_char"])])[0]
        migrations.append({"query_id": p["query_id"], "doc_id": doc, **rec})
        if rec["outcome"] == "DISTURBED":
            ed = edit_by_doc.get(doc, {})
            retired.append({
                "query_id": p["query_id"], "doc_id": doc,
                "span_v2": [g["start_char"], g["end_char"]],
                "migrator_cause": rec.get("cause"),
                "intersecting_edit": {"kind": ed.get("kind"), "class": ed.get("target_class"),
                                      "a": ed.get("a"), "b": ed.get("b")},
                "action": "RETIRED — flagged for re-registration, never silently carried"})
        else:
            survivors.append((p, doc, rec))

    # ---- rebuild survivors against v3; census re-run in full
    invs = build_v2_inventories(v3, cfg)          # generic over a corpus; v3 here
    rebuilt, checked, overlaps = [], 0, 0
    for p, doc, mig in survivors:
        g0 = p["gold_spans"][0]
        assert v3[doc][mig["new_start"]:mig["new_end"]] == \
            v2[doc][g0["start_char"]:g0["end_char"]], \
            f"{p['query_id']}: migrated text is not byte-identical"
        gold = [GoldSpan(doc_id=doc, start_char=mig["new_start"], end_char=mig["new_end"])]
        b = b2_for_query({a: invs[a] for a in V19_ARMS}, gold)
        built = build_all({a: invs[a] for a in V19_ARMS}, gold, b["b2"])
        sd = same_doc_answerless(invs[MONITORED_ARM], gold, b["b2"])
        if sd is None:
            retired.append({"query_id": p["query_id"], "doc_id": doc,
                            "migrator_cause": "same_doc_unconstructible_in_v3",
                            "action": "RETIRED"})
            continue
        assert_no_gold_overlap(sd, gold, f"{p['query_id']}/same_doc@v3")
        checked += 1
        cross = p["packages"]["cross_doc"]
        cov = sum(covered_chars(u, gg) for u in invs[MONITORED_ARM]
                  if u.doc_id == doc and u.text in cross for gg in gold)
        checked += 1
        if cov > 0:
            overlaps += 1
            raise CensusOverlap(f"{p['query_id']}: cross-doc package overlaps the migrated span")
        rebuilt.append({"query_id": p["query_id"], "question": p["question"],
                        "gold_text": p["gold_text"],
                        "gold_spans": [x.as_dict() for x in gold],
                        "migration": mig, "b2": b["b2"],
                        "packages": {"answer_bearing": built["packages"][MONITORED_ARM].package.text,
                                     "same_doc": "\n\n".join(u.text for u in sd),
                                     "cross_doc": cross}})

    # ---- acceptance against ground truth
    rows, disagreements = [], []
    for m in migrations:
        e = exp_by_q[m["query_id"]]
        agree = m["outcome"] == e["outcome"]
        if agree and e["outcome"] == "UNCHANGED" and e["delta"] is not None:
            agree = m["delta"] == e["delta"]
        row = {"query_id": m["query_id"], "class": e["class"],
               "expected": {"outcome": e["outcome"], "delta": e["delta"]},
               "migrator": {"outcome": m["outcome"], "delta": m.get("delta"),
                            "cause": m.get("cause")},
               "agree": agree}
        rows.append(row)
        if not agree:
            disagreements.append(row)

    rec = {"release": "v2 -> v3", "canary_frozen_at": "0257ebe",
           "parent_build": "fa9e587",
           "n_probes_in": len(store["probes"]), "n_retired": len(retired),
           "n_survivors": len(rebuilt),
           "migration_outcomes": dict(Counter(m["outcome"] for m in migrations)),
           "byte_identity_verified": sum(1 for m in migrations if m.get("verified")),
           "retirement_log": retired,
           "census": {"answerless_packages_checked": checked, "gold_overlaps_found": overlaps,
                      "expected_checks": 2 * len(rebuilt),
                      "_note": "re-executed against version 3 over survivors only"},
           "acceptance": {"spans": len(rows), "agreements": sum(1 for r in rows if r["agree"]),
                          "disagreements": len(disagreements),
                          "disagreement_rows": disagreements, "rows": rows},
           "monitored_arm": MONITORED_ARM, "size": len(rebuilt), "probes": rebuilt}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "migration_v3.json").write_text(json.dumps(
        {k: v for k, v in rec.items() if k != "probes"}, indent=2), encoding="utf-8")
    (RESULTS / "probe_store_v3.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return rec


if __name__ == "__main__":
    r = run()
    print(f"  probes in {r['n_probes_in']}  retired {r['n_retired']}  survivors {r['n_survivors']}")
    print(f"  migration outcomes: {r['migration_outcomes']}  byte-identity verified "
          f"{r['byte_identity_verified']}")
    print(f"  census: {r['census']['answerless_packages_checked']} checked "
          f"(expected {r['census']['expected_checks']}), {r['census']['gold_overlaps_found']} overlaps")
    a = r["acceptance"]
    print(f"  acceptance: {a['agreements']}/{a['spans']} agree, {a['disagreements']} disagree")
    print("  retirement log:")
    for t in r["retirement_log"]:
        print(f"    {t['query_id']:32} cause={t['migrator_cause']} "
              f"edit={t.get('intersecting_edit', {}).get('kind')}")
