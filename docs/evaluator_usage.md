# Reference evaluator: data and provenance requirements

This implementation supports deterministic reference recall/precision/FPPI, candidate ceilings, observed-score threshold selection and gap decompositions. It is not official COCO/KITTI AP, full OCE, published LaECE or an uncertainty guarantee.

Set `PYTHONPATH=src`, then run `python -m unittest discover -s tests` and `python -m threshold_transfer.evaluate --help`. The [implementation note](gpt/tooling_implementation.md) gives CLI examples and attributed development history. The [canonical contract](data_contract.md) describes records.

## Held-out declarations

Every annotation document needs `provenance.dataset` matching the role policy. Every prediction document needs `provenance.evaluated_image_ids` exactly equal to the manifest population, including empty scenes. Missing coverage/native identity fails held-out mode.

Every role also needs an identical `provenance.inference_pipeline` object, with these minimum fields:

```json
{
  "model_id": "example-only-not-a-verified-artifact",
  "checkpoint_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "preprocessing": "example exact resize, normalization and coordinate policy",
  "precision": "fp32",
  "category_mapping": {},
  "candidate_policy": {"score_floor": 0.001, "max_detections": 300}
}
```

This illustrates the schema; do not copy it as real provenance. Actual declarations must include all relevant NMS/top-k, query/class selection, caps, mappings and caching/rounding settings. Additional fields are compared too. Declared cache floors/caps are cross-checked when supplied as `cache_policy.score_floor` and `cache_policy.max_raw_det`. A selected threshold below a recorded floor fails held-out mode. Candidate ceilings remain conditional on recorded selection/budgets.

These checks compare caller-declared evidence; they do not authenticate weights, inference execution, grouping or provenance. `DECLARED_HELD_OUT` does not mean an external audit or G0 passed. Source selection must be image/group-disjoint from both tests. Paired tests may share groups, but not image identities. Verified group provenance remains necessary.

## Diagnostic replay

Previously inspected COCO/KITTI caches lack verified groups and complete pipeline declarations. Use diagnostic mode with explicit category, ignore and candidate policies. Missing/different pipelines and below-floor censoring appear in role limitations. Never fabricate provenance/groups to pass held-out checks.

Results preserve input provenance, including cache settings and excluded-row counts. Match rows are omitted from transfer JSON by default; use `--include-matches` only when needed. The low-level operating-point API still exposes rows. Multiple exact classes share one threshold but match within class; a human-union panel requires explicit relabelling.

Undefined values use null plus status. Infeasible source targets do not silently fall back. Passing tests, cache replay and PR publication do not establish an empirical gate.
