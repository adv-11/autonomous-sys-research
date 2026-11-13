"""GPT Sol: one posthoc CPU diagnosis of retained H4 outputs; no inference.

Native-category, size and overlap strata describe matched GT, not new validation.
One .70 greedy NMS on cached/clipped O2O person outputs is an approximation.
Run using existing numpy: python -B SCRIPT ROOT PRIVATE [--public PATH].
"""
import argparse
from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pilot", REPO / "experiments/2026-11-10_transfer_pilot.py")
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)
read, write, sha = pilot.read, pilot.write, pilot.sha
HEADS = ("yolo26s_o2o", "yolo26s_o2m")
PANELS = ("source_selection", "coco_reference", "fog", "night", "rain", "snow",
          "fog_normal", "night_normal", "rain_normal", "snow_normal")
STRATA = {
    "height_px": ["<32", "32-<96", ">=96"],
    "max_eligible_gt_iou": ["0", ">0-<.30", ">=.30"],
    "eligible_humans_in_image": ["1", "2-4", ">=5"],
    "intersects_ignore_or_crowd": ["no", "yes"],
    "native_category": ["person", "rider"],
}
DEFINITIONS = {
    "status": "POSTHOC descriptive; bins chosen before this diagnostic, after H4 results were known",
    "height_px": "Native annotation bbox height: <32, [32,96), >=96 pixels; not distance; source resolution differs",
    "max_eligible_gt_iou": "Maximum bbox IoU with any other eligible person/rider in same image: 0, (0,.30), >=.30; singleton=0",
    "eligible_humans_in_image": "Eligible merged person+rider count including this GT: 1, 2-4, >=5",
    "intersects_ignore_or_crowd": "Positive bbox intersection with any ignored/iscrowd human region in same image; not occlusion truth",
    "native_category": "pilot_native_category, with original merged-human matching unchanged; not person-only rematching",
    "sparse": "Denominator <10 GT flagged; no uncertainty/population inference or bin tuning",
    "nms": "ONE fixed IoU>.70 suppression, per-image person-only cached O2O outputs, score descending then candidate_id; no cap/floor change; already clipped; zero-area retained as FP; float64 numpy; not native O2M reproduction",
}


def intersection(a, b):
    return max(0., min(a[0]+a[2], b[0]+b[2])-max(a[0], b[0])) * max(0., min(a[1]+a[3], b[1]+b[3])-max(a[1], b[1]))


def iou(a, b):
    inter = intersection(a, b)
    union = a[2]*a[3]+b[2]*b[3]-inter
    return inter / union if union > 0 else 0.


def gt_features(panel):
    eligible = [a for a in panel["annotations"] if not (a["ignore"] or a["iscrowd"])]
    by_image, ignored = defaultdict(list), defaultdict(list)
    for a in panel["annotations"]:
        (ignored if a["ignore"] or a["iscrowd"] else by_image)[a["image_id"]].append(a)
    features = {}
    for a in eligible:
        others = [b for b in by_image[a["image_id"]] if b["annotation_id"] != a["annotation_id"]]
        overlap = max((iou(a["bbox"], b["bbox"]) for b in others), default=0.)
        height, count = a["bbox"][3], len(others)+1
        features[a["annotation_id"]] = dict(
            height_px="<32" if height < 32 else "32-<96" if height < 96 else ">=96",
            max_eligible_gt_iou="0" if overlap == 0 else ">0-<.30" if overlap < .30 else ">=.30",
            eligible_humans_in_image="1" if count == 1 else "2-4" if count <= 4 else ">=5",
            intersects_ignore_or_crowd="yes" if any(intersection(a["bbox"], b["bbox"]) > 0 for b in ignored[a["image_id"]]) else "no",
            native_category=a["attributes"]["pilot_native_category"],
            max_iou=overlap, image_id=a["image_id"])
    return features


def tp_set(ev, threshold=None):
    return {r["annotation_id"] for r in ev.rows if r["outcome"] == "TP" and (threshold is None or r["score"] >= threshold)}


def point(ev, threshold=None):
    p = ev.operating_point(threshold)
    return {k: p[k] for k in ("threshold", "image_count", "eligible_gt", "tp", "fp", "ignored", "fn", "recall", "fppi")}


def coverage(a, b, universe):
    assert a <= universe and b <= universe
    return dict(gt=len(universe), both=len(a & b), o2o_only=len(a-b), o2m_only=len(b-a), neither=len(universe-(a|b)))


def stratify(features, a, b):
    result = {}
    for name, bins in STRATA.items():
        result[name] = []
        for label in bins:
            universe = {key for key, f in features.items() if f[name] == label}
            result[name].append(dict(bin=label, **coverage(a & universe, b & universe, universe), sparse_gt_lt10=len(universe)<10))
        for k in ("gt", "both", "o2o_only", "o2m_only", "neither"):
            assert sum(row[k] for row in result[name]) == coverage(a, b, set(features))[k]
    return result


def nms_cached(raw, image_ids):
    """Bounded to source/reference/night; no raw logits or unselected classes exist."""
    grouped = defaultdict(list)
    for p in raw["predictions"]:
        if p["image_id"] in image_ids:
            grouped[p["image_id"]].append(p)
    retained, suppressions = [], []
    for preds in grouped.values():
        preds.sort(key=lambda p: (-p["score"], p["candidate_id"]))
        boxes = np.asarray([p["bbox"] for p in preds], dtype=np.float64)
        upper = boxes[:, :2] + boxes[:, 2:]
        area = boxes[:, 2] * boxes[:, 3]
        remaining = np.arange(len(preds))
        while len(remaining):
            chosen, rest = remaining[0], remaining[1:]
            retained.append(preds[chosen])
            inter = np.maximum(0., np.minimum(upper[chosen], upper[rest])-np.maximum(boxes[chosen, :2], boxes[rest, :2])).prod(axis=1)
            overlaps = inter/(area[chosen]+area[rest]-inter)
            dropped = rest[overlaps > .70]
            for index in dropped:
                suppressions.append(dict(candidate_id=preds[index]["candidate_id"], suppressed_by=preds[chosen]["candidate_id"], iou=float(overlaps[np.where(rest == index)[0][0]])))
            remaining = rest[overlaps <= .70]
    degenerates = [p for p in raw.get("degenerate_predictions", []) if p["image_id"] in image_ids]
    return dict(schema_version=raw["schema_version"], predictions=retained, degenerate_predictions=degenerates,
                provenance=dict(evaluated_image_ids=sorted(image_ids))), suppressions


def plot_svg(result, path):
    """One measured count chart; values are exact aggregate GT, no private IDs."""
    night = result["panels"]["night"]
    nms = result["cached_nms_approximation"]["panels"]["night"]
    rows = [("Native O2M", night["heads"][HEADS[1]]["operating"]),
            ("Native O2O", night["heads"][HEADS[0]]["operating"]),
            ("Cached O2O NMS: original t", nms["original_threshold"]),
            ("Cached O2O NMS: reselected t", nms["source_reselected"])]
    colors = {"tp": "#167d8d", "fp": "#cf7849"}
    labels = {"tp": "True positives (matched GT)", "fp": "False positives (predictions)"}
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="420" viewBox="0 0 1100 420">',
             '<rect width="1100" height="420" fill="white"/>',
             '<g font-family="Arial,sans-serif" fill="#1f2933">',
             '<text x="24" y="33" font-size="23" font-weight="bold">Cached H4 night: which objects survive same-head NMS?</text>',
             '<text x="24" y="60" font-size="15">All 11 O2O-only operating GT survive cached NMS; 105 eligible GT / 74 images</text>']
    for i, (label, counts) in enumerate(rows):
        y, x = 105+i*62, 330
        parts.append(f'<text x="24" y="{y+22}" font-size="15">{label}</text>')
        for key in colors:
            n = counts[key]
            width = n*6.2
            if n:
                parts.append(f'<rect x="{x:.1f}" y="{y}" width="{width:.1f}" height="33" fill="{colors[key]}"/>')
                parts.append(f'<text x="{x+width/2:.1f}" y="{y+22}" font-size="14" text-anchor="middle" fill="white">{n}</text>')
            x += width
    for i, key in enumerate(colors):
        x = 28+i*400
        parts += [f'<rect x="{x}" y="365" width="16" height="16" fill="{colors[key]}"/>', f'<text x="{x+23}" y="378" font-size="15">{labels[key]}</text>']
    parts.append('<text x="24" y="407" font-size="13">GPT Sol posthoc CPU diagnosis. IoU .70 post-clipping NMS is an approximation, not a native raw-policy swap.</text></g></svg>')
    path.write_text("\n".join(parts)+"\n", encoding="utf-8")


def main(root, private, public):
    start = time.monotonic()
    manifest = read(root / "packet/manifest.json")
    published = read(REPO / "docs/gpt/2026-11-11_sol_dual_head_transfer.json")
    panels = manifest["panels"]
    raw, evs, thresholds, provenance = {}, {}, {}, {}
    for head in HEADS:
        path = root / "results" / (head+"_maximal.json")
        raw[head] = read(path)
        provenance[head] = dict(predictions_sha256=sha(path), status_sha256=sha(root/"results"/(head+"_status.json")))
        thresholds[head] = published["heads"][head]["source_selection"]["threshold"]
        evs[head] = {p: pilot.pilot_evaluator(panels[p], raw[head]) for p in PANELS}
    result = dict(attribution="GPT Sol; new CPU analysis of GPT Sol 2026-11-11 native inference", base="1a8c7833f2369567ba1bf9d10eaf9f1b56259e59",
        status="POSTHOC finite-panel diagnosis; no unseen-test validation; H4 unchanged; G0 pending", definitions=DEFINITIONS,
        provenance=dict(manifest_sha256=sha(root/"packet/manifest.json"), input_heads=provenance,
                        evaluator_sha256=sha(REPO/"src/threshold_transfer/metrics.py"), pilot_wrapper_sha256=sha(pilot.__file__),
                        diagnostic_sha256=sha(__file__), python=sys.version.split()[0], numpy=np.__version__),
        native_thresholds=thresholds, panels={})
    private.mkdir(parents=True, exist_ok=True)
    private_details = {}
    for p in PANELS:
        features = gt_features(panels[p])
        data, private_details[p] = dict(images=len(panels[p]["images"]), gt=len(features), heads={}, coverage={}, strata={}), dict(features=features, matched={})
        for h in HEADS:
            data["heads"][h] = {"operating": point(evs[h][p], thresholds[h]), "ceiling": point(evs[h][p])}
            for label in ("operating", "ceiling"):
                expected = published["heads"][h]["panels"][p][label]
                assert all(data["heads"][h][label][k] == expected[k] for k in ("tp", "fp", "ignored"))
        for label, ceiling in (("operating", False), ("ceiling", True)):
            a, b = [tp_set(evs[h][p], None if ceiling else thresholds[h]) for h in HEADS]
            data["coverage"][label] = coverage(a, b, set(features))
            data["strata"][label] = stratify(features, a, b)
            private_details[p]["matched"][label] = {"o2o": sorted(a), "o2m": sorted(b)}
        matched = private_details[p]["matched"]
        data["operating_extra_other_head_ceiling"] = {}
        for h, other in (("o2o", "o2m"), ("o2m", "o2o")):
            extra = set(matched["operating"][h])-set(matched["operating"][other])
            available = set(matched["ceiling"][other])
            data["operating_extra_other_head_ceiling"][h] = dict(total=len(extra), covered_below_other_threshold=len(extra & available), absent_from_other_ceiling=len(extra-available))
        result["panels"][p] = data
    nms_panels = ("source_selection", "coco_reference", "night")
    image_ids = {i["image_id"] for p in nms_panels for i in panels[p]["images"]}
    nms_raw, suppressions = nms_cached(raw[HEADS[0]], image_ids)
    nms_evs = {p: pilot.pilot_evaluator(panels[p], nms_raw) for p in nms_panels}
    selection = nms_evs["source_selection"].select_threshold(.90)
    t, t_new = thresholds[HEADS[0]], selection["threshold"]
    approx = dict(label="POST-CLIPPING CACHED APPROXIMATION, not native O2M reproduction", iou=.70,
                  source_selection_status=selection["status"], original_threshold=t, reselected_threshold=t_new,
                  suppressed_candidates=len(suppressions), selected_images=len(image_ids), panels={})
    assert t_new is not None, "retain infeasible state rather than evaluating None as a selected threshold"
    for p in nms_panels:
        ev, features = nms_evs[p], private_details[p]["features"]
        before, fixed, reselected, other = tp_set(evs[HEADS[0]][p], t), tp_set(ev, t), tp_set(ev, t_new), tp_set(evs[HEADS[1]][p], thresholds[HEADS[1]])
        extra = before-other
        ceiling_before, ceiling_after = tp_set(evs[HEADS[0]][p]), tp_set(ev)
        data = dict(original_threshold=point(ev, t), source_reselected=point(ev, t_new), ceiling=point(ev),
                    versus_native_o2m={"original_threshold": coverage(fixed, other, set(features)), "source_reselected": coverage(reselected, other, set(features))},
                    native_o2o_extra_gt=len(extra), extra_survive_fixed=len(extra & fixed), extra_lost_fixed=len(extra-fixed),
                    extra_survive_reselection=len(extra & reselected), extra_recovered_by_reselection=len((extra-fixed) & reselected),
                    changed_matched_gt_at_fixed=dict(lost=len(before-fixed), gained=len(fixed-before)),
                    changed_matched_gt_at_ceiling=dict(lost=len(ceiling_before-ceiling_after), gained=len(ceiling_after-ceiling_before)),
                    strata_original_threshold=stratify(features, fixed, other))
        original = result["panels"][p]["heads"][HEADS[0]]["operating"]
        data["direct_plus_boundary_identity"] = {}
        for k in ("tp", "fp"):
            direct = data["original_threshold"][k]-original[k]
            boundary = data["source_reselected"][k]-data["original_threshold"][k]
            total = data["source_reselected"][k]-original[k]
            assert total == direct+boundary
            data["direct_plus_boundary_identity"][k] = dict(direct=direct, boundary=boundary, total=total)
        approx["panels"][p] = data
        private_details[p]["cached_nms"] = dict(original_threshold=sorted(fixed), source_reselected=sorted(reselected), extra_lost_fixed=sorted(extra-fixed))
    result["cached_nms_approximation"] = approx
    write(private / "object_diagnosis.json", private_details)
    write(private / "cached_nms_suppressions.json", suppressions)
    result["execution"] = dict(elapsed_seconds=time.monotonic()-start, native_matching_passes=20, approximate_matching_passes=3, inference_calls=0,
                               private_details_sha256=sha(private/"object_diagnosis.json"), private_suppressions_sha256=sha(private/"cached_nms_suppressions.json"))
    # Public output must contain no per-image/object identifiers or geometry.
    def privacy(value):
        if isinstance(value, dict):
            assert not set(value) & {"image_id", "candidate_id", "annotation_id", "bbox", "matches", "evaluated_image_ids"}
            for child in value.values(): privacy(child)
        elif isinstance(value, list):
            for child in value: privacy(child)
    privacy(result)
    write(public, result)
    plot_svg(result, public.with_suffix(".svg"))
    print(json.dumps(dict(night=result["panels"]["night"], approximation=approx, execution=result["execution"]), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("private", type=Path)
    parser.add_argument("--public", type=Path, default=REPO/"docs/gpt/2026-11-13_sol_mechanism_diagnosis.json")
    args = parser.parse_args()
    main(args.root, args.private, args.public)
