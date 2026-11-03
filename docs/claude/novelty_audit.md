# Novelty audit (Claude audit, Phase 0)

**Claude audit**, 2026-11-03. This audit is based on the full texts listed in [source_audit.md](source_audit.md). It is a source-backed critique, not a guarantee of novelty. The arXiv API keyword searches and two web searches were not exhaustive, and no Google Scholar or Semantic Scholar citation sweep was run.

## Verdict

**Partially scooped, with a narrower open core than the original plan states.** Four of the plan's novelty claims need revision:

1. **The "nobody measured frozen clear-day thresholds" claim is no longer true in general.** AegisBench (arXiv 2611.00077, 17 Oct 2026) freezes F1-optimal thresholds on clean validation data and reports person recall under shift. It finds a silent recall collapse at low light for Faster R-CNN, YOLOv11 and RT-DETR. Its domain differs (aerial search and rescue, synthetic corruptions plus 300 real night images), and it uses no target-recall operating point, no calibration metrics and no driving data. My project must cite it and can no longer claim that the frozen-threshold framing itself is new.
2. **The RQ0 "metric artifact" hook is plausible but not demonstrable from the paper.** 2611.00071 does not say which detection set enters its ECE. One mechanism would produce exactly its pattern (inference, not a source statement):
   - its correctness rule is "class matches and IoU > 0.5", with no stated one-to-one matching;
   - Park et al. show that DETR's suppressed secondary queries keep accurate localization with near-zero confidence;
   - if those queries enter the ECE, they count as "correct" at confidence ≈ 0, which inflates DETR's ECE, while NMS removes the equivalent duplicates for YOLO.

   This is testable only by re-implementation. No code is released, and its Table I ACDC rain count (1,661) exceeds ACDC's public rain annotations (500), so the data protocol cannot be reproduced exactly as written.
3. **DETR-family coverage is thinner than stated.** 2611.00071 uses the original DETR, not RT-DETR, so "real-time DETR calibration under weather shift" is genuinely untested *there*. Penquitt et al. do calibrate RT-DETR, but without condition shift.
4. **RQ3 is largely pre-empted and partly vacuous.** Kuzucu et al. already show that operating thresholds do not transfer across validation domains (shifted→ID) and that post-hoc calibrators lose some advantage under natural shift. In addition, a global monotone recalibration combined with a recall-retuned threshold provably changes nothing (see [methodology_objections.md](methodology_objections.md) O3).

## What still appears open (subject to a wider search)

| Candidate contribution | Closest prior work found | Remaining gap | Strength |
|---|---|---|---|
| **Target-recall** (not F1) clear-day thresholds for **driving VRUs** on **real** adverse data (ACDC night, fog, rain, snow), measuring recall loss and FPPI | AegisBench (aerial, F1, synthetic); 2611.00071 (mAP/ECE only, no operating point) | Driving VRUs, real conditions, a target-recall operating point, an FPPI cost curve | Moderate |
| **Within-model head control**: YOLO26 one-to-one (`nms=False`) vs one-to-many plus NMS from the *same weights*, under shift | None found | Isolates the effect of the assignment and score head from the backbone, data and recipe, as far as a shared trunk allows | **Strongest design idea; recommended** |
| Separating dataset shift from condition shift using ACDC normal-condition reference images (matched geography and camera) | ACDC's own UDA benchmarks (mAP only) | Threshold transfer BDD clear → ACDC-reference → ACDC-adverse | Moderate |
| Calibration metrics as **label-free** predictors of recall loss | ATC (Garg et al., ICLR 2022; classification) and Park's image-level reliability (COCO, Cityscapes, Foggy Cityscapes) | Detection, driving VRUs, operating-point recall | Weak to moderate; depends on fixing O5 |
| Calibration after TensorRT FP16/INT8 | Not searched in depth this session | Unknown | Unassessed |

## Claims I should not make (per this audit)

- I should not claim to be "the first to study threshold transfer under shift" (AegisBench), or that "calibrators don't transfer" is a new finding (Kuzucu).
- I should not describe YOLO26 as NMS-free without naming the head and the `ultralytics` version (see the head-default conflict in the source audit).
- I should not attribute an "overconfidence fix" claim to DEIM; the paper does not make it.
- I should not attribute architectural causes ("IoU-aware heads lose more small-VRU recall") to cross-repository comparisons. The design cannot isolate the head from the recipe, data pipeline and backbone, except in the YOLO26 dual-head control.
