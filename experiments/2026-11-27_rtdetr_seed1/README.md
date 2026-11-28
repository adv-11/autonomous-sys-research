# Seed-1 RT-DETR replicate (overnight, local RTX 5060)

Step 2 of [the 2026-11-27 plan](../../docs/research/2026-11-27_rtdetr_interpretation_next_steps.md).
I approved the overnight run on 2026-11-27 and allowed Claude to self-approve GPU runs.
Runner and evaluator written by Claude Opus. The seed-0 code in `../2026-11-26_local_rtdetr/`
is reused unchanged.

## What changes from seed 0

The output folder, the training seed (`setup_seed(1)`), and the number of loader workers:
- 4 workers on the main path.
- 0 workers on the fallback path, identical to seed 0.

Images and annotations are the seed-0 prepared files, linked by a directory junction.

**One deviation from the plan text:** the workers are **non-persistent**.
- The official loader pushes the current epoch into the dataset and collate function at the start of each epoch.
- Persistent workers would keep stale copies, so the strong-augmentation stop at epoch 17 would silently never happen.
- Non-persistent workers are the official default and keep the recipe exact.

## Rules, implemented in `run.py`

| Rule | Value |
|---|---|
| Speed gate | Median seconds per step over steps 25–200 must be ≤ 1.6 s, and the loader must not error |
| Gate fails | Rerun with 0 workers if the projected total is ≤ 9 h; otherwise run the substitute: both continuations from the seed-0 baseline with training seed 1 |
| Bonus | If the gate projects the baseline at ≤ 5.5 h, also run the seed-1 day-only and day/night continuations, provided they still fit the limit |
| Epoch-2 check | Stop if the projected finish is > 9 h; record a failure; no partial checkpoint is used |
| Hard limit | No stage runs past 9 h from the study start |

Every decision is logged in `outputs/local_rtdetr_seed1_20261127/study_events.json` (private).

## Evaluation (`evaluate_seed1.py`, CPU)

- Uses the same matching, populations, policies and bootstrap draws as seed 0 (rng 20261123).
- Recomputes seed 0 and checks it against the published threshold.
- Adds bootstrap intervals for the decomposition parts.
- Applies the pre-declared readout at the clear-day FPPI ≤ 1 threshold:
  - `SPLIT_REPRODUCED`: both intervals exclude 0 and the ceiling part still exceeds the threshold part.
  - `SPLIT_SEED_SENSITIVE`: either part moves by ≥ 0.03 or the order flips.
  - `INCONCLUSIVE`: anything else.
  - A selection ceiling below 0.85 is flagged as further evidence of under-training.
