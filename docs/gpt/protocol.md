# GPT proposed protocol: pedestrian threshold transfer

**Status:** independent GPT proposal, 2026-11-03; subject to the later GPT–Claude discussion and my approval. This is a research design, not a record of experiments. **G0 remains pending.** Source identities and access limits are in [source_audit.md](source_audit.md).

## 1. Question, population and estimands

Primary question: for a frozen detector pipeline, how does pedestrian recall on a held-out condition differ from clear-day recall when the operating threshold is selected using only clear-day data?

Primary population: BDD pedestrian annotations under a frozen eligibility policy, evaluated separately in clear daytime, clear night, and sufficiently supported weather×timeofday cells. Rain/night overlap is explicit. ACDC is a separate external-transfer panel, never pooled into BDD “night.” Rider and combined-human results are secondary until annotation policy is demonstrably aligned. Size/occlusion strata are descriptive, with boundaries frozen before test inspection; box height is not metric distance.

For model/checkpoint m, condition c and threshold t, define object-weighted recall

`R_m,c(t) = E_c[TP_i(t)] / E_c[G_i]`, and `F_m,c(t) = E_c[FP_i(t)]` (FPPI),

where G is eligible pedestrian count and the image distribution includes **zero-pedestrian images**. The sample recall is total TP divided by total eligible GT, not mean per-image recall. No eligible GT means recall is undefined. FPPI remains estimable. Freeze population weighting; sequence-average recall is a separately labelled estimand.

Choose target ρ=0.90 as a proposed operating aspiration, with prespecified sensitivity targets 0.70 and 0.80. Define `t*_m = max{observed source-selection pedestrian candidate scores t : Rhat_m,S(t) ≥ ρ}` using `score ≥ t` and whole tied groups. This finite, observed-score convention is essential to §5. An empirical attainment claim is not a population recall guarantee.

Report these distinct quantities, in percentage points where appropriate:

- **Transferred recall:** `R_m,c(t*_m)` and FPPI at exactly the same pipeline and threshold.
- **Transfer loss:** `L_m,c = R_m,clear-test(t*_m) − R_m,c(t*_m)`. This uses an independent clear test reference, not the selection recall forced toward ρ.
- **Target shortfall:** `S_m,c = max(0, ρ − R_m,c(t*_m))`; also report signed `ρ − R` so overachievement remains visible.
- **Candidate ceiling:** recall with every candidate retained under the frozen candidate policy. This is a pipeline ceiling, not detector capacity or Bayes recall.
- **Threshold-removable misses:** candidate-ceiling recall minus transferred recall on the same test slice. This is a diagnostic upper bound on recall recoverable by lowering a threshold, with no implied acceptable FP cost.

Pairwise detector contrasts use the same images and report both absolute target recall and differences in L. Different source baselines can produce misleading loss rankings. If source ρ is unattainable, emit **INFEASIBLE** and the ceiling, without substituting an arbitrary threshold or deleting the model. An all-candidate fallback may be reported separately. Test-slice infeasibility is a result, not grounds to change ρ. Shared lower-target comparisons must be preregistered or explicitly exploratory.

## 2. Data separation and policy alignment

Partition by the largest available independent recording/trip/scene group before fitting anything:

| Partition | Permitted use |
|---|---|
| Source training | Fit detector weights; no evaluation reuse |
| Source development | Recipe/checkpoint selection, model debugging, policy development |
| Source calibration | Fit a prespecified score calibrator and its hyperparameters |
| Source threshold selection | Choose t* and assess empirical feasibility |
| Clear held-out test + shifted held-out tests | One frozen evaluation; no selection |
| Optional target calibration + target threshold selection | Separate adaptation arm; test groups remain disjoint |

Source is **daytime AND clear**. Other weather definitions are sensitivities, never silently mixed into “clear.” The actual group IDs and allocations require accessible labels and counts. If only validation labels are public, reserve partitions from them; do not assume official test-label access. Thin slices may make five-way source splitting wasteful: grouped cross-fitting is an alternative only with an explicit fold-specific training/selection algorithm, not pooling predictions from models that saw their test labels.

Audit class ontology, extent, ignore/crowd rules, truncation, occlusion, minimum size, category aliases and label versions in an annotation manifest. COCO-person→BDD-pedestrian evaluates a mismatched task if riders remain treated as background. For exploratory pretrained models, either evaluate a documented person+rider human union (counting persons once and excluding bike boxes) or construct and manually check an eligibility/ignore policy for rider overlaps. Label this zero-shot panel separately from a BDD-fine-tuned pedestrian task. Do not equate a cyclist-plus-bike box to a rider-only box.

For ACDC, prefer an official detection annotation artifact if available and documented. If deriving boxes, use individual instance IDs, specified inclusive/exclusive coordinates and void/group handling; verify the complete instance extent and manually inspect a stratified sample including tiny, occluded and uncertain people. Compare against official policy before claiming cross-dataset equivalence. Keep corresponding normal/adverse recordings in one group across all partitions. Record counts of images, eligible objects, empty images, ignored objects and independent groups per joint condition and size stratum. Counts are presently unknown.

## 3. Freeze candidate selection and matching

Treat the unit of comparison as **weights + preprocessing + candidate selection + threshold + evaluator**. Record resize/letterbox, original-coordinate boxes, precision, foreground/background convention, class mapping, candidate floor, query count, NMS IoU, class-aware/agnostic behavior, multilabel expansion, top-k ordering, maximum detections and tie ordering. Save stable image/query/box IDs, original scores and sufficient class-score vectors; COCO scalar results alone cannot reproduce full OCE.

Primary deployment panel retains each model's declared inference semantics, with an explicitly permissive candidate floor and frozen caps. Cache candidates before the swept final threshold. For YOLO, use fixed class-aware hard NMS (proposed IoU 0.70) before sweeping; for one-to-one models use the specified branch and selection rule. Do not add NMS to DETRs merely to make box counts equal. Record class filtering **before or after** top-k: pedestrian filtering before a global cap changes the system.

Inspect raw outputs on a small lawful evaluation subset to verify that the floor, maxDet and pre-NMS cap do not censor operating points; expand caps/lower floors in a separate sensitivity panel. Publish the ceiling's dependence on these choices. A shared maxDet number alone does not equalize query-class top-k and dense-box selection. Time-limited NMS must not silently truncate the record. The pinned [Ultralytics selection code](https://github.com/ultralytics/ultralytics/blob/73c60b7edf7b02b90c07157c87d05957fbfdd68f/ultralytics/utils/nms.py) and [RT-DETR top-k](https://github.com/lyuwenyu/RT-DETR/blob/df2a96c8c3a098567a1149bf0248da6efe6d495d/rtdetrv2_pytorch/src/zoo/rtdetr/rtdetr_postprocessor.py) show why these settings matter.

Primary operating-point matching: per image/class, sort descending by score with stable candidate-ID ties; greedily match each retained prediction to the highest-IoU unmatched eligible GT with IoU **≥0.50**, deterministic GT-ID ties. One prediction matches at most one GT and vice versa. Remaining duplicates are FPs. Match eligible GT before applying the documented ignore rule to unmatched predictions (proposed ignore overlap: intersection/prediction area ≥0.50); excluded GT are not FNs. Report IoU 0.75 sensitivity and ordinary AP separately, retaining the official evaluator's matching/ignore settings for AP. Recall is nondecreasing over the cached score prefixes under this primary matching rule. A maximum-cardinality matching is a labelled sensitivity, not a silent evaluator substitution.

## 4. Calibration has a different target from recall

Use two diagnostic populations: permissive cached candidates, and the actual operating subset. Detection ECE uses the binary TP label under §3, with fixed 15 equal-width bins and 10/30-bin sensitivities; report bin counts, empty bins and retained counts. A no-detection set has undefined prediction-conditioned ECE, never perfect calibration by convention. D-ECE/LaECE cannot account for every missing object simply by averaging emitted predictions.

Reproduce the exact published LaECE₀ matching and IoU target separately from IoU≥0.50 binary correctness; do not interchange those names. For OCE, preserve full class scores and its per-object aggregation; report IoU 0.50 and 0.75 components and a declared arithmetic mean. The [pinned implementation](https://github.com/azizanlab/uq-detr/blob/fa2a64fad0e6a3dfbc10c3937bd298aeeac24a9e/src/uq_detr/metrics/oce.py) exposes a scalar-score approximation; never mix it with full-score OCE across families. Include empty-scene FPPI because unrelated FPs are outside OCE's object neighborhoods. Treat OCE as a combined score/coverage diagnostic, not an independent pure-calibration predictor of recall loss.

Use binary-positive-slope Platt or positive-temperature scalar sigmoid scaling for the invariance control. Fit against a named correctness or localization target on source calibration only. A loss trained using quality targets does not prove its score is a probability of binary IoU≥0.50 correctness. Keep identity, monotone calibration, tie-producing isotonic, and any context-aware/rank-changing method as distinct arms.

## 5. Monotone recalibration: theorem and exceptions

**GPT derivation.** Let C(x) be fixed labelled boxes with scalar scores s. Let g be the same strictly increasing function for every candidate, image and condition. Suppose all upstream selection/matching is fixed or rank-equivariant, ties use identical IDs, and threshold search enumerates observed source score boundaries using the same inclusion rule. Then recall-based reselection yields `t'* = g(t*)` and, on **every** source or target image,

`{d in C(x): g(s_d) ≥ g(t*)} = {d in C(x): s_d ≥ t*}`.

**Proof:** strict increase preserves every comparison, equality group and source threshold ordering. Each observed threshold corresponds bijectively to its transformed threshold and yields the same source TP/FP set. Hence the highest feasible observed source boundary corresponds under g. The displayed equivalence holds for all real scores, including target scores absent from source. Recall and FPPI are identical. Probability-sensitive calibration metrics can change. A strictly increasing map followed by this reselection cannot rescue threshold-transfer recall. This is an algebraic control, not a hypothesis to train models to test.

The assumptions delimit important counterexamples:

| Change | Concrete consequence |
|---|---|
| Existing ties | Scores 0.8, 0.8 remain tied under strict g. Whole-group thresholding is invariant, but a target requiring half that group may have unattainable exact recall. “≥ρ” permits overshoot. Changing tie IDs or splitting ties by score-dependent randomness changes the policy. |
| Non-strict isotonic map or rounded scores | Source TP A=0.8 and FP B=0.4 both map to 0.5. A alone can no longer be selected by a scalar threshold. Even monotone nondecreasing maps can change FPPI and feasible subsets. Floating-point saturation/clipping can create the same issue. |
| Different interpolation between source scores | Source has two GT, TP scores 0.8 and 0.4, target recall 0.5. Any t in (0.4,0.8] selects the same source subset. Raw midpoint t=0.6 admits a target score 0.62. With g(s)=s², midpoint reselection gives t'=0.4 between 0.16 and 0.64; 0.62²=0.3844 is rejected. **Strict global monotonicity alone is insufficient** unless boundary selection is equivariant. The proposed observed-score rule avoids this. |
| Classwise maps plus a pooled threshold | Source has one pedestrian TP at 0.8 and one rider TP at 0.7, pooled ρ=0.5. Raw selection retains pedestrian. Map pedestrian s/2 and rider s; reselection retains rider. Both maps are strictly increasing, but cross-class ordering changes. Independent per-class thresholds remain invariant within each fixed class. |
| Nonmonotone mapping | Source TP at 0.8, FP at 0.4; g(s)=1−s puts FP above TP. A threshold satisfying full recall now includes both. Unconstrained negative-slope Platt is not the positive-slope control. |
| Multiclass logit transformation | Softmax temperature scaling is not generally g(max score): vectors (0.6,0.2,0.2) and approximately (0.55,0.45,0) reverse their max-score order at T=2. Different class maps may also change argmax labels. |
| Pipeline changes | Rerunning a fixed numerical prefilter after g(s)=s² can discard a score 0.6 at floor 0.5; it originally survived. Changing NMS, soft-NMS scores, box fusion, top-k, class labels or precision can alter candidates. Pure rank-based hard NMS with fixed boxes/ties is itself invariant under a global strict map; do not attribute changes to NMS without identifying the violated assumption. |

Retaining a fixed numeric threshold after calibration can change detections, but answers a different deployment-policy question. Recalibrating and selecting thresholds with **new target labels** changes the information available; a simple target-selected raw-score threshold is the necessary baseline. Neither calibration nor threshold adjustment can recover absent candidates. Conformal recall claims require a specified loss, exchangeability unit and risk statement; arbitrary weather shift does not inherit a source-only guarantee.

## 6. Uncertainty, dependence and interpretation

Use a paired **group bootstrap**, proposed 2,000 replicates, sampling independent groups within each partition and any disjoint design strata. Draw each group's bootstrap weight once and reuse it across all models and every condition/slice containing that group. Keep normal/adverse counterparts together. If several trips share a known route/capture dependency, use the larger block or sensitivity analysis. If grouping metadata are unavailable, report that limitation; image bootstrap is not automatically valid. Sparse independent groups cannot support precise intervals regardless of object count. Choose a desired precision before final allocation (proposed primary-recall interval half-width: five percentage points); assess it from group-level pilot variation rather than an arbitrary object-count cutoff. Unsupported slices remain descriptive.

Report two uncertainty targets: (a) conditional on deployed t*, resample test groups only; (b) for the source-selection procedure, resample source calibration groups, refit g, resample source threshold groups, reselect t*, then resample test groups. Preserve disjointness and pairing at every stage. Report threshold distributions on the native score scale, feasibility frequency, tie-group sizes and resulting metric intervals. Infeasible replicates remain a reported probability; feasible-only intervals are explicitly conditional. If a point estimate is infeasible, no ordinary transfer CI is available for that policy. These intervals condition on trained weights; training-seed variance requires actual independent training runs.

Model×condition×seed cells are dependent measurements, not independent sample size. Primary reporting is paired model-specific estimates and contrasts with intervals. Prespecify primary night/clear and model contrasts; use simultaneous bootstrap intervals if making multiple confirmatory claims. RQ2 correlations are exploratory with few checkpoints: source-only metrics must predict **new** conditions/models, not reuse target calibration/error metrics as advance warnings. With enough diversity, group cross-validation must hold out entire models (and, for condition generalization, conditions); otherwise show descriptive associations only. OCE's missed-object penalty mechanically shares information with recall; no claim of independent predictive value follows from correlation. Do not turn many bootstrap replicas into additional observations.

Comparisons estimate differences between complete trained systems. YOLO11/YOLO26/RT-DETR differ in pretraining, backbone, size, assignment, augmentation and optimization. Matching input size, source recall or AP does not identify the causal effect of NMS removal, transformers or quality-aware loss; selecting models by test AP also leaks information. A within-backbone D-FINE versus DEIM ablation can narrow a mechanism question, with controlled recipe changes, repeated seeds and bounded scope. BDD conditions also differ in scene mix; ACDC adds dataset shift. Use “associated with condition” and “system comparison.” Box recall is not collision avoidance or planner safety.

## 7. Minimal evidence needed next

Proposed initial system panel: YOLO11s, YOLO26s O2O, RT-DETRv2-S/R18 with exact config; DEIM-D-FINE-S is a fourth system only after feasibility. Keep D-FINE-S as the optional mechanism control. Do not silently replace failed models. Native checkpoint recipes and matched-data fine-tuning answer different questions; report pretraining exposure and compute/optimization differences. Begin with one reproducible recipe per system and add seeds before architectural claims.

Before G0 can pass, obtain lawful data access; freeze annotation versions and group IDs; count slices and independent groups; audit conversion and ignore policies; hash checkpoints and pin complete environments; run actual RTX 5060 forward/backward and evaluation smoke tests, including empty and crowded cases, finite losses and peak VRAM. A proposed test is 20 training iterations plus evaluation on 50 representative images, with memory and runtime logs. Source code inspection is not this test. No dataset download, GPU run, paid compute, push, PR or merge occurred in this pass.
