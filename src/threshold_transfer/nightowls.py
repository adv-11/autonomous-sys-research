"""GPT Sol's CPU-only NightOwls validation-annotation adapter.

Returned documents contain restricted annotations: keep them private, outside Git.
This is a pedestrian-only descriptive panel, not official SDK scoring. See
docs/decisions/2026-11-13_nightowls_external_policy.md for the frozen choices.
"""

from __future__ import annotations

import copy
from collections import Counter
from typing import Any, Mapping

from .data import PreflightError, _check_box_xywh, _json_value, _native_document
from .schema import SCHEMA_VERSION, validate_documents

EXPECTED_CATEGORIES = {1: "pedestrian", 2: "bicycledriver", 3: "motorbikedriver", 4: "ignore"}
PRIMARY_PROFILE = "person_compatible_ignore"
SECONDARY_PROFILE = "unused_nonpedestrian"
PROFILES = (PRIMARY_PROFILE, SECONDARY_PROFILE)
MATCHING_CATEGORY = "human"


def _integer(value: Any, name: str) -> int:
    if type(value) is not int:
        raise PreflightError(f"{name} must be a native integer")
    return value


def convert_nightowls(doc: Mapping[str, Any], *, profile: str,
                     source: Mapping[str, Any] | None = None) -> dict:
    """Return a canonical-v1 dict without mutating or aliasing the native document.

    Retain every exact ``daytime == 'night'`` frame, including empty/unkeyed ones.
    Eligible GT are category 1, ignore 0, native height >=50, occluded not True.
    Null occlusion follows the SDK convention, not a claim of actual visibility.
    All other pedestrian boxes are ignored; the explicit profile decides whether
    categories 2/3/4 are also ignored or omitted. All retained boxes match ``human``;
    that token does not make riders eligible. No detection filter is applied.

    IDs, image/category references and positive finite geometry are checked even
    for omitted records. Pose/tracking metadata are opaque, not grouping evidence.
    The result requires allow_outside geometry and same_category_ioa matching.
    """
    if profile not in PROFILES:
        raise PreflightError(f"profile must be explicitly one of {PROFILES}")
    _native_document(doc, "nightowls", "validation", source)
    _json_value(doc)
    categories = {}
    for record in doc["categories"]:
        cid = _integer(record.get("id"), "category id")
        if cid in categories:
            raise PreflightError("duplicate native category id")
        categories[cid] = record.get("name")
    if categories != EXPECTED_CATEGORIES:
        raise PreflightError("NightOwls category table differs from the inspected validation table")

    images, by_native = [], {}
    for record in doc["images"]:
        iid = _integer(record.get("id"), "image id")
        if iid in by_native:
            raise PreflightError("duplicate native image id")
        for key in ("width", "height"):
            if _integer(record.get(key), key) <= 0:
                raise PreflightError("image dimensions must be positive")
        if not isinstance(record.get("file_name"), str) or not record["file_name"].strip():
            raise PreflightError("image file_name must be nonempty")
        if not isinstance(record.get("daytime"), str):
            raise PreflightError("image daytime must be explicit")
        if "recordings_id" not in record:
            raise PreflightError("image recordings_id must be explicit, possibly null")
        key = record["recordings_id"]
        if key is not None and (type(key) not in (int, float) or int(key) != key):
            raise PreflightError("recordings_id must be integer-valued or null")
        image = {
            "image_id": f"nightowls:validation:img{iid}", "file_name": record["file_name"],
            "width": record["width"], "height": record["height"], "split": "validation",
            "group_id": None if key is None else f"nightowls:recording:{int(key)}",
            "attributes": {"condition": "night", "dimension_source": "annotation_json",
                           "native": copy.deepcopy(record)},
        }
        by_native[iid] = (record, image)
        if record["daytime"] == "night":
            images.append(image)

    annotations, seen = [], set()
    native_night_counts = Counter()
    for record in doc["annotations"]:
        aid = _integer(record.get("id"), "annotation id")
        if aid in seen:
            raise PreflightError("duplicate native annotation id")
        seen.add(aid)
        iid = _integer(record.get("image_id"), "annotation image_id")
        cid = _integer(record.get("category_id"), "annotation category_id")
        if iid not in by_native or cid not in categories:
            raise PreflightError("unresolved native image/category reference")
        reason = _check_box_xywh(record.get("bbox"))
        if reason:
            raise PreflightError(reason)
        if type(record.get("ignore")) is not int or record["ignore"] not in (0, 1):
            raise PreflightError("native ignore must be integer 0/1")
        if "occluded" not in record or (record["occluded"] is not None
                                          and type(record["occluded"]) is not bool):
            raise PreflightError("native occluded must be boolean or null")
        native_image, image = by_native[iid]
        if native_image["daytime"] != "night":
            continue
        native_night_counts[image["image_id"]] += 1
        if profile == SECONDARY_PROFILE and cid != 1:
            continue
        eligible = (cid == 1 and record["ignore"] == 0 and record["bbox"][3] >= 50
                    and record["occluded"] is not True)
        annotations.append({
            "annotation_id": f"nightowls:validation:a{aid}", "image_id": image["image_id"],
            "category": MATCHING_CATEGORY, "bbox": list(record["bbox"]),
            "ignore": not eligible, "iscrowd": False,
            "attributes": {"native": copy.deepcopy({k: v for k, v in record.items()
                                                     if k != "bbox"})},
        })

    retained_counts = Counter(a["image_id"] for a in annotations)
    result = {
        "schema_version": SCHEMA_VERSION, "images": images, "annotations": annotations,
        "provenance": {
            "dataset": "nightowls", "converter": "threshold_transfer.nightowls.convert_nightowls",
            "role": "validation", "source_files": [copy.deepcopy(dict(source))] if source else [],
            "profile": profile, "policy_status": "provisional",
            "policy_decision": "docs/decisions/2026-11-13_nightowls_external_policy.md",
            "official_evaluator_equivalent": False, "categories": [MATCHING_CATEGORY],
            "native_category_ids": {name: cid for cid, name in EXPECTED_CATEGORIES.items()},
            "target_task": "pedestrian_only; distinct from COCO person and ACDC merged human",
            "matching_category_status": "human is a matching token; riders are never eligible GT",
            "population_policy": "all native daytime==night images; no subsampling or GT deletion",
            "eligibility_policy": "category_id==1, ignore==0, unclipped bbox[3]>=50, occluded is not True",
            "occlusion_policy": "null treated visible by SDK convention; actual visibility unknown",
            "unused_eligibility_flags": ["difficult", "truncated"],
            "ignore_policy": profile,
            "evaluator_policy": {"categories": [MATCHING_CATEGORY],
                                 "ignore_policy": "same_category_ioa", "bounds_policy": "allow_outside"},
            "bounds_policy": "allow_outside", "box_policy": "native xywh; no clipping or repair",
            "matching_policy": "existing eligible-first IoU>=0.50 then reusable ignore IoA>=0.50",
            "detection_filter": "none; SDK 40px detection filter not adopted",
            "iscrowd_policy": "no native crowd flag; false; declared ignore uses reusable IoA regions",
            "group_id_status": "namespaced non-null recording keys; null stays null; independence unverified",
            "panel_status": "external descriptive/diagnostic; not independent held-out or IID validated",
            "pose_status": "opaque unused native attribute; references not validated or repaired",
            "tracking_status": "opaque native attribute; not groups or verified unique people",
            "summary": {
                "image_count": len(images), "annotation_count": len(annotations),
                "eligible_gt_count": sum(not a["ignore"] for a in annotations),
                "ignored_gt_count": sum(a["ignore"] for a in annotations),
                "known_group_count": len({i["group_id"] for i in images} - {None}),
                "images_with_unknown_group": sum(i["group_id"] is None for i in images),
                "empty_image_count": sum(retained_counts[i["image_id"]] == 0 for i in images),
                "native_empty_night_image_count": sum(native_night_counts[i["image_id"]] == 0 for i in images),
                "excluded_non_night_image_count": len(by_native) - len(images),
            },
        },
    }
    validated, _ = validate_documents(
        result, {"schema_version": SCHEMA_VERSION, "predictions": [], "provenance": {}},
        bounds_policy="allow_outside")
    return validated
