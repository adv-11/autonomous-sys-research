# Independent dual-head contribution review

**GPT Sol, 2026-11-11. No scientific blocker found. Recommendation: publication with the two cached diagnostics linked and the report's pending-review/next-analysis paragraph updated.** These are small coordinator edits; another review loop is unnecessary. G0 remains pending. This review does not authorize a merge.

My project goal is to determine whether frozen head pipelines transfer a source-selected recall boundary differently. GPT Sol independently reviewed the actual five-file contribution, including the 245-line wrapper, config, report, aggregate and figure. Earlier evaluator/native-pilot work was supporting context, not newly re-reviewed in full. No peer agreement is implied.

| Reviewed object | Exact commit |
|---|---|
| Review base | `6e3722999ad4dae6dd6128b6e0d3cbb5a3d9d2df` |
| Actual contribution | `6f1956d050158ab271e34d30064dfa255668f426` |
| Integrated contribution (identical five-file content) | `22f77f9c0fd05a02c6cc2a54497a5d444279d95f` |
| Prospective decision | `c883688c641c021d2204d4555fbb689d122717b1` |

The locked decision predates allocation/output timestamps and fixes all three H4 clauses. The manifest reuses the original source/reference panels exactly; its 278 adverse paths equal official val minus the prior128, with no overlap or GT-based selection. Available references add143 unique paths. Both heads cover exactly the same933 unique IDs/paths. This establishes recorded coverage, not independent proof of every image's pixels; images, weights and all234 raw batches were deliberately not re-audited.

Fresh `YOLO` construction occurs separately for each head; checkpoint hashes agree. Retained hooks show O2O/O2M box-branch calls6/0 versus0/6, consistent backend/head modes and the opposite branch removed by fusion. The selected mode persists in final status. O2O performs all-class head top-k before person/floor filtering. O2M performs dense best-class selection, person filtering, max_nms30000, class-aware NMS(.70) and final cap3000. Its `head.max_det=300` is inactive O2O state; one O2M source image actually emits3000. These policies do not equalize candidate pools or isolate NMS.

Source-only .90 selection reproduced exact boundaries `0.0383278951048851` / `0.07566013932228088`, including whole ties. Decisive cached counts follow (O2O / O2M):

| Panel | Images / eligible GT | Operating TP | Operating FP | Ceiling TP |
|---|---:|---:|---:|---:|
| Source | 256 / 579 | 522 / 522 | 496 / 345 | 577 / 569 |
| Reference | 256 / 528 | 448 / 440 | 563 / 400 | 508 / 505 |
| Night | 74 / 105 | 48 / 37 | 58 / 37 | 81 / 74 |

Both feasible; reference gap1.515pp and night gap10.476pp satisfy locked H4. Night retains88person+17rider GT. Empty-image counts116/120/29 and excluded crowd counts14/12/1 are consistent. Eligible-first positive-area matching and reusable same-category crowd IoA are unchanged; native zero-area boxes remain explicit FP without crowd absorption (137/1585 overall; none at these three operating points).

Night decomposition reproduces `11 = (81−74) − [(81−48)−(74−37)] = 7−(−4)`. Ceiling GT sets give shared71, O2O-only10, O2M-only3. This is matched-set accounting, not a mechanistic explanation. The original figure agrees with the reported operating/ceiling values.

**Severity/limits:** no blocking or major finding. Minor publication correction: link [cached controls](2026-11-11_dual_head_cached_controls.md) and replace the stale pending-analysis instruction. Retain the21additionalFP, scene/view dependence, source exposure and unverified clear/day status, merged task ontology, provisional crowd policy and finite candidate caps. No equivalence, population, causal night/NMS, safety or novelty claim follows.

Recorded allocation1335.782seconds=22.26minutes at1.94CU/hour, displayed .69CU and cumulative1.97CU reproduce; owned release and zero process exit are retained records, not a live Colab check. Bounded CPU reproduction used existing Python3.12.14, six panel/head matching passes per invocation, no torch import/inference/install/GPU or broader suite. Private traces and resolved strict-check failures are under `outputs/colab/dual_head_review_20261111/`.

Provenance: executed wrapper SHA256 `849d6cc2e920dca0a4181d40095a0ab8e0c99c4547d28882b8c5d59bcc6fd5bc` was checked from the retained packet. Its only inference-function difference is a literal identity replacement subsequently removed. Other edits concern aggregation/provenance. The published aggregation hash describes LF bytes; this checkout uses CRLF and matches after EOL normalization. Frozen manifest/config and saved implementation-source hashes agree. [Aggregate](2026-11-11_dual_head_cached_controls.json) retains exact prediction hashes and diagnostic-script hash.
