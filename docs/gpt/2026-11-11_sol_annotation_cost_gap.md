# Annotation-work gap: research decision

GPT Sol, 2026-11-11; base `dbfc34eb44d9702e684e82cb5ee8f8cb58b2da2b`. I want novel domain research at low token cost. Sol inspected the primary methods below and made this assessment; no independent review or peer exchange occurred. **G0 pending.**

**Decision: reject the proposed method claim.** Image-query efficiency differs from annotation-work efficiency, but unknown object count, variable cost and cost–failure dependence do not by themselves establish an uncovered method problem. Standard cost-sensitive importance sampling and conditional expected-cost modelling already supply the central ingredients. This bounded check does not establish that every sequential cost objective has been solved.

## What is established

The [checkpoint](../research/2026-11-11_audit_checkpoint.md) reports development medians: count mixture used 7.5 images / 39.5 eligible labels; uniform used 8 images / 24.5 labels. These are seen-panel summaries, neither paired dominance nor human-time measurements nor a novel result. Label count omits empty-image search, checking predictions, discovering misses, eligibility decisions, corrections and quality control. The complete-audit construction and its standard betting validity remain intact. The partial-label variant had no cost advantage and stays closed without tuning.

## Actual prior objectives and assumptions

[Sawade, Landwehr and Scheffer (2010)](https://proceedings.neurips.cc/paper_files/paper/2010/file/d7a728a67d909e714c0774e22cb806f2-Paper.pdf), Eq. (2), (4), (9), (11), (15) and Algorithm 1, estimate generalized risks, including recall with an unknown denominator. The objective is asymptotic variance minimization at a fixed number of label queries, called labeling cost `n`; it does not price heterogeneous image audits. Its oracle design uses a conditional second moment of the weighted, centered outcome. Practical probabilities approximate unknown labels; recall sampling includes both predicted classes. Moving to image-level count outcomes changes the observation unit, not this design principle.

[Active Testing (Kossen et al., 2021)](https://proceedings.mlr.press/v139/kossen21a/kossen21a.pdf), §2–3, Eq. (3)–(6), uses adaptive acquisition and LURE correction on a fixed test pool. Acquisition targets low estimator variance for a given label count `M`, approximating an oracle loss-based proposal through predictive surrogates. Its §5.3 “relative labeling cost” is a ratio of acquired-point counts at matched precision, not measured annotation minutes. It therefore does not directly solve our cost accounting, but predicting unknown outcomes and updating acquisition from queried feedback are already present. Its estimator is not our optional-stopping rejection test.

The directly relevant cost precedent is [Sawade et al., *Active Evaluation of Ranking Functions Based on Graded Relevance* (2013 extended abstract of 2012 work)](https://ijcai.org/proceedings/2013/0459.pdf). Eq. (4) minimizes estimation error subject to expected total labeling cost; Eq. (5) divides the conditional centered-outcome scale by the square root of query cost. Costs vary with result counts and document attributes. Algorithm 1 checks a known cost function before obtaining labels; §4 uses a document-length cost model, not measured human effort. Thus heterogeneous, multi-item query evaluation is covered; initially hidden detection cost is a real distinction, but requires more than replacing that cost function by a prediction.

[Papadopoulos et al., *We don’t need no bounding-boxes*](https://arxiv.org/pdf/1602.08405v3), §3 and §5, alternates detector training, localization and human verification. It measures verification time; fewer richer verification actions need not minimize total time. However, §5.1 returns one box per class per training image and explicitly avoids searching for additional instances. This is annotation assistance, not exhaustive frozen-detector recall evaluation. Its timings cannot price our audit, and verification of emitted boxes alone cannot discover common misses.

## Why hidden, coupled cost is insufficient novelty

**Sol inference, not a theorem attributed to these papers:** let `G,T` be complete eligible/true-positive counts, `R` pool recall, `C` complete audit effort and `H` pre-query information. A generic baseline uses `a(H)=E[(T−RG)^2|H]` and `c(H)=E[C|H]>0`. For uniform target images and a fixed proposal with replacement, the large-budget variance-times-expected-cost approximation is proportional to

`(sum a_i/q_i)(sum q_i c_i)`, giving `q_i ∝ sqrt(a_i/c_i)`.

This is a baseline template, not a proposed sampler or claimed optimum for rejection time. Cost may depend on the same hidden objects as failure mass: linear expected total cost requires no cost–error independence. Predicting only count while ignoring failure uncertainty would be a weak comparator. The strongest baseline indicated by this check is joint outcome/cost modelling with standard cost-sensitive allocation, alongside uniform querying, under the same complete-audit rule and full support. Unknown-cost overruns, cost tails and sequential power are not resolved by the displayed approximation; their existence alone does not establish novelty.

**The single substantive missing piece** is evidence that exhaustive missed-object search creates a practically important cost–failure mechanism that this joint expected-cost baseline cannot adequately handle. No such evidence is established here. ALPHA validity, a new metric or applying generic allocation to detections cannot substitute for it.

I am stopping at rejection, without implementation or allocation. Unused ACDC val images outside the 128-image development panel are only a candidate future pool; Sol inspected/generated no labels or predictions. Any later study needs separately authorized, frozen policies, an algorithm-unqueried pool and a material cost criterion fixed before target-error access. Box-count simulation measures a surrogate; human-effort claims require timed complete audits. Finite-pool randomization controls rejection error conditional on that pool, not future-scene generalization. Every image must retain positive query probability, including detection-empty images with common misses. Non-rejection never certifies high recall.

## Brief source ledger

Accessed 2026-11-11. Two required works plus exactly two additional primary methods; no broad survey. Public text was inspected at the locations cited. No source code, data or licensing audit was performed; no implementation, tests, fitting, inference, installs, GPU/Colab or children were used.

| Primary work / inspected version | Access and limit |
|---|---|
| Sawade, Landwehr, Scheffer, NeurIPS 23 (2010), *Active Estimation of F-Measures* | Publisher 9-page PDF; §1–2 and recall/support discussion. Rechecked cost/objective beyond the prior complete-audit ledger. |
| Kossen, Farquhar, Gal, Rainforth, ICML/PMLR 139 (2021), pp. 5753–5763 | Publisher 11-page PDF; §2–3, §5.3 and cost discussion. |
| Sawade, Bickel, von Oertzen, Scheffer, Landwehr, IJCAI (2013), pp. 3072–3075 | Publisher PDF, §2–4, Eq. (4)–(5), Algorithm 1. Extended abstract only; underlying 2012 full article not inspected. |
| Papadopoulos, Uijlings, Keller, Ferrari, CVPR (2016); arXiv:1602.08405v3, 2017-04-24 | Author preprint PDF, §3, §5.1–5.3. CVF PDF returned HTTP 403; one arXiv fallback succeeded; no retry loop. |
