# Phase 0 recommendation (Claude audit)

**Claude audit**, 2026-11-03. Independent of the GPT research branch, which Claude has not seen. Supporting documents: [source_audit.md](source_audit.md), [novelty_audit.md](novelty_audit.md), [methodology_objections.md](methodology_objections.md), and the conceptual diagram [protocol_splits.svg](protocol_splits.svg). The diagram is a proposed protocol, not results.

## Summary for discussion

- **Identities.** All five arXiv IDs resolve to the intended papers, except that **2509.25164 is a third-party YOLO26 review**; the official Ultralytics report is **2606.03748**. Full texts were read for all of them, and the plan's main numbers from 2611.00071 are confirmed: YOLO ECE ≈ 0.01–0.02 and DETR ECE 0.44 → 0.58.
- **RQ0.** The "artifact" hook is plausible but unproven. 2611.00071 uses the original DETR (no RT-DETR), never says which detections enter its ECE, uses an unmatched "class + IoU > 0.5" correctness rule, releases no code, and reports an ACDC rain count (1,661) above ACDC's public rain labels (500). Exact reproduction is impossible; only a re-implementation with a literal-rule ECE variant can test the mechanism.
- **Novelty.** Narrower than planned. AegisBench (2611.00077, Oct 2026) already freezes clean-validation thresholds and measures silent person-recall collapse in low light (aerial, synthetic corruptions). Kuzucu et al. already show that thresholds and post-hoc calibrators do not transfer cleanly across domains. Still open: target-recall VRU operating points on real driving adverse data, a **same-checkpoint YOLO26 one-to-one vs one-to-many head control**, and dataset-shift vs condition-shift separation using ACDC reference images.
- **Blocking methodology issues.**
  - Global monotone recalibration combined with a recall-retuned threshold is provably a no-op for recall (O3).
  - The 0.90 target needs a feasibility rule and an unrecoverable vs transfer decomposition (O4).
  - RQ2 is pseudoreplicated and, with target-labelled OCE or mAP, circular (O5).
  - The COCO/BDD/ACDC person–rider policies need a merged VRU-human primary class (O2).
  - ACDC labels must come from the official instances, with void and group regions treated as ignore regions (O1).
- **Gate G0 remains PENDING.** No dataset has been lawfully obtained, no slice counts exist, no model has been smoke-tested on the RTX 5060, no protocol is frozen, and the BDD test-label status and ACDC JSON contents are unresolved.

## Recommended protocol changes before G0

1. Replace RQ3's "calibrated-space threshold" with the four non-trivial cases in O3. Add the invariance unit test.
2. Report the loss as U_c and T_c, with feasibility flags for R\* ∈ {0.80, 0.90, 0.95}. Add the F1-optimal frozen threshold to allow comparison with AegisBench.
3. Split RQ2 into RQ2a (label-free target predictors, so they can warn in advance) and RQ2b (labelled diagnostics). Use within-condition or mixed-effects analysis, a hierarchical bootstrap, and at least two seeds for two models.
4. Make the YOLO26 dual-head contrast (pinned `ultralytics` version, explicit `nms`) the primary architectural evidence. Describe cross-family DETR results only descriptively.
5. Use ACDC train for condition-aware calibration and ACDC val for testing (preserving the geographic split). Add ACDC-reference val as the matched clear anchor.
6. Correct `RESEARCH_PLAN.md` §2.3 and §3.1 through the parent workflow. This audit does not edit shared files.

## Prerequisites for G0 (none are met yet)

- Lawful access to BDD100K, ACDC (instances and reference set) and KITTI, if used; record versions and checksums.
- Slice counts: VRU-human instances per BDD time-of-day and weather slice, and per ACDC condition and split, including void and group overlap.
- An R_max feasibility check per candidate model on the clear calibration split.
- Smoke tests (training and evaluation) for each repository on the RTX 5060 with torch ≥ 2.7 cu128.
- A frozen preregistered protocol (class policy, matching, ignore rules, metric configs, analysis plan).

## Questions for the GPT researcher

1. Did your audit find any 2025–2026 work, other than AegisBench (2611.00077), that freezes clear-condition thresholds for **driving** VRUs or uses target-recall operating points? Do you agree the frozen-threshold framing can no longer be claimed as new?
2. Do you accept the O3 invariance argument? Which of the four non-trivial recalibration cases (per-class with a pooled threshold, pre-top-k or NMS, Mondrian, fixed-probability consumer) should RQ3 keep?
3. For RQ2, would you drop target-labelled predictors from the "advance warning" claim entirely? Which label-free predictor would you preregister?
4. Did you independently verify the YOLO26 head default (report: one-to-one; current docs: one-to-many) and BDD100K test-label availability? Do you agree the same-checkpoint dual-head contrast should be the primary architectural evidence?
5. How do you propose resolving the 2611.00071 ACDC count discrepancy (Rain 1,661 vs 500 public)? Contact the authors, or treat RQ0 as a re-implementation only?
6. Which VRU class policy did you adopt? Can we agree on pedestrian ∪ rider, with BDD `other person` and crowd as ignore regions, before any code is written?
