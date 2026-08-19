# Canary — runtime reliability monitor (prototype)

> **Released.** This module embodied §6.4/§6.5 of an invention disclosure and was held
> from publication pending an IP filing decision. That decision has been made: no patent
> will be filed, and the techniques are published as prior art (see
> *When the System Changes Underneath You*, doi:10.5281/zenodo.22017670). Apache-2.0;
> personal work. The hold notice below is retained in the build notes as part of the
> historical record, with the employer reference generalized.

---

## What it is

A RAG pipeline in production has no ground truth. You cannot tell, from traffic alone, whether
it has started refusing questions it can answer or answering questions it cannot. The canary
supplies ground truth on a schedule: a small store of **registered probes** whose answers are
known by construction, replayed against the live pipeline each cycle, scored by exact counts.

It measures **two failure directions**, which is the point — a monitor that watches only one is
gameable by moving the other:

| direction | probe | failure |
|---|---|---|
| **wrong abstention** | an **answer-bearing** package | the pipeline says `NOT FOUND` when the answer is present |
| **unsupported answer** | an **answerless** package | the pipeline answers when nothing supports it |

Answerless probes come in two flavours, counted separately: **same-document** (on-topic,
plausible, gold-bearing units removed — the hard case) and **cross-document** (another
document's context entirely).

## The loop

```
probe store  ──▶  probe runner  ──▶  telemetry  ──▶  chart
 30 probes        one cycle =        exact counts     rates per
 seed 1337        3 calls/probe      + per-probe      cycle, both
 census'd         classifier only    rows             directions
```

**Probe store** (`store.py`). Thirty questions drawn from the Track A test set by a seeded walk,
each carrying its registered answer span and three packages. Every construction is **imported by
identity** from the frozen experiment code — `v19.packages.build_all` for the answer-bearing
package, `v111.unanswerable.same_doc_answerless` for the same-document one — so the monitor
measures the same objects the experiments did, and there is no second implementation to drift.

**The store's census is a gate, not a report.** Every answerless package is verified to contain
**zero** gold coverage by provenance before it enters the store. A probe failing either
construction is excluded with its cause logged and replaced by the next draw in the same seed
walk, so the store always holds 30. Two causes exist:

- `same_doc_unconstructible` — the document is small enough that removing gold-bearing units
  leaves nothing.
- `cross_doc_contains_gold` — the successor draw landed in the *same* document, so its package
  contains the answer and is not answerless. Successor-with-wraparound does not guarantee a
  different document; on Track A, 4 of 176 queries have a same-document successor and all of
  their packages fully contain the querying gold. The census catches this rather than trusting
  the construction's name.

**Probe runner** (`runner.py`). One cycle submits each probe's three packages under the frozen
v1.9 prompt and classifies each reply with **v1.11's `NOT FOUND` classifier, imported by
identity**. Exact counts only — no judge, no similarity score, nothing that could drift.

**Telemetry** (JSON per cycle). Timestamp, monitored pipeline, requested and served model,
counts and rates with explicit denominators, and every per-probe row with its full reply text.

## Operating it

```bash
python canary/run_cycles.py     # builds the store if absent, runs the cycles, writes telemetry
python canary/chart.py          # renders canary_cycles.png from the telemetry
python -m pytest canary/tests/  # census, identity imports, ledger ceiling, model pin
```

Re-running is safe: a cycle whose telemetry already exists is skipped rather than repaid.

## Guarantees it keeps

- **The model is pinned, never inherited.** Passed explicitly, asserted at construction, and
  asserted against `response.model` on every cycle — a served model that differs is a stop, not
  a footnote. A configuration default that could reach a call is a defect wherever it lives.
- **Its own ceiling.** `CanaryLedger` inherits v1.8's crash-survivable storage and enforces
  **400 calls**, not the 25,000 it would have inherited. A ceiling that cannot fire is
  decorative; a test asserts this one fires.
- **Everything persisted.** Every package text and every reply, not summaries.
- **Nothing modified upstream.** `v19/`, `v111/` and every closed artifact are read-only here.

## What it is not

Not a quality metric — it counts two specific failures and says nothing about answer quality.
Not a benchmark — 30 probes detect movement, they do not rank systems. Not a substitute for
evaluation — it watches a pipeline that was evaluated elsewhere and tells you when it stops
behaving like the thing that was evaluated.
