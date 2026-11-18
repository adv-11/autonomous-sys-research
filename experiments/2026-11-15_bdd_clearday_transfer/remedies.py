"""Claude Opus: amendment 4 (exploratory) — night threshold remedies on existing predictions.

Remedies: equal-recall and equal-FPPI condition-aware night thresholds chosen on night
calibration data, and Platt calibration (global vs per-condition). Calibration data are
either a val-night split half (CPU proxy, --proxy) or BDD train-night images (--cal-preds).
The no-matched-candidate part is unrecoverable by any threshold and is reported alongside.

    PYTHONPATH=src;<pylib> python remedies.py --gt GT --arm B=b.npz --proxy --out-json OUT
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import matched_fppi as M  # noqa: E402

ET = M.ET
HALF_SALT = "bdd-valnight-half-v1:"
LEVELS = [0.5, 1.0, 2.0, 4.5]


def half_of(name):
    return int(hashlib.sha256((HALF_SALT + name).encode()).hexdigest()[:8], 16) % 2


def fit_platt(p, w=None, iters=30):
    """Weighted ML logistic fit of TP(1)/FP(0) on logit(score); returns (a, b)."""
    w = np.ones(p.n) if w is None else w
    s = np.concatenate([p.tp_all, p.fp_all])
    y = np.concatenate([np.ones(len(p.tp_all)), np.zeros(len(p.fp_all))])
    sw = np.concatenate([w[p.tp_img], w[p.fp_img]])
    keep = sw > 0
    s, y, sw = np.clip(s[keep], 1e-7, 1 - 1e-7), y[keep], sw[keep]
    x = np.log(s / (1 - s))
    X = np.stack([x, np.ones_like(x)], 1)
    beta = np.array([1.0, 0.0])
    for _ in range(iters):
        q = 1 / (1 + np.exp(-(X @ beta)))
        g = X.T @ (sw * (y - q))
        H = (X * (sw * q * (1 - q))[:, None]).T @ X
        step = np.linalg.solve(H + 1e-9 * np.eye(2), g)
        beta += step
        if np.abs(step).max() < 1e-10:
            break
    return float(beta[0]), float(beta[1])


def platt_threshold(ab_clear, ab_night, t):
    """Raw night score whose night-calibrated probability equals p_clear(t)."""
    a_c, b_c = ab_clear
    a_n, b_n = ab_night
    t = min(max(t, 1e-7), 1 - 1e-7)
    z = a_c * np.log(t / (1 - t)) + b_c          # logit p_clear(t)
    xn = (z - b_n) / a_n                          # a_n * logit(s) + b_n = z
    return float(1 / (1 + np.exp(-xn)))


def source_point(sel, spec, w=None):
    kind, val = spec
    t = sel.select(val, w) if kind == "recall" else M.select_fppi(sel, val, w)
    if t is None:
        return None
    pt = sel.point(t, w)
    return {"t": t, "recall": pt["recall"], "fppi": pt["fppi"]}


def remedy_thresholds(sel, cal, spec, ws=None, wcal=None):
    src = source_point(sel, spec, ws)
    if src is None:
        return None
    ab_c, ab_n = fit_platt(sel, ws), fit_platt(cal, wcal)
    out = {"transfer": src["t"],
           "equal_recall": cal.select(src["recall"], wcal),
           "equal_fppi": M.select_fppi(cal, src["fppi"], wcal),
           "platt_per_condition": platt_threshold(ab_c, ab_n, src["t"])}
    return out, src, ab_c, ab_n


def evaluate(test, clear, th, wt=None, wc=None):
    base = th["transfer"]
    c_op, c_ceil = clear.point(base, wc)["recall"], clear.point(None, wc)["recall"]
    n_ceil = test.point(None, wt)["recall"]
    n_base = test.point(base, wt)
    removable = n_ceil - n_base["recall"]
    thr_part = removable - (c_ceil - c_op)
    res = {"night_ceiling": n_ceil, "clear_recall": c_op, "clear_ceiling": c_ceil,
           "ceiling_part_unrecoverable": c_ceil - n_ceil, "threshold_part": thr_part,
           "night_removable": removable, "remedies": {}}
    for name, t in th.items():
        if t is None:
            res["remedies"][name] = None
            continue
        pt = test.point(t, wt)
        d = pt["recall"] - n_base["recall"]
        res["remedies"][name] = {"threshold": t, "recall": pt["recall"], "fppi": pt["fppi"],
                                 "delta_recall": d, "delta_fppi": pt["fppi"] - n_base["fppi"],
                                 "recovered_of_threshold_part": d / thr_part if thr_part > 0 else None,
                                 "recovered_of_night_removable": d / removable if removable > 0 else None}
    return res


def ci(v):
    v = [x for x in v if x is not None]
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] if len(v) > 10 else None


def run_direction(pops, cal_key, test_key, specs, B, rng):
    sel, clear, cal, test = pops["selection"], pops["val:clear_day"], pops[cal_key], pops[test_key]
    out = {}
    W = {k: [np.bincount(rng.integers(0, p.n, p.n), minlength=p.n).astype(float) for _ in range(B)]
         for k, p in (("sel", sel), ("clear", clear), ("cal", cal), ("test", test))}
    for label, spec in specs:
        r = remedy_thresholds(sel, cal, spec)
        if r is None:
            out[label] = {"status": "INFEASIBLE_SOURCE_TARGET"}
            continue
        th, src, ab_c, ab_n = r
        assert ab_c[0] > 0, "global Platt map must be strictly increasing"
        point = evaluate(test, clear, th)
        # oracle on the test half itself, same recall target (reference only)
        ot = test.select(src["recall"])
        point["oracle_equal_recall_on_test"] = None if ot is None else {
            "recall": test.point(ot)["recall"], "fppi": test.point(ot)["fppi"]}
        point.update({"source": src, "platt_clear_ab": ab_c, "platt_night_ab": ab_n,
                      "platt_global_check": "a>0: global map strictly monotone; reselected detections identical, recovery 0"})
        reps = {m: {"delta_recall": [], "delta_fppi": []} for m in th}
        reps["threshold_part"] = []
        for b in range(B):
            rb = remedy_thresholds(sel, cal, spec, W["sel"][b], W["cal"][b])
            if rb is None:
                continue
            e = evaluate(test, clear, rb[0], W["test"][b], W["clear"][b])
            reps["threshold_part"].append(e["threshold_part"])
            for m, v in e["remedies"].items():
                reps[m]["delta_recall"].append(None if v is None else v["delta_recall"])
                reps[m]["delta_fppi"].append(None if v is None else v["delta_fppi"])
        point["threshold_part_ci"] = ci(reps.pop("threshold_part"))
        for m, v in point["remedies"].items():
            if v is not None:
                v["delta_recall_ci"] = ci(reps[m]["delta_recall"])
                v["delta_fppi_ci"] = ci(reps[m]["delta_fppi"])
                v["bootstrap_undefined"] = sum(x is None for x in reps[m]["delta_recall"])
        out[label] = point
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--arm", action="append", required=True, help="LABEL=preds.npz[=recall_target]")
    ap.add_argument("--proxy", action="store_true", help="val-night split-half calibration")
    ap.add_argument("--cal-gt", type=Path, help="GT json for train-night calibration images")
    ap.add_argument("--cal-preds", action="append", default=[], help="LABEL=cal_preds.npz")
    ap.add_argument("--replicates", type=int, default=ET.CONFIG["evaluation"]["bootstrap"]["replicates"])
    ap.add_argument("--out-json", type=Path, required=True)
    a = ap.parse_args()
    gt = json.loads(a.gt.read_text())
    members = M.members_of(gt)
    night = members["val:night"]
    members["night_h0"] = [n for n in night if half_of(n) == 0]
    members["night_h1"] = [n for n in night if half_of(n) == 1]
    cal_preds = dict(s.split("=", 1) for s in a.cal_preds)
    cal_gt = json.loads(a.cal_gt.read_text()) if a.cal_gt else None
    result = {"amendment": "amendment_4 (exploratory)", "mode": "proxy split-half of val night" if a.proxy
              else "BDD train-night calibration", "labels_note": "BDD100K legacy 2018 labels; HF-mirror images",
              "arms": {}}
    for spec in a.arm:
        parts = spec.split("=")
        label, path = parts[0], parts[1]
        specs = [(f"L{L}", ("fppi", L)) for L in LEVELS]
        if len(parts) > 2:
            specs.insert(0, (f"target{parts[2]}", ("recall", float(parts[2]))))
        recs = M.load(gt, Path(path), 0.0)
        pops = {k: ET.Population([recs[n] for n in members[k]])
                for k in ("selection", "val:clear_day", "val:night", "night_h0", "night_h1")}
        z = np.load(path)
        arm = {"preds_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
               "counts": {k: {"images": p.n, "pedestrians": int(p.G.sum())} for k, p in pops.items()}}
        rng = np.random.default_rng(ET.CONFIG["evaluation"]["bootstrap"]["seed"])
        if a.proxy:
            arm["cal_h0_test_h1"] = run_direction(pops, "night_h0", "night_h1", specs, a.replicates, rng)
            arm["cal_h1_test_h0"] = run_direction(pops, "night_h1", "night_h0", specs, a.replicates, rng)
        else:
            crecs = M.load(cal_gt, Path(cal_preds[label]), 0.0)
            pops["train_night_cal"] = ET.Population([crecs[n] for n in sorted(cal_gt)])
            arm["counts"]["train_night_cal"] = {"images": pops["train_night_cal"].n,
                                                "pedestrians": int(pops["train_night_cal"].G.sum())}
            arm["cal_preds_sha256"] = hashlib.sha256(Path(cal_preds[label]).read_bytes()).hexdigest()
            arm["cal_trainnight_test_valnight"] = run_direction(pops, "train_night_cal", "val:night", specs,
                                                                a.replicates, rng)
        del z
        result["arms"][label] = arm
        for d, res in ((k, v) for k, v in arm.items() if k.startswith("cal_") and isinstance(v, dict)
                       and "preds" not in k):
            for op, r in res.items():
                if "remedies" not in r:
                    print(label, d, op, r.get("status"))
                    continue
                print(label, d, op, f"thrPart={r['threshold_part']:.3f} ceilPart={r['ceiling_part_unrecoverable']:.3f}",
                      " ".join(f"{m}:R{v['recall']:.3f}/F{v['fppi']:.2f}/dR{v['delta_recall']:+.3f}" if v else f"{m}:undef"
                               for m, v in r["remedies"].items()))
    a.out_json.write_text(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
