# Methodology objections (Claude audit, Phase 0)

**Claude audit**, 2026-11-03. Prepared independently in commit `4af4f810f36851b462298a9b473dd421f30e6ba3`, then **peer-revised** after Claude reviewed GPT's response commit `80519fcee2c99d134a5a6a89559f743772c2ffb8` ([discussion record](discussion_with_gpt.md)). Each objection says what is wrong with the current `RESEARCH_PLAN.md` protocol, what evidence supports it, and a concrete fix. Where the peer revision changed a position, a short **Revision** note records the initial wording and why it changed.

Labels:
- **[B]** blocks gate G0 until resolved.
- **[M]** must be fixed before the affected RQ runs.
- **[A]** advisory.

No dataset was downloaded and nothing was run, so every count or effect below is either a quoted source value or explicitly hypothetical. Toy numerical checks validate algebra only.

---

## O1 [B]: ACDC labels: use the official instance annotations, not semantic masks, and keep invalid, void and crowd distinct

**Evidence (ACDC v5 §3.3–3.5):**
- Instance annotations were produced by "convert[ing] the pixel-level semantic masks to polygon representations", after which annotators "merge/split polygons to form polygon annotation for each instance", exported "to standard COCO format".
- Adverse-image annotation has two stages. Pixels that cannot be "unquestionably assigned" in stage 1 are revisited in stage 2 using the normal-condition reference and the source video. The binary **invalid mask** marks pixels whose label changed between stages: they carry **legitimate labels** and are used in evaluation. About 7.5% of pixels remain **unlabeled (void)** even after stage 2.
- Cityscapes, whose classes ACDC inherits, labels indistinct crowds as a *group* rather than as instances.

**Problems:**
1. Deriving boxes from connected components of the **semantic** mask merges touching pedestrians and splits occluded ones. Only the official instance IDs or polygons are acceptable.
2. **Label-coverage bias has no established direction.** Two mechanisms pull in opposite directions: residual void could hide the hardest pedestrians (recall on labelled objects biased upward, real-but-unlabelled people inflating FPPI), while stage-2 labels assigned with privileged reference/video information could include people barely discernible in the single adverse frame (recall biased downward). Neither magnitude is measured. Penquitt et al. find missing annotations of small and occluded objects to be the dominant label error across four other datasets; that motivates, but does not demonstrate, the first mechanism here.
3. Mask-derived boxes are modal (visible extent). Whether BDD100K boxes follow the same convention is **unverified**.
4. Public ACDC annotations cover only train and val: 400 + 100 images per condition (night: 106 val). Test labels are withheld.

**Fix:**
- Use the official COCO-format instance JSON (and its `bbox` field if verified).
- Treat crowd/group regions and residual void as **proposed** ignore regions (a prediction mostly inside one is neither TP nor FP), pending inspection of the actual JSON and evaluator. **Do not treat the invalid mask as ignore.** Instead report a sensitivity stratum: GT pedestrians by the fraction of their instance pixels marked invalid.
- Visual audit of a stratified sample (tiny, occluded, uncertain people) per condition, drawn from non-test groups; log void overlap per prediction and report "FPs overlapping void" separately.
- Preserve ACDC's geographic split: train only for the target-adaptation arm, val as the held-out test.

**Revision.** The initial O1 grouped "group or crowd regions and void pixels" without mentioning the invalid mask, and asserted an upward recall bias. GPT pointed out that invalid regions carry legitimate labels; the ACDC text confirms it, and it also supplies the opposing mechanism above.

## O2 [B]: Class-policy mismatch across COCO, BDD100K and ACDC/Cityscapes

**Evidence:**
- Cityscapes `person` covers humans who primarily rely on their legs, including people pushing a bicycle; `rider` covers humans on any device (bicycles, motorcycles, scooters, skateboards, horses, Segways, skates, wheelchairs).
- BDD100K pinned `configs/det.toml`: separate `pedestrian` and `rider`; a `crowd` attribute; `ignored_mapping: "other person" = "pedestrian"`.
- COCO has a single `person` category; a cyclist is a COCO `person` (category-list level; the COCO guidelines were not read).
- 2611.00071 uses one merged `person` class and does not state its ACDC `rider` mapping.

**Problem:** a single policy cannot serve both a BDD-fine-tuned detector that distinguishes pedestrian from rider and a COCO zero-shot detector that cannot.

**Fix (revised):** two separately defined tasks.
- **Primary task: BDD-fine-tuned pedestrian detection.** Rider remains a separately supervised class outside the primary denominator. A pedestrian-labelled detection on an eligible rider is a pedestrian FP. Add a **class-confusion diagnostic**: the fraction of missed pedestrian GT that a rider-labelled output would have matched. Without it, a night increase in pedestrian/rider confusion is indistinguishable from detection failure.
- **Merged-human panels (secondary): zero-shot COCO `person`, and explicitly merged pedestrian/rider outputs of a fine-tuned detector.** GT is pedestrian ∪ rider, one match per human, bike/motorcycle boxes excluded. Each panel has its own source-selection threshold and denominator. Never score pedestrian-only outputs as a union detector, and never compare losses across these denominators as one task.
- **ACDC for the primary task** maps ACDC `person` to pedestrian, with the Cityscapes/BDD definition difference recorded as a limitation; the merged-human ACDC panel is separate.
- BDD `other person` and `crowd` → ignore remains a proposal until the evaluator's handling of `ignored_mapping` is read and annotations are inspected.

**Revision.** The initial O2 made pedestrian ∪ rider the primary class for all headline metrics. Claude now accepts GPT's proposal: the zero-shot mismatch requires a separate merged-human panel, not a redefinition of the fine-tuned primary task. Rider counts are also likely small per ACDC condition, which favours pedestrian as the confirmatory denominator.

## O3 [B for RQ3]: A global strictly increasing recalibration with equivariant threshold reselection cannot change recall transfer

**Claim (derivation; consistent with GPT protocol §5).** Let `g` be **one** strictly increasing scalar map applied to every candidate score in every image and condition. Assume boxes, labels, IoU/suppression geometry and deterministic tie IDs are fixed, every numerical cutoff is transformed with the scores (`floor → g(floor)`), and the threshold selector is **equivariant**: it chooses among observed source score boundaries with the same inclusion rule, e.g. `t* = max{observed source-selection score t : R̂_S(t) ≥ ρ}` with whole tied groups. Then `t′* = g(t*)` and on every image, source or target,

`{d : g(s_d) ≥ g(t*)} = {d : s_d ≥ t*}`.

Recall, FPPI and every set-based quantity are exactly unchanged; only probability-sensitive calibration metrics change.

**This holds even when `g` is applied before rank-based steps.** Score-ranked top-k, greedy hard NMS (class-aware or agnostic, by induction on the highest remaining candidate) and greedy score-ordered GT matching depend only on score order, which `g` preserves.

**Equivariant selection is a required assumption, not a detail.** With two source GT at TP scores 0.8 and 0.4 and ρ = 0.5, every threshold in (0.4, 0.8] selects the same source set. A midpoint rule gives t = 0.6 and accepts a target score of 0.62; after `g(s) = s²` the midpoint is 0.40 and 0.62² = 0.3844 is rejected. Identical source subsets do not imply identical target subsets.

**Genuine exceptions** (each changes information or ranking, and needs its own baseline):
- **Classwise maps with a pooled or cross-class selector**, including cross-class top-k (DETR query × class top-300): different maps change cross-class order.
- **Multiclass logit transforms** (softmax temperature) are not a scalar map of the max score and can reorder or relabel.
- **Non-strict maps**: isotonic regression can **merge distinct score groups** into plateaus, removing attainable source subsets and changing recall/FPPI by overshoot — not merely resolving existing ties. Rounding and floating-point saturation do the same.
- **Fixed numerical cutoffs not transformed** with the scores; score-modifying steps (soft-NMS, weighted box fusion).
- **Condition-dependent maps** (Mondrian): equivalent to per-condition thresholds; need labelled target data or a runtime condition estimate. A condition classifier supplies context, not calibration labels.
- **A fixed probability cutoff** (e.g. "trust p ≥ 0.5") that is not reselected: calibration quality then directly sets realized recall.

**Fix:** state the theorem with these assumptions in the protocol and add a unit test (strict maps, ties, upstream top-k/NMS, midpoint counterexample). RQ3 keeps (a) the strict-map invariance control, (b) a fixed-probability consumer arm with a cutoff fixed in advance, and (c) optional classwise/context arms with an identity-map threshold baseline. Target-labelled condition calibration is an **adaptation** arm with disjoint target fit/selection/test groups and a raw-score target-selected threshold baseline. No RQ3 recall improvement is claimed in advance.

**Revision.** The initial O3 required `g` to be applied "after all set-forming steps" and listed "calibration before cross-class top-k or class-agnostic NMS" as an exception. That was wrong for a single global map: rank-based operations are invariant. The true mechanism is classwise or vector-valued maps. It also said isotonic differences come "from tie-breaking"; plateaus merge distinct scores. And it omitted the equivariant-selector assumption, without which strict monotonicity is insufficient.

## O4 [B]: Preregister feasibility, headroom and the gap decompositions separately

**Problems:**
1. A target-recall threshold exists only if the candidate-ceiling recall `M` (all retained candidates under the frozen floor, caps, NMS/top-k) reaches ρ. `M` is limited by output caps (YOLO `max_det`, 300 queries for RT-DETR/D-FINE/DEIM/YOLO26 one-to-one), NMS suppression of adjacent people, and small objects after resizing (BDD 1280×720, ACDC 1920×1080 → 640 px). No inspected source reports `M` for these models on BDD pedestrians. It is unknown.
2. Under shift, `M_c` can fall below ρ, so an oracle target threshold need not exist.
3. Different quantities have been conflated: infeasibility, low headroom, positive shortfall, signed gap, and held-out clear-to-condition loss.

**Fix (revised):**
- **Targets:** primary ρ = 0.90; sensitivities 0.80 and 0.95, fixed before data inspection.
- **Feasibility on source-selection groups:** **INFEASIBLE** iff `M_S < ρ`; **UNDEFINED** if there is no eligible GT; headroom `H_S = M_S − ρ`, with `0 ≤ H_S < 0.02` flagged **LOW_HEADROOM** as a descriptive flag only. A model with `M_S = 0.91` can attain 0.90. Every model-target pair is retained; report bootstrap feasibility frequency.
- **Gap decompositions** (with `r_c ≤ M_c`, which holds because greedy score-ordered matching gives nondecreasing recall over score prefixes):
  - positive shortfall `S_c = (ρ − r_c)+ = U_c + V_c`, `U_c = (ρ − M_c)+`, `V_c = (min(ρ, M_c) − r_c)+`;
  - signed gap `D_c = ρ − r_c = U_c + T_c`, `T_c = min(ρ, M_c) − r_c` (negative when the target is exceeded). Example: ρ = 0.90, M = 0.95, r = 0.93 gives S = U = V = 0 but D = T = −0.03.
- **Held-out loss**, the quantity the research question is actually about, is `L_c = r_clear − r_c` with `r_clear` from the **independent clear test**, not the selection recall. It has an exact signed decomposition **(Claude proposal)**: with threshold-removable misses `W = M − r`,

  `L_c = (M_clear − M_c) + (W_c − W_clear)`,

  i.e. candidate-ceiling loss plus the increase in misses a lower threshold could recover. Neither `V_c` nor `T_c` alone is "threshold-transfer loss": on the clear test they are already nonzero from selection noise, so condition effects are contrasts against the clear test.
- Report recall granularity (1/n_GT) and group-level intervals.

**Revision.** The initial O4 called `R_max < R* + 0.02` "infeasible" (a margin rule, not infeasibility), labelled `T_c` the threshold-transfer component without noting it goes negative, and had no positive-part version. The coordinator agenda and GPT both flagged this; Claude accepts their corrections and adds the exact `L` decomposition above.

## O5 [B for RQ2]: Separate three information regimes; the initial panel supports description only

**Problems:**
1. **Pseudoreplication.** Model × condition cells are not independent; condition severity dominates pooled rankings; a single seed per model hides training variance. The effective unit for "which metric predicts which model loses more" is the model, of which there are 3–4.
2. **Circularity.** Target-labelled mAP, LaECE and especially OCE are computed on the same labels as recall loss. OCE assigns Brier = 1 to every missed GT (Park et al., Def. 1), so it mechanically shares information with recall; it also ignores FPs overlapping no GT, so FPPI stays necessary.

**Fix (revised; adopts GPT's three-regime split):**
- **RQ2a source-only:** raw TP-ECE (15 equal-width bins, primary matching, operating set at the source-selected t*) on source **calibrator-fit** groups, before fitting any map; fitted-map ECE only on independent groups or out-of-fold. It forecasts model vulnerability for a named contrast, not which condition will occur.
- **RQ2a-U unlabelled-target:** drop in mean per-image maximum permissive task-candidate score (empty output = 0) relative to the source baseline. It consumes target images, so it is not source-only; it is sensitive to scene prevalence and cannot count unseen people. ATC is a classification analogy, not a detector-recall estimator.
- **RQ2b target-labelled diagnostics:** ECE/LaECE₀/OCE/AP/oracle thresholds explain results; they never support advance warning.
- With the initial few models every association is **descriptive**. Predictive validation, if ever claimed, holds out whole models and whole conditions with a frozen predictor and fitting rule. Mixed models, bootstrap replicas, or seeds of two models do not manufacture independent architectures; permutation tests need defensible exchangeability.
- **Leakage guard (Claude addition):** every choice that tunes the pipeline or the analysis — candidate floor/cap audit, stratified visual audit, pilot precision estimate, statistic definitions — uses development or calibrator-fit groups, never held-out test groups.

**Revision.** The initial O5 placed source-calibration and unlabelled-target predictors together as "label-free", and suggested mixed models, exact permutation p-values and two seeds as if they made RQ2 inferential. Claude accepts GPT's narrower position.

## O6 [M]: Dataset shift is confounded with condition shift

**Problem:** BDD clear-day → ACDC adverse changes camera, resolution, country, annotation protocol and class policy as well as condition. 2611.00071 has the same confound.

**Fix (revised):** use ACDC's annotated normal-condition references, restricted to the **annotated correspondence subset**: only about half of adverse train/val views have an annotated reference (800 train / 203 val public). Compare BDD-clear-test → ACDC-reference (dataset shift) and ACDC-reference → ACDC-adverse (condition shift) on the same views with the same eligibility and declared weights. Report the all-adverse panel separately; never subtract it from the matched subset. Correspondence is GPS-matched scene/route level, not pixel alignment and not pedestrian identity — the people present differ between the two drives — so the contrast is a descriptive association, not a causal weather effect. JSON availability and correspondence files are a G0 prerequisite.

## O7 [M]: Architectural attribution; YOLO26 offers a reduced-confounding head/pipeline contrast, conditionally

**Problems:**
- Cross-family models differ in backbone, recipe, augmentation, epochs and code base; differences between a handful of them are system comparisons.
- YOLO26 trains one-to-many and one-to-one heads on one trunk. The official report calls one-to-one the default; current docs say predict/val default to one-to-many and require `nms=False` for one-to-one.
- **Branch availability is unverified.** In the pinned Ultralytics `head.py` (commit `73c60b7`), `Detect.fuse()` sets the unused branch to `None`, so a fused or exported artifact may hold only one head. The same file detaches the trunk features fed to the one-to-one head during training ("detach keeps one2one out of the backbone"), so in that code the trunk is shaped by the one-to-many objective. Whether the released checkpoints were trained with this code is unknown.

**Fix (revised):** pin the `ultralytics` version; inspect checkpoint keys **before** any fusion; load separate copies for each branch; log resolved head, `nms`/`end2end`, floor, cap and predict/val settings. Call the result a **same-checkpoint head/pipeline contrast**: the shared trunk and recipe reduce confounding, but head weights, assignment history, candidate cardinality and postprocessing change together. It isolates neither NMS nor assignment. If both branches are not present, report the contrast as unavailable rather than substituting separately trained checkpoints. Prefer seeds for the small panel over adding families.

**Revision.** The initial O7 and novelty audit said this contrast "isolates the head and assignment". That overstated it; Claude accepts GPT's wording and adds the detach observation.

## O8 [M]: Thresholded-ECE pitfalls and metric configuration

- Park et al. show D-ECE is minimized as the threshold approaches 1, so ECE at a low high-recall t* and at 0.3 measure different things.
- Preregister bin count, matching rule (one-to-one, greedy by score), duplicate handling and the detection set for every calibration metric.
- RQ0: add an all-outputs, non-one-to-one correctness variant as a **literal-rule proxy** for 2611.00071's stated rule ("class match and IoU > 0.5"). It is not a verified reconstruction of that paper's implementation. Cross the candidate-set choice with the matching rule on fixed weights and images, and keep `IoU > 0.50` (source) and `IoU ≥ 0.50` (primary) distinct. The duplicate-query hypothesis is untested until this controlled audit runs; modern models alone cannot reproduce original-DETR results.

## O9 [A]: Further notes

- **BDD slices.** `timeofday`/`weather` tags are reportedly noisy (plan; unverified). 2611.00071 reports a labelled "Clear (Test)" split of 3,563 images; maintainers said test labels would not be published, so the protocol reserves held-out groups from accessible labels and record the archive version.
- **Box-size bins** on the network-input scale or as a fraction of image height, frozen before test inspection.
- **Threshold rule comparator.** A source-selection F1-optimal frozen threshold, alongside target recall, allows comparison with AegisBench's framing without implying identical data or pipelines.
- **Boundary choice (Claude note).** The max-observed-boundary rule is equivariant but, among thresholds selecting the same source set, the most recall-pessimistic on target data. With dense candidate scores the effect should be small; record the gap to the next lower observed score as a diagnostic.
