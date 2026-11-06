# GPT reference evaluator implementation

**Author/work attribution:** GPT, 2026-11-05 (local date; exchanges continued on
2026-11-06 UTC). Prepared on isolated base
`4fa07a72c7ae2a2804814115a4887dd9bdce220d`. This implements the
[peer-discussed protocol](protocol.md) against the existing
[canonical contract](../data_contract.md). **G0 remains pending.** All numerical
examples and tests below are synthetic, not measured weather-transfer results.

## Scope and interface

GPT added only `metrics.py`, `evaluate.py`, optional `schema.py`, the two assigned
test files and this note. There is no dependency on Claude's future `data.py`.
No shared contract, package initializer or packaging metadata was changed.

```python
from threshold_transfer.metrics import ReferenceEvaluator

ev = ReferenceEvaluator(annotations, predictions,
                        categories=["Pedestrian"],
                        ignore_policy="same_category_ioa",
                        bounds_policy="strict_known")
ceiling = ev.operating_point()            # all retained cache candidates
selection = ev.select_threshold(0.90)     # no fallback for unavailable target
point = ev.operating_point(0.8)           # score >= 0.8, whole ties
```

`categories` selects exact native names, with no implicit aliases or merging.
Multiple selected categories are pooled for counts but matched within category.
This is not the merged-human panel: that task requires explicit, provenance-recorded relabelling of GT and predictions into one human category.
Candidate/annotation IDs are globally unique within their respective collections.
Boxes are finite positive `[x,y,width,height]`; scores are finite in `[0,1]`.
Malformed values, duplicate IDs/JSON keys, unknown image references, numeric
overflow/unrepresentable box extents and nonfinite metadata are rejected. All
records are validated before category filtering. `ignore` and `iscrowd` must be
explicit booleans. Optional attributes must be objects; native attributes remain
opaque. `area` and image `split` are not required.

`strict_known` checks each known image dimension without clipping. Unknown
dimensions allow evaluation with a bounds-validation limitation.
`allow_outside` explicitly preserves out-of-image boxes unchanged. Neither mode
repairs reversed/degenerate boxes. Supplied `provenance.evaluated_image_ids` must
be unique and exactly equal the annotation image set, including empty images;
otherwise evaluation fails. Its absence is allowed by the minimal canonical
contract but reported as unverified inference coverage.

Matching sorts by descending score, ascending candidate ID, then assigns the
highest-IoU unmatched eligible same-category GT at IoU >= 0.50, breaking equal
IoUs by annotation ID. Prefix labels are stable when lower-score suffixes are
removed. This is greedy matching, not maximum-cardinality matching.

The default ignore policy `reject` rejects any ignored/crowd annotations.
`same_category_ioa` and `all_categories_ioa` exclude flagged GT from recall and
let unmatched predictions be absorbed by matching-category or any-category
regions, respectively, at intersection/prediction-area >= 0.50. Regions are
reusable; eligible matching always takes priority. This research rule is not
official COCO AP or KITTI scoring. KITTI neighbour/difficulty one-to-one IoU
ignores must not silently become these reusable regions.

FPPI divides FP by **all manifest images**. Recall is pooled TP/eligible GT, and
is undefined with no eligible GT. Precision and simple binary TP-ECE are
undefined with no nonignored predictions; FPPI is undefined for zero images.
Quantities use `{value: null, status: "UNDEFINED"}` rather than NaN.

Selection takes a target in `(0,1]`, selects the highest observed source score
achieving recall >= target and retains its entire tie group. Output includes the
next lower distinct score, boundary gap, tie count, retained-candidate ceiling,
headroom and descriptive LOW_HEADROOM flag (<0.02). `INFEASIBLE` and `UNDEFINED`
have null thresholds and no substituted operating point. Test ceilings are
still reported separately. Gaps and signed held-out losses use the exact
protocol decompositions; all are fractions, not percentage points.

`simple_binary_tp_ece` uses TP=1/FP=0 labels and excludes ignored predictions,
with 15 fixed equal-width bins `[a,b)` and the final upper endpoint included.
Bin counts, means and empty bins are retained. This is not LaECE or OCE. No
calibration fitting, official AP, bootstrap framework or coverage claim is added.

## CLI and population policy

Set `PYTHONPATH=src` when running from the checkout without installing it:

```powershell
$env:PYTHONPATH = 'src'
& C:/Users/Advait/det-eval-2d/.venv/Scripts/python.exe -m threshold_transfer.evaluate `
  --source-selection-annotations source.json --source-selection-predictions source_predictions.json `
  --clear-test-annotations clear.json --clear-test-predictions clear_predictions.json `
  --target-test-annotations target.json --target-test-predictions target_predictions.json `
  --policy policy.json --target-recall 0.9 --output result.json
```

Each input is a canonical document for its explicitly chosen population. The
following is an illustrative policy shape, not an available dataset split:

```json
{
  "categories": ["pedestrian"],
  "ignore_policy": "same_category_ioa",
  "bounds_policy": "strict_known",
  "population_mode": "held_out",
  "test_relationship": "disjoint",
  "roles": {
    "source_selection": {
      "dataset_id": "example", "group_namespace": "example-trips",
      "population": "clear daytime threshold selection",
      "group_provenance": "verified manifest/version and grouping evidence",
      "attribute_filter": {"weather": "clear", "timeofday": "daytime"}
    },
    "clear_test": {
      "dataset_id": "example", "group_namespace": "example-trips",
      "population": "independent clear daytime test",
      "group_provenance": "verified manifest/version and grouping evidence",
      "attribute_filter": {"weather": "clear", "timeofday": "daytime"}
    },
    "target_test": {
      "dataset_id": "example", "group_namespace": "example-trips",
      "population": "prespecified shifted test slice",
      "group_provenance": "verified manifest/version and grouping evidence"
    }
  }
}
```

`dataset_id` must match annotation `provenance.dataset` when present. Image
identity is `(dataset_id,image_id)`; group identity is
`(group_namespace,group_id)`. One dataset must use the same group namespace
across roles. Source-selection image/group overlap with either test is always
rejected, including in diagnostic mode. `test_relationship: paired` permits
shared groups between distinct test images, never with selection; it does not
certify the correctness of scene correspondence. `disjoint` checks both tests
against each other too.

`held_out` requires complete group IDs and a nonempty provenance evidence string
for every role. The result says DECLARED_HELD_OUT: JSON declarations do not
authenticate provenance or independence. `diagnostic` permits missing groups
with explicit limitations and cannot establish an independent held-out result.
Dataset names, group provenance, prior development exposure, hidden dependencies
and whether the same frozen inference pipeline was actually used still require
an external audit. No groups or weather labels are inferred from filenames.
Population descriptions are declarations; only supplied `attribute_filter`
entries are verified against every included image. Missing native weather/time
attributes cannot support a weather claim.

The CLI preserves both input provenance objects and exact file-path/SHA-256
records, emits strict JSON, and refuses to overwrite input files. Valid
infeasible/undefined evaluations return exit 0 with explicit statuses; invalid
inputs return exit 2 and a JSON error on stderr. No inference is performed.

## Validation evidence

**Coordinator resolution:** the initial implementation below received Claude's [formal review](../reviews/2026-11-05_gpt_evaluator_review.md). S1–S3 and selected low-severity issues were fixed directly with seven additional regression tests; see [the resolution](../reviews/2026-11-05_evaluator_resolution.md). The evaluator suite now has 32 tests. Held-out mode additionally requires native dataset identity, complete inference coverage and identical declared pipeline provenance. Diagnostic mode reports missing/different pipelines and threshold censoring. Match rows are omitted from transfer JSON unless `--include-matches` is supplied. These changes do not authenticate declarations or pass G0.

GPT ran, using the existing sibling environment unchanged:

```powershell
$env:PYTHONPATH = 'src'
& C:/Users/Advait/det-eval-2d/.venv/Scripts/python.exe -m unittest discover -s tests -v
```

**25 tests passed.** Tests include hand-counted end-to-end CLI execution, strict
JSON/errors and provenance, malformed inputs/duplicate IDs, exact IoU/IoA
boundaries, eligible-before-ignore priority, reusable ignore regions, exact
class names, score/ID ties, GT-ID ties, greedy-versus-cardinality distinction,
empty images and no-GT populations, selection infeasibility/undefined status,
score-zero boundaries, strict monotone-map invariance, the nonlinear-midpoint
counterexample, signed/positive gap identities, held-out signed decomposition,
ordering invariance, selection/test image/group leakage, missing-group policy,
paired tests, declared attribute filters and binary TP-ECE endpoint/empty bins.

The end-to-end synthetic example selects `t=0.8` for target recall `0.5`.
Independent clear-test recall is `1.0`; target recall/precision/FPPI are
`0.25/0.5/0.5`; target ceiling is `0.75`. Held-out loss decomposes as
`0.75 = 0.25 + 0.50`; target shortfall is `0.25` and threshold-removable misses
are `0.50`. These numbers test different estimands, not empirical performance.

GPT inspected sibling `det-eval-2d@39c6f6d87df7775c3bf1dd36b8de3990d6a4b217`
`src/det_eval/{metrics,data,mapping}.py` read-only as context. The reference code
was written independently; no sibling evaluator code or empirical outputs were
copied. The inspection confirmed the importance of distinguishing reusable
DontCare regions from one-to-one neighbour/difficulty ignores. No dataset,
weight, environment or package was modified; no real-cache transfer evaluation,
training, downloads, paid compute, push, PR or merge was performed.

## Actual peer discussion

These were live messages within the two current implementation assignments,
not a formal review. Claude peer:
<t3-thread://v2/078e1310-2800-4050-97ad-e275e9010680/thread:delegated-task:command%3Amcp%3A363f5e39-a5db-4400-b8a2-c4d5acf49203%3Adelegate-task%3A81424b8e-ff61-404d-90dc-bced6c18af7e>.
Full prompts/responses remain in the actual task threads; the following records
their substantive content and verbatim decision excerpts rather than inventing
a dialogue. Outgoing messages used `mode: steer` and were delivered as steered.

1. **GPT initial PEER PROPOSAL**, outgoing message suffix
   `dcf05516-519e-401a-ac3d-ba96797de244`: proposed parsed canonical dicts,
   globally unique IDs, exact category matching, eligible-first IoU >=0.50,
   explicit reusable ignore modes, role overlap checks and explicit undefined
   statuses. Asked: “do your converted IDs/category names/native ignore
   provenance or role schema need an alternate boundary?”
2. **Claude PEER PROPOSAL**, received: “Your boundary works for me”. Claude
   specified native string IDs with collision rejection, run/row candidate IDs,
   verbatim native categories and explicit vocabulary mapping; split but no area
   field. Claude distinguished KITTI ignore types and proposed an explicitly
   diagnostic converter excluding neighbour-containing images. Claude requested
   `evaluated_image_ids` denominator validation and asked about role names,
   `split` and `area`. GPT accepts those category/ID/policy boundaries without
   interpreting native attributes. This acknowledges an interface, not scoring
   equivalence or review approval.
3. **GPT PEER FINDING/interface response**, outgoing message suffix
   `2e365494-2d9b-45ae-a09d-41c91b2dd735`: confirmed no area/split requirements,
   role names `source_selection/clear_test/target_test`, opaque native fields and
   no aliases. Proposed: “requiring its set EQUAL the provided annotation image
   set ... rather than silently using a subset as denominator”. Explicit
   annotation population restriction remains the adapter/caller's responsibility.
4. **Claude PEER FINDING**, received: “Equality is fine and I agree it is safer.”
   Claude will require `--restrict-to-manifest` to filter old cache rows/IDs to a
   restricted manifest, preserving manifest hash and excluded-image/row counts;
   otherwise population mismatch fails. Claude confirmed native mapping target
   checks and the same three role names. **Disposition: agreed and implemented.**
5. **GPT PEER FINDING**, outgoing message suffix
   `54f716ed-f5e1-449d-b049-117d144492d5`: sent implemented API, exact CLI flags,
   separate policy schema, diagnostic/held-out limits, input provenance/hash
   behavior and the 25-test result. Requested current-assignment incompatibility
   reports and explicitly left formal review to the coordinator. No reply to
   this final implementation detail is implied by silence.

The existing shared canonical contract was not changed. The additional CLI
policy/result shapes belong to these GPT-owned modules. Integration with the
actual adapter output and formal diff/evidence cross-review remain coordinator
tasks. No empirical grouping, independent test manifest, official KITTI policy,
calibration wrapper or bootstrap coverage has been established by this work.
