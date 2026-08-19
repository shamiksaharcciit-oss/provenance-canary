"""Cycles 1-6 chart. Counts with explicit denominators; monitored pipeline annotated per cycle.

Reads frozen telemetry for 1-5 READ-ONLY; writes only under pipeline_swap/.
Counts rather than rates because denominators differ by cycle AND, from cycle 6, by counter.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent / "results"
SRC = [
    ("baseline", ROOT / "canary/results/telemetry_cycle1_baseline.json", "F768"),
    ("stability", ROOT / "canary/results/telemetry_cycle2_stability.json", "F768"),
    ("model swap", ROOT / "canary/results/telemetry_cycle3_model_swap.json", "F768"),
    ("after v2", ROOT / "versioning/results/telemetry_cycle4_after_release.json", "F768"),
    ("after v3", ROOT / "versioning/retirement_demo/results/telemetry_cycle5_after_retirement.json", "F768"),
    ("pipeline swap", HERE / "telemetry_cycle6_pipeline_swap.json", "U256"),
]
SERIES = [("wrong_abstention", "wrong abstention", "#c0392b", "o"),
          ("unsupported_answer_same_doc", "unsupported answer - same-doc", "#2874a6", "s"),
          ("unsupported_answer_cross_doc", "unsupported answer - cross-doc", "#7d3c98", "^")]


def main() -> int:
    cyc = []
    for label, p, arm in SRC:
        t = json.loads(p.read_text(encoding="utf-8"))
        cyc.append({"label": label, "arm": arm, "model": t["model_requested"],
                    "rates": t["rates"], "n": t.get("n_probes"),
                    "denoms": t.get("denominators")})
    x = range(len(cyc))
    fig, ax = plt.subplots(figsize=(11, 5.4))
    for key, label, colour, marker in SERIES:
        ys = [c["rates"][key]["numerator"] for c in cyc]
        ax.plot(x, ys, marker=marker, color=colour, label=label, linewidth=2, markersize=8)
        for xi, c in zip(x, cyc):
            r = c["rates"][key]
            ax.annotate(f"{r['numerator']}/{r['denominator']}", (xi, r["numerator"]),
                        textcoords="offset points", xytext=(0, 9), ha="center",
                        fontsize=7.5, color=colour)
    ax.axvspan(1.5, 2.5, color="#f4d03f", alpha=0.18)
    for xpos, txt in ((2, "generator\nswapped"), (3, "corpus v2"), (4, "corpus v3\n3 retired"),
                      (5, "PIPELINE\nF768 -> U256")):
        ax.text(xpos, ax.get_ylim()[1] * 0.99, txt, ha="center", va="top", fontsize=7.5,
                style="italic", color="#555")
    for v in (2.5, 3.5, 4.5):
        ax.axvline(v, color="#999", linestyle="--", linewidth=0.8)
    ax.axvline(4.5, color="#c0392b", linestyle="--", linewidth=1.4)
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{c['label']}\n{c['model'].replace('claude-','')}\npipeline {c['arm']}"
                        for c in cyc], fontsize=7.5)
    ax.set_ylabel("failure COUNT (denominator beside each point)")
    ax.set_title("Canary monitor across generator, corpus and pipeline changes - cycles 1-6\n"
                 "counts, not rates: denominators differ by cycle and, from cycle 6, by counter\n"
                 "classifier v1 as published - INTERNAL ONLY, disclosure hold", fontsize=9.5)
    ax.set_ylim(bottom=-1.2)
    ax.grid(alpha=0.25, linestyle=":")
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    p = HERE / "cycles_1_to_6.png"
    fig.savefig(p, dpi=150)
    print(f"  wrote {p}")
    print(f"  cycle 6 denominators: {cyc[-1]['denoms']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
