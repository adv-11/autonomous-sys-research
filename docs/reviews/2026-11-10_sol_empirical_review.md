# Scientific review of Sol's completed 640 pilot

**GPT Astra, 2026-11-10; separately delegated completion at `a2072cef6bf2e020a77c1ee54cd8de432d8508a4`.** This review reuses the interrupted GPT Astra analysis and uncommitted draft; it is not a second independent empirical replication. GPT Sol executed the inference. No Claude or child agent participated. I want the research decision to follow the retained measurements. **G0 remains pending; my explicit approval still governs merges.**

## Disposition and scope

**No conclusion-invalidating objection remains for the completed 640 contribution.** H1 fails all three prespecified .90 contrasts on this finite panel; its fresh-source repeat is not triggered. No implementation correction is required. This supports stopping that hypothesis, not asserting that all candidate policies are ineffective.

Reviewed contribution: originals `14aa83e98383105d17e0741aca4e42a43ed2e7f2` and `e10325ed08cbc80817623629375210bd050dca7f`, integrated as `8ab428e` and `f120aac`. Scope is the scientific claims in the [completion note](../gpt/2026-11-10_sol_completion.md), aggregate, prospective [H1 note](../gpt/2026-11-10_astra_research.md), and zero-area/coverage decisions. The interrupted draft records identical original/integrated file comparisons and an unchanged positive-area evaluator; those comparisons were not repeated here. This is not a general software audit.

## Evidence retained from the interrupted review

The private `outputs/colab/astra_coverage_20261110/` directory under `C:/Users/Advait/autonomous-sys-research/` contains `analyze.py`, `review_reproduction.json` and `per_gt_private.json`. The script and persisted reproduction support the following completed checks from the **interrupted assignment**, not newly executed checks in this completion:

| Potential invalidation | Retained evidence and disposition |
| --- | --- |
| Incomplete population or candidate accounting | Four policies each cover the same 700 unique manifest IDs in 88 native batches. Baseline has 44,104 candidates, including 118 zero-area outputs. The retained script checks baseline coordinates, scores and classes against native batches and reconciles all policy candidate totals. |
| Wrong denominators or duplicated paired subsets | COCO selection/reference contain 579/528 eligible person GT. Disjoint adverse union: 128 images, 216 human GT (201 person, 15 rider), 62 empty-human images, six crowd regions. Unique normal references: 60 images, 154 GT (137 person, 17 rider), 18 empty images, no crowd regions. Paired subsets do not enter these unions twice. |
| Zero-area predictions spuriously matched or ignored | All 118 baseline cases are COCO; maximum score `0.00024431711062788963` is below both feasible reported operating thresholds. They are explicit FP, never TP or crowd absorption. The positive-area matcher remains unchanged. |
| Post-outcome hypothesis or false operating null | H1 was accepted before inference. Retained source-objective and night/COCO-reference B/D reproduction gives zero recall and TP/FP changes for all three q at .90; both strict inequalities fail. No .80 rescue or winning-policy selection. |
| Incorrect baseline result | Retained reproduction equals the published baseline operating/ceiling counts on all 14 panels. All selected empty images remain in FPPI. |
| Inference/evidence inconsistency | Retained records report COMPLETE and child exit zero, matching sent/current inference and evaluator-wrapper source bodies, and owned teardown. The interrupted draft's additional native-source/resource inspections are inherited observations, not new independent verification here. |

The present completion read the retained script, draft, verbose reproduction and compact aggregate. It checked the retained analysis/per-GT SHA256 values and exact compact-versus-verbose agreement for every published count/stratum and other shared field. It did **not** rerun the evaluator, raw-batch sweep, inference, source comparison, or regression suite. This avoids counting the same retained analysis as another replication. The earlier synthetic zero-area example is separately labelled in Sol's note and is not empirical evidence.

## Decisive retained counts

At the shared .90 source boundary `0.043987125158309937`:

| Panel | Images | GT | Operating TP / FP | All-output TP / FP |
| --- | ---: | ---: | ---: | ---: |
| COCO selection | 256 | 579 | 522 / 480 | 539 / 11,929 |
| COCO reference | 256 | 528 | 423 / 539 | 482 / 12,206 |
| All selected night adverse | 32 | 77 | 27 / 45 | 35 / 1,729 |
| Reference-eligible night adverse | 12 | 25 | 9 / 24 | 13 / 515 |
| Corresponding annotated normal | 12 | 35 | 13 / 70 | 16 / 582 |

The night tail adds eight TP and 1,684 FP; threshold lowering cannot reach .90 within these candidates. All four policies select the same .80 boundary `0.24039360880851746`; .95 is infeasible. Equal source boundaries alone would not establish an operating null: the retained TP/FP comparisons do. Paired normal/adverse counts concern the same 12 views but different people and denominators; they do not identify a causal night effect.

## Provenance and remaining limits

The [aggregate](../gpt/2026-11-10_astra_coverage_aggregate.json) preserves all original 640 counts and provenance plus explicit completion metadata. Original interrupted draft SHA256: `d2370701b8446cde03a2024d87673948f8264c43029957b1bc4ffd0ec613c5b3`; original compact aggregate: `f22058343a407c2844c3eea38d2e1fc6ec24999d725947d5b21b78f43a079135`; retained verbose reproduction: `81647f8670c05c50a8055cfaa43ef8521629d8498123df695942e5d46adadaf4`. Source worktree was `t3-c41a28e5`; its uncommitted artifacts were never treated as a completed review. The private source artifacts remain intact.

**1280 is a separately labelled addendum, not part of this 640 approval disposition.** Sol's actual results arrived during completion. Astra read and retained a snapshot of the uncommitted aggregate, checked selected counts/arithmetic and 640 baselines, and confirmed its embedded native status/operation records match the retained status/operation files. Astra did not reproduce its evaluator matches, inspect its raw batches, or formally review its implementation. The [diagnosis](../gpt/2026-11-10_astra_coverage_diagnosis.md) records H2, controls, actual exchange and this evidence boundary. Source-aggregate verification does not establish independent raw-data verification.

Informational limitations remain: provisional human/crowd task, possible pretrained-data exposure, COCO not verified clear/day, unresolved ACDC recording dependence and annotation/acquisition differences. Returned candidates do not exhaust raw human hypotheses or prove physical absence. There is no IID CI, primary BDD result, official AP, causal night inference, novelty claim or general capacity conclusion. No new data selection, installation, GPU/Colab operation, push, PR or merge was performed. Human merge approval is still required.
