# Reference evaluation data contract — v1 proposal

This contract connects the first dataset-preflight and reference-evaluation implementations. It is an implementation proposal, not a frozen dataset ontology or proof that any annotations have been obtained. Both researchers should flag ambiguities directly to the peer before implementing incompatible assumptions.

## Canonical annotation JSON

```json
{
  "schema_version": "threshold-transfer-v1",
  "images": [
    {"image_id": "example", "file_name": "example.jpg", "width": null, "height": null,
     "group_id": null, "split": "val", "attributes": {"timeofday": "daytime", "weather": "clear"}}
  ],
  "annotations": [
    {"annotation_id": "example-1", "image_id": "example", "category": "pedestrian",
     "bbox": [10.0, 20.0, 15.0, 30.0], "ignore": false, "iscrowd": false,
     "attributes": {}}
  ],
  "provenance": {"dataset": "synthetic-example", "policy_status": "provisional"}
}
```

IDs are nonempty strings, unique in their own collections. Boxes use original-image `[x, y, width, height]`, finite coordinates and strictly positive width/height. Do not silently repair reversed or degenerate boxes. When dimensions are known, validate them and bounds according to an explicitly documented policy. `width`, `height`, `group_id` and source attributes stay null/missing when genuinely unknown; never infer independent recording IDs from filenames without verified provenance. Unknown dimensions prevent claims of image-coordinate validation, but do not prevent annotation-only inventory.

Retain empty images. Preserve native category names and attributes; do not silently equate pedestrian, rider and cyclist-plus-bike boxes. `ignore` represents an explicit declared policy, and `iscrowd` retains native crowd information. Preserve unresolved aliases and ignore behavior in provenance; no converter may claim the provisional mapping is the official evaluator policy. Invalid-but-labelled ACDC pixels are not automatically void/ignore regions.

## Prediction JSON

```json
{
  "schema_version": "threshold-transfer-v1",
  "predictions": [
    {"candidate_id": "example-p1", "image_id": "example", "category": "pedestrian",
     "bbox": [10.0, 20.0, 15.0, 30.0], "score": 0.8}
  ],
  "provenance": {"candidate_policy": "synthetic-example-only"}
}
```

Candidate IDs are globally unique nonempty strings. Scores are finite in `[0,1]`; stable IDs break equal-score ties. Every image reference must exist in the annotation manifest. Selection floors, caps, NMS/top-k, mappings and precision must eventually be recorded with real predictions. This scalar-score format supports reference recall/FPPI and binary TP-ECE only; it cannot reconstruct full-vector OCE.

## Evaluation boundary

Primary task: pedestrian-only under the declared eligibility/ignore policy. Sort candidates by descending score, then candidate ID; match greedily to the highest-IoU unmatched eligible same-class GT at IoU ≥ 0.50, breaking GT ties by annotation ID. Remaining unmatched predictions may be ignored under a declared intersection-over-prediction-area rule, after eligible GT matching. Crowd policy must be explicit. Include all images in FPPI, including those with no eligible GT. No eligible GT means undefined recall, not zero/perfect recall.

Choose the highest **observed source score boundary** achieving recall ≥ target, retaining entire tie groups. Report infeasible and undefined cases explicitly; never substitute zero or another target silently. Candidate-ceiling recall, signed clear-to-condition loss, target shortfall and threshold-removable misses are distinct, as specified in the research protocol. Outputs must use JSON null plus an explicit status for undefined quantities, never nonstandard NaN or infinity.

The preflight implementation inventories actual metadata, reports missing group IDs, and rejects role assignments that claim independence without verified groups. Dataset acquisition, final split manifests, model inference and empirical evaluation remain later milestones.
