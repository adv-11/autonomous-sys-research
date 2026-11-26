"""Claude Opus 5.5: figures for the 2026-11-23 threshold-transfer synthesis.

Reads only committed, counts-only aggregates under docs/research/ and writes PNGs
to docs/research/2026-11-23_threshold_transfer_synthesis/. No predictions,
boxes or image identifiers are read; nothing is recomputed beyond selecting
and plotting stored values (absolute shares 1 - M are simple complements of
stored ceilings, per the PR #13 erratum).

Run with any interpreter that has Matplotlib and NumPy, e.g. the existing
report-only venv used by the NightOwls figure script (tmp/pdfs/venv):

    tmp/pdfs/venv/Scripts/python.exe -I scripts/reports/threshold_transfer_synthesis_figures.py
"""
from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "docs" / "research"
BDD = R / "2026-11-15_bdd_clearday_transfer"
REM = R / "2026-11-17_threshold_remedies"
NOW = R / "2026-11-23_nightowls_evaluation"
OUT = R / "2026-11-23_threshold_transfer_synthesis"

COL = {"A": "#2563a6", "C": "#6fa8dc", "B": "#c05b23", "B2": "#e69a5e"}
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
    "axes.spines.right": False, "savefig.dpi": 200, "axes.titleweight": "bold",
    "axes.titlesize": 10,
})


def jload(p: Path):
    if p.suffix == ".gz":
        return json.loads(gzip.decompress(p.read_bytes()))
    return json.loads(p.read_text(encoding="utf-8"))


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", (OUT / f"{name}.png").relative_to(ROOT))


def nightowls_rows():
    rows = {}
    with open(NOW / "recordings_primary.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["source_policy"] == "h50_r0.8" and r["profile"] == "unused_nonpedestrian" \
                    and r["setup"] == "reasonable":
                rows[(r["arm"], r["group"])] = r
    with open(NOW / "source_policies.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["source_policy"] == "h50_r0.8" and r["profile"] == "unused_nonpedestrian" \
                    and r["setup"] == "reasonable" and r["group"] == "pooled":
                rows[(r["arm"], "pooled_ci")] = r
    return rows


# ---------------------------------------------------------------- figure 1
def fig_summary():
    conds = [("val:clear_day", "clear day"), ("val:cloudy_day", "cloudy"),
             ("val:rainy_day", "rain"), ("val:snowy_day", "snow"),
             ("val:dawn_dusk", "dawn/dusk"), ("val:night", "night")]
    runs = {"B": jload(BDD / "B_1280.json"), "B2": jload(REM / "B2_1280.json")}
    acdc = jload(REM / "acdc_panel.json")
    now = nightowls_rows()
    agg = jload(NOW / "aggregate.json.gz")

    fig, axs = plt.subplots(1, 3, figsize=(13.5, 4.2),
                            gridspec_kw={"width_ratios": [1.15, 1.25, 1.2]})
    # (a) BDD all-height, preregistered t*(0.80), 1280 px runs
    ax = axs[0]
    for j, (arm, d) in enumerate(runs.items()):
        tr = d["transfer"]["0.8"]
        xs, ys, lo, hi = [], [], [], []
        for i, (k, _) in enumerate(conds):
            s = tr[k]
            xs.append(i + (j - 0.5) * 0.3)
            ys.append(s["operating"]["recall"])
            lo.append(s["operating"]["recall"] - s["recall_ci"][0])
            hi.append(s["recall_ci"][1] - s["operating"]["recall"])
        ax.errorbar(xs, ys, yerr=[lo, hi], fmt="o", color=COL[arm], capsize=2,
                    label=f"{arm} ({'seed 0' if arm == 'B' else 'seed 1'}, 1280 px)")
    ax.axhline(0.8, color="0.5", lw=0.8, ls="--")
    ax.set_xticks(range(len(conds)), [c[1] for c in conds], rotation=30)
    ax.set_ylim(0.4, 0.9)
    ax.set_ylabel("pedestrian recall at transferred threshold")
    ax.set_title("(a) BDD val, all heights, t*(0.80)")
    ax.legend(frameon=False, loc="lower left", fontsize=8)

    # (b) ACDC, same thresholds, descriptive (no intervals)
    ax = axs[1]
    strata = ["fog", "night", "rain", "snow"]
    for j, arm in enumerate(["B", "B2"]):
        key = f"{arm}_1280:target0.8"
        for i, s in enumerate(strata):
            adv = acdc["arms"][arm]["strata"][f"{s}_adverse"]["at"][key]["recall"]
            ref = acdc["arms"][arm]["strata"][f"{s}_reference"]["at"][key]["recall"]
            x = i + (j - 0.5) * 0.3
            ax.plot([x, x], [ref, adv], color=COL[arm], lw=1, alpha=0.6)
            ax.scatter([x], [adv], color=COL[arm], marker="o", zorder=3,
                       label=f"{arm} adverse" if i == 0 else None)
            ax.scatter([x], [ref], facecolor="white", edgecolor=COL[arm], marker="s",
                       zorder=3, label=f"{arm} normal reference" if i == 0 else None)
    ax.axhline(0.8, color="0.5", lw=0.8, ls="--")
    ax.set_xticks(range(4), strata)
    ax.set_ylim(0.4, 0.9)
    ax.set_ylabel("pedestrian recall at BDD t*(0.80)")
    ax.set_title("(b) ACDC at BDD t*(0.80), descriptive")
    ax.legend(frameon=False, fontsize=7.5, ncol=2, loc="lower left")
    ax.text(0.99, 0.98, "no intervals: 4–6 recordings per condition",
            transform=ax.transAxes, ha="right", va="top", fontsize=7, color="0.35")

    # (c) >=50 px policy: BDD clear/night references vs NightOwls pooled / R3-out
    ax = axs[2]
    cats = ["BDD clear\n(≥50 px)", "BDD night\n(≥50 px)", "NightOwls\npooled", "NightOwls\nR3 out"]
    for j, (arm, lab) in enumerate([("A_640", "A"), ("B_1280", "B"), ("C_640", "C")]):
        b = agg["arms"][arm]["bdd_h50"]
        ys = [b["clear"]["policies"]["h50_r0.8"]["operating"]["recall"],
              b["night"]["policies"]["h50_r0.8"]["operating"]["recall"],
              float(now[(arm, "pooled")]["recall"]),
              float(now[(arm, "dominant_out")]["recall"])]
        xs = [i + (j - 1) * 0.22 for i in range(4)]
        ax.scatter(xs, ys, color=COL[lab], zorder=3, label=f"{lab} ({arm.split('_')[1]} px)")
        ci = now[(arm, "pooled_ci")]
        lo, hi = float(ci["cluster_conditional_unkeyed_recall_low"]), \
            float(ci["cluster_conditional_unkeyed_recall_high"])
        ax.plot([xs[2], xs[2]], [lo, hi], color=COL[lab], lw=1.2)
    ax.axhline(0.8, color="0.5", lw=0.8, ls="--")
    ax.set_xticks(range(4), cats)
    ax.set_ylim(0.3, 0.9)
    ax.set_title("(c) ≥50 px policy t*(0.80): BDD vs NightOwls")
    ax.legend(frameon=False, fontsize=7.5, loc="lower left")
    ax.text(0.99, 0.98, "NightOwls bars: five-key recording bootstrap\n(descriptive, lumpy)",
            transform=ax.transAxes, ha="right", va="top", fontsize=7, color="0.35")
    fig.suptitle("Recall at the clear-day-selected threshold, transferred unchanged (YOLO11s)",
                 fontsize=11, y=1.02)
    fig.tight_layout()
    save(fig, "fig1_transfer_summary")


# ---------------------------------------------------------------- figure 2
def fig_remedies():
    rem = {a: jload(REM / f"remedies_trainnight_{a}.json")["arms"][a] for a in ["A", "B", "C", "B2"]}
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.3))
    # (a) B at the preregistered t*(0.80): night test curve vs clear-day curve
    ax = axs[0]
    c = rem["B"]["cal_trainnight_test_valnight"]["target0.8"]
    nc = c["night_test_curve"]
    cc = c["clear_curve"]
    ax.plot([p[0] for p in cc], [p[1] for p in cc], color="0.45", lw=1.4, label="BDD val clear day")
    ax.plot([p[0] for p in nc], [p[1] for p in nc], color="#1f2f5c", lw=1.4, label="BDD val night")
    marks = [("transfer", "transferred t*", "o"), ("equal_fppi", "equal-FPPI", "s"),
             ("equal_recall", "equal-recall", "^"), ("platt_per_condition", "Platt per condition", "D")]
    for key, lab, m in marks:
        r = c["remedies"][key]
        ax.scatter(r["fppi"], r["recall"], marker=m, s=46, zorder=4, label=lab,
                   edgecolor="black", linewidth=0.6)
    ax.axhline(c["night_ceiling"], color="#1f2f5c", lw=0.8, ls=":")
    ax.text(28, c["night_ceiling"] + 0.008, "night candidate ceiling", fontsize=7, color="#1f2f5c",
            ha="right")
    ax.set_xlim(0, 30)
    ax.set_ylim(0.4, 0.95)
    ax.set_xlabel("false positives per image (test)")
    ax.set_ylabel("pedestrian recall")
    ax.set_title("(a) Arm B, preregistered t*(0.80)")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")

    # (b) recall gain vs FPPI cost, all arms and operating points
    ax = axs[1]
    ops = [("target0.8", "t*(0.80)"), ("L1.0", "FPPI 1"), ("L4.5", "FPPI 4.5")]
    rmk = {"equal_fppi": "s", "equal_recall": "^", "platt_per_condition": "D"}
    for arm in ["A", "C", "B", "B2"]:
        for op, _ in ops:
            if op not in rem[arm]["cal_trainnight_test_valnight"]:
                continue
            if op == "target0.8" and arm in ("A", "C"):
                continue  # infeasible at 640 px
            c = rem[arm]["cal_trainnight_test_valnight"][op]
            for key, m in rmk.items():
                r = c["remedies"][key]
                ax.scatter(r["delta_fppi"], r["delta_recall"], marker=m, color=COL[arm], s=34,
                           edgecolor="black", linewidth=0.4, zorder=3)
    for arm in ["A", "C", "B", "B2"]:
        ax.scatter([], [], color=COL[arm], label=arm)
    for key, m in rmk.items():
        ax.scatter([], [], marker=m, color="white", edgecolor="black", label=key.replace("_", " "))
    ax.axhline(0, color="0.6", lw=0.7)
    ax.set_xscale("symlog", linthresh=1)
    ax.set_xlim(-0.5, 30)
    ax.set_xlabel("Δ night FPPI vs transferred threshold (symlog)")
    ax.set_ylabel("Δ night recall (test)")
    ax.set_title("(b) Remedy gain vs false-positive cost")
    ax.legend(frameon=False, fontsize=7.5, ncol=2, loc="upper left")
    ax.text(0.99, 0.02, "operating points: t*(0.80) [B, B2], clear-day FPPI 1 and 4.5 [all]",
            transform=ax.transAxes, ha="right", fontsize=7, color="0.35")
    fig.suptitle("Night threshold remedies move along the night curve (exploratory, amendment 4)",
                 fontsize=11, y=1.02)
    fig.tight_layout()
    save(fig, "fig2_remedy_tradeoff")


# ---------------------------------------------------------------- figure 3
def fig_decomposition():
    rem = {a: jload(REM / f"remedies_trainnight_{a}.json")["arms"][a] for a in ["A", "B", "C", "B2"]}
    now = nightowls_rows()
    agg = jload(NOW / "aggregate.json.gz")
    rows = []  # label, recall, removable, unmatched, ceiling_diff
    for arm, op, lab in [("A", "L1.0", "A, BDD night, FPPI 1"), ("C", "L1.0", "C, BDD night, FPPI 1"),
                         ("B", "L1.0", "B, BDD night, FPPI 1"), ("B2", "L1.0", "B2, BDD night, FPPI 1"),
                         ("B", "target0.8", "B, BDD night, t*(0.80)"),
                         ("B2", "target0.8", "B2, BDD night, t*(0.80)")]:
        c = rem[arm]["cal_trainnight_test_valnight"][op]
        rec = c["remedies"]["transfer"]["recall"]
        mn = c["night_ceiling"]
        rows.append((lab, rec, mn - rec, 1 - mn, c["clear_ceiling"] - mn))
    for arm, lab in [("A_640", "A"), ("B_1280", "B"), ("C_640", "C")]:
        r = now[(arm, "pooled")]
        gt = float(r["eligible_gt"])
        rec = float(r["recall"])
        mn = float(r["ceiling_recall"])
        m_clear = agg["arms"][arm]["bdd_h50"]["clear"]["ceiling"]["recall"]
        rows.append((f"{lab}, NightOwls ≥50 px, t*(0.80)", rec, mn - rec, 1 - mn, m_clear - mn))
        assert abs((1 - mn) * gt - float(r["no_matched_candidate"])) < 0.5
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    y = list(range(len(rows)))[::-1]
    for yi, (lab, rec, remv, unm, cd) in zip(y, rows):
        ax.barh(yi, rec, color="#3b7d4f")
        ax.barh(yi, remv, left=rec, color="#e3b448")
        # red segment = 1 - M_night, split into the clear-day-level share (1 - M_clear, solid)
        # and the excess over clear day (M_clear - M_night = ceiling difference, hatched)
        ax.barh(yi, unm - cd, left=rec + remv, color="#9a3b3b")
        ax.barh(yi, cd, left=1 - cd, color="#d9a0a0", hatch="///", edgecolor="#9a3b3b", lw=0)
    ax.set_yticks(y, [r[0] for r in rows], fontsize=8)
    ax.set_xlim(0, 1)
    ax.set_xlabel("share of eligible night pedestrians")
    handles = [Patch(color="#3b7d4f", label="detected at transferred threshold"),
               Patch(color="#e3b448", label="matched candidate removed by threshold (M − R)"),
               Patch(color="#9a3b3b", label="no matched candidate, clear-day level (1 − M_clear)"),
               Patch(facecolor="#d9a0a0", hatch="///", edgecolor="#9a3b3b",
                     label="no matched candidate, excess over clear day (M_clear − M_night)")]
    ax.legend(handles=handles, frameon=False, fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2)
    ax.set_title("Absolute night miss composition (IoU ≥ 0.5, score ≥ 1e-4)\n"
                 "BDD rows: all heights vs BDD clear day; NightOwls rows: vs BDD ≥50 px clear day")
    fig.tight_layout()
    save(fig, "fig3_miss_composition")


# ---------------------------------------------------------------- figure 4
def fig_seed_resolution():
    m = jload(REM / "matched_ABCB2_all.json")["paired_differences"]
    pairs = [("B minus A", "B − A (resolution, seed 0)"), ("B2 minus C", "B2 − C (resolution, seed 1)"),
             ("C minus A", "C − A (seed, 640 px)"), ("B2 minus B", "B2 − B (seed, 1280 px)")]
    metrics = [("recall", "night recall"), ("loss", "night loss vs clear day"),
               ("ceiling_part", "ceiling-difference part"), ("threshold_part", "threshold part T")]
    pcol = ["#c05b23", "#e69a5e", "#2563a6", "#6fa8dc"]
    fig, axs = plt.subplots(1, 4, figsize=(13, 3.4), sharey=True)
    for ax, (mk, mlab) in zip(axs, metrics):
        for i, ((pk, plab), c) in enumerate(zip(pairs, pcol)):
            v = m[pk]["1.0"]["val:night"][mk]
            yi = len(pairs) - 1 - i
            ax.errorbar(v["value"], yi, xerr=[[v["value"] - v["ci"][0]], [v["ci"][1] - v["value"]]],
                        fmt="o", color=c, capsize=2)
        ax.axvline(0, color="0.5", lw=0.8)
        ax.set_title(mlab)
        ax.set_xlabel("paired difference")
    axs[0].set_yticks(range(len(pairs)), [p[1] for p in pairs][::-1])
    fig.suptitle("Paired night differences at matched clear-day FPPI 1 (image bootstrap, conditional "
                 "on trained weights)", fontsize=10.5, y=1.04)
    fig.tight_layout()
    save(fig, "fig4_seed_resolution")


if __name__ == "__main__":
    fig_summary()
    fig_remedies()
    fig_decomposition()
    fig_seed_resolution()
