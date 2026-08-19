# provenance-canary

The artifact release for **When the System Changes Underneath You**
(doi:[10.5281/zenodo.22017670](https://doi.org/10.5281/zenodo.22017670)) —
deterministic runtime monitoring for retrieval pipelines, built on the same
provenance layer as the companion paper *When the Scoreboard Lies*
(doi:[10.5281/zenodo.22016705](https://doi.org/10.5281/zenodo.22016705)).

A canary, as in the coal mine: seeded probe questions whose correct behaviour is
a provable property of the input — the answer is demonstrably present, or
demonstrably absent — so the expectation needs no judge model and survives any
wording the system chooses. Scoring is exact counts. Every reply is persisted;
every verdict is re-derivable.

## What is here

| Path | Contents |
|---|---|
| `canary/` | the probe store builder, runner, ledger, and cycles 1–3: baseline, stability, and the silent generator swap detected the day it happened |
| `versioning/` | span migration across a corpus release (cycle 4): registered content migrated across document edits with 298/298 verified agreement |
| `versioning/retirement_demo/` | a second corpus release with document retirement (cycle 5) |
| `pipeline_swap/` | a change of the monitored pipeline itself (cycle 6), the refusal-sentinel classifiers v2/v3, and the re-scoring tools that re-derive every published cell from the archive |
| `record/` | the four build notes, retained verbatim as the historical record (employer references generalized, as disclosed below) |

Each module carries its own README, tests, and frozen `results/` — telemetry,
ledgers, probe stores, and charts for all six monitoring cycles.

## Reproducing

The modules run **on top of the companion repository's apparatus** — that is the
paper's point: the monitoring layer is the evaluation layer, reused. Clone both
side by side and put the companion on the path:

```bash
git clone https://github.com/shamiksaharcciit-oss/provenance-rag-eval
git clone https://github.com/shamiksaharcciit-oss/provenance-canary
cd provenance-canary
pip install -r ../provenance-rag-eval/requirements.txt pytest
PYTHONPATH=../provenance-rag-eval python -m pytest canary/tests versioning/tests \
    versioning/retirement_demo/tests pipeline_swap/tests -q   # 77 tests, offline
```

The tests and the re-scoring tools run offline against the frozen results. The
live monitoring cycles (`run_cycles.py`, `run_cycle4.py`, `run_cycle5.py`,
`run_cycle6.py`) require an Anthropic API key and reproduce the cycle mechanics,
not the historical events — the swap they detected happened on the provider's
schedule, not ours. The corpus is entirely synthetic (invented systems:
kestrel, basalt, cobalt, …); no third-party text is used or redistributed.

## Provenance of this repository

These modules embodied §6.4/§6.5 of an invention disclosure and were withheld
from the companion paper's release pending an IP filing decision. That decision
has been made: **no patent will be filed**. The techniques are published as
prior art; no patent applications are pending or planned. This is independent
personal work; in the historical record (`record/`), references to the author's
employer have been generalized, with no content, figure or verdict altered —
the same convention as the companion repository.

## Citing

Cite the paper: doi:10.5281/zenodo.22017670. Machine-readable citation in
`CITATION.cff`. License: Apache-2.0.
