"""Canary chart (build spec §1.4): rates per cycle, both failure directions.

Reads the telemetry JSONs; plots nothing it did not read. Headless backend so it runs anywhere.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "canary" / "results"
SERIES = [("wrong_abstention", "wrong abstention (answer WAS present)", "#c0392b", "o"),
          ("unsupported_answer_same_doc", "unsupported answer — same-doc", "#2874a6", "s"),
          ("unsupported_answer_cross_doc", "unsupported answer — cross-doc", "#7d3c98", "^")]


def main() -> int:
    s = json.loads((OUT / "cycles_summary.json").read_text(encoding="utf-8"))
    cycles = s["cycles"]
    labels = [c["cycle"].replace("_", "\n") for c in cycles]
    models = [c["model_requested"] for c in cycles]
    x = range(len(cycles))

    fig, ax = plt.subplots(figsize=(8, 4.6))
    for key, label, colour, marker in SERIES:
        ys = [c["rates"][key]["rate"] for c in cycles]
        ax.plot(x, ys, marker=marker, color=colour, label=label, linewidth=2, markersize=8)
        for xi, yi, c in zip(x, ys, cycles):
            ax.annotate(f"{c['rates'][key]['numerator']}/{c['rates'][key]['denominator']}",
                        (xi, yi), textcoords="offset points", xytext=(0, 8),
                        ha="center", fontsize=8, color=colour)

    ax.axvspan(1.5, 2.5, color="#f4d03f", alpha=0.18)
    ax.text(2, ax.get_ylim()[1] * 0.97, "generator swapped", ha="center", va="top",
            fontsize=8, style="italic", color="#7d6608")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{l}\n{m}" for l, m in zip(labels, models)], fontsize=8)
    ax.set_ylabel(f"failure rate (n = {cycles[0]['n_probes']} probes)")
    ax.set_title("Canary monitor — three cycles on the F768 pipeline\n"
                 "INTERNAL ONLY — disclosure hold", fontsize=10)
    ax.set_ylim(bottom=-0.02)
    ax.grid(alpha=0.25, linestyle=":")
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    path = OUT / "canary_cycles.png"
    fig.savefig(path, dpi=150)
    print(f"  wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
