# Independent review of the existing-seed missed-GT diagnosis

GPT Sol, 2026-11-26. Reviewed GPT Sol commit `4fc7938a010b2e0266db5479058d0d02b929d072`, including the note, counts, provenance, discussion, PNG and experiment scripts. Original B/B2 experiments and reused matching helper: Claude Opus 5.5. This is a separate review task; AI review does not replace my explicit GitHub merge approval. G0 remains pending.

**Verdict: scientific accounting passes; one small privacy correction is required before publication.** No numerical or matching defect was found that changes the two-seed interpretation. No implementation files were edited, and no peer agreement is asserted.

1. **Required publication fix — personal private-evidence locations in the reproduction commands.** `experiments/2026-11-26_seed_miss_diagnosis/README.md:11` and `:12` publish absolute personal-machine paths, including the private input/output locations. Replace these with caller-supplied variables such as `$CpuPython`, `$PlotPython`, `$BddInputs` and `$PrivateEvidence`; keep the repository-relative script paths. No raw annotation/image IDs, geometry or private cache records were found in the new public counts, provenance or PNG. This objection concerns disclosed storage locations, not the overlap result.
2. **Optional wording precision.** The figure title in `figure.py:48` says “changed identities,” and the note opens with “identities.” Use “changed GT detection status” / “GT annotations” so a standalone figure cannot suggest physical-person identity tracking. The note's explicit final limitation already gives the correct per-annotation interpretation.

The coordinator can apply these small edits directly. There is no outstanding scientific objection requiring another experiment.

The independent checker reads retained private caches, rebuilds every canonical key directly from the hash-frozen GT manifest, and checks uniqueness, explicit evaluator annotation-ID mapping, image, exact box and height equality in both runs. The three populations are disjoint: selection 1,842 images / 2,376 GT; clear day 1,764 / 2,450; all-weather night 3,929 / 2,843. Both caches contain exactly these common eligible GT sets, including images without pedestrians in FP denominators. The retained geometry key is an annotation join, not an assertion of physical identity across images.

Independently recomputed counts below use order **both detected / B only / B2 only / neither**:

| Frozen policy | Population | Reproduced overlap | FP B / B2 |
|---|---|---|---|
| Source FPPI 1 | Selection | 1,552 / 124 / 109 / 591 | 1,842 / 1,842 |
| Source FPPI 1 | Clear day | 1,646 / 143 / 110 / 551 | 1,970 / 1,932 |
| Source FPPI 1 | Night | 1,395 / 178 / 233 / 1,037 | 1,793 / 2,136 |
| Source recall .80 | Selection | 1,803 / 98 / 98 / 377 | 7,995 / 9,476 |
| Source recall .80 | Clear day | 1,888 / 100 / 111 / 351 | 7,988 / 9,671 |
| Source recall .80 | Night | 1,756 / 175 / 224 / 688 | 9,293 / 12,797 |

At primary night thresholds, the independently obtained 3-by-3 state matrix (B rows, B2 columns; absent / below / detected) is `[[345,112,26],[131,449,207],[27,151,1395]]`. Clear day is `[[187,49,17],[57,258,93],[24,119,1646]]`. Thus night joint ceiling absence is 345; exactly-one ceiling presence is `(112+26)+(131+27)=296`. Clear-day counterparts are 187 and 147. Ceiling overlap (both / B only / B2 only / neither) is 2,202 / 158 / 138 / 345 at night and 2,116 / 81 / 66 / 187 on clear day, matching panel C.

Night B/B2 marginal ceiling absence is 483/503, versus clear-day 253/268. The resulting differences are 6.6626/6.7538 percentage points; 345/2,843 is instead an absolute joint absence share. Primary night missed-union accounting is 1,037 shared + 411 changed = 1,448; B2's net gain is 233 minus 178 = 55. These support the reported distinction between similar marginals and different per-annotation detected sets, conditional on these two systems.

All frozen thresholds equal their existing source reports exactly: primary B/B2 `0.10467208921909332` / `0.10264253616333008`; .80 sensitivity `0.014860522001981735` / `0.010537411086261272`. Both source .80 policies have saved status **FEASIBLE**. Primary selection cost is exactly FPPI 1; the source selector is explicitly exploratory/post hoc and source-only. This review did not reselect thresholds. All six aggregate populations reproduce the public B/B2 TP, FP and ceiling marginals at both policies; test FPPI is unequal, as disclosed.

Source inspection confirms deterministic descending score / candidate-ID order, highest-IoU unmatched GT with annotation-ID tie breaks at IoU >= .50, and inclusive threshold prefixes. Removing a lower-score suffix leaves earlier assignments unchanged. `None` means unmatched at the saved candidate floor, while a finite score below the operating threshold remains a distinct state; neither implies a raw geometrically overlapping box is absent. The reference helper keeps zero-area native candidates as FPs. Prediction arrays have complete unique image coverage, valid offsets, finite boxes/scores, floor 1e-4 and no all-class cap hits. Prediction, GT, evaluator/helper, public report and matched-report hashes agree with provenance; inference-summary hashes, 1280 resolution, zero cap-hit metadata and recorded checkpoint hashes also agree. Checkpoint bytes and original inference were not independently rerun.

All policy/population/height 3-by-3 matrices match an independent recount with the existing fixed bins `[0,16)`, `[16,32)`, `[32,64)`, `[64,128)`, `[128,infinity)`. Their GT totals partition each population. The PNG was visually inspected: segment counts, B/B2 colors, GT denominators, percentage axis and distinction between operating points and ceiling match the tables; no numerical plot correction is needed.

For a bounded check beyond retained assignments, the unchanged reference matcher was rerun on 24 deterministically chosen images per run, totaling 241 GT: two empty, four nonempty by sorted name and two most crowded images from each population. Every per-GT matched score, absence and FP-score multiset agrees with the private cache. This exercises empty/crowded cases but does not independently rematch all 7,669 GT or validate a different matching algorithm. Full-population overlap counts are independently reduced from retained assignments; that distinction limits this verification.

Reproduction: run the accompanying `2026-11-26_seed_miss_review_check.py` with `--author`, `--inputs` and `--cache` pointing to the reviewed checkout, existing BDD inputs and retained diagnosis caches. It emitted only aggregate counts and PASS assertions using the existing CPU environment. A separate metadata-only read checked inference-summary/checkpoint metadata hashes and the two ceiling-difference calculations above. No inference, installations, downloads, threshold search, bootstrap, GPU/Colab work, synthetic tests or framework construction were performed.

The note correctly limits inference to two frozen trained seeds, labels source .80 as unequal-test-FP sensitivity, separates absolute absence from condition differences, and makes no causal, novelty, seed-distribution or G0 claim. The discussion records failed routing attempts and expressly withholds agreement; this review neither verifies the historical tool transport independently nor treats those failed attempts as discussion with Claude. Public aggregate consistency does not establish original annotation correctness, mirror publisher identity, physical-person tracking or generalization to future seeds.
