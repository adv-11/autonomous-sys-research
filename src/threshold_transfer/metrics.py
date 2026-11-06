"""GPT reference score-prefix protocol, not COCO AP or official KITTI scoring.

Each candidate matches eligible same-class GT first, then may be absorbed by an
ignore region. Ignored/crowd regions are reusable under either explicit IoA mode.
Native dataset-specific ignore attributes are opaque; converters own that policy.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
import math

from .schema import identifier, number, validate_documents

IGNORE_POLICIES = ("reject", "same_category_ioa", "all_categories_ioa")


def quantity(value, status=None):
    return {"value": value, "status": status or ("UNDEFINED" if value is None else "DEFINED")}


def _intersection(a, b):
    return (max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])) *
            max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])))


def _iou(a, b):
    inter = _intersection(a, b)
    # Subtract first to avoid overflowing a+b for otherwise valid huge boxes.
    denominator = (a[2] * a[3] - inter) + b[2] * b[3]
    if not math.isfinite(denominator):
        raise ValueError("IoU union area is not representable")
    return inter / denominator


def binary_tp_ece(rows, bins=15):
    """Equal-width binary TP-ECE over nonignored retained candidates only.

    TP=1, FP=0 under this module's matching; IGNORED excluded. Bins are [a,b),
    except the final bin includes score 1. This is neither LaECE nor OCE.
    """
    if isinstance(bins, bool) or not isinstance(bins, int) or bins <= 0:
        raise ValueError("bins must be a positive integer")
    buckets = [[] for _ in range(bins)]
    ignored = 0
    for row in rows:
        score = number(row.get("score"), "score", 0, 1)
        label = row.get("outcome")
        if label == "IGNORED":
            ignored += 1
            continue
        if label not in ("TP", "FP"):
            raise ValueError("ECE outcome must be TP, FP or IGNORED")
        buckets[min(int(score * bins), bins - 1)].append((score, label == "TP"))
    count = sum(map(len, buckets))
    result, errors = [], []
    for index, bucket in enumerate(buckets):
        confidence = math.fsum(s for s, _ in bucket) / len(bucket) if bucket else None
        accuracy = sum(y for _, y in bucket) / len(bucket) if bucket else None
        result.append({"lower": index / bins, "upper": (index + 1) / bins,
                       "count": len(bucket), "mean_score": confidence, "tp_rate": accuracy})
        if bucket:
            errors.append(len(bucket) * abs(confidence - accuracy))
    return {**quantity(math.fsum(errors) / count if count else None),
            "name": "simple_binary_tp_ece", "count": count, "ignored_count": ignored,
            "bins": result}


class ReferenceEvaluator:
    """Validate once and label all candidates in deterministic score-prefix order.

    Explicit categories are pooled but matched within exact native category names.
    No class merging, candidate floor/cap, NMS, clipping or rounding occurs here.
    """

    def __init__(self, annotations, predictions, *, categories,
                 ignore_policy="reject", bounds_policy="strict_known"):
        if (not isinstance(categories, (list, tuple)) or not categories or
                any(not isinstance(c, str) or not c.strip() for c in categories) or
                len(set(categories)) != len(categories)):
            raise ValueError("categories must be explicit, unique nonempty strings")
        if ignore_policy not in IGNORE_POLICIES:
            raise ValueError("unknown ignore policy")
        self.annotations, self.predictions = validate_documents(
            annotations, predictions, bounds_policy=bounds_policy)
        self.categories = sorted(categories)
        self.ignore_policy = ignore_policy
        self.bounds_policy = bounds_policy
        self.limitations = []
        image_ids = {i["image_id"] for i in self.annotations["images"]}
        coverage = self.predictions["provenance"].get("evaluated_image_ids")
        if coverage is None:
            self.limitations.append("Prediction inference coverage is not independently verified; evaluated_image_ids absent.")
        else:
            if not isinstance(coverage, list):
                raise ValueError("evaluated_image_ids must be a list")
            for image_id in coverage:
                identifier(image_id, "evaluated_image_id")
            if len(set(coverage)) != len(coverage) or set(coverage) != image_ids:
                raise ValueError("evaluated_image_ids must equal the complete annotation image population")
        unknown_dimensions = sum(i.get("width") is None or i.get("height") is None
                                 for i in self.annotations["images"])
        if unknown_dimensions:
            self.limitations.append(f"Full image-coordinate bounds unverified for {unknown_dimensions} images with missing dimensions.")
        if bounds_policy == "allow_outside":
            self.limitations.append("Out-of-image coordinates explicitly allowed without clipping.")
        eligible, ignored = defaultdict(list), defaultdict(list)
        self.gt_count = 0
        for gt in self.annotations["annotations"]:
            if gt["ignore"] or gt["iscrowd"]:
                if ignore_policy == "reject":
                    raise ValueError("ignored/crowd annotations require explicit ignore policy")
                ignored[gt["image_id"]].append(gt)
            elif gt["category"] in self.categories:
                eligible[(gt["image_id"], gt["category"])].append(gt)
                self.gt_count += 1
        candidates = [p for p in self.predictions["predictions"] if p["category"] in self.categories]
        candidates.sort(key=lambda p: (-p["score"], p["candidate_id"]))
        matched = set()
        self.rows = []
        for pred in candidates:
            options = []
            for gt in eligible[(pred["image_id"], pred["category"])]:
                if gt["annotation_id"] not in matched:
                    overlap = _iou(pred["bbox"], gt["bbox"])
                    if overlap >= 0.50:
                        options.append((-overlap, gt["annotation_id"]))
            annotation_id, outcome = None, "FP"
            if options:
                _, annotation_id = min(options)
                matched.add(annotation_id)
                outcome = "TP"
            else:
                regions = sorted(ignored[pred["image_id"]], key=lambda g: g["annotation_id"])
                for gt in regions:
                    if ignore_policy == "same_category_ioa" and gt["category"] != pred["category"]:
                        continue
                    ioa = _intersection(pred["bbox"], gt["bbox"]) / (pred["bbox"][2] * pred["bbox"][3])
                    if ioa >= 0.50:
                        annotation_id, outcome = gt["annotation_id"], "IGNORED"
                        break
            self.rows.append({"candidate_id": pred["candidate_id"], "image_id": pred["image_id"],
                              "category": pred["category"], "score": pred["score"],
                              "outcome": outcome, "annotation_id": annotation_id})

    def operating_point(self, threshold=None):
        """None retains all cached candidates; numeric boundaries include all ties."""
        if threshold is not None:
            number(threshold, "threshold", 0, 1)
        retained = [r for r in self.rows if threshold is None or r["score"] >= threshold]
        tp = sum(r["outcome"] == "TP" for r in retained)
        fp = sum(r["outcome"] == "FP" for r in retained)
        image_count = len(self.annotations["images"])
        return {"threshold": threshold, "image_count": image_count, "eligible_gt": self.gt_count,
                "retained_candidates": len(retained), "tp": tp, "fp": fp,
                "ignored": len(retained) - tp - fp, "fn": self.gt_count - tp,
                "recall": quantity(tp / self.gt_count if self.gt_count else None),
                "precision": quantity(tp / (tp + fp) if tp + fp else None),
                "fppi": quantity(fp / image_count if image_count else None),
                "binary_tp_ece": binary_tp_ece(retained), "matches": retained}

    def select_threshold(self, target_recall):
        """Highest observed boundary achieving recall>=target, preserving tie groups."""
        number(target_recall, "target_recall", 0, 1)
        if target_recall == 0:
            raise ValueError("target_recall must be in (0, 1]")
        ceiling = self.operating_point()
        base = {"target_recall": target_recall, "threshold": None, "operating_point": None,
                "candidate_ceiling": ceiling, "next_lower_score": None, "boundary_gap": None,
                "boundary_tie_count": None, "headroom": quantity(None), "headroom_flag": None}
        if not self.gt_count:
            return {**base, "status": "UNDEFINED"}
        exact_headroom = Fraction(ceiling["tp"], self.gt_count) - Fraction(str(target_recall))
        headroom = float(exact_headroom)
        base["headroom"] = quantity(headroom)
        base["headroom_flag"] = "INFEASIBLE" if headroom < 0 else (
            "LOW_HEADROOM" if exact_headroom < Fraction(1, 50) else "ADEQUATE")
        if headroom < 0:
            return {**base, "status": "INFEASIBLE"}
        # Full-prefix labels are unchanged by removing any lower-scoring suffix.
        tp, index = 0, 0
        while index < len(self.rows):
            start, score = index, self.rows[index]["score"]
            while index < len(self.rows) and self.rows[index]["score"] == score:
                tp += self.rows[index]["outcome"] == "TP"
                index += 1
            if tp / self.gt_count >= target_recall:
                lower = self.rows[index]["score"] if index < len(self.rows) else None
                return {**base, "status": "FEASIBLE", "threshold": score,
                        "operating_point": self.operating_point(score),
                        "next_lower_score": lower, "boundary_gap": score - lower if lower is not None else None,
                        "boundary_tie_count": index - start}
        raise AssertionError("feasible ceiling must have an observed feasible boundary")


def target_gap_decomposition(target, operating, ceiling):
    """Exact signed/positive target gaps; recall units, never percentage points."""
    number(target, "target", 0, 1)
    if operating is None or ceiling is None:
        return {k: quantity(None) for k in ("signed_gap", "shortfall", "ceiling_shortfall",
                "removable_shortfall", "signed_threshold_component", "threshold_removable_misses")}
    number(operating, "operating recall", 0, 1)
    number(ceiling, "ceiling recall", 0, 1)
    if operating > ceiling:
        raise ValueError("operating recall exceeds candidate ceiling")
    u = max(0.0, target - ceiling)
    t = min(target, ceiling) - operating
    return {k: quantity(v) for k, v in {
        "signed_gap": target - operating, "shortfall": max(0.0, target - operating),
        "ceiling_shortfall": u, "removable_shortfall": max(0.0, t),
        "signed_threshold_component": t, "threshold_removable_misses": ceiling - operating}.items()}


def held_out_loss_decomposition(clear_recall, target_recall, clear_ceiling, target_ceiling):
    """L=(M_clear-M_target)+(W_target-W_clear), a descriptive signed identity."""
    values = (clear_recall, target_recall, clear_ceiling, target_ceiling)
    keys = ("held_out_loss", "ceiling_difference", "threshold_miss_difference")
    if any(v is None for v in values):
        return {key: quantity(None) for key in keys}
    for value in values:
        number(value, "recall", 0, 1)
    if clear_recall > clear_ceiling or target_recall > target_ceiling:
        raise ValueError("operating recall exceeds candidate ceiling")
    return dict(zip(keys, map(quantity, (clear_recall - target_recall,
                clear_ceiling - target_ceiling,
                (target_ceiling - target_recall) - (clear_ceiling - clear_recall)))))
