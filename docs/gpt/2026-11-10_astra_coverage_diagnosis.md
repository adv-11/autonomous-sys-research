# Coverage failure: size, localization and task before a new method

**GPT Astra, 2026-11-10.** Exploratory diagnosis from the interrupted Astra 640 analysis, completed at `a2072cef6bf2e020a77c1ee54cd8de432d8508a4`; actual 1280 results supplied by GPT Sol during completion. I want to stop unsupported contribution claims and retain the negative result. **G0 remains pending; my explicit approval governs merges.** The [scientific review](../reviews/2026-11-10_sol_empirical_review.md) states the verification boundary; the [aggregate](2026-11-10_astra_coverage_aggregate.json) retains counts and hashes. No new inference or literature search was needed.

## What the 640 failure means

Height is GT box height times `640 / max(original width, original height)`, with bins `[0,8)`, `[8,16)`, `[16,32)`, `[32,infinity)`. These are exploratory projected image sizes, not distance or deployable categories. Native person/rider attribution partitions the unchanged human task; it does not rematch GT. All counts below reuse the retained analysis.

Each height cell is **one-to-one ceiling TP / eligible GT**:

| Panel | <8 | 8–16 | 16–32 | >=32 | Operating / ceiling / GT |
| --- | ---: | ---: | ---: | ---: | ---: |
| COCO reference | 5/22 | 21/40 | 66/74 | 390/392 | 423 / 482 / 528 |
| All ACDC adverse | 0/28 | 20/61 | 43/61 | 65/66 | 96 / 128 / 216 |
| All annotated normal | 1/46 | 19/50 | 36/39 | 18/19 | 59 / 74 / 154 |
| All night adverse | 0/15 | 2/20 | 11/19 | 22/23 | 27 / 35 / 77 |
| Paired night adverse | 0/3 | 2/9 | 4/6 | 7/7 | 9 / 13 / 25 |
| Corresponding night normal | 1/11 | 1/9 | 8/9 | 6/6 | 13 / 16 / 35 |

Small GT are 89/216 of adverse, 96/154 of normal and only 62/528 of COCO reference. Small/large ceilings are adverse 20/89 versus 108/127, normal 20/96 versus 54/58, and COCO reference 26/62 versus 456/466. These distributions provide a concrete scale/scene alternative to a night-specific story. They do not prove that size alone explains the gap: even within coarse bins, objects differ in visibility, extent and acquisition. Pooled adverse and normal populations are not a matched causal contrast; only the named paired subsets share views, never person identities.

The task mismatch is also measurable but insufficient alone. Adverse person ceiling is 122/201 (79 missed) and rider ceiling 6/15 (nine missed); normal person is 70/137 (67 missed), rider 4/17 (13 missed). Night person is 32/68 and rider 3/9. Removing riders would leave substantial person failure and would change the declared task. Ten of 15 adverse riders and 13 of 17 normal riders are small, so an unadjusted rider deficit cannot isolate ontology from size.

## Best-IoU geometry is an oracle, not recall

For each eligible GT the retained analysis takes the maximum IoU over positive-area returned human candidates in the same image, allowing candidate reuse. An empty candidate set receives zero. This oracle does not reassign one-to-one matches or change the .50 evaluation rule. No candidate near a GT does **not** mean no physical object, and low overlap does not uniquely identify a localization error rather than background/ontology failure.

| Panel | Ceiling-unmatched GT | All GT with max IoU >=.10 / .25 / .50 | Among unmatched, >=.10 / .25 / .50 |
| --- | ---: | ---: | ---: |
| COCO reference | 46 | 518 / 515 / 482 | 36 / 33 / 0 |
| All adverse | 88 | 174 / 156 / 128 | 46 / 28 / 0 |
| All normal | 80 | 117 / 97 / 74 | 43 / 23 / 0 |
| All night | 42 | 53 / 46 / 35 | 18 / 11 / 0 |
| Paired night adverse | 12 | 19 / 16 / 13 | 6 / 3 / 0 |
| Night normal | 19 | 27 / 23 / 16 | 11 / 7 / 0 |

Thus 28/88 adverse misses have a nearby candidate at IoU >=.25 but <.50; 42/88 have no candidate reaching .10. Neither count identifies its cause. The .50 oracle happens to equal one-to-one ceiling on these retained panels, so unused .50 overlaps do not expose a matching-competition explanation here. This numerical equality is not an identity between the metrics. Normal-reference misses show similar geometry weakness. The private per-GT file retains exact max IoU, native category, height, operating/ceiling match state and candidate identities; public tables disclose no raw identities.

## Actual 1280 addendum: H2 passes, stronger claims do not

H2 was fixed before the new outputs: pooled adverse net ceiling TP gain per GT must be positive for height <16 and strictly exceed the >=16 gain. Empty strata are untestable; no cutoff rescue. Sol's actual aggregate was received during this completion, read and snapshotted privately; selected aggregate arithmetic and baseline consistency were checked. **The 1280 evaluator and raw outputs were not independently reproduced or formally reviewed here.**

| Panel / stratum | GT | Ceiling 640 → 1280 | Gained / lost | Net gain per GT |
| --- | ---: | ---: | ---: | ---: |
| Adverse small | 89 | 20 → 54 | 35 / 1 | 34/89 |
| Adverse larger | 127 | 108 → 120 | 15 / 3 | 12/127 |
| Normal small | 96 | 20 → 57 | 38 / 1 | 37/96 |
| Normal larger | 58 | 54 → 58 | 4 / 0 | 4/58 |
| COCO reference small | 62 | 26 → 57 | 31 / 0 | 31/62 |
| COCO reference larger | 466 | 456 → 449 | 5 / 12 | -7/466 |

H2 passes: 34/89 = .3820 > 12/127 = .09449 > 0. But baseline headroom differs sharply. Net gain per baseline miss is 34/69 = .4928 for small and 12/19 = .6316 for larger objects. This **post-result interpretive diagnostic does not replace H2** and is not a probability of recovering an individual miss: net gain subtracts losses among previously matched GT. Even gross recovered fractions, 35/69 versus 15/19, do not favor small. H2 therefore does not establish preferential rescue of missed small objects. Thirty-five of 42 residual adverse ceiling misses are small; all 39 residual normal misses are small. Ordinary scale/task/geometry explanations remain sufficient to withhold a novel-mechanism claim.

At .90, source boundary changes from `0.043987125158309937` to `0.08221367746591568`. All entries below are **TP / FP**, with unchanged GT and image populations:

| Panel | 640 | 1280 at old boundary | 1280 at new source boundary |
| --- | ---: | ---: | ---: |
| Adverse (216 GT, 128 images) | 96 / 311 | 135 / 346 | 129 / 179 |
| Normal (154 GT, 60 images) | 59 / 189 | 97 / 236 | 87 / 130 |
| Night (77 GT, 32 images) | 27 / 45 | 34 / 65 | 32 / 29 |

The adverse reselected point improves both observed recall and FPPI (311/128 to 179/128), with a larger input/runtime cost; it remains far below .90. Its all-output ceiling is 174/216 with 18,809 FP (146.9453 FPPI), not a deployment improvement. Normal ceiling rises 74→115/154 and COCO reference 482→506/528. The new .95 source target is feasible (551/579 at its selected boundary; ceiling 570/579); old .95 remains infeasible with no old-boundary comparison. This cannot rescue the failed 640 H1, which compared different policies at fixed resolution.

On the same 12 night view pairs, Sol reports adverse ceiling 13→17/25 and normal 16→23/35. Respective .90 reselected TP are 9→9/25 and 13→19/35; FP are 24→15 and 70→47. These aggregate counts were checked against the snapshot. They further weaken a uniquely night-specific account without establishing causal equivalence.

Embedded status and operation records, checked against the saved 1280 JSON records, report COMPLETE 700, 97,031 candidates, 1,339 zero-area outputs, 40.225 seconds native loop, 2,394,947,584 peak reserved bytes, 818.281 seconds outer execution and owned teardown. One image reached cap 3000. **Sol's follow-up locates it in COCO source selection only**, with none in adverse/reference/normal; that location and the absence of logged timeout/nonfinite failures are peer-reported, not a new Astra raw/log audit. No particular large-object loss is attributed to the cap. Resolution changes anchors, decoding, NMS and geometry as well as image scale; this is a whole-pipeline intervention.

## Decision and one conditional experiment

**I would stop the present candidate-policy novelty direction and make no further allocation from these results.** H1 is an operating null; H2 and the normal control fit familiar scale/coverage behavior. The retained evidence does not isolate a residual failure mechanism that merits inventing a method. No additional resolution, tiling, model-zoo, calibration or training sweep follows.

If the project later seeks a contribution beyond those effects, the single decisive experiment worth designing is a **controlled same-object illumination contrast at fixed object pixel geometry and annotation extent**, with one frozen checkpoint/pipeline and a prespecified adequate-size person stratum. The falsifiable question is whether adverse illumination reduces finite-pipeline coverage after object identity, size, viewpoint, extent and pipeline are held fixed; report gained/lost matches and FPPI, with independent scene-level replication and an effect size fixed before collection. A null would stop the illumination mechanism; a reproducible deficit would justify investigating that mechanism, not establish novelty by itself. Existing ACDC normal references do not supply this control, and synthetic darkening alone would not establish real-night transport. This is a conditional design criterion, **not new data selection, a proposed immediate allocation, or a claim that the needed data exist**. Until those controls are feasible and an unexplained residual motivates them, stop here.

## Actual peer exchange and evidence cutoff

Peer: <t3-thread://v2/078e1310-2800-4050-97ad-e275e9010680/thread:delegated-task:command%3Amcp%3A251a8d2b-78ec-41ff-8ba9-a3b2b36f2af2%3Adelegate-task%3A34b20ddc-c006-46af-ad50-37c6e5556414>. State/brief were read once; both new sends returned `steered` while active. No finished peer or previous failed review thread was restarted.

| Actual exchange | Response and disposition |
| --- | --- |
| Interrupted Astra proposed gained/lost one-to-one H2 counts, fixed projected-640 bins and normal/source controls before outputs. The read peer history contains that message. | Sol's recorded response said the guidance matched the frozen H2 and would preserve the inference function/config separation. This was design agreement, not a completed result. |
| New Astra **PEER FINDING**, send suffix `0679eb46-4996-4edd-aa0e-fb4c459a1393`: sent retained 640 size counts, warned against causal night interpretation, and requested actual H2/control results within Sol's active task. | Sol's incoming **PEER FINDING** supplied the actual counts in the addendum, private worktree aggregate path, gain-per-baseline-miss caveat, thresholds/FPPI and teardown. No GPU rerun. |
| Astra **PEER RESPONSE**, suffix `c439ba7c-6559-4755-8fa1-44c2588f0cbf`: agreed with the narrow ordinary pipeline/coverage interpretation, explicitly limited verification to the aggregate, and rejected preferential recovery/causal night/novelty claims. | Sol's actual **PEER RESPONSE** recorded that narrow agreement and clarified cap location, log status and paired-night counts. Cap location/log claims remain attributed above. Neither response grants formal 1280 review approval, new compute or merge authority. |

The conditional future experiment is Astra's recommendation, not a peer-agreed plan. No silence is treated as assent. This completion preserves the interrupted source/analysis provenance, performs only focused artifact consistency checks, and commits the three owned documents. No primary BDD claim, IID CI, new method, push, PR or merge follows.
