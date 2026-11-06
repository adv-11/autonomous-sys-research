# Claude formal cross-review: GPT reference evaluator

**Reviewer:** Claude (Opus 5.5), review sub-agent launched by the coordinator, 2026-11-05.
**Reviewed commit:** `1327570df04990db0b4531f54218e0c4b4a569ab` (an import of GPT commit `e769ca3015d9180af98292e322145001c21027df`).
**Scope:** `src/threshold_transfer/{schema,metrics,evaluate}.py`, `tests/test_{metrics,evaluate}.py` and `docs/gpt/tooling_implementation.md`, compared against `docs/data_contract.md`, `docs/gpt/protocol.md` §§1, 3–6 and `CONTRIBUTING.md`.
**Status:** this is an AI model review, not my GitHub approval. **G0 remains pending.** No real weather-transfer results exist or are claimed.

## Summary

I found **no must-fix correctness bugs** in the core estimands. Greedy score-prefix matching, candidate-ID and annotation-ID tie handling, matching eligible GT before applying ignore regions, explicit native-category and ignore modes, whole-tie selection of the highest observed boundary, the INFEASIBLE/UNDEFINED states, both target-gap decompositions and the signed held-out loss identity all agree with the protocol. The simple binary TP-ECE is named honestly and is not presented as LaECE or OCE. Strict JSON input and output works as documented.

The main gaps are safeguards that matter when the first real caches arrive. In `held_out` mode the CLI accepts (S1) missing inference coverage, (S2) inconsistent or censoring candidate pipelines across roles, and (S3) aliased dataset identities, and in all three cases it still reports `DECLARED_HELD_OUT`. The note says that pipeline identity needs an external audit, so S2 is disclosed. S1 and S3 are not visible in the role-validation status. I recommend fixing them, or turning them into explicit role-level limitations, before the evaluator is run on real caches. None of them blocks integration as a contract-level reference implementation.

```text
roles ─► validate_documents ─► ReferenceEvaluator (labels fixed once, score-prefix stable)
                                   │
source_selection ── select_threshold(ρ) ─► t* | INFEASIBLE | UNDEFINED
                                   │
clear_test / target_test ── operating_point(t*) + ceiling ─► gaps, L decomposition
_role_policy: image/group overlap ✔   coverage ✘(S1)   pipeline identity ✘(S2)   dataset alias ✘(S3)
```

## Findings

Severity: **must-fix** = wrong result on valid input. **Should-fix** = a missing safeguard that can silently mislabel a real evaluation. **Low** = minor or cosmetic. Repro commands use `PYTHONPATH=src` and import `tests/test_*` helpers.

| ID | Severity | Path | Issue |
|---|---|---|---|
| S1 | should-fix | `metrics.py:239-241`, `evaluate.py:70-90` | `held_out` accepts predictions without `evaluated_image_ids`. An image that was never inferred counts as zero detections, and its FP and recall effects disappear silently. The limitation is listed only under `populations[role].limitations`, while `role_validation.status` stays `DECLARED_HELD_OUT`. |
| S2 | should-fix | `evaluate.py:93-121` | Prediction provenance is copied but never compared across roles. Repro: example() from `test_evaluate`; set the source prediction provenance to `{"candidate_policy":"floor=0.001","model":"A"}` and the target to `{"candidate_policy":"floor=0.85","model":"B"}`. The run returns `DECLARED_HELD_OUT` with target recall 0.25 and no flag. If t* falls below the candidate floor of a test cache, both the operating point and the candidate ceiling are censored without any warning. Suggestion: in `held_out` mode, require an identical declared pipeline identity (checkpoint hash and candidate policy) in every role. When a numeric floor or cap is declared, check `t* ≥ floor` and emit a `CENSORED` status or limitation otherwise. |
| S3 | should-fix | `evaluate.py:50-56,62` | When `provenance.dataset` is absent, `dataset_id` comes only from the caller. Repro: remove `provenance.dataset`, copy the `source_selection` documents into `clear_test`, and declare `dataset_id:"Synthetic"` with `group_namespace:"other"`. The run is accepted as `DECLARED_HELD_OUT` with fully identical images. Suggestion: require `provenance.dataset` in `held_out` mode, and/or also check overlap of non-null `file_name` values. |
| L1 | low | `metrics.py:321-323` | The headroom flag uses floating-point subtraction. With 41/50 recall and ρ = 0.80, H is mathematically 0.02, but the computed value is 0.019999999999999907, which is flagged `LOW_HEADROOM`. The protocol defines LOW as `0 ≤ H < 0.02`. Compare with a small tolerance or with exact rationals (`Fraction(tp, gt)` against the decimal target). The FEASIBLE/INFEASIBLE decision itself is consistent: `a ≥ b ⇒ a − b ≥ 0` in IEEE arithmetic. |
| L2 | low | `metrics.py:226-265`, tooling note line 29 | Several categories are pooled with a single cross-class threshold but matched within each category. That combination is neither the primary pedestrian task nor the protocol's merged-human panel (one human match per instance). The merged-human panel needs the adapter to relabel GT and predictions explicitly to one category, with provenance. The note should say this so that a pooled multi-category run is not mistaken for that panel. |
| L3 | low | `evaluate.py:157-168`, `schema.py:57-64` | Deeply nested JSON (`[`×100000) raises `RecursionError`, which escapes the CLI's JSON error contract. Each file is also read twice: once to parse and once to hash. Hashing the parsed bytes would remove the time-of-check/time-of-use gap. |
| L4 | low | `metrics.py:308`, `evaluate.py:113-136` | Every operating point embeds every retained per-candidate row. Up to eight row lists are emitted: the selection ceiling and selected point, plus a ceiling and an operating point per role. A real permissive-floor cache could produce output of many gigabytes. Consider an option to omit `matches` or write them to a separate file. |
| L5 | low | `evaluate.py:78-80` | `paired` allows the very same `(dataset, image_id)` in both `clear_test` and `target_test`. Paired should probably mean shared groups with disjoint images. |
| L6 | info | `metrics.py:258-261` | The `reject` policy fails on ignore or crowd annotations in categories that are not selected. This is conservative and fails loudly. Document it. |

No must-fix items were identified.

## Points verified as correct

- **Prefix stability.** A candidate's label depends only on candidates that come earlier in the `(−score, candidate_id)` order, so recall is nondecreasing over score prefixes. The duplicate-to-ignore path (an eligible GT that is already matched, followed by an IoA region) behaves as specified. IoU ≥ 0.5 implies IoA ≥ 0.5, so the two rules do not conflict.
- **Selection.** The first tie group whose cumulative recall reaches ρ must contain a TP, so the threshold is the highest feasible observed boundary. `-0.0` and `0.0` group together correctly. INFEASIBLE agrees with the end of the loop.
- **Decompositions.** Checked algebraically: `S = U + V`, `D = U + T` with T signed, and `L = (M_clear − M_c) + (W_c − W_clear)`. Undefined values propagate as null with an explicit status.
- **Geometry.** Nonfinite values, overflowing extents and areas, and underflowing (subnormal-product) boxes are rejected. A box with a 1.3e154 extent still produces a finite IoU. Bounds are not clipped. Conversions from `xyxy` can make `x+w` exceed `x2` by one ulp in about 0.75% of random two-decimal boxes. That only matters when `x2` equals the image width exactly, and it then fails loudly. Edge-touching boxes at W = 1280 never triggered it (0 of 20,000).
- **ECE bins.** No `k/b` score landed outside its reported `[lower, upper)` for b ∈ {10, 15, 30}.
- **Monotone invariance** holds for maps that remain strictly increasing in floating point. A map that underflows (s⁸ near 1e-60) merges ties, which matches the saturation caveat the protocol already gives.
- **Leakage checks.** Selection/test image and group overlap is rejected in both modes. The CLI refuses to overwrite inputs. Output is strict JSON. An unwritable output path exits with code 2.

## Explicit pending limitations (not findings)

Not yet implemented or established, and correctly listed as pending: official AP, full OCE, published LaECE, bootstrap and its coverage, the IoU 0.75 sensitivity, percentage-point reporting, any official KITTI or BDD ignore policy, and integration with real adapter output. G0's empirical prerequisites are unmet.

## Checks actually run

- `PYTHONPATH=src C:/Users/Advait/det-eval-2d/.venv/Scripts/python.exe -m unittest discover -s tests` on Python 3.12.14: 25 tests, OK. The parent separately reported a passing Python 3.11 run.
- An untracked adversarial script (in the Claude session scratchpad) covering the headroom boundary, ECE bin edges, `xyxy` conversion rounding, `reject` scope, the S1/S2/S3 repros, paired identical images, extreme geometry, deep-nesting and missing-directory CLI errors, output size, and an underflowing monotone map. All results are synthetic.
- Read-only inspection of the sibling `det-eval-2d/src/det_eval/metrics.py` confirmed that KITTI neighbour and difficulty ignores there are one-to-one IoU-matched, which differs from the reusable IoA regions used here. The tooling note already states this.
- No real cache, dataset, training, package install, download, push, PR or merge was performed. The live Claude adapter task was not contacted.

## Publication recommendation

**Integrate as the contract-level reference evaluator.** No must-fix correctness items were found. The parent should fix S1–S3 directly, or record them as explicit role-level limitations, before any real-cache held-out run. L1–L6 are optional small fixes. A replacement review is not needed for these minor fixes. **G0 remains pending.**
