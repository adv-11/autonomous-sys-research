"""GPT Sol: bounded CPU review of retained predictions; no inference or fitting.

Run with an existing Python >=3.11, -B, ROOT and PRIVATE_OUTPUT arguments.
Only source/reference/night are matched once per head. Public output has no IDs.
"""
import argparse
from bisect import bisect_right
from collections import Counter
import importlib.util
from itertools import groupby
import json
from pathlib import Path
import statistics
import sys

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pilot", REPO / "experiments/2026-11-10_transfer_pilot.py")
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)
read, write, sha = pilot.read, pilot.write, pilot.sha
HEADS = ("yolo26s_o2o", "yolo26s_o2m")
PANELS = ("source_selection", "coco_reference", "night")


class Prefix:
    def __init__(self, rows):
        self.scores, self.tp, self.fp, self.ignored = [], [0], [0], [0]
        for score, group in groupby(rows, key=lambda r: r["score"]):
            counts = Counter(r["outcome"] for r in group)
            self.scores.append(-score)
            for key in ("tp", "fp", "ignored"):
                values = getattr(self, key)
                values.append(values[-1] + counts[key.upper()])

    def point(self, threshold=None):
        index = len(self.scores) if threshold is None else bisect_right(self.scores, -threshold)
        return dict(threshold=threshold, tp=self.tp[index], fp=self.fp[index], ignored=self.ignored[index])

    def oracle(self, budget):
        # Whole observed groups only. On equal TP prefer fewer FP, then the
        # highest boundary. Empty prefix is allowed and has threshold=None.
        feasible = [i for i, fp in enumerate(self.fp) if fp <= budget]
        index = min(feasible, key=lambda i: (-self.tp[i], self.fp[i], i))
        return dict(budget=budget, threshold=-self.scores[index-1] if index else None,
                    tp=self.tp[index], fp=self.fp[index], ignored=self.ignored[index])


def span(values):
    return dict(min=min(values), median=statistics.median(values), max=max(values))


def main(root, private, public):
    manifest = read(root / "packet/manifest.json")
    panels = manifest["panels"]
    old_path = root.parent / "empirical_20261110/packet/manifest.json"
    old = read(old_path)
    assert sha(old_path) == manifest["original_manifest_sha256"]
    assert all(panels[k] == old["panels"][k] for k in PANELS[:2])
    conditions = ("fog", "night", "rain", "snow")
    paths = lambda p: {i["file_name"] for i in p["images"]}
    previous = set().union(*(paths(old["panels"][k]) for k in conditions))
    new = set().union(*(paths(panels[k]) for k in conditions))
    assert len(previous) == 128 and len(new) == 278 and not previous & new
    # The manifest selects exactly the official remaining paths, not a GT subset.
    from threshold_transfer.acdc import AGGREGATE_FILES
    adverse = read(root.parents[2] / "data/acdc/extracted" / AGGREGATE_FILES[("val", False)])
    official = {"images/acdc/" + i["file_name"] for i in adverse["images"]}
    assert new == official - previous
    images = {i["image_id"]: i["file_name"] for p in panels.values() for i in p["images"]}
    assert len(images) == len(set(images.values())) == 933
    published = read(REPO / "docs/gpt/2026-11-11_sol_dual_head_transfer.json")
    fixed, summary, provenance = {}, {}, {}
    private.mkdir(parents=True, exist_ok=True)
    gt_by_image = Counter(a["image_id"] for a in panels["source_selection"]["annotations"]
                          if not (a["ignore"] or a["iscrowd"]))
    for head in HEADS:
        raw_path = root / "results" / (head + "_maximal.json")
        raw = read(raw_path)
        ids = raw["provenance"]["evaluated_image_ids"]
        assert len(ids) == len(set(ids)) == 933 and set(ids) == set(images)
        status = read(root / "results" / (head + "_status.json"))
        assert status["status"] == "COMPLETE" and status["checkpoint_sha256"] == published["config"]["models"]["yolo26s"]["sha256"]
        provenance[head] = dict(predictions_sha256=sha(raw_path), status_sha256=sha(root / "results" / (head + "_status.json")))
        fixed[head], summary[head] = {}, {}
        for name in PANELS:
            ev = pilot.pilot_evaluator(panels[name], raw)
            prefix = Prefix(ev.rows)
            fixed[head][name] = dict(ev=ev, prefix=prefix)
            with (private / f"{head}_{name}_rows.jsonl").open("w", encoding="utf-8") as stream:
                for row in ev.rows:
                    stream.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
            if name == "source_selection":
                selected = ev.select_threshold(.9)
                threshold = selected["threshold"]
                assert selected["status"] == "FEASIBLE"
                assert threshold == published["heads"][head]["source_selection"]["threshold"]
            op = prefix.point(threshold)
            ceiling = prefix.point()
            for label, point in (("operating", op), ("ceiling", ceiling)):
                expected = published["heads"][head]["panels"][name][label]
                assert all(point[k] == expected[k] for k in ("tp", "fp", "ignored"))
                check = ev.operating_point(point["threshold"])
                assert all(point[k] == check[k] for k in ("tp", "fp", "ignored"))
            summary[head][name] = dict(gt=ev.gt_count, operating=op, ceiling=ceiling)
        summary[head]["night_oracles"] = [fixed[head]["night"]["prefix"].oracle(b) for b in (37, 58)]
        for oracle in summary[head]["night_oracles"]:
            assert oracle["threshold"] is not None
            assert oracle["fp"] <= oracle["budget"]
            assert oracle["tp"] == fixed[head]["night"]["ev"].operating_point(oracle["threshold"])["tp"]
    sets = [{r["annotation_id"] for r in fixed[h]["night"]["ev"].rows if r["outcome"] == "TP"} for h in HEADS]
    assert (len(sets[0] & sets[1]), len(sets[0] - sets[1]), len(sets[1] - sets[0])) == (71, 10, 3)
    traces = []
    for image in panels["source_selection"]["images"]:
        deleted = image["image_id"]
        trace = dict(deleted_image_id=deleted, removed_gt=gt_by_image[deleted], heads={})
        for head in HEADS:
            ev = fixed[head]["source_selection"]["ev"]
            remaining_gt = ev.gt_count - gt_by_image[deleted]
            # Scores retain the evaluator's exact descending order and precision.
            # First attaining TP belongs to the highest feasible observed tie group.
            tp_scores = [r["score"] for r in ev.rows if r["outcome"] == "TP" and r["image_id"] != deleted]
            needed = (9 * remaining_gt + 9) // 10
            feasible = remaining_gt > 0 and len(tp_scores) >= needed
            result = dict(feasible=feasible, source_gt=remaining_gt)
            if feasible:
                t = tp_scores[needed - 1]
                removed = Prefix([r for r in ev.rows if r["image_id"] == deleted]).point(t)
                full = fixed[head]["source_selection"]["prefix"].point(t)
                source = {k: full[k] - removed[k] for k in ("tp", "fp", "ignored")}
                assert source["tp"] * 10 >= 9 * remaining_gt
                assert sum(s > t for s in tp_scores) * 10 < 9 * remaining_gt
                result.update(threshold=t, source=source, removed_at_new_threshold=removed)
                for name in PANELS[1:]:
                    result[name] = fixed[head][name]["prefix"].point(t)
            trace["heads"][head] = result
        both = all(r["feasible"] for r in trace["heads"].values())
        trace["both_source_feasible"] = both
        if both:
            for name in PANELS[1:]:
                trace[name + "_gap"] = (trace["heads"][HEADS[0]][name]["tp"] - trace["heads"][HEADS[1]][name]["tp"]) / fixed[HEADS[0]][name]["ev"].gt_count
            trace["reference_clause"] = abs(trace["coco_reference_gap"]) <= .02
            trace["night_clause"] = abs(trace["night_gap"]) >= .05
        trace["H4_screen"] = both and trace["reference_clause"] and trace["night_clause"]
        traces.append(trace)
    write(private / "paired_source_deletions.json", traces)
    loo = dict(deletions=len(traces), clause_counts={k: sum(t.get(k, False) for t in traces) for k in
               ("both_source_feasible", "reference_clause", "night_clause", "H4_screen")}, heads={})
    feasible_traces = [t for t in traces if t["both_source_feasible"]]
    loo["signed_gap_pp"] = {name: span([100*t[name+"_gap"] for t in feasible_traces]) for name in PANELS[1:]}
    baseline_thresholds = {h: summary[h]["source_selection"]["operating"]["threshold"] for h in HEADS}
    baseline_gaps = {p: (summary[HEADS[0]][p]["operating"]["tp"] - summary[HEADS[1]][p]["operating"]["tp"])
                     / summary[HEADS[0]][p]["gt"] for p in PANELS[1:]}
    loo["source_influence"] = dict(
        either_threshold_changed=sum(any(t["heads"][h]["threshold"] != baseline_thresholds[h] for h in HEADS) for t in feasible_traces),
        gap_changed={p: sum(t[p+"_gap"] != baseline_gaps[p] for t in feasible_traces) for p in PANELS[1:]},
        removed_gt=span([t["removed_gt"] for t in traces]),
        minimum_night_gap_removed_gt=sorted(t["removed_gt"] for t in feasible_traces if t["night_gap"] == min(z["night_gap"] for z in feasible_traces)))
    for head in HEADS:
        results = [t["heads"][head] for t in traces if t["heads"][head]["feasible"]]
        baseline = summary[head]["source_selection"]["operating"]["threshold"]
        counts = Counter(r["threshold"] for r in results)
        loo["heads"][head] = dict(feasible=len(results), threshold=span([r["threshold"] for r in results]),
            threshold_changed=sum(r["threshold"] != baseline for r in results),
            threshold_frequencies=[dict(threshold=t, deletions=n) for t, n in sorted(counts.items(), reverse=True)],
            source_tp=span([r["source"]["tp"] for r in results]),
            target_counts={p: {k: span([r[p][k] for r in results]) for k in ("tp", "fp")} for p in PANELS[1:]})
    operation = read(root / "operation.json")
    public_result = dict(reviewer="GPT Sol", base="6e3722999ad4dae6dd6128b6e0d3cbb5a3d9d2df",
        contribution="6f1956d050158ab271e34d30064dfa255668f426", integrated="22f77f9c0fd05a02c6cc2a54497a5d444279d95f",
        primary_H4="SUPPORT, unchanged", diagnostic_status="POST_HOC; oracle NONDEPLOYABLE; deletion deterministic sensitivity",
        provenance=dict(manifest_sha256=sha(root/"packet/manifest.json"), original_manifest_sha256=sha(old_path),
                        config_sha256=sha(root/"packet/config.json"), script_sha256=sha(__file__),
                        reference_metrics_sha256=sha(REPO/"src/threshold_transfer/metrics.py"), inputs=provenance,
                        python=sys.version.split()[0], matching_passes=6, inference_calls=0),
        checks=dict(new_target_paths=278, previous_excluded=128, exact_images_per_head=933,
                    night_ceiling_shared=71, night_ceiling_unique=[10,3]),
        reproduced=summary, paired_source_leave_one_out=loo,
        recorded_resources={k: operation[k] for k in ("elapsed_seconds", "displayed_delta_CU", "admission_rate_CU_hr", "owned_teardown_verified")})
    def privacy(value):
        if isinstance(value, dict):
            assert not set(value) & {"image_id", "deleted_image_id", "candidate_id", "annotation_id", "matches", "bbox", "evaluated_image_ids"}
            for child in value.values(): privacy(child)
        elif isinstance(value, list):
            for child in value: privacy(child)
    privacy(public_result)
    write(public, public_result)
    print(json.dumps(dict(primary=public_result["primary_H4"], oracles={h: summary[h]["night_oracles"] for h in HEADS}, loo=loo), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("private", type=Path)
    parser.add_argument("--public", type=Path, default=REPO/"docs/reviews/2026-11-11_dual_head_cached_controls.json")
    args = parser.parse_args()
    main(args.root, args.private, args.public)
