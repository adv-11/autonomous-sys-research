# Night threshold remedies, a second 1280 px seed and an ACDC panel

**Claude Opus 5.5 (designated executor), 2026-11-17/18. Exploratory follow-up to the [BDD clear-day transfer report](2026-11-15_bdd_clearday_transfer.md) (PR #13). Not yet reviewed; G0 pending.**

I want to know whether the night recall lost at a transferred clear-day threshold can be recovered by choosing the threshold differently, and at what false-positive cost. The part with no matched candidate cannot be recovered by any threshold. [Amendment 4](../../experiments/2026-11-15_bdd_clearday_transfer/amendment_4.json) (`0b8909e`) fixed the remedies, calibration data and Colab stage before any number existed. Everything here is exploratory and post hoc.

> Same provenance limits as PR #13: **BDD100K legacy 2018 labels**, Hugging Face mirror images (archive SHA-256 verified; publisher unverified), one architecture (YOLO11s), image bootstrap without training-seed variance.

## Remedies and calibration data

- **Equal-FPPI night threshold:** the lowest night-calibration score whose night FPPI stays within the clear-day budget (the clear-day selection FPPI at t*).
- **Equal-recall night threshold:** the highest night-calibration score whose night recall reaches the source recall target.
- **Platt scaling** `p = σ(a·logit(s) + b)`, fitted on TP/FP candidates:
  - **Global** (fitted on the clear-day selection split): strictly increasing, so reselecting the threshold selects the same detections. Its recovery is exactly zero by construction.
  - **Per condition:** the night threshold is the raw score whose night-calibrated probability equals the clear-day calibrated probability at t*.
- **Calibration data:** 2,000 BDD legacy **train** images with `timeofday = night`, the first by salted SHA-256 ([record](../../experiments/2026-11-15_bdd_clearday_transfer/nightcal_manifest_record.json); 1,226 pedestrians; none trained on, since training was clear-day only). Test data: all 3,929 BDD val night images. A val-night split-half proxy, computed before the Colab inference existed, gave the same pattern ([proxy aggregates](2026-11-17_threshold_remedies/)).
- **Intervals:** 1,000-replicate image bootstrap, with selection, calibration and test images resampled independently and thresholds and Platt maps refitted in every replicate.

## Results: a threshold can move along the night curve, not onto the clear-day curve

Night test values; Δ is relative to the transferred clear-day threshold; 95% intervals.

| Arm, operating point | Transferred night recall / FPPI | Threshold part | Equal-FPPI: Δrecall, night FPPI | Equal-recall: Δrecall, night FPPI | Per-condition Platt: Δrecall | No matched candidate (unrecoverable) |
|---|---|---|---|---|---|---|
| A, clear-day FPPI 1 | 0.459 / 0.46 | 0.081 | +0.060 [+0.042, +0.079], 1.04 | +0.091 [+0.038, +0.149], 1.47 | +0.004 [-0.006, +0.016] | 0.088 |
| A, clear-day FPPI 4.5 | 0.600 / 2.79 | 0.045 | +0.033 [+0.023, +0.048], 4.94 | +0.069 [+0.023, +0.105], 9.30 | +0.007 [-0.002, +0.019] | 0.088 |
| B, t*(0.80), preregistered | 0.679 / 2.37 | 0.066 | +0.044 [+0.031, +0.062], 4.79 | +0.133 [+0.086, +0.170], 20.96 | +0.009 [+0.002, +0.022] | 0.067 |
| B, clear-day FPPI 1 | 0.553 / 0.46 | 0.110 | +0.068 [+0.051, +0.088], 1.10 | +0.139 [+0.092, +0.198], 3.11 | +0.007 [-0.003, +0.017] | 0.067 |
| B, clear-day FPPI 4.5 | 0.682 / 2.48 | 0.066 | +0.045 [+0.031, +0.060], 4.96 | +0.133 [+0.088, +0.156], 22.37 | +0.008 [+0.001, +0.018] | 0.067 |
| C, clear-day FPPI 1 | 0.460 / 0.50 | 0.109 | +0.065 [+0.042, +0.085], 1.06 | +0.095 [+0.042, +0.151], 1.65 | +0.004 [-0.007, +0.015] | 0.062 |
| C, clear-day FPPI 4.5 | 0.606 / 3.00 | 0.061 | +0.033 [+0.021, +0.045], 4.74 | +0.056 [+0.003, +0.099], 6.77 | +0.012 [+0.001, +0.025] | 0.062 |

![Night remedies on the night operating curve](2026-11-17_threshold_remedies/bdd_night_remedies.png)

- **Equal-FPPI** spends the clear-day false-positive budget at night. It recovers 0.03–0.07 recall, which is 53–87% of the threshold part (the threshold-removed loss relative to clear day), at the clear-day FPPI. It is the only remedy that does not cost more false positives than clear day already accepts.
- **Equal-recall** reaches the recall target at night, but the night operating curve is flat near its ceiling. For B at the preregistered 0.80, night recall rises from 0.679 to 0.813 while FPPI rises from 2.4 to 21.0. At clear-day FPPI 1 it costs 1.0–2.7 extra FPPI.
- **Platt per condition** recovers at most 0.012 (≤ 20%). Equal calibrated confidence keeps the night threshold close to the transferred one, which is consistent with night lowering TP and FP scores similarly (not tested directly). **Global Platt** recovers nothing, as it must.
- **Unrecoverable:** 0.06–0.09 recall at night has no matched candidate (IoU 0.5, score ≥ 1e-4). This bound depends on the definition, per the PR #13 sensitivity.
- **Mechanism, descriptively:** at every FPPI the night curve lies below the clear-day curve. Any single-threshold remedy trades false positives for recall along the night curve. Closing the gap needs better night candidates or scores, not a better threshold.

PENDING_B2

PENDING_ACDC

PENDING_NIGHTOWLS

PENDING_COMPUTE

## Limits

- Exploratory and post hoc throughout (amendment 4); none of these remedies was preregistered in the frozen config.
- The calibration set is BDD train night, the same camera fleet and label policy as the test. A deployed system would need its own night calibration labels, and the 2,000-image set is small: equal-recall intervals are wide (±0.05).
- Single architecture; the B2 seed check addresses only the 1280 px arm.
- The image bootstrap ignores training-seed variance and shared routes, drivers and cities.
