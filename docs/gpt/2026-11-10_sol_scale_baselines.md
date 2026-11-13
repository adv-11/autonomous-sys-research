# Cached ordinary multiscale baselines

**GPT Sol, 2026-11-10; base `c5284bdd9908111f4a6f4245917862e24dd9c38e`. Real CPU evaluation of retrieved predictions; G0 pending.** I want to test whether ordinary cross-resolution processing leaves enough useful opportunity to justify method development. The result supports **stopping the current method direction**. Fusion recovers four adverse ceiling GT beyond 1280, but loses seven operating TP at the .90 source objective while reducing FP. The agreement gate attains every source objective yet has lower adverse recall and more FP than 1280 at .90. These are useful negative development results, not a novel reliability mechanism.

The [script](../../experiments/2026-11-10_cached_scale_baselines.py) and [aggregate](2026-11-10_sol_scale_baselines_aggregate.json) preserve all 14 named panels plus the existing adverse/normal pools, .80/.90/.95 operating points, ceilings, counts, FPPI and gained/lost counts. Historical baseline files and the evaluator are unchanged. No inference, new image/annotation audit, installation, training, Colab call or GPU operation occurred.

## Locked alternatives and accounting

The unchanged 700-image manifest supplies 256 COCO selection, 256 COCO reference, 128 adverse and 60 annotated normal images. Empty images, eligible GT and provisional human/crowd policy are unchanged. The two named caches are YOLO11s native post-NMS predictions at 640 and 1280, floor .0001/cap 3000. Both were already retrieved and verified; no batch re-verification or transfer was repeated.

**Late fusion** concatenates both positive-area lists, prefixes candidate IDs with resolution, orders globally by descending native score then ID, and applies same-image/class hard NMS, suppressing only IoU **>.70**, retaining equality. Scores and stored boxes are unchanged; there is no averaging, recalibration or final cap. Tagged lexical ties put `1280:` before `640:`. This is post-NMS fusion, not equivalent to native pre-NMS multiscale inference.

**Agreement-filtered 1280** retains a positive 1280 row iff any positive human row from the **entire** same-image 640 cache has IoU **>=.50**. The witness pool is independent of the operating threshold; 1280 score/geometry are unchanged. Source infeasibility would remain infeasible, without relaxing the gate.

Zero-area rows never enter overlap operations: fusion retains all 118+1,339=1,457 emissions; the gate retains all 1,339 from 1280. The unchanged `pilot_evaluator` appends these as explicit FP without crowd absorption. Positive rows use unchanged `ReferenceEvaluator`, greedy one-to-one IoU .50 and provisional same-category crowd/ignore IoA .50, allowing native coordinates outside bounds. No FP is assigned a GT size or person/rider stratum. Positive counts across 700 images are 43,986 / 95,692 / 123,546 / 41,293 for 640 / 1280 / fusion / gate.

## Source feasibility

Each pipeline selects its own highest observed source score meeting the objective, inclusively with whole ties. Source TP is 464/579 at .80, 522/579 at .90 and 551/579 at feasible .95. Each cell gives **boundary; source FP**, with FPPI obtained by dividing by 256.

| Pipeline | .80 | .90 | .95 |
|---|---|---|---|
| 640 | .24039360880851746; 71 | .043987125158309937; 480 | **INFEASIBLE** |
| 1280 | .2718588709831238; 110 | .08221367746591568; 405 | .01611722819507122; 1,479 |
| Fusion | .41543442010879517; 80 | .14203764498233795; 325 | .038388121873140335; 1,062 |
| Gate | .269478976726532; 104 | .04346418380737305; 572 | .0017826053081080317; 3,760 |

Source ceilings are 539/579, 570/579, 571/579 and 553/579 respectively. Gate .95 is **LOW_HEADROOM** (95.51% ceiling); source attainment is an empirical selection result, not a population guarantee. Four gate source .95 FP are zero-area emissions; none contributes at source .80/.90. Undefined recall remains explicit wherever a denominator is zero; the infeasible 640 .95 has no substituted operating point.

## Equal-objective operating comparison

At each pipeline's **own .90 source boundary**, cells give **TP/eligible GT; FP (FPPI)**. These are transferred descriptive operating results, not thresholds chosen on ACDC.

| Panel; images | 640 | 1280 | Fusion | Gate |
|---|---|---|---|---|
| COCO reference; 256 | 423/528; 539 (2.105) | 438/528; 449 (1.754) | 434/528; 407 (1.590) | 447/528; 683 (2.668) |
| Fog; 32 | 15/27; 56 (1.750) | 21/27; 33 (1.031) | 20/27; 29 (.906) | 20/27; 33 (1.031) |
| Night; 32 | 27/77; 45 (1.406) | 32/77; 29 (.906) | 29/77; 20 (.625) | 33/77; 45 (1.406) |
| Rain; 32 | 21/40; 115 (3.594) | 25/40; 68 (2.125) | 24/40; 55 (1.719) | 22/40; 64 (2.000) |
| Snow; 32 | 33/72; 95 (2.969) | 51/72; 49 (1.531) | 49/72; 39 (1.219) | 41/72; 61 (1.906) |
| Pooled adverse; 128 | 96/216; 311 (2.430) | 129/216; 179 (1.398) | 122/216; 143 (1.117) | 116/216; 203 (1.586) |
| Pooled normal; 60 | 59/154; 189 (3.150) | 87/154; 130 (2.167) | 83/154; 109 (1.817) | 77/154; 115 (1.917) |

Against 1280, fusion .90 gains/loses GT **2/9 adverse, 1/5 normal, 14/18 COCO reference**. Its adverse recall is 56.48% versus 59.72%, with .281 fewer FPPI. Against 640 it gains/loses 32/6 adverse GT and reduces FP from 311 to 143. Thus ordinary fusion improves on the smaller pipeline here, but does not recover 1280 losses at a superior pooled .90 operating point. The mixed per-panel results are preserved: paired rain gains one TP and reduces FP versus 1280, whereas pooled recall falls.

Gate .90 gains/loses GT **3/16 adverse, 3/13 normal, 17/8 COCO reference** versus 1280. At the fixed 1280 .90 boundary it removes 16 adverse TP and 71 FP (113 TP/108 FP remain); lowering to its own source boundary restores three TP and adds 95 FP, yielding 116/203. The analogous normal decomposition is 87/130 -> 72/75 -> 77/115; COCO reference is 438/449 -> 430/409 -> 447/683. The gate's extra COCO-reference recall therefore accompanies a substantial FP increase, while source feasibility does not protect adverse coverage.

Sensitivity results do not establish dominance either. At .80, adverse TP/FP are **74/36, 106/29, 93/17, 100/16** in pipeline order; normal are 40/24, 66/27, 59/17, 61/24. At .95, feasible 1280/fusion/gate adverse results are **145/882, 141/671, 128/1,638**; normal are 105/494, 98/457, 83/706. COCO-reference .95 is 472/1,638, 473/1,255, 479/3,693. Fusion's one additional reference TP at .95 is a finite favorable comparison, not an adverse transfer gain.

## Ceilings, complementarity and geometric bound

Every cached output is retained for each ceiling. Cells give **TP/GT (M%); FP (FPPI)**; these tails are not deployment policies.

| Panel | 640 | 1280 | Fusion | Gate |
|---|---|---|---|---|
| COCO selection | 539/579 (93.09); 11,929 (46.598) | 570/579 (98.45); 25,015 (97.715) | 571/579 (98.62); 32,312 (126.219) | 553/579 (95.51); 11,515 (44.980) |
| COCO reference | 482/528 (91.29); 12,206 (47.680) | 506/528 (95.83); 25,086 (97.992) | 516/528 (97.73); 32,802 (128.133) | 487/528 (92.23); 11,224 (43.844) |
| Pooled adverse | 128/216 (59.26); 7,397 (57.789) | 174/216 (80.56); 18,809 (146.945) | 178/216 (82.41); 24,583 (192.055) | 133/216 (61.57); 5,811 (45.398) |
| Pooled normal | 74/154 (48.05); 3,288 (54.800) | 115/154 (74.68); 8,071 (134.517) | 115/154 (74.68); 10,721 (178.683) | 86/154 (55.84); 2,373 (39.550) |

Fusion ceiling gained/lost versus 1280 is **4/0 adverse, 0/0 normal, 12/2 COCO reference**. It recovers all four adverse GT lost in the earlier 640->1280 comparison; three are in the fixed >=16 projected-640-height complement, one <16. The gate loses 41/174 adverse ceiling TP, including 30 small and 11 larger; normal loses 29/115 and COCO reference 19/506. At adverse .90, its net loss is 13 small TP and zero larger TP. Person/rider counts remain in the aggregate, without allocating FP to these GT strata.

The optional oracle is **maximum-cardinality one-to-one matching** on positive union candidates at IoU >=.50 against eligible GT, ignoring scores. It is GT-aware, not deployable recall, and cannot reuse a candidate as a best-IoU-per-GT oracle can. The 1280/union oracle TP counts are **174/178 adverse, 115/116 normal, 506/518 COCO reference**. Thus only four adverse objects beyond the 1280 candidate geometry are available at all; fusion already attains that adverse ceiling. This bound says nothing about acceptable FP cost or recoverability of misses by another model. Empty images and ignored/crowd GT remain explicit in ordinary metrics; oracle matching excludes ignored/crowd GT and has no FP/reliability interpretation.

## Execution, exchange and decision

The only synthetic check passed: nested boxes with exact .70 NMS/.50 gate equality, deterministic score ties, class/image isolation, and one ambiguous two-GT matching graph requiring augmentation. These synthetic results are separate from the real cache evaluation. No full regression suite was run. The final CPU aggregate run took **14.422 seconds**, using read-only Python 3.12 and NumPy 2.5.4; no torch/CUDA import was executed. A prior 15.375-second run produced identical scientific counts; the final run reduced public diagnostic repetition and retained detailed private strata. Manifest/cache/code SHA256 records are in the aggregate; only the named manifest and two caches were hashed, not 352 batches.

Raw alternatives, evaluator rows, GT transitions, detailed aggregate and actual peer exchanges remain under ignored `C:/Users/Advait/autonomous-sys-research/outputs/colab/cached_scale_baselines_20261110/`. Public artifacts omit per-GT/candidate identities, coordinates and image filenames. Both alternatives cost **two existing network passes**. Historical native loops were 25.19 s and 40.23 s measured separately, including capture/processing; their sum is not measured joint end-to-end latency. No cheaper-than-1280 claim follows. Cumulative historical use remains **.98 displayed CU**, with no new allocation.

**Actual exchange:** GPT Astra's active-task proposal said that gate exclusion without a low-resolution witness is definitional; the witness need not match the same GT. It requested source feasibility, operating/ceiling transitions and normal/COCO controls. GPT Sol replied via successful `mode:steer`: “no essential omission in that interpretation,” committed to those comparisons, and stated that results were then uncomputed and joint latency unmeasured. After computation, Sol attempted a second steer containing the actual aggregates above. The tool returned `thread_not_sendable`: “has no running turn that can be steered.” The peer was not restarted; delivery or agreement on these numbers is not implied. The coordinator subsequently reported Astra's completed stop recommendation at `81d2aabd677b0005eaba88a7af2d79e439fc1332`, including ordinary fusion/calibration prior art and abstract-only access for PCR 2025. This is coordinator-reported context, not an independent source check or formal review by Sol.

**My next decision is to stop this method-development direction on the present evidence.** Ordinary fusion accounts for the small adverse geometric complementarity and presents familiar recall/FP tradeoffs. Source-feasible agreement can discard useful target coverage, but its rule already requires low-resolution witnesses: this does not identify a new mechanism, and normal controls show a similar exclusion. No learned calibrator, extra baseline or GPU run follows. Reopening would require useful conditional information beyond score/geometry/count composition and independent unseen validation, neither established here.

This is post-pilot development on seen ACDC. COCO is not verified clear/day; pretrained exposure, provisional human/crowd policy, scene dependence and different normal/adverse people remain limitations. No CI, causal darkness effect, novelty, general reliability guarantee, official AP or BDD result is claimed. H1 remains closed; H2 remains an ordinary scale effect. G0 stays pending. GPT Sol performed this analysis without Claude or children. Formal publication review is separately scoped; my explicit approval still governs merges. No push, PR or merge occurred.
