"""Claude Opus: review finding F1 — how the ceiling/threshold split depends on the ceiling definition.

The loss (clear-day minus night recall at the transferred t*, greedy IoU>=0.5) is unchanged; only
the candidate ceiling is redefined, and the threshold part is loss minus ceiling part (the same
identity as held_out_loss_decomposition). Variants:
  base      greedy IoU>=0.5 match by a pedestrian candidate with score>=1e-4 (reported definition)
  floor1e-3 same, score>=1e-3. Exact from the 1e-4 run: greedy labels are prefix-stable, and with
            no cap hits a 1e-3 floor keeps the same >=1e-3 boxes through NMS.
  any_iou50 any pedestrian candidate (score>=1e-4) at IoU>=0.5, non-greedy (checks greedy effect)
  any_iou30 any pedestrian candidate (score>=1e-4) at IoU>=0.3 (localization-tolerant)
Exploratory, post hoc; point estimates only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import matched_fppi as M  # noqa: E402


def any_iou_hits(gt_boxes, cand, thr):
    if not len(gt_boxes):
        return np.zeros(0, bool)
    if not len(cand):
        return np.zeros(len(gt_boxes), bool)
    g, c = np.asarray(gt_boxes, float)[:, None, :], np.asarray(cand, float)[None, :, :]
    iw = np.clip(np.minimum(g[..., 2], c[..., 2]) - np.maximum(g[..., 0], c[..., 0]), 0, None)
    ih = np.clip(np.minimum(g[..., 3], c[..., 3]) - np.maximum(g[..., 1], c[..., 1]), 0, None)
    inter = iw * ih
    union = ((g[..., 2] - g[..., 0]) * (g[..., 3] - g[..., 1]) + (c[..., 2] - c[..., 0]) * (c[..., 3] - c[..., 1]) - inter)
    return ((inter / union) >= thr).any(axis=1)


def ceilings(gt, path, members, recs):
    z = np.load(path)
    names, offs, bx = [str(n) for n in z["names"]], z["offsets"], z["boxes"]
    idx = {n: i for i, n in enumerate(names)}
    out = {}
    for s in ("val:clear_day", "val:night"):
        tot = base = f3 = a50 = a30 = 0
        for n in members[s]:
            peds = gt[n]["peds"]
            cand = bx[offs[idx[n]]:offs[idx[n] + 1]]
            m = recs[n]["gt_match"]
            tot += len(peds)
            base += sum(v is not None for v in m)
            f3 += sum(v is not None and v >= 1e-3 for v in m)
            a50 += int(any_iou_hits(peds, cand, 0.5).sum())
            a30 += int(any_iou_hits(peds, cand, 0.3).sum())
        out[s] = {"base": base / tot, "floor1e-3": f3 / tot, "any_iou50": a50 / tot, "any_iou30": a30 / tot}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--arm", action="append", required=True, help="LABEL=preds.npz=t1,t2,... (named thresholds)")
    ap.add_argument("--out-json", type=Path, required=True)
    a = ap.parse_args()
    gt = json.loads(a.gt.read_text())
    members = M.members_of(gt)
    res = {"note": __doc__.strip().splitlines()[0], "arms": {}}
    for spec in a.arm:
        label, path, ts = spec.split("=", 2)
        recs = M.load(gt, Path(path), 0.0)
        pops = {s: M.ET.Population([recs[n] for n in members[s]]) for s in ("val:clear_day", "val:night")}
        ceil = ceilings(gt, path, members, recs)
        arm = {"ceilings": ceil, "operating_points": {}}
        for item in ts.split(","):
            name, t = item.split(":")
            t = float(t)
            assert t >= 1e-3, "floor1e-3 variant requires t* >= 1e-3"
            rc, rn = pops["val:clear_day"].point(t)["recall"], pops["val:night"].point(t)["recall"]
            loss = rc - rn
            arm["operating_points"][name] = {
                "threshold": t, "clear_recall": rc, "night_recall": rn, "loss": loss,
                "split": {v: {"ceiling_part": ceil["val:clear_day"][v] - ceil["val:night"][v],
                              "threshold_part": loss - (ceil["val:clear_day"][v] - ceil["val:night"][v])}
                          for v in ceil["val:night"]}}
        res["arms"][label] = arm
    a.out_json.write_text(json.dumps(res, indent=1))
    for label, arm in res["arms"].items():
        for name, op in arm["operating_points"].items():
            print(label, name, f"loss={op['loss']:.3f}", "  ".join(
                f"{v}: ceil={d['ceiling_part']:+.3f} thr={d['threshold_part']:+.3f}" for v, d in op["split"].items()))


if __name__ == "__main__":
    main()
