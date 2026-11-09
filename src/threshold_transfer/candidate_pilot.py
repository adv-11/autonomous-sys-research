"""GPU-free logic for Claude's bounded candidate-policy pilot (KITTI development images).

The pilot captures each pipeline once at a permissive policy (floor 1e-4, cap 3000) with a
stable primitive identity per candidate (``a<anchor>:c<class>`` for YOLO heads,
``q<query>:c<class>`` for RT-DETRv2). Lower floor/cap settings are then *derived* from that
capture, which is valid only where the native selector is nested:

* YOLO26 one-to-one: hidden head top-k with k = max(max_det, 300), then strict ``conf > floor``
  and ``[:max_det]``. Ignoring ties, the two-stage top-k equals a global top-k over
  anchor x class, so a smaller (floor, cap) is a filtered prefix of the capture.
* YOLO11 / YOLO26 one-to-many: strict ``conf > floor`` before class-aware greedy hard NMS, then
  ``[:max_det]``. A box is suppressed only by higher-scoring kept boxes, so raising the floor
  deletes low scorers without changing survivors; the cap is a prefix. This needs a fixed
  deterministic tie order, unchanged boxes/IoU/class offsets, no ``max_nms`` overflow and no
  NMS time-limit break. A different NMS IoU is a different pipeline, not a derived setting.
* RT-DETRv2: top-k over query x class sigmoid scores, no native floor; the export floor is a
  later deletion, so smaller settings are prefixes.

These are claims about score values. Candidate *identities* at a tied boundary are not
certified; :func:`boundary` reports such ties and they propagate as ``UNKNOWN``. The runner
checks at least one actual native lower setting against the derived one before relying on
derivation. Nothing here measures recall, calibration or detector quality.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Iterable, Mapping, Sequence

COMPARATORS = (">", ">=")
COMPLETENESS = ("COMPLETE_RELATIVE_TO_POOL", "INCOMPLETE", "UNKNOWN")


def select_images(names: Iterable[str], *, seed: str, count: int) -> list[str]:
    """First ``count`` file names by ``SHA256(seed + ':' + name)``, ties by name (label-free)."""
    names = sorted(set(names))
    if count > len(names):
        raise ValueError("not enough images")
    return sorted(names, key=lambda n: (hashlib.sha256(f"{seed}:{n}".encode("utf-8")).hexdigest(), n))[:count]


def passes(score: float, floor: float, comparator: str) -> bool:
    if comparator not in COMPARATORS:
        raise ValueError(f"comparator must be one of {COMPARATORS}")
    return score > floor if comparator == ">" else score >= floor


def _check_rows(rows: Sequence[Mapping]) -> None:
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("candidate identities must be unique within an image")
    scores = [r["score"] for r in rows]
    if any(a < b for a, b in zip(scores, scores[1:])):
        raise ValueError("capture rows must be in native non-increasing score order")


def derive(rows: Sequence[Mapping], *, floor: float, cap: int, comparator: str) -> list[Mapping]:
    """Filtered prefix of a native-ordered capture: rows passing the floor, first ``cap`` kept.

    Valid only for selectors shown to be nested (module docstring) and when the capture's own
    floor/cap do not bind more tightly than the requested setting.
    """
    if cap <= 0:
        raise ValueError("cap must be positive")
    _check_rows(rows)
    return [r for r in rows if passes(r["score"], floor, comparator)][:cap]


def boundary(rows: Sequence[Mapping], *, floor: float, cap: int, comparator: str) -> dict:
    """Cap boundary of the floor-passing rows: kth/next scores, binding flag and tie at the cut."""
    above = [r["score"] for r in rows if passes(r["score"], floor, comparator)]
    binding = len(above) > cap
    kth = above[cap - 1] if len(above) >= cap else (above[-1] if above else None)
    nxt = above[cap] if binding else None
    return {"passing_floor": len(above), "kept": min(cap, len(above)), "cap_binding": binding,
            "kth_score": kth, "first_omitted_score": nxt,
            "tie_at_cap_boundary": bool(binding and kth == nxt),
            "duplicate_scores_kept": sum(v - 1 for v in Counter(above[:cap]).values() if v > 1)}


def geometry(boxes: Iterable[Sequence[float]], width: float, height: float) -> dict:
    """Outside-image counts for native boxes and the common post-selection clip.

    ``changed_by_clip`` counts boxes moved by clipping to [0, W] x [0, H]; ``collapsed`` counts
    boxes with zero width or height after clipping (entirely outside or on an edge). Candidate
    identity is unchanged; collapsed boxes are reported, not silently dropped.
    """
    outside = collapsed = 0
    for x1, y1, x2, y2 in boxes:
        cx1, cy1 = min(max(x1, 0.0), width), min(max(y1, 0.0), height)
        cx2, cy2 = min(max(x2, 0.0), width), min(max(y2, 0.0), height)
        if (cx1, cy1, cx2, cy2) != (x1, y1, x2, y2):
            outside += 1
        if cx2 <= cx1 or cy2 <= cy1:
            collapsed += 1
    return {"changed_by_clip": outside, "collapsed_after_clip": collapsed}


def compare(derived: Sequence[Mapping], native: Sequence[Mapping], *, score_tol: float = 0.0,
            box_tol: float = 0.0) -> dict:
    """Compare a derived setting with an actual native run of that setting, row by row.

    ``identical_identities`` requires the same candidate IDs in the same order. Score/box
    differences are reported as maxima so a nondeterministic kernel shows up as a number.
    """
    same_len = len(derived) == len(native)
    ids_equal = same_len and all(d["id"] == n["id"] for d, n in zip(derived, native))
    score_diff = max((abs(d["score"] - n["score"]) for d, n in zip(derived, native)), default=0.0)
    box_diff = max((abs(a - b) for d, n in zip(derived, native) for a, b in zip(d["box"], n["box"])),
                   default=0.0)
    return {"derived_rows": len(derived), "native_rows": len(native), "identical_identities": ids_equal,
            "max_abs_score_diff": score_diff, "max_abs_box_diff": box_diff,
            "within_tolerance": bool(ids_equal and score_diff <= score_tol and box_diff <= box_tol)}


def class_first(pool: Sequence[Mapping], *, floor: float, cap: int, comparator: str) -> list[Mapping]:
    """Explicitly different pipeline: rank only the person pool, then floor and cap.

    ``pool`` holds every person-class primitive the selector could see (e.g. all anchors' person
    scores, or the person rows of an uncapped class-aware NMS). Ties keep pool order.
    """
    ordered = sorted(enumerate(pool), key=lambda t: (-t[1]["score"], t[0]))
    return [r for _, r in ordered if passes(r["score"], floor, comparator)][:cap]


def stage_status(threshold: float, stages: Sequence[Mapping]) -> dict:
    """Selection completeness of ``score >= threshold`` relative to a named finite pool.

    Each stage records the largest score it may have omitted: ``bound`` (None if unknown),
    ``inclusive`` (omitted scores <= bound rather than < bound) and ``exact`` (bound is an
    attained omitted score). The result is COMPLETE only if every stage provably omitted nothing
    at or above the threshold; an exact omitted score at or above it gives INCOMPLETE; anything
    else (unknown stage, non-attained bound, equality at an inclusive bound) is UNKNOWN. This
    is relative to the stated pool only, never recall or semantic correctness.
    """
    status = "COMPLETE_RELATIVE_TO_POOL"
    reasons = []
    for s in stages:
        b = s.get("bound")
        if s.get("omitted_count", None) == 0:
            continue
        if b is None:
            status = "UNKNOWN"
            reasons.append(f"{s['name']}: no bound")
            continue
        safe = b < threshold or (b == threshold and not s.get("inclusive", True))
        if safe:
            continue
        if s.get("exact"):
            return {"status": "INCOMPLETE", "reasons": [f"{s['name']}: omitted score {b} >= {threshold}"]}
        status = "UNKNOWN"
        reasons.append(f"{s['name']}: bound {b} not below threshold")
    return {"status": status, "reasons": reasons}
