"""Strict canonical-v1 validation for GPT's dependency-free reference evaluator."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

SCHEMA_VERSION = "threshold-transfer-v1"
BOUNDS_POLICIES = ("strict_known", "allow_outside")


def identifier(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value


def number(value, name, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or (low is not None and value < low) or (high is not None and value > high):
        raise ValueError(f"{name} is nonfinite or outside its allowed range")
    return value


def json_value(value):
    """Reject non-JSON values, including nonfinite metadata, before serialization."""
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, (int, float)):
        number(value, "JSON number")
    elif isinstance(value, list):
        for item in value:
            json_value(item)
    elif isinstance(value, dict) and all(isinstance(k, str) for k in value):
        for item in value.values():
            json_value(item)
    else:
        raise ValueError("expected JSON-compatible value")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path):
    def reject_constant(value):
        raise ValueError(f"nonstandard JSON constant: {value}")

    result = json.loads(Path(path).read_text(encoding="utf-8"),
                        object_pairs_hook=_unique_object, parse_constant=reject_constant)
    json_value(result)
    return result


def _document(document, collection):
    json_value(document)
    if not isinstance(document, dict) or document.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("expected canonical threshold-transfer-v1 document")
    if not isinstance(document.get(collection), list):
        raise ValueError(f"{collection} must be a list")
    if not isinstance(document.get("provenance"), dict):
        raise ValueError("provenance must be an object")


def _records(records, id_key):
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("record must be an object")
        key = identifier(record.get(id_key), id_key)
        if key in seen:
            raise ValueError(f"duplicate {id_key}: {key}")
        seen.add(key)


def _box(record, image, bounds_policy):
    box = record.get("bbox")
    if not isinstance(box, list) or len(box) != 4:
        raise ValueError("bbox must be [x, y, width, height]")
    x, y, width, height = [number(v, "bbox coordinate") for v in box]
    if width <= 0 or height <= 0:
        raise ValueError("bbox width and height must be strictly positive")
    # Overflow and underflow would make geometric division invalid.
    number(x + width, "bbox right edge")
    number(y + height, "bbox bottom edge")
    area = number(width * height, "bbox area")
    if area <= 0 or x + width <= x or y + height <= y:
        raise ValueError("bbox is not representable with positive area/extent")
    if bounds_policy == "strict_known":
        for start, extent, dimension in ((x, width, image.get("width")),
                                         (y, height, image.get("height"))):
            if dimension is not None and (start < 0 or start + extent > dimension):
                raise ValueError("bbox outside known image bounds")


def validate_documents(annotations, predictions, *, bounds_policy="strict_known"):
    """Return defensive copies; validate all records even outside selected classes.

    Unknown dimensions permit geometry evaluation but never imply bounds validation.
    allow_outside preserves coordinates unchanged, including negative origins.
    """
    if bounds_policy not in BOUNDS_POLICIES:
        raise ValueError("unknown bounds policy")
    _document(annotations, "images")
    if not isinstance(annotations.get("annotations"), list):
        raise ValueError("annotations must be a list")
    _document(predictions, "predictions")
    _records(annotations["images"], "image_id")
    _records(annotations["annotations"], "annotation_id")
    _records(predictions["predictions"], "candidate_id")
    images = {i["image_id"]: i for i in annotations["images"]}
    for image in images.values():
        for key in ("width", "height"):
            if image.get(key) is not None and number(image[key], key) <= 0:
                raise ValueError("image dimensions must be positive")
        if image.get("group_id") is not None:
            identifier(image["group_id"], "group_id")
        if "attributes" in image and not isinstance(image["attributes"], dict):
            raise ValueError("image attributes must be an object")
    for kind, records in (("annotation", annotations["annotations"]),
                          ("prediction", predictions["predictions"])):
        for record in records:
            ref = identifier(record.get("image_id"), "image_id")
            if ref not in images:
                raise ValueError(f"unknown image reference: {ref}")
            identifier(record.get("category"), "category")
            _box(record, images[ref], bounds_policy)
            if kind == "annotation":
                if "attributes" in record and not isinstance(record["attributes"], dict):
                    raise ValueError("annotation attributes must be an object")
                for key in ("ignore", "iscrowd"):
                    if not isinstance(record.get(key), bool):
                        raise ValueError(f"{key} must be an explicit boolean")
            else:
                number(record.get("score"), "score", 0, 1)
    return copy.deepcopy(annotations), copy.deepcopy(predictions)
