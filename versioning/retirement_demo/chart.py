"""Cycles 1-5 chart (build spec §4). COUNTS on the axis, denominators in the labels.

Reads cycles 1-4 from the frozen artifacts READ-ONLY and writes only under retirement_demo/.
Counts rather than rates because the denominator changes at cycle 5: plotting rates would let a
denominator change look like a behaviour change.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CAN = ROOT / "canary" / "results"
V = ROOT / "versioning" / "results"
HERE = Path(__file__).resolve().parent / "results"
SERIES = [("wrong_abstention", "wrong abstention", "#c0392b", "o"),
          ("unsupported_answer_same_doc", "unsupported answer - same-doc", "#2874a6", "s"),
          ("unsupported_answer_cross_doc", "unsupported answer - cross-doc", "#7d3c98", "^")]


def main() -> int:
    cycles = json.loads((CAN / "cycles_summary.json").read_text(encoding="utf-8"))["cycles"]
    for p in (V / "telemetry_cycle4_after_release.json",
              HERE / "telemetry_cycle5_after_retirement.json"):
        cycles.append({k: v for k, v in json.loads(p.read_text(encoding="utf-8")).items()
                       if k != "probes"})

    labels = ["baseline\nv1", "stability\nv1", "model swap\nv1",
              "after release\nv2", "after retirement\nv3"]
    models = [c["model_requested"].replace("claude-", "") for c in cycles]
    ns = [c["n_probes"] for c in cycles]
    x = range(len(cycles))

    fig, ax = plt.subplots(figsize=(10, 5))
    for key, label, colour, marker in SERIES:
        ys = [c["rates"][key]["numerator"] for c in cycles]
        ax.plot(x, ys, marker=marker, color=colour, label=label, linewidth=2, markersize=8)
        for xi, yi in zip(x, ys):
            ax.annotate(str(yi), (xi, yi), textcoords="offset points", xytext=(0, 8),
                        ha="center", fontsize=8, color=colour)
    ax.axvspan(1.5, 2.5, color="#f4d03f", alpha=0.18)
    ax.text(2, ax.get_ylim()[1] * 0.98, "generator swapped", ha="center", va="top",
            fontsize=8, style="italic", color="#7d6608")
    ax.axvline(2.5, color="#555", linestyle="--", linewidth=1)
    ax.axvline(3.5, color="#555", linestyle="--", linewidth=1)
    ax.text(4, ax.get_ylim()[1] * 0.98, "3 probes retired\ndenominator 30 -> 27",
            ha="center", va="top", fontsize=8, style="italic", color="#555")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{l}\n{m}\nn={n}" for l, m, n in zip(labels, models, ns)], fontsize=8)
    ax.set_ylabel("failure COUNT (denominator in label)")
    ax.set_title("Canary monitor across two corpus releases - cycles 1-5\n"
                 "counts, not rates: the denominator changes at cycle 5\n"
                 "INTERNAL ONLY - disclosure hold", fontsize=10)
    ax.set_ylim(bottom=-0.8)
    ax.grid(alpha=0.25, linestyle=":")
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    p = HERE / "cycles_1_to_5.png"
    fig.savefig(p, dpi=150)
    print(f"  wrote {p}")
    print(f"  denominators: {ns}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
