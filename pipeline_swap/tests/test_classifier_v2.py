"""Classifier v2 and the screens, as a versioned instrument (build spec §7). No model calls."""
from __future__ import annotations

from pipeline_swap.classifier_v2 import TRAILING_PUNCTUATION, disagrees, is_not_found_v2, verdict
from pipeline_swap.typology import screen
from src.v17.reading import is_not_found as v1


# ------------------------------------------------------------------ v2 is v1 plus one thing

def test_v2_accepts_the_bare_sentinel_exactly_as_v1_does():
    for s in ("NOT FOUND", "  NOT FOUND\n", "\tNOT FOUND  "):
        assert v1(s) and is_not_found_v2(s)


def test_v2_rescues_trailing_punctuation_and_v1_does_not():
    """The 33-reply defect, pinned as a test."""
    for s in ("NOT FOUND.", "NOT FOUND!", "NOT FOUND;", "NOT FOUND,", "NOT FOUND. "):
        assert not v1(s), f"precondition: v1 must reject {s!r}"
        assert is_not_found_v2(s), f"v2 must accept {s!r}"
        assert disagrees(s)


def test_v2_does_NOT_fold_case():
    """Deliberately narrow: a model ignoring the declared casing has not used the token."""
    for s in ("not found", "Not Found", "not found."):
        assert not is_not_found_v2(s) and not v1(s)
        assert not disagrees(s)


def test_v2_does_NOT_accept_sentinel_plus_prose():
    """The 41 shortlist replies stay ANSWER under both versions until a human rules."""
    s = "NOT FOUND\n\nThe context provided does not contain any information about this."
    assert not v1(s) and not is_not_found_v2(s) and not disagrees(s)


def test_v2_does_not_accept_an_embedded_sentinel():
    assert not is_not_found_v2("The answer is NOT FOUND in the provided context.")


def test_v2_never_reclassifies_a_real_answer_as_refusal():
    for s in ("v3.5.0", "900 milliseconds", "The Vega router uses Apache-2.0."):
        assert not is_not_found_v2(s)


def test_verdict_dispatches_to_the_named_version():
    assert verdict("NOT FOUND.", "v1") == "ANSWER"
    assert verdict("NOT FOUND.", "v2") == "REFUSAL"


def test_trailing_punctuation_set_is_explicit_and_narrow():
    assert set(TRAILING_PUNCTUATION) == set(".!;:,")


# ------------------------------------------------------------------ screens are deterministic

def test_screens_are_deterministic():
    row = {"text": "NOT FOUND\n\nThe context does not contain that information at all.",
           "verdict": "ANSWER"}
    assert screen(row) == screen(dict(row))


def test_s1_requires_substantive_residue_not_just_punctuation():
    assert "S1" not in screen({"text": "NOT FOUND.", "verdict": "ANSWER"})
    assert "S1" in screen({"text": "NOT FOUND\n\n" + "x" * 25, "verdict": "ANSWER"})


def test_s4_only_fires_on_answer_classified_replies():
    assert "S4" not in screen({"text": "NOT FOUND", "verdict": "REFUSAL"})
    assert "S4" in screen({"text": "not found.", "verdict": "ANSWER"})


def test_s2_lexicon_is_word_boundary_matched():
    assert "S2" in screen({"text": "It may be 42.", "verdict": "ANSWER"})
    assert "S2" not in screen({"text": "The mayor signed it.", "verdict": "ANSWER"})


# ------------------------------------------------------------------ Part A: swap, cascade, ledger

def test_cascade_retirement_is_leg_level_with_its_new_cause():
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "results" / "probe_store_u256.json"
    if not p.exists():
        import pytest as _p
        _p.skip("rebuild not run")
    s = json.loads(p.read_text(encoding="utf-8"))
    c = s["cascade_retirements"]
    assert len(c) == 1 and c[0]["leg"] == "cross_doc"
    assert c[0]["cause"].startswith("depends_on_retired_span(")
    probe = [x for x in s["probes"] if x["query_id"] == c[0]["query_id"]][0]
    assert "cross_doc" not in probe["packages"], "a retired leg must emit no package"
    assert {"answer_bearing", "same_doc"} <= set(probe["packages"]), "other legs stay live"


def test_denominators_are_per_counter():
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "results" / "probe_store_u256.json"
    if not p.exists():
        import pytest as _p
        _p.skip("rebuild not run")
    d = json.loads(p.read_text(encoding="utf-8"))["denominators"]
    assert d == {"wrong_abstention": 27, "same_doc": 27, "cross_doc": 26}


def test_census_covers_every_live_answerless_leg_with_no_overlap():
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "results" / "probe_store_u256.json"
    if not p.exists():
        import pytest as _p
        _p.skip("rebuild not run")
    s = json.loads(p.read_text(encoding="utf-8"))
    c = s["census"]
    assert c["answerless_packages_checked"] == c["expected_checks"] == 53
    assert c["gold_overlaps_found"] == 0


def test_cycle6_reports_both_classifiers_with_explicit_denominators():
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "results" / "telemetry_cycle6_pipeline_swap.json"
    if not p.exists():
        import pytest as _p
        _p.skip("cycle 6 not run")
    t = json.loads(p.read_text(encoding="utf-8"))
    assert t["monitored_pipeline"] == "U256" and t["previous_monitored_pipeline"] == "F768"
    for key in ("rates", "rates_v2"):
        assert t[key]["wrong_abstention"]["denominator"] == 27
        assert t[key]["unsupported_answer_same_doc"]["denominator"] == 27
        assert t[key]["unsupported_answer_cross_doc"]["denominator"] == 26


def test_ledger_binds_and_reports_its_own_ceiling(tmp_path):
    from pipeline_swap.ledger import SWAP_CEILING, PipelineSwapLedger
    from v18.ledger import CeilingBreached
    import pytest as _p
    led = PipelineSwapLedger(tmp_path / "l.json")
    led.record(stage="c6", calls=80)
    t = led.totals()
    assert t["ceiling"] == SWAP_CEILING == 110 and t["headroom_against_ceiling"] == 30
    led.record(stage="c7", calls=29)
    with _p.raises(CeilingBreached, match="110"):
        led.record(stage="c8", calls=2)


def test_identity_imports_across_the_frozen_builds():
    import canary.runner as cr
    import v111.unanswerable as v111u
    import v19.packages as v19p
    import pipeline_swap.rebuild_u256 as rb
    import pipeline_swap.run_cycle6 as rc
    assert rc.render is cr.render and rc.make_client is cr.make_client
    assert cr.false_answer is v111u.false_answer
    assert rb.build_all is v19p.build_all
    assert rb.same_doc_answerless is v111u.same_doc_answerless
