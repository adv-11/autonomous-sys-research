"""Claude Opus, amendment 4: ACDC as a descriptive external panel for the BDD-trained runs.

GT: ACDC detection labels via threshold_transfer.acdc.convert_acdc (iscrowd -> ignore,
provisional policy); native 'person' is the pedestrian class (riders stay separate, as in
BDD). Predictions: raw candidates from remote.py (--set acdc). Thresholds: the BDD
source-selection thresholds, unchanged (B: preregistered t*(0.80); A/C: exploratory).
Matching: unchanged ReferenceEvaluator (via the evaluate_transfer match rules) with
same-category IoA>=0.5 absorption by crowd regions. Point estimates only: with 4-6 GoPro
recording clusters per condition no resampling interval has validated coverage. Descriptive only.

    PYTHONPATH=src;<pylib> python acdc_eval.py --acdc-root R --arm B=acdc_B.npz=bdd_eval.json [...] --out-json OUT
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evaluate_transfer as ET  # noqa: E402
from threshold_transfer.acdc import AGGREGATE_FILES, convert_acdc, gopro_recording, parse_file_name  # noqa: E402
from threshold_transfer.metrics import ReferenceEvaluator  # noqa: E402


def load_gt(root):
    images, anns = {}, defaultdict(list)
    for (split, ref), rel in AGGREGATE_FILES.items():
        doc = convert_acdc(json.loads((root / rel).read_text()), split=split, reference=ref,
                           ignore_policy="acdc_iscrowd_v1_provisional", check_masks=False)
        for im in doc["images"]:
            images[im["file_name"]] = im
        by_id = {im["image_id"]: im["file_name"] for im in doc["images"]}
        for a in doc["annotations"]:
            if a["category"] == "person":
                anns[by_id[a["image_id"]]].append(a)
    return images, anns


def match(names, images, anns, preds):
    """Reference evaluator per chunk; zero-area candidates are explicit FPs (2026-11-10 decision)."""
    recs = {}
    for k in range(0, len(names), 300):
        chunk = names[k:k + 300]
        ims = [{"image_id": n, "width": images[n]["width"], "height": images[n]["height"]} for n in chunk]
        gts, cands, zero = [], [], defaultdict(list)
        for n in chunk:
            for j, a in enumerate(anns[n]):
                gts.append({"annotation_id": f"{n}#g{j}", "image_id": n, "category": "pedestrian",
                            "bbox": a["bbox"], "ignore": a["ignore"], "iscrowd": a["iscrowd"]})
            b, s = preds[n]
            for j in range(len(s)):
                x1, y1, x2, y2 = (float(v) for v in b[j])
                if x2 == x1 or y2 == y1:
                    zero[n].append(float(s[j]))
                    continue
                cands.append({"candidate_id": f"{n}#p{j:05d}", "image_id": n, "category": "pedestrian",
                              "bbox": [x1, y1, x2 - x1, y2 - y1], "score": float(s[j])})
        ev = ReferenceEvaluator({"schema_version": "threshold-transfer-v1", "images": ims, "annotations": gts,
                                 "provenance": {}},
                                {"schema_version": "threshold-transfer-v1", "predictions": cands,
                                 "provenance": {"evaluated_image_ids": chunk}},
                                categories=["pedestrian"], ignore_policy="same_category_ioa")
        for n in chunk:
            elig = [j for j, a in enumerate(anns[n]) if not a["ignore"]]
            recs[n] = {"tp": [], "fp": list(zero[n]), "zero": len(zero[n]), "ignored": 0,
                       "gt_h": [anns[n][j]["bbox"][3] for j in elig], "gt_match": [None] * len(elig),
                       "_pos": {j: i for i, j in enumerate(elig)}}
        for r in ev.rows:
            o = recs[r["image_id"]]
            if r["outcome"] == "TP":
                o["tp"].append(r["score"])
                o["gt_match"][o["_pos"][int(r["annotation_id"].split("#g")[1])]] = r["score"]
            elif r["outcome"] == "IGNORED":
                o["ignored"] += 1
            else:
                o["fp"].append(r["score"])
    return recs


def cluster_weights(names, rng, B):
    keys = [gopro_recording(parse_file_name(n)["sequence"]) or parse_file_name(n)["sequence"] for n in names]
    uniq = sorted(set(keys))
    idx = np.array([uniq.index(k) for k in keys])
    out = []
    for _ in range(B):
        cw = np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq)).astype(float)
        out.append(cw[idx])
    return out, len(uniq)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--acdc-root", type=Path, required=True)
    ap.add_argument("--arm", action="append", required=True, help="LABEL=acdc_preds.npz=bdd_eval.json[,more.json]")
    ap.add_argument("--replicates", type=int, default=1000)
    ap.add_argument("--out-json", type=Path, required=True)
    a = ap.parse_args()
    images, anns = load_gt(a.acdc_root)
    strata = defaultdict(list)
    for n in sorted(images):
        p = parse_file_name(n)
        strata[f"{p['condition']}_{'reference' if p['reference'] else 'adverse'}"].append(n)
    result = {"note": "Descriptive external panel (amendment 4); ACDC provisional iscrowd-ignore policy; "
                      "BDD source thresholds unchanged; no intervals published (4-6 recording clusters per condition).",
              "strata": {s: {"images": len(v), "pedestrians": sum(not x["ignore"] for n in v for x in anns[n])}
                         for s, v in strata.items()}, "arms": {}}
    for spec in a.arm:
        label, path, evs = spec.split("=", 2)
        z = np.load(path)
        names, offs, bx, sc = [str(n) for n in z["names"]], z["offsets"], z["boxes"], z["scores"]
        preds = {n: (bx[offs[i]:offs[i + 1]], sc[offs[i]:offs[i + 1]]) for i, n in enumerate(names)}
        assert set(names) == set(images), "ACDC prediction coverage must equal the labelled image set"
        thresholds = {}
        for f in evs.split(","):
            ev = json.loads(Path(f).read_text())
            for target, s in ev["selection"].items():
                if s.get("threshold") is not None:
                    thresholds[f"{Path(f).stem}:target{target}"] = s["threshold"]
        recs = match(sorted(images), images, anns, preds)
        arm = {"preds_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(), "thresholds": thresholds,
               "strata": {}}
        rng = np.random.default_rng(20261115)
        for s, ns in sorted(strata.items()):
            pop = ET.Population([recs[n] for n in ns])
            _, nclu = cluster_weights(ns, rng, 1)
            # Review F5: no intervals; 4-6 recording clusters per condition give no validated coverage.
            entry = {"clusters": nclu, "ceiling": pop.point(None)["recall"], "at": {}}
            for name, t in thresholds.items():
                pt = pop.point(t)
                entry["at"][name] = {"recall": pt["recall"], "fppi": pt["fppi"], "precision": pt["precision"]}
            arm["strata"][s] = entry
        result["arms"][label] = arm
        for s, e in arm["strata"].items():
            first = next(iter(e["at"].items()), (None, None))
            print(label, s, f"ceil={e['ceiling']:.3f}", first[0], {k: round(v, 3) for k, v in (first[1] or {}).items()
                                                                     if isinstance(v, float)})
    a.out_json.write_text(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
