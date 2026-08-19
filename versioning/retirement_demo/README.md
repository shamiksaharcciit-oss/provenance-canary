# Retirement-path demonstration — corpus v3

> **Released.** This module embodied §6.4/§6.5 of an invention disclosure and was held
> from publication pending an IP filing decision. That decision has been made: no patent
> will be filed, and the techniques are published as prior art (see
> *When the System Changes Underneath You*, doi:10.5281/zenodo.22017670). Apache-2.0;
> personal work. The hold notice below is retained in the build notes as part of the
> historical record, with the employer reference generalized.

---

## Why this build exists

The `fa9e587` version-migration build proved the DISTURBED-and-retire path two ways — through the
298-span ground-truth acceptance and through a unit test — but never exercised it live: its seed
walk happened to miss every probe span, so all 30 probes survived and nothing retired. That was
the honest outcome of a no-hand-picking rule, and it left the most consequential branch of §6.5
demonstrated only in the small.

This build reaches it.

## The design stance, stated rather than buried

**The edits here are deliberately targeted at probe answer spans.** This build exercises a code
path; it does not measure nature, and it would be dishonest to present targeted edits as though
they were a sampled release. What remains seed-governed is *which* probes: the store is walked in
its fixed order and the first three probes lying in three distinct documents become the targets.
Nobody chose convenient ones, and `expected_outcomes_v3.json` logs the walk including its skips.

## The release (v2 → v3, single hop)

| edits | class | expected |
|---|---|---|
| 3 × rewrite a sentence **inside** a target probe's answer span | E4 | **DISTURBED** |
| 1 × insertion before a span in another probe-bearing document | E1 | UNCHANGED, +delta |
| 1 × deletion before a span in another probe-bearing document | E2 | UNCHANGED, −delta |
| 40 documents untouched | E6 | UNCHANGED, delta 0 |

The mixed benign edits matter: a release that only ever destroys spans would not show that the
migrator distinguishes destruction from ordinary movement.

As in the parent build, **the ground truth is written before the migrator runs** — computed from
edit and span coordinates alone — so acceptance compares two independent derivations rather than
grading the migrator against itself. The edit taxonomy, its application and its expectation
arithmetic are imported by identity from `versioning.edits`; this module supplies a new edit
list, not a new generator.

## What happens to a disturbed probe

It is **retired**, and the retirement log is a first-class deliverable rather than a side effect.
Each entry names the probe, its v2 span, the migrator's cause, and the intersecting edit.

A retired probe emits no coordinates and does not appear in the surviving store. That is the
whole point: a probe carried past a disturbed span is a probe whose ground truth has quietly
stopped being true, and a monitor built on it reports confidently about nothing. Deciding what to
do about a retirement — re-register, replace, drop — is a human's job; the mechanism's
responsibility ends at refusing to guess.

## The denominator

Cycle 5 runs on **27 probes, and every number says 27.** The combined chart plots **counts, not
rates**, with denominators in the axis labels, because a denominator that changes between cycles
makes a rate plot misleading in exactly the direction that flatters the system: three retirements
would move every rate slightly, and a reader could not tell that from a behaviour change.

Cycle 5 is described, wherever it is described, as clustering with the pre-release baselines at
the monitor's resolution — never as identical to them. Thirty-ish probes cannot separate small
count differences from noise; the claim the data supports is relative, that corpus releases sit
with the baselines while a model swap sits an order away.

## Running it

```bash
python versioning/retirement_demo/release.py         # v3 + expectations, zero calls
python versioning/retirement_demo/migrate_retire.py  # migrate, retire, census, accept; zero calls
python versioning/retirement_demo/run_cycle5.py      # the only stage that spends
python versioning/retirement_demo/chart.py           # cycles 1-5
python -m pytest versioning/retirement_demo/tests/
```

## Boundaries kept

- **`canary/` frozen at `0257ebe`**, imported by identity, never modified. The parent build's
  artifacts (`corpus_v2`, migration records, cycles 1–4 telemetry) are read-only here.
- **Own ledger, both surfaces**: binds at 110 calls and *reports* 110.
- **Model pinned explicitly**, asserted at construction and against `response.model`.
- **Everything persisted**: edit list, v3 documents, expectations, per-span migration records,
  retirement log, census log, cycle-5 replies, chart.
- Single hop only. No re-registration workflow. No model-assisted span recovery — that would
  replace a proof with an opinion.
