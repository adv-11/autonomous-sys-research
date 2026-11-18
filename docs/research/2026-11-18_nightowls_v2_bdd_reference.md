# BDD ≥50 reference for NightOwls v2

GPT Sol ran local CPU calculations on existing **BDD predictions only** on
2026-11-18 UTC, after freezing the [v2 amendment](2026-11-18_nightowls_contract_v2.md)
at `af7f442`. No NightOwls predictions were opened, matched or scored. These
are new source/reference calculations, post hoc on BDD; they do not turn the
external pre-scoring amendment into a pre-prediction registration. G0 remains
pending. The preserved [independent Claude Opus review](../reviews/2026-11-18_opus_review_nightowls_contract.md)
reviewed `8a89a635`, not these fixes; no new review approval is claimed.
Its copied file SHA-256 is
`dc9490fa60c972f9736983d507ab2ae2fa52b9a85cfe82e1b5340b31d79ef976`,
identical to the coordinator-supplied source before commit `522562f`.

The existing `evaluate_transfer.py` ran with **`--min-height 50`**, targets
.80/.90/.95, **1,000 bootstrap replicates**, original seed **20261115**, and
the full selection/clear-day `ReferenceEvaluator` equivalence checks enabled.
Using the original BDD seed reproduces the BDD evaluator's reference intervals;
the external joint resampling uses the v2/v1 seed 20261117. Predictions,
matching, candidate policy, populations and target selection were unchanged.
Short GT become ignore regions, not FNs. The final amendment fixes the source
height rule, regardless of whether a particular target is feasible.

All three runs have the same ≥50 support: **1,842 selection images / 1,181
eligible GT**, **1,764 clear-day images / 1,256 GT**, **3,929 night images /
1,616 GT**. Image counts include empty and ignored-only frames. Available BDD
evaluation labels cannot enforce NightOwls' not-occluded eligibility. Neither
height alignment nor model-input-height reporting removes that mismatch.

## Reselected ≥50 source thresholds (primary v2 policy)

| Run | t*(.80), primary | t*(.90), sensitivity | t*(.95), sensitivity |
|---|---|---|---|
| A_640 | 0.11140981316566467 | 0.0056989616714417934 | INFEASIBLE |
| B_1280 | 0.23994138836860657 | 0.024179309606552124 | 0.0009108111844398081 |
| C_640 | 0.12197767943143845 | 0.0036546909250319004 | INFEASIBLE |

At the primary .80 target, all three selection recalls are 945/1,181
= .8001693480. Apply each exact threshold unchanged to NightOwls; do not
replace it with the target oracle. B's .95 threshold is below 1e-3, so the
predeclared floor1e-3 decomposition sensitivity is not applicable there.

Primary BDD reference point estimates (≥50 GT, short pedestrians ignored):

| Run / BDD test | Recall | FPPI | Precision | Ceiling recall | No-matched-candidate misses / removed-by-threshold misses |
|---|---|---|---|---|---|
| A / clear-day | .824045 | 1.103741 | .347082 | .943471 | 71 / 150 |
| A / night | .621287 | .529397 | .325551 | .852723 | 238 / 374 |
| B / clear-day | .821656 | .382086 | .604924 | .972134 | 35 / 189 |
| B / night | .620668 | .154747 | .622595 | .899752 | 162 / 451 |
| C / clear-day | .831210 | .986395 | .375000 | .945064 | 69 / 143 |
| C / night | .608292 | .503945 | .331758 | .863861 | 220 / 413 |

Each miss pair sums to GT−TP at that operating point. These are BDD results,
not evidence about NightOwls. The full private JSON retains exact counts,
all targets, source feasibility, oracle diagnostics, bootstrap intervals and
reference/fast-path check dispositions. All three runs passed the full
selection/clear-day reference equivalence checks. B/C completed with exit 0
after the console-only correction described below; A's complete JSON was
retained without repeating its unchanged calculations a third time.

Private result SHA-256 values (`ARM_h50.json`):

- A: `d23bfb38ec6a93e051fad90f2828375587a9dd2fea0905f08f10ac8c6584e201`.
- B: `59dfd7a9f77c29b975db85e88909d11305bc502ef82dd9ff8df46f921fc60223`.
- C: `90032294b7f75f8a90e08f3131351a2d4f9822e7195f52e2d05c3f7c35359908`.

For anonymous recording labels in v2, use the historical inventory's exact
ordering: sort non-null native keys by **their string representation** and
assign R1–R5; null stays unkeyed. This makes the historical-order wording
operationally explicit without exposing keys or changing the chosen dominant
recording. The support-count sequence in v2 already uses that ordering.

## Original all-height threshold on the height-aligned population

Only B has an original feasible .80/.90/.95 all-height source policy: .80,
**t*=0.014860522001981735**. A/C and B's .90/.95 retain their original source
infeasibility. Reusing B's original t* on ≥50 BDD gives:

| BDD ≥50 population | TP / GT | Recall | FPPI | Precision | Candidate ceiling |
|---|---|---|---|---|---|
| Selection | 1,073 / 1,181 | .908552 | 3.864278 | .130997 | .966977 |
| Clear-day test | 1,138 / 1,256 | .906051 | 3.974490 | .139649 | .972134 |
| Night test | 1,249 / 1,616 | .772896 | 2.178671 | .127332 | .899752 |

These are the height-aligned secondary no-shift/reference expectations for the
original policy. They demonstrate why the original all-height .80 target is
not an equal-recall ≥50 operating point. They are not NightOwls observations.

## Reproduction and execution limitations

Base interpreter: `C:/Users/Advait/AppData/Roaming/uv/python/cpython-3.12-windows-x86_64-none/python.exe -I -B`.
Reuse already installed NumPy **2.2.6** by adding the existing private
`outputs/bdd_transfer_20261115/pylib` plus this checkout's `src` to `sys.path`;
no package was downloaded or installed. Run from `scripts/`, with absolute
paths to the evaluator and inputs. For each arm, pass:

```text
evaluate_transfer.py --preds BASE/preds/ARM.npz
  --gt BASE/private/gt_pedestrian.json --label "ARM h50 v2 CPU"
  --min-height 50 --out-json PRIVATE/ARM_h50.json
```

`BASE` is the main checkout's private `outputs/bdd_transfer_20261115` directory;
`PRIVATE` is this worktree's gitignored `outputs/nightowls_v2_bdd_h50`.
Prediction SHA-256 values must match the original
[ledger](2026-11-15_bdd_clearday_transfer/compute_ledger.json). Ground-truth SHA-256:
`37929323cb4943766a163a8ea8bf1e02ba1e244c5ae29fe6cebe02ce5a257bbf`.
The secondary fixed-threshold calculation reuses `match_chunk(..., min_h=50)`
and `Population.point(original_t)` over selection/clear-day/night, with exact
input hashes checked. Its reproduction script and aggregate receipt remain
in the same private directory. No boxes, image/recording IDs or predictions
are published here.

Two initial A executions wrote complete, identical JSON (SHA-256
`d23bfb38ec6a93e051fad90f2828375587a9dd2fea0905f08f10ac8c6584e201`), then
exited 1 while formatting the foggy slice's correctly undefined recall or
ceiling as a float. The first output and failure receipt are preserved
privately. The only evaluator change guards **console display** for zero-GT
slices; matching, null metrics and output calculations are unchanged. The
new end-to-end synthetic fixture verifies h=50 inclusion, h=49 exclusion,
null foggy recall/ceiling and successful CLI reporting. **36 relevant tests
passed**, including existing NightOwls/ZIP, reference metrics and BDD tests.
