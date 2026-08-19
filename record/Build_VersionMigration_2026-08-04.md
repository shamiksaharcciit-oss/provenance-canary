# Version migration prototype — build instructions for agent 1

**Status:** engineering build, not a pre-registered experiment. No hypotheses, no freeze,
no branches. Standing orders apply in full (§5). INTERNAL ONLY (§6).
**Date:** 4 August 2026
**Purpose:** reduce §6.5 of `Invention_Disclosure_Provenance_DRAFT.md` (document
versioning and provenance stability) from a designed extension to a
reduced-to-practice one: registered answer spans migrated across real document edits
by the three-outcome mapping, with the answer-free census re-proved after migration,
and monitoring telemetry shown continuous across a corpus release.

---

## 1. What to build

Everything under a new `versioning/` directory only. Four parts.

### 1.1 Versioned corpus

The existing Track A corpus is **version 1** and is never modified. Build a scripted,
deterministic edit generator (seed 1337) that produces a **version 2** of a subset of
documents, stored as new files under `versioning/corpus_v2/`. Select 15 of the 45
documents by seed walk; the remaining 30 pass through untouched (they are version 2 by
identity — the control that identity migration is exact).

The edit script is the ground truth, so it must record its own intent. Each edit is
one of a fixed taxonomy, and at generation time the script computes, from the edit's
coordinates and every registered span's coordinates, the **expected outcome per span**
and writes it to `versioning/expected_outcomes.json` before the migrator ever runs:

- **E1 — insertion before a span** (new paragraph, heading, boilerplate): expect
  UNCHANGED with positive offset delta.
- **E2 — deletion before a span**: expect UNCHANGED with negative delta.
- **E3 — edit strictly after a span** (any kind): expect UNCHANGED with zero delta.
- **E4 — edit intersecting a span** (rewrite a sentence inside it, delete part of it,
  or insert into its middle): expect DISTURBED.
- **E5 — block relocation** (cut a contiguous block containing at least one whole
  span, paste it elsewhere in the same document): expect MOVED.
- **E6 — untouched document**: expect UNCHANGED, delta zero, for every span in it.

Coverage requirement: at least 3 registered spans per expected class E1–E5 across the
edited documents, plus the E6 control set. If the seed walk's selection cannot reach
that coverage, extend the walk (more documents or more edits per document) — log the
extension; do not hand-pick.

### 1.2 Span migrator

Character-level diff between each document's version 1 and version 2 (standard
library diffing is fine; the arithmetic is prior-art implementation and the spec does
not care which, only that it is deterministic). Map every registered answer span
through the diff into exactly one outcome:

- **UNCHANGED**: the span's characters fall entirely inside equal regions of the
  diff; migrated coordinates = original coordinates shifted by the net delta of
  preceding edits.
- **MOVED**: the span is not covered by equal regions in place, but its exact byte
  sequence exists intact at a determinable new location (the relocated block).
  Migrated coordinates = the new location.
- **DISTURBED**: neither of the above — an edit intersects the span itself. Never
  migrated, no coordinates emitted; logged with the intersecting edit identified.

**The binding invariant, asserted for every UNCHANGED and MOVED span:** the text at
the migrated coordinates in version 2 is byte-identical to the text at the original
coordinates in version 1. Migration is verified, not trusted. A single failure of
this assertion is a STOP, not a statistic.

Ambiguity rule: if a MOVED candidate's byte sequence appears at more than one
location in version 2, classify DISTURBED with cause `ambiguous_relocation` — the
migrator never guesses among candidates.

### 1.3 Store migration and census re-proof

Apply the migrator to the canary probe store's 30 registered spans against the
version-2 corpus. Probes whose span migrated (UNCHANGED or MOVED) are rebuilt:
packages reconstructed against version 2 by the identity-imported constructions
(same imports as the canary build — `v19.packages.build_all`,
`v111.unanswerable.same_doc_answerless`, the cross-doc construction), budgets
unchanged. Probes whose span is DISTURBED are **retired with cause logged** — exactly
the §6.5 rule: disturbed spans are flagged for re-registration, never silently
carried.

Then the census, re-executed in full against version 2: every rebuilt answerless
package verified zero-overlap with its migrated answer span by provenance, executed
and logged, before any package is used. The guarantee is re-proved, not assumed. Any
overlap is a STOP.

### 1.4 Continuity demonstration (the only part that calls a model)

One monitoring cycle — **cycle 4** — run with the migrated store against the
version-2 corpus: generator `claude-sonnet-5`, plan-pinned and asserted, the frozen
v1.9 prompt, the identity-imported NOT FOUND classifier. Same telemetry format as
cycles 1–3, with the denominator being the surviving (non-retired) probe count,
stated explicitly. The comparison artifact is a chart of cycles 1–4: baseline, flat,
model-swap spike, and then — back on the baseline generator, across a corpus release —
the expected return to baseline rates on a smaller denominator. Report whatever the
numbers are; nothing is tuned to make continuity look better.

Cycle 1–3 telemetry is read from `canary/results/` for the chart but **nothing under
`canary/` is modified** — it is frozen at 0257ebe. Cycle 4's telemetry, the chart,
and all migration artifacts live under `versioning/`.

## 2. What NOT to build

No re-registration UI or workflow for disturbed spans (logging the retirement is the
mechanism). No multi-hop migration (v1→v2→v3). No model-assisted diffing or span
recovery — a model call to "find where the span went" would replace a proof with an
opinion and is out of scope by design, not by budget. No changes to the formatter,
the apparatus, or anything under `v1*/`.

## 3. Budget and mechanics

Parts 1.1–1.3 are pure computation: **zero model calls, $0**. Part 1.4 is one cycle:
≤ 30 probes × 3 packages = ≤ 90 calls. Ceiling **120 calls / ~$2**, own ledger,
ceiling binding by test — and per the standing rule below, the test pins **both** the
enforcement surface and the reporting surface. Persist every artifact: version-2
documents, the diff opcodes per document, `expected_outcomes.json`, per-span
migration records with coordinates and verification results, retirement log, census
log, cycle-4 replies and telemetry.

## 4. Acceptance against ground truth

The migrator's outcomes are compared against `expected_outcomes.json` — every span in
the edited documents plus the E6 controls. Expected: 100% agreement. Any disagreement
is reported span-by-span and is a STOP for that span's class (the expectation file
may be wrong; the migrator may be wrong; the report says which artifact says what,
and the ruling side decides). The byte-identity invariant of §1.2 is additionally
asserted independently of the expectations file.

## 5. Standing orders in force

Plan-pinned model asserted against `response.model` on every cycle-4 call; no
parameter inherited from another experiment's defaults — own config, own ledger,
every parameter surface (enforcement *and* reporting) pinned by test; persist every
repetition's output; specs exercised against real artifacts before use (the census of
§1.3 executed, not assumed); identity-imports asserted by object-identity test, no
transcription — if a needed component cannot be imported by identity, STOP; nothing
under `v1*/` or `canary/` modified; commits under `versioning/` paths plus this
document only.

## 6. INTERNAL ONLY — disclosure hold

This prototype embodies §6.5 of the invention disclosure, which is deliberately
excluded from the publication and held pending the employer's filing decision (since made: no filing), under the same
hold as the canary prototype. Nothing from `versioning/` — code, corpus edits,
telemetry, chart, or description — is published, pushed to any public location, or
shared outside the filing process until that decision is made. The README carries
this paragraph at the top.

## 7. Deliverables and stop

`versioning/` with the edit generator, migrator, store migration, census, cycle-4
runner, tests (ground-truth agreement; byte-identity invariant; ambiguity rule;
ledger ceiling binding on both surfaces; model-pin assertion; identity-import
assertions), all persisted artifacts, the cycles 1–4 chart, and the README. One
report back: what was built, the per-class span counts and migration outcomes, the
ground-truth agreement result, the census result, cycle-4 numbers with denominators,
spend, and anything the spec left undetermined (which is a STOP, not a choice). No
interpretation beyond the counts.
