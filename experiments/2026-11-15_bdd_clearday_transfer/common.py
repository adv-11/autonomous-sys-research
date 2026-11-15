"""Claude Opus: pure split/label logic for the BDD clear-day transfer experiment.

Applies to BDD100K legacy 2018 labels (Berkeley candidate archive) only; these are
not Detection 2020 labels. Stdlib only so it runs locally and on Colab unchanged.
"""
from __future__ import annotations

import hashlib

# Ten BDD detection classes. Pedestrian is index 0 (legacy native name "person").
CLASSES = ("pedestrian", "rider", "car", "truck", "bus", "train",
           "motorcycle", "bicycle", "traffic light", "traffic sign")
LEGACY_TO_CLASS = {"person": "pedestrian", "rider": "rider", "car": "car", "truck": "truck",
                   "bus": "bus", "train": "train", "motor": "motorcycle", "bike": "bicycle",
                   "traffic light": "traffic light", "traffic sign": "traffic sign"}
DROPPED_PREFIXES = ("lane/", "area/")  # polyline/polygon lane and drivable-area labels
WIDTH, HEIGHT = 1280, 720  # nominal; verified on the real images in Colab before use

SELECTION_SALT = "bdd-clearday-selection-v1:"
SELECTION_PER_10000 = 1500  # ~15% of source images held out for threshold selection

HEIGHT_BINS = ((0, 16), (16, 32), (32, 64), (64, 128), (128, None))


def is_source(attrs):
    return attrs.get("weather") == "clear" and attrs.get("timeofday") == "daytime"


def selection_bucket(name):
    """Deterministic 0..9999 bucket from the image stem; independent of labels."""
    return int(hashlib.sha256((SELECTION_SALT + name).encode()).hexdigest()[:8], 16) % 10000


def source_role(name):
    return "selection" if selection_bucket(name) < SELECTION_PER_10000 else "train"


def primary_stratum(attrs):
    """Mutually exclusive val strata. Night and dawn/dusk pool all weather."""
    w, t = attrs.get("weather"), attrs.get("timeofday")
    if t == "night":
        return "night"
    if t == "dawn/dusk":
        return "dawn_dusk"
    if w == "foggy":
        return "foggy"  # all times of day; tiny, descriptive only
    if t != "daytime":
        return "undefined"
    return {"clear": "clear_day", "overcast": "cloudy_day", "partly cloudy": "cloudy_day",
            "rainy": "rainy_day", "snowy": "snowy_day"}.get(w, "undefined")


def secondary_strata(attrs):
    """Overlapping marginal strata reported as sensitivities."""
    w, t = attrs.get("weather"), attrs.get("timeofday")
    out = []
    if t == "night" and w == "clear":
        out.append("night_clear")
    if t == "night" and w in ("rainy", "snowy"):
        out.append("night_rain_snow")
    if w == "rainy":
        out.append("rainy_all")
    if w == "snowy":
        out.append("snowy_all")
    return out


def convert_objects(objects):
    """Legacy objects -> list of (class_index, x1, y1, x2, y2) plus drop counts.

    Boxes are kept in original pixel coordinates. Unknown categories raise. Boxes
    with nonpositive extent are dropped and counted, never repaired. No clipping is
    applied here (the label survey found zero out-of-bounds legacy boxes; the
    conversion asserts that rather than silently clipping).
    """
    boxes, dropped = [], {"no_box2d": 0, "nonpositive": 0, "out_of_bounds": 0, "dropped_category": 0}
    for obj in objects:
        cat = obj["category"]
        if cat.startswith(DROPPED_PREFIXES):
            dropped["dropped_category"] += 1
            continue
        if cat not in LEGACY_TO_CLASS:
            raise ValueError(f"unknown legacy category: {cat}")
        if "box2d" not in obj:
            dropped["no_box2d"] += 1
            continue
        b = obj["box2d"]
        x1, y1, x2, y2 = (float(b[k]) for k in ("x1", "y1", "x2", "y2"))
        if x1 < 0 or y1 < 0 or x2 > WIDTH or y2 > HEIGHT:
            dropped["out_of_bounds"] += 1
            raise ValueError("legacy box outside nominal 1280x720; clipping policy needed")
        if x2 <= x1 or y2 <= y1:
            dropped["nonpositive"] += 1
            continue
        boxes.append((CLASSES.index(LEGACY_TO_CLASS[cat]), x1, y1, x2, y2))
    return boxes, dropped


def yolo_lines(boxes, width=WIDTH, height=HEIGHT):
    lines = []
    for c, x1, y1, x2, y2 in boxes:
        lines.append(f"{c} {(x1 + x2) / 2 / width:.6f} {(y1 + y2) / 2 / height:.6f} "
                     f"{(x2 - x1) / width:.6f} {(y2 - y1) / height:.6f}")
    return "\n".join(lines) + ("\n" if lines else "")


def height_bin(h):
    for lo, hi in HEIGHT_BINS:
        if h >= lo and (hi is None or h < hi):
            return f"{lo}-{hi}" if hi is not None else f">={lo}"
    raise ValueError("negative height")
