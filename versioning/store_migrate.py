"""Store migration and census re-proof (build spec §1.3). Zero model calls.

The canary's 30 registered spans are migrated against version 2. Probes whose span survives
(UNCHANGED or MOVED) are rebuilt: packages reconstructed against the v2 corpus by the same
identity-imported constructions the canary used, budgets unchanged. Probes whose span is
DISTURBED are **retired with cause logged** — §6.5's rule, and the reason the retirement log is
an artifact rather than a print statement: a disturbed span silently carried is a probe whose
"ground truth" is no longer true.

Then the census, re-executed in full: every rebuilt answerless package verified zero-overlap with
its **migrated** span by provenance. The guarantee is re-proved against the new corpus, not
inherited from the old one. Any overlap is a STOP.

`canary/` is read-only here; it is frozen at 0257ebe and this module only reads its store.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

V = ROOT / "versioning"
CANARY_STORE = ROOT / "canary" / "results" / "probe_store.json"

# identity imports — the same objects the canary build used
from src.chunkers.base import Unit                                   # noqa: E402
from src.datasets.base import Document, GoldSpan                     # noqa: E402
from src.score.provenance import covered_chars                       # noqa: E402
from v19.control import b2_for_query                                 # noqa: E402
from v19.packages import build_all                                   # noqa: E402
from v111.unanswerable import assert_no_gold_overlap, same_doc_answerless  # noqa: E402

MONITORED_ARM = "F768"
V19_ARMS = ("F768", "U768", "U256")


class CensusOverlap(AssertionError):
    """A rebuilt answerless package overlaps its migrated span. STOP."""


def _v2_inventories(v2_docs: dict[str, str], v1_invs: dict):
    """Rebuild each arm's units against v2 by re-chunking the edited documents.

    Units for untouched documents are reused unchanged; edited documents are re-chunked by the
    same builders, so provenance offsets refer to v2 coordinates throughout.
    """
    from segment_size_sweep import build_arm
    return build_arm  # re-chunking driver supplied by the caller; see build_v2_inventories


def build_v2_inventories(v2_docs: dict[str, str], tcfg):
    """Arms rebuilt against the v2 corpus, cache-only (no formatter call may spend)."""
    from src.chunkers.base import ChunkContext
    from src.datasets.base import Dataset
    from src.llm.client import LLMClient, build_llm
    import src.llm.client as LC
    from v111.requests_build import V19_ARMS as ARMS
    from segment_size_sweep import build_arm

    ds2 = Dataset(track_id="A-v2",
                  documents=[Document(doc_id=k, text=v) for k, v in sorted(v2_docs.items())],
                  queries=[])
    llm = build_llm(tcfg)
    original = LC.LLMClient._call_provider

    def _refuse(self, prompt, system):
        raise RuntimeError("v2 inventory build hit a formatter cache miss; this build spends $0")

    LC.LLMClient._call_provider = _refuse
    try:
        ctx_full = ChunkContext(embedder=None, llm=llm, config=tcfg)
        ctx_det = ChunkContext(embedder=None, llm=LLMClient(provider="none"), config=tcfg)
        return {a: build_arm(a, ds2, ctx_full, ctx_det)[0] for a in ARMS}
    finally:
        LC.LLMClient._call_provider = original


def migrate_store(out_path: Path | None = None) -> dict:
    from src import config as C
    from versioning.acceptance import load_v1_docs, load_v2_docs
    from versioning.migrate import migrate_document

    store = json.loads(CANARY_STORE.read_text(encoding="utf-8"))
    v1, v2 = load_v1_docs(), load_v2_docs()
    cfg = C.load_default()
    cfg.setdefault("_cache_root", str(ROOT / "cache"))
    cfg["llm"]["provider"] = "anthropic"

    # ---- migrate each probe's registered span
    migrated, retired = [], []
    for p in store["probes"]:
        g = p["gold_spans"][0]
        doc = g["doc_id"]
        rec = migrate_document(v1[doc], v2[doc], [(g["start_char"], g["end_char"])])[0]
        if rec["outcome"] == "DISTURBED":
            retired.append({"query_id": p["query_id"], "doc_id": doc,
                            "span": [g["start_char"], g["end_char"]],
                            "cause": rec.get("cause"),
                            "_note": "flagged for re-registration; never silently carried"})
        else:
            migrated.append({"probe": p, "doc_id": doc, "migration": rec})

    # ---- rebuild surviving probes against v2
    invs = build_v2_inventories(v2, cfg)
    rebuilt, census_checked, census_overlaps = [], 0, 0
    docs_by_id = v2
    for m in migrated:
        p, doc, mig = m["probe"], m["doc_id"], m["migration"]
        gold = [GoldSpan(doc_id=doc, start_char=mig["new_start"], end_char=mig["new_end"])]
        assert v2[doc][mig["new_start"]:mig["new_end"]] == \
            v1[doc][p["gold_spans"][0]["start_char"]:p["gold_spans"][0]["end_char"]], \
            f"{p['query_id']}: migrated text is not byte-identical"
        b = b2_for_query({a: invs[a] for a in V19_ARMS}, gold)
        built = build_all({a: invs[a] for a in V19_ARMS}, gold, b["b2"])
        answer_bearing = built["packages"][MONITORED_ARM].package.text
        sd_units = same_doc_answerless(invs[MONITORED_ARM], gold, b["b2"])
        if sd_units is None:
            retired.append({"query_id": p["query_id"], "doc_id": doc,
                            "cause": "same_doc_unconstructible_in_v2"})
            continue
        assert_no_gold_overlap(sd_units, gold, f"{p['query_id']}/same_doc@v2")
        census_checked += 1
        same_doc = "\n\n".join(u.text for u in sd_units)
        # cross-doc: reuse the frozen v1 cross-doc package and re-prove it against the migrated span
        cross_doc = p["packages"]["cross_doc"]
        xd_cov = 0
        for u in invs[MONITORED_ARM]:
            if u.doc_id == doc and u.text in cross_doc:
                xd_cov += sum(covered_chars(u, g) for g in gold)
        census_checked += 1
        if xd_cov > 0:
            census_overlaps += 1
            raise CensusOverlap(f"{p['query_id']}: cross-doc package overlaps the migrated span")
        rebuilt.append({"query_id": p["query_id"], "question": p["question"],
                        "gold_text": p["gold_text"],
                        "gold_spans": [g.as_dict() for g in gold],
                        "migration": mig, "b2": b["b2"],
                        "packages": {"answer_bearing": answer_bearing,
                                     "same_doc": same_doc, "cross_doc": cross_doc}})

    from collections import Counter
    rec = {"source_store": str(CANARY_STORE), "canary_frozen_at": "0257ebe",
           "n_original": len(store["probes"]), "n_migrated": len(rebuilt),
           "n_retired": len(retired),
           "migration_outcomes": dict(Counter(m["migration"]["outcome"] for m in migrated)),
           "retired": retired,
           "census": {"answerless_packages_checked": census_checked,
                      "gold_overlaps_found": census_overlaps,
                      "_note": "re-executed against version 2; not inherited from version 1"},
           "monitored_arm": MONITORED_ARM, "size": len(rebuilt), "probes": rebuilt}
    if out_path:
        out_path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return rec


if __name__ == "__main__":
    r = migrate_store(V / "results" / "probe_store_v2.json")
    print(f"  original {r['n_original']}  migrated {r['n_migrated']}  retired {r['n_retired']}")
    print(f"  migration outcomes: {r['migration_outcomes']}")
    print(f"  census: {r['census']['answerless_packages_checked']} checked, "
          f"{r['census']['gold_overlaps_found']} overlaps")
    for t in r["retired"]:
        print(f"    RETIRED {t['query_id']:32} {t.get('cause')}")
