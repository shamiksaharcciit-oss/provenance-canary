"""Retirement-demo tests (build spec §7). No model is called."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import canary.runner as canary_runner
import v111.unanswerable as v111u
import v19.packages as v19p
import versioning.edits as vedits
import versioning.migrate as vmigrate
from v18.ledger import CeilingBreached
from versioning.migrate import DISTURBED, UNCHANGED
from versioning.retirement_demo.ledger import DEMO_CEILING, RetirementDemoLedger
from versioning.retirement_demo.release import targeting_walk

HERE = Path(__file__).resolve().parents[1]
RESULTS = HERE / "results"


def _store(name):
    p = RESULTS / name
    if not p.exists():
        pytest.skip(f"{name} not built yet")
    return json.loads(p.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ the targeting walk

def test_targeting_walk_is_deterministic_and_document_distinct():
    store = {"probes": [
        {"query_id": f"q{i}", "gold_spans": [{"doc_id": f"d{i // 2}", "start_char": 0,
                                              "end_char": 100}]} for i in range(8)]}
    a, log_a = targeting_walk(store)
    b, _ = targeting_walk(store)
    assert [t["query_id"] for t in a] == [t["query_id"] for t in b], "walk must be deterministic"
    assert len({t["doc_id"] for t in a}) == 3, "targets must lie in distinct documents"
    assert any(e["decision"] == "skipped" for e in log_a), "skips must be logged, not silent"


def test_targeting_walk_skips_spans_too_short_for_an_intersecting_edit():
    store = {"probes": [
        {"query_id": "short", "gold_spans": [{"doc_id": "d0", "start_char": 0, "end_char": 5}]},
        {"query_id": "ok1", "gold_spans": [{"doc_id": "d1", "start_char": 0, "end_char": 200}]},
        {"query_id": "ok2", "gold_spans": [{"doc_id": "d2", "start_char": 0, "end_char": 200}]},
        {"query_id": "ok3", "gold_spans": [{"doc_id": "d3", "start_char": 0, "end_char": 200}]}]}
    targets, log = targeting_walk(store)
    assert [t["query_id"] for t in targets] == ["ok1", "ok2", "ok3"]
    assert any(e["query_id"] == "short" and "chars" in e["reason"] for e in log)


# ------------------------------------------------------------------ the demonstrated branch

def test_the_three_targets_classify_disturbed_and_are_retired():
    r = _store("probe_store_v3.json")
    exp = json.loads((HERE / "expected_outcomes_v3.json").read_text(encoding="utf-8"))
    targets = {t["query_id"] for t in exp["targets"]}
    retired = {t["query_id"] for t in r["retirement_log"]}
    assert targets == retired, f"targets {targets} != retired {retired}"
    assert r["migration_outcomes"][DISTURBED] == 3


def test_every_retirement_names_its_intersecting_edit():
    r = _store("probe_store_v3.json")
    for t in r["retirement_log"]:
        assert t["migrator_cause"], "a retirement without a cause is a silent drop"
        assert t["intersecting_edit"]["kind"] == "rewrite"
        assert t["action"].startswith("RETIRED")


def test_no_retired_probe_carries_coordinates_forward():
    r = _store("probe_store_v3.json")
    retired = {t["query_id"] for t in r["retirement_log"]}
    assert not (retired & {p["query_id"] for p in r["probes"]}), \
        "a retired probe must not appear in the surviving store"


def test_all_survivors_passed_byte_identity():
    r = _store("probe_store_v3.json")
    assert r["byte_identity_verified"] == r["n_survivors"] == 27


def test_census_covers_two_answerless_packages_per_survivor_with_no_overlap():
    r = _store("probe_store_v3.json")
    c = r["census"]
    assert c["answerless_packages_checked"] == c["expected_checks"] == 2 * r["n_survivors"]
    assert c["gold_overlaps_found"] == 0


def test_acceptance_is_total_agreement():
    r = _store("probe_store_v3.json")
    a = r["acceptance"]
    assert a["disagreements"] == 0 and a["agreements"] == a["spans"] == 30


def test_cycle5_denominator_is_the_survivor_count():
    p = RESULTS / "telemetry_cycle5_after_retirement.json"
    if not p.exists():
        pytest.skip("cycle 5 not run yet")
    t = json.loads(p.read_text(encoding="utf-8"))
    assert t["n_probes"] == 27
    for k, v in t["rates"].items():
        assert v["denominator"] == 27, f"{k} carries denominator {v['denominator']}"


# ------------------------------------------------------------------ ledger, both surfaces

def test_ledger_enforcement_surface_binds(tmp_path):
    led = RetirementDemoLedger(tmp_path / "l.json")
    led.record(stage="c5", calls=DEMO_CEILING - 1)
    with pytest.raises(CeilingBreached, match="110"):
        led.record(stage="c6", calls=2)


def test_ledger_reporting_surface_reports_its_own_ceiling(tmp_path):
    led = RetirementDemoLedger(tmp_path / "l.json")
    led.record(stage="c5", calls=81)
    t = led.totals()
    assert t["ceiling"] == DEMO_CEILING == 110
    assert t["headroom_against_ceiling"] == 29
    assert t["frozen_projection"] is None


# ------------------------------------------------------------------ identity imports

def test_release_reuses_the_parent_edit_generator_by_identity():
    import versioning.retirement_demo.release as rel
    assert rel.apply_edit is vedits.apply_edit
    assert rel.expected_for_span is vedits.expected_for_span
    assert rel.Edit is vedits.Edit


def test_migration_reuses_the_parent_migrator_by_identity():
    import versioning.retirement_demo.migrate_retire as mr
    assert mr.migrate_document is vmigrate.migrate_document
    assert mr.build_all is v19p.build_all
    assert mr.same_doc_answerless is v111u.same_doc_answerless


def test_cycle5_reuses_the_canary_loop_by_identity():
    import versioning.retirement_demo.run_cycle5  # noqa: F401
    import canary.runner as again
    assert again is canary_runner
    assert canary_runner.false_answer is v111u.false_answer


def test_model_pin_is_explicit_not_config_resolved():
    from canary.runner import make_client
    c = make_client("claude-sonnet-5",
                    {"cost_guard": {}, "llm": {"model": "claude-opus-4-8"}}, ".")
    assert c.model == "claude-sonnet-5"
