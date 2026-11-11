"""GPT Sol: two locked CPU-only baselines on already retrieved native caches.

No inference imports are executed. NumPy is used only for float64 box overlap.
Raw alternatives, evaluator rows and paired GT identities remain private.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import importlib.util
from pathlib import Path
import time

import numpy as np

SPEC = importlib.util.spec_from_file_location(
    "completed_pilot", Path(__file__).with_name("2026-11-10_transfer_pilot.py"))
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)

OBJECTIVES = (.8, .9, .95)
METHODS = ("640", "1280", "late_fusion", "agreement1280")


def boxes(rows):
    return np.asarray([r["bbox"] for r in rows], dtype=np.float64).reshape(-1, 4)


def overlaps(box, others):
    """Positive-area xywh only; same arithmetic convention as reference IoU."""
    extent = np.maximum(0, np.minimum(box[:2] + box[2:], others[:, :2] + others[:, 2:])
                        - np.maximum(box[:2], others[:, :2]))
    inter = extent[:, 0] * extent[:, 1]
    return inter / ((box[2] * box[3] - inter) + others[:, 2] * others[:, 3])


def late_fusion(rows):
    """Global native-score/ID order; suppress only same image/class IoU > .70."""
    ordered = sorted(rows, key=lambda r: (-r["score"], r["candidate_id"]))
    groups = defaultdict(list)
    for row in ordered:
        groups[(row["image_id"], row["category"])].append(row)
    kept = []
    for group in groups.values():
        geometry, active = boxes(group), np.ones(len(group), dtype=bool)
        for index, row in enumerate(group):
            if not active[index]:
                continue
            kept.append(row)
            tail = np.flatnonzero(active[index + 1:]) + index + 1
            if len(tail):
                active[tail[overlaps(geometry[index], geometry[tail]) > .70]] = False
    return sorted(kept, key=lambda r: (-r["score"], r["candidate_id"]))


def agreement(high, low):
    """Any positive human row in the entire same-image low-resolution cache."""
    pool = defaultdict(list)
    for row in low:
        pool[row["image_id"]].append(row)
    geometry = {image: boxes(rows) for image, rows in pool.items()}
    return [row for row in high if row["image_id"] in geometry and
            np.any(overlaps(np.asarray(row["bbox"]), geometry[row["image_id"]]) >= .50)]


def cardinality(adjacency):
    """Small GT-to-candidate augmenting DFS; candidate use is one-to-one."""
    owner = {}

    def augment(gt, seen):
        for candidate in adjacency[gt]:
            if candidate in seen:
                continue
            seen.add(candidate)
            if candidate not in owner or augment(owner[candidate], seen):
                owner[candidate] = gt
                return True
        return False

    for gt in range(len(adjacency)):
        augment(gt, set())
    return set(owner.values())


def oracle(panel, rows):
    """GT-aware maximum-cardinality IoU .50, ignoring confidence and crowd GT."""
    candidates = defaultdict(list)
    for row in rows:
        candidates[(row["image_id"], row["category"])].append(row)
    gt_groups = defaultdict(list)
    for gt in panel["annotations"]:
        if gt["category"] == "human" and not (gt["ignore"] or gt["iscrowd"]):
            gt_groups[(gt["image_id"], gt["category"])].append(gt)
    matched = set()
    for key, gts in gt_groups.items():
        geometry = boxes(candidates[key])
        adjacency = [np.flatnonzero(overlaps(np.asarray(gt["bbox"]), geometry) >= .50).tolist()
                     for gt in gts]
        matched.update(gts[i]["annotation_id"] for i in cardinality(adjacency))
    return matched


def tiny_check():
    def row(key, width=10, category="human", score=.8, image="i"):
        return dict(candidate_id=key, image_id=image, category=category,
                    score=score, bbox=[0, 0, width, 10])
    # Nested areas give exact .70 and .50 IoU; equality is kept by NMS/gate.
    a, b, c, d = row("a"), row("b", 7), row("c"), row("d", category="other")
    assert [r["candidate_id"] for r in late_fusion([c, b, d, a])] == ["a", "b", "d"]
    e, f, g = row("e", 5), row("f", 4), row("g", image="empty")
    assert agreement([e, f, g], [a]) == [e]
    # Greedy A->0 would block B; augmentation recovers both without reuse.
    assert cardinality([[0, 1], [0]]) == {0, 1}
    print("PASS tiny synthetic NMS equality/tie/class, gate equality/image, ambiguous matching graph", flush=True)


def compact(point):
    if point is None:
        return None
    return {k: point[k] for k in ("threshold", "image_count", "eligible_gt", "tp", "fp", "fn",
                                   "ignored", "retained_candidates", "recall", "fppi")} | {
        "zero_area_fp": sum(r.get("native_zero_area", False) for r in point["matches"])}


def tp_ids(point):
    return {r["annotation_id"] for r in point["matches"] if r["outcome"] == "TP"}


def aggregate(root, destination):
    started = time.monotonic()
    root, destination = Path(root), Path(destination)
    private_root = root / "cached_scale_baselines_20261110"
    private_root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "empirical_20261110/packet/manifest.json"
    if not manifest_path.exists():
        manifest_path = root / "empirical_completion_20261110/packet/manifest.json"
    manifest = pilot.read(manifest_path)
    paths = {"640": root / "empirical_completion_20261110/results/yolo11s_maximal.json",
             "1280": root / "resolution_20261110/results/yolo11s_maximal.json"}
    raws = {key: pilot.read(path) for key, path in paths.items()}
    expected = {i["image_id"] for p in manifest["panels"].values() for i in p["images"]}
    assert len(expected) == 700
    for key, raw in raws.items():
        coverage = raw["provenance"]["evaluated_image_ids"]
        assert len(coverage) == len(set(coverage)) == 700 and set(coverage) == expected
        assert raw["provenance"]["policy"] == dict(id="maximal", floor=.0001, cap=3000)
        # Prefix each resolution, including zero-area rows; never alter score/geometry.
        for collection in ("predictions", "degenerate_predictions"):
            raw[collection] = [dict(row, candidate_id=key + ":" + row["candidate_id"])
                               for row in raw[collection]]
    union = raws["640"]["predictions"] + raws["1280"]["predictions"]
    provenance = dict(evaluated_image_ids=sorted(expected))
    raws["late_fusion"] = dict(provenance=provenance, predictions=late_fusion(union),
        degenerate_predictions=raws["640"]["degenerate_predictions"] + raws["1280"]["degenerate_predictions"])
    raws["agreement1280"] = dict(provenance=provenance,
        predictions=agreement(raws["1280"]["predictions"], raws["640"]["predictions"]),
        degenerate_predictions=raws["1280"]["degenerate_predictions"])
    for name in METHODS[2:]:
        pilot.write(private_root / (name + "_raw.json"), raws[name])
    panels = dict(manifest["panels"])
    for name, members in (("pooled_adverse", ["fog", "night", "rain", "snow"]),
                          ("pooled_normal", [c + "_normal" for c in ("fog", "night", "rain", "snow")])):
        panels[name] = {**panels[members[0]], "images": [i for n in members for i in panels[n]["images"]],
                        "annotations": [a for n in members for a in panels[n]["annotations"]]}
    source = {name: pilot.pilot_evaluator(panels["source_selection"], raw) for name, raw in raws.items()}
    selections = {name: {str(rho): ev.select_threshold(rho) for rho in OBJECTIVES}
                  for name, ev in source.items()}
    public = dict(researcher="GPT Sol", base="c5284bdd9908111f4a6f4245917862e24dd9c38e",
        study="post-pilot development; stored predictions only", g0="PENDING",
        rules=dict(late_fusion="native score descending then resolution-tagged ID; class-aware IoU > .70; no new cap",
                   agreement1280="any positive human full-cache 640 witness IoU >= .50; preserve 1280 score/box",
                   zero_area="union both for fusion; 1280 for agreement; explicit FP outside overlap operations",
                   matching="unchanged ReferenceEvaluator/pilot_evaluator; provisional same-category crowd IoA .50"),
        source_objectives={name: {rho: {k: compact(v) if k in ("operating_point", "candidate_ceiling") else v
                                        for k, v in selection.items()} for rho, selection in objectives.items()}
                           for name, objectives in selections.items()}, panels={},
        resources=dict(new_allocation=False, cumulative_historical_displayed_CU=.98,
                       network_passes_per_alternative=2, historical_separate_loops_seconds=[25.191635, 40.23],
                       joint_latency="unmeasured; not cheaper than 1280"),
        provenance=dict(manifest_sha256=pilot.sha(manifest_path),
                        cache_sha256={k: pilot.sha(p) for k, p in paths.items()},
                        wrapper_sha256=pilot.sha(Path(__file__)),
                        evaluator_sha256=pilot.sha(pilot.REPO / "src/threshold_transfer/metrics.py"),
                        pilot_sha256=pilot.sha(Path(pilot.__file__)), numpy=np.__version__),
        postprocessing_counts={name: dict(positive=len(raw["predictions"]), zero_area=len(raw["degenerate_predictions"]))
                               for name, raw in raws.items()})
    print(pilot.json.dumps(dict(source={name: {rho: dict(status=s["status"], threshold=s["threshold"],
                  source_tp=s["operating_point"]["tp"] if s["operating_point"] else None)
                  for rho, s in sels.items()} for name, sels in selections.items()})), flush=True)
    private = {}
    for panel_name, panel in panels.items():
        evs = {name: source[name] if panel_name == "source_selection" else pilot.pilot_evaluator(panel, raws[name])
               for name in METHODS}
        gt = {a["annotation_id"]: a for a in panel["annotations"]
              if a["category"] == "human" and not (a["ignore"] or a["iscrowd"])}
        images = {i["image_id"]: i for i in panel["images"]}
        strata = {"all": set(gt)}
        # Only the already fixed size split and native person/rider diagnostics.
        strata["small_lt16"] = {k for k, a in gt.items() if a["bbox"][3] * 640 /
            max(images[a["image_id"]]["width"], images[a["image_id"]]["height"]) < 16}
        strata["larger_ge16"] = set(gt) - strata["small_lt16"]
        for category in ("person", "rider"):
            strata[category] = {k for k, a in gt.items() if a["attributes"]["pilot_native_category"] == category}
        ceilings = {name: ev.operating_point() for name, ev in evs.items()}
        points = {rho: {name: evs[name].operating_point(selections[name][rho]["threshold"])
                       if selections[name][rho]["status"] == "FEASIBLE" else None for name in METHODS}
                  for rho in map(str, OBJECTIVES)}

        def transition(old, new, key):
            if old is None or new is None:
                return None
            before, after = tp_ids(old), tp_ids(new)
            private[panel_name + "/" + key] = dict(gained=sorted(after-before), lost=sorted(before-after),
                retained=sorted(before & after), missed_both=sorted(set(gt)-before-after))
            return {label: dict(gt=len(ids), before=len(before & ids), after=len(after & ids),
                               gained=len((after-before) & ids), lost=len((before-after) & ids))
                    for label, ids in strata.items()}

        transitions = {}
        for alt in METHODS[2:]:
            for baseline in METHODS[:2]:
                key = alt + "_vs_" + baseline
                transitions[key] = dict(ceiling=transition(ceilings[baseline], ceilings[alt], key + "/ceiling"),
                    objectives={rho: transition(p[baseline], p[alt], key + "/" + rho) for rho, p in points.items()})
        # Distinguish gate geometry removal at the 1280 boundary from its own source reselection.
        gate_fixed = {rho: evs["agreement1280"].operating_point(selections["1280"][rho]["threshold"])
                      if selections["1280"][rho]["status"] == "FEASIBLE" else None for rho in points}
        gate_components = {rho: dict(at_1280_boundary=compact(fixed),
            removal=transition(points[rho]["1280"], fixed, "gate_removal/" + rho),
            reselection=transition(fixed, points[rho]["agreement1280"], "gate_reselection/" + rho))
                           for rho, fixed in gate_fixed.items()}
        oracle_ids = {name: oracle(panel, raws[name]["predictions"]) for name in ("1280",)}
        oracle_ids["union"] = oracle(panel, union)
        private[panel_name + "/oracle"] = {k: sorted(v) for k, v in oracle_ids.items()}
        result = dict(images=len(images), gt=len(gt),
            empty_images=sum(i not in {a["image_id"] for a in gt.values()} for i in images),
            ignored_or_crowd_gt=sum(a["ignore"] or a["iscrowd"] for a in panel["annotations"]),
            ceilings={name: compact(p) for name, p in ceilings.items()},
            objectives={rho: {name: compact(p) for name, p in points_at.items()} for rho, points_at in points.items()},
            transitions=transitions, gate_components=gate_components,
            geometric_oracle=dict(label="GT-aware maximum-cardinality one-to-one IoU .50; ignores score; not deployable recall",
                tp={name: len(ids) for name, ids in oracle_ids.items()},
                union_minus_1280_oracle=len(oracle_ids["union"])-len(oracle_ids["1280"]),
                union_minus_1280_reference=len(oracle_ids["union"])-ceilings["1280"]["tp"]))
        public["panels"][panel_name] = result
        pilot.write(private_root / (panel_name + "_evaluation_rows.json"), {name: ev.rows for name, ev in evs.items()})
        if panel_name in ("coco_reference", "pooled_adverse", "pooled_normal"):
            print(pilot.json.dumps({panel_name: dict(ceilings={k: (p["tp"], p["fp"]) for k, p in ceilings.items()},
                operating90={k: (p["tp"], p["fp"]) if p else None for k, p in points["0.9"].items()},
                oracle=result["geometric_oracle"])}), flush=True)
    pilot.write(private_root / "gt_transitions_private.json", private)
    # Keep detailed strata in private analysis; the public table needs only the
    # already assigned control panels, ceiling and primary .90 interpretation.
    pilot.write(private_root / "detailed_aggregate.json", public)
    for panel_name, result in public["panels"].items():
        for contrast in result["transitions"].values():
            for label, values in [("ceiling", contrast["ceiling"]), *contrast["objectives"].items()]:
                if values is not None and (panel_name not in ("coco_reference", "pooled_adverse", "pooled_normal")
                                           or label not in ("ceiling", "0.9")):
                    for key in list(values):
                        if key != "all":
                            del values[key]
        for rho, components in result["gate_components"].items():
            for component in ("removal", "reselection"):
                values = components[component]
                if values is not None and (panel_name not in ("coco_reference", "pooled_adverse", "pooled_normal") or rho != "0.9"):
                    for key in list(values):
                        if key != "all":
                            del values[key]
    public["resources"]["cpu_analysis_seconds"] = time.monotonic() - started
    # Machine-readable aggregate stays compact; the note supplies review tables.
    serialized = pilot.json.dumps(public, separators=(",", ":"), allow_nan=False) + "\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(serialized, encoding="utf-8")
    (private_root / "aggregate.json").write_text(serialized, encoding="utf-8")
    print("COMPLETE", destination, "CPU seconds", public["resources"]["cpu_analysis_seconds"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["tiny-check", "aggregate"])
    parser.add_argument("--root", default="C:/Users/Advait/autonomous-sys-research/outputs/colab")
    parser.add_argument("--output", default=str(pilot.REPO / "docs/gpt/2026-11-10_sol_scale_baselines_aggregate.json"))
    args = parser.parse_args()
    if args.mode == "tiny-check":
        tiny_check()
    else:
        aggregate(args.root, args.output)
