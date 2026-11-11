# Dual-head transfer checkpoint

GPT Sol completed the [fixed YOLO26 comparison](../gpt/2026-11-11_sol_dual_head_transfer.md) on the unchanged COCO source/reference sets and278previously unqueried ACDC adverse val image paths, with143annotated normal references. Both fresh heads processed933images. A separate [Sol review](../reviews/2026-11-11_dual_head_review.md) found no scientific blocker; its [cached controls](../reviews/2026-11-11_dual_head_cached_controls.md) are complete. G0 remains pending; my approval still governs merges.

H4 passes its prospective finite-panel screen: both source .90aspirations are feasible; the COCO-reference recall gap is1.52percentage points, below2; the new-night gap is10.48points, above5. This is not a statistical equivalence or population test.

On74new-night images/105eligible GT, O2O has48TP/58FP and O2M37TP/37FP. The11TP difference costs21additionalFP. The count decomposition is `11 = (81-74) - [(81-48)-(74-37)]`: seven net ceiling TP plus four fewer threshold-removable misses. The ceiling-covered sets intersect at71GT, with10O2O-only and3O2M-only; equal totals would not establish identical objects.

The same checkpoint does not isolate NMS. Learned branches, assignment history, all-class head selection, person filtering and postprocessing differ. O2M's inactive `head.max_det=300` must not be mistaken for its actual final NMS cap3000. Runtime hooks and source records support which branches executed; their scientific effect still needs interpretation.

## Two interpretation checks from cached outputs

The independent Sol reviewer verified the actual new code/evidence and decisive counts. Two completed post-hoc diagnostics assess operating-point cost and source-boundary fragility:

- **Target-oracle FPPI control:** compare both night frontiers at FP budgets37and58, the two published operating counts. Select only whole tied score groups. These target-label-selected points are nondeployable diagnostics, never replacement operating thresholds or a new H4 verdict.
- **Paired source leave-one-image-out:** remove each of the256COCO selection images from both heads, reselect .90 on the same remaining images and evaluate cached night/reference outputs. Reuse fixed per-image matching rows; no network or source-image repeat. Report gap ranges and feasibility/screen counts as deterministic sensitivity, not a bootstrap interval, p-value or independent source replication. Do not use deletion to choose a favorable source subset.

The primary H4 remains unchanged. All256paired deletions preserve its screen. The night target-oracle comparisons are O2O42TP/32FP versus O2M37TP/28FP at ceiling37FP, and48/55versus44/54at ceiling58FP. These retain smaller differences under common FP ceilings but do not establish exact-cost equality or whole-frontier dominance. The result motivates a head-pipeline mechanism question, not architecture causality or novelty. No new GPU allocation is authorized by this checkpoint.

Displayed empirical use is now1.97units (1.28historical plus.69), with owned L4 release verified. Source exposure, merged-human/crowd conventions, dependent views and different normal/adverse people remain limits. My explicit approval still governs merges.
