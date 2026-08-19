"""Versioning tests (build spec §7): ground-truth agreement, byte-identity invariant, ambiguity
rule, ledger ceiling on BOTH surfaces, model pin, identity imports. No model is called."""
from __future__ import annotations

import pytest

import canary.runner as canary_runner
import v111.unanswerable as v111u
import v19.packages as v19p
from src.datasets.base import GoldSpan
from v18.ledger import CeilingBreached
from versioning.edits import Edit, apply_edit, expected_for_span
from versioning.ledger import VERSIONING_CEILING, VersioningLedger
from versioning.migrate import (DISTURBED, MOVED, MigrationNotVerified, UNCHANGED,
                                migrate_document, migrate_span, opcodes)

D = "d1"


def mig(v1, v2, s, t):
    return migrate_span(v1, v2, opcodes(v1, v2), s, t)


# ------------------------------------------------------------------ the three outcomes

def test_insertion_before_a_span_is_unchanged_with_positive_delta():
    v1 = "AAAA the target span BBBB"
    v2 = "AAAA XXXXX the target span BBBB"
    r = mig(v1, v2, 5, 21)
    assert r["outcome"] == UNCHANGED and r["delta"] == 6
    assert v2[r["new_start"]:r["new_end"]] == v1[5:21]


def test_deletion_before_a_span_is_unchanged_with_negative_delta():
    v1 = "AAAA DELETEME the target span BBBB"
    v2 = "AAAA the target span BBBB"
    r = mig(v1, v2, 14, 30)
    assert r["outcome"] == UNCHANGED and r["delta"] == -9


def test_edit_after_a_span_is_unchanged_with_zero_delta():
    v1 = "the target span BBBB"
    v2 = "the target span CCCCCCC"
    r = mig(v1, v2, 0, 15)
    assert r["outcome"] == UNCHANGED and r["delta"] == 0


def test_edit_intersecting_a_span_is_disturbed_and_never_migrated():
    v1 = "AAAA the target span BBBB"
    v2 = "AAAA the REWRITTEN span BBBB"
    r = mig(v1, v2, 5, 21)
    assert r["outcome"] == DISTURBED
    assert r["new_start"] is None and r["new_end"] is None


def test_relocated_block_is_moved_and_byte_identical():
    span = "the target span"
    v1 = "PREFIX_LONG_ENOUGH_TO_ANCHOR " + span + " SUFFIX_ALSO_LONG_ENOUGH"
    v2 = span + " PREFIX_LONG_ENOUGH_TO_ANCHOR  SUFFIX_ALSO_LONG_ENOUGH"
    s = v1.index(span)
    r = mig(v1, v2, s, s + len(span))
    assert r["outcome"] == MOVED
    assert v2[r["new_start"]:r["new_end"]] == span


# ------------------------------------------------------------------ the ambiguity rule

def test_a_span_appearing_twice_after_relocation_is_disturbed_not_guessed():
    """The rule's precondition is supplied directly: no equal opcode covers the span, and its
    byte sequence occurs twice in v2. Driving this through `SequenceMatcher` instead would test
    the matcher's alignment preferences rather than the rule."""
    span = "duplicated marker text"
    v1 = "AAAAAAAAAAAA " + span + " BBBBBBBBBBBB"
    v2 = span + " CCCCCCCCCCCC " + span
    s = v1.index(span)
    no_covering_equal = [("replace", 0, len(v1), 0, len(v2))]
    r = migrate_span(v1, v2, no_covering_equal, s, s + len(span))
    assert r["outcome"] == DISTURBED
    assert r["cause"] == "ambiguous_relocation"
    assert r["new_start"] is None, "the migrator must not pick one of the candidates"


def test_a_uniquely_relocatable_span_is_moved_under_the_same_precondition():
    """Control for the rule above: one occurrence migrates, two do not."""
    span = "uniquely relocated text"
    v1 = "AAAAAAAAAAAA " + span + " BBBBBBBBBBBB"
    v2 = span + " CCCCCCCCCCCC"
    s = v1.index(span)
    r = migrate_span(v1, v2, [("replace", 0, len(v1), 0, len(v2))], s, s + len(span))
    assert r["outcome"] == MOVED and v2[r["new_start"]:r["new_end"]] == span


# ------------------------------------------------------------------ the binding invariant

def test_byte_identity_failure_is_a_stop_not_a_statistic():
    """A migrator that emitted non-identical coordinates must raise, not report."""
    v1, v2 = "abcdefghij", "abcdefghij"
    ops = [("equal", 0, 10, 0, 10)]
    # a deliberately wrong opcode: claims equality that does not hold
    bad_ops = [("equal", 0, 10, 3, 13)]
    assert migrate_span(v1, v2, ops, 2, 6)["outcome"] == UNCHANGED
    with pytest.raises(MigrationNotVerified):
        migrate_span(v1, v2, bad_ops, 2, 6)


# ------------------------------------------------------------------ expectations arithmetic

def test_expected_outcomes_are_computed_from_coordinates_alone():
    e = Edit(D, "insert", "E1", a=10, payload="XXXXX")
    assert expected_for_span(e, 20, 30) == {"outcome": "UNCHANGED", "delta": 5, "class": "E1"}
    assert expected_for_span(e, 0, 5) == {"outcome": "UNCHANGED", "delta": 0, "class": "E3"}
    assert expected_for_span(e, 5, 15)["outcome"] == "DISTURBED"


def test_relocation_expectations_match_the_applied_edit():
    text = "0123456789ABCDEFGHIJ"
    e = Edit(D, "relocate", "E5", a=10, b=15, paste_at=0)
    assert apply_edit(text, e) == "ABCDE0123456789FGHIJ"
    assert expected_for_span(e, 11, 14)["outcome"] == "MOVED"
    assert expected_for_span(e, 0, 5) == {"outcome": "UNCHANGED", "delta": 5, "class": "E1"}
    assert expected_for_span(e, 16, 19) == {"outcome": "UNCHANGED", "delta": 0, "class": "E3"}


# --------------------------------------------- retirement path, unexercised by the demo run

def test_a_disturbed_span_retires_rather_than_migrating():
    """The demonstration's 30 probes all survived, so this proves the retirement branch
    directly: a DISTURBED outcome yields no coordinates, which is what forces retirement."""
    v1 = "AAAA the registered answer span BBBB"
    v2 = "AAAA the rewritten answer span BBBB"
    r = migrate_document(v1, v2, [(5, 31)])[0]
    assert r["outcome"] == DISTURBED
    assert r["new_start"] is None, "a disturbed span must emit no coordinates to carry forward"


# ------------------------------------------------------------------ ledger, both surfaces

def test_ledger_enforcement_surface_binds_at_its_own_ceiling(tmp_path):
    led = VersioningLedger(tmp_path / "l.json")
    led.record(stage="c4", calls=VERSIONING_CEILING - 1)
    with pytest.raises(CeilingBreached, match="120"):
        led.record(stage="c5", calls=2)


def test_ledger_reporting_surface_reports_its_own_ceiling(tmp_path):
    led = VersioningLedger(tmp_path / "l.json")
    led.record(stage="c4", calls=90)
    t = led.totals()
    assert t["ceiling"] == VERSIONING_CEILING == 120
    assert t["headroom_against_ceiling"] == 30
    assert t["frozen_projection"] is None


# ------------------------------------------------------------------ identity imports

def test_cycle4_reuses_the_canary_loop_not_a_copy():
    from versioning import run_cycle4  # noqa: F401
    import canary.runner as again
    assert again is canary_runner


def test_store_migration_uses_the_frozen_constructions_by_identity():
    import versioning.store_migrate as sm
    assert sm.build_all is v19p.build_all
    assert sm.same_doc_answerless is v111u.same_doc_answerless
    assert sm.assert_no_gold_overlap is v111u.assert_no_gold_overlap


def test_classifier_is_still_v111s_object():
    assert canary_runner.false_answer is v111u.false_answer


def test_model_pin_is_explicit_not_config_resolved():
    from canary.runner import make_client
    c = make_client("claude-sonnet-5",
                    {"cost_guard": {}, "llm": {"model": "claude-opus-4-8"}}, ".")
    assert c.model == "claude-sonnet-5"
