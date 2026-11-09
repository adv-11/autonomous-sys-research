"""GPU-free logic for Claude's model-feasibility smoke tests (G0 prerequisite).

This module selects development images by a documented deterministic rule,
converts COCO boxes to YOLO training labels, and exports raw detector candidates
into the canonical ``threshold-transfer-v1`` prediction format. It imports no
deep-learning framework, so it can be unit-tested without a GPU. The scripts
under ``scripts/smoke/`` supply the model-specific inference rows.

Nothing here measures detector performance or decides G0.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from typing import Iterable, Mapping, Sequence

from .schema import SCHEMA_VERSION, validate_documents

PERSON_CATEGORY = "person"
COCO_SMALL_AREA = 32 * 32  # COCO's "small" object definition, on the native `area` field.

# Ordered strata. Earlier strata claim images first; later strata skip claimed ones.
DEFAULT_QUOTAS = (
    ("crowded_count", 12),      # most non-crowd person annotations
    ("iscrowd_person", 8),      # >=1 native iscrowd person region
    ("small_person", 10),       # >=1 non-crowd person with COCO area < 32^2
    ("empty", 8),               # zero annotations of any category
    ("no_person_nonempty", 4),  # objects present, no person or crowd-person annotation
    ("general", 8),             # any remaining image
)
DEGENERATE_POLICIES = ("reject", "drop_and_count")


def hash_key(seed: str, image_id) -> str:
    """Stable, platform-independent pseudo-random order key."""
    return hashlib.sha256(f"{seed}:{image_id}".encode("utf-8")).hexdigest()


def image_statistics(coco_doc: Mapping) -> dict:
    """Per-image counts used by the selection rule, from a native COCO instances document."""
    names = {c["id"]: c["name"] for c in coco_doc["categories"]}
    person_ids = {cid for cid, name in names.items() if name == PERSON_CATEGORY}
    if len(person_ids) != 1:
        raise ValueError("expected exactly one native 'person' category")
    stats = {img["id"]: {"n_ann": 0, "n_person": 0, "n_crowd_person": 0, "n_small_person": 0}
             for img in coco_doc["images"]}
    for ann in coco_doc["annotations"]:
        s = stats.get(ann["image_id"])
        if s is None:
            raise ValueError(f"annotation references unknown image {ann['image_id']}")
        s["n_ann"] += 1
        if ann["category_id"] in person_ids:
            if ann.get("iscrowd", 0):
                s["n_crowd_person"] += 1
            else:
                s["n_person"] += 1
                if ann["area"] < COCO_SMALL_AREA:
                    s["n_small_person"] += 1
    return stats


def _eligible(stratum: str, s: Mapping) -> bool:
    if stratum == "crowded_count":
        return s["n_person"] > 0
    if stratum == "iscrowd_person":
        return s["n_crowd_person"] > 0
    if stratum == "small_person":
        return s["n_small_person"] > 0
    if stratum == "empty":
        return s["n_ann"] == 0
    if stratum == "no_person_nonempty":
        return s["n_ann"] > 0 and s["n_person"] == 0 and s["n_crowd_person"] == 0
    if stratum == "general":
        return True
    raise ValueError(f"unknown stratum: {stratum}")


def select_eval_images(coco_doc: Mapping, *, seed: str, quotas: Sequence = DEFAULT_QUOTAS) -> list[dict]:
    """Return ordered selection rows ``{image_id, stratum, rank, **counts}``.

    ``crowded_count`` sorts by descending non-crowd person count, ties by hash key;
    every other stratum sorts eligible, unclaimed images by hash key. A quota that
    cannot be filled raises instead of silently shrinking the sample.
    """
    stats = image_statistics(coco_doc)
    claimed, rows = set(), []
    for stratum, quota in quotas:
        pool = [i for i, s in stats.items() if i not in claimed and _eligible(stratum, s)]
        if stratum == "crowded_count":
            pool.sort(key=lambda i: (-stats[i]["n_person"], hash_key(seed, i)))
        else:
            pool.sort(key=lambda i: hash_key(seed, i))
        if len(pool) < quota:
            raise ValueError(f"stratum {stratum} has {len(pool)} eligible images; quota {quota}")
        for rank, image_id in enumerate(pool[:quota]):
            claimed.add(image_id)
            rows.append({"image_id": image_id, "stratum": stratum, "rank": rank, **stats[image_id]})
    return rows


def select_train_images(coco_doc: Mapping, eval_ids: Iterable, *, seed: str, total: int) -> list:
    """Training pool: all evaluation images plus hash-ordered extras up to ``total``.

    Evaluation images are deliberately included so empty and crowded scenes reach the
    backward pass. The smoke evaluates the unmodified official checkpoint, not these
    20-iteration weights, so this overlap is not train/test leakage of any reported result.
    """
    eval_ids = list(eval_ids)
    if len(set(eval_ids)) != len(eval_ids) or total < len(eval_ids):
        raise ValueError("evaluation ids must be unique and no larger than the training pool")
    rest = sorted((img["id"] for img in coco_doc["images"] if img["id"] not in set(eval_ids)),
                  key=lambda i: hash_key(seed, i))
    return eval_ids + rest[: total - len(eval_ids)]


def split_roles(selection: Sequence[Mapping]) -> dict[str, list]:
    """Deterministic disjoint three-way split, round-robin within each stratum.

    This exists only because the reference evaluator CLI requires three disjoint
    roles. COCO images carry no conditions; the role names do not mean anything here.
    """
    roles = {"source_selection": [], "clear_test": [], "target_test": []}
    names = list(roles)
    counters = Counter()
    for row in selection:
        index = counters[row["stratum"]] % 3
        counters[row["stratum"]] += 1
        roles[names[index]].append(row["image_id"])
    return roles


def coco80_category_ids(coco_doc: Mapping) -> list[int]:
    """The 80 native COCO category ids in ascending order (index = contiguous label)."""
    ids = sorted(c["id"] for c in coco_doc["categories"])
    if len(ids) != 80:
        raise ValueError(f"expected 80 COCO categories, found {len(ids)}")
    return ids


def yolo_label_lines(annotations: Iterable[Mapping], *, width: float, height: float,
                     category_ids: Sequence[int]) -> tuple[list[str], int]:
    """YOLO ``cls cx cy w h`` (normalized) lines for one image; returns (lines, skipped_crowd).

    Crowd regions are skipped, matching Ultralytics' own COCO converter. Boxes are
    clipped to the image because YOLO labels cannot represent outside coordinates;
    nonpositive boxes after clipping are rejected rather than silently dropped.
    """
    index = {cid: i for i, cid in enumerate(category_ids)}
    lines, skipped = [], 0
    for ann in annotations:
        if ann.get("iscrowd", 0):
            skipped += 1
            continue
        x, y, w, h = ann["bbox"]
        x1, y1 = max(0.0, x), max(0.0, y)
        x2, y2 = min(float(width), x + w), min(float(height), y + h)
        if x2 <= x1 or y2 <= y1:
            raise ValueError(f"annotation {ann.get('id')} has no positive area inside the image")
        cx, cy = (x1 + x2) / 2 / width, (y1 + y2) / 2 / height
        lines.append(f"{index[ann['category_id']]} {cx:.6f} {cy:.6f} "
                     f"{(x2 - x1) / width:.6f} {(y2 - y1) / height:.6f}")
    return lines, skipped


def coco_subset(coco_doc: Mapping, image_ids: Iterable) -> dict:
    """Native COCO document restricted to ``image_ids`` (order preserved, all annotations kept)."""
    wanted = list(image_ids)
    keep = set(wanted)
    by_id = {img["id"]: img for img in coco_doc["images"]}
    missing = keep - set(by_id)
    if missing:
        raise ValueError(f"unknown image ids: {sorted(missing)[:5]}")
    return {"info": coco_doc.get("info", {}), "licenses": coco_doc.get("licenses", []),
            "categories": coco_doc["categories"],
            "images": [by_id[i] for i in wanted],
            "annotations": [a for a in coco_doc["annotations"] if a["image_id"] in keep]}


def canonical_subset(canonical: Mapping, image_ids: Iterable, *, note: str) -> dict:
    """Canonical annotation document restricted to string ``image_ids``; group_id untouched."""
    keep = [str(i) for i in image_ids]
    wanted = set(keep)
    images = {img["image_id"]: img for img in canonical["images"]}
    missing = wanted - set(images)
    if missing:
        raise ValueError(f"unknown canonical image ids: {sorted(missing)[:5]}")
    provenance = dict(canonical["provenance"])
    provenance.pop("summary", None)
    provenance.pop("validation", None)
    provenance["subset"] = {"note": note, "image_count": len(keep)}
    return {"schema_version": canonical["schema_version"],
            "images": [images[i] for i in keep],
            "annotations": [a for a in canonical["annotations"] if a["image_id"] in wanted],
            "provenance": provenance}


def export_candidates(rows_by_image: Mapping[str, Sequence], *, model_key: str,
                      evaluated_image_ids: Sequence[str], image_sizes: Mapping[str, tuple],
                      score_floor: float, max_detections: int, degenerate_policy: str = "reject",
                      inference_pipeline: Mapping | None = None) -> tuple[dict, dict]:
    """Convert raw per-image detector rows to a canonical prediction document.

    ``rows_by_image[image_id]`` is a sequence of ``(x1, y1, x2, y2, score, category)``
    in original-image pixel coordinates, as emitted by the model's native
    post-processing *before* this function. This function applies the explicit
    floor (``score >= score_floor``) and cap (top ``max_detections`` by score, then
    native order) and records how many rows each removed. Boxes are not clipped.
    Coordinates and scores are not rounded.

    Every evaluated image appears in ``evaluated_image_ids`` even with zero rows. A
    missing image key raises an error (coverage must be explicit, not inferred).
    """
    if degenerate_policy not in DEGENERATE_POLICIES:
        raise ValueError(f"degenerate_policy must be one of {DEGENERATE_POLICIES}")
    if not (0 <= score_floor <= 1) or isinstance(max_detections, bool) or max_detections <= 0:
        raise ValueError("explicit score floor in [0,1] and positive cap are required")
    ids = [str(i) for i in evaluated_image_ids]
    if len(set(ids)) != len(ids):
        raise ValueError("evaluated_image_ids must be unique")
    extra = set(map(str, rows_by_image)) - set(ids)
    if extra:
        raise ValueError(f"rows for images outside the evaluated population: {sorted(extra)[:5]}")
    predictions = []
    per_image = {}
    totals = Counter()
    for image_id in ids:
        if image_id not in rows_by_image:
            raise ValueError(f"no row list for evaluated image {image_id}; pass [] for empty output")
        width, height = image_sizes[image_id]
        raw = list(rows_by_image[image_id])
        valid, degenerate, nonfinite = [], 0, 0
        for native_rank, row in enumerate(raw):
            x1, y1, x2, y2, score, category = row
            values = (x1, y1, x2, y2, score)
            if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
                nonfinite += 1
                continue
            if not (0 <= score <= 1):
                raise ValueError(f"{image_id}: score {score} outside [0,1]")
            if x2 <= x1 or y2 <= y1:
                if degenerate_policy == "reject":
                    raise ValueError(f"{image_id}: degenerate box {row[:4]}")
                degenerate += 1
                continue
            valid.append((float(score), native_rank, float(x1), float(y1), float(x2), float(y2), str(category)))
        if nonfinite:
            raise ValueError(f"{image_id}: {nonfinite} nonfinite detector rows")
        above = [v for v in valid if v[0] >= score_floor]
        above.sort(key=lambda v: (-v[0], v[1]))
        kept = above[:max_detections]
        outside = 0
        for rank, (score, native_rank, x1, y1, x2, y2, category) in enumerate(kept):
            if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
                outside += 1
            predictions.append({"candidate_id": f"{model_key}:{image_id}:{rank:04d}",
                                "image_id": image_id, "category": category,
                                "bbox": [x1, y1, x2 - x1, y2 - y1], "score": score})
        stats = {"native_rows": len(raw), "degenerate_dropped": degenerate,
                 "below_floor": len(valid) - len(above), "removed_by_cap": len(above) - len(kept),
                 "kept": len(kept), "kept_person": sum(k[6] == PERSON_CATEGORY for k in kept),
                 "outside_image_bounds": outside,
                 "min_kept_score": kept[-1][0] if kept else None,
                 "cap_binding": len(above) >= max_detections}
        per_image[image_id] = stats
        for key in ("native_rows", "degenerate_dropped", "below_floor", "removed_by_cap", "kept",
                    "kept_person", "outside_image_bounds"):
            totals[key] += stats[key]
        totals["images_cap_binding"] += stats["cap_binding"]
        totals["images_zero_kept"] += stats["kept"] == 0
    document = {"schema_version": SCHEMA_VERSION, "predictions": predictions,
                "provenance": {"researcher": "Claude", "model_key": model_key,
                               "evaluated_image_ids": ids,
                               "candidate_export": {"score_floor": score_floor, "max_detections": max_detections,
                                                    "floor_rule": "score >= floor",
                                                    "cap_rule": "top-k by score, ties by native rank",
                                                    "degenerate_policy": degenerate_policy,
                                                    "clipping": "none", "rounding": "none"}}}
    if inference_pipeline is not None:
        document["provenance"]["inference_pipeline"] = dict(inference_pipeline)
    n = len(ids)
    summary = {"images": n, **{k: totals[k] for k in sorted(totals)},
               "candidates_per_image_mean": totals["kept"] / n if n else None,
               "person_candidates_per_image_mean": totals["kept_person"] / n if n else None,
               "per_image": per_image}
    return document, summary


def restrict_predictions(predictions: Mapping, image_ids: Iterable[str]) -> dict:
    """Prediction document restricted to a role's images, with matching coverage."""
    keep = [str(i) for i in image_ids]
    wanted = set(keep)
    coverage = set(predictions["provenance"].get("evaluated_image_ids", []))
    if not wanted <= coverage:
        raise ValueError("role images are not all covered by the prediction document")
    provenance = dict(predictions["provenance"])
    provenance["evaluated_image_ids"] = keep
    return {"schema_version": predictions["schema_version"],
            "predictions": [p for p in predictions["predictions"] if p["image_id"] in wanted],
            "provenance": provenance}


def cap_censoring(primary: Mapping, sensitivity: Mapping) -> dict:
    """Compare per-image kept counts at the primary cap against a larger sensitivity cap.

    Both summaries must use the same floor and pipeline, and the larger-cap output must
    contain the primary output (true for score-sorted top-k and post-NMS truncation).
    A sensitivity run whose own cap binds gives only a lower bound on the removal.
    """
    if set(primary["per_image"]) != set(sensitivity["per_image"]):
        raise ValueError("primary and sensitivity runs cover different images")
    lost_total, lost_person, images_affected, sens_binding = 0, 0, 0, 0
    for image_id, p in primary["per_image"].items():
        s = sensitivity["per_image"][image_id]
        lost = s["kept"] - p["kept"]
        person = s["kept_person"] - p["kept_person"]
        if lost < 0 or person < 0:
            raise ValueError(f"{image_id}: larger cap kept fewer candidates")
        lost_total += lost
        lost_person += person
        images_affected += lost > 0
        sens_binding += bool(s["cap_binding"])
    return {"candidates_removed_by_primary_cap": lost_total,
            "person_candidates_removed_by_primary_cap": lost_person,
            "images_with_cap_removal": images_affected,
            "images_where_sensitivity_cap_also_binds": sens_binding,
            "exact": sens_binding == 0}


def validate_pair(annotations: Mapping, predictions: Mapping) -> None:
    """Run the shared schema validator; out-of-image predictions are allowed, not clipped."""
    validate_documents(annotations, predictions, bounds_policy="allow_outside")


def finite_all(values: Iterable) -> bool:
    return all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values)
