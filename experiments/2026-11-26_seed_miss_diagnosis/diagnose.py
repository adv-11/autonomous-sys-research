"""GPT Sol: bounded CPU overlap diagnostic on existing B/B2 candidates.

No inference or threshold selection. Reuses Claude Opus's unchanged match_chunk.
Person data and matching cache go ONLY to --private-out; public tables are counts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "experiments/2026-11-15_bdd_clearday_transfer")]
import numpy as np
import evaluate_transfer as ET


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def key_for(name, box):
    # The legacy converted GT has no original publisher annotation IDs. Use a
    # geometry key, never zip two per-run GT lists. Duplicates fail closed below.
    payload = json.dumps([name, list(map(float, box))], separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def match(path, gt, names, cache_path, gt_sha):
    digest = sha(path)
    provenance = {"predictions_sha256": digest, "gt_sha256": gt_sha,
                  "evaluator_sha256": sha(ROOT / "src/threshold_transfer/metrics.py"),
                  "match_chunk_sha256": sha(Path(ET.__file__))}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text())
        assert cache["provenance"] == provenance
        return cache
    with np.load(path, allow_pickle=False) as z:
        all_names = list(map(str, z["names"]))
        assert len(all_names) == len(set(all_names)) and set(all_names) == set(gt)
        offsets, boxes, scores = z["offsets"], z["boxes"], z["scores"]
        assert len(offsets) == len(all_names) + 1
        assert offsets[0] == 0 and offsets[-1] == len(scores) == len(boxes)
        assert np.all(offsets[1:] >= offsets[:-1])
        assert np.isfinite(boxes).all() and np.isfinite(scores).all()
        assert np.all(scores >= 1e-4) and np.all(scores <= 1)
        assert np.all(z["all_class_candidates"] < 3000)
        lookup = {n: i for i, n in enumerate(all_names)}
        preds = {n: (boxes[offsets[lookup[n]]:offsets[lookup[n] + 1]],
                     scores[offsets[lookup[n]]:offsets[lookup[n] + 1]]) for n in names}
    people, images = {}, {}
    for start in range(0, len(names), 200):
        chunk = names[start:start + 200]
        recs, evaluator = ET.match_chunk(chunk, gt, preds)
        # Explicit annotation IDs connect evaluator rows to verified geometry.
        annotation_to_key = {}
        for n in chunk:
            images[n] = {"fp": recs[n]["fp"], "zero": recs[n]["zero"]}
            for k, box in enumerate(gt[n]["peds"]):
                key = key_for(n, box)
                assert key not in people, "duplicate image/box identity is ambiguous"
                aid = f"{n}#g{k}"
                annotation_to_key[aid] = key
                people[key] = {"image": n, "annotation_id": aid, "box": box,
                               "height": box[3] - box[1], "score": None}
        for row in evaluator.rows:
            if row["outcome"] == "TP":
                person = people[annotation_to_key[row["annotation_id"]]]
                assert person["image"] == row["image_id"] and person["score"] is None
                person["score"] = row["score"]
        for n in chunk:
            # Accounting against the existing evaluator's output, including heights.
            assert sorted(p["score"] for p in people.values()
                          if p["image"] == n and p["score"] is not None) == sorted(recs[n]["tp"])
        print(f"matched {path.stem}: {min(start + 200, len(names))}/{len(names)} images", flush=True)
    cache = {"provenance": provenance, "people": people, "images": images}
    write(cache_path, cache)
    return cache


def counts(keys, caches, thresholds):
    # States: 0 absent from greedy candidate ceiling, 1 present below threshold,
    # 2 detected at the frozen operating threshold. Full 3x3 table resolves
    # stable misses into absent/absent, absent/below and below/below.
    matrix = np.zeros((3, 3), dtype=int)
    for key in keys:
        states = []
        for run in ("B", "B2"):
            score = caches[run]["people"][key]["score"]
            states.append(0 if score is None else 2 if score >= thresholds[run] else 1)
        matrix[tuple(states)] += 1
    n = len(keys)
    both, bonly, b2only = int(matrix[2, 2]), int(matrix[2, :2].sum()), int(matrix[:2, 2].sum())
    neither = int(matrix[:2, :2].sum())
    assert both + bonly + b2only + neither == n
    return {"gt": n, "state_matrix_B_rows_B2_columns": matrix.tolist(),
            "both_detected": both, "B_only_detected": bonly, "B2_only_detected": b2only,
            "neither_detected_stable_misses": neither,
            "one_detected_swapped_misses": bonly + b2only,
            "missed_by_either_union": n - both,
            "B_misses": neither + b2only, "B2_misses": neither + bonly,
            "both_ceiling_absent": int(matrix[0, 0]),
            "B_absent_B2_below": int(matrix[0, 1]),
            "B_below_B2_absent": int(matrix[1, 0]),
            "both_below": int(matrix[1, 1]),
            "B_ceiling_absent": int(matrix[0].sum()),
            "B2_ceiling_absent": int(matrix[:, 0].sum())}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", type=Path, required=True)
    ap.add_argument("--private-out", type=Path, required=True)
    args = ap.parse_args()
    public = ROOT / "docs/research/2026-11-26_seed_miss_diagnosis"
    public.mkdir(parents=True, exist_ok=True)
    args.private_out.mkdir(parents=True, exist_ok=True)
    gt_path = args.inputs / "private/gt_pedestrian.json"
    gt = json.loads(gt_path.read_text())
    assert sha(gt_path) == ET.CONFIG["manifest_sha256"]["gt_pedestrian.json"]
    names = sorted(n for n, g in gt.items() if g["role"] == "selection" or
                   g.get("stratum") in ("clear_day", "night"))
    matched_path = ROOT / "docs/research/2026-11-17_threshold_remedies/matched_ABCB2_all.json"
    matched = json.loads(matched_path.read_text())
    reports = {"B": ROOT / "docs/research/2026-11-15_bdd_clearday_transfer/B_1280.json",
               "B2": ROOT / "docs/research/2026-11-17_threshold_remedies/B2_1280.json"}
    policies = {"source_FPPI_1": {}, "source_recall_080_sensitivity": {}}
    caches, provenance = {}, {}
    for run, path in {"B": args.inputs / "preds/B_1280.npz",
                      "B2": args.inputs / "stage2/preds/B2_1280.npz"}.items():
        report = json.loads(reports[run].read_text())
        assert sha(path) == report["preds_sha256"]
        inference_summary = json.loads(path.with_suffix(".npz.json").read_text())
        assert inference_summary["out_sha256"] == report["preds_sha256"]
        assert inference_summary["imgsz"] == 1280 and inference_summary["cap_hits"] == 0
        policies["source_FPPI_1"][run] = matched["arms"][run]["1.0"]["threshold"]
        policies["source_recall_080_sensitivity"][run] = report["selection"]["0.8"]["threshold"]
        caches[run] = match(path, gt, names, args.private_out / f"{run}_matches.json", sha(gt_path))
        provenance[run] = {**caches[run]["provenance"], "report_sha256": sha(reports[run]),
                           "checkpoint_sha256": inference_summary["weights_sha256"],
                           "inference_summary_sha256": sha(path.with_suffix(".npz.json"))}
    assert set(caches["B"]["people"]) == set(caches["B2"]["people"])
    for key, p in caches["B"]["people"].items():
        q = caches["B2"]["people"][key]
        assert (p["image"], p["box"], p["height"]) == (q["image"], q["box"], q["height"])
    output = {}
    for policy, thresholds in policies.items():
        output[policy] = {}
        for condition in ("selection", "clear_day", "night"):
            image_names = [n for n in names if (gt[n]["role"] == "selection" if condition == "selection"
                           else gt[n].get("stratum") == condition)]
            image_set = set(image_names)
            keys = sorted(k for k, p in caches["B"]["people"].items() if p["image"] in image_set)
            result = counts(keys, caches, thresholds)
            result["images"] = len(image_names)
            result["by_height"] = {}
            for lo, hi in ET.C.HEIGHT_BINS:
                subset = [k for k in keys if caches["B"]["people"][k]["height"] >= lo and
                          (hi is None or caches["B"]["people"][k]["height"] < hi)]
                result["by_height"][ET.C.height_bin(lo)] = counts(subset, caches, thresholds)
            result["FP"] = {}
            for run in ("B", "B2"):
                fp = sum(s >= thresholds[run] for n in image_names for s in caches[run]["images"][n]["fp"])
                result["FP"][run] = fp
                # One bounded evidence check: exact frozen-report marginals and FPPI.
                report = json.loads(reports[run].read_text())
                s = "selection" if condition == "selection" else "val:" + condition
                ceiling_tp = result["gt"] - result[f"{run}_ceiling_absent"]
                detected = result["gt"] - result[f"{run}_misses"]
                assert ceiling_tp == report["strata"][s]["ceiling"]["tp"]
                if policy == "source_FPPI_1":
                    ref = matched["arms"][run]["1.0"]
                    point = ref["selection"] if condition == "selection" else ref["conditions"][s]
                    assert detected / result["gt"] == point["recall"]
                    assert fp / len(image_names) == point["fppi"]
                else:
                    point = report["selection"]["0.8"]["point"] if condition == "selection" else report["transfer"]["0.8"][s]["operating"]
                    assert detected == point["tp"] and fp == point["fp"]
            assert sum(v["gt"] for v in result["by_height"].values()) == result["gt"]
            output[policy][condition] = result
    write(public / "counts.json", output)
    write(public / "provenance.json", {"analyst": "GPT Sol", "original_experiment": "Claude Opus 5.5",
          "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "policies": policies, "runs": provenance, "matched_report_sha256": sha(matched_path),
          "identity": "SHA256(image name + exact float bbox); unique per GT; annotation-ID-to-geometry mapping verified; no cross-run positional join",
          "state_order": ["absent", "below", "detected"],
          "validation": "PASS: exact existing report TP, FP and ceiling counts on selection, clear day and night for both policies; identical geometry key sets and heights; all height/overlap partitions sum exactly",
          "candidate_policy": {**ET.CONFIG["inference"], "imgsz": 1280}, "IoU": 0.5, "new_GPU_CU": 0,
          "scope": "Existing B and B2 only; no NightOwls rescoring; no new threshold selection or intervals"})
    for policy, conditions in output.items():
        for condition in ("clear_day", "night"):
            r = conditions[condition]
            print(policy, condition, json.dumps({k: v for k, v in r.items() if k != "by_height"}))


if __name__ == "__main__":
    main()
