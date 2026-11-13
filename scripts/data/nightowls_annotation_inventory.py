"""Annotation-only NightOwls inventory: publish counts, never rows or native IDs."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


def inventory(path):
    payload = path.read_bytes()
    doc = json.loads(payload)
    images, annotations = doc["images"], doc["annotations"]
    by_id = {image["id"]: image for image in images}
    categories = {category["id"]: category["name"] for category in doc["categories"]}
    assert len(by_id) == len(images)
    assert len({a["id"] for a in annotations}) == len(annotations)
    assert all(a["image_id"] in by_id and a["category_id"] in categories for a in annotations)
    pedestrian = next(key for key, value in categories.items() if value == "pedestrian")
    groups = {}
    for image in images:
        groups.setdefault(image["recordings_id"], []).append(image)
    rows = []
    invalid, outside, area_mismatch = 0, 0, 0
    for annotation in annotations:
        x, y, width, height = annotation["bbox"]
        valid = all(math.isfinite(v) for v in (x, y, width, height)) and width > 0 and height > 0
        invalid += not valid
        image = by_id[annotation["image_id"]]
        outside += valid and (x < 0 or y < 0 or x + width > image["width"] or y + height > image["height"])
        area_mismatch += not math.isclose(annotation["area"], width * height, abs_tol=1e-6)
    night_ids = {i["id"] for i in images if i["daytime"] == "night"}
    night_annotations = [a for a in annotations if a["image_id"] in night_ids]
    for ordinal, (_group, members) in enumerate(sorted(groups.items(), key=lambda pair: str(pair[0])), 1):
        selected = {image["id"] for image in members if image["daytime"] == "night"}
        subset = [a for a in night_annotations if a["image_id"] in selected]
        people = [a for a in subset if a["category_id"] == pedestrian and a["ignore"] == 0]
        rows.append(dict(anonymous_recording_slot=ordinal, all_frames=len(members), night_frames=len(selected),
                         native_nonignored_pedestrian_annotations=len(people),
                         night_frames_without_native_nonignored_pedestrians=len(selected - {a["image_id"] for a in people})))
    assert sum(row["night_frames"] for row in rows) == len(night_ids)
    assert sum(row["native_nonignored_pedestrian_annotations"] for row in rows) == sum(
        a["category_id"] == pedestrian and a["ignore"] == 0 for a in night_annotations)
    return dict(attribution="GPT Sol coordinator; actual annotation-only inventory, no images or inference",
        source_sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload), images=len(images),
        annotations=len(annotations), native_categories=categories,
        daytime_counts=dict(Counter(i["daytime"] for i in images)), recording_field="recordings_id",
        recording_count=len(groups), timestamp_types=dict(Counter(type(i["timestamp"]).__name__ for i in images)),
        image_dimensions={f"{w}x{h}": count for (w, h), count in Counter((i["width"], i["height"]) for i in images).items()},
        frames_without_any_annotation=len(set(by_id) - {a["image_id"] for a in annotations}),
        night_frames=len(night_ids), night_annotations=len(night_annotations),
        night_annotation_counts_by_category={categories[key]: count for key, count in Counter(a["category_id"] for a in night_annotations).items()},
        flag_domains={field: dict(Counter(json.dumps(a[field]) for a in annotations)) for field in ("ignore", "difficult", "occluded", "truncated")},
        geometry=dict(nonfinite_or_nonpositive_boxes=invalid, boxes_outside_image=outside,
                      recorded_area_not_equal_bbox_area=area_mismatch, repaired_boxes=0),
        recording_counts=rows,
        limits=["Recording keys are observed units, not independently verified trips/scenes.",
                "Native nonignored pedestrian counts are not a frozen evaluation eligibility policy.",
                "Box extent/visibility/ignore semantics require publisher evidence; coordinates alone do not establish them.",
                "No RGB, image archive/index, detector output, converter or external protocol was acquired or executed."])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("annotations", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.annotations.resolve() == args.output.resolve():
        parser.error("output cannot overwrite the annotation input")
    result = inventory(args.annotations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("source_sha256", "images", "annotations", "night_frames", "recording_count", "recording_counts", "geometry")}))
