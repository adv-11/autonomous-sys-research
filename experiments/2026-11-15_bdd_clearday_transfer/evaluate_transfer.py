"""Claude Opus, Stage 3 (local CPU): threshold transfer from clear-day selection to BDD val strata.

Matching uses threshold_transfer.metrics.ReferenceEvaluator unchanged (IoU>=0.5,
greedy score order), run per image chunk: its labels are image-local, so chunked
rows equal a whole-population run. A whole-population ReferenceEvaluator check on
the selection split and val clear_day verifies the fast aggregate path.
Native zero-area boxes follow docs/decisions/2026-11-10_native_zero_area.md:
explicit FP rows, counted separately, never repaired.

    PYTHONPATH=src;<pylib> python evaluate_transfer.py --preds P.npz --gt gt_pedestrian.json --label NAME --out-json A.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402
from threshold_transfer.metrics import (ReferenceEvaluator, held_out_loss_decomposition,  # noqa: E402
                                        target_gap_decomposition)

CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
TARGETS = CONFIG["evaluation"]["recall_targets"]  # overridable by --targets (amendment_2)
STRATA = ["selection"] + [f"val:{s}" for s in CONFIG["primary_strata"]] + \
         [f"val2:{s}" for s in CONFIG["secondary_strata"]] + ["val:all"]
BINS = [C.height_bin(lo) for lo, _ in C.HEIGHT_BINS]


def match_chunk(names, gt, preds, min_h=0.0):
    """Run the reference evaluator on a chunk; return per-image matched-GT scores and FP scores.

    min_h>0 (amendment_2 h32 population): pedestrian GT shorter than min_h become ignore
    regions (same_category_ioa); candidates absorbed by them are neither TP nor FP.
    """
    images = [{"image_id": n, "width": C.WIDTH, "height": C.HEIGHT} for n in names]
    anns, cands, zero = [], [], {}
    for n in names:
        for k, (x1, y1, x2, y2) in enumerate(gt[n]["peds"]):
            anns.append({"annotation_id": f"{n}#g{k}", "image_id": n, "category": "pedestrian",
                         "bbox": [x1, y1, x2 - x1, y2 - y1], "ignore": (y2 - y1) < min_h, "iscrowd": False})
        boxes, scores = preds[n]
        for k in range(len(scores)):
            x1, y1, x2, y2 = (float(v) for v in boxes[k])
            if not (x2 >= x1 and y2 >= y1):
                raise ValueError("reversed native box")
            if x2 == x1 or y2 == y1:
                zero.setdefault(n, []).append(float(scores[k]))
                continue
            cands.append({"candidate_id": f"{n}#p{k:05d}", "image_id": n, "category": "pedestrian",
                          "bbox": [x1, y1, x2 - x1, y2 - y1], "score": float(scores[k])})
    ev = ReferenceEvaluator({"schema_version": "threshold-transfer-v1", "images": images,
                             "annotations": anns, "provenance": {}},
                            {"schema_version": "threshold-transfer-v1", "predictions": cands,
                             "provenance": {"evaluated_image_ids": names}},
                            categories=["pedestrian"],
                            ignore_policy="same_category_ioa" if min_h > 0 else "reject")
    elig = {n: [k for k, p in enumerate(gt[n]["peds"]) if p[3] - p[1] >= min_h] for n in names}
    out = {n: {"tp": [], "fp": list(zero.get(n, [])), "zero": len(zero.get(n, [])), "ignored": 0,
               "gt_h": [gt[n]["peds"][k][3] - gt[n]["peds"][k][1] for k in elig[n]],
               "gt_match": [None] * len(elig[n])} for n in names}
    pos = {n: {k: i for i, k in enumerate(elig[n])} for n in names}
    for r in ev.rows:
        o = out[r["image_id"]]
        if r["outcome"] == "TP":
            o["tp"].append(r["score"])
            o["gt_match"][pos[r["image_id"]][int(r["annotation_id"].split("#g")[1])]] = r["score"]
        elif r["outcome"] == "IGNORED":
            o["ignored"] += 1
        else:
            o["fp"].append(r["score"])
    return out, ev


class Population:
    """Per-image arrays for fast exact operating points and image bootstrap."""

    def __init__(self, recs):
        self.n = len(recs)
        self.G = np.array([len(r["gt_h"]) for r in recs])
        self.tp_scores = [np.array(r["tp"], dtype=float) for r in recs]
        self.fp_all = np.concatenate([np.array(r["fp"], dtype=float) for r in recs] + [np.zeros(0)])
        self.fp_img = np.repeat(np.arange(self.n), [len(r["fp"]) for r in recs])
        self.tp_all = np.concatenate(self.tp_scores + [np.zeros(0)])
        self.tp_img = np.repeat(np.arange(self.n), [len(t) for t in self.tp_scores])
        self.zero = np.array([r["zero"] for r in recs])
        self.gt_h = np.concatenate([np.array(r["gt_h"], dtype=float) for r in recs] + [np.zeros(0)])
        self.gt_m = np.concatenate([np.array([np.nan if m is None else m for m in r["gt_match"]], dtype=float)
                                    for r in recs] + [np.zeros(0)])
        self.gt_img = np.repeat(np.arange(self.n), self.G)

    def point(self, t, w=None):
        """Counts at inclusive threshold t (None = ceiling) under image weights w."""
        w = np.ones(self.n) if w is None else w
        keep_tp = np.ones(len(self.tp_all), bool) if t is None else self.tp_all >= t
        keep_fp = np.ones(len(self.fp_all), bool) if t is None else self.fp_all >= t
        tp = float(w[self.tp_img[keep_tp]].sum())
        fp = float(w[self.fp_img[keep_fp]].sum())
        g, n = float((w * self.G).sum()), float(w.sum())
        return {"tp": tp, "fp": fp, "gt": g, "images": n, "recall": tp / g if g else None,
                "fppi": fp / n, "precision": tp / (tp + fp) if tp + fp else None}

    def select(self, target, w=None):
        """Evaluator rule: highest observed boundary with recall>=target = k-th TP score."""
        w = np.ones(self.n) if w is None else w
        g = float((w * self.G).sum())
        order = np.argsort(-self.tp_all, kind="stable")
        cum = np.cumsum(w[self.tp_img[order]])
        ok = np.nonzero(cum / g >= target)[0]
        return None if not len(ok) else float(self.tp_all[order[ok[0]]])

    def by_height(self, t):
        res = {}
        for (lo, hi), name in zip(C.HEIGHT_BINS, BINS):
            m = (self.gt_h >= lo) & ((self.gt_h < hi) if hi is not None else True)
            g = int(m.sum())
            ceil = int((m & ~np.isnan(self.gt_m)).sum())
            op = None if t is None else int((m & (self.gt_m >= t)).sum())
            res[name] = {"gt": g, "ceiling_recall": ceil / g if g else None,
                         "recall_at_t": (op / g if g else None) if op is not None else None}
        return res


def ci(values):
    v = np.array([x for x in values if x is not None and not (isinstance(x, float) and math.isnan(x))])
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] if len(v) else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--preds", type=Path, required=True)
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--replicates", type=int, default=CONFIG["evaluation"]["bootstrap"]["replicates"])
    ap.add_argument("--skip-full-check", action="store_true")
    ap.add_argument("--targets", type=float, nargs="+", default=None)
    ap.add_argument("--min-height", type=float, default=0.0)
    args = ap.parse_args(argv)
    global TARGETS
    if args.targets:
        TARGETS = args.targets
    gt = json.loads(args.gt.read_text())
    z = np.load(args.preds)
    names, offs = [str(n) for n in z["names"]], z["offsets"]
    all_boxes, all_scores = z["boxes"], z["scores"]  # decode once; npz members are lazy
    preds = {n: (all_boxes[offs[i]:offs[i + 1]], all_scores[offs[i]:offs[i + 1]]) for i, n in enumerate(names)}
    assert set(names) == set(gt), "prediction coverage must equal the frozen selection+val population"
    totals = dict(zip(names, z["all_class_candidates"].tolist()))

    recs = {}
    for start in range(0, len(names), 400):
        chunk = names[start:start + 400]
        out, _ = match_chunk(chunk, gt, preds, args.min_height)
        recs.update(out)
    members = {s: [] for s in STRATA}
    for n in names:
        g = gt[n]
        if g["role"] == "selection":
            members["selection"].append(n)
        else:
            members["val:" + g["stratum"]].append(n)
            members["val:all"].append(n)
            for s in g["secondary"]:
                members["val2:" + s].append(n)
    pops = {s: Population([recs[n] for n in m]) for s, m in members.items() if m}

    result = {"label": args.label, "population": "all pedestrians" if not args.min_height else
              f"pedestrian GT height >= {args.min_height:g} px; shorter GT ignore regions", "targets": TARGETS, "labels_note": "BDD100K legacy 2018 labels; HF mirror images (unverified publisher)",
              "preds_sha256": hashlib.sha256(args.preds.read_bytes()).hexdigest(), "strata": {}, "selection": {}, "transfer": {}, "checks": {}}
    sel = pops["selection"]
    for s, p in pops.items():
        result["strata"][s] = {"images": p.n, "pedestrians": int(p.G.sum()),
                               "ceiling": p.point(None), "ceiling_by_height": p.by_height(None),
                               "zero_area_candidates": int(p.zero.sum()),
                               "ignored_candidates": int(sum(recs[n]["ignored"] for n in members[s])),
                               "cap_hits": int(sum(totals[n] >= CONFIG["inference"]["max_det_cap"] for n in members[s])),
                               "mean_ped_candidates_per_image": (len(p.tp_all) + len(p.fp_all)) / p.n}

    # Whole-population reference check (exact equality with fast path)
    if not args.skip_full_check:
        for s in ("selection", "val:clear_day"):
            _, ev = match_chunk(members[s], gt, preds, args.min_height)
            for target in TARGETS:
                ref = ev.select_threshold(target)
                fast_t = pops[s].select(target)
                ref_t = ref["threshold"]
                if ref["status"] == "INFEASIBLE":
                    assert fast_t is None, (s, target, fast_t)
                    continue
                fast_p = pops[s].point(ref_t)
                # zero-area FPs are outside ev; compare TP and positive-area FP only
                zfp = sum(1 for n in members[s] for v in recs[n]["fp"][:recs[n]["zero"]] if v >= ref_t)
                assert ref["status"] == "FEASIBLE" and abs(fast_t - ref_t) == 0, (s, target, fast_t, ref_t)
                assert ref["operating_point"]["tp"] == fast_p["tp"], s
                assert ref["operating_point"]["fp"] == fast_p["fp"] - zfp, s
            result["checks"][s] = "ReferenceEvaluator whole-population select_threshold/operating_point == fast path"

    rng = np.random.default_rng(CONFIG["evaluation"]["bootstrap"]["seed"])
    B = args.replicates
    boot_w = {s: [np.bincount(rng.integers(0, p.n, p.n), minlength=p.n).astype(float) for _ in range(B)]
              for s, p in pops.items()}
    clear = pops["val:clear_day"]
    for target in TARGETS:
        t = sel.select(target)
        sel_point = sel.point(t)
        tb = [sel.select(target, w) for w in boot_w["selection"]]
        result["selection"][str(target)] = {"threshold": t, "point": sel_point if t is not None else None,
                                            "selection_ceiling": sel.point(None),
                                            "threshold_ci": ci(tb), "status": "FEASIBLE" if t is not None else "INFEASIBLE",
                                            "bootstrap_infeasible_replicates": sum(x is None for x in tb)}
        if t is None:  # no source operating point: transfer undefined, never the ceiling
            result["transfer"][str(target)] = {"status": "INFEASIBLE_SOURCE_TARGET"}
            continue
        tr = {}
        clear_op, clear_ceil = clear.point(t), clear.point(None)
        for s, p in pops.items():
            op, ceil = p.point(t), p.point(None)
            oracle_t = p.select(target)
            oracle = p.point(oracle_t) if oracle_t is not None else None
            boots = []
            for b in range(B):
                tbb = tb[b]
                if tbb is None:
                    continue
                w, wc = boot_w[s][b], boot_w["val:clear_day"][b]
                o, c = p.point(tbb, w), p.point(None, w)
                co, cc = clear.point(tbb, wc), clear.point(None, wc)
                boots.append((o["recall"], o["fppi"], c["recall"],
                              (co["recall"] - o["recall"]) if o["recall"] is not None else None,
                              (cc["recall"] - c["recall"]) if c["recall"] is not None else None,
                              ((c["recall"] - o["recall"]) - (cc["recall"] - co["recall"])) if o["recall"] is not None else None))
            col = list(zip(*boots)) if boots else [[]] * 6
            entry = {"operating": op, "ceiling_recall": ceil["recall"],
                     "recall_ci": ci(col[0]), "fppi_ci": ci(col[1]), "ceiling_ci": ci(col[2]),
                     "gap_to_target": target_gap_decomposition(target, op["recall"], ceil["recall"]) if op["recall"] is not None else None,
                     "oracle": {"threshold": oracle_t, "fppi": oracle["fppi"] if oracle else None,
                                "precision": oracle["precision"] if oracle else None,
                                "status": "FEASIBLE" if oracle_t is not None else "INFEASIBLE"},
                     "by_height": p.by_height(t)}
            if op["recall"] is not None:
                entry["loss_vs_clear_day"] = held_out_loss_decomposition(
                    clear_op["recall"], op["recall"], clear_ceil["recall"], ceil["recall"])
                entry["loss_ci"] = {"held_out_loss": ci(col[3]), "ceiling_difference": ci(col[4]),
                                    "threshold_miss_difference": ci(col[5])}
            tr[s] = entry
        result["transfer"][str(target)] = tr
    args.out_json.write_text(json.dumps(result, indent=1, default=float))
    for target, tr in result["transfer"].items():
        print("target", target, tr.get("status", "FEASIBLE"))
        for s in STRATA:
            if s in tr:
                e = tr[s]
                print(f"  {s:22s} n={pops[s].n:5d} G={int(pops[s].G.sum()):5d} R@t*={e['operating']['recall']:.3f} "
                      f"FPPI={e['operating']['fppi']:.3f} ceil={e['ceiling_recall']:.3f}")


if __name__ == "__main__":
    main()
