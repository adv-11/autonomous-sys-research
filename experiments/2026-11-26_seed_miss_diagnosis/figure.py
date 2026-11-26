"""GPT Sol: plot measured aggregate counts only; no private input required."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/research/2026-11-26_seed_miss_diagnosis"
data = json.loads((OUT / "counts.json").read_text())
colors = ["#327d88", "#d9a64b", "#bd7656", "#454757"]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "svg.hashsalt": "seed-miss-diagnosis-20261126"})
fig, axes = plt.subplots(3, 1, figsize=(10.6, 7.1), sharex=True)
panels = [("source_FPPI_1", "A  Frozen source FPPI 1 policies (primary exploratory comparison)"),
          ("source_recall_080_sensitivity", "B  Source recall 0.80 sensitivity (unequal test FPPI)"),
          ("ceiling", "C  Candidate ceiling (greedy matched at score floor 0.0001)")]
for ax, (policy, title) in zip(axes, panels):
    for y, condition in enumerate(("clear_day", "night")):
        r = data["source_FPPI_1" if policy == "ceiling" else policy][condition]
        n = r["gt"]
        if policy == "ceiling":
            absent = r["both_ceiling_absent"]
            vals = [n - r["B_ceiling_absent"] - r["B2_ceiling_absent"] + absent,
                    r["B2_ceiling_absent"] - absent, r["B_ceiling_absent"] - absent, absent]
        else:
            vals = [r["both_detected"], r["B_only_detected"], r["B2_only_detected"],
                    r["neither_detected_stable_misses"]]
        assert sum(vals) == n
        left = 0
        for value, color in zip(vals, colors):
            width = 100 * value / n
            ax.barh(y, width, left=left, height=.55, color=color, edgecolor="white", linewidth=.8)
            ax.text(left + width / 2, y, str(value), ha="center", va="center",
                    color="white" if color in (colors[0], colors[3]) else "#20232c", fontsize=10)
            left += width
    ax.set_yticks([0, 1], ["Clear day\nGT = 2,450", "Night\nGT = 2,843"])
    ax.invert_yaxis()
    ax.set_title(title, loc="left", fontsize=11, pad=12)
    ax.set_xlim(0, 100)
    ax.tick_params(axis="both", length=0)
    ax.set_axisbelow(True)
    ax.grid(axis="x", alpha=.15)
    for spine in ax.spines.values():
        spine.set_visible(False)
axes[-1].set_xlabel("Share of eligible GT (%)   |   Segment labels are measured GT counts", labelpad=9)
fig.suptitle("Two 1280 px seeds: shared misses and changed GT detection status", x=.02, ha="left", fontsize=14, y=.99)
fig.legend(handles=[Patch(color=c, label=l) for c, l in zip(colors,
           ["Both runs", "B only", "B2 only", "Neither run"])],
           loc="upper center", bbox_to_anchor=(.56, .946), ncol=4, frameon=False)
fig.text(.02, .025, "A/B: detected at each run's frozen threshold. C: matched in the candidate ceiling.\n"
         "BDD legacy 2018 GT; native YOLO11s candidates; IoU >= 0.50. GPT Sol analysis of Claude Opus's saved runs.",
         fontsize=9, color="#494b55")
fig.subplots_adjust(left=.13, right=.985, top=.86, bottom=.145, hspace=.66)
fig.savefig(OUT / "seed_miss_overlap.png", dpi=180, facecolor="white")
plt.close(fig)
