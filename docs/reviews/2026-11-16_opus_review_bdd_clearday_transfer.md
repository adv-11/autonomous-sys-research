# Review: BDD clear-day threshold transfer (YOLO11s, arms A/B/C)

**Claude Opus (independent review task), 2026-11-16.** This is a separate Claude Opus task standing in for GPT Sol, whose workspace is out of credits. I did not run the experiment. I reviewed `622bbc8..099928a` on `t3/9306f2e9` (head `099928a`) read-only and recomputed key numbers from the private predictions with my own matcher. This is an AI review. It is not the owner's merge approval, and **G0 remains pending**.

**Verdict: ready after fixes.** Every headline number I recomputed reproduces exactly. No restricted data is committed. The compute ledger is consistent. What remains is one branch-base problem, two places where the wording overstates what the definitions and the seed count support, and some small provenance corrections. None of them changes a number.

## What I verified independently

My script used its own greedy IoU ≥ 0.5 matcher, threshold rules and bootstrap with different RNG seeds. It did not import `evaluate_transfer.py` or `matched_fppi.py`. Prediction SHA-256s match the remote `out_sha256` for all three arms.

| Check | Report | Recomputed |
|---|---|---|
| Selection ceiling A / B / C | 0.770 / 0.883 / 0.762 | 0.7698 / 0.8834 / 0.7622 |
| B t\*(0.80) | 0.0149 | 0.014861 |
| B night recall / FPPI / ceiling | 0.679 / 2.37 / 0.830 | 0.6792 / 2.365 / 0.8301 |
| B night loss = never-a-candidate + removed-by-threshold | 0.132 = 0.067 + 0.066 | 0.1322 = 0.0666 + 0.0656 |
| B night / clear-day oracle FPPI at 0.80 | 16.19 / 3.66 | 16.19 / 3.66 |
| B night-clear (3,274 images) recall | "matches night" | 0.6803 |
| B ≥128 px ceiling, night vs clear day | 0.87 vs 0.98 | 0.867 vs 0.979 |
| B night recall 95% CI (own bootstrap seed) | [0.640, 0.719] | [0.636, 0.719] |
| Matched L = 1: night recall A / B / C | 0.459 / 0.553 / 0.460 | 0.4594 / 0.5533 / 0.4601 |
| Matched L = 1: B − A night recall, paired CI | +0.094 [0.075, 0.113] | +0.0939 [0.074, 0.113] |
| Matched L = 1: B − A night loss, paired CI | +0.008 [−0.018, 0.033] | +0.0081 [−0.016, 0.033] |
| C − A components, L = 0.5 | −0.026 / +0.038 | −0.0257 / +0.0379 |
| Night oracle recovery at matched FPPI; night gap | 0.03–0.07; 0.12–0.18 | 0.028–0.067; 0.123–0.177 |

All matched-FPPI rows for L = 0.5, 1, 2 and 4.5 also agree to three decimals. Validation clear-day FPPI at the selection-matched thresholds is within 0.12 of L for every arm, so the matching holds on the test split as well.

### Bootstrap

- `evaluate_transfer.py:204-237` resamples selection and each test stratum independently and reselects t\* in every replicate, as the configuration requires.
- `matched_fppi.py:121-123` draws one set of weights per stratum over sorted names and reuses it for every arm. Because `Population` order is identical across arms, B − A and C − A are correctly paired, and my paired bootstrap matches.
- Replicates in which the selection target is infeasible are dropped, which makes the intervals conditional on feasibility. For every reported feasible target the infeasible count is 0 (`bootstrap_infeasible_replicates`), so this has no effect here.

### Definitions

- **Matching:** the unchanged `ReferenceEvaluator` greedy rule. Greedy versus "any candidate at IoU ≥ 0.5" changes ceilings by at most 0.003.
- **Ignore regions and crowds:** the all-pedestrian population has none (`reject` policy; the legacy labels have no crowd flag). The ≥32 px population matches eligible GT first, then absorbs candidates into short-GT ignore regions at IoA ≥ 0.5 (`metrics.py:121-144`).
- **Height bins:** measured on original 720-px GT heights.
- **Candidate cap:** never reached. The maximum is 1,317 all-class candidates per image against a cap of 3,000.
- **NMS dropout:** no image has zero candidates, so no image was silently emptied by the NMS time limit (relevant to A's 256-image prediction batches).
- **Score floor:** the median per-image minimum pedestrian score is about 1.06e-4, so the 1e-4 floor is what binds.

### Compute

- The ledger stages sum to 32.42 CU (16.72 h × 1.94 CU/h), against a displayed balance drop of 32.38 CU.
- Stage times match `logs/queue.log`.
- Teardown is shown in `logs/ledger.log`: 0 active assignments and no server sessions.

### Restricted data

- No committed file contains BDD-style image identifiers or box arrays. The `peds`, `bbox` and `image_id` matches are code keys only.
- `figures.py` loads no images.
- The four PNGs are plots.

## Findings (most severe first)

### F1 (P2, interpretation): the "never a candidate / removed by threshold" split depends on definitions, not only on seeds

**Where:** `docs/research/2026-11-15_bdd_clearday_transfer.md:5`, `:47` ("about half never produced and half removed by the threshold") and `:70`.

**Problem:** the ceiling counts a pedestrian as a candidate only when a pedestrian-class box with score ≥ 1e-4 matches it at IoU ≥ 0.5 under Ultralytics' single-label (max-class) NMS (`amendment_2.json:5`). Moving either cut point moves B's night split substantially, and the loss itself stays 0.132:

- **IoU cut:** with any candidate at IoU ≥ 0.3, the night-minus-clear-day ceiling gap is 0.043 for B (0.949 vs 0.906) instead of 0.067, and 0.050 for A (0.901 vs 0.851) instead of 0.088. Roughly 35–45% of the "never a candidate" component is pedestrians that do have a candidate, just a poorly localized one.
- **Score floor:** at 1e-3 instead of 1e-4, B's ceiling gap rises to 0.090 (0.869 vs 0.779), leaving 0.042 for the threshold. The night ceiling is "softer": B loses 0.051 of night ceiling between 1e-4 and 1e-3, against 0.028 on clear day.
- **Class confusion (cannot be checked):** pedestrians boxed as rider or another class are also counted as "never a candidate". Non-pedestrian boxes were discarded at inference, so this share cannot be measured.

**What survives:** both components stay positive under every variant I tried.

**Fix:** rename the component, for example "no pedestrian-class candidate at IoU ≥ 0.5 above score 1e-4". Replace "about half never produced" with a statement that the split is definition-dependent, and add the two sensitivities above. Keep "both components are positive" as the robust claim.

### F2 (P2, process): the reviewed branch does not contain its parent commit `622bbc8`

**Problem:** `git merge-base 622bbc8 099928a` is `ad96840`. The task branch forked before `622bbc8` ("Freeze dataset scope at five and lift the compute envelope", 20:33:32Z), so `git diff 622bbc8..099928a` shows that decision section deleted. In this branch's tree, the record that authorises the spend is therefore missing:

- 32.4 CU was spent, above `envelope_CU: 20` in the frozen `config.json:158`.
- `amendment_1.json:5` cites the coordinator's lifted envelope as its authority.

A merge-base PR into `bdd-legacy-transfer` would keep the section, but a squash, rebase or PR against `main` could drop it.

**Fix:** rebase or merge onto `622bbc8` before opening the PR, and add one line to the ledger or report citing that commit as the spend authority. While there, record cumulative project GPU spend against the 100 CU check-in, because the ledger gives only this session's 32.4 CU.

### F3 (P2, overstatement): "the night gap does not change" with resolution

**Where:** report `:68` ("the night-minus-clear-day loss is unchanged"); task claim 3.

**Problem:** the B − A loss intervals span about ±0.03 ([−0.030, 0.038] across L), and B is one training seed. The data support "no detectable change; a difference of up to about 0.03 either way cannot be excluded at the image level, and seed variance is not included". The recall gain itself (+0.08 to +0.10) is robust: it is more than 9× the A/C seed difference in night recall (≤ 0.009).

**Fix:** reword the bullet accordingly.

### F4 (P3, provenance): amendment `written_utc` stamps are later than their own commits

| Amendment | `written_utc` | Commit time |
|---|---|---|
| `amendment_1.json:4` | 20:50Z | 20:44:19Z |
| `amendment_2.json:4` | 23:45Z | 23:38:51Z |
| `amendment_3.json:4` | 10:45Z | 10:32:06Z |

**What the evidence shows:** git and file times still support the claimed order:

- `amendment_1` precedes the trainA start (20:44:44Z).
- `amendment_2` precedes the h32/low evaluations (23:39Z).
- `amendment_3` precedes the first matched outputs (10:33–10:34Z).

There is one disclosure gap. The preregistered `eval/A_640.json`, which already holds validation ceilings per stratum, was written at 23:36Z, before `amendment_2`. Its "no val transfer number had been viewed" (`amendment_2.json:6`) is literally true, because all transfer was undefined, but validation ceilings existed.

**Fix:** correct the stamps to the commit times, or drop them, and add one sentence on the existing `A_640.json`.

### F5 (P3, labelling): C − A comparisons go beyond amendment 3

**Problem:** `amendment_3.json:13` specifies only B − A paired differences. The C − A rows (report `:62-63`) and the seed-based withdrawal of the decomposition-shift claim are additional post-hoc analyses. Separately, the FPPI grid was chosen after A's and B's fixed-target validation results were known (`amendment_3.json:9`).

**Assessment:** both are labelled post hoc overall, and the withdrawal is conservative.

**Fix:** label the C − A rows "exploratory, beyond amendment 3".

### F6 (P3, wording): what is preregistered

**Problem:** report `:94` says "only B's 0.80 result is preregistered". The A and C infeasibility outcomes are also preregistered results. B and C entered through `amendment_1` before any training, not through the frozen config.

**Fix:** state that A, the primary arm, could not test the preregistered question, and that the headline analysis rests on the amendment-1 resolution arm.

### F7 (P3, traceability): committed aggregates do not record their prediction hashes

**Problem:** every committed result JSON has `"preds_sha256": null` (`evaluate_transfer.py:175`). The prediction and weight SHA-256s exist only in private `preds/*.npz.json`. Hashes are not restricted data.

**Fix:** add them to `compute_ledger.json` so the committed numbers are tied to specific predictions.

## Assessment of the four main claims

1. **Feasibility:** confirmed. A, C infeasible at every target; B feasible at 0.80 only.
2. **B at 0.80:** numbers confirmed. The "even split" is fragile to definitions (F1).
3. **Matched FPPI:** the +0.08–0.10 night-recall gain is confirmed. "Gap unchanged" needs softening (F3).
4. **Seed instability:** confirmed. The A→C component shift equals the A→B shift, and withdrawing the decomposition-shift claim is correct.

With one architecture, two 640 px seeds and one 1280 px seed, the report correctly avoids asserting a mechanism. The positive night recall loss at the transferred clear-day threshold is well supported for this model.
