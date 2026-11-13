# Verified omissions in a fixed-pool recall audit

GPT Sol, 2026-11-11; base `f825d50f8c9203e4f0944329c5d4df2e332b54f6`. I want a conservative partial-feedback decision at low cost. Sol derived the proofs and ran the bounded CPU demo; no independent review occurred. **G0 pending.**

**Decision:** valid under verified omissions; no novelty claim or useful annotation advantage established. Stop without tuning or new allocation. The [complete-audit results](2026-11-11_sol_recall_audit.md) remain unchanged.

## Matching lemma

Freeze predictions, threshold, score/candidate-ID order, classes, eligibility, geometry and annotation IDs. Each prediction chooses its highest-IoU available eligible same-class GT at IoU >=.50, breaking ties by unchanged annotation ID. These preferences must restrict consistently to subsets.

**Proof:** delete one eligible GT. Immediately before each prediction, the full-run available GT set A and subset-run set B satisfy either A=B or A=B union {h}. Initially h is the deleted GT. When sets coincide, subsequent eligible choices coincide. Otherwise, if the full run does not choose h, both choose the same shared GT (or neither); the invariant persists. If the full run chooses h and the subset run chooses b, the new extra full-side item is b. If the subset run chooses nothing, the sets become equal. Thus at termination |B|<=|A|: subset FN cannot exceed full FN. Apply single deletions successively for any subset. This is a proof, not enumeration; matches themselves may change.

The exact [matcher](../../src/threshold_transfer/metrics.py) tries eligible GT **before** ignore/crowd absorption; ignored regions are reusable and do not consume eligible matching capacity. Preserve their conventions; they are outside the denominator. Matching has no label-dependent prediction suppression, order changes or cross-image effects. Native zero-area rows never match and remain in D, as do ignored emitted rows. Changing retained IDs/ties, geometry or eligibility is outside the lemma.

The weaker fallback counts verified GT with **no** emitted same-class candidate reaching IoU .50. It too lower-bounds FN, but candidate reuse in this reachability oracle does not measure one-to-one recall. The stronger lemma holds here, so no fallback experiment was needed.

## Betting with partial observations

Let Z_i=9 FN_i be fixed latent mass, and Y_t=9 f_t for the queried image I_t. Verified omissions ensure 0<=Y_t<=Z_{I_t}. For positive total GT, the .90 recall null implies:

\[
9\sum_i FN_i\le\sum_i T_i\le C=\sum_i D_i.
\]

At each draw remove one image permanently. Let Q be previously queried images, U the remainder, S the sum of Q's **observed lower bounds**, B=C-S, and p_i>0 the actual conditional draw probabilities on U, summing to one. Choose p and eta in [0,1] predictably before drawing. Even if omissions depend on the draw, hidden truth, previous outcomes or fresh randomness, their pathwise bound gives, under the null:

\[
\sum_{i\in U}Z_i\le C-\sum_{i\in Q}Z_i\le C-S=B,
\qquad
\mathbb E\left[\frac{Y_t}{p_{I_t}}\mid\mathcal F_{t-1}\right]
=\sum_{i\in U}\mathbb E[Y_t\mid I_t=i,\mathcal F_{t-1}]
\le\sum_{i\in U}Z_i\le B.
\]

For B>0 use:

\[
M_0=1,\qquad M_t=M_{t-1}\left(1-\eta_t+\eta_t\frac{Y_t}{p_{I_t}B}\right).
\]

This is a nonnegative null supermartingale, so Ville bounds any crossing of 1/alpha by alpha, including adaptive stopping. No independence or omission-rate model is needed. Hidden feedback must not invalidate the recorded conditional p. Never double-count later labels from removed images.

If B=0, null remaining mass is zero: freeze wealth and reject logically on positive Y. S>C is already a contradiction; freeze afterward. These rules cover C=0 without division. Zero queries give no rejection. Freeze after exhaustion. Any rejection requires positive observed f, establishing positive GT; otherwise recall may be undefined. Dropping D_i-T_i from complete X enlarges the null: even complete-Y exhaustion need not detect every recall violation. Partial non-rejection/exhaustion **never certifies safety or high recall**. All-zero omissions can erase all power.

This concerns a frozen finite pool relative to a policy-defined reference, with design randomness only; it gives no IID-scene or future guarantee. Spurious, duplicate, misclassified, wrong-geometry or wrongly eligible labels are **not covered**. Cached annotations were not independently verified as physical truth.

## Prior overlap and boundaries

Reuse the [ALPHA/Active Testing/Sawade ledger](2026-11-11_sol_recall_audit.md#primary-source-ledger): the factor is ALPHA Eq. (5) with observation Y/(n p) and null mean B/n; adaptive sampling and recall ratios already have established antecedents. Conservative conditional domination resolves this application's observation gap, not an identified novel method. No method name is proposed. Two additional targeted primary fetches failed on 2026-11-11; neither supplies verified methodology, and neither was retried:

| Candidate source | Access limitation |
|---|---|
| Waudby-Smith/Ramdas, *Estimating means of bounded random variables by betting*, [publisher URL attempted](https://academic.oup.com/jrsssb/article/86/1/1/7043398) | Inaccessible; search-level identification only, full text unverified. |
| Murrugarra-Llerena/Jung, *Noise-Aware Evaluation of Object Detectors*, WACV 2025, [primary PDF](https://openaccess.thecvf.com/content/WACV2025/papers/Llerena_Noise-Aware_Evaluation_of_Object_Detectors_WACV_2025_paper.pdf) | 403; full text unverified. No robustness inference from snippets. |

## Locked development cost decision

The [script](../../experiments/2026-11-11_partial_audit.py) reuses cached complete counts/runs, helpers and native1280 predictions; input hashes match. Alpha=.05, eta=.5, seeds 0–19 and both original policies are unchanged. Hash retention uses a fixed SHA256 half-probability rule; adversarial omission removes the smallest-ID complete-matched label per image, using privileged truth only to construct feedback. Retained fields and emitted D are unchanged. The sampler receives only D and queried (label count,f). Private IDs/traces remain ignored. [Aggregate](2026-11-11_sol_partial_audit_aggregate.json) includes ranges and reasons.

Reproduce with installed Python 3.12.14: `experiments/2026-11-11_partial_audit.py --complete-cache PATH`. PATH was the prior task's ignored `C:/Users/Advait/.t3/worktrees/autonomous-sys-research/t3-21935e2a/outputs/colab/recall_audit_20261111/private_runs.json`; its SHA256 is recorded. The default ROOT cache location was absent; original cached inputs were read without modification.

Adverse costs below are medians; U/M denote uniform/count mixture. Each non-rejection counts its full cost.

| Observation / annotation regime | Queries U/M | Eligible labels observed U/M | Non-rejections U/M (of 20 each) |
|---|---:|---:|---:|
| Original complete X reference | 8 / 7.5 | 24.5 / 39.5 | 0 / 0 |
| Conservative Y / complete | 21.5 / 21.5 | 43.5 / 85 | 0 / 0 |
| Conservative Y / hash half | 114 / 87.5 | 96 / 104 | 0 / 0 |
| Conservative Y / omit matched | 21.5 / 21.5 | 36 / 71 | 0 / 0 |

Source: every regime/policy had 20 non-rejections and 256 queries; observed labels were 579/270/443 for complete/hash/omit. Synthetic omitted-TP sanity: true (G,T,D)=(10,9,9), partial (9,8,9), Y=9=C; naive partial X=10>C is an **INVALID negative control**, not a competitor. A changed retained tie ID breaks monotonicity (FN 0 to 1); zero-budget/exhaustion checks passed. Seen panels and seeds are development evidence, not unseen validation or a Monte Carlo nominal-error claim. Label counts are not human time. Partial feedback retains rejection power here but costs more than complete X; privileged omissions establish no deployable savings. No GPU, inference, installs, children, push, PR or merge.
