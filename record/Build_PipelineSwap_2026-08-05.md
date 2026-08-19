# Pipeline-swap cycle and classifier typology — build instructions for agent 1

**Status:** engineering build, not a pre-registered experiment. No hypotheses, no freeze,
no branches. Standing orders apply in full (§5). INTERNAL ONLY (§6).
**Date:** 5 August 2026
**Purpose:** two deliverables. **Part A** exercises the last undemonstrated leg of the
reliability loop — a change to the *monitored pipeline itself* — so that every leg
(generator, corpus, pipeline) has a live cycle behind it. **Part B** produces, from
already-persisted replies at zero model cost, the classifier failure-typology analysis
the external review requested.

**Scope of commits:** a new top-level `pipeline_swap/` directory, the re-emitted
combined chart, and this document only. `canary/` (0257ebe), `versioning/` (fa9e587),
and `versioning/retirement_demo/` (3f0b7fd) remain frozen; their runner, constructions
and classifier are imported by identity, never modified. Corpus state for Part A is the
current live state: version 3, the 27-probe surviving store.

---

## Part A — cycle 6: the monitored pipeline changes

1. **The swap.** The monitored pipeline changes from `F768` (the formatter pipeline,
   monitored in cycles 1–5) to **`U256`** (the naive 256-token pipeline) — chosen
   because it is structurally the most different pipeline available: different unit
   sizes, different boundaries, no formatter edits. Everything else is held identical:
   generator `claude-sonnet-5` (plan-pinned, asserted per call), the frozen v1.9
   prompt, the identity-imported NOT FOUND classifier, corpus v3, the 27 surviving
   spans.
2. **Package rebuild.** All three package types for all 27 probes are rebuilt for
   `U256` by the identity-imported constructions (`v19.packages.build_all`, the v1.11
   same-doc and cross-doc answerless constructions), budgets unchanged. This is the
   demonstration's point: the store's registered spans and construction code are
   pipeline-independent; only the units they assemble change. Persist every package.
3. **Census re-proof.** The answer-free census runs in full over the rebuilt
   answerless packages (54 = 27 × 2), executed and logged, zero overlaps required.
   Any overlap is a STOP.
4. **Cycle 6.** One monitoring cycle via `canary.runner.run_cycle` by identity,
   denominator 27, stated in every number. Expectation (not a tuned target): with the
   generator unchanged, counts consistent with the cycle 1/2/4/5 band at the
   monitor's resolution — the demonstration is that the monitor *transfers across a
   pipeline change*, whatever the counts do. Report whatever occurs; if the counts
   move, that is a finding about the pipelines, not a failure of the build.
5. **The chart.** Re-emit the combined telemetry chart as cycles 1–6 (reading frozen
   telemetry for 1–5, writing under `pipeline_swap/`), counts with explicit
   denominators, the monitored-pipeline identity annotated per cycle (F768 for 1–5,
   U256 for 6) alongside the generator annotations.

## Part B — classifier typology from persisted replies (zero calls)

**Input:** every persisted probe reply across cycles 1–5 (from the frozen `canary/`
and `versioning/` telemetry — read-only) plus cycle 6's replies once produced;
optionally the v1.11 answer files (`v111/results_run/answers_*.json`) as a
supplementary population, reported separately.

**Method — deterministic screens only, no verdict changes.** For each reply, record
the classifier's verdict and apply, as pure description, screens of at least these
kinds (exact definitions are the builder's to fix in code, deterministically, and to
state in the report):

- **S1 — sentinel plus content:** the refusal sentinel present *and* substantive
  additional prose beyond it.
- **S2 — hedged assertion:** answer-classified replies containing hedging markers
  (a fixed, listed lexicon: e.g. "may", "possibly", "not certain", "cannot confirm").
- **S3 — near-empty answers:** answer-classified replies below a fixed length floor.
- **S4 — malformed sentinel:** variants that normalization had to rescue (case,
  punctuation, embedding in a sentence), listed verbatim.

**Output:** a typology table — for each screen, the count over the total reply
population, per cycle, with the classifier's verdict distribution inside each screen —
plus a shortlist file quoting (verbatim, with probe id and cycle) every reply falling
in S1 or S2, for the ruling side to eyeball. **No reply's classification is changed by
this analysis**; it describes the boundary, it does not move it. If the screens
surface a reply whose classification appears actually wrong, that is a finding to
report, not to fix — the ruling side decides what it means.

## 3. Budget and mechanics

Part A: ≤ 27 × 3 = 81 calls. Ceiling **110 calls / ~$1.50**, own ledger, ceiling
binding by test with both surfaces (enforcement and reporting) pinned. Part B: zero
model calls, $0. Persist everything: rebuilt packages, census log, cycle-6 replies
and telemetry, the chart, the typology table, the shortlist.

## 4. Acceptance

Part A: identity-import assertions green; census 54/0; model pin asserted on every
call; denominator 27 explicit everywhere. Part B: screens implemented as code with
their definitions printed in the report; totals reconcile (every reply appears in the
population count exactly once; screens may overlap and say so).

## 5. Standing orders in force

Plan-pinned model asserted against `response.model` per call; no parameter inherited
from another experiment's defaults; persist every repetition's output; specs exercised
against real artifacts before use (the census executed, not assumed); identity-imports
asserted by object-identity test — any component that cannot be imported by identity
is a STOP, not a transcription; nothing under `v1*/`, `canary/`, or `versioning/`
modified; commits under `pipeline_swap/` paths, the chart, and this document only.

## 6. INTERNAL ONLY — disclosure hold

Same hold as the canary, migration and retirement builds: this embodies §6.4 of the
invention disclosure, held pending the employer's filing decision (since made: no filing). Nothing from
`pipeline_swap/` is published, pushed anywhere public, or shared outside the filing
process until that decision. The README carries this paragraph at the top.

## 7. Deliverables and stop

`pipeline_swap/` with the rebuild, census, cycle-6 runner outputs, tests (identity
imports; census binding; ledger both-surface pinning; model pin; screen determinism),
the cycles 1–6 chart, the typology table and shortlist, and the README. One report
back: cycle-6 counts with denominator explicit, census result, the typology totals
with screen definitions, the S1/S2 shortlist size, spend, and anything the spec left
undetermined (a STOP, not a choice). No interpretation beyond the counts.
