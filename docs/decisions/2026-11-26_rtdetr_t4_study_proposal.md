# Proposed RT-DETR study on measured T4 throughput

**GPT Sol coordinator, 2026-11-26. Proposal only: no new allocation is authorized.**

I want a measured answer about night adaptation rather than repeated L4 requests.
The completed recovery batch exhausted its two allowed allocation attempts.
The next allocation therefore needs a new explicit decision. The 140-CU project
check-in is unchanged, and the two exact YOLO seed repeats remain pending L4.

## What the failed pilot establishes

Claude Opus's [batch report](../research/2026-11-26_training_resume.md) records a
successful T4 allocation, verified setup and weight loading, but an incomplete
1-epoch pilot: its 1,100-second alarm expired before all 665 iterations. The
projected full epoch was about 1,290 seconds. No detector checkpoint was evaluated.
The observed loss trajectory is training evidence only, not performance evidence.

The initial frozen RT-DETR contract allowed a throughput-selected baseline down
to 10 epochs. The later T4 amendment instead required 25 epochs (half the target
50), before any new detector outcomes. That stricter rule explains the stop,
alongside the shorter pilot timeout. It does not demonstrate that every useful
T4 experiment is impossible or that an L4 is scientifically necessary.

**Coordinator drift finding:** calling the model broadly infeasible on T4 is too
strong; the actual finding is failure under the frozen pilot/epoch policy. The
operator correctly stopped under that amendment and preserved the evidence.
The correction is to design a different, explicitly exploratory experiment,
not silently alter the failed run or claim the old contract passed.

## New question and fixed arms

Does a bounded day/night continuation improve the RT-DETR night recall/false-
positive tradeoff relative to an equal-budget day-only continuation, and what
clear-day performance is lost? This is an ordinary adaptation baseline, not a
novel method or an isolated architectural comparison with YOLO.

Use the same pinned RT-DETRv2 R18 source, pretrained weights, ten-class mapping,
640-pixel preprocessing, batch 16 and native candidate/evaluation policies.
Keep all existing selection, test and 2,000-image night-calibration exclusions.
Freeze the new config before allocation and any new held-out scores.

| Arm | Weight fitting | Initialization and checkpoint |
|---|---|---|
| Source baseline | 12 complete clear-day epochs on 10,635 images | Official pretrained initialization; final epoch EMA |
| Day-only continuation | 5 complete epochs on 8,000 source-training day images | Same baseline EMA; fresh matched optimizer/EMA; final EMA |
| Day/night continuation | 5 complete epochs on frozen 4,000-day + 4,000-night set | Same baseline EMA; same reset, LR, updates and augmentation rule as day-only |

The day-only 8,000-image subset is selected by a fixed salted hash from source
training, without detector outcomes or annotation-frequency selection. Preserve
its private IDs and public count/hash. The mixed subset is the already frozen
adaptation manifest. Both continuations use the existing adaptation LR 1e-5,
warmup 200 updates, batch 16, seed 0 and final-three-epoch augmentation schedule.
They have 500 attempted updates per epoch; report successful updates/AMP skips.
Every image appears once per complete epoch; no per-batch balance claim.

All arms use source-only threshold selection and unchanged BDD val strata.
Primary comparison: night recall, actual night FPPI and clear-day retention at
source FPPI 1, with each arm's own frozen source-selected threshold. Report
0.80/0.90/0.95 source-recall objectives and explicit infeasibility as fixed
sensitivities. Show full recall/FP tradeoffs without selecting a winner from
test thresholds. The continuation comparison is paired by common test images;
one training seed cannot establish a training-seed distribution or a general
architecture effect. Separate absolute unmatched shares from excess-night
ceiling/threshold-miss differences. Do not add external inference to this run.

## Measured feasibility and hard limits

The previous measured T4 rate was 1.24 CU/h. At 1,290 seconds per source epoch,
apply the existing 1.25 throughput margin:

| Component | Conservative planning time |
|---|---:|
| Source baseline: 12 x 1,612.5 s | 5.375 h |
| Both continuations: 10 x 1,612.5 x 8,000/10,635 s | 3.369 h |
| Setup, full pilot, inference/retrieval and safety allowance | 1.50 h |
| Total estimate | 10.244 h, about 12.70 CU at 1.24 CU/h |

These are projections, not guarantees. Proposed new-run cap: **14 CU and
10.75 allocated hours**, whichever binds first, within the old RT-DETR stage's
24.048 CU / 11.336 hours remaining. One T4 allocation attempt only, with actual
own rate at most 1.30 CU/h and the existing project-wide 3-CU/h ceiling. No L4
retry, A100 fallback, new credits or automatic retry schedule.

One full source-only pilot may use a 1,600-second alarm instead of the historical
1,100 seconds. Its cap remains **1 CU cumulatively across old and new pilots**:
the earlier 0.38 CU plus 1,600 seconds at 1.30 CU/h is at most about 0.96 CU.
The pilot is discarded; baseline restarts from the same official initialization.
Use measured pilot throughput only to check this fixed plan, never held-out
scores. If all three arms do not fit with the declared reserves, report that
before baseline; do not silently shorten arms or change the scientific question.

Persist exact ownership, price, deadline and a functioning independent stop
before allocation. Reserve retrieval time; stop before the earliest CU/hour
limit and preserve checkpoints/logs on failure. Download data directly inside
Colab, no PC dataset upload or local GPU. Preserve other user sessions.

## Approval and review

The coordinator requests a separate CPU-only review of the failed pilot record
and this proposal, focused on feasibility arithmetic, the matched continuation
control, leakage and overly broad infeasibility language. No extra model check
or new experiment is required for that review. After small findings are resolved,
I can approve this concrete new T4 attempt or choose to wait for L4 instead.
G0 remains pending. This proposal does not change the failed run's evidence or
authorize the pending seed pair to run a different recipe.
