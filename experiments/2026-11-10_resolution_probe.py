"""GPT Sol H2: one native 1280 intervention against retained 640 evidence.

Inference and zero-area accounting are imported unchanged from the completed
pilot. No packet preparation, sample selection, training or policy sweep.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "completed_pilot", Path(__file__).with_name("2026-11-10_transfer_pilot.py"))
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)


def aggregate(root, baseline, destination):
    """Public counts only; paired identities and raw candidates stay private."""
    root, baseline = Path(root), Path(baseline)
    manifest = pilot.read(root / "packet/manifest.json")
    config = pilot.read(root / "packet/config.json")
    assert pilot.sha(root / "packet/manifest.json") == config["manifest_sha256"]
    delivered = pilot.read(root / "code_record.json")
    assert pilot.read(root / "results/delivery_verified.json") == delivered
    for path, key in (("sent_script.py", "script_sha256"), ("sent_baseline.py", "baseline_script_sha256"),
                      ("packet/config.json", "config_sha256"), ("packet/manifest.json", "manifest_sha256")):
        assert pilot.sha(root / path) == delivered[key]
    # The delivered baseline is verified above; later Colab-only guards do not
    # rewrite the historical executed-code identity.
    status = pilot.read(root / "results/yolo11s_status.json")
    assert status["status"] == "COMPLETE"
    assert pilot.read(root / "results/process_status.json")["returncode"] == 0
    raws = [pilot.read(p / "results/yolo11s_maximal.json") for p in (baseline, root)]
    expected = {i["image_id"] for p in manifest["panels"].values() for i in p["images"]}
    assert len(expected) == 700
    for raw in raws:
        ids = raw["provenance"]["evaluated_image_ids"]
        assert len(ids) == len(set(ids)) == 700 and set(ids) == expected
    native_files = sorted((root / "results").glob("yolo11s_maximal_native_batch_*.json"))
    native = [i for f in native_files for i in pilot.read(f)]
    assert len(native_files) == 88 and len(native) == 700
    assert {i["image_id"] for i in native} == expected
    assert sum(len(i["xyxy"]) for i in native) == status["coverage"]["maximal"]["candidate_count"]
    panels = dict(manifest["panels"])
    for name, members in (("pooled_adverse", ["fog", "night", "rain", "snow"]),
                          ("pooled_normal", [c + "_normal" for c in ("fog", "night", "rain", "snow")])):
        panels[name] = {**panels[members[0]],
                        "images": [i for n in members for i in panels[n]["images"]],
                        "annotations": [a for n in members for a in panels[n]["annotations"]]}
    evaluators = {name: [pilot.pilot_evaluator(panel, raw) for raw in raws]
                  for name, panel in panels.items()}
    private = {}

    def ids(point):
        return {r["annotation_id"] for r in point["matches"] if r["outcome"] == "TP"}

    def compact(point):
        if point is None:
            return None
        return {k: point[k] for k in ("threshold", "image_count", "eligible_gt", "tp", "fp", "fn", "ignored",
                                      "retained_candidates", "recall", "fppi")} | {
            "zero_area_fp": sum(r.get("native_zero_area", False) for r in point["matches"])}

    def transition(old, new, eligible, key):
        old_ids, new_ids = ids(old) & eligible, ids(new) & eligible
        gained, lost = new_ids - old_ids, old_ids - new_ids
        private[key] = {"gained": sorted(gained), "lost": sorted(lost),
                        "retained": sorted(old_ids & new_ids), "missed_both": sorted(eligible - old_ids - new_ids)}
        n = len(eligible)
        misses = n - len(old_ids)
        return dict(gt=n, tp_before=len(old_ids), tp_after=len(new_ids), gained=len(gained), lost=len(lost),
                    net_tp=len(gained)-len(lost), delta_recall=(len(gained)-len(lost))/n if n else None,
                    residual_misses1280=n-len(new_ids), baseline_misses=misses,
                    net_gain_per_baseline_miss=(len(gained)-len(lost))/misses if misses else None)

    source_selections = [[ev.select_threshold(r) for r in config["objectives"]]
                         for ev in evaluators["source_selection"]]
    public = dict(researcher="GPT Sol", base=config["base"], hypothesis="H2", g0="PENDING",
                  aggregation_code_record=dict(script_sha256=pilot.sha(__file__),
                                               baseline_script_sha256=pilot.sha(pilot.__file__)),
                  config=config, panels={}, source_objectives={}, native_status=status,
                  validation=dict(exact_images=700, native_batches=88, child_returncode=0),
                  limitations=["Finite pipeline ceiling, not detector capacity; resolution also changes decoding, NMS and clipping.",
                               "COCO not verified clear/day; no IID CI, primary BDD, novelty or causal night claim.",
                               "Normal/adverse pairing is scene/view only, not person correspondence.",
                               "GT size bins are diagnostic and not a deployable policy; unequal baseline headroom affects H2 interpretation.",
                               "FP cannot be assigned to GT size/person/rider strata; panel FPPI includes all empty images."])
    for j, rho in enumerate(config["objectives"]):
        public["source_objectives"][str(rho)] = {}
        for res, selections in zip((640, 1280), source_selections):
            sel = selections[j]
            public["source_objectives"][str(rho)][str(res)] = {
                k: (compact(sel[k]) if k in ("operating_point", "candidate_ceiling") else sel[k]) for k in sel}
    for name, panel in panels.items():
        ev0, ev1 = evaluators[name]
        ceiling0, ceiling1 = ev0.operating_point(), ev1.operating_point()
        images = {i["image_id"]: i for i in panel["images"]}
        gt = {a["annotation_id"]: a for a in panel["annotations"]
              if a["category"] == "human" and not (a["ignore"] or a["iscrowd"])}
        eligible = set(gt)
        heights = {key: a["bbox"][3]*640/max(images[a["image_id"]]["width"], images[a["image_id"]]["height"])
                   for key, a in gt.items()}
        strata = {"all": eligible, "small_lt16": {k for k, h in heights.items() if h < 16},
                  "larger_ge16": {k for k, h in heights.items() if h >= 16}}
        for label, lo, hi in (("lt8", 0, 8), ("8to16", 8, 16), ("16to32", 16, 32), ("ge32", 32, float("inf"))):
            strata[label] = {k for k, h in heights.items() if lo <= h < hi}
        for category in ("person", "rider"):
            group = {k for k, a in gt.items() if a["attributes"]["pilot_native_category"] == category}
            strata[category] = group
            for binname in ("lt8", "8to16", "16to32", "ge32"):
                strata[category + "_" + binname] = group & strata[binname]
        result = dict(images=len(images), gt=len(gt), empty_images=sum(not any(a["image_id"] == i for a in gt.values()) for i in images),
                      ceiling640=compact(ceiling0), ceiling1280=compact(ceiling1),
                      delta_M=ceiling1["recall"]["value"]-ceiling0["recall"]["value"] if gt else None,
                      delta_ceiling_fp=ceiling1["fp"]-ceiling0["fp"],
                      strata={key: transition(ceiling0, ceiling1, members, name+"/ceiling/"+key) for key, members in strata.items()},
                      objectives={})
        for j, rho in enumerate(config["objectives"]):
            old, new = source_selections[0][j], source_selections[1][j]
            p0 = ev0.operating_point(old["threshold"]) if old["status"] == "FEASIBLE" else None
            fixed = ev1.operating_point(old["threshold"]) if old["status"] == "FEASIBLE" else None
            reselected = ev1.operating_point(new["threshold"]) if new["status"] == "FEASIBLE" else None
            entry = dict(baseline640=compact(p0), resolution1280_old_boundary=compact(fixed),
                         resolution1280_new_boundary=compact(reselected))
            for label, a, b in (("direct_resolution", p0, fixed), ("source_reselection", fixed, reselected),
                                ("total", p0, reselected)):
                entry[label] = (dict(delta_recall=b["recall"]["value"]-a["recall"]["value"] if gt else None,
                                     delta_tp=b["tp"]-a["tp"], delta_fp=b["fp"]-a["fp"],
                                     delta_fppi=b["fppi"]["value"]-a["fppi"]["value"],
                                     transitions=transition(a, b, eligible, name+"/"+str(rho)+"/"+label))
                                if a is not None and b is not None else None)
            result["objectives"][str(rho)] = entry
        public["panels"][name] = result
    adverse = public["panels"]["pooled_adverse"]
    assert adverse["images"] == 128 and adverse["gt"] == 216
    small, larger = (adverse["strata"][k] for k in ("small_lt16", "larger_ge16"))
    testable = small["gt"] > 0 and larger["gt"] > 0
    public["H2"] = dict(status="TESTABLE" if testable else "UNTESTABLE", small=small, larger=larger,
                        supports=(small["delta_recall"] > 0 and small["delta_recall"] > larger["delta_recall"]) if testable else None,
                        rule="positive net small-stratum ceiling TP gain/GT, strictly greater than complement")
    operation = pilot.read(root / "operation.json")
    def observed(log, pattern):
        match = re.search(pattern, (root / log).read_text(encoding="utf-8"))
        return float(match.group(1)) if match else None
    before = observed("before_usage.log", r"Current balance:\s*([\d.]+)")
    after = observed("final_usage.log", r"Current balance:\s*([\d.]+)")
    public["execution"] = {k: v for k, v in operation.items() if k != "events"} | {
        "displayed_balance_before_CU": before, "displayed_balance_after_CU": after,
        "displayed_delta_CU": round(before-after, 2),
        "cumulative_displayed_CU": round(.55+before-after, 2),
        "final_active_assignments": observed("final_usage.log", r"Active assignments:\s*(\d+)"),
        "final_usage_rate_CU_hr": observed("final_usage.log", r"Usage rate:\s*([\d.]+)")}
    public["hashes"] = {"wrapper": pilot.sha(Path(__file__)), "baseline_code": pilot.sha(Path(pilot.__file__)),
                         "manifest": pilot.sha(root/"packet/manifest.json"),
                         "config": pilot.sha(root/"packet/config.json"),
                         "baseline640_predictions": pilot.sha(baseline/"results/yolo11s_maximal.json"),
                         "resolution1280_predictions": pilot.sha(root/"results/yolo11s_maximal.json"),
                         "evidence_archive": pilot.sha(root/"evidence_final.tar.gz")}
    public["sent_code_record"] = pilot.read(root/"code_record.json")
    public["cap_saturation_panels"] = {name: sum(i["candidate_count"] == 3000 and i["image_id"] in
        {im["image_id"] for im in panel["images"]} for i in raws[1]["measurements"])
        for name, panel in panels.items()}
    public["figure_provenance"] = {"recipe_sha256": pilot.sha(root/"figure.ps1"),
                                   "method": "CPU-only Windows .NET Charting; plotting recipe retained privately"}
    pilot.write(root / "gt_transitions_private.json", private)
    pilot.write(root / "artifact_hashes.json", {p.name: pilot.sha(p) for p in (root/"results").iterdir() if p.is_file()})
    pilot.write(destination, public)
    print(pilot.json.dumps(dict(H2=public["H2"], source=public["source_objectives"], execution=public["execution"])))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["infer", "aggregate"])
    parser.add_argument("root")
    parser.add_argument("--baseline")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.mode == "aggregate":
        aggregate(args.root, args.baseline, args.output)
        raise SystemExit(0)
    pilot.require_colab()
    config = pilot.read(Path(args.root) / "config.json")
    assert config["imgsz"] == 1280 and config["batch"] == 8
    assert config["policies"] == [dict(id="maximal", floor=.0001, cap=3000)]
    assert pilot.sha(Path(args.root) / "manifest.json") == config["manifest_sha256"]
    pilot.infer(args.root, "yolo11s")
