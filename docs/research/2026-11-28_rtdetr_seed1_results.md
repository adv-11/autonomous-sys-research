# RT-DETR seed-1 replicate: results

Step 2 of [the 2026-11-27 plan](2026-11-27_rtdetr_interpretation_next_steps.md). I approved the overnight
run on 2026-11-27. Claude Opus wrote the runner and evaluator and executed them on the local RTX 5060
(`experiments/2026-11-27_rtdetr_seed1/`). Public aggregates are in
[`results/2026-11-27_rtdetr_seed1/`](../../results/2026-11-27_rtdetr_seed1/). G0 stays pending.

## Run

- **Speed gate passed.** The median step took 0.70 s with 4 loader workers, against an average of
  2.14 s for seed 0 with 0 workers. The baseline therefore took 2.7 h instead of 7.9 h.
- **Bonus arms ran.** The gate projected the baseline under 5.5 h, so the seed-1 day-only and
  day/night continuations were added.
- **Completion.** The whole study took 4.1 h. All six stages exited with code 0, with no
  fallback and no stop.
- **Training recipe.** Identical to seed 0 except for the seed and the worker count: 20 + 5 + 5
  epochs, batch 16, constant LR, and strong augmentation stopped 3 epochs before the end.
  The workers were non-persistent so that this stop takes effect; see the experiment README.
- **Evaluation.** The unchanged evaluator, run with the same 1,000 bootstrap draws as seed 0.
  Recomputing seed 0 reproduced the published threshold (0.3445) and the published night recall, FPPI, intervals and decomposition.

## Results at the clear-day FPPI ≤ 1 threshold (BDD100K validation)

Intervals are 95% paired image bootstrap intervals. They do not include seed variance.

| Arm | Threshold | Clear recall | Night recall | Night FPPI | Night ceiling | Ceiling part | Threshold part |
|---|---:|---:|---:|---:|---:|---:|---:|
| Seed 0 baseline | 0.344 | 0.690 | 0.592 [0.564, 0.622] | 0.65 [0.57, 0.74] | 0.820 | 0.062 [0.033, 0.090] | 0.036 [0.007, 0.058] |
| **Seed 1 baseline** | 0.345 | 0.688 | 0.582 [0.554, 0.611] | 0.61 [0.52, 0.70] | 0.816 | 0.062 [0.032, 0.091] | 0.043 [0.017, 0.066] |
| Seed 1 + day only | 0.348 | 0.689 | 0.580 [0.554, 0.609] | 0.62 [0.54, 0.72] | 0.814 | 0.066 [0.036, 0.095] | 0.043 [0.016, 0.068] |
| Seed 1 + day/night | 0.353 | 0.691 | 0.593 [0.563, 0.625] | 0.57 [0.49, 0.68] | 0.845 | 0.036 [0.007, 0.063] | 0.062 [0.032, 0.085] |

"Ceiling part" is the difference in the share of pedestrians with no matching detection, night
minus clear day. "Threshold part" is the difference in the share that had a matching detection
but was removed by the threshold.

## Findings

1. **Pre-declared readout: `SPLIT_REPRODUCED`.** Seed 1 gives 0.062 ceiling + 0.043 threshold,
   against 0.062 + 0.036 for seed 0. Both seed-1 intervals exclude 0. The largest move is 0.007,
   far below the 0.03 cut-off, and the order did not flip. Paired seed-1 minus seed-0
   differences:

   | Part | Difference | Interval |
   |---|---:|---:|
   | Ceiling | 0.000 | [−0.016, 0.014] |
   | Threshold | +0.007 | [−0.009, 0.029] |

   Both intervals include 0. The selection ceiling is 0.864, the same as seed 0, so there is no
   under-training flag.

   **Caveat:** "ceiling exceeds threshold" holds for both seeds' point estimates only. The two
   intervals overlap, so ceiling dominance itself is not established, for this detector or
   across detectors.
2. **Seed changes FPPI more than recall.** Seed 1 minus seed 0:

   | Condition | FPPI | Recall |
   |---|---:|---:|
   | Night | −0.043 [−0.078, −0.011] | −0.009 [−0.022, 0.000] |
   | Clear day | −0.02 [−0.08, 0.04] | — |

   A seed-to-seed FPPI change of 0.04 is about half the seed-0 adaptation effect (−0.095). The
   image bootstrap understates total uncertainty for FPPI contrasts.
3. **The night-training effect on false alarms replicates, and is smaller.** Day/night minus day-only
   at seed 1:

   | Measure | Seed 1 | Seed 0 |
   |---|---:|---:|
   | Night FPPI | −0.051 [−0.077, −0.015] | −0.095 |
   | Night recall | +0.013 [0.002, 0.027] | +0.006, unestablished |
   | Night recall at the 0.80-recall threshold | +0.021 [0.004, 0.036] | — |

   The recall gain is small. It counts as an additional, unplanned contrast (I looked at it
   after seeing the data), not as a confirmed effect.
4. **Night training raises the candidate ceiling at seed 1.** The night ceiling rises from 0.814
   to 0.845. Its paired ceiling-part change is −0.030 [−0.044, −0.016].
   - The seed-0 rise (0.816 → 0.835) had no interval, and the 2026-11-27 plan doc called it a
     ranking change, not a ceiling lift. Seed 1 contradicts that wording.
   - The transferred threshold captures only part of the new candidates: the threshold-removable
     night share rises from 0.234 to 0.253.
   - After night training, the split reverses: the threshold part (0.062) exceeds the ceiling part
     (0.036). Which part dominates therefore depends on the training data, not only on the detector.
5. **Recall 0.90 and 0.95 remain infeasible** in every arm. The clear-day selection ceiling is
   0.864–0.870.

## Limits

- Two seeds, 20 of the recipe's 120 epochs, and BDD100K legacy labels.
- The image bootstrap excludes seed and route variance, and finding 2 shows the seed variance
  matters for FPPI.
- The adaptation arm still confounds night content with 4,000 unseen images.
- Findings 3 and 4 are exploratory. They come from repeated inspection of the same test set.
- The seed-1 continuations start from the seed-1 baseline, so baseline and continuation seeds are
  not crossed.

## What this changes

- Keep "both parts of the night loss are positive" for RT-DETR. It now replicates across two
  seeds.
- Drop any claim that one part dominates. The point-estimate order holds across seeds for the
  baseline, but the intervals overlap and night training reverses it.
- Restate the adaptation result as follows: night-mixed fine-tuning lowers night false alarms in
  both seeds, and in seed 1 it also lifts the candidate ceiling, with a small recall gain.
- Step 1, the CPU re-analysis, is still open.
