# Next-step brainstorms after the local RT-DETR run (2026-11-27)

Two independent, read-only tasks were launched in parallel by the Claude coordinator with the same brief
(results, settings check, resources). They did not coordinate. Both corrected one claim in the brief:
it said most RT-DETR night loss is candidate ceiling, which holds for the difference split only and is
not shared with YOLO11s. Their final messages are recorded verbatim below.
The decision is in [the plan](../research/2026-11-27_rtdetr_interpretation_next_steps.md).

## GPT Sol (gpt-6.1-sol)

> The results support a narrow conclusion: clear-day threshold transfer loses night recall in both trained systems, and changing the final threshold cannot recover every missed pedestrian. They do **not** jointly establish that most loss comes from the candidate ceiling. YOLO11s' threshold component exceeds its ceiling component at source FPPI 1 and is roughly comparable at recall 0.80. RT-DETR's ceiling component dominates at FPPI 1.
>
> Two wording corrections matter. "No matched candidate" includes localization, classification and candidate-selection failures; "never proposed" implies more than measured. RT-DETR's 0.036 component is the **difference** in threshold-removable misses between conditions, whereas its absolute night threshold-removable share is about 0.228.
>
> The strongest validity threats are short RT-DETR training, one RT-DETR seed, different training recipes and resolutions across systems, image-bootstrap intervals excluding route and training variation, condition differences in pedestrian size and scene composition, and adaptation combining night content with previously unseen images. The adaptation result establishes a conditional FPPI reduction; recall improvement remains unresolved. Repeated test inspection makes subsequent hypotheses exploratory. G0 remains pending.
>
> Candidate next steps:
>
> - **Cached-output ceiling audit:** distinguish native top-k competition, class scoring and localization, then standardize condition comparisons by pedestrian height. **0 GPU hours**; high explanatory value. Risk: overlapping diagnostics can be mistaken for causal explanations.
> - **Independent RT-DETR seed:** repeat baseline plus matched continuations. Approximately **9.5 GPU hours before inference**, using observed timings. Tests repeatability; likely exceeds one overnight window without verified throughput improvement.
> - **Longer source-only training:** add 15 epochs to the baseline, approximately **6 GPU hours plus inference** at observed throughput. Tests sensitivity to training duration. Risk: the existing augmentation shutdown makes this an additional-training intervention, not a faithful uninterrupted longer recipe.
> - **Matched novelty control:** compare equally sized unseen-day and unseen-night continuations, if unused clear-day data exist. Roughly **1.6 GPU hours plus inference** for two five-epoch arms. Separates novelty from condition exposure; feasibility and independence remain unverified.
>
> **I recommend the cached-output audit before another training run.** RT-DETR already retains raw query logits and boxes, so the central "detector versus threshold" interpretation can be sharpened without inference.
>
> Freeze this specification before execution: arms = existing baseline, day control and adaptation; training seed 0, zero new epochs, CPU workers 0. Primary population unchanged (selection, clear-day test, night test; existing evaluator, eligibility and source-FPPI-1 policy). Candidate diagnostics: native top-300; pedestrian scores from all saved queries at the same floor; class-agnostic query geometry as an explicitly diagnostic upper bound; IoU 0.50 primary and 0.30 sensitivity. Height bins: existing five bins; standardize night to clear-day eligible-object proportions where support exists; keep FPPI on its original image population. Bootstrap: 1,000 paired image replicates, seed 20261127, source-threshold reselection. Completion criteria: reproduce native aggregates, report each diagnostic's ceiling change and residual condition gap, preserve null results; missing caches, reproduction failure or unsupported strata are explicit failures; no replacement training.
>
> Budget: zero GPU hours, maximum nine elapsed hours. Future GPU work remains on Colab under the supplied project instruction.

## Claude Opus (claude-opus-5-5, high effort)

> **Correction to the brief:** "most night loss is candidate ceiling" holds only for the *difference* decomposition. In absolute terms more night pedestrians are threshold-removable than have no candidate.
>
> **Interpretation.** Night is the only condition with a clear loss; both parts of the night loss are positive. At the transferred threshold night FPPI is lower than clear day (RT-DETR 0.65 vs 1.09; YOLO B 2.37 vs 4.53): night scores are pushed down for true and false detections alike. The dominant component is not shared: RT-DETR 0.062 ceiling / 0.036 threshold; YOLO at clear-day FPPI 1 had a threshold part as large or larger (A 0.088/0.081, C 0.062/0.109, B 0.067/0.110). RT-DETR night absolute: 0.180 no candidate, 0.228 threshold-removable. New aggregate check (point estimates): the night ceiling gap is not size-driven; it appears within height bins (32–64 px 0.847 vs 0.901; 64–128 px 0.912 vs 0.976), and night has proportionally more tall pedestrians; reweighting night to the clear-day height mix gives a ceiling ≈ 0.803 (gap ≈ 0.079). The night-mixed continuation lowers night FPPI with no recall change: a ranking change, not a ceiling lift (0.816 → 0.835 without interval).
>
> **Threats:** one seed (YOLO seed changes moved the split by ~0.03, the size of RT-DETR's whole threshold part); under-training (20 of 120 epochs, selection ceiling 0.864); novelty confound in the adaptation arm; night label noise; bootstrap ignores route clustering; IoU 0.3 / class-agnostic sensitivity not yet run for RT-DETR.
>
> **Candidates:** (A) CPU re-analysis of retained candidates (IoU 0.3, class-agnostic, height-standardized ceiling with intervals, in-box brightness test), 0 GPU h, low risk. (B) Second RT-DETR baseline seed, ~4–5 h with data loading fixed or 7.9 h without; Windows worker risk. (C) Continuation replicate with a novel-day control × seeds {1, 2}, ~7–8 h. (D) Longer baseline (40–60 epochs), 10–24 h. (E) RT-DETR on NightOwls v2, ~1–2 GPU h, R3 dominates.
>
> **Recommendation: B tonight, A during the day.** Frozen: one baseline arm, exact config with seed=1, 20 epochs, batch 16, constant LR 1e-4, aug stop 17, EMA warmups 2000, final EMA; num_workers=4 persistent. Abort/fallback: if the median of the first 200 steps exceeds 1.6 s or the loader errors, rerun with num_workers=0 only if projected ≤ 9 h, else run C as the pre-declared substitute; after epoch 2, stop if projected > 9 h, record failure, no partial checkpoint. Success: 20 epochs, ≥ 99.5% successful updates, full evaluation saved. Readout: "split reproduced" if both components' intervals exclude 0 and ceiling still exceeds threshold; "seed-sensitive" if either moves ≥ 0.03 or the order flips, then drop the RT-DETR dominance claim; selection ceiling < 0.85 is further under-training evidence. The height-standardized and timing figures are estimates, not measured results.
