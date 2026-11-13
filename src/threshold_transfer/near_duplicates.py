"""Perceptual near-duplicate screening for ACDC normal-condition references (Claude).

The byte-identity edges in ``acdc_grouping`` find only *exact* reuse of a reference
image. This module supplies the GPU-free pieces of a bounded perceptual screen:
64-bit DCT perceptual hashes (pHash) and 64-bit difference hashes (dHash), Hamming
pair enumeration under fixed thresholds, pair categories relative to the existing
``acdc-recording-v1`` components, a capped visual-review queue and component-count
sensitivities.

A small Hamming distance is a *screening flag*. It is not evidence that two frames
come from the same recording or trip, and nothing here merges primary components.
Representation and thresholds are fixed in ``configs/research/development_pilot.json``
before any distance was computed.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from typing import Iterable, Mapping, Sequence

import numpy as np

PHASH_SIZE = 32       # grayscale side length before the DCT
PHASH_BLOCK = 8       # low-frequency block -> 64 bits
DHASH_SHAPE = (8, 9)  # rows, columns -> 8 x 8 horizontal gradient bits
CATEGORIES = ("within_component", "cross_component_same_condition", "cross_condition")
REVIEW_PRIORITY = {"cross_condition": 0, "cross_component_same_condition": 1, "within_component": 2}
REVIEW_LABELS = ("confirmed_same_place", "uncertain", "rejected_different_place")


def _dct_matrix(n: int) -> np.ndarray:
    """Orthonormal DCT-II matrix, so ``D @ x @ D.T`` is the 2-D DCT (no scipy needed)."""
    k = np.arange(n)[:, None]
    i = np.arange(n)[None, :]
    d = np.cos(math.pi * (2 * i + 1) * k / (2 * n)) * math.sqrt(2.0 / n)
    d[0, :] = math.sqrt(1.0 / n)
    return d


_DCT32 = _dct_matrix(PHASH_SIZE)


def _pack(bits: np.ndarray) -> int:
    """Pack 64 booleans (row-major) into an int, first bit most significant."""
    flat = np.asarray(bits, dtype=bool).ravel()
    if flat.size != 64:
        raise ValueError("expected 64 bits")
    value = 0
    for b in flat:
        value = (value << 1) | int(b)
    return value


def phash_bits(gray: np.ndarray) -> int:
    """pHash of a ``32 x 32`` grayscale array: DCT, top-left 8x8 block, bit = coef > median.

    The median includes the DC coefficient (the ``imagehash.phash`` convention).
    """
    gray = np.asarray(gray, dtype=np.float64)
    if gray.shape != (PHASH_SIZE, PHASH_SIZE):
        raise ValueError(f"pHash input must be {PHASH_SIZE}x{PHASH_SIZE}")
    coef = (_DCT32 @ gray @ _DCT32.T)[:PHASH_BLOCK, :PHASH_BLOCK]
    return _pack(coef > np.median(coef))


def dhash_bits(gray: np.ndarray) -> int:
    """dHash of an ``8 x 9`` grayscale array: bit = right pixel brighter than left."""
    gray = np.asarray(gray, dtype=np.float64)
    if gray.shape != DHASH_SHAPE:
        raise ValueError("dHash input must be 8 rows x 9 columns")
    return _pack(gray[:, 1:] > gray[:, :-1])


def hamming(a: int, b: int) -> int:
    return bin((a ^ b) & 0xFFFFFFFFFFFFFFFF).count("1")


def _popcount64(x: np.ndarray) -> np.ndarray:
    if hasattr(np, "bitwise_count"):
        return np.bitwise_count(x).astype(np.int64)
    bytes_ = x.view(np.uint8).reshape(*x.shape, 8)
    table = np.array([bin(i).count("1") for i in range(256)], dtype=np.int64)
    return table[bytes_].sum(axis=-1)


def pairwise_hamming(hashes: Sequence[int], max_distance: int) -> list[tuple[int, int, int]]:
    """All index pairs ``i < j`` with Hamming distance <= ``max_distance``, sorted."""
    arr = np.array([int(h) for h in hashes], dtype=np.uint64)
    out = []
    for i in range(len(arr) - 1):
        d = _popcount64(arr[i + 1:] ^ arr[i])
        for j in np.nonzero(d <= max_distance)[0]:
            out.append((i, i + 1 + int(j), int(d[j])))
    return out


def distance_histogram(hashes: Sequence[int], labels: Sequence[str]) -> dict[str, list[int]]:
    """Counts of pHash distances 0..64 for every unordered pair, split by pair category label.

    ``labels[i]`` is ``(component, condition)``; the category follows :func:`pair_category`.
    """
    arr = np.array([int(h) for h in hashes], dtype=np.uint64)
    comp = np.array([lab[0] for lab in labels])
    cond = np.array([lab[1] for lab in labels])
    hist = {c: np.zeros(65, dtype=np.int64) for c in CATEGORIES}
    for i in range(len(arr) - 1):
        d = _popcount64(arr[i + 1:] ^ arr[i])
        same_comp = comp[i + 1:] == comp[i]
        same_cond = cond[i + 1:] == cond[i]
        for name, mask in (("within_component", same_comp),
                           ("cross_component_same_condition", ~same_comp & same_cond),
                           ("cross_condition", ~same_comp & ~same_cond)):
            hist[name] += np.bincount(d[mask], minlength=65)
    return {k: v.tolist() for k, v in hist.items()}


def pair_category(a: Mapping, b: Mapping) -> str:
    """Category of a pair of records carrying ``component`` and ``condition``.

    Two different conditions inside one component are classed ``within_component``:
    that dependency is already blocked by the primary policy.
    """
    if a["component"] == b["component"]:
        return "within_component"
    if a["condition"] == b["condition"]:
        return "cross_component_same_condition"
    return "cross_condition"


def flagged_pairs(records: Sequence[Mapping], max_distance: int) -> list[dict]:
    """Image pairs with pHash distance <= ``max_distance``, annotated with dHash and category."""
    pairs = []
    for i, j, d in pairwise_hamming([r["phash"] for r in records], max_distance):
        a, b = records[i], records[j]
        pairs.append({"a": a["path"], "b": b["path"], "phash_distance": d,
                      "dhash_distance": hamming(a["dhash"], b["dhash"]),
                      "category": pair_category(a, b),
                      "components": tuple(sorted((a["component"], b["component"]))),
                      "conditions": tuple(sorted((a["condition"], b["condition"])))})
    return pairs


def review_queue(pairs: Iterable[Mapping], max_pairs: int) -> tuple[list[dict], list[dict]]:
    """Choose at most ``max_pairs`` component-pair representatives for visual review.

    Only cross-component pairs qualify. Each unordered component pair is represented by its
    closest image pair (pHash, then dHash, then paths). Cross-condition component pairs come
    first, then same-condition ones, each by representative distance. Returns
    ``(queue, remaining)``; ``remaining`` lists unreviewed component pairs with their counts.
    """
    by_component = defaultdict(list)
    for p in pairs:
        if p["category"] != "within_component":
            by_component[p["components"]].append(p)
    reps = []
    for key, members in by_component.items():
        best = min(members, key=lambda p: (p["phash_distance"], p["dhash_distance"], p["a"], p["b"]))
        reps.append({**best, "image_pairs_in_component_pair": len(members)})
    reps.sort(key=lambda p: (REVIEW_PRIORITY[p["category"]], p["phash_distance"],
                             p["dhash_distance"], p["a"], p["b"]))
    return reps[:max_pairs], reps[max_pairs:]


def merge_components(image_component: Mapping[str, str],
                     extra_edges: Iterable[tuple[str, str]]) -> tuple[dict[str, str], int]:
    """Union-find over component IDs. Returns ``(image -> root component, merges applied)``."""
    parent = {c: c for c in sorted(set(image_component.values()))}

    def find(c):
        while parent[c] != c:
            parent[c] = parent[parent[c]]
            c = parent[c]
        return c

    applied = 0
    for a, b in extra_edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            applied += 1
    return {img: find(c) for img, c in image_component.items()}, applied


def component_sensitivity(image_component: Mapping[str, str], image_condition: Mapping[str, str],
                          labelled_adverse: Iterable[str], extra_edges: Iterable[tuple[str, str]]) -> dict:
    """Component counts after adding ``extra_edges`` (component-id pairs) to the primary policy.

    This is a *sensitivity* calculation: it never rewrites the primary manifest.
    """
    merged, applied = merge_components(image_component, extra_edges)
    conditions = sorted(set(image_condition.values()))
    labelled = set(labelled_adverse)
    by_condition = {c: len({merged[i] for i in merged if image_condition[i] == c}) for c in conditions}
    labelled_by_condition = {c: len({merged[i] for i in labelled if image_condition[i] == c})
                             for c in conditions}
    members = defaultdict(set)
    for img, root in merged.items():
        members[root].add(image_condition[img])
    return {"components": len(set(merged.values())), "merges_applied": applied,
            "components_by_condition": by_condition,
            "labelled_adverse_components_by_condition": labelled_by_condition,
            "components_spanning_conditions": sum(len(v) > 1 for v in members.values())}


def closure_ids(image_component: Mapping[str, str], extra_edges: Iterable[tuple[str, str]],
                prefix: str) -> dict[str, str]:
    """Content-addressed closure ID per image: ``prefix`` + SHA-256 of the sorted member paths."""
    merged, _ = merge_components(image_component, extra_edges)
    members = defaultdict(list)
    for img, root in merged.items():
        members[root].append(img)
    out = {}
    for paths in members.values():
        paths.sort()
        digest = hashlib.sha256(json.dumps(paths, separators=(",", ":"), ensure_ascii=True)
                                .encode("ascii")).hexdigest()
        out.update(dict.fromkeys(paths, f"{prefix}:{digest}"))
    return out


def closure_support(image_closure: Mapping[str, str], image_condition: Mapping[str, str],
                    labelled_adverse: Iterable[str], excluded_images: Iterable[str]) -> dict:
    """Labelled-adverse support per condition after excluding every closure touching ``excluded_images``.

    An excluded closure is removed whole, with all of its conditions. Nothing is reassigned.
    """
    excluded_closures = {image_closure[i] for i in excluded_images}
    labelled = sorted(set(labelled_adverse))
    out = {"closures": len(set(image_closure.values())), "excluded_closures": len(excluded_closures),
           "labelled_adverse_images_excluded": sum(image_closure[i] in excluded_closures for i in labelled),
           "by_condition": {}}
    for c in sorted(set(image_condition.values())):
        kept = [i for i in labelled if image_condition[i] == c and image_closure[i] not in excluded_closures]
        sizes = Counter(image_closure[i] for i in kept)
        out["by_condition"][c] = {
            "eligible_labelled_adverse_images": len(kept),
            "eligible_closures_with_labelled_adverse": len(sizes),
            "largest_closure_share": round(max(sizes.values()) / len(kept), 4) if kept else None,
            "closure_sizes_desc": sorted(sizes.values(), reverse=True)}
    return out


def summarize_flags(pairs: Sequence[Mapping], thresholds: Sequence[int]) -> dict:
    """Image-pair and component-pair counts at each cumulative threshold, by category.

    A component spanning two conditions can meet another component in both categories, so the
    per-category component-pair counts may sum to more than ``distinct_cross_component_pairs``.
    """
    out = {}
    for t in thresholds:
        sub = [p for p in pairs if p["phash_distance"] <= t]
        cross = {tuple(p["components"]) for p in sub if p["category"] != "within_component"}
        out[str(t)] = {
            "image_pairs": dict(Counter(p["category"] for p in sub)),
            "distinct_cross_component_pairs": len(cross),
            "component_pairs": dict(Counter(cat for cat, _ in {(p["category"], tuple(p["components"]))
                                                               for p in sub
                                                               if p["category"] != "within_component"})),
        }
    return out
