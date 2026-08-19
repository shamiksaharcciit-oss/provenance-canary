"""Cycles 1-4 chart (build spec §1.4). Reads canary/ telemetry READ-ONLY; writes under versioning/."""
from __future__ import annotations
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CAN = ROOT / "canary" / "results"
V = ROOT / "versioning" / "results"
SERIES = [("wrong_abstention", "wrong abstention", "#c0392b", "o"),
          ("unsupported_answer_same_doc", "unsupported answer - same-doc", "#2874a6", "s"),
          ("unsupported_answer_cross_doc", "unsupported answer - cross-doc", "#7d3c98", "^")]


def main() -> int:
    cycles = json.loads((CAN / "cycles_summary.json").read_text(encoding="utf-8"))["cycles"]
    c4 = json.loads((V / "telemetry_cycle4_after_release.json").read_text(encoding="utf-8"))
    cycles = cycles + [{k: v for k, v in c4.items() if k != "probes"}]

    labels = ["baseline\nv1 corpus", "stability\nv1 corpus",
              "model swap\nv1 corpus", "after release\nv2 corpus"]
    models = [c["model_requested"].replace("claude-", "") for c in cycles]
    ns = [c["n_probes"] for c in cycles]
    x = range(len(cycles))

    fig, ax = plt.subplots(figsize=(9, 4.8))
    for key, label, colour, marker in SERIES:
        ys = [c["rates"][key]["rate"] for c in cycles]
        ax.plot(x, ys, marker=marker, color=colour, label=label, linewidth=2, markersize=8)
        for xi, c in zip(x, cycles):
            r = c["rates"][key]
            ax.annotate(f"{r['numerator']}/{r['denominator']}", (xi, r["rate"]),
                        textcoords="offset points", xytext=(0, 8), ha="center",
                        fontsize=8, color=colour)
    ax.axvspan(1.5, 2.5, color="#f4d03f", alpha=0.18)
    ax.text(2, ax.get_ylim()[1] * 0.98, "generator swapped", ha="center", va="top",
            fontsize=8, style="italic", color="#7d6608")
    ax.axvline(2.5, color="#555", linestyle="--", linewidth=1)
    ax.text(3, ax.get_ylim()[1] * 0.98, "corpus release v1 -> v2", ha="center", va="top",
            fontsize=8, style="italic", color="#555")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{l}\n{m}\nn={n}" for l, m, n in zip(labels, models, ns)], fontsize=8)
    ax.set_ylabel("failure rate")
    ax.set_title("Canary monitor across a corpus release - cycles 1-4\n"
                 "INTERNAL ONLY - disclosure hold", fontsize=10)
    ax.set_ylim(bottom=-0.02)
    ax.grid(alpha=0.25, linestyle=":")
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    p = V / "cycles_1_to_4.png"
    fig.savefig(p, dpi=150)
    print(f"  wrote {p}")
    print(f"  denominators: {ns}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
