# Research question: annotation-efficient recall rejection

I want the next research step to address validation of a transferred recall claim rather than another detection-scale heuristic. The scale diagnostics are finished. This is a **candidate statistical research question**, with no validated new method, guarantee or novelty claim yet.

Consider a fixed image pool and frozen detector/threshold. Its emitted human detection counts `D_i` are observable without target GT. A complete image audit reveals eligible GT `G_i` and one-to-one TP `T_i`, with `T_i <= D_i` and `T_i <= G_i`. For object-weighted recall target .90, investigate the reduction

`X_i = 9*(G_i-T_i) + D_i-T_i >= 0`, `C = sum_i D_i`.

The high-recall null implies `sum X_i <= C`. For adaptive image sampling without replacement with recorded positive probabilities `p_i`, audited sum `S`, and predictable `eta` in `[0,1]`, investigate a candidate betting factor

`(1-eta) + eta * X_i / (p_i*(C-S))`.

Sol must try to break the derivation, check zero budgets/undefined recall/optional stopping, and identify its relationship to existing finite-population betting, recall estimation and active evaluation methods. No claim follows until the assumptions and proof hold. This would concern evidence **against** a high-recall claim on a fixed pool; failure to reject would not certify safety, future scenes or high recall. Audits must reveal all eligible GT under the frozen annotation policy.

If valid, a small CPU-only development simulation can hide the already retained labels, compare uniform sampling with one fixed full-support observable-count policy, and report annotation query cost. Monte Carlo does not establish statistical validity; no target-tuned sampling search or unseen-validation claim is allowed. The potential value is a principled audit of common misses without pretending that prediction agreement reveals them or that frames are IID. Whether the formulation is already covered by prior work is an explicit research question.

One concise Sol task, at most three targeted primary-source checks, no GPU/Colab allocation, new model, dataset scan, training or framework. Stop on a counterexample, prior-art closure or a complete proof-and-development decision. G0 remains pending; my explicit merge approval and the previous research limits remain.
