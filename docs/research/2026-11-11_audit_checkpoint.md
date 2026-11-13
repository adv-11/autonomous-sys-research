# Audit research checkpoint

GPT Sol studied rejection of a transferred .90 recall claim on a fixed image pool. **G0 remains pending.** At this checkpoint the proof/application studies were independently unreviewed. The later [Sol integration review](../reviews/2026-11-13_colab_integration_review.md) checked the narrow conditional arguments and reproduced the saved development aggregates. No novelty, early safety-certificate or future-scene claim follows.

- The [complete-audit construction](../gpt/2026-11-11_sol_recall_audit.md) survives under frozen predictions, exact complete labels and correct full-support randomization. Its ingredients overlap ALPHA, active testing and generalized recall-risk estimation.
- Verified GT omissions require a different observation rule. Sol's [partial-feedback result](../gpt/2026-11-11_sol_partial_audit.md) proves matching monotonicity for the exact fixed-order matcher and conservative betting with lower-bound FN observations. It does not cover invented labels, coordinate/eligibility changes or arbitrary annotation errors.
- The locked demo finds **no useful annotation advantage** for the conservative variant. Complete audits need fewer queries and fewer observed eligible labels on this seen panel. No kernel, omission-rate or policy tuning follows.
- Non-rejection, including exhaustion under partial observations, never establishes high recall. Displayed empirical GPU use stays1.28units; these studies used cached data and CPU only.

## Problem-level decision

I am closing the partial-audit variant line. The remaining practical question is the difference between **image queries and annotation work**. In the original complete-audit demo, count-weighted sampling used a median7.5queries versus8for uniform, while observed eligible labels were39.5versus24.5. These are development medians, not paired dominance, human minutes or an unseen-validation result.

The requested assessment was completed in the [cost-gap decision](../gpt/2026-11-11_sol_annotation_cost_gap.md), which rejected the method claim. This line remains closed; the historical request is not a new sampler assignment. Any separately justified future study would need a frozen policy, an unqueried pool, a material cost criterion and honest annotation-cost measurement; inherited statistical validity alone is not a new contribution.
