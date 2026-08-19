# Canary prototype — build instructions for agent 1

**Status:** engineering build, not a pre-registered experiment. No hypotheses, no freeze,
no branches. Standing orders still apply in full (§4). INTERNAL ONLY (§5).
**Date:** 3 August 2026
**Purpose:** assemble the runtime reliability monitor described in §6.4 of
`Invention_Disclosure_Provenance_DRAFT.md` from components that already exist, run it
against a real pipeline, and produce the demonstration artifacts. This converts the
disclosure's one prophetic embodiment into a reduced-to-practice one.

---

## 1. What to build

A monitoring loop, under `canary/` only, with four parts:

1. **Probe store.** 30 questions drawn from the Track A test set by fixed seed 1337,
   each carrying: its registered answer span; an **answer-bearing package** for the
   monitored pipeline (the frozen v1.9 construction, B(q) budgets); a **same-document
   answerless package** (the v1.11 E-A same-doc construction — gold-overlapping units
   excluded, on-topic, padded to budget); and a **cross-document answerless package**
   (the v1.11 cross-doc construction). Constructions imported from `v19/`/`v111/` by
   identity — no transcription. Questions whose same-doc construction is impossible
   (the six small documents) are excluded by the store builder with the exclusion
   logged; draw replacements by the same seed walk so the store holds 30.
2. **Probe runner.** One monitoring cycle = for each stored probe: submit the
   answer-bearing package with the frozen v1.9 prompt; classify the reply as ANSWER or
   REFUSAL using the v1.11 NOT FOUND classifier (import by identity); a REFUSAL
   increments `wrong_abstention`. Submit each answerless package likewise; an ANSWER
   increments `unsupported_answer` (per construction, counted separately). All outputs
   persisted, every call ledgered, models plan-pinned and asserted per the standing
   order.
3. **Telemetry.** Per cycle, a JSON record: timestamp, monitored pipeline id, model id,
   counts and rates with denominators, per-probe rows. Exact counts only; no judge, no
   score beyond the classifier.
4. **Report.** A small chart (rates per cycle, both failure directions) and a README
   that explains the loop in one page and carries the §5 notice verbatim.

## 2. The demonstration run

Monitored pipeline: `F768` (the formatter pipeline, as the stand-in "deployed" system).
Three cycles, ~180 calls total:

- **Cycle 1 — baseline.** Generator `claude-sonnet-5` (plan-pinned). Establishes the
  reference rates.
- **Cycle 2 — stability.** Identical configuration, fresh calls. Shows cycle-to-cycle
  noise on exact counts.
- **Cycle 3 — induced change.** Generator switched to `claude-haiku-4-5-20251001`
  (pinned), everything else identical. This simulates an unannounced model swap in
  production. From the v1.11 record, this model abstains rarely if ever; the telemetry
  is expected to move — most plausibly `unsupported_answer` rising on answerless
  packages — and *the point of the demonstration is that the monitor detects the
  change, whichever direction it takes*. Do not tune anything to make the movement
  larger; report what happens.

The chart of those three cycles — flat, flat, moved — is the artifact the disclosure
and any internal demo needs.

## 3. Budget and mechanics

Ceiling **400 calls / ~$5**; expected ~185 plus retries. Direct calls (not batch) are
fine at this scale; the cost guard is not modified. Reuse cached package material where
byte-identical; persist every generated reply and every package text (the standing
persistence order). If any needed component cannot be imported by identity and would
have to be re-implemented, STOP and say so rather than transcribing.

## 4. Standing orders in force

Plan-pinned models asserted against `response.model` on every call; no
experiment-scoped parameter inherited from another experiment's defaults (own ledger
ceiling, own config, binding by test); persist every repetition's output; specs
exercised against real artifacts before running (the store builder's census: every
answerless package verified zero-overlap by provenance, executed, logged); nothing
under `v1*/` modified; closed artifacts and the paper untouched; commits under
`canary/` paths plus this document only.

## 5. INTERNAL ONLY — disclosure hold

This prototype embodies §6.4 of the invention disclosure, which is deliberately
excluded from the publication and held pending the employer's filing decision (since made: no filing). Nothing from
`canary/` — code, README, chart, telemetry, or description — is published, pushed to
any public location, or shared outside the filing process until that decision is made.
The README carries this paragraph at the top.

## 6. Deliverables and stop

`canary/` with store builder, runner, telemetry, tests (construction census;
classifier and builder identity-imports asserted; ledger ceiling binding; model-pin
assertion), the three-cycle telemetry JSONs, the chart, and the README. One report
back: what was built, the census result, the three cycles' numbers, spend, and
anything the spec left undetermined (which is a STOP, not a choice). No interpretation
beyond the counts.
