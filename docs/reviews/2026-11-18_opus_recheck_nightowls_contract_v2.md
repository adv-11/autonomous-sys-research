# Re-check: NightOwls contract v2 response to the Opus review

**Reviewer:** Claude Opus (independent re-check task), 2026-11-18. Read-only: no edits, commits, pushes or Colab.
**Target:** `origin/gpt-nightowls-external-contract` at `924d13b`. The response commits are `522562f..924d13b`, and v2 was frozen at `af7f442`. Prior review: `docs/reviews/2026-11-18_opus_review_nightowls_contract.md` (findings at `8a89a635`).

**Verdict: ready for PR.** All six findings are resolved in the contract text. I recomputed the BDD ≥50 reference exactly. The evaluator change only affects console output. No NightOwls metric exists on this machine. Two small items remain. Neither blocks the PR, but R1 should be fixed in this PR, before scoring.

## 1. Findings disposition

| Finding | Status | Evidence |
|---|---|---|
| H1: population mismatch | Resolved | v2:24-39 picks a new t\* on BDD ≥50 using `--min-height 50`, with short GT as same-category ignore regions. The same rule applies to selection, clear-day and night. The bootstrap picks t\* again on that population. v2:41-48 makes BDD ≥50 clear-day the primary clear reference and forbids all-height subtraction. v2:50-57 keeps the all-height t\* as a labelled secondary on ≥50. v2:59-64 discloses that occlusion is not aligned. |
| M1: FPPI comparability | Resolved | v2:68-75 makes `unused_nonpedestrian` primary for every BDD-vs-NightOwls contrast. v2:77-87 makes `person_compatible_ignore` a labelled sensitivity whose FPPI is not to be mixed with BDD's, and requires reporting ignored totals. See R1 for the code default. |
| M2: input scale | Resolved | v2:91-110 reports model-input-pixel bins (native × actual letterbox ratio), records the ratios (.5/.625 and 1.0/1.25) and states the confound. It authorises no scale-matched inference. |
| M3: recording dominance | Resolved | v2:114-150 adds R1–R5 per-recording aggregates, a leave-dominant-out pooled sensitivity (dominant key fixed by GT count), the restored support floors (≥10 jointly covered GT per key, 150 boxes) and disclosure of the 126 possible multisets and P = .32768. Counts check: 1,005 + 291 + 4,994 + 332 + 149 + 860 = 7,631. 4,994 / 7,631 = .654 and 4,994 / 6,771 = .738. C(9,5) = 126. The post-freeze labelling note ("string order", reference:67-71) is harmless: there are 5 keys, all 4 digits, so numeric and string order are identical. |
| L1: undocumented edits after freeze | Resolved | v2:154-162 adds the correction note. The v1 header now points to v2 and labels itself as history. |
| L2: disk and download | Resolved | v2:166-195 reads images from the ZIP without extracting, sets a 60-min cumulative / 120-s stall cap, and keeps a CU ledger. Arithmetic: 95 min × 1.94 = 3.07 CU, and × 3 = 4.75 CU. |

## 2. Timing

- `af7f442` (v2) is an ancestor of `924d13b`, and the v2 file is unchanged in `af7f442..924d13b`.
- The private ≥50 outputs have mtimes of 00:02–00:07 −0800. The commit is dated 00:01:34 −0800, which is consistent with "computed after the freeze".
- This machine holds no NightOwls prediction or metric files: none in the main `outputs/`, any worktree's `outputs/`, or `data/`. The only NightOwls artefacts are annotation canonicals, verification files and access probes.
- v2:13-20 correctly calls itself pre-scoring, not pre-prediction.
- Limits:
  - Commit times are self-reported.
  - The GitHub events API showed no recent pushes, so I have no server-side push timestamp.
  - Colab was not inspected (out of scope). The claim that nothing was scored on Colab therefore rests on the coordinator's hold.

## 3. Evaluator change

The diff (`evaluate_transfer.py:9, 261-266`) changes only the console `print` loop, which runs after `args.out_json.write_text(...)` (line 255). It also adds a docstring line. It cannot change any stored number. Sol's A JSON from before the fix and the retained A JSON have the identical hash `d23bfb38…e201`.

## 4. Spot recompute (B_1280, ≥50)

I ran the branch evaluator (identical to the worktree file apart from CRLF line endings) on `preds/B_1280.npz` (sha `143534c8…1d55`, matching the ledger) and `private/gt_pedestrian.json` (sha `37929323…7bbf`). Flags: `--min-height 50 --replicates 20`, under the specified Python with `-I -B`. Exit 0, and the full ReferenceEvaluator checks passed.

- t\*(.80) = **0.23994138836860657**; t\*(.90) and t\*(.95) are also identical.
- Selection: 945/1,181 = .800169.
- **Night: 1,003/1,616 = .620668**, FPPI .154747, precision .622595, ceiling .899752. Misses split 162 / 451.
- Clear-day: .821656 / .382086 / .604924 / .972134.
- `operating`, `ceiling_recall`, `by_height` and `loss_vs_clear_day` at .80, and the whole `strata` block, are **exactly equal** to Sol's `B_1280_h50.json`.
- Sol's private `fixed_original_reference.py` (B all-height t\* on ≥50) also reproduces Sol's JSON exactly. Night: 1,249/1,616 = .772896.

## 5. Tests

- With the private NumPy pylib on the path, the relevant set (`test_bdd_clearday_transfer`, `test_nightowls`, `test_nightowls_archive`, `test_metrics`) ran **36 tests: OK, 0 skipped**. The new h50 regression actually ran.
- The full suite ran 204 tests with 1 failure: `test_evaluate.CliTests.test_real_module_cli_strict_output_provenance_and_rejection`. This is the known environmental failure, where a subprocess under `-I` cannot import the package. Neither `tests/test_evaluate.py` nor `src/threshold_transfer/evaluate.py` changed relative to `main`.

## Remaining objections (non-blocking)

- **R1 (fix in this PR, before scoring).** The code still labels the superseded primary profile.
  - `src/threshold_transfer/nightowls.py:18-19` sets `PRIMARY_PROFILE = "person_compatible_ignore"` and `SECONDARY_PROFILE = "unused_nonpedestrian"`.
  - `scripts/data/prepare_nightowls_transfer.py:27` defaults `--profile` to `PROFILES[0]`, which is `person_compatible_ignore`.
  - v2:68-75 makes `unused_nonpedestrian` primary for cross-dataset contrasts. An executor relying on the default or the constant names could label the sensitivity as primary.
  - Fix: make `--profile` required, or rename the constants by role (for example `PERSON_COMPATIBLE` and `PEDESTRIAN_ONLY`). This is display or CLI only; matching is unaffected.
- **R2 (clarify).** v2:124-125 says the leave-dominant-out result uses "original source t\* unchanged". Elsewhere, v2 uses "original" to mean the all-height policy (v2:50), and that policy is infeasible for A and C. Read literally, the sensitivity would cover only B's secondary policy. The intent appears to be "each reported policy's source t\*, unchanged". Clarify this in the PR before scoring.
- **Note.** v2:91-97 requires BDD model-input-height bins. The BDD reference note does not report them yet. For BDD they follow from native bins (ratio .5 or 1.0), so they can come with the results report. This is not a blocker.
