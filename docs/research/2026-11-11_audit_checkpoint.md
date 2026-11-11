# Audit research checkpoint

GPT Sol studied rejection of a transferred .90 recall claim on a fixed image pool. **G0 remains pending.** These proof/application studies have not received an independent publication review, and make no novelty, early safety-certificate or future-scene claim.

- The [complete-audit construction](../gpt/2026-11-11_sol_recall_audit.md) survives under frozen predictions, exact complete labels and correct full-support randomization. Its ingredients overlap ALPHA, active testing and generalized recall-risk estimation.
- Verified GT omissions require a different observation rule. Sol's [partial-feedback result](../gpt/2026-11-11_sol_partial_audit.md) proves matching monotonicity for the exact fixed-order matcher and conservative betting with lower-bound FN observations. It does not cover invented labels, coordinate/eligibility changes or arbitrary annotation errors.
- The locked demo finds **no useful annotation advantage** for the conservative variant. Complete audits need fewer queries and fewer observed eligible labels on this seen panel. No kernel, omission-rate or policy tuning follows.
- Non-rejection, including exhaustion under partial observations, never establishes high recall. Displayed empirical GPU use stays1.28units; these studies used cached data and CPU only.

## Problem-level decision

I am closing the partial-audit variant line. The remaining practical question is the difference between **image queries and annotation work**. In the original complete-audit demo, count-weighted sampling used a median7.5queries versus8for uniform, while observed eligible labels were39.5versus24.5. These are development medians, not paired dominance, human minutes or an unseen-validation result.

Before implementing another sampler, I want one concise assessment of whether unknown object-count cost creates an uncovered object-detection evaluation problem. The closest cost-aware active-evaluation and object-detection annotation methods must be addressed. If they already cover it, reject the method claim. Any future study needs a frozen policy, an unqueried pool, a material cost criterion and honest annotation-cost measurement; inherited statistical validity alone is not a new contribution.
