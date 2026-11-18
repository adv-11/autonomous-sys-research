"""Claude Opus: amendment 4 figure — night remedies as points on the night operating curve.

    python remedy_figures.py --arm A=remedies_trainnight_A.json [...] --out PNG
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SERIES = {"transfer": ("#52514e", "o", "transferred clear-day t*"),
          "equal_fppi": ("#2a78d6", "s", "night threshold, equal FPPI"),
          "equal_recall": ("#eb6834", "^", "night threshold, equal recall"),
          "platt_per_condition": ("#1baf7a", "D", "per-condition Platt")}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    panels = []
    for spec in a.arm:
        label, path = spec.split("=", 1)
        res = json.loads(Path(path).read_text())["arms"][label]["cal_trainnight_test_valnight"]
        for op in (["target0.8"] if "target0.8" in res else []) + ["L1.0"]:
            panels.append((label, op, res[op]))
    fig, axes = plt.subplots(1, len(panels), figsize=(3.6 * len(panels), 3.8), facecolor=SURF, sharey=True)
    for ax, (label, op, r) in zip(axes, panels):
        ax.set_facecolor(SURF)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.grid(color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        nc, cc = zip(*sorted(r["night_test_curve"])), zip(*sorted(r["clear_curve"]))
        ax.plot(*cc, color=INK2, lw=1.2, ls="--", label="clear day (val)")
        ax.plot(*nc, color=INK, lw=1.6, label="night (val)")
        ax.axhline(r["night_ceiling"], color=INK2, lw=1, ls=":")
        ax.text(0.12, r["night_ceiling"] + 0.008, "night ceiling: no matched candidate above", fontsize=6.5, color=INK2)
        for m, (col, mk, name) in SERIES.items():
            v = r["remedies"].get(m)
            if v:
                ax.plot([v["fppi"]], [v["recall"]], marker=mk, ms=7, color=col, lw=0, label=name,
                        markeredgecolor=SURF, markeredgewidth=1)
        ax.set_xscale("log")
        ax.set_xlim(0.1, 40)
        ax.set_ylim(0.3, 0.95)
        ax.set_xlabel("false positives per image", fontsize=8, color=INK2)
        title = f"{label}: " + ("preregistered t*(0.80)" if op.startswith("target") else "clear-day FPPI 1")
        ax.set_title(title, fontsize=9, color=INK, loc="left")
        ax.tick_params(colors=INK2, labelsize=8)
    axes[0].set_ylabel("pedestrian recall", fontsize=8, color=INK2)
    axes[0].legend(frameon=False, fontsize=6.5, loc="lower right")
    fig.text(0.01, 0.01, "BDD100K legacy 2018 labels; HF-mirror images (publisher unverified). Night thresholds chosen on "
             "2,000 BDD train-night images, tested on val night. Exploratory (amendment 4).", fontsize=7, color=INK2)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(a.out, dpi=150)


if __name__ == "__main__":
    main()
