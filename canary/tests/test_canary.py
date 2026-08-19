"""Canary tests (build spec §6): construction census, identity imports, ledger ceiling,
model-pin assertion. No model is called."""
from __future__ import annotations

import pytest

import v111.unanswerable as v111u
import v19.packages as v19p
from canary.ledger import CANARY_CEILING, CanaryLedger
from canary.runner import make_client, render
from canary.store import MONITORED_ARM, ProbeUnconstructible, _package_covers, build_probe
from src.chunkers.base import Unit
from src.datasets.base import GoldSpan
from v18.ledger import CeilingBreached

D = "d1"


def u(i, n=40, s=None):
    s = i * 100 if s is None else s
    return Unit(unit_id=f"u{i}", text=" ".join([f"w{i}"] * n), doc_id=D,
                source_ranges=[(s, s + 100)])


# ------------------------------------------------------- identity imports (no transcription)

def test_classifier_is_v111s_object_not_a_copy():
    from canary import runner
    assert runner.false_answer is v111u.false_answer


def test_package_builder_is_v19s_object_not_a_copy():
    from canary import store
    assert store.build_all is v19p.build_all
    assert store.same_doc_answerless is v111u.same_doc_answerless


def test_prompt_is_the_frozen_v19_template():
    from src.v17.reading import PROMPT_TEMPLATE
    from canary import runner
    assert runner.PROMPT_TEMPLATE is PROMPT_TEMPLATE


def test_render_is_brace_safe():
    assert "{x}" in render("a {x} b", "q?")


# ------------------------------------------------------------------- construction census

def test_coverage_helper_detects_gold_in_a_package():
    gold = [GoldSpan(doc_id=D, start_char=110, end_char=150)]
    assert _package_covers([u(1, s=100)], gold) > 0
    assert _package_covers([u(9, s=900)], gold) == 0


def test_a_cross_doc_package_containing_the_gold_is_excluded():
    """The 4-of-176 same-document-successor case: not answerless, so not usable."""
    gold = [GoldSpan(doc_id=D, start_char=110, end_char=150)]
    assert _package_covers([u(1, s=100)], gold) > 0, "precondition: this package holds the gold"


def test_probe_unconstructible_is_raised_with_its_cause():
    e = ProbeUnconstructible("cross_doc_contains_gold")
    assert str(e) == "cross_doc_contains_gold"


def test_same_doc_construction_excludes_gold_bearing_units():
    units = [u(0, s=0), u(1, s=100), u(2, s=200)]
    gold = [GoldSpan(doc_id=D, start_char=110, end_char=150)]
    pkg = v111u.same_doc_answerless(units, gold, 100)
    assert pkg is not None and all(x.unit_id != "u1" for x in pkg)
    v111u.assert_no_gold_overlap(pkg, gold, "t")


# ------------------------------------------------------------------- ledger ceiling binds

def test_canary_ledger_uses_its_own_ceiling_not_v18s(tmp_path):
    led = CanaryLedger(tmp_path / "l.json")
    assert led.read()["ceiling"] == CANARY_CEILING == 400
    assert led.read()["experiment"] == "canary-prototype"


def test_canary_ledger_raises_at_its_own_ceiling(tmp_path):
    """v1.8's ledger would have allowed this; the canary's must not."""
    led = CanaryLedger(tmp_path / "l.json")
    led.record(stage="c1", calls=399)
    with pytest.raises(CeilingBreached, match="400"):
        led.record(stage="c2", calls=2)


def test_canary_ledger_is_append_only(tmp_path):
    led = CanaryLedger(tmp_path / "l.json")
    led.record(stage="c1", calls=5)
    led.record(stage="c2", calls=7)
    assert [e["calls"] for e in led.read()["entries"]] == [5, 7]


# ------------------------------------------------------------------- the model pin

def test_client_is_pinned_at_construction():
    cfg = {"cost_guard": {}, "llm": {"max_tokens": 512}}
    c = make_client("claude-haiku-4-5-20251001", cfg, ".")
    assert c.model == "claude-haiku-4-5-20251001"


def test_client_never_resolves_its_model_from_config():
    """A config carrying a different model must not win: the argument is the pin."""
    cfg = {"cost_guard": {}, "llm": {"model": "claude-opus-4-8", "max_tokens": 512}}
    c = make_client("claude-sonnet-5", cfg, ".")
    assert c.model == "claude-sonnet-5"


def test_response_model_mismatch_is_an_apparatus_stop():
    from v19.generate import ModelPinViolated
    c = make_client("claude-sonnet-5", {"cost_guard": {}, "llm": {}}, ".")
    c.models_seen.extend(["claude-sonnet-5", "claude-opus-4-8"])
    with pytest.raises(ModelPinViolated):
        c.assert_model_constant()


def test_canary_ledger_REPORTS_its_own_ceiling_not_v18s(tmp_path):
    """Enforcement and reporting are separate surfaces; both must be the canary's."""
    led = CanaryLedger(tmp_path / "l.json")
    led.record(stage="c1", calls=90)
    t = led.totals()
    assert t["ceiling"] == CANARY_CEILING == 400
    assert t["headroom_against_ceiling"] == 310
    assert t["frozen_projection"] is None
