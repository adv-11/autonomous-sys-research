# Adapter/evaluator integration evidence

**Coordinator validation, 2026-11-05.** The combined implementation passes 58 synthetic tests: 32 evaluator/safeguard tests and 26 data-preflight tests. The evaluator has Claude's [formal review](../reviews/2026-11-05_gpt_evaluator_review.md) and a [direct resolution](../reviews/2026-11-05_evaluator_resolution.md). The converter still needs its separate formal GPT review before PR publication.

The coordinator read Claude's four unchanged generated documents and passed both annotation/prediction pairs through the reference evaluator. These are previously inspected development assets, not a new night/weather study or a held-out claim.

| Pair | Images / annotations / predictions | Integration outcome |
|---|---|---|
| COCO cached person | 5,000 / 36,781 / 123,897 | Default undeclared-ignore mode refuses it; explicit same-category IoA with strict known bounds accepts it. Fixed-threshold count consistency passes. |
| KITTI diagnostic Pedestrian | 2,427 / 22,238 / 101,660 | Same checks pass under the declared diagnostic policy. This is not official KITTI scoring or the complete validation population. |

For both pairs, held-out role checks return FAIL because recording groups are unknown. No groups, weather tags, clean/shift split or independent test exposure were invented. No recall-transfer result is reported here. The detailed integration record stays in gitignored outputs/integration/adapter_evaluator.json.

## Input identity

| Generated document | SHA-256 |
|---|---|
| coco_val2017_annotations.json | feb8c056cc60e2013c65ef1e78f57ce2c42171c801f6c7d9d2f5fe72ed2d12a6 |
| coco__yolo11s_person.json | 1f4439e26514ad55cbd9b477611a3158f5ed2a91ca136314c4489968334c326f |
| kitti_val_diagnostic_annotations.json | 0b3bbcb7e520ba2328bffe779d5c5d071598bc660eef0709aaa1eaebeb96f7e6 |
| kitti__yolo11s_640_ft_native3.json | 72e01bdaca68e193029bf26108764b567f43114c9041ebebaf409d9d384f3a4c |

These identify converter outputs, not authoritative release hashes. The [implementation note](../claude/data_preflight_implementation.md) records source evidence and conversion policies.

## Resolution of the undelivered final peer questions

These are coordinator answers from code inspection and real integration, not a fabricated GPT response. Claude's final message arrived after GPT's implementation task ended; its questions are being supplied automatically to the new formal converter review.

- **Q1:** default rejection of ignored/crowd annotations is intentional. Both manifests need an explicit ignore policy. The accepted IoA rule is a reference diagnostic, not an official benchmark rule.
- **Q2:** the KITTI diagnostic subset does not apply difficulty filtering and must retain that limitation. Unsupported one-to-one difficulty ignores must not become reusable regions silently.
- **Q3:** evaluator output preserves full annotation/prediction provenance, including cache policy, excluded-row counts and restriction records. Pipeline/floor checks are now explicit; missing full-vector scores and verified groups cannot be reconstructed.
- **Q4:** strict-known bounds validation applies to GT and predictions. Both unchanged real pairs passed.

G0 remains pending: BDD/ACDC access and artifact inspection, verified groups/conditions and split manifests, inference provenance, model-specific training/evaluation smoke tests, and subsequent statistical validation. My approval is still required for research PR merges.

## Post-review validation

After the [adapter corrections](../reviews/2026-11-05_data_resolution.md), 67 combined synthetic tests pass on both Python 3.11 and Python 3.12. The coordinator regenerated both real pairs from native files and passed their dictionaries directly to the evaluator, without relying on JSON serialization to normalize object keys. Strict bounds and count consistency checks pass; unknown-group held-out checks still fail as intended. The earlier detection project's Git working tree remains clean.

COCO counts remain 5,000 images / 36,781 annotations / 123,897 predictions, and the diagnostic KITTI counts remain 2,427 / 22,238 / 101,660. These are compatibility checks, not newly estimated weather-transfer performance. Current generated output identities are recorded under gitignored `outputs/integration/review_fixed/validation.json`; that file also records the exact native source/cache hashes. The earlier table identifies the previous integration run, not every later provenance declaration.
