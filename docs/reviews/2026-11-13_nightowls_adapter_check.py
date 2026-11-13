"""Claude Opus independent check of the NightOwls adapter and pilot selection.

Expected values are recomputed from the native JSON without the adapter, then
compared record-by-record with both adapter profiles. Prints aggregates only:
no native IDs, file names, boxes, recording values or tracking values.
Run with PYTHONPATH=src. Writes nothing.
"""

import argparse
import copy
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from threshold_transfer.data import check_roles, load_json, sha256_file
from threshold_transfer.metrics import ReferenceEvaluator
from threshold_transfer.nightowls import PRIMARY_PROFILE, SECONDARY_PROFILE, convert_nightowls
from threshold_transfer.schema import SCHEMA_VERSION

ANNOTATION_SHA = "584c0dc11f0d086fc5bcbaca0385cf2dd9794074f815f2727fbf9a093fd9a9b6"
MANIFEST_SHA = "4f31e685cd3d2d263448e7faf207d80f7befe8c6738b041c3bc4d6614b5de99a"


def expected(doc, profile):
    """Independent restatement of the frozen policy over native records."""
    night = {i["id"]: i for i in doc["images"] if i["daytime"] == "night"}
    rows = {}
    for a in doc["annotations"]:
        if a["image_id"] not in night or (profile == SECONDARY_PROFILE and a["category_id"] != 1):
            continue
        eligible = (a["category_id"] == 1 and a["ignore"] == 0 and a["bbox"][3] >= 50
                    and a["occluded"] is not True)
        rows[f"nightowls:validation:a{a['id']}"] = (f"nightowls:validation:img{a['image_id']}",
                                                     tuple(a["bbox"]), not eligible)
    groups = {f"nightowls:validation:img{i}": (None if r["recordings_id"] is None
                                               else f"nightowls:recording:{int(r['recordings_id'])}")
              for i, r in night.items()}
    return groups, rows


def check_adapter(raw):
    assert sha256_file(raw) == ANNOTATION_SHA
    doc = load_json(raw)
    before = copy.deepcopy(doc)
    out = {"native": {"images": len(doc["images"]), "annotations": len(doc["annotations"]),
                      "daytime": dict(Counter(i["daytime"] for i in doc["images"]))}}
    for profile in (PRIMARY_PROFILE, SECONDARY_PROFILE):
        groups, rows = expected(doc, profile)
        conv = convert_nightowls(doc, profile=profile, source={"sha256": ANNOTATION_SHA})
        assert doc == before, "native document mutated"
        got_groups = {i["image_id"]: i["group_id"] for i in conv["images"]}
        got_rows = {a["annotation_id"]: (a["image_id"], tuple(a["bbox"]), a["ignore"])
                    for a in conv["annotations"]}
        # Geometry identity: same numbers and same Python types (no clipping/float coercion).
        native_boxes = {f"nightowls:validation:a{a['id']}": a["bbox"] for a in doc["annotations"]}
        type_mismatch = sum([type(v) for v in a["bbox"]] != [type(v) for v in native_boxes[a["annotation_id"]]]
                            for a in conv["annotations"])
        outside = sum(a["bbox"][0] < 0 or a["bbox"][1] < 0 or a["bbox"][0] + a["bbox"][2] > 1024
                      or a["bbox"][1] + a["bbox"][3] > 640 for a in conv["annotations"])
        aliased = sum(a["bbox"] is native_boxes[a["annotation_id"]] for a in conv["annotations"])
        cats = Counter(a["attributes"]["native"]["category_id"] for a in conv["annotations"])
        known = {g for g in got_groups.values() if g is not None}
        unknown = {i for i, g in got_groups.items() if g is None}
        per_image = Counter(a["image_id"] for a in conv["annotations"])
        ev = ReferenceEvaluator(conv, {"schema_version": SCHEMA_VERSION, "predictions": [],
                                       "provenance": {"purpose": "construction only"}},
                                **conv["provenance"]["evaluator_policy"])
        roles = {i: "target_test" for i in got_groups}
        held = check_roles(conv, roles, mode="held_out")
        diag = check_roles(conv, roles, mode="diagnostic")
        out[profile] = {
            "images": len(conv["images"]), "records": len(conv["annotations"]),
            "eligible": sum(not r[2] for r in got_rows.values()),
            "ignored": sum(r[2] for r in got_rows.values()),
            "known_groups": len(known), "unknown_group_images": len(unknown),
            "eligible_in_unknown": sum(not r[2] and r[0] in unknown for r in got_rows.values()),
            "eligible_per_known_group_sorted": sorted(Counter(got_groups[r[0]] for r in got_rows.values()
                                                              if not r[2] and got_groups[r[0]]).values()),
            "native_category_counts": {str(k): v for k, v in sorted(cats.items())},
            "images_without_records": sum(per_image[i] == 0 for i in got_groups),
            "group_map_equal_independent": got_groups == groups,
            "records_equal_independent": got_rows == rows,
            "bbox_type_mismatches": type_mismatch, "bbox_aliases_to_native": aliased,
            "outside_frame_records_preserved": outside,
            "all_category_human": all(a["category"] == "human" for a in conv["annotations"]),
            "all_iscrowd_false": all(a["iscrowd"] is False for a in conv["annotations"]),
            "evaluator_policy": conv["provenance"]["evaluator_policy"],
            "evaluator_gt_count": ev.gt_count, "evaluator_images": len(ev.annotations["images"]),
            "held_out_status": held["status"], "held_out_unknown_group_images": held.get("unknown_group_images"),
            "diagnostic_status": diag["status"],
            "summary": conv["provenance"]["summary"],
        }
        del conv, ev
    return out, doc


def check_selection(manifest, doc, seed):
    assert sha256_file(manifest) == MANIFEST_SHA
    sel = json.loads(Path(manifest).read_text(encoding="utf-8"))
    night = [i for i in doc["images"] if i["daytime"] == "night"]
    native = {i["id"]: i for i in doc["images"]}
    buckets = {}
    for i in night:
        buckets.setdefault(i["recordings_id"], []).append(i["id"])
    chosen = [i["id"] for i in sel["images"]]
    # Reproduce: lowest SHA256(seed:id) per bucket, ties by id; 10 per known key, 14 for null.
    reproduced = []
    for key, ids in buckets.items():
        n = 14 if key is None else 10
        reproduced += sorted(ids, key=lambda x: (hashlib.sha256(f"{seed}:{x}".encode()).hexdigest(), x))[:n]
    per_bucket = Counter("null" if native[i]["recordings_id"] is None else "known" for i in chosen)
    return {
        "selected": len(chosen), "unique": len(set(chosen)),
        "selected_records_equal_native": all(native.get(r["id"]) == r for r in sel["images"]),
        "all_night": all(native[i]["daytime"] == "night" for i in chosen),
        "known_keys_covered": len({native[i]["recordings_id"] for i in chosen} - {None}),
        "per_known_key_counts": sorted(Counter(native[i]["recordings_id"] for i in chosen
                                               if native[i]["recordings_id"] is not None).values()),
        "null_bucket_count": per_bucket["null"],
        "reproduced_with_seed_colon_id_rule": sorted(reproduced) == sorted(chosen),
        "unique_file_names_in_selection": len({native[i]["file_name"] for i in chosen}),
        "selected_with_no_native_annotation": sum(
            i not in {a["image_id"] for a in doc["annotations"]} for i in chosen),
        "manifest_has_annotation_or_bbox_fields": any(k in r for r in sel["images"]
                                                     for k in ("bbox", "annotations", "category_id")),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("annotations")
    p.add_argument("--manifest")
    p.add_argument("--seed", default="nightowls-image-access-pilot-2026-11-13-v1")
    args = p.parse_args()
    result, native_doc = check_adapter(Path(args.annotations))
    if args.manifest:
        result["selection"] = check_selection(Path(args.manifest), native_doc, args.seed)
    print(json.dumps(result, indent=1, sort_keys=True))
