"""Claude Opus: figures for the BDD clear-day transfer report (aggregate JSON/CSV inputs only).

    python figures.py --eval A=a.json [B=b.json ...] --runs A=results.csv ... --outdir DIR
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"]  # reference categorical slots 1,2,3,7
MARKERS = ["o", "s", "^", "D"]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
NEVER = "#b9b8b2"  # neutral for "never produced"
CAPTION = "BDD100K legacy 2018 labels; HF-mirror images (publisher unverified); YOLO11s fine-tuned on clear-day."
CONDS = [("val:clear_day", "clear day"), ("val:cloudy_day", "cloudy day"), ("val:rainy_day", "rain (day)"),
         ("val:snowy_day", "snow (day)"), ("val:dawn_dusk", "dawn/dusk"), ("val:night", "night")]


def style(ax):
    ax.set_facecolor(SURF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def curves(runs, out):
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.4), facecolor=SURF)
    panels = [("train/box_loss", "train box loss"), ("train/cls_loss", "train cls loss"),
              ("metrics/mAP50-95(B)", "selection-split mAP50-95 (all 10 classes)")]
    for ax, (key, title) in zip(axes, panels):
        style(ax)
        ax.grid(axis="y", color=GRID, lw=0.8)
        for i, (label, path) in enumerate(runs):
            rows = list(csv.DictReader(open(path)))
            rows = [{k.strip(): v for k, v in r.items()} for r in rows]
            ax.plot([int(r["epoch"]) for r in rows], [float(r[key]) for r in rows], lw=2,
                    color=SERIES[i], label=label)
        ax.set_title(title, fontsize=9, color=INK, loc="left")
        ax.set_xlabel("epoch", fontsize=8, color=INK2)
    axes[0].legend(frameon=False, fontsize=8)
    fig.text(0.01, 0.01, CAPTION + " Selection split = held-out clear-day train images.", fontsize=7, color=INK2)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def transfer(evals, target, out):
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), facecolor=SURF, sharey=True)
    n = len(evals)
    for j, (label, ev) in enumerate(evals):
        tr = ev["transfer"].get(target, {})
        for k, (key, _) in enumerate(CONDS):
            if key not in tr:
                continue
            e = tr[key]
            y = k + (j - (n - 1) / 2) * 0.17
            r, rc = e["operating"]["recall"], e["recall_ci"]
            f, fc = e["operating"]["fppi"], e["fppi_ci"]
            kw = dict(color=SERIES[j], marker=MARKERS[j], ms=6, lw=0, label=label if k == 0 else None)
            axes[0].errorbar([r], [y], xerr=[[r - rc[0]], [rc[1] - r]], elinewidth=1.5, **kw)
            axes[0].plot([e["ceiling_recall"]], [y], marker="|", ms=9, color=SERIES[j], lw=0)
            axes[1].errorbar([f], [y], xerr=[[f - fc[0]], [fc[1] - f]], elinewidth=1.5, **kw)
            if e["oracle"]["fppi"] is not None:
                axes[1].plot([e["oracle"]["fppi"]], [y], marker=MARKERS[j], ms=6, mfc="none",
                             mec=SERIES[j], lw=0)
    for ax in axes:
        style(ax)
    axes[0].axvline(float(target), color=INK2, lw=1, ls="--")
    axes[0].set_yticks(range(len(CONDS)), [c for _, c in CONDS])
    axes[0].invert_yaxis()
    axes[0].set_title(f"pedestrian recall at source threshold t*(recall {target})  | = candidate ceiling",
                      fontsize=9, color=INK, loc="left")
    axes[1].set_title("false positives per image at t*  (hollow = per-condition oracle threshold)",
                      fontsize=9, color=INK, loc="left")
    axes[0].legend(frameon=False, fontsize=8, ncol=len(evals), loc="lower center", bbox_to_anchor=(0.5, -0.22))
    fig.text(0.01, 0.01, CAPTION + " Bars: 95% image-bootstrap CI (selection and test resampled).",
             fontsize=7, color=INK2)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def decomposition(label, ev, target, out):
    tr = ev["transfer"][target]
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8), facecolor=SURF,
                             gridspec_kw={"width_ratios": [1, 1.1]})
    ax = axes[0]
    style(ax)
    for k, (key, _) in enumerate(CONDS):
        e = tr[key]
        r, c = e["operating"]["recall"], e["ceiling_recall"]
        segs = [(r, SERIES[0], "detected at t*"), (c - r, SERIES[1], "removed by threshold"),
                (1 - c, NEVER, "never a candidate")]
        left = 0
        for w, col, name in segs:
            ax.barh(k, w, left=left, color=col, height=0.62, edgecolor=SURF, linewidth=2,
                    label=name if k == 0 else None)
            left += w
        ax.text(1.01, k, f"{r:.2f} / {c:.2f}", va="center", fontsize=7, color=INK2)
    ax.set_yticks(range(len(CONDS)), [c for _, c in CONDS])
    ax.invert_yaxis()
    ax.set_xlim(0, 1.12)
    ax.set_title(f"{label}: share of pedestrians (recall / ceiling), t* for recall {target}",
                 fontsize=9, color=INK, loc="left")
    ax.legend(frameon=False, fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.45, -0.08))
    ax = axes[1]
    style(ax)
    bins = list(tr["val:clear_day"]["by_height"].keys())
    for j, (key, name) in enumerate([("val:clear_day", "clear day"), ("val:night", "night")]):
        bh, ce = tr[key]["by_height"], ev["strata"][key]["ceiling_by_height"]
        xs = [i + (j - 0.5) * 0.36 for i in range(len(bins))]
        rec = [bh[b]["recall_at_t"] or 0 for b in bins]
        cei = [ce[b]["ceiling_recall"] or 0 for b in bins]
        col = SERIES[2 + j]  # aqua/violet: distinct from the left panel's segment colors
        ax.bar(xs, cei, width=0.34, color=col, alpha=0.35, edgecolor=SURF, linewidth=2)
        ax.bar(xs, rec, width=0.34, color=col, edgecolor=SURF, linewidth=2, label=f"{name} (light = ceiling)")
        for x, b in zip(xs, bins):
            ax.text(x, -0.07, f"n={bh[b]['gt']}", ha="center", fontsize=6, color=INK2)
    ax.grid(axis="x", visible=False)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_xticks(range(len(bins)), [b + " px" for b in bins])
    ax.set_ylim(-0.1, 1.0)
    ax.set_title("recall at t* and ceiling by GT box height", fontsize=9, color=INK, loc="left")
    ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.text(0.01, 0.01, CAPTION, fontsize=7, color=INK2)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", nargs="+", default=[])
    ap.add_argument("--runs", nargs="+", default=[])
    ap.add_argument("--primary", default=None)
    ap.add_argument("--target", default="0.9")
    ap.add_argument("--outdir", type=Path, required=True)
    a = ap.parse_args()
    a.outdir.mkdir(parents=True, exist_ok=True)
    evals = [(s.split("=", 1)[0], json.loads(Path(s.split("=", 1)[1]).read_text())) for s in a.eval]
    runs = [tuple(s.split("=", 1)) for s in a.runs]
    if runs:
        curves(runs, a.outdir / "bdd_transfer_training_curves.png")
    if evals:
        transfer(evals, a.target, a.outdir / "bdd_transfer_recall_fppi.png")
        label, ev = next(((l, e) for l, e in evals if l == a.primary), evals[0])
        decomposition(label, ev, a.target, a.outdir / "bdd_transfer_decomposition.png")


if __name__ == "__main__":
    main()
