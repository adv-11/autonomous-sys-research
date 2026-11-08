"""ACDC dependency graph, candidate groups and a seeded allocation proposal.

Claude implementation completing a GPT draft (incomplete; Codex credits exhausted); see
docs/claude/acdc_grouping.md for provenance, evidence and limits. Reads RGB file paths,
optional raw file bytes (SHA-256 only, never decoded) and detection annotation counts.
No detector output is read. ``acdc.py`` is unchanged: its ``group_id`` stays null.

Components of the dependency graph are *candidate* groups. They block known
dependencies; they do not certify independence (same route/day/reference drive remain
unknown). Allocation roles are a proposal pending Advait's approval; G0 stays pending.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from .acdc import AGGREGATE_FILES, CONDITIONS, EXPECTED_CATEGORIES, parse_file_name
from .data import PreflightError, load_json, sha256_file

POLICY = "acdc-recording-v1"
# Rule and seed carried over unchanged from the GPT draft; no alternative seed was run.
SEED = "acdc-grouping-v1-2026-11-06"
ROLES = ("calibrator_fit", "threshold_selection", "held_out")
EDGE_TYPES = ("chapter", "pair", "recording", "identical_bytes")
_RECORDING = re.compile(r"(?:GOPR|GP(?:0[1-9]|[1-9][0-9]))([0-9]{4})", re.ASCII)
RGB_DIR = "rgb_anon_trainvaltest/rgb_anon"
README = "gt_detection_trainval/README.md"
# Two-sided 97.5% Student-t quantiles (standard tables), for the design illustration.
_T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
         8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
         15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093}


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def parse_name(name):
    """Parse an RGB path relative to ``rgb_anon/``; fail closed on anything unexpected.

    ``pair_key`` deliberately omits the split, so an adverse/reference stem links even
    across splits (stricter than the README convention). A reference image reuses the
    adverse chapter token, so its token says nothing about the normal drive's recording.
    """
    if not isinstance(name, str) or not name.isascii():
        raise PreflightError("ACDC path must be an ASCII string")
    info = parse_file_name(name)
    match = _RECORDING.fullmatch(info["sequence"])
    if not match:
        raise PreflightError(f"unknown recording token: {info['sequence']!r}")
    return {**info, "recording_number": match[1],
            "pair_key": f"{info['condition']}/{info['sequence']}_frame_{info['frame']}"}


def build_components(names, *, recording_links=True, content=None):
    """Union-find over edge buckets. Returns (path->group, witness edges, parsed).

    Each bucket (edge type, key) is a clique, stored as a star of witness edges.
    Group IDs hash the sorted member paths, so they do not depend on input order.
    ``content`` (path->sha256) adds an ``identical_bytes`` edge between byte-equal files.
    """
    names = list(names)
    parsed_list = [parse_name(n) for n in names]
    if len(names) != len(set(names)):
        raise PreflightError("duplicate image path")
    parsed = dict(sorted(zip(names, parsed_list)))
    if content is not None and set(content) != set(parsed):
        raise PreflightError("content hashes must cover exactly the image paths")
    parent = {n: n for n in parsed}

    def find(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    anchors, edges = {}, []
    for name, info in parsed.items():
        keys = [("chapter", (info["condition"], info["sequence"])), ("pair", info["pair_key"])]
        if recording_links:
            # Global over conditions: also blocks a cross-condition number collision.
            keys.append(("recording", info["recording_number"]))
        if content is not None:
            keys.append(("identical_bytes", content[name]))
        for kind, key in keys:
            if (kind, key) in anchors:
                other = anchors[(kind, key)]
                edges.append({"type": kind, "a": other, "b": name})
                parent[find(name)] = find(other)
            else:
                anchors[(kind, key)] = name
    members = defaultdict(list)
    for name in parsed:
        members[find(name)].append(name)
    groups = {}
    for paths in members.values():
        group = "acdc-candidate-v1:" + hashlib.sha256(canonical_bytes(paths)).hexdigest()
        groups.update(dict.fromkeys(paths, group))
    return groups, edges, parsed


def session_proxy_count(parsed, groups, gap):
    """Sensitivity only: chain components of one condition whose recording numbers
    differ by <= ``gap`` (consecutive GoPro numbers suggest one outing). Returns the
    number of resulting blocks per condition. Not used for allocation."""
    numbers = defaultdict(lambda: defaultdict(set))
    for n, info in parsed.items():
        numbers[info["condition"]][groups[n]].add(int(info["recording_number"]))
    result = {}
    for condition in CONDITIONS:
        spans = sorted((min(v), max(v)) for v in numbers[condition].values())
        blocks, end = 0, None
        for low, high in spans:
            if end is None or low - end > gap:
                blocks += 1
                end = high
            else:
                end = max(end, high)
        result[condition] = blocks
    return result


def allocate(groups, parsed, labelled_adverse, *, seed=SEED):
    """Allocate whole components to roles, stratified by condition signature.

    Within a stratum, order components by SHA256(seed + newline + group ID), ties by ID;
    first ceil(n/4) -> calibrator_fit, next ceil(n/4) -> threshold_selection, rest ->
    held_out. A stratum with n < 3 is descriptive_only. Components without labelled
    adverse images are unlabelled_only. No counts, labels or detector output are used.
    """
    labelled_adverse = set(labelled_adverse)
    if not labelled_adverse <= groups.keys():
        raise PreflightError("labelled image absent from the image tree")
    signatures = defaultdict(set)
    for n, g in groups.items():
        signatures[g].add(parsed[n]["condition"])
    strata = defaultdict(set)
    for n in labelled_adverse:
        if parsed[n]["reference"] or parsed[n]["split"] == "test":
            raise PreflightError("allocation population must be labelled adverse train/val")
        strata[tuple(sorted(signatures[groups[n]]))].add(groups[n])
    roles = dict.fromkeys(signatures, "unlabelled_only")
    for components in strata.values():
        ordered = sorted(components, key=lambda g: (
            hashlib.sha256((seed + "\n" + g).encode("ascii")).hexdigest(), g))
        cut = (len(ordered) + 3) // 4
        for index, g in enumerate(ordered):
            roles[g] = ("descriptive_only" if len(ordered) < 3 else
                        ROLES[0] if index < cut else ROLES[1] if index < 2 * cut else ROLES[2])
    return roles


def annotation_counts(doc, split, reference):
    """Per-image native person/rider counts (crowd separate); masks are not decoded."""
    if not isinstance(doc, dict) or not all(isinstance(doc.get(k), list)
                                            for k in ("images", "annotations", "categories")):
        raise PreflightError("detection JSON must hold images/annotations/categories lists")
    categories = {}
    for c in doc["categories"]:
        if not isinstance(c, dict) or c.get("id") in categories:
            raise PreflightError("malformed or duplicate category")
        categories[c["id"]] = (c.get("name"), c.get("supercategory"))
    if categories != EXPECTED_CATEGORIES:
        raise PreflightError("unexpected ACDC category table")
    paths, counts = {}, {}
    for image in doc["images"]:
        if not isinstance(image, dict):
            raise PreflightError("image entry must be an object")
        native, name = image.get("id"), image.get("file_name")
        if type(native) is not int or native in paths:
            raise PreflightError("invalid or duplicate image id")
        info = parse_name(name)
        if info["split"] != split or info["reference"] != reference or name in counts:
            raise PreflightError("duplicate frame or annotation role mismatch")
        paths[native] = name
        counts[name] = Counter()
    annotation_ids = set()
    for ann in doc["annotations"]:
        if not isinstance(ann, dict):
            raise PreflightError("annotation entry must be an object")
        aid, iid, cid, crowd = (ann.get(k) for k in ("id", "image_id", "category_id", "iscrowd"))
        if (type(aid) is not int or aid in annotation_ids or type(iid) is not int
                or iid not in paths or type(cid) is not int or cid not in categories
                or type(crowd) is not int or crowd not in (0, 1)):
            raise PreflightError("invalid annotation identity, category or crowd flag")
        annotation_ids.add(aid)
        count = counts[paths[iid]]
        count["all_instances"] += 1
        category = categories[cid][0]
        if category in ("person", "rider"):
            count[f"{category}_{'crowd' if crowd else 'noncrowd'}"] += 1
    return counts


def panel_summary(names, counts, groups):
    names = sorted(names)
    sizes = Counter(groups[n] for n in names)
    totals = sum((counts[n] for n in names), Counter())
    largest = max(sizes.values(), default=0)
    return {"images": len(names), "components": len(sizes),
            "largest_component_images": largest,
            "largest_component_image_share": largest / len(names) if names else None,
            "empty_images_all_classes": sum(counts[n]["all_instances"] == 0 for n in names),
            "empty_images_noncrowd_person": sum(counts[n]["person_noncrowd"] == 0 for n in names),
            "empty_images_noncrowd_human": sum(
                counts[n]["person_noncrowd"] + counts[n]["rider_noncrowd"] == 0 for n in names),
            **{k: totals[k] for k in ("person_noncrowd", "person_crowd",
                                      "rider_noncrowd", "rider_crowd")}}


def precision_design(group_counts, sigmas_pp=(5, 10, 15), target_pp=5.0):
    """Illustrative half-width t_{G-1} * sigma_b / sqrt(G) for G equally weighted
    independent groups with between-group recall SD sigma_b (an assumption, not data).
    Also the largest sigma_b meeting ``target_pp``. G < 2 is undefined."""
    rows = {}
    for label, g in group_counts.items():
        if g < 2 or g - 1 not in _T975:
            rows[label] = {"groups": g, "half_width_pp": None, "max_sigma_b_pp": None}
            continue
        t = _T975[g - 1]
        rows[label] = {"groups": g,
                       "half_width_pp": {str(s): round(t * s / math.sqrt(g), 2) for s in sigmas_pp},
                       "max_sigma_b_pp": round(target_pp * math.sqrt(g) / t, 2)}
    return rows


def feasibility_verdict(held_out_components):
    """Label-free, conservative design decision (not a proved precision bound).

    A condition with fewer than two held-out components cannot estimate between-group
    uncertainty at all, so the allocation is rejected for confirmatory ~5 pp claims.
    Otherwise no component count substitutes for the protocol's group-level pilot and
    coverage validation (protocol §6), so the verdict only defers to that pilot."""
    counts = dict(held_out_components)
    single = sorted(c for c, g in counts.items() if g < 2)
    if not counts or single:
        return {"verdict": "INSUFFICIENT_SUPPORT_FOR_CONFIRMATORY_5PP",
                "held_out_components_by_condition": counts,
                "conditions_below_two_components": single,
                "detail": "conservative design decision, not an impossibility bound: conditions "
                          "with <2 held-out components cannot estimate between-group "
                          "uncertainty; supports descriptive reporting only; see "
                          "docs/claude/acdc_grouping.md for alternatives"}
    return {"verdict": "REQUIRES_GROUP_LEVEL_PILOT",
            "held_out_components_by_condition": counts,
            "detail": "no count cutoff establishes 5 pp precision; requires a group-level "
                      "pilot and bootstrap coverage validation (protocol §6)"}


def chapter_continuity(parsed):
    """Evidence that chapters sharing a number are one continuous recording: count
    adjacent chapter pairs where one split occupies both the end (frame >= 1000) of
    chapter i and the start (frame <= 60) of chapter i+1."""
    frames = defaultdict(lambda: defaultdict(list))
    for info in parsed.values():
        if not info["reference"]:
            chapter = 0 if info["sequence"].startswith("GOPR") else int(info["sequence"][2:4])
            frames[(info["condition"], info["recording_number"], info["split"])][chapter].append(
                int(info["frame"]))
    straddles = adjacent = 0
    for chapters in frames.values():
        for i in chapters:
            if i + 1 in chapters:
                adjacent += 1
                straddles += max(chapters[i]) >= 1000 and min(chapters[i + 1]) <= 60
    all_max = [int(i["frame"]) for i in parsed.values()]
    return {"adjacent_same_split_chapter_pairs": adjacent,
            "pairs_straddling_chapter_boundary": straddles,
            "max_frame_index": max(all_max, default=None)}


def audit(root, *, hash_images=True):
    """Return (aggregate summary, PRIVATE per-image manifest) for an extracted ACDC root."""
    root = Path(root)
    rgb = root / RGB_DIR
    files = sorted(p for p in rgb.rglob("*") if p.is_file())
    if not files:
        raise PreflightError("empty RGB tree")
    names = [p.relative_to(rgb).as_posix() for p in files]
    content = {n: sha256_file(p) for n, p in zip(names, files)} if hash_images else None
    groups, edges, parsed = build_components(names, content=content)
    chapter_groups = build_components(names, recording_links=False)[0]
    recording_groups = build_components(names)[0] if content is not None else groups
    members = defaultdict(list)
    for n, g in groups.items():
        members[g].append(n)
    full_pairs = defaultdict(list)
    for n, info in parsed.items():
        full_pairs[info["pair_key"]].append(n)
    if any(len(ns) != 2 or {parsed[n]["reference"] for n in ns} != {False, True}
           for ns in full_pairs.values()):
        raise PreflightError("image tree must contain exactly one adverse and one reference per stem")
    counts, sources, adverse, references = {}, [], set(), set()
    for (split, ref), relative in sorted(AGGREGATE_FILES.items()):
        batch = annotation_counts(load_json(root / relative), split, ref)
        if counts.keys() & batch.keys() or not batch.keys() <= groups.keys():
            raise PreflightError("duplicate annotated path or annotated image missing from tree")
        counts.update(batch)
        (references if ref else adverse).update(batch)
        sources.append({"relative_path": relative, "sha256": sha256_file(root / relative)})
    adverse_keys = {parsed[n]["pair_key"] for n in adverse}
    if any(parsed[n]["pair_key"] not in adverse_keys for n in references):
        raise PreflightError("orphan annotated reference")
    ref_keys = {parsed[n]["pair_key"] for n in references}
    paired = {n for n in adverse if parsed[n]["pair_key"] in ref_keys}
    roles = allocate(groups, parsed, adverse)
    role_names = (*ROLES, "descriptive_only")
    panels = {panel: {role: {c: panel_summary(
        [n for n in population if parsed[n]["condition"] == c and roles[groups[n]] == role],
        counts, groups) for c in CONDITIONS} for role in role_names}
        for panel, population in (("adverse", adverse), ("annotated_reference", references),
                                  ("paired_adverse", paired))}

    def recurring(field, by):
        buckets = defaultdict(set)
        for info in parsed.values():
            buckets[info[by]].add(info[field])
        return sum(len(v) > 1 for v in buckets.values())

    duplicates = Counter(content.values()) if content else Counter()
    labelled_components = {c: len({groups[n] for n in adverse if parsed[n]["condition"] == c})
                           for c in CONDITIONS}
    held_out = {c: panels["adverse"]["held_out"][c]["components"] for c in CONDITIONS}
    design_groups = {f"held_out_{c}": g for c, g in held_out.items()}
    design_groups["held_out_pooled_adverse"] = len(
        {groups[n] for n in adverse if roles[groups[n]] == "held_out"})
    design_groups.update({f"all_labelled_{c}": g for c, g in labelled_components.items()})
    design_groups["all_labelled_pooled_adverse"] = len({groups[n] for n in adverse})
    manifest = {"policy": POLICY, "seed": SEED,
                "images": [{"relative_path": n, "sha256": content[n] if content else None,
                            "size_bytes": p.stat().st_size, "candidate_group_id": groups[n],
                            "proposed_role": roles[groups[n]],
                            "detection_annotated": n in counts} for n, p in zip(names, files)],
                "edges": edges}
    summary = {
        "author": "Claude (Opus 5.5), completing a GPT draft (incomplete; Codex credits "
                  "exhausted); not GPT-reviewed",
        "base_commit": "e5a7e92", "inspection_date": "2026-11-06",
        "status": "proposal only; Advait approval pending; G0 pending",
        "scope": "RGB paths, raw-byte SHA-256 and detection annotation counts; no image "
                 "decoding, no detector output",
        "policy": POLICY, "seed": SEED,
        "allocation_rule": allocate.__doc__.split("\n\n")[1].strip().replace("\n    ", " "),
        "inputs": sources,
        "readme": {"relative_path": README, "sha256": sha256_file(root / README)},
        "local_full_manifest": {
            "sha256": hashlib.sha256(canonical_bytes(manifest)).hexdigest(),
            "recipe": "SHA-256 of canonical ASCII JSON (sort_keys, separators (',', ':'), "
                      "ensure_ascii, allow_nan=False, no newline); images sorted by path with "
                      "raw-byte SHA-256, size, candidate group, proposed role; star witness edges."},
        "tree": {
            "images": len(names), "stems_with_adverse_and_reference": len(full_pairs),
            "by_condition_split": dict(sorted(Counter(
                f"{i['condition']}/{i['split']}{'_ref' if i['reference'] else ''}"
                for i in parsed.values()).items())),
            "chapter_and_pair_components": len(set(chapter_groups.values())),
            "recording_numbers": len({i["recording_number"] for i in parsed.values()}),
            "components_without_identical_bytes_edges": len(set(recording_groups.values())),
            "components": len(set(groups.values())),
            "components_spanning_conditions": sum(
                len({parsed[n]["condition"] for n in ns}) > 1 for ns in members.values()),
            "labelled_adverse_components_by_condition_signature": dict(sorted(Counter(
                "+".join(sorted({parsed[n]["condition"] for n in members[g]}))
                for g in {groups[n] for n in adverse}).items())),
            "components_by_condition": {c: len({groups[n] for n in names
                                                if parsed[n]["condition"] == c}) for c in CONDITIONS},
            "labelled_adverse_components_by_condition": labelled_components,
            "tokens_recurring_across_conditions": recurring("condition", "sequence"),
            "tokens_recurring_across_splits": recurring("split", "sequence"),
            "recording_numbers_recurring_across_conditions": recurring("condition", "recording_number"),
            "recording_numbers_recurring_across_splits": recurring("split", "recording_number"),
            "recording_numbers_with_multiple_chapters": recurring("sequence", "recording_number"),
            "byte_identical_file_groups": sum(v > 1 for v in duplicates.values()) if content else None,
            "chapter_continuity": chapter_continuity(parsed),
            "session_proxy_blocks_by_gap": {str(k): session_proxy_count(parsed, groups, k)
                                            for k in (0, 2, 10)},
            "components_by_role": dict(sorted(Counter(roles.values()).items())),
            "witness_edges_by_type": {t: sum(e["type"] == t for e in edges) for t in EDGE_TYPES},
        },
        "totals": {p: panel_summary(ns, counts, groups) for p, ns in (
            ("adverse", adverse), ("annotated_reference", references), ("paired_adverse", paired))},
        "panels": panels,
        "precision_design_illustration": precision_design(design_groups),
        "feasibility_verdict": feasibility_verdict(held_out),
    }
    return summary, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", type=Path, required=True, help="extracted ACDC root (read only)")
    parser.add_argument("--summary", type=Path, required=True, help="aggregate JSON output")
    parser.add_argument("--manifest", type=Path, required=True,
                        help="private per-image manifest; must be under the repository outputs/")
    parser.add_argument("--no-hash-images", action="store_true",
                        help="skip raw-byte hashing (no identical_bytes edges or checks)")
    args = parser.parse_args(argv)
    try:
        repo = Path(__file__).resolve().parents[2]
        manifest_path, summary_path = args.manifest.resolve(), args.summary.resolve()
        root = args.root.resolve()
        if not manifest_path.is_relative_to(repo / "outputs"):
            raise PreflightError("private manifest must stay under repository outputs/")
        if (summary_path == manifest_path or summary_path.is_relative_to(root)
                or manifest_path.is_relative_to(root)):
            raise PreflightError("outputs must be distinct and outside the read-only input root")
        summary, manifest = audit(root, hash_images=not args.no_hash_images)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n",
                                encoding="utf-8")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_bytes(canonical_bytes(manifest))
    except (PreflightError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"acdc_grouping: {error}", file=sys.stderr)
        return 2
    print(f"acdc_grouping: {summary['tree']['images']} images, "
          f"{summary['tree']['components']} components; wrote summary and private manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
