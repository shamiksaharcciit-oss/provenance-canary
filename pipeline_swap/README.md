# Pipeline swap and classifier typology

> **Released.** This module embodied §6.4/§6.5 of an invention disclosure and was held
> from publication pending an IP filing decision. That decision has been made: no patent
> will be filed, and the techniques are published as prior art (see
> *When the System Changes Underneath You*, doi:10.5281/zenodo.22017670). Apache-2.0;
> personal work. The hold notice below is retained in the build notes as part of the
> historical record, with the employer reference generalized.

---

## Part A — the last leg of the loop

A reliability monitor is only worth its name if it survives the three things that change under a
live system: **the generator**, **the corpus**, and **the pipeline itself**. Cycles 1–3 changed
the generator, 4–5 changed the corpus across two releases, and cycle 6 changes the monitored
pipeline from `F768` (formatter) to `U256` (naive 256-token) — structurally the most different
pipeline available: different unit sizes, different boundaries, no formatter edits.

Everything else is held identical: same generator, same frozen prompt, same classifier, same
corpus v3, same 27 registered spans. **The store's spans and the construction code are
pipeline-independent; only the units they assemble change.** That is the demonstration.

### The cascade retirement

Probe `A-014-aster-router::f1`'s cross-doc construction needs its test-list successor's package.
That successor is `A-030-kestrel-broker::syn` — one of the three probes retired when the v3
release rewrote its answer span. The construction cannot be applied.

The rule applied is the design's own: **constructions depending on a disturbed span retire with
it.** That probe's *cross-doc leg alone* retires with cause
`depends_on_retired_span(A-030-kestrel-broker::syn)`; its answer-bearing and same-document legs
stay live. Walking to the next successor was rejected — it would invent a rule the construction
does not have.

**Denominators are therefore per counter, and every number says which:**

| counter | denominator |
|---|---|
| wrong abstention | **/27** |
| unsupported answer, same-document | **/27** |
| unsupported answer, cross-document | **/26** |

### A declared divergence

The build spec says run the cycle through `canary.runner.run_cycle` by identity. It cannot express
what this build needs: it assumes every probe has all three legs, reports one denominator, and
scores under one classifier. The loop is therefore local to this directory. Everything that
**calls or scores** is still imported by identity — the renderer and pinned client from
`canary.runner`, the v1 classifier from `src.v17.reading`, v2 from this build's instrument. Only
the iteration and tallying, which the amendment changed, are new.

## Part B — what the classifier was counting

`is_not_found` v1 is `answer.strip() == "NOT FOUND"`. It normalises whitespace and nothing else.

A reply of exactly **`NOT FOUND.`** — the declared sentinel with a trailing period — is an
unambiguous abstention that v1 scores as an *answer*, and therefore as a monitored failure. Across
cycles 1–5 that happened **33 times**, all in answerless slots, inflating `unsupported_answer`.

### Classifier v2, a versioned instrument

    strip whitespace -> strip trailing punctuation -> exact sentinel match

**Deliberately narrow.** No case folding: `not found` stays an ANSWER, because a model that
ignores the declared casing has not used the declared token, and widening further would start
deciding what counts as an abstention rather than recognising the one that was requested. No
substring matching: `NOT FOUND\n\nThe context provided…` stays an ANSWER under **both** versions.

**v1 is never modified and never removed.** It remains the classifier of record for every
published number. Corrections are emitted as parallel artifacts labelled `classifier-v2`; the
frozen telemetry keeps its v1 numbers as the record of what was actually reported.

### The screens

| screen | definition |
|---|---|
| S1 | sentinel present **and** ≥ 20 non-sentinel characters remain |
| S2 | ANSWER-classified and matching a fixed, listed hedging lexicon |
| S3 | ANSWER-classified and < 3 characters after stripping |
| S4 | ANSWER-classified but the text reads as an abstention |

S4 as specified asked for "variants that normalization had to rescue". This classifier rescues
none, so S4 is the honest complement: the cases a rescuing normalisation *would* have caught and
this one does not.

**No reply's classification is changed by any of this.** The screens describe the boundary; they
do not move it. The 41 sentinel-then-prose replies are shortlisted verbatim for a human and remain
ANSWER under both versions until ruled on.

## Running it

```bash
python pipeline_swap/rebuild_u256.py    # packages, cascade retirement, census — zero calls
python pipeline_swap/run_cycle6.py      # the only stage that spends
python pipeline_swap/typology.py        # screens over all persisted replies — zero calls
python pipeline_swap/rescore_v2.py      # additive v2 correction of cycles 1-5 — zero calls
python pipeline_swap/exposure_scan.py   # frozen v1.9/v1.11 populations — zero calls, read-only
python pipeline_swap/chart.py
python -m pytest pipeline_swap/tests/
```

## Boundaries kept

- `canary/` `0257ebe`, `versioning/` `fa9e587`, `versioning/retirement_demo/` `3f0b7fd` — all
  frozen, imported by identity, never modified. `v1*/` read-only throughout.
- Own ledger at **110 calls**, both surfaces pinned — binds at 110 and *reports* 110.
- Model pinned explicitly, asserted against `response.model`.
- Every package and every reply persisted; corrections additive and labelled, never overwriting.
