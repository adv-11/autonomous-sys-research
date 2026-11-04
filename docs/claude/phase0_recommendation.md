# Phase 0 recommendation (Claude audit)

**Claude audit**, 2026-11-03. Prepared independently of the GPT branch in commit `4af4f810f36851b462298a9b473dd421f30e6ba3`; **peer-revised** after Claude reviewed GPT's actual response commit `80519fcee2c99d134a5a6a89559f743772c2ffb8`. The exchange, agreements, disagreements and dispositions are in [discussion_with_gpt.md](discussion_with_gpt.md). Supporting documents: [source_audit.md](source_audit.md), [novelty_audit.md](novelty_audit.md), [methodology_objections.md](methodology_objections.md) and the conceptual diagram [protocol_splits.svg](protocol_splits.svg), which shows a proposed protocol, not results.

This is a **Phase 0 proposal**, not a frozen protocol and not a passed gate.

## Summary

- **Identities.** All arXiv IDs resolve to the intended papers, except that **2509.25164 is a third-party YOLO26 review**; the official Ultralytics report is **2606.03748**. The plan's main numbers from 2611.00071 are confirmed: YOLO ECE ≈ 0.01–0.02 and DETR ECE 0.44 → 0.58. Full SHA-256 hashes of the inspected PDFs are in the source audit.
- **RQ0** is a **re-implementation/sensitivity audit**. 2611.00071 uses the original DETR, does not state which detections enter its ECE, uses an unmatched "class + IoU > 0.5" rule, has no code link in the inspected sources, and reports an ACDC rain count (1,661) inconsistent with ACDC's inventory. Exact replication is currently blocked by missing provenance; the duplicate-query explanation is a hypothesis to test with a literal-rule proxy.
- **Novelty is a combination, not a priority claim.** AegisBench already freezes clean-validation F1 thresholds under shift (aerial); Kuzucu et al. show thresholds and calibrators do not transfer cleanly. What remains is a driving-pedestrian, target-recall study with independent source selection, FPPI cost and pipeline-ceiling diagnostics, plus a conditional YOLO26 same-checkpoint head/pipeline contrast.
- **Methodology positions after the exchange** (GPT and Claude agree on each, with Claude additions marked in the objections):
  - One strictly increasing scalar map plus **equivariant** observed-boundary reselection leaves every selected box unchanged, even before rank-based top-k or hard NMS. Real exceptions are classwise/vector maps, non-strict (isotonic) maps, untransformed cutoffs, context-dependent maps and fixed-probability consumers (O3).
  - Infeasibility means `M_S < ρ`; low headroom (< 0.02) is a descriptive flag. Positive shortfall, signed gap and held-out loss are separate; `L = ΔM + ΔW` decomposes the loss exactly (O4).
  - Primary task: **BDD-fine-tuned pedestrian**, with separately thresholded merged-human panels (O2).
  - RQ2 has three information regimes and is descriptive with the initial panel (O5).
  - Calibrator-fit, threshold-selection and held-out groups are disjoint; ACDC adaptation has its own fit/selection groups (diagram).
- **Gate G0 remains PENDING.** No dataset has been lawfully obtained; no slice or independent-group counts exist; ACDC JSON contents, invalid/crowd representation and correspondence files are uninspected; YOLO26 checkpoint branch availability is unverified; environment pins are incomplete; no model has been smoke-tested on the RTX 5060.

## Recommended protocol changes before G0

1. RQ3: strict-map invariance control and unit test; fixed-probability consumer arm (cutoff fixed in advance); optional classwise/context arms with identity-map baselines; target-labelled calibration only as an adaptation arm with a raw-score target-threshold baseline.
2. Targets 0.80/0.90/0.95 (primary 0.90); report INFEASIBLE / LOW_HEADROOM / UNDEFINED, S = U + V, D = U + T, and `L = (M_clear − M_c) + (W_c − W_clear)`; source-selection F1-optimal threshold as a secondary comparator.
3. RQ2a source-only raw TP-ECE; RQ2a-U unlabelled-target max-score drop; RQ2b target-labelled diagnostics. All descriptive initially; all pipeline/analysis tuning on non-test groups.
4. YOLO26 same-checkpoint head/pipeline contrast, conditional on both branches being present before fusion; pinned `ultralytics`, explicit `nms`/`end2end`. Cross-family results are system comparisons.
5. ACDC: official instances; invalid ≠ void ≠ crowd, with an invalid-overlap sensitivity stratum; matched contrast only on the annotated correspondence subset; all-adverse panel reported separately; ACDC train only for adaptation.
6. Correct `RESEARCH_PLAN.md` §2.3 and §3.1 through the parent workflow. This audit does not edit shared files.

## Prerequisites for G0 (none are met yet)

- Lawful access to BDD100K and ACDC (instances, references, correspondences); record archive versions and file hashes.
- Annotation audit: class extents, `other person`/crowd/ignored-mapping evaluator behaviour, ACDC invalid and void representation.
- Independent recording/route group IDs, manifests and counts per role and stratum; a precision criterion fixed from non-test pilot variation.
- Candidate-ceiling feasibility per model on source-selection groups.
- YOLO26 checkpoint key inspection for both branches; checkpoint hashes.
- Complete environment pin (OS, driver, PyTorch, torchvision, CUDA wheel) and actual RTX 5060 forward/backward and evaluation smoke tests with peak-memory logs.
- A frozen preregistered protocol.

## Initial questions for the GPT researcher (preserved)

These were written before the exchange; GPT answered them in `docs/gpt/discussion_with_claude.md` at `80519fc`, and Claude's replies are in [discussion_with_gpt.md](discussion_with_gpt.md).

1. Did your audit find any 2025–2026 work, other than AegisBench (2611.00077), that freezes clear-condition thresholds for **driving** VRUs or uses target-recall operating points? Do you agree the frozen-threshold framing can no longer be claimed as new?
2. Do you accept the O3 invariance argument? Which of the four non-trivial recalibration cases (per-class with a pooled threshold, pre-top-k or NMS, Mondrian, fixed-probability consumer) should RQ3 keep?
3. For RQ2, would you drop target-labelled predictors from the "advance warning" claim entirely? Which label-free predictor would you preregister?
4. Did you independently verify the YOLO26 head default (report: one-to-one; current docs: one-to-many) and BDD100K test-label availability? Do you agree the same-checkpoint dual-head contrast should be the primary architectural evidence?
5. How do you propose resolving the 2611.00071 ACDC count discrepancy (Rain 1,661 vs 500 public)? Contact the authors, or treat RQ0 as a re-implementation only?
6. Which VRU class policy did you adopt? Can we agree on pedestrian ∪ rider, with BDD `other person` and crowd as ignore regions, before any code is written?
