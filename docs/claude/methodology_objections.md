# Methodology objections (Claude audit, Phase 0)

**Claude audit**, 2026-11-03. Each objection says what is wrong with the current `RESEARCH_PLAN.md` protocol, what evidence supports it, and a concrete fix. Labels:
- **[B]** blocks gate G0 until resolved.
- **[M]** must be fixed before the affected RQ runs.
- **[A]** advisory.

No dataset was downloaded and nothing was run, so every count or effect below is either a quoted source value or explicitly hypothetical.

---

## O1 [B]: ACDC labels: use the official instance annotations, not semantic masks, and audit what the derivation omits

**Evidence (ACDC v5 §3.3, §3.5):**
- ACDC instance annotations were produced by "convert[ing] the pixel-level semantic masks to polygon representations", after which annotators "merge/split polygons to form polygon annotation for each instance", exported "to standard COCO format".
- Semantic annotators "were asked to be conservative", and pixels that "cannot be unquestionably assigned to a single semantic class are left unlabeled".
- Cityscapes, whose classes ACDC inherits, labels indistinct crowds as a *group* rather than as instances.

**Problems:**
1. Deriving boxes from connected components of the **semantic** mask is wrong. It merges touching pedestrians into one box and splits a pedestrian occluded by a pole into two. The plan's wording ("derive boxes from instance masks") is correct only if the official instance IDs or polygons are used.
2. Conservative labelling at night means the darkest, most ambiguous pedestrians are plausibly left void. Those are exactly the objects a recall-loss study cares about. Recall measured on the remaining labelled objects is then **biased upward** for adverse conditions, while unlabelled-but-real pedestrians inflate FPPI. This is a hypothesis, not a measured effect, but Penquitt et al. found that missing annotations of small and occluded objects are the dominant label error across four datasets.
3. Mask-derived boxes are modal (visible extent). Whether BDD100K boxes follow the same convention is **unverified** (the BDD docs were unreachable).
4. Public ACDC annotations cover only train and val: 400 + 100 images per condition (night: 106 val). Test labels are withheld. Every ACDC number in my project therefore comes from at most about 500 images per condition.

**Fix:**
- Use the official COCO-format instance JSON (and its `bbox` field if present).
- Treat group or crowd regions and void pixels as **ignore regions**: a prediction falling mostly inside one is neither a TP nor an FP.
- Run a visual audit of at least 100 images per condition, plus a log of how much void area each prediction overlaps.
- Report "FPs overlapping void" separately.
- Preserve ACDC's geographic split: use **train** as the only place condition-specific calibration may be fitted, and **val** as the held-out test.

## O2 [B]: Class-policy mismatch across COCO, BDD100K and ACDC/Cityscapes

**Evidence:**
- Cityscapes `person` = "All humans that would primarily rely on their legs to move… includes… people pushing a bicycle". Cityscapes `rider` = "Humans relying on some device for movement… bicycles, motorcycles, scooters, skateboards, horses, Segways, (inline) skates, wheelchairs" (Cityscapes paper, class definitions).
- BDD100K official configuration (`configs/det.toml`): separate `pedestrian` and `rider`; a `crowd` attribute; `ignored_mapping: "other person" = "pedestrian"`.
- COCO has a single `person` category and no rider category, so a cyclist is a COCO `person` (category-list level only; the COCO guidelines were not read).
- 2611.00071 trains and evaluates one merged `person` class and does not say how ACDC `rider` was mapped.

**Problems:**
1. In zero-shot Stage A, a COCO `person` prediction on a cyclist is a correct detection that would be scored as an FP plus a missed `rider` if classes are kept separate.
2. "Rider" covers a much wider set under Cityscapes (wheelchairs, skateboards) than a casual reading of BDD suggests. The BDD definition itself remains unverified.
3. KITTI `Cyclist` box extent is unverified.

**Fix:** preregister **one primary VRU-human class = pedestrian ∪ rider**, matched class-agnostically within the human group, for all recall and FPPI headline metrics. Keep per-class results as secondary diagnostics. Map:
- BDD `other person` and `crowd` to ignore;
- ACDC `rider` to VRU-human;
- COCO `person` to VRU-human.

Bicycles and motorcycles stay out of the VRU recall denominator unless a separate "vehicle-of-VRU" analysis is added. Document the remaining policy differences rather than claim equivalence.

## O3 [B for RQ3]: A global monotone recalibration combined with a recall-retuned threshold cannot change recall transfer

**Claim (derivation, not a source quote):** let `g` be strictly increasing and applied to the scores after all set-forming steps (NMS, top-k). Let τ\* be chosen on the clear-day split C so that Recall_C ≥ R\*.
- Because {s ≥ τ} = {g(s) ≥ g(τ)}, recall on C as a function of a calibrated threshold τ′ equals Recall_C(g⁻¹(τ′)).
- The selected calibrated threshold is therefore τ′\* = g(τ\*).
- On every image of every condition, the retained detection set is identical.
- Hence Recall_c, ΔR_c and FPPI_c are **exactly unchanged**. Only calibration metrics (LaECE, OCE) change.

Isotonic regression is only non-decreasing; its flat steps coarsen the attainable thresholds, so any difference comes from tie-breaking, not better transfer. The plan's RQ3 step "re-define the threshold on the calibrated probability… does calibrated-space thresholding transfer better?" is therefore a null by construction for temperature, Platt and global isotonic calibration.

**Cases where recalibration can matter (and should be the actual RQ3):**
- **Per-class calibrators with a pooled VRU threshold.** Pedestrian and rider scores get different maps, so the cross-class ordering changes.
- **Calibration before cross-class top-k or class-agnostic NMS.** This applies to DETR's top-300 over (query × class) and YOLO26's one-to-one top-k.
- **Condition-aware (Mondrian) calibration.** This is equivalent to per-condition thresholds and requires labelled target data (ACDC train) or a runtime condition detector.
- **A fixed probability threshold** (e.g., "trust p ≥ 0.5"), not retuned for recall. This is the realistic downstream-consumer case, where calibration quality directly determines the realised recall.

**Fix:** state the invariance in the protocol. Add a unit test (toy scores, a monotone map, identical retained sets). Restrict the RQ3 recall claims to the four cases above.

## O4 [B]: The 0.90 VRU recall target may be infeasible; preregister the feasibility rule and decompose the loss

**Problems:**
1. A target-recall threshold exists only if the maximum attainable recall R_max(C) at score → 0 is ≥ R\*. R_max is capped by:
   - output caps (YOLO `max_det`, and 300 queries for RT-DETR, D-FINE, DEIM and YOLO26 one-to-one);
   - NMS suppressing adjacent pedestrians;
   - tiny objects at 640 px input. BDD images are 1280×720 and ACDC images 1920×1080, so a 640-px resize shrinks small pedestrians further.

   No source checked here reports R_max for these models on BDD VRUs. It is **unknown, not assumed**.
2. Under shift, R_max,c can fall below R\* even at threshold 0. The plan's "oracle threshold τ_c that achieves R\*" then does not exist.

**Fix:**
- Preregister: compute R_max on the clear calibration split per model; if R_max < R\* + 0.02, mark that (model, R\*) pair **infeasible** and report it as such rather than silently lowering the target.
- Always report R\* ∈ {0.80, 0.90, 0.95} with feasibility flags.
- Decompose the loss on each condition:
  - unrecoverable U_c = max(0, R\* − R_max,c), meaning the detector cannot reach the target at any threshold;
  - threshold-transfer T_c = min(R\*, R_max,c) − Recall_c(τ\*).

  Only T_c is "threshold transfer". The plan's ΔR conflates the two.
- Report recall granularity (1/n_GT) and image-clustered CIs; rider counts per ACDC condition may be small.

## O5 [B for RQ2]: RQ2 is pseudoreplicated and partly circular

**Problems:**
1. **Pseudoreplication.**
   - The 16–20 (model × condition) cells are not independent: each model contributes about 4 cells, and condition severity dominates.
   - A predictor that merely encodes "night is hard" earns a high pooled Kendall τ without ranking *models* at all.
   - An image bootstrap captures test-set noise but not training variance (1 seed per model), so it understates uncertainty for model-level claims.
   - The effective number of independent units for "which metric predicts which model loses more" is the number of models (4–5).
2. **Circularity.** Condition mAP, condition LaECE and especially condition **OCE** need target labels and are computed on the same images as ΔR. OCE assigns Brier = 1 to every missed GT (Park et al., Def. 1), so target-OCE at the operating set mechanically encodes the miss rate: it is ~ΔR, not a predictor of it. Such metrics also cannot "warn in advance", which is the plan's own framing.
3. **OCE blind spot.** OCE averages over GT objects only, so FPs that overlap no GT are invisible to it. Comparing it with FPPI therefore needs a separate FP metric.

**Fix:**
- Split RQ2 into two parts:
  - **RQ2a (advance warning):** predictors computed from clear labelled data plus *unlabelled* target images only (score-distribution shift, mean max-confidence, ATC-style thresholds; Garg et al., ICLR 2022, arXiv 2201.04234).
  - **RQ2b (diagnostic):** target-labelled metrics, explicitly labelled as non-predictive.
- Analyse within condition (models ranked per condition), or use a mixed model with condition fixed effects. Report exact permutation p-values, which are coarse at n = 4–5.
- Use a hierarchical bootstrap over recordings or sequences, then images.
- Add seeds for at least two models before making any model-level claim.

## O6 [M]: Dataset shift is confounded with condition shift

**Problem:** BDD clear-day → ACDC night changes the camera, resolution, city (Switzerland vs the US), annotation protocol and class policy, as well as illumination. 2611.00071 has the same confound.

**Fix:** use ACDC's annotated **normal-condition reference images** (800 train / 203 val; same routes) as a clear anchor. This splits the loss into:
- BDD-val-clear → ACDC-reference (dataset shift);
- ACDC-reference → ACDC-adverse (condition shift).

The correspondences are same-place, different-time, and are not pixel-aligned. Only 50% of the train/val reference images are annotated.

## O7 [M]: Architectural attribution requires a controlled comparison; YOLO26 offers one

**Problems:**
- RT-DETR, D-FINE and DEIM differ from YOLO11 in backbone, recipe, augmentation, epochs and code base. "One-to-one or IoU-aware heads lose more" cannot be inferred from four differently trained models (the charter already forbids this).
- YOLO26 trains a one-to-many and a one-to-one head on one trunk. The official report calls the one-to-one head the default, but the current docs say predict and val default to one-to-many and require `nms=False` for one-to-one.

**Fix:**
- Pin the `ultralytics` version and set `nms` explicitly.
- Evaluate **both YOLO26 heads from the same checkpoint** as the primary head-type contrast. Caveat: the two heads share features trained under Progressive Loss, which decays the one-to-many weight from 0.8 to 0.1, so this isolates the head and assignment, not the whole training regime.
- Treat cross-family DETR comparisons as descriptive.

## O8 [M]: Thresholded-ECE pitfalls and metric configuration

- Park et al. show that D-ECE is minimized as the threshold approaches 1. "Thresholded D-ECE" at τ\* for a high-recall target (where τ\* may be very low) and at 0.3 measure different things.
- Fix: preregister the bin count, the matching rule (one-to-one, greedy by score, as in COCO evaluation), the duplicate handling, and the detection set for every calibration metric.
- Add an explicit **all-outputs, no-matching** ECE variant that mirrors 2611.00071's literal correctness rule. This is the only way RQ0 can test the duplicate-query mechanism proposed in [novelty_audit.md](novelty_audit.md).

## O9 [A]: Further notes

- **BDD slices.** The BDD `timeofday` and `weather` tags are known to be noisy (plan; unverified here). 2611.00071 reports a labelled BDD "Clear (Test)" split of 3,563 images. If BDD test labels are not public, that split must be a re-partition. This is unresolved, and my project should not copy it.
- **Box-size bins.** Define bins on the **network-input** scale or as a fraction of image height, not in raw pixels, because BDD and ACDC resolutions differ.
- **Choice of threshold rule.** AegisBench freezes F1-optimal thresholds. Reporting the F1-optimal rule alongside target-recall thresholds makes my results comparable with it.
