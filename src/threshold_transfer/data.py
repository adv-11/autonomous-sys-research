"""Dependency-light dataset/cache preflight and canonical conversion (Claude implementation).

Scope (see ``docs/claude/data_preflight_implementation.md``):

* read-only inventory of local annotation JSON, KITTI label files, image directories and
  legacy ``{meta, detections}`` prediction caches;
* conversion of COCO-style annotation manifests to the ``threshold-transfer-v1`` canonical
  annotation document defined in ``docs/data_contract.md``;
* conversion of the earlier det-eval-2d compressed prediction cache to the canonical
  prediction document, preserving every evaluated image (including empty ones), the
  original row order through deterministic candidate IDs, and the cache policy;
* a fail-closed group/role check for declared independent splits.

Nothing here repairs coordinates, guesses category IDs, aliases ``person`` to a
pedestrian class, infers group IDs from filenames, or claims official KITTI scoring.
Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import struct
import sys
import tempfile
from collections import Counter, defaultdict
from functools import wraps
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "threshold-transfer-v1"
ROLES = ("source_selection", "clear_test", "target_test")
COCO_IGNORE_POLICIES = {
    # ignore := native iscrowd. A declared research policy, not the official COCOeval rule
    # (COCOeval also uses area ranges and crowd IoA matching inside its own evaluator).
    "coco_iscrowd_v1_provisional",
    # ignore := False everywhere; iscrowd retained. Evaluators must then decide explicitly.
    "no_ignore_declared",
}
KITTI_DIAGNOSTIC_POLICY = "kitti_diagnostic_dontcare_ioa_no_neighbour_images"
KITTI_NATIVE_KEYS = ("kitti_ignore", "ignore_reason", "kitti_difficulty", "occlusion", "truncation")
INVALID_POLICIES = ("reject", "exclude_and_report")
LEGACY_ROW_FIELDS = ["image_id", "x1", "y1", "x2", "y2", "score", "zero_based_vocabulary_index"]


class PreflightError(ValueError):
    """Raised when input violates the contract or a required policy is missing."""


# --------------------------------------------------------------------------- helpers


def canonical_id(value: Any, what: str) -> str:
    """Map a native int/str identifier to a nonempty string. bool/float/None are rejected."""
    if isinstance(value, bool) or value is None:
        raise PreflightError(f"{what}: invalid identifier {value!r}")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and value.strip():
        return value
    raise PreflightError(f"{what}: identifier must be int or nonempty str, got {value!r}")


def _is_number(v: Any) -> bool:
    try:
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
    except OverflowError:
        return False


def _json_value(value: Any) -> None:
    """Validate public dictionaries before any result/file is returned or replaced."""
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, (int, float)):
        if not _is_number(value):
            raise PreflightError("nonfinite or unrepresentable JSON number")
    elif isinstance(value, list):
        for item in value:
            _json_value(item)
    elif isinstance(value, dict) and all(isinstance(k, str) for k in value):
        for item in value.values():
            _json_value(item)
    else:
        raise PreflightError("expected JSON-compatible values with string object keys")


def _report_value(value: Any) -> Any:
    """Make rejected-data examples serializable without repairing any geometry."""
    if isinstance(value, (int, float)) and not isinstance(value, bool) and not _is_number(value):
        return f"rejected-number:{value!r}"
    if isinstance(value, list):
        return [_report_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _report_value(v) for k, v in value.items()}
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return f"rejected-value:{value!r}"


def _checked_result(function):
    @wraps(function)
    def checked(*args, **kwargs):
        result = function(*args, **kwargs)
        _json_value(result)
        return result
    return checked


def _native_document(doc, dataset_tag, split, source):
    if not isinstance(doc, dict):
        raise PreflightError("annotation document must be an object")
    if not isinstance(dataset_tag, str) or not dataset_tag.strip():
        raise PreflightError("dataset_tag must be a nonempty string")
    if split is not None and (not isinstance(split, str) or not split.strip()):
        raise PreflightError("split must be a nonempty string or null")
    if source is not None:
        if not isinstance(source, dict):
            raise PreflightError("source provenance must be an object")
        _json_value(source)
    for key in ("images", "annotations", "categories"):
        if not isinstance(doc.get(key), list) or any(not isinstance(r, dict) for r in doc[key]):
            raise PreflightError(f"{key} must be a list of objects")


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise PreflightError(f"duplicate JSON key: {k}")
            result[k] = v
        return result
    def reject(value):
        raise PreflightError(f"nonstandard JSON constant: {value}")
    try:
        with opener(path, "rt", encoding="utf-8") as f:
            result = json.load(f, object_pairs_hook=unique, parse_constant=reject)
        _json_value(result)
        return result
    except (OSError, ValueError, UnicodeError, OverflowError, RecursionError) as error:
        raise PreflightError(f"cannot read JSON {path.name}: {error}") from error


def _protect_output(path, inputs=(), roots=()):
    destination = Path(path).resolve()
    for source in inputs:
        source = Path(source).resolve()
        if destination == source or (destination.exists() and source.exists() and
                                      os.path.samefile(destination, source)):
            raise PreflightError("output cannot overwrite a consumed input")
    if any(destination.is_relative_to(Path(root).resolve()) for root in roots):
        raise PreflightError("output cannot be inside a protected source asset tree")


def write_json(obj: Any, path: Path, *, protected_inputs=(), protected_roots=()) -> None:
    path = Path(path)
    _protect_output(path, protected_inputs, protected_roots)
    _json_value(obj)
    rendered = json.dumps(obj, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp", delete=False) as f:
            temporary = Path(f.name)
            f.write(rendered)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _decimals(v: float) -> int:
    """Number of decimals in the shortest repr of a float (repr round-trips)."""
    s = repr(float(v))
    if "e" in s or "E" in s:
        return 99
    return len(s.split(".", 1)[1].rstrip("0")) if "." in s else 0


def _check_box_xywh(bbox: Any) -> str | None:
    if not isinstance(bbox, list) or len(bbox) != 4:
        return "bbox_not_length_4"
    if not all(_is_number(v) for v in bbox):
        return "bbox_nonfinite_or_nonnumeric"
    if bbox[2] <= 0 or bbox[3] <= 0:
        return "bbox_nonpositive_width_or_height"
    x, y, w, h = map(float, bbox)
    if not all(math.isfinite(v) for v in (x + w, y + h, w * h)):
        return "bbox_overflowing_extent_or_area"
    if w * h <= 0 or x + w <= x or y + h <= y:
        return "bbox_unrepresentable_positive_extent_or_area"
    return None


def _legacy_bbox(row):
    x1, y1, x2, y2 = map(float, row[1:5])
    box = [x1, y1, x2 - x1, y2 - y1]
    reason = _check_box_xywh(box)
    if reason:
        raise PreflightError(reason)
    return box


def _out_of_bounds(bbox: list[float], width: Any, height: Any) -> bool:
    if not (isinstance(width, int) and isinstance(height, int)):
        return False
    x, y, w, h = bbox
    return x < 0 or y < 0 or x + w > width or y + h > height


# ------------------------------------------------------------ annotation conversion


def _convert_images(doc: Mapping[str, Any], split: str | None) -> tuple[list[dict], dict[str, dict]]:
    if not isinstance(doc.get("images"), list):
        raise PreflightError("annotation document has no 'images' list")
    images, by_id = [], {}
    for rec in doc["images"]:
        iid = canonical_id(rec.get("id"), "image id")
        if iid in by_id:
            raise PreflightError(f"duplicate image id after canonicalisation: {iid!r}")
        w, h = rec.get("width"), rec.get("height")
        for name, v in (("width", w), ("height", h)):
            if v is not None and (not isinstance(v, int) or isinstance(v, bool) or v <= 0):
                raise PreflightError(f"image {iid}: invalid {name} {v!r}")
        out = {
            "image_id": iid,
            "file_name": rec.get("file_name"),
            "width": w,
            "height": h,
            # No verified independent recording/trip/scene IDs exist for COCO/KITTI locally.
            "group_id": None,
            "split": split,
            # No weather/timeofday metadata is fabricated.
            "attributes": {},
        }
        if out["file_name"] is not None and not isinstance(out["file_name"], str):
            raise PreflightError("image file_name must be a string or null")
        images.append(out)
        by_id[iid] = out
    return images, by_id


def _category_names(doc: Mapping[str, Any]) -> dict[Any, str]:
    cats = doc.get("categories")
    if not isinstance(cats, list):
        raise PreflightError("annotation document has no 'categories' list")
    names: dict[Any, str] = {}
    seen = set()
    for c in cats:
        if not isinstance(c, dict):
            raise PreflightError("category record must be an object")
        cid, name = canonical_id(c.get("id"), "category id"), c.get("name")
        if cid in names:
            raise PreflightError(f"duplicate category id {cid!r}")
        if not isinstance(name, str) or not name.strip() or name in seen:
            raise PreflightError(f"category {cid!r}: missing or duplicate name {name!r}")
        names[cid] = name
        seen.add(name)
    return names


def _base_annotations(doc, by_image, cat_names, dataset_tag, invalid_policy, extra_native=()):
    if invalid_policy not in INVALID_POLICIES:
        raise PreflightError(f"invalid_box_policy must be one of {INVALID_POLICIES}")
    if not isinstance(doc.get("annotations"), list):
        raise PreflightError("annotation document has no 'annotations' list")
    out, seen = [], set()
    invalid: Counter = Counter()
    invalid_examples: list[dict] = []
    oob = 0
    for a in doc["annotations"]:
        native_id = canonical_id(a.get("id"), "annotation id")
        aid = f"{dataset_tag}:a{native_id}"
        if aid in seen:
            raise PreflightError(f"duplicate annotation id after canonicalisation: {native_id!r}")
        seen.add(aid)
        iid = canonical_id(a.get("image_id"), f"annotation {native_id} image_id")
        if iid not in by_image:
            raise PreflightError(f"annotation {native_id} references unknown image {iid!r}")
        category_id = canonical_id(a.get("category_id"), f"annotation {native_id} category_id")
        if category_id not in cat_names:
            raise PreflightError(f"annotation {native_id} has unknown category_id {a.get('category_id')!r}")
        iscrowd = a.get("iscrowd", 0)
        if not isinstance(iscrowd, (int, bool)) or iscrowd not in (0, 1):
            raise PreflightError(f"annotation {native_id}: iscrowd {iscrowd!r} not 0/1")
        reason = _check_box_xywh(a.get("bbox"))
        if reason:
            invalid[reason] += 1
            if len(invalid_examples) < 20:
                invalid_examples.append({"annotation_id": aid, "bbox": _report_value(a.get("bbox")), "reason": reason})
            if invalid_policy == "reject":
                raise PreflightError(f"annotation {native_id}: {reason} bbox={a.get('bbox')!r}")
            continue
        img = by_image[iid]
        if _out_of_bounds(a["bbox"], img["width"], img["height"]):
            oob += 1
        native = {"category_id": a.get("category_id")}
        for k in extra_native:
            if k in a:
                native[k] = a[k]
        _json_value(native)
        out.append({
            "annotation_id": aid,
            "image_id": iid,
            "category": cat_names[category_id],
            "bbox": [float(v) for v in a["bbox"]],
            "ignore": False,
            "iscrowd": bool(iscrowd),
            "attributes": {"native": native},
        })
    report = {
        "invalid_box_policy": invalid_policy,
        "invalid_boxes": dict(invalid),
        "invalid_box_examples": invalid_examples,
        "out_of_image_bounds": oob,
        "bounds_policy": "report_only; strict [0,width]x[0,height], tolerance 0; no clipping",
    }
    return out, report


def _summary(images, annotations) -> dict:
    per_image = Counter(a["image_id"] for a in annotations)
    return {
        "image_count": len(images),
        "annotation_count": len(annotations),
        "empty_image_count": sum(1 for i in images if per_image[i["image_id"]] == 0),
        "category_counts": dict(sorted(Counter(a["category"] for a in annotations).items())),
        "ignore_count": sum(a["ignore"] for a in annotations),
        "iscrowd_count": sum(a["iscrowd"] for a in annotations),
        "images_with_unknown_dimensions": sum(1 for i in images if i["width"] is None or i["height"] is None),
        "images_with_unknown_group": sum(1 for i in images if i["group_id"] is None),
    }


@_checked_result
def convert_coco(doc, *, dataset_tag: str, split: str | None, ignore_policy: str,
                 invalid_box_policy: str = "reject", source: Mapping[str, Any] | None = None) -> dict:
    """Convert a plain COCO instances document. Fails closed on KITTI-derived fields."""
    _native_document(doc, dataset_tag, split, source)
    if ignore_policy not in COCO_IGNORE_POLICIES:
        raise PreflightError(f"ignore_policy must be explicitly one of {sorted(COCO_IGNORE_POLICIES)}")
    for a in doc.get("annotations", []):
        if any(k in a for k in ("kitti_ignore", "ignore_reason")):
            raise PreflightError("document carries native KITTI ignore fields; use convert_kitti_derived")
    cat_names = _category_names(doc)
    images, by_id = _convert_images(doc, split)
    anns, report = _base_annotations(doc, by_id, cat_names, dataset_tag, invalid_box_policy, ("area",))
    if ignore_policy == "coco_iscrowd_v1_provisional":
        for a in anns:
            a["ignore"] = a["iscrowd"]
    return {
        "schema_version": SCHEMA_VERSION,
        "images": images,
        "annotations": anns,
        "provenance": {
            "dataset": dataset_tag,
            "converter": "threshold_transfer.data.convert_coco",
            "source": dict(source or {}),
            "policy_status": "provisional",
            "ignore_policy": ignore_policy,
            "official_evaluator_equivalent": False,
            "categories": sorted(cat_names.values()),
            "native_category_ids": {c["name"]: c["id"] for c in doc["categories"]},
            "dropped_native_fields": ["segmentation"],
            "group_id_status": "unknown: no verified independent group metadata",
            "condition_metadata_status": "absent: no weather/timeofday attributes in source",
            "validation": report,
            "summary": _summary(images, anns),
        },
    }


@_checked_result
def convert_kitti_derived(doc, *, dataset_tag: str, split: str | None, policy: str | None,
                          invalid_box_policy: str = "reject",
                          source: Mapping[str, Any] | None = None) -> dict:
    """Convert the det-eval-2d KITTI COCO-style GT under an explicitly diagnostic policy.

    The native evaluator has three ignore kinds with different semantics: DontCare regions
    (IoA, unlimited absorption, copied once per evaluated class), neighbour classes
    (Van->Car, Person_sitting->Pedestrian; IoU, one-to-one absorption) and difficulty
    filtering. A generic ignore flag cannot represent the latter two, so canonical
    conversion is blocked unless the caller selects the labelled diagnostic subset policy:
    images containing any neighbour record are removed, DontCare becomes ``ignore=True``
    (same-category IoA in the evaluator), and no difficulty filter is applied.
    """
    _native_document(doc, dataset_tag, split, source)
    if policy != KITTI_DIAGNOSTIC_POLICY:
        raise PreflightError(
            "KITTI native ignore semantics (DontCare IoA, neighbour-class IoU one-to-one, "
            "difficulty filtering) cannot be expressed as one generic ignore flag; canonical "
            f"conversion is blocked. Pass policy={KITTI_DIAGNOSTIC_POLICY!r} for the explicitly "
            "non-official diagnostic subset."
        )
    cat_names = _category_names(doc)
    images, by_id = _convert_images(doc, split)
    # Policy population exclusions must survive a record's invalid-box exclusion.
    neighbour_images: set[str] = set()
    for native in doc["annotations"]:
        iid = canonical_id(native.get("image_id"), "KITTI image_id")
        if iid not in by_id:
            raise PreflightError(f"KITTI record references unknown image {iid!r}")
        if any(k not in native for k in ("kitti_ignore", "ignore_reason")):
            raise PreflightError("KITTI record missing native ignore fields")
        kig, crowd, reason = native["kitti_ignore"], native.get("iscrowd", 0), native["ignore_reason"]
        if any(not isinstance(flag, (int, bool)) or flag not in (0, 1) for flag in (kig, crowd)):
            raise PreflightError("KITTI ignore flags must be native 0/1 booleans")
        if reason is None:
            if kig or crowd:
                raise PreflightError("KITTI ignore flag without ignore_reason")
        elif reason == "dontcare":
            if not kig or not crowd:
                raise PreflightError("KITTI dontcare record flags inconsistent")
        elif isinstance(reason, str) and reason.startswith("neighbour:"):
            if crowd or not kig:
                raise PreflightError("KITTI neighbour record flags inconsistent")
            neighbour_images.add(iid)
        else:
            raise PreflightError(f"unsupported native ignore_reason {reason!r}")
    anns, report = _base_annotations(doc, by_id, cat_names, dataset_tag, invalid_box_policy,
                                     KITTI_NATIVE_KEYS + ("area",))
    kinds: Counter = Counter()
    for a in anns:
        n = a["attributes"]["native"]
        missing = [k for k in ("kitti_ignore", "ignore_reason") if k not in n]
        if missing:
            raise PreflightError(f"{a['annotation_id']}: missing native KITTI fields {missing}")
        reason = n["ignore_reason"]
        if reason is None:
            if n["kitti_ignore"] or a["iscrowd"]:
                raise PreflightError(f"{a['annotation_id']}: ignore flag without ignore_reason")
            kinds["eligible_native_class"] += 1
        elif reason == "dontcare":
            if not a["iscrowd"]:
                raise PreflightError(f"{a['annotation_id']}: dontcare record without iscrowd=1")
            kinds["dontcare_per_class_copy"] += 1
            a["ignore"] = True
        elif isinstance(reason, str) and reason.startswith("neighbour:"):
            if a["iscrowd"] or not n["kitti_ignore"]:
                raise PreflightError(f"{a['annotation_id']}: neighbour record flags inconsistent")
            kinds[reason] += 1
            neighbour_images.add(a["image_id"])
        else:
            raise PreflightError(f"{a['annotation_id']}: unsupported native ignore_reason {reason!r}")
    kept_images = [i for i in images if i["image_id"] not in neighbour_images]
    kept_anns = [a for a in anns if a["image_id"] not in neighbour_images]
    return {
        "schema_version": SCHEMA_VERSION,
        "images": kept_images,
        "annotations": kept_anns,
        "provenance": {
            "dataset": dataset_tag,
            "converter": "threshold_transfer.data.convert_kitti_derived",
            "source": dict(source or {}),
            "policy_status": "diagnostic",
            "ignore_policy": KITTI_DIAGNOSTIC_POLICY,
            "official_kitti_equivalent": False,
            "official_evaluator_equivalent": False,
            "limitations": [
                "Images containing neighbour-class records (Van for Car, Person_sitting for "
                "Pedestrian) are excluded because their IoU one-to-one ignore rule is not "
                "representable; the remaining population is a non-random, scene-dependent subset.",
                "DontCare regions are retained once per evaluated class (native derived layout) "
                "with ignore=True; intended for same-category intersection/prediction-area rules.",
                "No difficulty filter (easy/moderate/hard) is applied; native kitti_difficulty, "
                "occlusion and truncation are preserved in attributes.native only.",
                "KITTI minimum-height detection filtering and per-class IoU thresholds are not "
                "applied. Results are development diagnostics, never official KITTI scores.",
                "The derived JSON and its earlier results are previously inspected development "
                "data, not an untouched confirmatory test.",
            ],
            "categories": sorted(cat_names.values()),
            "native_category_ids": {c["name"]: c["id"] for c in doc["categories"]},
            "native_record_kinds_before_exclusion": dict(kinds),
            "excluded_neighbour_image_count": len(neighbour_images),
            "excluded_neighbour_image_ids": sorted(neighbour_images, key=_id_sort_key),
            "group_id_status": "unknown: KITTI raw-drive mapping files are not present locally",
            "condition_metadata_status": "absent: no weather/timeofday attributes in source",
            "validation": report,
            "summary": _summary(kept_images, kept_anns),
        },
    }


def _id_sort_key(s: str):
    return (0, int(s), s) if s.isdigit() else (1, 0, s)


# ------------------------------------------------------------ legacy prediction cache


def _legacy_meta(cache: Mapping[str, Any]) -> tuple[dict, list[str], list[str]]:
    if not isinstance(cache, Mapping) or set(cache) != {"meta", "detections"}:
        raise PreflightError("legacy cache must be exactly {meta, detections}")
    meta = cache["meta"]
    if not isinstance(meta, dict):
        raise PreflightError("legacy meta must be an object")
    _json_value(meta)
    if not isinstance(cache["detections"], list):
        raise PreflightError("legacy 'detections' must be a list of rows")
    for k in ("image_ids", "vocabulary", "detector"):
        if k not in meta:
            raise PreflightError(f"legacy meta missing {k!r}")
    if not isinstance(meta["image_ids"], list) or not isinstance(meta["detector"], dict):
        raise PreflightError("legacy image_ids must be a list and detector an object")
    ids = [canonical_id(i, "meta image id") for i in meta["image_ids"]]
    if len(set(ids)) != len(ids):
        raise PreflightError("duplicate image ids in legacy meta after canonicalisation")
    if meta.get("num_images") is not None and (
            isinstance(meta["num_images"], bool) or not isinstance(meta["num_images"], int)
            or meta["num_images"] != len(ids)):
        raise PreflightError(f"meta num_images {meta['num_images']} != len(image_ids) {len(ids)}")
    vocab = meta["vocabulary"]
    if not isinstance(vocab, list) or not all(isinstance(v, str) and v.strip() for v in vocab):
        raise PreflightError("legacy vocabulary must be a list of nonempty strings")
    # Duplicate names occur in real caches (torchvision's 91-slot COCO list has ten 'N/A'
    # placeholders). They are tolerated only while unmapped; see convert_legacy_predictions.
    return meta, ids, vocab


def duplicate_vocabulary(vocab: list[str]) -> dict[str, list[int]]:
    pos: dict[str, list[int]] = defaultdict(list)
    for i, v in enumerate(vocab):
        pos[v].append(i)
    return {k: v for k, v in pos.items() if len(v) > 1}


def cache_policy(meta: Mapping[str, Any]) -> dict:
    det = meta.get("detector", {})
    if not isinstance(det, dict):
        raise PreflightError("detector metadata must be an object")
    floor, cap = det.get("score_thresh"), det.get("max_raw_det")
    if floor is not None and (not _is_number(floor) or not 0 <= floor <= 1):
        raise PreflightError("invalid detector score floor")
    if cap is not None and (isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0):
        raise PreflightError("invalid detector raw candidate cap")
    return {
        "score_floor": det.get("score_thresh"),
        "max_raw_det_per_image": det.get("max_raw_det"),
        "max_eval_det_not_applied": det.get("max_eval_det"),
        "nms_iou": det.get("nms_iou"),
        "nms_multi_label": det.get("nms_multi_label"),
        # det-eval-2d scripts/run_inference.py@39c6f6d: round(v, 2) coords, round(s, 5) scores.
        "coordinate_decimals": 2,
        "score_decimals": 5,
        "rounding_source": "det-eval-2d scripts/run_inference.py line 115 at 39c6f6d",
        "censoring": "candidate ceiling is conditional on this floor, cap and rounding",
    }


def scan_legacy_rows(cache: Mapping[str, Any]) -> dict:
    """Validate every legacy row; return aggregate statistics and per-row invalid reasons."""
    meta, ids, vocab = _legacy_meta(cache)
    id_set = set(ids)
    pol = cache_policy(meta)
    reasons: Counter = Counter()
    bad: dict[int, str] = {}
    per_image: Counter = Counter()
    dup = duplicate_vocabulary(vocab)
    dup_index = {i for idxs in dup.values() for i in idxs}
    dup_rows = 0
    below_floor = coord_excess = score_excess = 0
    for idx, row in enumerate(cache["detections"]):
        r = None
        if not isinstance(row, list) or len(row) != 7:
            r = "row_not_length_7"
        else:
            iid, x1, y1, x2, y2, s, lab = row
            try:
                iid_c = canonical_id(iid, "row image id")
            except PreflightError:
                iid_c = None
            if iid_c is None:
                r = "image_id_invalid"
            elif iid_c not in id_set:
                r = "image_id_not_in_meta"
            elif not all(_is_number(v) for v in (x1, y1, x2, y2)):
                r = "coordinate_nonfinite_or_nonnumeric"
            elif not _is_number(s) or not 0.0 <= s <= 1.0:
                r = "score_nonfinite_or_outside_0_1"
            elif isinstance(lab, bool) or not isinstance(lab, int) or not 0 <= lab < len(vocab):
                r = "vocabulary_index_invalid"
            elif x2 <= x1 or y2 <= y1:
                r = "box_zero_or_reversed"
            else:
                try:
                    _legacy_bbox(row)
                except (PreflightError, OverflowError) as error:
                    r = f"box_not_representable:{error}"
            if r is None:
                per_image[iid_c] += 1
                dup_rows += lab in dup_index
                if pol["score_floor"] is not None and s < pol["score_floor"]:
                    below_floor += 1
                if any(_decimals(v) > pol["coordinate_decimals"] for v in (x1, y1, x2, y2)):
                    coord_excess += 1
                if _decimals(s) > pol["score_decimals"]:
                    score_excess += 1
        if r:
            reasons[r] += 1
            bad[idx] = r
    cap = pol["max_raw_det_per_image"]
    counts = [per_image[i] for i in ids]
    return {
        "row_count": len(cache["detections"]),
        "valid_row_count": len(cache["detections"]) - len(bad),
        "invalid_rows": dict(reasons),
        "invalid_row_indices": bad,
        "evaluated_image_count": len(ids),
        "empty_output_image_count": sum(1 for c in counts if c == 0),
        "max_rows_per_image": max(counts, default=0),
        "images_at_cap": sum(1 for c in counts if cap is not None and c == cap),
        "images_over_cap": sum(1 for c in counts if cap is not None and c > cap),
        "rows_below_score_floor": below_floor,
        "rows_exceeding_coordinate_rounding": coord_excess,
        "rows_exceeding_score_rounding": score_excess,
        "duplicate_vocabulary_names": dup,
        "rows_with_duplicate_vocabulary_name": dup_rows,
        "label_index_histogram": {str(k): v for k, v in sorted(Counter(
            r[6] for i, r in enumerate(cache["detections"]) if i not in bad).items())},
        "cache_policy": pol,
    }


@_checked_result
def convert_legacy_predictions(cache, *, category_mapping: Mapping[str, str],
                               annotations: Mapping[str, Any] | None = None,
                               restrict_to_manifest: bool = False,
                               invalid_row_policy: str = "reject",
                               source: Mapping[str, Any] | None = None) -> dict:
    """Convert {meta, detections} rows [image_id,x1,y1,x2,y2,score,vocab_index] to canonical.

    ``category_mapping`` maps vocabulary names to native annotation category names and must
    be explicit; unmapped vocabulary rows are dropped and counted. Candidate IDs are
    ``<run>:<zero-padded original row index>`` so (score desc, id asc) keeps original order.
    """
    if invalid_row_policy not in INVALID_POLICIES:
        raise PreflightError(f"invalid_row_policy must be one of {INVALID_POLICIES}")
    if not isinstance(category_mapping, Mapping) or not category_mapping:
        raise PreflightError("an explicit, nonempty category_mapping is required")
    if any(not isinstance(k, str) or not k.strip() for k in category_mapping):
        raise PreflightError("category_mapping keys must be nonempty strings")
    if source is not None:
        if not isinstance(source, dict):
            raise PreflightError("source provenance must be an object")
        _json_value(source)
    meta, ids, vocab = _legacy_meta(cache)
    unknown_keys = sorted(set(category_mapping) - set(vocab))
    if unknown_keys:
        raise PreflightError(f"category_mapping keys not in cache vocabulary: {unknown_keys}")
    ambiguous = sorted(set(category_mapping) & set(duplicate_vocabulary(vocab)))
    if ambiguous:
        raise PreflightError(f"category_mapping keys are duplicated in the vocabulary (ambiguous): {ambiguous}")
    for k, v in category_mapping.items():
        if not isinstance(v, str) or not v.strip():
            raise PreflightError(f"category_mapping[{k!r}] must be a nonempty category name")
    if annotations is not None:
        if (not isinstance(annotations, dict) or not isinstance(annotations.get("images"), list)
                or not isinstance(annotations.get("annotations"), list)
                or not isinstance(annotations.get("provenance"), dict)):
            raise PreflightError("annotations must be a canonical manifest")
        _json_value(annotations)
        manifest_ids = [canonical_id(i.get("image_id"), "manifest image_id") for i in annotations["images"]]
        if len(set(manifest_ids)) != len(manifest_ids):
            raise PreflightError("duplicate manifest image_id")
        cats = set(annotations.get("provenance", {}).get("categories") or
                   {a["category"] for a in annotations["annotations"]})
        missing = sorted(set(category_mapping.values()) - cats)
        if missing:
            raise PreflightError(f"mapping targets absent from annotation categories: {missing}")
    run = meta.get("run")
    if not isinstance(run, str) or not run.strip():
        raise PreflightError("legacy meta needs a nonempty 'run' to namespace candidate IDs")
    scan = scan_legacy_rows(cache)
    bad = scan.pop("invalid_row_indices")
    if bad and invalid_row_policy == "reject":
        first = min(bad)
        raise PreflightError(f"invalid legacy row {first}: {bad[first]} ({len(bad)} invalid rows)")

    evaluated = list(ids)
    restriction = None
    if annotations is not None:
        manifest_ids = [i["image_id"] for i in annotations["images"]]
        mset, eset = set(manifest_ids), set(ids)
        if restrict_to_manifest:
            not_evaluated = sorted(mset - eset, key=_id_sort_key)
            if not_evaluated:
                raise PreflightError(f"{len(not_evaluated)} manifest images were never evaluated "
                                     f"by this cache, e.g. {not_evaluated[:5]}")
            evaluated = [i for i in ids if i in mset]
        elif mset != eset:
            raise PreflightError(f"cache image set differs from manifest ({len(eset - mset)} extra, "
                                 f"{len(mset - eset)} missing); pass restrict_to_manifest explicitly")
    elif restrict_to_manifest:
        raise PreflightError("restrict_to_manifest requires an annotation manifest")
    keep = set(evaluated)

    width = len(str(max(len(cache["detections"]) - 1, 0)))
    preds = []
    dropped_unmapped: Counter = Counter()
    excluded_rows = 0
    for idx, row in enumerate(cache["detections"]):
        if idx in bad:
            continue
        iid = canonical_id(row[0], "row image id")
        if iid not in keep:
            excluded_rows += 1
            continue
        name = vocab[row[6]]
        if name not in category_mapping:
            dropped_unmapped[name] += 1
            continue
        preds.append({
            "candidate_id": f"{run}:{idx:0{width}d}",
            "image_id": iid,
            "category": category_mapping[name],
            "bbox": _legacy_bbox(row),
            "score": float(row[5]),
        })
    if annotations is not None and restrict_to_manifest:
        restriction = {
            "annotation_manifest_canonical_json_sha256": hashlib.sha256(
                json.dumps(annotations, sort_keys=True, allow_nan=False).encode()).hexdigest(),
            "excluded_image_count": len(ids) - len(evaluated),
            "excluded_row_count": excluded_rows,
        }
    oob = None
    if annotations is not None:
        dims = {i["image_id"]: (i.get("width"), i.get("height")) for i in annotations["images"]}
        oob = sum(1 for p in preds if _out_of_bounds(p["bbox"], *dims[p["image_id"]]))
    ties = Counter((p["image_id"], p["category"], p["score"]) for p in preds)
    tie_groups = [c for c in ties.values() if c > 1]
    det_meta = {k: v for k, v in meta.items() if k != "image_ids"}
    return {
        "schema_version": SCHEMA_VERSION,
        "predictions": preds,
        "provenance": {
            "converter": "threshold_transfer.data.convert_legacy_predictions",
            "source": dict(source or {}),
            "run": run,
            "dataset": meta.get("dataset"),
            "split": meta.get("split"),
            "evaluated_image_ids": evaluated,
            "legacy_meta_without_image_ids": det_meta,
            "row_schema": LEGACY_ROW_FIELDS,
            "candidate_id_rule": f"'{run}:' + original row index zero-padded to {width} digits",
            "bbox_rule": "[x1, y1, x2-x1, y2-y1] in float; no rounding, clipping or repair",
            "cache_policy": scan["cache_policy"],
            "category_mapping": dict(category_mapping),
            "category_mapping_status": "explicit caller declaration; not inferred",
            "dropped_unmapped_rows": dict(sorted(dropped_unmapped.items())),
            "invalid_row_policy": invalid_row_policy,
            "population_restriction": restriction,
            "same_image_category_score_tie_groups": len(tie_groups),
            "max_tie_group_size": max(tie_groups, default=1),
            "scalar_score_limitation": "scalar scores only; full-vector OCE not reconstructible",
            "validation": scan,
            "prediction_count": len(preds),
            "predictions_outside_known_image_bounds": oob,
        },
    }


# ------------------------------------------------------------------ group/role check


@_checked_result
def check_roles(manifest: Mapping[str, Any], roles: Mapping[str, str], *, mode: str) -> dict:
    """Check an image->role assignment against manifest group IDs.

    ``mode='held_out'`` declares independent splits: fails on any unknown group, any group
    spanning roles, or unknown images. ``mode='diagnostic'`` tolerates unknown groups but
    still fails on known groups spanning roles and never reports independence.
    """
    if mode not in ("held_out", "diagnostic"):
        raise PreflightError("mode must be 'held_out' or 'diagnostic'")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("images"), list):
        raise PreflightError("role manifest must have an images list")
    if not isinstance(roles, Mapping):
        raise PreflightError("role assignments must be an object")
    groups = {}
    for image in manifest["images"]:
        if not isinstance(image, dict):
            raise PreflightError("role image must be an object")
        iid = image.get("image_id")
        if not isinstance(iid, str):
            raise PreflightError("canonical role image_id must be a nonempty string")
        canonical_id(iid, "role image_id")
        if iid in groups:
            raise PreflightError(f"duplicate role image_id: {iid}")
        group = image.get("group_id")
        if group is not None and (not isinstance(group, str) or not group.strip()):
            raise PreflightError("group_id must be a nonempty string or null")
        groups[iid] = group
    for iid, role in roles.items():
        if not isinstance(iid, str) or not iid.strip() or not isinstance(role, str):
            raise PreflightError("role assignment keys/values must be strings with nonempty IDs")
    errors: list[str] = []
    if not roles:
        errors.append("empty assignment cannot establish role consistency")
    bad_roles = sorted({r for r in roles.values() if r not in ROLES})
    if bad_roles:
        errors.append(f"unknown roles {bad_roles}; allowed {list(ROLES)}")
    unknown_images = sorted(set(roles) - set(groups), key=_id_sort_key)
    if unknown_images:
        errors.append(f"{len(unknown_images)} assigned images absent from manifest")
    group_roles: dict[Any, set] = defaultdict(set)
    unknown_group_images = 0
    for iid, role in roles.items():
        if iid not in groups:
            continue
        g = groups[iid]
        if g is None:
            unknown_group_images += 1
        else:
            group_roles[g].add(role)
    spanning = sorted(str(g) for g, rs in group_roles.items() if len(rs) > 1)
    if spanning:
        errors.append(f"{len(spanning)} groups span multiple roles, e.g. {spanning[:5]}")
    if unknown_group_images and mode == "held_out":
        errors.append(f"{unknown_group_images} assigned images have unknown group_id; "
                      "independence cannot be declared")
    status = "FAIL" if errors else ("PASS" if mode == "held_out" else "DIAGNOSTIC_ONLY")
    return {
        "mode": mode,
        "status": status,
        "independent_split_declared": False,
        "declared_groups_consistent": status == "PASS",
        "errors": errors,
        "role_counts": dict(Counter(roles.values())),
        "unknown_group_images": unknown_group_images,
        "known_group_count": len(group_roles),
        "limitations": ["Consistency checks on declared groups only; independent grouping provenance "
                        "requires external evidence. No verified independence claim is made."],
    }


# ------------------------------------------------------------------------ inventory


def image_dimensions(path: Path) -> tuple[int, int] | None:
    """Read PNG IHDR or JPEG SOF dimensions with the stdlib; None if unrecognised."""
    with open(path, "rb") as f:
        head = f.read(26)
        if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
            return struct.unpack(">II", head[16:24])
        if head[:2] != b"\xff\xd8":
            return None
        f.seek(2)
        while True:
            b = f.read(1)
            while b and b != b"\xff":
                b = f.read(1)
            while b == b"\xff":
                b = f.read(1)
            if not b:
                return None
            marker = b[0]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                continue
            seg = f.read(2)
            if len(seg) < 2:
                return None
            length = struct.unpack(">H", seg)[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                data = f.read(5)
                h, w = struct.unpack(">HH", data[1:5])
                return w, h
            f.seek(length - 2, 1)


def directory_listing_digest(directory: Path, suffix: str) -> dict:
    files = sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lower() == suffix)
    h = hashlib.sha256()
    total = 0
    for p in files:
        size = p.stat().st_size
        total += size
        h.update(f"{p.name}\t{size}\n".encode())
    return {"file_count": len(files), "total_bytes": total,
            "name_size_listing_sha256": h.hexdigest(),
            "digest_rule": "sha256 over sorted 'name<TAB>size<LF>' lines; not a content hash"}


def parse_kitti_labels(label_dir: Path, stems: Iterable[str] | None = None) -> dict:
    files = sorted(label_dir.glob("*.txt"))
    if stems is not None:
        wanted = set(stems)
        files = [p for p in files if p.stem in wanted]
    classes: Counter = Counter()
    malformed = 0
    reversed_boxes = 0
    empty = 0
    for p in files:
        lines = [ln.split() for ln in p.read_text().splitlines() if ln.strip()]
        if not lines:
            empty += 1
        for parts in lines:
            if len(parts) not in (15, 16):
                malformed += 1
                continue
            classes[parts[0]] += 1
            x1, y1, x2, y2 = (float(v) for v in parts[4:8])
            if x2 <= x1 or y2 <= y1:
                reversed_boxes += 1
    return {"label_file_count": len(files), "object_lines_by_class": dict(sorted(classes.items())),
            "malformed_lines": malformed, "zero_or_reversed_boxes": reversed_boxes,
            "empty_label_files": empty}


def inventory(config_path: Path, *, dims: bool = False, hash_weights: bool = True,
              asset_root: Path | None = None) -> dict:
    """Read-only inventory of the local assets named in a local_assets config."""
    config_path = Path(config_path).resolve()
    cfg = load_json(config_path)
    repo_root = config_path.parent.parent
    root = Path(asset_root).resolve() if asset_root else (repo_root / cfg["asset_root"]).resolve()
    rel = lambda key: root / cfg[key]  # noqa: E731
    out: dict[str, Any] = {"schema": "threshold-transfer-inventory-v1", "asset_root_name": root.name,
                           "config": cfg, "files": {}, "notes": []}

    coco_path = rel("coco_annotations")
    coco = load_json(coco_path)
    coco_img_dir = rel("coco_images")
    out["files"]["coco_annotations"] = {"sha256": sha256_file(coco_path), "bytes": coco_path.stat().st_size}
    conv = convert_coco(coco, dataset_tag="coco-val2017", split="val2017",
                        ignore_policy="coco_iscrowd_v1_provisional", invalid_box_policy="exclude_and_report")
    on_disk = {p.name for p in coco_img_dir.glob("*.jpg")}
    names = {i["file_name"] for i in conv["images"]}
    coco_sec = {
        "top_level_keys": sorted(coco),
        "info": coco.get("info"),
        "category_count": len(coco["categories"]),
        "categories": [c["name"] for c in coco["categories"]],
        "native_human_categories": [c["name"] for c in coco["categories"] if c.get("supercategory") == "person"],
        "pedestrian_category_present": any(c["name"].lower() == "pedestrian" for c in coco["categories"]),
        "summary": conv["provenance"]["summary"],
        "validation": conv["provenance"]["validation"],
        "image_dir": directory_listing_digest(coco_img_dir, ".jpg"),
        "manifest_images_missing_on_disk": len(names - on_disk),
        "disk_images_not_in_manifest": len(on_disk - names),
        "native_ignore_semantics": "iscrowd (RLE/polygon crowd regions); COCOeval matches crowd by "
                                   "IoA with unlimited absorption, plus area ranges",
        "group_id_status": "unknown", "condition_metadata": "absent",
    }
    if dims:
        mism = unread = 0
        for i in conv["images"]:
            d = image_dimensions(coco_img_dir / i["file_name"])
            if d is None:
                unread += 1
            elif d != (i["width"], i["height"]):
                mism += 1
        coco_sec["dimension_audit"] = {"checked": len(conv["images"]), "mismatches": mism, "unreadable": unread,
                                       "method": "stdlib JPEG SOF header parse"}
    out["coco"] = coco_sec

    kitti_img_dir, kitti_lbl_dir = rel("kitti_images"), rel("kitti_labels")
    kd_path = rel("kitti_derived_val_annotations")
    kd = load_json(kd_path)
    out["files"]["kitti_derived_val_annotations"] = {"sha256": sha256_file(kd_path), "bytes": kd_path.stat().st_size}
    split_dir = root / "configs" / "kitti_split"
    splits = {s: (split_dir / f"{s}.txt").read_text().split() for s in ("train", "val")
              if (split_dir / f"{s}.txt").exists()}
    for s in splits:
        out["files"][f"kitti_split_{s}"] = {"sha256": sha256_file(split_dir / f"{s}.txt"), "lines": len(splits[s])}
    val_stems = splits.get("val")
    raw_val = parse_kitti_labels(kitti_lbl_dir, val_stems) if val_stems else None
    reasons = Counter(a.get("ignore_reason") for a in kd["annotations"])
    zero_derived = sum(1 for a in kd["annotations"] if _check_box_xywh(a.get("bbox")))
    try:
        convert_kitti_derived(kd, dataset_tag="kitti-val-derived", split="kitti-val", policy=None)
        blocked = None
    except PreflightError as e:
        blocked = str(e)
    diag = convert_kitti_derived(kd, dataset_tag="kitti-val-derived", split="kitti-val",
                                 policy=KITTI_DIAGNOSTIC_POLICY, invalid_box_policy="exclude_and_report")
    dc_raw = raw_val["object_lines_by_class"].get("DontCare", 0) if raw_val else None
    kitti_sec = {
        "image_dir": directory_listing_digest(kitti_img_dir, ".png"),
        "label_dir_file_count": len(list(kitti_lbl_dir.glob("*.txt"))),
        "raw_labels_all": parse_kitti_labels(kitti_lbl_dir),
        "split_files": {s: len(v) for s, v in splits.items()},
        "split_overlap": len(set(splits.get("train", [])) & set(splits.get("val", []))),
        "split_origin": "earlier project's own random image split; not grouped by raw drive",
        "raw_labels_val": raw_val,
        "derived_val": {
            "top_level_keys": sorted(kd), "info": kd.get("info"),
            "categories": [c["name"] for c in kd["categories"]],
            "image_count": len(kd["images"]), "annotation_record_count": len(kd["annotations"]),
            "ignore_reason_counts": {str(k): v for k, v in reasons.items()},
            "invalid_bbox_records": zero_derived,
            "dontcare_copies_per_raw_region": (reasons.get("dontcare", 0) / dc_raw) if dc_raw else None,
            "difficulty_counts": {str(k): v for k, v in Counter(
                a.get("kitti_difficulty") for a in kd["annotations"] if a.get("ignore_reason") is None).items()},
        },
        "canonical_default_conversion": {"blocked": blocked is not None, "reason": blocked},
        "diagnostic_conversion": {k: diag["provenance"][k] for k in (
            "ignore_policy", "official_kitti_equivalent", "excluded_neighbour_image_count",
            "native_record_kinds_before_exclusion", "validation", "summary")},
        "native_ignore_semantics": {
            "DontCare": "region; IoA vs detection area; unlimited absorption; copied per evaluated class",
            "neighbour": "Van->Car, Person_sitting->Pedestrian; IoU; absorbs at most one detection",
            "difficulty": "objects failing level become IoU one-to-one ignores at evaluation time",
            "Truck/Tram/Misc": "not evaluated; detections on them remain FPs",
        },
        "group_id_status": "unknown: train_mapping.txt / train_rand.txt drive mapping not found locally",
        "condition_metadata": "absent",
    }
    if dims:
        mism = 0
        for i in kd["images"]:
            d = image_dimensions(kitti_img_dir / i["file_name"])
            if d != (i["width"], i["height"]):
                mism += 1
        kitti_sec["dimension_audit"] = {"checked": len(kd["images"]), "mismatches": mism,
                                        "method": "stdlib PNG IHDR parse"}
    out["kitti"] = kitti_sec

    cache_dir = rel("legacy_predictions")
    caches = []
    for p in sorted(cache_dir.glob("*.json.gz")):
        c = load_json(p)
        scan = scan_legacy_rows(c)
        scan.pop("invalid_row_indices")
        m = c["meta"]
        caches.append({
            "file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size,
            "run": m.get("run"), "dataset": m.get("dataset"), "split": m.get("split"),
            "vocab_key": m.get("vocab_key"), "vocabulary_size": len(m.get("vocabulary", [])),
            "vocabulary_head": m.get("vocabulary", [])[:3],
            "weights": m.get("weights"), "detector_name": m.get("detector", {}).get("name"),
            "checkpoint": m.get("detector", {}).get("checkpoint"),
            "scan": scan,
        })
    out["legacy_caches"] = caches
    if hash_weights:
        out["files"]["weights"] = {k: {"sha256": sha256_file(rel(k)), "bytes": rel(k).stat().st_size}
                                   for k in ("yolo11s_weights", "rtdetr_l_weights") if rel(k).exists()}
    out["notes"] = [
        "Read-only inspection; no file in the asset root was modified.",
        "No BDD100K or ACDC data are present; condition (night/weather) metadata is absent.",
        "group_id is null for every image; no independence claim is possible from these assets.",
    ]
    return out


# ------------------------------------------------------------------------------ CLI


def _parse_mapping(items: list[str]) -> dict[str, str]:
    out = {}
    for item in items:
        if "=" not in item:
            raise PreflightError(f"--map expects vocab=category, got {item!r}")
        k, v = item.split("=", 1)
        if k in out:
            raise PreflightError(f"duplicate --map key {k!r}")
        out[k] = v
    return out


def _source(path: Path) -> dict:
    return {"file_name": Path(path).name, "sha256": sha256_file(Path(path))}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m threshold_transfer.data", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("inventory")
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--dims", action="store_true", help="stdlib header dimension audit of every image")
    p.add_argument("--asset-root", type=Path, help="override config asset_root (e.g. from a worktree)")
    p = sub.add_parser("convert-coco")
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--dataset-tag", required=True)
    p.add_argument("--split")
    p.add_argument("--ignore-policy", required=True, choices=sorted(COCO_IGNORE_POLICIES))
    p.add_argument("--invalid-box-policy", default="reject", choices=INVALID_POLICIES)
    p = sub.add_parser("convert-kitti-derived")
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--dataset-tag", required=True)
    p.add_argument("--split")
    p.add_argument("--policy", help=f"required: {KITTI_DIAGNOSTIC_POLICY}")
    p.add_argument("--invalid-box-policy", default="reject", choices=INVALID_POLICIES)
    p = sub.add_parser("convert-legacy")
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--map", action="append", default=[], metavar="VOCAB=CATEGORY", required=True)
    p.add_argument("--annotations", type=Path)
    p.add_argument("--restrict-to-manifest", action="store_true")
    p.add_argument("--invalid-row-policy", default="reject", choices=INVALID_POLICIES)
    p = sub.add_parser("check-roles")
    p.add_argument("--annotations", required=True, type=Path)
    p.add_argument("--roles", required=True, type=Path, help="JSON object image_id -> role")
    p.add_argument("--mode", required=True, choices=["held_out", "diagnostic"])
    p.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    try:
        inputs = [getattr(a, name) for name in ("input", "annotations", "roles", "config")
                  if getattr(a, name, None) is not None]
        roots = []
        if a.cmd == "inventory":
            config = load_json(a.config)
            if not isinstance(config, dict) or not isinstance(config.get("asset_root"), str):
                raise PreflightError("inventory config needs an asset_root string")
            root = (a.asset_root if a.asset_root else a.config.resolve().parent.parent / config["asset_root"]).resolve()
            roots.append(root)
            directory_keys = {"coco_images", "kitti_images", "kitti_labels", "legacy_predictions"}
            for key, value in config.items():
                if key in ("asset_root", "root_resolution"):
                    continue
                if not isinstance(value, str):
                    raise PreflightError("configured asset paths must be strings")
                (roots if key in directory_keys else inputs).append(root / value)
        if getattr(a, "out", None):
            _protect_output(a.out, inputs, roots)
        if a.cmd == "inventory":
            result = inventory(a.config, dims=a.dims, asset_root=a.asset_root)
        elif a.cmd == "convert-coco":
            result = convert_coco(load_json(a.input), dataset_tag=a.dataset_tag, split=a.split,
                                  ignore_policy=a.ignore_policy, invalid_box_policy=a.invalid_box_policy,
                                  source=_source(a.input))
        elif a.cmd == "convert-kitti-derived":
            result = convert_kitti_derived(load_json(a.input), dataset_tag=a.dataset_tag, split=a.split,
                                           policy=a.policy, invalid_box_policy=a.invalid_box_policy,
                                           source=_source(a.input))
        elif a.cmd == "convert-legacy":
            ann = load_json(a.annotations) if a.annotations else None
            result = convert_legacy_predictions(load_json(a.input), category_mapping=_parse_mapping(a.map),
                                                annotations=ann, restrict_to_manifest=a.restrict_to_manifest,
                                                invalid_row_policy=a.invalid_row_policy, source=_source(a.input))
        else:
            result = check_roles(load_json(a.annotations), load_json(a.roles), mode=a.mode)
        if getattr(a, "out", None):
            write_json(result, a.out, protected_inputs=inputs, protected_roots=roots)
        else:
            _json_value(result)
            print(json.dumps(result, indent=1, allow_nan=False))
    except (PreflightError, OSError, ValueError, TypeError, AttributeError, KeyError,
            OverflowError, RecursionError, UnicodeError) as e:
        print(f"PREFLIGHT ERROR: {e}", file=sys.stderr)
        return 2
    if a.cmd == "check-roles" and result["status"] == "FAIL":
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
