# Publication review: resolution and cached scale baselines

**GPT Astra, 2026-11-10; separately delegated review at `9a177209df28dfc4af1cf2c1e2d6575a8a8031e1`.** GPT Sol produced the experiments; GPT Astra performed this review without Claude or children. I want the published checkpoint to preserve the measured result and its limits. **G0 remains pending; my explicit approval still governs merges.**

## Recommendation and reviewed contributions

**No material scientific blocker or required implementation correction was found.** The new code, decisive retained-output reproduction and checkpoint support publication as a descriptive research checkpoint: H1 stays closed, H2 supports ordinary resolution/pipeline sensitivity, and the current method claim stops. This does not rule out all future methods or confer human merge approval. No additional review loop, inference or statistical qualification is required for these narrowly stated conclusions.

| Contribution | Exact reviewed identity and disposition |
| --- | --- |
| A: 1280 intervention | Sol original `0c9408a1f010e576e5677efc1cc32333a58348cf`, integrated `aa56e84`: 184-line resolution wrapper, config, note, aggregate and PNG. Original and integrated files compare identically. Accept within the stated finite-panel scope. |
| B: cached baselines | Sol original `e1217afa8f9cbe9755c1bfce990c3a1f1ea3ecec`, integrated `7d5c4a8`: 288-line baseline script, note and compact aggregate. Original and integrated files compare identically. Accept as post-pilot development analysis. |
| C: synthesis | `9a177209df28dfc4af1cf2c1e2d6575a8a8031e1`, [checkpoint](../research/2026-11-10_checkpoint.md). Its pooled .90 numbers, interpretation and source-access qualifications are consistent with A/B and the existing Astra notes. Accept; its statement that this newer review is pending is accurate at that base and can now link here. |

The [completed 640 review](2026-11-10_sol_empirical_review.md) remains valid and was not repeated. The [coverage diagnosis](../gpt/2026-11-10_astra_coverage_diagnosis.md) and [opportunity note](../gpt/2026-11-10_astra_scale_opportunity.md) were read as prior evidence, not counted as fresh replication or literature verification.

## Algorithm and provenance checks

The H2 decision exists at `a2072cef6bf2e020a77c1ee54cd8de432d8508a4`, timestamped 23:20:27 UTC, before the retained 1280 allocation at 23:23:31 UTC. The code implements that fixed rule: eligible GT height times `640 / max(width,height)`, small strictly below 16, net gained-minus-lost one-to-one ceiling matches divided by all eligible GT in each stratum. No outcome-selected cutoff or baseline-miss denominator replaces H2.

The original manifest and delivered resolution manifest have SHA256 `21c5a2c738a22c5e6e6bff535c1122a8fdc3cbac69216ce9e9ba07c3e3b1156a`. Both retained prediction files cover exactly its 700 unique images. The reproduction checked 256 source-selection images, 256 disjoint COCO reference images and the 128-image adverse union, with 216 eligible GT and 62 empty images. Source selection and target evaluation retain their roles; paired adverse subsets are not added again to the pooled denominator.

Code inspection confirms the following contracts:

- Fusion concatenates native post-NMS positive outputs, prefixes IDs by resolution and sorts by descending score then tagged ID. Same-image/class hard NMS suppresses only IoU > .70; equality remains. Returned boxes/scores are unchanged, with no extra cap. Tagged IDs are unique in the reviewed caches; lexical ties place `1280:` before `640:`.
- The gate keeps a positive 1280 box iff any positive same-image human box in the full 640 cache overlaps at IoU >= .50. Its witness need not survive the operating threshold or match GT. It preserves native 1280 scores/boxes and all 1280 zero-area emissions. Fusion preserves both sets of zero-area emissions. These are explicit FP outside overlap operations, without repair or crowd absorption.
- `pilot_evaluator` and the positive-area `ReferenceEvaluator` are unchanged from the reviewed baseline. Each pipeline selects its own highest observed source boundary, inclusively with whole ties, for .80/.90/.95. There is no target tuning or infeasibility rescue. The retained .95 native-640 result remains infeasible; gate .95 includes four source zero-area FP and retains its low-headroom qualification.
- The oracle uses augmenting-path maximum-cardinality one-to-one IoU-.50 matching against eligible GT, ignoring confidence and excluded/crowd GT. It is neither the earlier candidate-reusing best-IoU diagnostic nor deployable recall.

Private evidence is under `C:/Users/Advait/autonomous-sys-research/outputs/colab/`. For `resolution_20261110`, the retrieved `results/delivery_verified.json` equals `code_record.json`; the actual sent wrapper, sent baseline, config and manifest match those recorded hashes. The delivered baseline module is byte-identical to the current imported module. The sent wrapper contains inference only; the final wrapper adds aggregation. Final wrapper hashes match the committed Git blobs. An initial working-copy hash assertion failed because the two new wrappers were checked out with CRLF; LF normalization exactly equals those blobs, resolving the discrepancy without a code change. Transport exit zero was not used as code-identity evidence.

## Independent bounded reproduction

GPT Astra ran a read-only CPU reconstruction from the original manifest and the two `results/yolo11s_maximal.json` files in `empirical_completion_20261110` and `resolution_20261110`. Their hashes match B's provenance. The harness imported the reviewed baseline functions and unchanged evaluator, restricted postprocessing/evaluation to source selection plus pooled adverse, reconstructed alternatives, reselected .90 and recomputed adverse matches and H2 transitions. It did not consume saved evaluation rows as ground truth. This is independent execution using reviewed code, **not an independently implemented matcher or new inference**. Existing Python 3.14.7 / NumPy 2.5.4 were used with bytecode writes disabled; torch/Ultralytics were not imported.

All source .90 points attain 522/579 GT. The following freshly computed values exactly equal the public aggregates and checkpoint:

| Pipeline | Source .90 boundary | Source FP | Adverse TP / FP | Adverse all-output TP / FP |
| --- | ---: | ---: | ---: | ---: |
| 640 | .043987125158309937 | 480 | 96 / 311 | 128 / 7,397 |
| 1280 | .08221367746591568 | 405 | 129 / 179 | 174 / 18,809 |
| Fusion | .14203764498233795 | 325 | 122 / 143 | 178 / 24,583 |
| Gate | .04346418380737305 | 572 | 116 / 203 | 133 / 5,811 |

Adverse denominators are 216 GT and 128 images throughout. H2 reproduces **20 -> 54/89 small** (35 gained, one lost) and **108 -> 120/127 larger** (15 gained, three lost). Thus 34/89 exceeds 12/127 and is positive. Net recovery per baseline miss, 34/69 versus 12/19, and gross recovery, 35/69 versus 15/19, do not favor small objects. The note preserves this distinction.

The recomputed adverse oracle is **174 for 1280 and 178 for the union**. Fusion attains 178 at its all-output ceiling, with prohibitive 24,583 FP. This establishes only four additional geometrically matchable GT in these cached boxes, not full detector capacity. At .90 fusion trades seven fewer TP for 36 fewer FP and is not dominated. The gate loses 13 TP and adds 24 FP relative to 1280 **in this pooled .90 comparison**; neither universal panel dominance nor all-objective dominance follows.

The existing tiny synthetic check also passed: exact .70/.50 boundaries, stable ties, class/image isolation and an ambiguous matching graph requiring augmentation. It is separate from empirical evidence. Other panels and .80/.95 claims were inspected in retained aggregates/code, not freshly swept. Normal and COCO-reference 1280 control counts agree between A and B; their weakness/response supports caution about night-specific interpretations. The existing PNG was visually inspected for aggregate-only presentation and appropriate descriptive labels.

## Severity, disposition and limits

**Blocking/high/medium scientific findings: none.** Informational limitations are already disclosed: COCO is not verified clear/day, pretraining exposure is unresolved, ACDC groups/views are dependent, normal/adverse people differ, and the provisional human/crowd task is not official AP or the primary BDD task. Whole-pipeline changes do not isolate darkness, architecture or physical scale. No independent-group CI, population guarantee or exhaustive novelty claim is justified or made.

The saved status/operation records agree with A's aggregate, report COMPLETE and owned teardown, and the retained final usage log reports zero active assignments and zero usage rate. Displayed cumulative use is .98 CU, including inherited failed-attempt accounting; settlement lag remains explicit. This review made no live account check. Fusion/gating add no current inference but require two network passes online; 25.19 + 40.23 seconds are historical separate loops, not measured joint latency. WBF full-HTML access, Kuppers' inherited detail/direct-PDF limitation and PCR abstract-only access remain correctly distinguished; no new source search was performed.

Public notes, PNG and aggregate fields contain no raw GT coordinates, per-image/GT/candidate identities, private event logs or credentials. No full raw-batch sweep, weight/image hashing, data acquisition, full regression suite, install, GPU/Colab operation, peer restart or new task was performed. The previous 640 raw verification is inherited. Only this review document is changed; no push, PR or merge is authorized by this disposition.
