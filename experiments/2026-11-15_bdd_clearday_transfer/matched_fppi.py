"""Claude Opus: amendment 3 (exploratory, post hoc) — arms compared at matched clear-day FPPI.

t*(L) = lowest observed selection-split score whose selection FPPI <= L (whole ties).
Matching reuses evaluate_transfer.match_chunk (unchanged ReferenceEvaluator).
Bootstrap image draws are shared across arms, so arm differences are paired.

    PYTHONPATH=src;<pylib> python matched_fppi.py --gt GT --arm A=a.npz --arm B=b.npz [...] --out-json OUT
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evaluate_transfer as ET  # noqa: E402
from threshold_transfer.metrics import held_out_loss_decomposition  # noqa: E402

LEVELS = json.loads((HERE / "amendment_3.json").read_text(encoding="utf-8"))["fppi_levels"]
KEYS = ["val:clear_day", "val:cloudy_day", "val:rainy_day", "val:snowy_day", "val:dawn_dusk", "val:night",
        "val2:night_clear"]


def select_fppi(p, level, w=None):
    """Lowest observed score s with weighted FP(score>=s)/images <= level; None if none."""
    w = np.ones(p.n) if w is None else w
    scores = np.concatenate([p.tp_all, p.fp_all])
    fpw = np.concatenate([np.zeros(len(p.tp_all)), w[p.fp_img]])
    alive = np.concatenate([w[p.tp_img] > 0, w[p.fp_img] > 0])  # observed in this resample
    scores, fpw = scores[alive], fpw[alive]
    order = np.argsort(-scores, kind="stable")
    s, cum = scores[order], np.cumsum(fpw[order])
    last = np.r_[s[1:] != s[:-1], True]  # end of each tie group
    ok = np.nonzero(last & (cum / w.sum() <= level))[0]
    return None if not len(ok) else float(s[ok[-1]])


def load(gt, path, min_h):
    z = np.load(path)
    names, offs = [str(n) for n in z["names"]], z["offsets"]
    bx, sc = z["boxes"], z["scores"]
    preds = {n: (bx[offs[i]:offs[i + 1]], sc[offs[i]:offs[i + 1]]) for i, n in enumerate(names)}
    assert set(names) == set(gt)
    recs = {}
    for k in range(0, len(names), 400):
        recs.update(ET.match_chunk(names[k:k + 400], gt, preds, min_h)[0])
    return recs


def members_of(gt):
    m = {s: [] for s in ["selection"] + KEYS}
    for n in sorted(gt):
        g = gt[n]
        if g["role"] == "selection":
            m["selection"].append(n)
        else:
            if "val:" + g["stratum"] in m:
                m["val:" + g["stratum"]].append(n)
            for s in g["secondary"]:
                if "val2:" + s in m:
                    m["val2:" + s].append(n)
    return m


def ci(v):
    v = [x for x in v if x is not None]
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] if v else None


def analyse(recs, members, boot_w):
    pops = {s: ET.Population([recs[n] for n in m]) for s, m in members.items()}
    sel, clear = pops["selection"], pops["val:clear_day"]
    out, reps = {}, {}
    for L in LEVELS:
        t = select_fppi(sel, L)
        tb = [select_fppi(sel, L, w) for w in boot_w["selection"]]
        lev = {"threshold": t, "threshold_ci": ci(tb), "selection": sel.point(t), "conditions": {}}
        rep = {}
        for s in KEYS:
            p = pops[s]
            op, ceil = p.point(t), p.point(None)
            ot = select_fppi(p, L)
            vals = []
            for b, tbb in enumerate(tb):
                w, wc = boot_w[s][b], boot_w["val:clear_day"][b]
                o, c = p.point(tbb, w), p.point(None, w)
                co, cc = clear.point(tbb, wc), clear.point(None, wc)
                vals.append((o["recall"], o["fppi"], c["recall"], co["recall"] - o["recall"],
                             cc["recall"] - c["recall"], (c["recall"] - o["recall"]) - (cc["recall"] - co["recall"])))
            col = list(zip(*vals))
            d = held_out_loss_decomposition(clear.point(t)["recall"], op["recall"],
                                            clear.point(None)["recall"], ceil["recall"])
            lev["conditions"][s] = {
                "recall": op["recall"], "recall_ci": ci(col[0]), "fppi": op["fppi"], "fppi_ci": ci(col[1]),
                "precision": op["precision"], "ceiling": ceil["recall"], "ceiling_ci": ci(col[2]),
                "loss": d["held_out_loss"]["value"], "loss_ci": ci(col[3]),
                "ceiling_part": d["ceiling_difference"]["value"], "ceiling_part_ci": ci(col[4]),
                "threshold_part": d["threshold_miss_difference"]["value"], "threshold_part_ci": ci(col[5]),
                "oracle_same_fppi": {"threshold": ot, "recall": p.point(ot)["recall"] if ot is not None else None},
                "by_height": p.by_height(t)}
            rep[s] = {"recall": col[0], "loss": col[3], "ceiling_part": col[4], "threshold_part": col[5]}
        out[str(L)] = lev
        reps[str(L)] = rep
    return out, reps, {s: {"images": p.n, "pedestrians": int(p.G.sum())} for s, p in pops.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--arm", action="append", required=True)
    ap.add_argument("--min-height", type=float, default=0.0)
    ap.add_argument("--replicates", type=int, default=ET.CONFIG["evaluation"]["bootstrap"]["replicates"])
    ap.add_argument("--out-json", type=Path, required=True)
    a = ap.parse_args()
    gt = json.loads(a.gt.read_text())
    members = members_of(gt)
    rng = np.random.default_rng(ET.CONFIG["evaluation"]["bootstrap"]["seed"])
    boot_w = {s: [np.bincount(rng.integers(0, len(m), len(m)), minlength=len(m)).astype(float)
                  for _ in range(a.replicates)] for s, m in members.items()}  # shared across arms -> paired
    result = {"amendment": "amendment_3 (exploratory, post hoc)", "fppi_levels": LEVELS,
              "population": "all pedestrians" if not a.min_height else
              f"pedestrian GT height >= {a.min_height:g} px; shorter GT ignore regions",
              "labels_note": "BDD100K legacy 2018 labels; HF-mirror images (publisher unverified)",
              "arms": {}, "paired_differences": {}}
    reps = {}
    for spec in a.arm:
        label, path = spec.split("=", 1)
        res, reps[label], counts = analyse(load(gt, Path(path), a.min_height), members, boot_w)
        result["arms"][label] = res
        result["counts"] = counts
    labels = list(result["arms"])
    for i, la in enumerate(labels):
        for lb in labels[i + 1:]:
            pair = {}
            for L in map(str, LEVELS):
                pair[L] = {}
                for s in ("val:night", "val:clear_day"):
                    e = {}
                    for m in ("recall", "loss", "ceiling_part", "threshold_part"):
                        xa, xb = reps[la][L][s][m], reps[lb][L][s][m]
                        pa = result["arms"][la][L]["conditions"][s][m]
                        pb = result["arms"][lb][L]["conditions"][s][m]
                        e[m] = {"value": pb - pa, "ci": ci([q - p for p, q in zip(xa, xb)])}
                    pair[L][s] = e
            result["paired_differences"][f"{lb} minus {la}"] = pair
    a.out_json.write_text(json.dumps(result, indent=1))
    for label in labels:
        for L in map(str, LEVELS):
            r = result["arms"][label][L]
            n, c = r["conditions"]["val:night"], r["conditions"]["val:clear_day"]
            print(f"{label:6s} L={L:4s} t*={r['threshold']} clearR={c['recall']:.3f} nightR={n['recall']:.3f} "
                  f"ceilPart={n['ceiling_part']:+.3f} thrPart={n['threshold_part']:+.3f} nightFPPI={n['fppi']:.2f}")


if __name__ == "__main__":
    main()
