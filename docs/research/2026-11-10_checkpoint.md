# Research checkpoint: threshold policies, resolution and scale consistency

I want to understand which detector failures remain after ordinary operating-point and image-scale effects are controlled, before proposing a new method. GPT Sol ran the experiments and GPT Astra developed hypotheses, reviewed the 640 result and assessed the closest prior work. All GPU execution used Colab; later comparisons reused cached predictions on CPU. **G0 remains pending.**

## Compact result

- **H1 rejected on this panel:** all four candidate policies selected the same .90 source threshold. Every prespecified source-boundary/direct-candidate contrast was zero. The fresh-source repeat was not triggered.
- **H2 supported under its fixed screening rule:** doubling input resolution recovered a net 34/89 small GT versus 12/127 larger GT. Unequal baseline miss headroom prevents calling this preferential recovery per missed small object. Normal references improve too, undermining a night-specific account.
- **Ordinary baselines close the immediate method opportunity:** fusion offers a recall/FP tradeoff; the agreement gate is worse than 1280 on both pooled adverse measures at .90. The union matching oracle adds only four adverse GT beyond 1280.
- **Decision:** stop this candidate-policy/fusion method direction. Current observations do not establish novelty. No further GPU run, calibrator or model sweep follows from them.

The frozen panel contains 256 COCO source-selection images, 256 disjoint COCO reference images, 128 adverse ACDC images and 60 annotated normal references. The table uses all 216 eligible adverse human GT and all 128 adverse images, including empty images. Each pipeline selects its own threshold on the same COCO source objective; these are descriptive transferred operating points, not target-tuned thresholds or population recall guarantees.

| Pipeline at source objective .90 | Adverse TP / GT | Recall | FP / images | FPPI |
|---|---:|---:|---:|---:|
| Native 640 | 96/216 | 44.44% | 311/128 | 2.430 |
| Native 1280 | 129/216 | 59.72% | 179/128 | 1.398 |
| Post-NMS late fusion | 122/216 | 56.48% | 143/128 | 1.117 |
| Agreement-filtered 1280 | 116/216 | 53.70% | 203/128 | 1.586 |

Fusion is not dominated here: it trades seven fewer TP for 36 fewer FP than 1280. The gate attains the requested source recall while losing 13 adverse TP and adding 24 FP relative to 1280. That is a useful development warning, but the gate's low-resolution-witness requirement already explains why it can discard recovered objects. It is not by itself a new reliability mechanism.

## Evidence and interpretation

The [640 experiment](../gpt/2026-11-10_sol_completion.md) records the frozen sample, native policies, zero-area FP convention, failed-attempt history and raw-evidence provenance. Astra's [scientific review](../reviews/2026-11-10_sol_empirical_review.md) independently reproduces its decisive claims. The [1280 intervention](../gpt/2026-11-10_sol_resolution.md) preserves gained/lost GT, old versus source-reselected thresholds and compute measurements. The [cached baselines](../gpt/2026-11-10_sol_scale_baselines.md) report all source objectives, ceilings, controls and the GT-aware maximum-cardinality oracle. Astra's separate [publication review](../reviews/2026-11-10_empirical_checkpoint_review.md) inspected the newer code and independently executed the decisive retained-output calculations; no material blocker was found. The review artifact was committed before its task's credit error and recovered on 2026-11-11; it remains attributed to Astra, with no claim of new Sol verification.

Astra's [coverage diagnosis](../gpt/2026-11-10_astra_coverage_diagnosis.md) separates scale/ontology/localization evidence from causal interpretation. Its [opportunity assessment](../gpt/2026-11-10_astra_scale_opportunity.md) finds established overlap in view fusion, geometry-conditioned calibration and prediction-consistency evaluation, with explicit primary-source access limits. It recommends no current method claim.

COCO is not verified clear/day; pretrained exposure is not excluded. ACDC scenes and reference views are dependent, normal/adverse views need not contain the same people, and the human/crowd task is provisional. No IID intervals, causal-night effect, official AP equivalence, primary BDD result or physical detector-capacity claim is made. The conditional pipeline ceiling is not exhaustive object coverage. The later cached baselines are development analyses on already observed panels, not unseen validation.

## Resource and next decision

Displayed empirical GPU use totals **.98 compute units**, including the earlier failed .31-unit attempt. Billing can lag. Every owned session was terminated and zero active assignments were verified. Cached fusion/gating required no new inference; using either online would require both network passes, with no measured joint end-to-end latency or cheaper-than-1280 claim.

Before reopening method development, I need a specific residual information or failure mechanism that ordinary score, geometry, counts and fusion baselines do not explain, together with feasible unseen labelled validation and a kill criterion. More scale, a new method name or more compute will not supply that evidence. The next immediate deliverable is a focused review and a publishable research checkpoint, preserving these negative decisions. My explicit approval still governs sequential merges; [PR #8](https://github.com/adv-11/autonomous-sys-research/pull/8) remains open at the latest host check.
