# Fixed-panel native inference completion

**GPT Sol execution, 2026-11-10; base `3d2244e1495106594e0c16781f5fb71066a9e185`. G0 pending.** This is a separate completion assignment. The [earlier failed attempt](2026-11-10_sol_results.md) and its aggregate remain historical evidence; its missing raw box is not retrospectively classified as zero area. GPT Astra's [prospective H1](2026-11-10_astra_research.md) is unchanged. No Claude work, peer restart, training, local GPU operation, new sample, push, PR or merge is part of this assignment.

I want an actual result on whether native candidate policies change source-selected threshold transfer enough to motivate further research. GPT Sol owns the correction, Colab execution, retrieval and interpretation under the [prospective zero-area decision](../decisions/2026-11-10_native_zero_area.md). My approval still governs merges.

## Prospective execution record

Before allocation or any completed policy result, GPT Sol adopted explicit native-zero-area accounting: save raw native batches before validation; preserve finite unreversed zero-width/height detections separately with native coordinates, candidate IDs and scores; append FP rows to the unchanged positive-area `ReferenceEvaluator`, sorted by `(-score, candidate_id)`. Inclusive score thresholds, ties, FPPI and binary TP-ECE include these rows. Zero-area detections receive no crowd absorption; undefined zero-denominator IoA is not computed. No coordinate repair, epsilon expansion or clipping is introduced. Reversed/nonfinite/wrong-class outputs, censoring/timeouts and incomplete coverage still fail. This is provisional diagnostic accounting, not official AP.

The tiny deterministic CPU example passed before allocation: one TP plus one zero-area FP, at equal and unequal scores, two images including an empty image, a crowd region, inclusive boundaries, whole ties, FPPI .5 and ECE count two. This is a synthetic accounting check, not a research result; no regression suite or qualification programme was run.

The unchanged 700-image packet supplies 256 COCO selection, 256 disjoint COCO reference, 32 ACDC adverse val images per condition and 60 annotated normal references. All empty images remain. The four native YOLO11s policies remain floor .0001/cap3000 (`maximal`), floor .0001/cap100, floor .0001/cap300 and floor .01/cap3000. Each runs directly, totaling 2,800 forward images; no training or additional model is required. Person-only outputs and COCO person / ACDC person+rider human mapping, matching, objectives .80/.90/.95, batch eight and 640 input remain unchanged.

**Estimate recorded before allocation:** allow 40 minutes for chunk transfer, setup, 2,800 forward images, retrieval and teardown. Previous successful chunk/setup operation occupied approximately 11 minutes; valid inference throughput was unmeasured. At the previous L4 rate 1.94 CU/hour, this allowance is `40/60*1.94 = 1.293333 CU`. The hard wall is 60 minutes including retrieval/cleanup, admission rate at most 6 CU/hour, cumulative empirical envelope 10 CU less prior .31 displayed CU and .20 CU reserved for meter lag. Sole operator GPT Sol uses one named owned L4 session and isolated state under ignored `outputs/colab/empirical_completion_20261110/`. No top-up or other session teardown is authorized.

The original 490,741,760-byte packet and its 118 chunks remain unchanged. After reconstruction and SHA verification, only the corrected script/config are uploaded separately. The manifest and image bytes are reused without a dataset rescan or selection. Original packet identity does not describe the overwritten working directory. Exact separate delivery hashes and execution outcomes are recorded below after retrieval.

## Results and disposition

Execution in progress; no completed performance result is asserted by this prospective record.
