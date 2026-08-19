# Retirement-path demonstration — build instructions for agent 1

**Status:** engineering build, not a pre-registered experiment. No hypotheses, no freeze,
no branches. Standing orders apply in full (§5). INTERNAL ONLY (§6).
**Date:** 4 August 2026
**Purpose:** exercise, in a live run, the one §6.5 path the version-migration
demonstration proved only by test: an edit that intersects probe answer spans, the
store retiring those probes with cause, the census re-proving the survivors, and a
monitoring cycle running on the reduced denominator. This converts the companion
draft's scope note ("the retirement path was exercised by the 298-span acceptance and
by unit test, not by the live run") into a demonstrated behaviour.

**This document is the written instruction that reopens `versioning/` for commits — but
only under the new subdirectory `versioning/retirement_demo/` plus a re-emitted
combined chart. Every artifact of the fa9e587 build (corpus_v2, migration records,
cycles 1–4 telemetry) remains untouched. `canary/` remains frozen at 0257ebe;
its runner is imported by identity, never modified.**

---

## 1. Design stance: targeted, and declared as such

Last build's seed walk happened to miss every probe span; that was the honest outcome
of a no-hand-picking rule. This build is different in kind and says so: its purpose is
to exercise a code path, not to measure nature, so the edits are **deliberately
targeted at probe answer spans** and the report describes them as targeted. What stays
seed-governed is *which* probes, so no one chose convenient ones:

- Take the probe store as migrated to version 2 (30 probes).
- Walk the store in its fixed seed order; select the **first 3 probes whose spans lie
  in 3 distinct documents**. Those are the targets. Log the walk.

## 2. The release (corpus version 3)

Build `versioning/retirement_demo/corpus_v3/` from corpus_v2 by the existing scripted
edit generator, extended with this release's edit list:

1. **Three E4 edits** (one per target document): rewrite a sentence *inside* the
   target probe's answer span — the real-world event "a document revision changed the
   answer content." Expected outcome for each target span: DISTURBED.
2. **Two benign edits** in two *other* documents that contain probe spans: one E1
   (insertion before a span), one E2 (deletion before a span). Expected: UNCHANGED
   with non-zero deltas — so the release exercises mixed outcomes, not only the
   dramatic one.
3. All other documents pass through untouched.

As before, `expected_outcomes.json` is computed from edit and span coordinates alone,
written **before** the migrator runs, covering every registered span in the five
edited documents plus untouched controls. This is a v2→v3 single-hop diff; multi-hop
remains out of scope.

## 3. Migration, retirement, census

Run the identity-imported migrator v2→v3 over the full probe store:

- The 3 targeted spans must classify DISTURBED and must **not** be migrated. The
  store retires each with a logged cause identifying the intersecting edit — this log
  is a first-class deliverable, not a side effect.
- The remaining 27 migrate (UNCHANGED expected everywhere; byte-identity invariant
  asserted on every one; a single failure is a STOP).
- Packages for the 27 survivors are rebuilt against v3 by the identity-imported
  constructions, budgets unchanged.
- The answer-free census re-runs in full over the survivors' answerless packages
  (expected 54 = 27 × 2), executed and logged, zero overlaps required. Any overlap is
  a STOP.
- Ground-truth acceptance: migrator outcomes vs `expected_outcomes.json`, expected
  100%; any disagreement reported span-by-span and is a STOP for that class.

## 4. Cycle 5, and the combined chart

One monitoring cycle against corpus v3 with the surviving store: generator
`claude-sonnet-5`, plan-pinned and asserted per call, the frozen v1.9 prompt, the
identity-imported NOT FOUND classifier, `canary.runner.run_cycle` by identity.
**Denominator 27, stated in every number.** Expectation (not a tuned target): counts
consistent with the cycle 1/2/4 baselines at the monitor's resolution; report whatever
occurs.

Re-emit the combined telemetry chart as cycles 1–5 (reading 1–4 from the frozen
artifacts, writing the new chart under `versioning/retirement_demo/`), with cycle 5's
reduced denominator visibly annotated. Counts, not rates, on the axis, denominators in
the labels.

## 5. Budget, mechanics, standing orders

Parts 1–3: zero model calls, $0. Cycle 5: ≤ 27 × 3 = 81 calls. Ceiling **110 calls /
~$1.50**, own ledger, ceiling binding by test with **both surfaces pinned**
(enforcement and reporting — the standing rule). Persist everything: the edit list,
v3 documents, diff opcodes, expected outcomes, per-span migration records, the
retirement log, census log, cycle-5 replies and telemetry, the chart. Models asserted
against `response.model` on every call. Identity-imports asserted by object-identity
test; any component that cannot be imported by identity is a STOP, not a transcription.
Nothing under `v1*/` or `canary/` modified; nothing under `versioning/` outside
`retirement_demo/` modified except the combined chart emission. Commits under
`versioning/retirement_demo/` paths, the chart, and this document only.

## 6. INTERNAL ONLY — disclosure hold

Same hold as the canary and version-migration builds: this embodies §6.4/§6.5 of the
invention disclosure, held pending the employer's filing decision (since made: no filing). Nothing from
`retirement_demo/` is published, pushed anywhere public, or shared outside the filing
process until that decision. The README carries this paragraph at the top.

## 7. Deliverables and stop

`versioning/retirement_demo/` with the release builder, migration/retirement/census
artifacts, cycle-5 runner outputs, tests (targeting walk deterministic; DISTURBED
classification of the 3 targets; retirement log completeness; byte-identity on all 27
survivors; census binding; ledger both-surface pinning; model-pin assertion;
identity-import assertions), the cycles 1–5 chart, and the README. One report back:
the targeting walk result, per-span outcomes vs expectations, the retirement log
contents, census result, cycle-5 counts with denominator 27 explicit, spend, and
anything the spec left undetermined (a STOP, not a choice). No interpretation beyond
the counts.
