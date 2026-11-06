"""Role-aware JSON CLI for GPT's reference operating-point evaluation.

Run with ``python -m threshold_transfer.evaluate --help``. No inference, official
AP, uncertainty estimation or calibration fitting is performed by this module.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

from .metrics import ReferenceEvaluator, held_out_loss_decomposition, target_gap_decomposition
from .schema import identifier, json_value, load_json

ROLES = ("source_selection", "clear_test", "target_test")


def _role_policy(evaluators, policy):
    """Check declared identities/groups; evidence is declared, not authenticated.

    Image identity is (dataset_id, image_id); group identity is
    (group_namespace, group_id). Namespace honesty and unrecorded dependencies
    cannot be established from these JSON documents.
    """
    mode = policy.get("population_mode")
    if mode not in ("diagnostic", "held_out"):
        raise ValueError("population_mode must be diagnostic or held_out")
    relationship = policy.get("test_relationship")
    if relationship not in ("disjoint", "paired"):
        raise ValueError("test_relationship must be disjoint or paired")
    roles = policy.get("roles")
    if not isinstance(roles, dict) or set(roles) != set(ROLES):
        raise ValueError("policy.roles must contain exactly source_selection, clear_test, target_test")
    populations, limitations, counts = {}, [], {}
    namespaces = {}
    for role in ROLES:
        declaration = roles[role]
        if not isinstance(declaration, dict):
            raise ValueError("each role declaration must be an object")
        dataset = identifier(declaration.get("dataset_id"), "dataset_id")
        namespace = identifier(declaration.get("group_namespace"), "group_namespace")
        identifier(declaration.get("population"), "population description")
        evidence = declaration.get("group_provenance")
        if evidence is not None:
            identifier(evidence, "group_provenance")
        if dataset in namespaces and namespaces[dataset] != namespace:
            raise ValueError("one dataset_id cannot use inconsistent group namespaces across roles")
        namespaces[dataset] = namespace
        doc = evaluators[role].annotations
        native_dataset = doc["provenance"].get("dataset")
        if native_dataset is not None and native_dataset != dataset:
            raise ValueError("dataset_id must agree with annotation provenance.dataset")
        filters = declaration.get("attribute_filter", {})
        if not isinstance(filters, dict) or not all(isinstance(k, str) for k in filters):
            raise ValueError("attribute_filter must be an object")
        image_keys, group_keys, missing = set(), set(), 0
        for image in doc["images"]:
            image_keys.add((dataset, image["image_id"]))
            if any(k not in image.get("attributes", {}) or image["attributes"][k] != v
                   for k, v in filters.items()):
                raise ValueError(f"{role} includes image outside declared attribute_filter")
            if image.get("group_id") is None:
                missing += 1
            else:
                group_keys.add((namespace, image["group_id"]))
        if missing or evidence is None:
            if mode == "held_out":
                raise ValueError(f"{role}: held_out requires complete group IDs and group provenance")
            limitations.append(f"{role}: diagnostic only; {missing} missing group IDs; "
                               f"group provenance {'missing' if evidence is None else 'declared'}; independence unverified.")
        populations[role] = (image_keys, group_keys)
        counts[role] = {"images": len(image_keys), "groups": len(group_keys), "missing_group_ids": missing}
    pairs = [("source_selection", "clear_test"), ("source_selection", "target_test")]
    if relationship == "disjoint":
        pairs.append(("clear_test", "target_test"))
    for left, right in pairs:
        for index, unit in ((0, "image"), (1, "group")):
            if populations[left][index] & populations[right][index]:
                raise ValueError(f"declared {unit} overlap between {left} and {right}")
    limitations.append("Role/population/group provenance is caller-declared; unrecorded dependence, "
                       "prior development exposure and dishonest namespaces cannot be detected.")
    limitations.append("Population descriptions label roles; only supplied attribute_filter entries "
                       "are checked. Clear/daytime semantics are not inferred from filenames.")
    return {"mode": mode, "test_relationship": relationship, "counts": counts,
            "status": "DECLARED_HELD_OUT" if mode == "held_out" else "DIAGNOSTIC",
            "limitations": limitations}


def evaluate_transfer(documents, *, policy, target_recall):
    """documents maps each role to (canonical annotations, canonical predictions).

    No test labels participate in threshold selection. Selection failure propagates
    as null operating points and explicit status; test ceilings remain diagnostics.
    """
    json_value(policy)
    if not isinstance(policy, dict) or set(documents) != set(ROLES):
        raise ValueError("expected policy object and exactly the three named roles")
    for required in ("categories", "ignore_policy", "bounds_policy"):
        if required not in policy:
            raise ValueError(f"explicit {required} policy is required")
    evaluators = {role: ReferenceEvaluator(*documents[role], categories=policy["categories"],
                  ignore_policy=policy["ignore_policy"], bounds_policy=policy["bounds_policy"])
                  for role in ROLES}
    separation = _role_policy(evaluators, policy)
    selection = evaluators["source_selection"].select_threshold(target_recall)
    populations, provenance = {}, {}
    for role in ROLES:
        evaluator = evaluators[role]
        ceiling = evaluator.operating_point()
        point = evaluator.operating_point(selection["threshold"]) if selection["status"] == "FEASIBLE" else None
        populations[role] = {"status": "EVALUATED" if point is not None else selection["status"],
            "operating_point": point, "candidate_ceiling": ceiling,
            "target_gaps": target_gap_decomposition(target_recall,
                point["recall"]["value"] if point else None, ceiling["recall"]["value"]),
            "limitations": evaluator.limitations}
        provenance[role] = {"annotations": copy.deepcopy(evaluator.annotations["provenance"]),
                            "predictions": copy.deepcopy(evaluator.predictions["provenance"])}
    clear, target = populations["clear_test"], populations["target_test"]
    loss = held_out_loss_decomposition(
        clear["operating_point"]["recall"]["value"] if clear["operating_point"] else None,
        target["operating_point"]["recall"]["value"] if target["operating_point"] else None,
        clear["candidate_ceiling"]["recall"]["value"], target["candidate_ceiling"]["recall"]["value"])
    return {"schema_version": "threshold-transfer-reference-result-v1", "researcher": "GPT",
            "protocol": "greedy_score_prefix_iou_0.50_reference_not_official_AP",
            "units": "recall/precision/gaps in fractions; FPPI in false positives per image",
            "g0_status": "PENDING", "policy": copy.deepcopy(policy),
            "matching_policy": {"iou_threshold": 0.50, "candidate_order": "score descending, candidate_id ascending",
                "gt_order": "IoU descending, annotation_id ascending", "eligible_gt_first": True,
                "ignore_overlap": "intersection / prediction area >= 0.50; reusable regions",
                "ignore_policy": policy["ignore_policy"]},
            "role_validation": separation, "selection": selection, "populations": populations,
            "held_out_loss": loss, "input_provenance": provenance,
            "pending": ["Official AP", "Full OCE", "Published LaECE", "Bootstrap coverage", "Empirical G0 prerequisites"]}


def _file_record(path):
    path = Path(path)
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for role in ROLES:
        prefix = role.replace("_", "-")
        parser.add_argument(f"--{prefix}-annotations", required=True, type=Path)
        parser.add_argument(f"--{prefix}-predictions", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--target-recall", required=True, type=float)
    parser.add_argument("--output", type=Path, help="default: stdout")
    args = parser.parse_args(argv)
    try:
        documents, files = {}, {}
        input_paths = [args.policy]
        for role in ROLES:
            ann = getattr(args, f"{role}_annotations")
            pred = getattr(args, f"{role}_predictions")
            documents[role] = (load_json(ann), load_json(pred))
            files[role] = {"annotations": _file_record(ann), "predictions": _file_record(pred)}
            input_paths.extend((ann, pred))
        if args.output is not None and args.output.resolve() in {p.resolve() for p in input_paths}:
            raise ValueError("output cannot overwrite an input file")
        result = evaluate_transfer(documents, policy=load_json(args.policy), target_recall=args.target_recall)
        result["input_files"] = files
        result["policy_file"] = _file_record(args.policy)
        rendered = json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0
    except (ValueError, OSError, TypeError) as error:
        sys.stderr.write(json.dumps({"status": "ERROR", "error": str(error)}, allow_nan=False) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
