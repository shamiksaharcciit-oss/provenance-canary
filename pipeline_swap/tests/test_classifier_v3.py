"""Classifier v3 tests: the 41, the 33, a regression set of ordinary answers, and containment.

No model calls. The 41 and the 33 are loaded from the persisted artifacts rather than retyped,
so these tests check the populations that were actually ruled on.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pipeline_swap.classifier_v2 import is_not_found_v2
from pipeline_swap.classifier_v3 import is_not_found_v3, new_under_v3, residue, verdict
from src.v17.reading import is_not_found as is_not_found_v1

RESULTS = Path(__file__).resolve().parents[1] / "results"
BARE_RE = re.compile(r"(?i)^\s*not\s+found[.!;:,]*\s*$")

#: Ordinary answers: none may become a refusal under any version.
REGRESSION_ANSWERS = [
    "v3.5.0",
    "900 milliseconds",
    "AGPL-3.0",
    "The Vega router is distributed under the Apache-2.0 license.",
    "The default timeout is 30 seconds, per the configuration section.",
    "It may be 42.",
    "The answer is NOT FOUND in the provided context.",   # embedded, not leading
    "Nothing in the context states this, so NOT FOUND.",  # sentinel trails, does not lead
    "not found",                                          # case not folded, by design
    "not found.",
    "NOT FOUNDATION is the parent org.",                  # word-boundary guard
]


def _shortlist():
    p = RESULTS / "typology_shortlist.json"
    if not p.exists():
        pytest.skip("shortlist not built")
    return json.loads(p.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ the 41

def test_all_41_shortlisted_replies_classify_refusal_under_v3():
    rows = _shortlist()
    assert len(rows) == 41
    wrong = [r["query_id"] for r in rows if not is_not_found_v3(r["text"])]
    assert not wrong, f"v3 failed to classify as REFUSAL: {wrong}"


def test_all_41_were_answers_under_both_earlier_versions():
    """Precondition: v3 is what changes them, nothing earlier did."""
    for r in _shortlist():
        assert not is_not_found_v1(r["text"]) and not is_not_found_v2(r["text"])
        assert new_under_v3(r["text"])


def test_every_shortlisted_reply_has_prose_after_the_sentinel():
    """The ruled pattern: sentinel-led abstention WITH explanatory prose."""
    for r in _shortlist():
        assert residue(r["text"]), f"{r['query_id']} has no residue; it is not a shortlist shape"


# ------------------------------------------------------------------ the 33

def test_all_33_bare_sentinel_replies_still_classify_refusal_under_v3():
    """v3 must not regress what v2 fixed."""
    p = RESULTS / "telemetry_v2_cycles1to5.json"
    if not p.exists():
        pytest.skip("v2 rescore not built")
    flips = [f for c in json.loads(p.read_text(encoding="utf-8"))["cycles"] for f in c["flips"]]
    assert len(flips) == 33
    for f in flips:
        assert is_not_found_v2(f["text"]) and is_not_found_v3(f["text"])
        assert BARE_RE.match(f["text"]), "the 33 are the bare-sentinel population"


# ------------------------------------------------------------------ regression set

def test_no_ordinary_answer_becomes_a_refusal_under_any_version():
    for s in REGRESSION_ANSWERS:
        assert not is_not_found_v1(s), s
        assert not is_not_found_v2(s), s
        assert not is_not_found_v3(s), s


def test_embedded_and_trailing_sentinels_stay_answers():
    assert not is_not_found_v3("The answer is NOT FOUND in the provided context.")
    assert not is_not_found_v3("Nothing states this, so NOT FOUND.")


def test_word_boundary_guard():
    assert not is_not_found_v3("NOT FOUNDATION is the parent org.")
    assert is_not_found_v3("NOT FOUND, per the context.")


def test_case_is_still_not_folded():
    for s in ("not found", "Not Found", "not found. The context lacks it."):
        assert not is_not_found_v3(s)


# ------------------------------------------------------------------ containment and dispatch

def test_v3_contains_v2_contains_v1_over_every_persisted_reply():
    from pipeline_swap.typology import collect
    for r in collect():
        t = r["text"]
        if is_not_found_v1(t):
            assert is_not_found_v2(t) and is_not_found_v3(t)
        if is_not_found_v2(t):
            assert is_not_found_v3(t)


def test_bare_sentinel_has_empty_residue():
    assert residue("NOT FOUND") == "" and residue("  NOT FOUND.  ") == ""


def test_residue_is_the_prose_after_the_sentinel():
    assert residue("NOT FOUND\n\nThe context lacks it.") == "The context lacks it."


def test_verdict_dispatches_to_the_named_version():
    s = "NOT FOUND\n\nThe context does not contain it."
    assert verdict(s, "v1") == "ANSWER"
    assert verdict(s, "v2") == "ANSWER"
    assert verdict(s, "v3") == "REFUSAL"
