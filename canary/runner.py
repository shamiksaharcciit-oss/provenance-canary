"""Canary probe runner and telemetry (build spec §§2-3).

One monitoring cycle, per probe:

    answer_bearing  -> a REFUSAL is a `wrong_abstention`     (the answer was there)
    same_doc        -> an ANSWER  is an `unsupported_answer` (on-topic, answerless)
    cross_doc       -> an ANSWER  is an `unsupported_answer` (other document, answerless)

Counted separately per construction. The classifier is v1.11's, imported by identity — there is
no second definition of "did it refuse" in this repository.

Exact counts only. No judge, no score beyond the classifier.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from src.v17.reading import PROMPT_TEMPLATE  # frozen v1.9 prompt, canonical at e19dd35
from v111.unanswerable import false_answer   # the NOT FOUND classifier, by identity
from v19.generate import V19Client           # pin + cache-bypassing call path, by identity

ANSWERLESS = ("same_doc", "cross_doc")


def render(package: str, query: str) -> str:
    """The frozen v1.9 prompt. Brace-safe: package text is corpus text."""
    return PROMPT_TEMPLATE.replace("{package}", package).replace("{query}", query)


def make_client(model: str, tcfg, cache_root: Path) -> V19Client:
    """Plan-pinned, asserted at construction. Never resolved from configuration (§4)."""
    g = tcfg.get("cost_guard", {})
    c = V19Client(provider="anthropic", model=model,
                  temperature=0.0, max_tokens=tcfg.get("llm", {}).get("max_tokens", 1024),
                  cache_dir=Path(cache_root) / "llm",
                  max_llm_calls=g.get("max_llm_calls", 100000),
                  max_usd=g.get("max_usd", 60.0))
    assert c.model == model, f"client is on {c.model!r}, not the pinned {model!r}"
    return c


def run_cycle(store: dict, model: str, tcfg, cache_root: Path, ledger, cycle_id: str,
              out_dir: Path) -> dict:
    """One monitoring cycle. Every reply persisted; `response.model` asserted at the end."""
    cl = make_client(model, tcfg, cache_root)
    rows, t0 = [], time.time()
    counts = {"wrong_abstention": 0,
              "unsupported_answer": {k: 0 for k in ANSWERLESS}}

    for p in store["probes"]:
        row = {"query_id": p["query_id"], "replies": {}}
        # answer-bearing: refusing is the failure
        r = cl.complete_uncached(render(p["packages"]["answer_bearing"], p["question"]))
        refused = 1 - false_answer(r)          # false_answer == 0 means it said NOT FOUND
        counts["wrong_abstention"] += refused
        row["replies"]["answer_bearing"] = {"text": r, "refusal": refused}
        # answerless: answering is the failure
        for k in ANSWERLESS:
            r = cl.complete_uncached(render(p["packages"][k], p["question"]))
            fa = false_answer(r)
            counts["unsupported_answer"][k] += fa
            row["replies"][k] = {"text": r, "unsupported_answer": fa}
        rows.append(row)

    seen = sorted(set(cl.models_seen))
    assert seen == [model], f"APPARATUS-STOP: response.model {seen} != [{model!r}]"
    cs = cl.cost_summary()
    ledger.record(stage=cycle_id, calls=cs["llm_calls"],
                  input_tokens=cs["input_tokens"], output_tokens=cs["output_tokens"],
                  note=f"canary cycle on {model}")

    n = len(store["probes"])
    rec = {"cycle": cycle_id,
           "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "monitored_pipeline": store["monitored_arm"],
           "model_requested": model, "model_served": seen,
           "n_probes": n,
           "counts": {"wrong_abstention": counts["wrong_abstention"],
                      "unsupported_answer": dict(counts["unsupported_answer"])},
           "rates": {"wrong_abstention": {"numerator": counts["wrong_abstention"],
                                          "denominator": n,
                                          "rate": round(counts["wrong_abstention"] / n, 6)},
                     **{f"unsupported_answer_{k}": {"numerator": counts["unsupported_answer"][k],
                                                    "denominator": n,
                                                    "rate": round(counts["unsupported_answer"][k] / n, 6)}
                        for k in ANSWERLESS}},
           "cost": cs, "seconds": round(time.time() - t0, 1),
           "probes": rows}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"telemetry_{cycle_id}.json").write_text(json.dumps(rec, indent=2),
                                                        encoding="utf-8")
    return rec
