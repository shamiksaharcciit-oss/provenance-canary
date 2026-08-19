# Version migration — document versioning and provenance stability (prototype)

> **Released.** This module embodied §6.4/§6.5 of an invention disclosure and was held
> from publication pending an IP filing decision. That decision has been made: no patent
> will be filed, and the techniques are published as prior art (see
> *When the System Changes Underneath You*, doi:10.5281/zenodo.22017670). Apache-2.0;
> personal work. The hold notice below is retained in the build notes as part of the
> historical record, with the employer reference generalized.

---

## The problem

Registered answer spans are character offsets into a document. Documents get edited. An offset
into version 1 points at the wrong text in version 2 — silently, because an offset is always
*some* text. Any provenance system anchored to offsets either migrates its registrations across
edits or quietly rots, and a monitor built on rotted registrations reports confidently about
nothing.

## The three-outcome mapping

Every registered span maps through a character-level diff into exactly one outcome. There is no
fourth, and no "probably":

| outcome | condition | result |
|---|---|---|
| **UNCHANGED** | the span lies entirely inside an equal region | migrated, shifted by the net delta of preceding edits |
| **MOVED** | not in place, but the exact byte sequence exists intact at one determinable location | migrated to that location |
| **DISTURBED** | neither | **never migrated**, no coordinates emitted, flagged for re-registration |

**Two rules make the mapping safe rather than merely plausible.**

*The binding invariant.* For every UNCHANGED and MOVED span, the text at the migrated coordinates
in v2 must be byte-identical to the text at the original coordinates in v1. This is asserted, not
assumed, and a single failure raises `MigrationNotVerified` — a stop, not a statistic. A migration
that cannot prove itself is worth less than no migration, because it looks like success.

*The ambiguity rule.* If a MOVED candidate's byte sequence occurs more than once in v2, the
outcome is DISTURBED with cause `ambiguous_relocation`. The migrator never picks among candidates.
A span that could be in two places is not a span that moved.

**DISTURBED is a feature.** The disclosure's §6.5 rule is that disturbed spans are flagged for
re-registration and never silently carried. A system that "recovers" a disturbed span by finding
something similar has replaced a proof with an opinion — which is why model-assisted span recovery
is out of scope here by design, not by budget.

## What was demonstrated

Version 1 is the Track A corpus, never modified. A deterministic edit generator (seed 1337)
produced version 2 of 15 of 45 documents under `corpus_v2/`; the other 30 pass through by
identity, controlling that identity migration is exact.

**The ground truth is written before the migrator runs.** `expected_outcomes.json` is computed
from edit coordinates and span coordinates alone — arithmetic, not observation — so the
acceptance in `acceptance.json` compares two independently derived artifacts rather than checking
the migrator against itself.

Then the canary's registered store is migrated against version 2, surviving probes are rebuilt by
the same identity-imported constructions, and **the answer-free census is re-executed in full**:
every rebuilt answerless package re-proved zero-overlap against its *migrated* span. The guarantee
is re-proved against the new corpus, never inherited from the old one.

Finally one monitoring cycle runs against version 2 on the baseline generator, using
`canary.runner.run_cycle` **imported by identity** — cycle 4 is the same loop as cycles 1–3, not a
reimplementation, which is what makes the four-cycle comparison mean anything.

## Running it

```bash
python -c "from pathlib import Path; from versioning.edits import build_v2; build_v2(Path('versioning'))"
python versioning/acceptance.py       # migrator vs ground truth
python versioning/store_migrate.py    # migrate the store, re-prove the census
python versioning/run_cycle4.py       # the one stage that calls a model
python versioning/chart.py            # cycles 1-4
python -m pytest versioning/tests/
```

Parts 1–3 are pure computation and spend nothing.

## Guarantees it keeps

- **Nothing upstream is modified.** `canary/` is frozen at `0257ebe` and is read here only;
  `v1*/` and every closed artifact are read-only.
- **Its own ceiling, on both surfaces.** `VersioningLedger` binds at 120 calls and *reports* 120 —
  a parameter has as many surfaces as it has readers, and pinning only the one that throws leaves
  the reader misinformed.
- **The model is pinned, never inherited**, and asserted against `response.model`.
- **Everything persisted**: version-2 documents, expectations, per-span migration records with
  coordinates and verification results, the retirement log, the census log, cycle-4 replies.

## What it is not

Not a diffing library — the arithmetic is standard and the spec says so. Not multi-hop: v1→v2
only. Not a re-registration workflow; logging the retirement is the mechanism, and deciding what
to do about a retired probe is a human's job.
