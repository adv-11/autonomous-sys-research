"""GPT Sol independent review: counts-only output; bounded CPU rematching.

Pass --author, --inputs and --cache directories; never prints GT identifiers.
No inference, threshold search, bootstrap or GPU dependencies.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def key(name, box):
    return hashlib.sha256(json.dumps([name, [float(x) for x in box]],
                                    separators=(",", ":")).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for arg in ("author", "inputs", "cache"):
        ap.add_argument("--" + arg, type=Path, required=True)
    a = ap.parse_args()
    pub = a.author / "docs/research/2026-11-26_seed_miss_diagnosis"
    provenance, published = read(pub / "provenance.json"), read(pub / "counts.json")
    gt_path = a.inputs / "private/gt_pedestrian.json"
    gt = read(gt_path)
    groups = {"selection": {n for n, g in gt.items() if g["role"] == "selection"}}
    for condition in ("clear_day", "night"):
        groups[condition] = {n for n, g in gt.items()
                             if g["role"] != "selection" and g.get("stratum") == condition}
    assert not any(groups[x] & groups[y] for x in groups for y in groups if x < y)
    names = set.union(*groups.values())
    expected = {}
    for name in names:
        for index, box in enumerate(gt[name]["peds"]):
            k = key(name, box)
            assert k not in expected
            expected[k] = (name, f"{name}#g{index}", box, box[3] - box[1])
    caches = {run: read(a.cache / f"{run}_matches.json") for run in ("B", "B2")}
    matched_path = a.author / "docs/research/2026-11-17_threshold_remedies/matched_ABCB2_all.json"
    matched = read(matched_path)
    assert digest(matched_path) == provenance["matched_report_sha256"]
    reports = {}
    for run, report in (("B", "2026-11-15_bdd_clearday_transfer/B_1280.json"),
                        ("B2", "2026-11-17_threshold_remedies/B2_1280.json")):
        path = a.author / "docs/research" / report
        reports[run] = read(path)
        p = provenance["runs"][run]
        assert digest(path) == p["report_sha256"]
        assert digest(gt_path) == p["gt_sha256"]
        for field, rel in (("evaluator_sha256", "src/threshold_transfer/metrics.py"),
                           ("match_chunk_sha256", "experiments/2026-11-15_bdd_clearday_transfer/evaluate_transfer.py")):
            assert digest(a.author / rel) == p[field]
        assert all(caches[run]["provenance"][k] == p[k] for k in caches[run]["provenance"])
        assert set(caches[run]["people"]) == set(expected)
        assert set(caches[run]["images"]) == names
        for k, row in caches[run]["people"].items():
            assert (row["image"], row["annotation_id"], row["box"], row["height"]) == expected[k]
            assert row["score"] is None or 1e-4 <= row["score"] <= 1
        assert provenance["policies"]["source_FPPI_1"][run] == matched["arms"][run]["1.0"]["threshold"]
        assert provenance["policies"]["source_recall_080_sensitivity"][run] == reports[run]["selection"]["0.8"]["threshold"]
        print(run, "source recall .80 status", reports[run]["selection"]["0.8"]["status"])
    bins = ((0, 16, "0-16"), (16, 32, "16-32"), (32, 64, "32-64"),
            (64, 128, "64-128"), (128, float("inf"), ">=128"))
    for policy, thresholds in provenance["policies"].items():
        for condition, images in groups.items():
            keys = [k for k, row in expected.items() if row[0] in images]
            for label, subset in [(None, keys)] + [(label, [k for k in keys if lo <= expected[k][3] < hi])
                                                   for lo, hi, label in bins]:
                states = Counter(tuple(0 if caches[r]["people"][k]["score"] is None else
                                       2 if caches[r]["people"][k]["score"] >= thresholds[r] else 1
                                       for r in ("B", "B2")) for k in subset)
                ref = published[policy][condition]
                if label:
                    ref = ref["by_height"][label]
                matrix = [[states[i, j] for j in range(3)] for i in range(3)]
                assert matrix == ref["state_matrix_B_rows_B2_columns"] and len(subset) == ref["gt"]
                overlap = [states[2, 2], sum(states[2, j] for j in (0, 1)),
                           sum(states[i, 2] for i in (0, 1)), sum(states[i, j] for i in (0, 1) for j in (0, 1))]
                assert overlap == [ref[f] for f in ("both_detected", "B_only_detected", "B2_only_detected", "neither_detected_stable_misses")]
                if label:
                    continue
                fps = {}
                for axis, run in enumerate(("B", "B2")):
                    tp = sum(v for state, v in states.items() if state[axis] == 2)
                    ceiling = sum(v for state, v in states.items() if state[axis] != 0)
                    fps[run] = sum(s >= thresholds[run] for n in images for s in caches[run]["images"][n]["fp"])
                    stratum = condition if condition == "selection" else "val:" + condition
                    original = reports[run]
                    assert ceiling == original["strata"][stratum]["ceiling"]["tp"]
                    if policy == "source_FPPI_1":
                        arm = matched["arms"][run]["1.0"]
                        point = arm["selection"] if condition == "selection" else arm["conditions"][stratum]
                        assert tp / len(keys) == point["recall"] and fps[run] / len(images) == point["fppi"]
                    else:
                        point = original["selection"]["0.8"]["point"] if condition == "selection" else original["transfer"]["0.8"][stratum]["operating"]
                        assert (tp, fps[run]) == (point["tp"], point["fp"])
                assert fps == ref["FP"] and len(images) == ref["images"]
                print(policy, condition, "GT", len(keys), "overlap", overlap, "matrix", matrix, "FP", fps)
    sys.path[:0] = [str(a.author / "src"), str(a.author / "experiments/2026-11-15_bdd_clearday_transfer")]
    import numpy as np
    import evaluate_transfer as et
    sample = set()
    for images in groups.values():
        sample.update(sorted(n for n in images if not gt[n]["peds"])[:2])
        sample.update(sorted(n for n in images if gt[n]["peds"])[:4])
        sample.update(sorted(images, key=lambda n: (-len(gt[n]["peds"]), n))[:2])
    sample = sorted(sample)
    for run, rel in (("B", "preds/B_1280.npz"), ("B2", "stage2/preds/B2_1280.npz")):
        path = a.inputs / rel
        assert digest(path) == provenance["runs"][run]["predictions_sha256"]
        with np.load(path, allow_pickle=False) as z:
            all_names = [str(n) for n in z["names"]]
            assert len(all_names) == len(set(all_names)) and set(all_names) == set(gt)
            offsets, boxes, scores = z["offsets"], z["boxes"], z["scores"]
            assert offsets[0] == 0 and offsets[-1] == len(boxes) == len(scores)
            assert np.all(np.diff(offsets) >= 0) and np.isfinite(boxes).all() and np.isfinite(scores).all()
            assert np.all(scores >= 1e-4) and np.all(scores <= 1) and np.all(z["all_class_candidates"] < 3000)
            lookup = {n: i for i, n in enumerate(all_names)}
            preds = {n: (boxes[offsets[lookup[n]]:offsets[lookup[n]+1]], scores[offsets[lookup[n]]:offsets[lookup[n]+1]]) for n in sample}
        recs, ev = et.match_chunk(sample, gt, preds)
        tp = {row["annotation_id"]: row["score"] for row in ev.rows if row["outcome"] == "TP"}
        for k, (name, aid, box, height) in expected.items():
            if name in preds:
                assert caches[run]["people"][k]["score"] == tp.get(aid)
        for name in sample:
            assert sorted(recs[name]["fp"]) == sorted(caches[run]["images"][name]["fp"])
        print(run, "bounded rematch images", len(sample), "GT", sum(len(gt[n]["peds"]) for n in sample), "PASS")
    print("PASS: hashes, unique geometry/annotation mapping, all six aggregate populations, both policies, fixed height matrices, bounded rematch")


if __name__ == "__main__":
    main()
