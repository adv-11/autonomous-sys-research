"""Independent Claude Opus counts checker for the private NightOwls validation JSON.

Written separately from scripts/data/nightowls_annotation_inventory.py (not imported).
Emits nonrecoverable aggregates only: no file names, image/annotation/track/recording IDs,
timestamps or boxes. SDK-setup counts mirror the *implementation* of ox-vgg/nightowlsapi
python/eval_MR_multisetup.py at ad0f18fc95e093e86036f055ab210a3de46021b7 (height = bbox[3];
vis_ratio = 0.5 if occluded is truthy else 1.0; Reasonable = height>=50 and vis>=0.65;
All = height>=20 and vis>=0.2); they are not an adopted project policy.

Usage: python -I -B this.py PRIVATE_JSON [--inventory docs/datasets/nightowls_validation_inventory.json]
"""
import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

SDK_SETUPS = {"Reasonable": (50, 0.65), "All": (20, 0.2)}


def check(path):
    raw = path.read_bytes()
    doc = json.loads(raw)
    images, anns = doc["images"], doc["annotations"]
    cats = {c["id"]: c["name"] for c in doc["categories"]}
    pose_ids = {p["id"] for p in doc["poses"]}
    img = {i["id"]: i for i in images}
    out = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
           "top_level": sorted(doc), "images": len(images), "annotations": len(anns),
           "categories": {str(k): v for k, v in sorted(cats.items())},
           "pose_vocabulary": {str(p["id"]): p["name"] for p in doc["poses"]}}
    out["integrity"] = {
        "image_ids_unique": len(img) == len(images),
        "annotation_ids_unique": len({a["id"] for a in anns}) == len(anns),
        "image_refs_resolve": all(a["image_id"] in img for a in anns),
        "category_refs_resolve": all(a["category_id"] in cats for a in anns),
        "pose_refs_unresolved": sum(a["pose_id"] not in pose_ids for a in anns),
        "pose_refs_unresolved_by_category": dict(Counter(cats[a["category_id"]] for a in anns if a["pose_id"] not in pose_ids)),
    }
    out["daytime"] = dict(Counter(i["daytime"] for i in images))
    out["dimensions"] = dict(Counter(f'{i["width"]}x{i["height"]}' for i in images))
    rec_types = Counter(type(i["recordings_id"]).__name__ for i in images)
    keys = {i["recordings_id"] for i in images}
    out["recordings"] = {"value_types": dict(rec_types), "distinct_values_including_null": len(keys),
                         "distinct_nonnull_keys": len(keys - {None}),
                         "frames_with_null_key": sum(i["recordings_id"] is None for i in images)}
    key = lambda a: f'{cats[a["category_id"]]}|ignore={a["ignore"]}'
    out["category_x_ignore"] = dict(Counter(key(a) for a in anns))
    out["ignore_flag_equals_category_ignore"] = all((a["ignore"] == 1) == (cats[a["category_id"]] == "ignore") for a in anns)
    out["flags_by_category"] = {f: {f"{cats[c]}|{json.dumps(v)}": n for (c, v), n in sorted(Counter((a["category_id"], a[f]) for a in anns).items(), key=str)}
                                for f in ("difficult", "occluded", "truncated")}
    bad = outside = area_bad = 0
    outside_by_cat = Counter()
    for a in anns:
        x, y, w, h = a["bbox"]
        ok = all(math.isfinite(v) for v in (x, y, w, h)) and w > 0 and h > 0
        bad += not ok
        im = img[a["image_id"]]
        o = ok and (x < 0 or y < 0 or x + w > im["width"] or y + h > im["height"])
        outside += o
        outside_by_cat[cats[a["category_id"]]] += o
        area_bad += not math.isclose(a["area"], w * h, abs_tol=1e-6)
    out["geometry"] = {"nonfinite_or_nonpositive": bad, "outside_image": outside,
                       "outside_by_category": dict(outside_by_cat), "area_ne_w_times_h": area_bad}
    night = {i["id"] for i in images if i["daytime"] == "night"}
    ped = [a for a in anns if cats[a["category_id"]] == "pedestrian" and a["ignore"] == 0]
    nped = [a for a in ped if a["image_id"] in night]

    def sdk_ok(a, setup):
        hmin, vmin = SDK_SETUPS[setup]
        vis = 0.5 if a["occluded"] else 1.0
        return a["bbox"][3] >= hmin and vis >= vmin

    out["night_pedestrian_nonignored"] = {
        "annotations": len(nped), "frames_with_one": len({a["image_id"] for a in nped}),
        "night_frames_without_one": len(night - {a["image_id"] for a in nped}),
        "height_lt_50": sum(a["bbox"][3] < 50 for a in nped), "min_height": min(a["bbox"][3] for a in nped),
        "occluded_null": sum(a["occluded"] is None for a in nped),
        "outside_image": sum(1 for a in nped if (lambda x, y, w, h: x < 0 or y < 0 or x + w > 1024 or y + h > 640)(*a["bbox"])),
        "truncated_true": sum(bool(a["truncated"]) for a in nped),
        **{f"sdk_{s}_eligible": sum(sdk_ok(a, s) for a in nped) for s in SDK_SETUPS}}
    out["frames_without_any_annotation"] = len(set(img) - {a["image_id"] for a in anns})
    slots = []
    for n, k in enumerate(sorted(keys, key=str), 1):  # same ordering rule as the inventory, for comparison only
        members = [i for i in images if i["recordings_id"] == k]
        nid = {i["id"] for i in members if i["daytime"] == "night"}
        p = [a for a in nped if a["image_id"] in nid]
        slots.append({"slot": n, "native_key_is_null": k is None, "all_frames": len(members), "night_frames": len(nid),
                      "nonignored_pedestrians": len(p), "night_frames_without": len(nid - {a["image_id"] for a in p}),
                      "distinct_tracks": len({a["tracking_id"] for a in p}),
                      **{f"sdk_{s}_eligible": sum(sdk_ok(a, s) for a in p) for s in SDK_SETUPS}})
    out["recording_slots"] = slots
    return out


def compare(res, inv):
    exp = {"sha256": inv["source_sha256"], "bytes": inv["bytes"], "images": inv["images"],
           "annotations": inv["annotations"], "frames_without_any_annotation": inv["frames_without_any_annotation"]}
    diffs = [f"{k}: {res[k]} != {v}" for k, v in exp.items() if res[k] != v]
    if res["daytime"] != inv["daytime_counts"]:
        diffs.append("daytime")
    if res["geometry"]["outside_image"] != inv["geometry"]["boxes_outside_image"]:
        diffs.append("outside")
    if res["night_pedestrian_nonignored"]["night_frames_without_one"] != sum(r["night_frames_without_native_nonignored_pedestrians"] for r in inv["recording_counts"]):
        diffs.append("empty night frames")
    for mine, theirs in zip(res["recording_slots"], inv["recording_counts"]):
        pairs = [("all_frames", "all_frames"), ("night_frames", "night_frames"),
                 ("nonignored_pedestrians", "native_nonignored_pedestrian_annotations"),
                 ("night_frames_without", "night_frames_without_native_nonignored_pedestrians")]
        diffs += [f"slot {mine['slot']} {a}" for a, b in pairs if mine[a] != theirs[b]]
    return diffs


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("annotations", type=Path)
    ap.add_argument("--inventory", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    res = check(args.annotations)
    if args.inventory:
        res["inventory_mismatches"] = compare(res, json.loads(args.inventory.read_text(encoding="utf-8")))
    text = json.dumps(res, indent=1, allow_nan=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
